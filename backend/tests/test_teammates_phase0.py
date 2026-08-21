"""Teammate interest → Discord + manual competition submission."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.models.db import Listing
from app.models.enums import ConfidenceLevel, SkillLevel, SourcePlatform

DISCORD = (
    "https://discord.com/channels/1535536397463724062/1535536398093000708"
)


def _client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Listing(
                id="listing-team-1",
                title="Team Build Weekend",
                organizer="Devfolio",
                url="https://example.com/team-build",
                source=SourcePlatform.devfolio,
                deadline_utc=datetime.now(timezone.utc) + timedelta(days=20),
                domains=["web-dev"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="Starter kits.",
                prize_pool_usd=2000,
                has_starter_code=True,
                confidence=ConfidenceLevel.high,
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    get_settings.cache_clear()
    return TestClient(app), engine


def test_interest_returns_discord_link(monkeypatch):
    monkeypatch.setenv("DISCORD_TEAM_URL", DISCORD)
    get_settings.cache_clear()
    client, _ = _client_with_db()

    response = client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "user@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["listing_title"] == "Team Build Weekend"
    assert body["discord_url"] == DISCORD
    assert "discord" in body["message"].lower()

    listing = client.get("/api/listings/listing-team-1").json()
    assert listing["team_channel_url"] == DISCORD


def test_alerts_looking_for_team_mentions_discord(monkeypatch):
    monkeypatch.setenv("DISCORD_TEAM_URL", DISCORD)
    get_settings.cache_clear()
    client, _ = _client_with_db()

    sub = client.post(
        "/api/alerts/subscribe",
        json={
            "email": "priya@example.com",
            "skill_level": "beginner",
            "domains": ["web-dev"],
            "country": "IN",
            "looking_for_team": True,
        },
    )
    assert sub.status_code == 200
    assert "discord" in sub.json()["message"].lower()

    profile = client.get(f"/api/profiles/{sub.json()['profile_id']}").json()
    assert profile["looking_for_team"] is True


def test_duplicate_interest_is_idempotent(monkeypatch):
    get_settings.cache_clear()
    client, _ = _client_with_db()

    first = client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "Same@Example.com"},
    )
    second = client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "same@example.com"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["interest_count"] == 1
    assert second.json()["interest_count"] == 1


def test_manual_listing_submit_create_and_update():
    get_settings.cache_clear()
    client, _ = _client_with_db()

    created = client.post(
        "/api/listings/submit",
        json={
            "title": "Campus AI Sprint",
            "url": "https://www.kaggle.com/competitions/campus-ai-sprint",
            "organizer": "IIT Club",
            "prize_pool_usd": 1500,
            "skill_floor": "beginner",
            "domains": ["nlp", "web-dev"],
            "submitter_email": "host@example.com",
            "notes": "College Discord already live",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "created"
    listing_id = body["id"]

    feed = client.get("/api/listings", params={"has_prize": "true", "limit": 50})
    titles = {row["title"] for row in feed.json()}
    assert "Campus AI Sprint" in titles

    detail = client.get(f"/api/listings/{listing_id}").json()
    assert detail["source"] == "kaggle"
    assert detail["community_submitted"] is True
    assert detail["prize_pool_usd"] == 1500

    sources = client.get("/api/sources").json()
    labels = {row["source"]: row["label"] for row in sources["sources"]}
    assert "manual" not in labels
    assert "kaggle" in labels

    updated = client.post(
        "/api/listings/submit",
        json={
            "title": "Campus AI Sprint (corrected)",
            "url": "https://www.kaggle.com/competitions/campus-ai-sprint",
            "prize_pool_usd": 2000,
            "skill_floor": "intermediate",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "updated"
    assert updated.json()["id"] == listing_id

    detail2 = client.get(f"/api/listings/{listing_id}").json()
    assert detail2["title"] == "Campus AI Sprint (corrected)"
    assert detail2["prize_pool_usd"] == 2000
    assert detail2["source"] == "kaggle"
    assert detail2["community_submitted"] is True


def test_manual_listing_infers_devpost_and_other():
    get_settings.cache_clear()
    client, _ = _client_with_db()

    devpost = client.post(
        "/api/listings/submit",
        json={
            "title": "Devpost Weekend",
            "url": "https://devpost.com/software/example-hack",
            "prize_pool_usd": 500,
        },
    )
    assert devpost.status_code == 200
    detail = client.get(f"/api/listings/{devpost.json()['id']}").json()
    assert detail["source"] == "devpost"
    assert detail["community_submitted"] is True

    other = client.post(
        "/api/listings/submit",
        json={
            "title": "Weird Host Comp",
            "url": "https://example.com/weird-host-comp",
            "prize_pool_usd": 100,
        },
    )
    assert other.status_code == 200
    detail2 = client.get(f"/api/listings/{other.json()['id']}").json()
    assert detail2["source"] == "other"
    assert detail2["community_submitted"] is True


def test_manual_listing_rejects_bad_url():
    get_settings.cache_clear()
    client, _ = _client_with_db()
    response = client.post(
        "/api/listings/submit",
        json={"title": "No Link Comp", "url": "not-a-url"},
    )
    assert response.status_code == 422
