from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import (
    ConfidenceLevel,
    DomainCategory,
    SkillLevel,
    SourcePlatform,
    TeamRole,
)


class Eligibility(BaseModel):
    students_only: bool = Field(description="True if explicitly restricted to students.")
    country_restrictions: List[str] = Field(
        default_factory=list,
        description="ISO codes of allowed countries. Empty if global.",
    )
    team_size_max: Optional[int] = Field(default=None, description="Maximum team size allowed.")
    requires_travel: bool = Field(
        default=False, description="True if in-person attendance is mandatory."
    )


class HackathonListingEnrichment(BaseModel):
    """Instructor-ready schema for LLM enrichment of raw competition text."""

    title: str
    organizer: str
    url: str
    deadline_utc: Optional[datetime] = None
    domain: List[DomainCategory] = Field(default_factory=list)
    skill_floor: SkillLevel
    skill_floor_reasoning: str = Field(
        description="One sentence explaining why this skill level was assigned."
    )
    eligibility: Eligibility
    prize_pool_usd: Optional[int] = None
    has_starter_code: bool = Field(
        description="True if starter repo, notebook, or template is provided."
    )
    confidence: ConfidenceLevel = Field(
        description="'high', 'medium', or 'low'. Use low if guessing."
    )


class ListingRead(BaseModel):
    id: str
    title: str
    organizer: str
    url: str
    source: SourcePlatform
    deadline_utc: Optional[datetime] = None
    domains: List[DomainCategory]
    skill_floor: SkillLevel
    skill_floor_reasoning: str
    students_only: bool
    country_restrictions: List[str]
    team_size_max: Optional[int] = None
    requires_travel: bool
    prize_pool_usd: Optional[int] = None
    has_starter_code: bool
    confidence: ConfidenceLevel
    is_active: bool
    fit_reason: Optional[str] = None
    is_expanded_match: bool = False
    # Event-run team channel (Discord / Devpost forum). Safe outbound link.
    team_channel_url: Optional[str] = None
    # Ambient demand signal — only populated once count >= threshold. No names.
    teammate_interest_count: Optional[int] = None


class ProfileCreate(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    free_text: Optional[str] = Field(
        default=None,
        description="Natural language description of skills and interests.",
    )
    skill_level: SkillLevel = SkillLevel.beginner
    domains: List[DomainCategory] = Field(default_factory=list)
    country: str = "IN"
    students_only_ok: bool = True
    can_travel: bool = False
    max_team_size: Optional[int] = None
    prefer_starter_code: bool = True
    min_deadline_days: int = Field(default=7, ge=0, le=365)
    alerts_enabled: bool = False
    looking_for_team: bool = False
    team_needs: List[TeamRole] = Field(default_factory=list)


class ProfileRead(ProfileCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class MatchRequest(BaseModel):
    profile_id: Optional[str] = None
    free_text: Optional[str] = None
    skill_level: Optional[SkillLevel] = None
    domains: Optional[List[DomainCategory]] = None
    country: Optional[str] = "IN"
    students_only_ok: bool = True
    can_travel: bool = False
    max_team_size: Optional[int] = None
    prefer_starter_code: bool = True
    min_deadline_days: int = 7
    limit: int = Field(default=5, ge=1, le=20)


class MatchResponse(BaseModel):
    matches: List[ListingRead]
    total_candidates: int
    broadened: bool = False
    message: Optional[str] = None
    suggest_alerts: bool = False


class AlertSubscribe(BaseModel):
    email: EmailStr
    profile_id: Optional[str] = None
    skill_level: SkillLevel = SkillLevel.beginner
    domains: List[DomainCategory] = Field(default_factory=list)
    country: str = "IN"
    free_text: Optional[str] = None
    looking_for_team: bool = False
    team_needs: List[TeamRole] = Field(default_factory=list)


class AlertSubscribeResponse(BaseModel):
    ok: bool
    message: str
    profile_id: str


class ListingInterestCreate(BaseModel):
    email: EmailStr
    profile_id: Optional[str] = None
    team_needs: List[TeamRole] = Field(default_factory=list)


class ListingInterestResponse(BaseModel):
    ok: bool
    message: str
    listing_id: str
    listing_title: str
    interest_count: int
    # True when the ambient public count is now visible on the listing.
    count_is_public: bool
    discord_url: str


class ManualListingSubmit(BaseModel):
    """Public form to add a competition we don't scrape (or to correct one)."""

    title: str = Field(min_length=3, max_length=200)
    url: str = Field(min_length=8, max_length=500)
    organizer: Optional[str] = Field(default=None, max_length=200)
    deadline_utc: Optional[datetime] = None
    prize_pool_usd: Optional[int] = Field(default=None, ge=0, le=50_000_000)
    domains: List[DomainCategory] = Field(default_factory=list)
    skill_floor: SkillLevel = SkillLevel.intermediate
    has_starter_code: bool = False
    students_only: bool = False
    requires_travel: bool = False
    team_size_max: Optional[int] = Field(default=None, ge=1, le=50)
    notes: Optional[str] = Field(default=None, max_length=1000)
    submitter_email: Optional[EmailStr] = None

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return cleaned

    @field_validator("title")
    @classmethod
    def title_strip(cls, value: str) -> str:
        return value.strip()


class ManualListingSubmitResponse(BaseModel):
    ok: bool
    message: str
    id: str
    status: str  # created | updated


class DemandListingRow(BaseModel):
    listing_id: str
    title: str
    source: SourcePlatform
    deadline_utc: Optional[datetime] = None
    interest_count: int
    team_channel_url: Optional[str] = None
    is_active: bool


class DemandDashboard(BaseModel):
    """Internal Phase 0 metrics — gated by ingest/admin token."""

    threshold: int
    profiles_looking_for_team: int
    profiles_total_with_email: int
    looking_for_team_rate: float
    listings_at_or_above_threshold: int
    total_interests: int
    gate_passed: bool
    listings: List[DemandListingRow]


class HealthResponse(BaseModel):
    status: str
    version: str
    listings_count: int
    environment: str


class SourceCount(BaseModel):
    source: SourcePlatform
    label: str
    count: int
    in_default_feed: bool = False


class SourcesResponse(BaseModel):
    sources: List[SourceCount]
    default_sources: List[SourcePlatform]


class IngestListing(BaseModel):
    title: str
    organizer: str
    url: str
    source: SourcePlatform = SourcePlatform.other
    deadline_utc: Optional[datetime] = None
    domains: List[DomainCategory] = Field(default_factory=list)
    skill_floor: SkillLevel
    skill_floor_reasoning: str = ""
    students_only: bool = False
    country_restrictions: List[str] = Field(default_factory=list)
    team_size_max: Optional[int] = None
    requires_travel: bool = False
    prize_pool_usd: Optional[int] = None
    has_starter_code: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    content_hash: Optional[str] = None
    raw_snippet: Optional[str] = None
    team_channel_url: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    id: str
