"""Hybrid matching: deterministic SQL filters + optional LLM ranking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models.db import Listing
from app.models.enums import DomainCategory, SkillLevel
from app.models.schemas import ListingRead, MatchRequest, MatchResponse
from app.services.ranking import rank_listings_with_llm, rank_listings_heuristic

SKILL_ORDER = {
    SkillLevel.beginner: 0,
    SkillLevel.intermediate: 1,
    SkillLevel.advanced: 2,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def listing_to_read(
    listing: Listing,
    *,
    fit_reason: Optional[str] = None,
    is_expanded_match: bool = False,
    teammate_interest_count: Optional[int] = None,
) -> ListingRead:
    return ListingRead(
        id=listing.id,
        title=listing.title,
        organizer=listing.organizer,
        url=listing.url,
        source=listing.source,
        deadline_utc=listing.deadline_utc,
        domains=[DomainCategory(d) for d in (listing.domains or [])],
        skill_floor=listing.skill_floor,
        skill_floor_reasoning=listing.skill_floor_reasoning,
        students_only=listing.students_only,
        country_restrictions=list(listing.country_restrictions or []),
        team_size_max=listing.team_size_max,
        requires_travel=listing.requires_travel,
        prize_pool_usd=listing.prize_pool_usd,
        has_starter_code=listing.has_starter_code,
        confidence=listing.confidence,
        is_active=listing.is_active,
        fit_reason=fit_reason,
        is_expanded_match=is_expanded_match,
        team_channel_url=listing.team_channel_url,
        teammate_interest_count=teammate_interest_count,
    )


def _normalize_domains(domains: Optional[Sequence[DomainCategory | str]]) -> List[str]:
    if not domains:
        return []
    return [d.value if isinstance(d, DomainCategory) else str(d) for d in domains]


def filter_listings(
    session: Session,
    request: MatchRequest,
    *,
    broaden_domains: bool = False,
) -> List[Listing]:
    now = _utcnow()
    min_deadline = now + timedelta(days=request.min_deadline_days)
    skill = request.skill_level or SkillLevel.beginner
    max_skill_rank = SKILL_ORDER[skill]
    domains = [] if broaden_domains else _normalize_domains(request.domains)

    statement = select(Listing).where(
        Listing.is_active == True,  # noqa: E712
        (Listing.deadline_utc == None) | (col(Listing.deadline_utc) >= min_deadline),  # noqa: E711
    )
    listings = list(session.exec(statement).all())

    filtered: List[Listing] = []
    for listing in listings:
        if SKILL_ORDER.get(listing.skill_floor, 0) > max_skill_rank:
            continue

        restrictions = listing.country_restrictions or []
        country = (request.country or "").upper()
        if (
            restrictions
            and country
            and country not in {"GLOBAL", "ANY", "WORLD"}
            and country not in {c.upper() for c in restrictions}
        ):
            continue

        if listing.students_only and not request.students_only_ok:
            continue

        if listing.requires_travel and not request.can_travel:
            continue

        if (
            request.max_team_size is not None
            and listing.team_size_max is not None
            and listing.team_size_max > request.max_team_size
        ):
            continue

        if domains:
            listing_domains = set(listing.domains or [])
            if listing_domains.isdisjoint(set(domains)):
                continue

        filtered.append(listing)

    # Prefer cash-prize comps, then starter-code for beginners, then soonest deadline.
    def sort_key(item: Listing):
        prize_rank = 0 if (item.prize_pool_usd and item.prize_pool_usd > 0) else 1
        starter_rank = 0
        if request.prefer_starter_code and skill == SkillLevel.beginner:
            starter_rank = 0 if item.has_starter_code else 1
        return (prize_rank, starter_rank, -(item.prize_pool_usd or 0), item.deadline_utc or now)

    filtered.sort(key=sort_key)
    return filtered


def match_hackathons(session: Session, request: MatchRequest) -> MatchResponse:
    candidates = filter_listings(session, request, broaden_domains=False)
    broadened = False

    if len(candidates) < 3:
        broadened_candidates = filter_listings(session, request, broaden_domains=True)
        if len(broadened_candidates) > len(candidates):
            candidates = broadened_candidates
            broadened = True

    total = len(candidates)
    shortlist = candidates[:40]

    settings = get_settings()
    if settings.openai_api_key and shortlist:
        ranked = rank_listings_with_llm(shortlist, request)
    else:
        ranked = rank_listings_heuristic(shortlist, request)

    matches = [
        listing_to_read(
            item.listing,
            fit_reason=item.fit_reason,
            is_expanded_match=broadened and bool(request.domains),
        )
        for item in ranked[: request.limit]
    ]

    suggest_alerts = total < 3 or broadened
    message = None
    if total == 0:
        message = (
            "No active competitions match your filters right now. "
            "Join weekly alerts and we’ll email you when something opens."
        )
    elif broadened:
        message = (
            "Fewer than 3 exact domain matches — showing nearby competitions. "
            "Join alerts to catch niche openings early."
        )

    return MatchResponse(
        matches=matches,
        total_candidates=total,
        broadened=broadened,
        message=message,
        suggest_alerts=suggest_alerts,
    )