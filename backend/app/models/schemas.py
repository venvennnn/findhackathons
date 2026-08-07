from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ConfidenceLevel, DomainCategory, SkillLevel, SourcePlatform


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


class AlertSubscribeResponse(BaseModel):
    ok: bool
    message: str
    profile_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
    listings_count: int
    environment: str


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


class IngestResponse(BaseModel):
    status: str
    id: str