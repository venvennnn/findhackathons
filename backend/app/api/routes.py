from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.core.database import engine, get_session
from app.models.db import AlertSubscription, Listing, UserProfile, utcnow
from app.models.enums import DomainCategory, SkillLevel, SourcePlatform
from app.models.schemas import (
    AlertSubscribe,
    AlertSubscribeResponse,
    HealthResponse,
    IngestListing,
    IngestResponse,
    ListingRead,
    MatchRequest,
    MatchResponse,
    ProfileCreate,
    ProfileRead,
)
from app.services.matching import listing_to_read, match_hackathons

router = APIRouter()


def _profile_to_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        id=profile.id,
        email=profile.email,
        display_name=profile.display_name,
        free_text=profile.free_text,
        skill_level=profile.skill_level,
        domains=[DomainCategory(d) for d in (profile.domains or [])],
        country=profile.country,
        students_only_ok=profile.students_only_ok,
        can_travel=profile.can_travel,
        max_team_size=profile.max_team_size,
        prefer_starter_code=profile.prefer_starter_code,
        min_deadline_days=profile.min_deadline_days,
        alerts_enabled=profile.alerts_enabled,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/health")
def health() -> dict:
    """Liveness endpoint used by Railway. Returns 200 if the process is up."""
    settings = get_settings()
    payload = {
        "status": "ok",
        "version": settings.app_version,
        "listings_count": 0,
        "environment": settings.environment,
        "database": "ok",
    }
    try:
        with Session(engine) as session:
            payload["listings_count"] = len(session.exec(select(Listing)).all())
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "degraded"
        payload["database"] = "error"
        payload["database_error"] = str(exc)
    return payload


@router.get("/listings", response_model=List[ListingRead])
def list_listings(
    skill_level: Optional[SkillLevel] = None,
    domain: Optional[DomainCategory] = None,
    source: Optional[SourcePlatform] = None,
    country: Optional[str] = None,
    has_starter_code: Optional[bool] = None,
    active_only: bool = True,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> List[ListingRead]:
    statement = select(Listing)
    if active_only:
        statement = statement.where(Listing.is_active == True)  # noqa: E712
        now = datetime.now(timezone.utc)
        statement = statement.where(
            (Listing.deadline_utc == None) | (col(Listing.deadline_utc) >= now)  # noqa: E711
        )
    if skill_level:
        statement = statement.where(Listing.skill_floor == skill_level)
    if source:
        statement = statement.where(Listing.source == source)
    if has_starter_code is not None:
        statement = statement.where(Listing.has_starter_code == has_starter_code)

    listings = list(session.exec(statement.order_by(Listing.deadline_utc).limit(limit * 3)).all())

    results: List[ListingRead] = []
    for listing in listings:
        if domain and domain.value not in (listing.domains or []):
            continue
        if country:
            restrictions = listing.country_restrictions or []
            if restrictions and country.upper() not in {c.upper() for c in restrictions}:
                continue
        results.append(listing_to_read(listing))
        if len(results) >= limit:
            break
    return results


@router.get("/listings/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: str, session: Session = Depends(get_session)) -> ListingRead:
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing_to_read(listing)


@router.post("/profiles", response_model=ProfileRead)
def create_profile(
    payload: ProfileCreate,
    session: Session = Depends(get_session),
) -> ProfileRead:
    profile = UserProfile(
        email=str(payload.email) if payload.email else None,
        display_name=payload.display_name,
        free_text=payload.free_text,
        skill_level=payload.skill_level,
        domains=[d.value for d in payload.domains],
        country=payload.country.upper(),
        students_only_ok=payload.students_only_ok,
        can_travel=payload.can_travel,
        max_team_size=payload.max_team_size,
        prefer_starter_code=payload.prefer_starter_code,
        min_deadline_days=payload.min_deadline_days,
        alerts_enabled=payload.alerts_enabled,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    if payload.alerts_enabled and payload.email:
        existing = session.exec(
            select(AlertSubscription).where(AlertSubscription.email == str(payload.email))
        ).first()
        if existing:
            existing.profile_id = profile.id
            existing.is_active = True
        else:
            session.add(
                AlertSubscription(email=str(payload.email), profile_id=profile.id, is_active=True)
            )
        session.commit()

    return _profile_to_read(profile)


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: str, session: Session = Depends(get_session)) -> ProfileRead:
    profile = session.get(UserProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_read(profile)


@router.post("/match", response_model=MatchResponse)
def match(payload: MatchRequest, session: Session = Depends(get_session)) -> MatchResponse:
    if payload.profile_id:
        profile = session.get(UserProfile, payload.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        request = MatchRequest(
            profile_id=profile.id,
            free_text=payload.free_text or profile.free_text,
            skill_level=payload.skill_level or profile.skill_level,
            domains=payload.domains
            or [DomainCategory(d) for d in (profile.domains or [])],
            country=payload.country or profile.country,
            students_only_ok=payload.students_only_ok
            if payload.students_only_ok is not None
            else profile.students_only_ok,
            can_travel=payload.can_travel if payload.can_travel is not None else profile.can_travel,
            max_team_size=payload.max_team_size
            if payload.max_team_size is not None
            else profile.max_team_size,
            prefer_starter_code=payload.prefer_starter_code
            if payload.prefer_starter_code is not None
            else profile.prefer_starter_code,
            min_deadline_days=payload.min_deadline_days
            if payload.min_deadline_days is not None
            else profile.min_deadline_days,
            limit=payload.limit,
        )
        return match_hackathons(session, request)

    return match_hackathons(session, payload)


@router.post("/internal/ingest", response_model=IngestResponse)
def ingest_listing(
    payload: IngestListing,
    session: Session = Depends(get_session),
    x_ingest_token: Optional[str] = Header(default=None),
) -> IngestResponse:
    settings = get_settings()
    if settings.ingest_token and x_ingest_token != settings.ingest_token:
        raise HTTPException(status_code=401, detail="Invalid ingest token")

    existing = session.exec(select(Listing).where(Listing.url == payload.url)).first()
    now = utcnow()
    if existing and payload.content_hash and existing.content_hash == payload.content_hash:
        existing.last_seen_at = now
        existing.is_active = True
        session.add(existing)
        session.commit()
        return IngestResponse(status="unchanged", id=existing.id)

    domains = [d.value for d in payload.domains]
    if existing:
        existing.title = payload.title
        existing.organizer = payload.organizer
        existing.source = payload.source
        existing.deadline_utc = payload.deadline_utc
        existing.domains = domains
        existing.skill_floor = payload.skill_floor
        existing.skill_floor_reasoning = payload.skill_floor_reasoning
        existing.students_only = payload.students_only
        existing.country_restrictions = payload.country_restrictions
        existing.team_size_max = payload.team_size_max
        existing.requires_travel = payload.requires_travel
        existing.prize_pool_usd = payload.prize_pool_usd
        existing.has_starter_code = payload.has_starter_code
        existing.confidence = payload.confidence
        existing.content_hash = payload.content_hash
        existing.raw_snippet = payload.raw_snippet
        existing.is_active = True
        existing.updated_at = now
        existing.last_seen_at = now
        session.add(existing)
        session.commit()
        return IngestResponse(status="updated", id=existing.id)

    listing = Listing(
        title=payload.title,
        organizer=payload.organizer,
        url=payload.url,
        source=payload.source,
        deadline_utc=payload.deadline_utc,
        domains=domains,
        skill_floor=payload.skill_floor,
        skill_floor_reasoning=payload.skill_floor_reasoning,
        students_only=payload.students_only,
        country_restrictions=payload.country_restrictions,
        team_size_max=payload.team_size_max,
        requires_travel=payload.requires_travel,
        prize_pool_usd=payload.prize_pool_usd,
        has_starter_code=payload.has_starter_code,
        confidence=payload.confidence,
        content_hash=payload.content_hash,
        raw_snippet=payload.raw_snippet,
        is_active=True,
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return IngestResponse(status="created", id=listing.id)


@router.post("/alerts/subscribe", response_model=AlertSubscribeResponse)
def subscribe_alerts(
    payload: AlertSubscribe,
    session: Session = Depends(get_session),
) -> AlertSubscribeResponse:
    profile: Optional[UserProfile] = None
    if payload.profile_id:
        profile = session.get(UserProfile, payload.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile.email = str(payload.email)
        profile.alerts_enabled = True
        profile.updated_at = utcnow()
    else:
        profile = UserProfile(
            email=str(payload.email),
            free_text=payload.free_text,
            skill_level=payload.skill_level,
            domains=[d.value for d in payload.domains],
            country=payload.country.upper(),
            alerts_enabled=True,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

    existing = session.exec(
        select(AlertSubscription).where(AlertSubscription.email == str(payload.email))
    ).first()
    if existing:
        existing.profile_id = profile.id
        existing.is_active = True
    else:
        session.add(
            AlertSubscription(email=str(payload.email), profile_id=profile.id, is_active=True)
        )
    session.commit()

    return AlertSubscribeResponse(
        ok=True,
        message="You're on the weekly alert list. We'll email matches as they open.",
        profile_id=profile.id,
    )