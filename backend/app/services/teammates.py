"""Phase 0 teammate demand helpers — counts only, no public identities."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from sqlmodel import Session, col, func, select

from app.core.config import get_settings
from app.models.db import Listing, ListingInterest, UserProfile
from app.models.schemas import DemandDashboard, DemandListingRow


def interest_counts_by_listing(
    session: Session,
    listing_ids: Sequence[str],
) -> Dict[str, int]:
    if not listing_ids:
        return {}
    rows = session.exec(
        select(ListingInterest.listing_id, func.count(ListingInterest.id))
        .where(col(ListingInterest.listing_id).in_(list(listing_ids)))
        .group_by(ListingInterest.listing_id)
    ).all()
    return {listing_id: int(count) for listing_id, count in rows}


def public_interest_count(raw_count: int) -> Optional[int]:
    """Only expose ambient counts once they clear the Phase 0 threshold."""
    threshold = get_settings().teammate_interest_threshold
    if raw_count >= threshold:
        return raw_count
    return None


def build_demand_dashboard(session: Session) -> DemandDashboard:
    settings = get_settings()
    threshold = settings.teammate_interest_threshold

    profiles = list(session.exec(select(UserProfile)).all())
    with_email = [p for p in profiles if p.email]
    looking = [p for p in with_email if p.looking_for_team]
    rate = (len(looking) / len(with_email)) if with_email else 0.0

    count_rows = session.exec(
        select(ListingInterest.listing_id, func.count(ListingInterest.id)).group_by(
            ListingInterest.listing_id
        )
    ).all()
    counts = {listing_id: int(count) for listing_id, count in count_rows}
    total_interests = sum(counts.values())

    listings = list(session.exec(select(Listing)).all())
    demand_rows: List[DemandListingRow] = []
    for listing in listings:
        count = counts.get(listing.id, 0)
        if count == 0 and not listing.is_active:
            continue
        demand_rows.append(
            DemandListingRow(
                listing_id=listing.id,
                title=listing.title,
                source=listing.source,
                deadline_utc=listing.deadline_utc,
                interest_count=count,
                team_channel_url=listing.team_channel_url,
                is_active=listing.is_active,
            )
        )
    demand_rows.sort(key=lambda row: (-row.interest_count, row.title.lower()))

    above = sum(1 for row in demand_rows if row.interest_count >= threshold)
    # Phase 0 gate: ≥15% looking_for_team among email profiles AND ≥1 listing with ≥threshold.
    gate_passed = rate >= 0.15 and above >= 1

    return DemandDashboard(
        threshold=threshold,
        profiles_looking_for_team=len(looking),
        profiles_total_with_email=len(with_email),
        looking_for_team_rate=round(rate, 4),
        listings_at_or_above_threshold=above,
        total_interests=total_interests,
        gate_passed=gate_passed,
        listings=demand_rows,
    )


def upsert_interest(
    session: Session,
    *,
    listing: Listing,
    email: str,
    profile_id: Optional[str],
    team_needs: Iterable[str],
) -> ListingInterest:
    email_norm = email.strip().lower()
    needs = list(team_needs)
    existing = session.exec(
        select(ListingInterest).where(
            ListingInterest.listing_id == listing.id,
            ListingInterest.email == email_norm,
        )
    ).first()
    if existing:
        existing.team_needs = needs
        if profile_id:
            existing.profile_id = profile_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = ListingInterest(
        listing_id=listing.id,
        email=email_norm,
        profile_id=profile_id,
        team_needs=needs,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
