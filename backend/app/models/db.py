from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, JSON
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
    source: SourcePlatform = Field(default=SourcePlatform.other, index=True)
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
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AlertSubscription(SQLModel, table=True):
    __tablename__ = "alert_subscriptions"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True)
    profile_id: Optional[str] = Field(default=None, foreign_key="user_profiles.id", index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    last_sent_at: Optional[datetime] = None