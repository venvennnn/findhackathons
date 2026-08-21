from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, JSON, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.enums import ConfidenceLevel, SkillLevel, SourcePlatform


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Listing(SQLModel, table=True):
    __tablename__ = "listings"

    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(index=True)
    organizer: str
    url: str = Field(unique=True, index=True)
    # Store as VARCHAR — Postgres native ENUMs break when we add values like "manual".
    source: SourcePlatform = Field(
        default=SourcePlatform.other,
        sa_column=Column(String(32), nullable=False, index=True),
    )
    deadline_utc: Optional[datetime] = Field(default=None, index=True)
    domains: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    skill_floor: SkillLevel = Field(default=SkillLevel.beginner, index=True)
    skill_floor_reasoning: str = ""
    students_only: bool = False
    country_restrictions: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    team_size_max: Optional[int] = None
    requires_travel: bool = False
    prize_pool_usd: Optional[int] = None
    has_starter_code: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    content_hash: Optional[str] = Field(default=None, index=True)
    raw_snippet: Optional[str] = None
    # Outbound link to the event's own team-finding channel (Discord, Devpost, etc.)
    team_channel_url: Optional[str] = None
    # True when a person submitted/corrected this listing via the website.
    community_submitted: bool = False
    # Original prize label (e.g. "₹200,000") when not already USD.
    prize_text: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    display_name: Optional[str] = None
    free_text: Optional[str] = None
    skill_level: SkillLevel = SkillLevel.beginner
    domains: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    country: str = Field(default="IN", index=True)
    students_only_ok: bool = True
    can_travel: bool = False
    max_team_size: Optional[int] = None
    prefer_starter_code: bool = True
    min_deadline_days: int = 7
    alerts_enabled: bool = Field(default=False, index=True)
    # Phase 0 teammate signal — intent only, no public profile.
    looking_for_team: bool = Field(default=False, index=True)
    team_needs: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AlertSubscription(SQLModel, table=True):
    __tablename__ = "alert_subscriptions"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True)
    profile_id: Optional[str] = Field(default=None, foreign_key="user_profiles.id", index=True)
    is_active: bool = Field(default=True, index=True)
    # Opaque token for one-click unsubscribe links in digests.
    unsubscribe_token: str = Field(default_factory=new_id, index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)
    last_sent_at: Optional[datetime] = None


class ListingInterest(SQLModel, table=True):
    """Per-listing 'looking for teammates' signal (Phase 0). No public identity."""

    __tablename__ = "listing_interests"
    __table_args__ = (
        UniqueConstraint("email", "listing_id", name="uq_interest_email_listing"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    listing_id: str = Field(foreign_key="listings.id", index=True)
    email: str = Field(index=True)
    profile_id: Optional[str] = Field(default=None, foreign_key="user_profiles.id", index=True)
    team_needs: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
