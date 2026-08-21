"""Weekly digest: match active subscribers → Resend email."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.db import AlertSubscription, UserProfile, utcnow
from app.models.enums import DomainCategory, SkillLevel
from app.models.schemas import ListingRead, MatchRequest
from app.services.email import (
    EmailNotConfiguredError,
    render_digest_email,
    resend_configured,
    send_email,
)
from app.services.matching import discord_team_url, filter_listings, listing_to_read
from app.services.ranking import rank_listings_heuristic


def ensure_unsubscribe_token(sub: AlertSubscription) -> str:
    if not getattr(sub, "unsubscribe_token", None):
        sub.unsubscribe_token = str(uuid4())
    return sub.unsubscribe_token


def unsubscribe_url_for(token: str) -> str:
    base = get_settings().app_base_url.rstrip("/")
    return f"{base}/unsubscribe?token={token}"


def _deadline_label(deadline: Optional[datetime]) -> str:
    if not deadline:
        return "deadline TBA"
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    days = (deadline - datetime.now(timezone.utc)).days
    if days < 0:
        return "closing soon"
    if days == 0:
        return "closes today"
    if days == 1:
        return "closes tomorrow"
    return f"closes in {days} days"


def digest_for_profile(
    session: Session,
    profile: UserProfile,
    *,
    limit: int,
) -> List[ListingRead]:
    """Heuristic shortlist only — digests should stay cheap and predictable."""
    request = MatchRequest(
        profile_id=profile.id,
        free_text=profile.free_text,
        skill_level=profile.skill_level or SkillLevel.beginner,
        domains=[DomainCategory(d) for d in (profile.domains or []) if d],
        country=profile.country or "IN",
        students_only_ok=profile.students_only_ok,
        can_travel=profile.can_travel,
        max_team_size=profile.max_team_size,
        prefer_starter_code=profile.prefer_starter_code,
        min_deadline_days=profile.min_deadline_days if profile.min_deadline_days is not None else 7,
        limit=limit,
    )
    candidates = filter_listings(session, request, broaden_domains=False)
    broadened = False
    if len(candidates) < 3:
        widened = filter_listings(session, request, broaden_domains=True)
        if len(widened) > len(candidates):
            candidates = widened
            broadened = True
    ranked = rank_listings_heuristic(candidates[:40], request)
    return [
        listing_to_read(
            item.listing,
            fit_reason=item.fit_reason,
            is_expanded_match=broadened and bool(request.domains),
        )
        for item in ranked[:limit]
    ]


def _listing_payload(item: ListingRead) -> Dict[str, Any]:
    return {
        "title": item.title,
        "url": item.url,
        "organizer": item.organizer,
        "prize_pool_usd": item.prize_pool_usd,
        "deadline_label": _deadline_label(item.deadline_utc),
        "fit_reason": item.fit_reason or "",
    }


def send_weekly_digests(
    session: Session,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Send Friday digests to all active subscribers.

    Skips anyone emailed in the last 6 days unless force=True.
    """
    settings = get_settings()
    limit = max(1, min(settings.alerts_digest_limit, 20))
    now = utcnow()
    cooldown = now - timedelta(days=6)

    stats: Dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "configured": resend_configured(),
        "examined": 0,
        "sent": 0,
        "skipped_cooldown": 0,
        "skipped_empty": 0,
        "skipped_no_profile": 0,
        "failed": 0,
        "errors": [],
    }

    if not dry_run and not resend_configured():
        stats["ok"] = False
        stats["errors"].append(
            "RESEND_API_KEY is not set on Railway — digests not sent."
        )
        return stats

    subs = list(
        session.exec(
            select(AlertSubscription).where(AlertSubscription.is_active == True)  # noqa: E712
        ).all()
    )

    for sub in subs:
        stats["examined"] += 1
        ensure_unsubscribe_token(sub)

        if not force and sub.last_sent_at and sub.last_sent_at > cooldown:
            stats["skipped_cooldown"] += 1
            continue

        profile: Optional[UserProfile] = None
        if sub.profile_id:
            profile = session.get(UserProfile, sub.profile_id)
        if profile is None:
            email = (sub.email or "").strip().lower()
            if email:
                profile = session.exec(
                    select(UserProfile).where(UserProfile.email == email)
                ).first()
        if profile is None:
            stats["skipped_no_profile"] += 1
            continue

        matches = digest_for_profile(session, profile, limit=limit)
        if not matches:
            stats["skipped_empty"] += 1
            continue

        token = ensure_unsubscribe_token(sub)
        subject, html, text = render_digest_email(
            listings=[_listing_payload(m) for m in matches],
            unsubscribe_url=unsubscribe_url_for(token),
            discord_url=discord_team_url(),
        )

        if dry_run:
            stats["sent"] += 1
            continue

        try:
            send_email(to=sub.email, subject=subject, html=html, text=text)
            sub.last_sent_at = now
            session.add(sub)
            session.commit()
            stats["sent"] += 1
        except EmailNotConfiguredError as exc:
            stats["ok"] = False
            stats["failed"] += 1
            stats["errors"].append(str(exc))
            return stats
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            stats["failed"] += 1
            stats["errors"].append(f"{sub.email}: {exc}")

    return stats


def deactivate_by_token(session: Session, token: str) -> bool:
    """Mark subscription inactive; also clear profile.alerts_enabled when linked."""
    token = (token or "").strip()
    if not token:
        return False
    sub = session.exec(
        select(AlertSubscription).where(AlertSubscription.unsubscribe_token == token)
    ).first()
    if not sub:
        return False
    sub.is_active = False
    session.add(sub)
    if sub.profile_id:
        profile = session.get(UserProfile, sub.profile_id)
        if profile:
            profile.alerts_enabled = False
            profile.updated_at = utcnow()
            session.add(profile)
    # Also deactivate any other active rows for the same email.
    email = (sub.email or "").strip().lower()
    if email:
        siblings = session.exec(
            select(AlertSubscription).where(AlertSubscription.email == email)
        ).all()
        for sibling in siblings:
            sibling.is_active = False
            session.add(sibling)
    session.commit()
    return True
