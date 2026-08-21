"""Persist enriched listings by calling the backend ingest API (preferred)
or writing directly when DATABASE_URL is set and API is unavailable.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
from sqlalchemy import Column, JSON, create_engine, text
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import String, Boolean, DateTime, Integer


Base = declarative_base()


class ListingRow(Base):
    __tablename__ = "listings"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    title = Column(String, nullable=False)
    organizer = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True, index=True)
    source = Column(String, nullable=False)
    deadline_utc = Column(DateTime(timezone=True), nullable=True)
    domains = Column(JSON, nullable=False, default=list)
    skill_floor = Column(String, nullable=False)
    skill_floor_reasoning = Column(String, nullable=False, default="")
    students_only = Column(Boolean, default=False)
    country_restrictions = Column(JSON, nullable=False, default=list)
    team_size_max = Column(Integer, nullable=True)
    requires_travel = Column(Boolean, default=False)
    prize_pool_usd = Column(Integer, nullable=True)
    has_starter_code = Column(Boolean, default=False)
    confidence = Column(String, default="medium")
    content_hash = Column(String, nullable=True, index=True)
    raw_snippet = Column(String, nullable=True)
    team_channel_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def enriched_to_payload(enriched, *, source: str, content_hash: str, raw_snippet: str) -> Dict[str, Any]:
    return {
        "title": enriched.title,
        "organizer": enriched.organizer,
        "url": enriched.url,
        "source": source,
        "deadline_utc": enriched.deadline_utc.isoformat() if enriched.deadline_utc else None,
        "domains": [d.value if hasattr(d, "value") else str(d) for d in (enriched.domain or [])],
        "skill_floor": enriched.skill_floor.value,
        "skill_floor_reasoning": enriched.skill_floor_reasoning,
        "students_only": enriched.eligibility.students_only,
        "country_restrictions": enriched.eligibility.country_restrictions or [],
        "team_size_max": enriched.eligibility.team_size_max,
        "requires_travel": enriched.eligibility.requires_travel,
        "prize_pool_usd": enriched.prize_pool_usd,
        "has_starter_code": enriched.has_starter_code,
        "confidence": enriched.confidence.value,
        "content_hash": content_hash,
        "raw_snippet": raw_snippet[:4000],
        "team_channel_url": getattr(enriched, "team_channel_url", None),
    }


def upsert_listing(
    *,
    enriched,
    source: str,
    content_hash: str,
    raw_snippet: str,
) -> str:
    payload = enriched_to_payload(
        enriched, source=source, content_hash=content_hash, raw_snippet=raw_snippet
    )

    api_url = os.getenv("BACKEND_API_URL", "").rstrip("/")
    ingest_token = os.getenv("INGEST_TOKEN", "")
    if api_url:
        headers = {"Content-Type": "application/json"}
        if ingest_token:
            headers["X-Ingest-Token"] = ingest_token
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{api_url}/api/internal/ingest", json=payload, headers=headers)
            if response.status_code == 401:
                raise RuntimeError(
                    "Railway rejected INGEST_TOKEN (401). "
                    "Modal secret INGEST_TOKEN must exactly match Railway Variables → INGEST_TOKEN."
                )
            response.raise_for_status()
            return response.json().get("status", "ok")

    return _upsert_direct(payload)


def _upsert_direct(payload: Dict[str, Any]) -> str:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./findhackathons.db")
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    deadline = None
    if payload.get("deadline_utc"):
        deadline = datetime.fromisoformat(payload["deadline_utc"].replace("Z", "+00:00"))

    with Session(engine) as session:
        existing = session.query(ListingRow).filter(ListingRow.url == payload["url"]).first()
        if existing and existing.content_hash == payload["content_hash"]:
            existing.last_seen_at = now
            existing.is_active = True
            session.commit()
            return "unchanged"

        fields = dict(
            title=payload["title"],
            organizer=payload["organizer"],
            source=payload["source"],
            deadline_utc=deadline,
            domains=payload["domains"],
            skill_floor=payload["skill_floor"],
            skill_floor_reasoning=payload["skill_floor_reasoning"],
            students_only=payload["students_only"],
            country_restrictions=payload["country_restrictions"],
            team_size_max=payload["team_size_max"],
            requires_travel=payload["requires_travel"],
            prize_pool_usd=payload["prize_pool_usd"],
            has_starter_code=payload["has_starter_code"],
            confidence=payload["confidence"],
            content_hash=payload["content_hash"],
            raw_snippet=payload["raw_snippet"],
            team_channel_url=payload.get("team_channel_url"),
            is_active=True,
            updated_at=now,
            last_seen_at=now,
        )

        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            session.commit()
            return "updated"

        row = ListingRow(id=str(uuid4()), url=payload["url"], created_at=now, **fields)
        session.add(row)
        session.commit()
        return "created"


def deactivate_stale(days: int = 2) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return 0
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE listings SET is_active = false, updated_at = :now "
                "WHERE is_active = true AND last_seen_at < :cutoff"
            ),
            {"now": datetime.now(timezone.utc), "cutoff": cutoff_dt},
        )
        return result.rowcount or 0