"""Phase 0 teammate finding: interest signals, ambient threshold, demand dashboard."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.models.db import Listing
from app.models.enums import ConfidenceLevel, SkillLevel, SourcePlatform


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
                team_channel_url="https://discord.gg/example",
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    # Keep ambient threshold predictable for tests.
    get_settings.cache_clear()
    return TestClient(app), engine


def test_interest_stays_private_below_threshold(monkeypatch):
    monkeypatch.setenv("TEAMMATE_INTEREST_THRESHOLD", "8")
    get_settings.cache_clear()
    client, _ = _client_with_db()

    for i in range(3):
        response = client.post(
            "/api/listings/listing-team-1/interest",
            json={"email": f"user{i}@example.com", "team_needs": ["frontend"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["interest_count"] == i + 1
        assert body["count_is_public"] is False

    listing = client.get("/api/listings/listing-team-1").json()
    assert listing["team_channel_url"] == "https://discord.gg/example"
    assert listing["teammate_interest_count"] is None


def test_ambient_count_appears_at_threshold(monkeypatch):
    monkeypatch.setenv("TEAMMATE_INTEREST_THRESHOLD", "3")
    get_settings.cache_clear()
    client, _ = _client_with_db()

    for i in range(3):
        response = client.post(
            "/api/listings/listing-team-1/interest",
            json={"email": f"builder{i}@example.com", "team_needs": ["ml"]},
        )
        assert response.status_code == 200

    listing = client.get("/api/listings/listing-team-1").json()
    assert listing["teammate_interest_count"] == 3


def test_alerts_looking_for_team_and_demand_dashboard(monkeypatch):
    monkeypatch.setenv("TEAMMATE_INTEREST_THRESHOLD", "2")
    monkeypatch.setenv("INGEST_TOKEN", "test-token")
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
            "team_needs": ["frontend", "design"],
        },
    )
    assert sub.status_code == 200
    assert "looking for teammates" in sub.json()["message"].lower()

    profile = client.get(f"/api/profiles/{sub.json()['profile_id']}").json()
    assert profile["looking_for_team"] is True
    assert "frontend" in profile["team_needs"]

    client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "a@example.com"},
    )
    client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "b@example.com"},
    )

    denied = client.get("/api/internal/demand")
    assert denied.status_code == 401

    demand = client.get(
        "/api/internal/demand",
        headers={"X-Ingest-Token": "test-token"},
    )
    assert demand.status_code == 200
    body = demand.json()
    assert body["threshold"] == 2
    assert body["profiles_looking_for_team"] >= 1
    assert body["listings_at_or_above_threshold"] >= 1
    assert body["listings"][0]["interest_count"] >= 2


def test_duplicate_interest_is_idempotent(monkeypatch):
    monkeypatch.setenv("TEAMMATE_INTEREST_THRESHOLD", "8")
    get_settings.cache_clear()
    client, _ = _client_with_db()

    first = client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "Same@Example.com", "team_needs": ["backend"]},
    )
    second = client.post(
        "/api/listings/listing-team-1/interest",
        json={"email": "same@example.com", "team_needs": ["backend", "ml"]},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["interest_count"] == 1
    assert second.json()["interest_count"] == 1
