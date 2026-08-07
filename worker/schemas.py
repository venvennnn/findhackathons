"""Shared enrichment schema for the Modal ingestion worker."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class DomainCategory(str, Enum):
    web_dev = "web-dev"
    mobile = "mobile"
    nlp = "nlp"
    cv = "cv"
    tabular = "tabular"
    web3 = "web3"
    hardware = "hardware"
    game_dev = "game-dev"
    other = "other"


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


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


class HackathonListing(BaseModel):
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