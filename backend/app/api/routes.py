from datetime import datetime, timezone
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.core.database import engine, get_session
from app.models.db import AlertSubscription, Listing, UserProfile, utcnow
from app.models.enums import (
    ConfidenceLevel,
    DomainCategory,
    SkillLevel,
    SourcePlatform,
    TeamRole,
)
from app.models.schemas import (
    AlertSubscribe,
    AlertSubscribeResponse,
    DemandDashboard,
    IngestListing,
    IngestResponse,
    ListingInterestCreate,
    ListingInterestResponse,
    ListingRead,
    ManualListingSubmit,
    ManualListingSubmitResponse,
    MatchRequest,
    MatchResponse,
    ProfileCreate,
    ProfileRead,
    SourceCount,
    SourcesResponse,
)
from app.services.matching import discord_team_url, listing_to_read, match_hackathons
from app.services.teammates import (
    build_demand_dashboard,
    interest_counts_by_listing,
    public_interest_count,
    upsert_interest,
)

router = APIRouter()

# Default feed: Devpost + Kaggle + Devfolio + other hosts people submit.
# Unstop is opt-in only. Legacy `manual` rows stay visible until remapped.
DEFAULT_FEED_SOURCES: List[SourcePlatform] = [
    SourcePlatform.kaggle,
    SourcePlatform.devpost,
    SourcePlatform.devfolio,
    SourcePlatform.other,
    SourcePlatform.manual,
]

SOURCE_LABELS = {
    SourcePlatform.kaggle: "Kaggle",
    SourcePlatform.devpost: "Devpost",
    SourcePlatform.devfolio: "Devfolio",
    SourcePlatform.unstop: "Unstop",
    SourcePlatform.manual: "Added by people",
    SourcePlatform.other: "Other sites",
}

# Sidebar shows platforms — not a separate "Added by people" bucket.
SIDEBAR_SOURCES: List[SourcePlatform] = [
    SourcePlatform.kaggle,
    SourcePlatform.devpost,
    SourcePlatform.devfolio,
    SourcePlatform.unstop,
    SourcePlatform.other,
]


def _infer_source_from_url(url: str) -> SourcePlatform:
    """Map a competition URL to its host platform for sidebar grouping."""
    low = (url or "").lower()
    if "kaggle.com" in low:
        return SourcePlatform.kaggle
    if "devpost.com" in low:
        return SourcePlatform.devpost
    if "devfolio.co" in low or "devfolio.com" in low:
        return SourcePlatform.devfolio
    if "unstop.com" in low:
        return SourcePlatform.unstop
    return SourcePlatform.other


def _parse_sources(raw: Optional[str]) -> Optional[List[SourcePlatform]]:
    if not raw or not raw.strip():
        return None
    out: List[SourcePlatform] = []
    seen: Set[str] = set()
    for part in raw.split(","):
        key = part.strip().lower()
        if not key or key in seen:
            continue
        try:
            platform = SourcePlatform(key)
        except ValueError:
            continue
        seen.add(key)
        out.append(platform)
    return out or None


def _require_ingest_token(x_ingest_token: Optional[str]) -> None:
    settings = get_settings()
    if settings.ingest_token and x_ingest_token != settings.ingest_token:
        raise HTTPException(status_code=401, detail="Invalid ingest token")


def _role_values(roles: List[TeamRole]) -> List[str]:
    return [r.value for r in roles]


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
        looking_for_team=bool(profile.looking_for_team),
        team_needs=[
            TeamRole(r)
            for r in (profile.team_needs or [])
            if r in {role.value for role in TeamRole}
        ],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _listing_read(session: Session, listing: Listing, **kwargs) -> ListingRead:
    counts = interest_counts_by_listing(session, [listing.id])
    raw = counts.get(listing.id, 0)
    return listing_to_read(
        listing,
        teammate_interest_count=public_interest_count(raw),
        **kwargs,
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
    sources: Optional[str] = Query(
        default=None,
        description=(
            "Comma-separated platforms, e.g. kaggle,devpost,devfolio,manual. "
            "Default excludes Unstop unless include_unstop=true."
        ),
    ),
    include_unstop: bool = Query(
        default=False,
        description="When no sources= is set, also include Unstop listings.",
    ),
    country: Optional[str] = None,
    has_starter_code: Optional[bool] = None,
    has_prize: Optional[bool] = Query(
        default=True,
        description="Default true: only cash-prize listings. "
        "Pass false to include Knowledge / no-prize competitions as well.",
    ),
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

    # Source filter: single `source` wins; else `sources`; else default feed.
    if source:
        allowed = [source]
    else:
        allowed = _parse_sources(sources)
        if allowed is None:
            allowed = list(DEFAULT_FEED_SOURCES)
            if include_unstop:
                allowed.append(SourcePlatform.unstop)
    statement = statement.where(col(Listing.source).in_([s.value for s in allowed]))

    if has_starter_code is not None:
        statement = statement.where(Listing.has_starter_code == has_starter_code)
    if has_prize is not False:
        statement = statement.where(
            Listing.prize_pool_usd != None,  # noqa: E711
            Listing.prize_pool_usd > 0,
        )

    listings = list(session.exec(statement.limit(limit * 5)).all())
    listings.sort(
        key=lambda item: (
            -(item.prize_pool_usd or 0),
            item.deadline_utc or datetime.max.replace(tzinfo=timezone.utc),
        )
    )

    counts = interest_counts_by_listing(session, [item.id for item in listings])
    results: List[ListingRead] = []
    for listing in listings:
        if domain and domain.value not in (listing.domains or []):
            continue
        if country:
            restrictions = listing.country_restrictions or []
            if restrictions and country.upper() not in {c.upper() for c in restrictions}:
                continue
        results.append(
            listing_to_read(
                listing,
                teammate_interest_count=public_interest_count(counts.get(listing.id, 0)),
            )
        )
        if len(results) >= limit:
            break
    return results


@router.get("/sources", response_model=SourcesResponse)
def list_sources(
    active_only: bool = True,
    session: Session = Depends(get_session),
) -> SourcesResponse:
    """Active listing counts by source — powers the directory sidebar."""
    statement = select(Listing)
    if active_only:
        statement = statement.where(Listing.is_active == True)  # noqa: E712
        now = datetime.now(timezone.utc)
        statement = statement.where(
            (Listing.deadline_utc == None) | (col(Listing.deadline_utc) >= now)  # noqa: E711
        )
    listings = list(session.exec(statement).all())
    tallies: dict[str, int] = {}
    for item in listings:
        key = item.source.value if hasattr(item.source, "value") else str(item.source)
        # Fold legacy source=manual into "other" for the sidebar.
        if key == SourcePlatform.manual.value:
            key = SourcePlatform.other.value
        tallies[key] = tallies.get(key, 0) + 1

    default_set = {s.value for s in DEFAULT_FEED_SOURCES}
    rows: List[SourceCount] = []
    for platform in SIDEBAR_SOURCES:
        key = platform.value
        rows.append(
            SourceCount(
                source=platform,
                label=SOURCE_LABELS.get(platform, key.title()),
                count=tallies.get(key, 0),
                in_default_feed=key in default_set,
            )
        )
    return SourcesResponse(sources=rows, default_sources=list(DEFAULT_FEED_SOURCES))


@router.post("/listings/submit", response_model=ManualListingSubmitResponse)
def submit_listing(
    payload: ManualListingSubmit,
    session: Session = Depends(get_session),
) -> ManualListingSubmitResponse:
    """Public manual add/correct a competition.

    Source is inferred from the URL host (kaggle/devpost/…) so the listing
    appears under that platform in the sidebar. community_submitted marks
    that a person added it.
    """
    url = payload.url.strip()
    source = _infer_source_from_url(url)
    existing = session.exec(select(Listing).where(Listing.url == url)).first()
    now = utcnow()
    domains = [d.value for d in payload.domains] or ["other"]
    organizer = (payload.organizer or "").strip() or "Community submission"
    snippet_bits = [
        f"Manual submission at {now.isoformat()}",
        f"Notes: {payload.notes}" if payload.notes else "",
        f"Submitter: {payload.submitter_email}" if payload.submitter_email else "",
    ]
    raw_snippet = " | ".join(bit for bit in snippet_bits if bit)

    try:
        if existing:
            existing.title = payload.title
            existing.organizer = organizer
            existing.source = source
            existing.deadline_utc = payload.deadline_utc
            existing.domains = domains
            existing.skill_floor = payload.skill_floor
            existing.skill_floor_reasoning = (
                existing.skill_floor_reasoning
                or "Manually submitted / corrected via the website."
            )
            existing.students_only = payload.students_only
            existing.team_size_max = payload.team_size_max
            existing.requires_travel = payload.requires_travel
            existing.prize_pool_usd = payload.prize_pool_usd
            existing.has_starter_code = payload.has_starter_code
            existing.confidence = ConfidenceLevel.medium
            existing.raw_snippet = raw_snippet
            existing.community_submitted = True
            existing.team_channel_url = existing.team_channel_url or discord_team_url()
            existing.is_active = True
            existing.updated_at = now
            existing.last_seen_at = now
            session.add(existing)
            session.commit()
            return ManualListingSubmitResponse(
                ok=True,
                message="Updated that competition — thanks for the correction.",
                id=existing.id,
                status="updated",
            )

        listing = Listing(
            title=payload.title,
            organizer=organizer,
            url=url,
            source=source,
            deadline_utc=payload.deadline_utc,
            domains=domains,
            skill_floor=payload.skill_floor,
            skill_floor_reasoning="Manually submitted via the website.",
            students_only=payload.students_only,
            country_restrictions=[],
            team_size_max=payload.team_size_max,
            requires_travel=payload.requires_travel,
            prize_pool_usd=payload.prize_pool_usd,
            has_starter_code=payload.has_starter_code,
            confidence=ConfidenceLevel.medium,
            raw_snippet=raw_snippet,
            community_submitted=True,
            team_channel_url=discord_team_url(),
            is_active=True,
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        return ManualListingSubmitResponse(
            ok=True,
            message="Added — it should show up in the feed shortly.",
            id=listing.id,
            status="created",
        )
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        detail = str(exc)
        # Common production failure before the VARCHAR migration: PG enum lacks 'manual'.
        if "sourceplatform" in detail.lower() or "invalid input value for enum" in detail.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Database needs a quick migration for manual submissions "
                    "(source enum). Redeploy/restart the API so schema patch runs, "
                    "then try again."
                ),
            ) from exc
        if "team_channel_url" in detail.lower() and "does not exist" in detail.lower():
            raise HTTPException(
                status_code=503,
                detail="Database is missing team_channel_url — restart the API to migrate, then retry.",
            ) from exc
        if "community_submitted" in detail.lower() and "does not exist" in detail.lower():
            raise HTTPException(
                status_code=503,
                detail="Database is missing community_submitted — restart the API to migrate, then retry.",
            ) from exc
        print(f"[submit] failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not save competition: {detail[:240]}",
        ) from exc


@router.get("/listings/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: str, session: Session = Depends(get_session)) -> ListingRead:
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_read(session, listing)


@router.post("/listings/{listing_id}/interest", response_model=ListingInterestResponse)
def express_listing_interest(
    listing_id: str,
    payload: ListingInterestCreate,
    session: Session = Depends(get_session),
) -> ListingInterestResponse:
    """Record email + competition interest, then send people to Discord."""
    listing = session.get(Listing, listing_id)
    if not listing or not listing.is_active:
        raise HTTPException(status_code=404, detail="Listing not found")

    email = str(payload.email).strip().lower()
    needs = _role_values(payload.team_needs)
    discord = discord_team_url()

    profile: Optional[UserProfile] = None
    if payload.profile_id:
        profile = session.get(UserProfile, payload.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile.email = email
        profile.looking_for_team = True
        profile.team_needs = needs or profile.team_needs or []
        profile.updated_at = utcnow()
        session.add(profile)
    else:
        profile = session.exec(select(UserProfile).where(UserProfile.email == email)).first()
        if profile:
            profile.looking_for_team = True
            if needs:
                profile.team_needs = needs
            profile.updated_at = utcnow()
            session.add(profile)
        else:
            profile = UserProfile(
                email=email,
                looking_for_team=True,
                team_needs=needs,
                alerts_enabled=False,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)

    session.commit()
    upsert_interest(
        session,
        listing=listing,
        email=email,
        profile_id=profile.id,
        team_needs=needs,
    )

    counts = interest_counts_by_listing(session, [listing.id])
    raw = counts.get(listing.id, 0)
    public = public_interest_count(raw)
    return ListingInterestResponse(
        ok=True,
        message=(
            f"Saved — you're looking for teammates on “{listing.title}”. "
            "Jump into Discord, introduce yourself, and mention the competition."
        ),
        listing_id=listing.id,
        listing_title=listing.title,
        interest_count=raw,
        count_is_public=public is not None,
        discord_url=discord,
    )


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
        looking_for_team=payload.looking_for_team,
        team_needs=_role_values(payload.team_needs),
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
        response = match_hackathons(session, request)
    else:
        response = match_hackathons(session, payload)

    # Attach ambient teammate counts to match results.
    counts = interest_counts_by_listing(session, [m.id for m in response.matches])
    enriched = []
    for item in response.matches:
        data = item.model_dump()
        data["teammate_interest_count"] = public_interest_count(counts.get(item.id, 0))
        enriched.append(ListingRead(**data))
    response.matches = enriched
    return response


@router.post("/internal/ingest", response_model=IngestResponse)
def ingest_listing(
    payload: IngestListing,
    session: Session = Depends(get_session),
    x_ingest_token: Optional[str] = Header(default=None),
) -> IngestResponse:
    _require_ingest_token(x_ingest_token)

    existing = session.exec(select(Listing).where(Listing.url == payload.url)).first()
    now = utcnow()
    if existing and payload.content_hash and existing.content_hash == payload.content_hash:
        existing.last_seen_at = now
        existing.is_active = True
        if payload.team_channel_url:
            existing.team_channel_url = str(payload.team_channel_url)
        session.add(existing)
        session.commit()
        return IngestResponse(status="unchanged", id=existing.id)

    domains = [d.value for d in payload.domains]
    channel = str(payload.team_channel_url) if payload.team_channel_url else None
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
        if channel is not None:
            existing.team_channel_url = channel
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
        team_channel_url=channel,
        is_active=True,
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return IngestResponse(status="created", id=listing.id)


@router.get("/internal/demand", response_model=DemandDashboard)
def teammate_demand_dashboard(
    session: Session = Depends(get_session),
    x_ingest_token: Optional[str] = Header(default=None),
) -> DemandDashboard:
    """Phase 0 gate metrics. Protected with the same token as ingest."""
    _require_ingest_token(x_ingest_token)
    return build_demand_dashboard(session)


@router.post("/alerts/subscribe", response_model=AlertSubscribeResponse)
def subscribe_alerts(
    payload: AlertSubscribe,
    session: Session = Depends(get_session),
) -> AlertSubscribeResponse:
    needs = _role_values(payload.team_needs)
    profile: Optional[UserProfile] = None
    if payload.profile_id:
        profile = session.get(UserProfile, payload.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile.email = str(payload.email)
        profile.alerts_enabled = True
        profile.looking_for_team = payload.looking_for_team or profile.looking_for_team
        if needs:
            profile.team_needs = needs
        profile.updated_at = utcnow()
    else:
        email = str(payload.email).strip().lower()
        profile = session.exec(select(UserProfile).where(UserProfile.email == email)).first()
        if profile:
            profile.alerts_enabled = True
            profile.looking_for_team = payload.looking_for_team or profile.looking_for_team
            if needs:
                profile.team_needs = needs
            if payload.free_text:
                profile.free_text = payload.free_text
            profile.skill_level = payload.skill_level
            profile.domains = [d.value for d in payload.domains]
            profile.country = payload.country.upper()
            profile.updated_at = utcnow()
        else:
            profile = UserProfile(
                email=email,
                free_text=payload.free_text,
                skill_level=payload.skill_level,
                domains=[d.value for d in payload.domains],
                country=payload.country.upper(),
                alerts_enabled=True,
                looking_for_team=payload.looking_for_team,
                team_needs=needs,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)

    existing = session.exec(
        select(AlertSubscription).where(AlertSubscription.email == str(payload.email).lower())
    ).first()
    if existing:
        existing.profile_id = profile.id
        existing.is_active = True
    else:
        session.add(
            AlertSubscription(
                email=str(payload.email).lower(),
                profile_id=profile.id,
                is_active=True,
            )
        )
    session.commit()

    message = "You're on the weekly alert list. We'll email matches as they open."
    if payload.looking_for_team:
        message += (
            " Looking for teammates? Join Discord, introduce yourself, "
            f"and name the competition: {discord_team_url()}"
        )

    return AlertSubscribeResponse(
        ok=True,
        message=message,
        profile_id=profile.id,
    )
