from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

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
                title="Beginner Python Sprint",
                organizer="Campus Hack",
                url="https://example.com/beginner-python",
                source=SourcePlatform.other,
                deadline_utc=datetime.now(timezone.utc) + timedelta(days=30),
                domains=["web-dev", "tabular"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="Starter notebook included.",
                students_only=True,
                country_restrictions=["IN"],
                team_size_max=4,
                requires_travel=False,
                prize_pool_usd=1000,
                has_starter_code=True,
                confidence=ConfidenceLevel.high,
            )
        )
        session.add(
            Listing(
                title="Advanced CV Challenge",
                organizer="Kaggle",
                url="https://example.com/advanced-cv",
                source=SourcePlatform.kaggle,
                deadline_utc=datetime.now(timezone.utc) + timedelta(days=40),
                domains=["cv"],
                skill_floor=SkillLevel.advanced,
                skill_floor_reasoning="No starter code.",
                students_only=False,
                country_restrictions=[],
                prize_pool_usd=25000,
                has_starter_code=False,
                confidence=ConfidenceLevel.high,
            )
        )
        session.add(
            Listing(
                title="Kaggle Knowledge Playground",
                organizer="Kaggle",
                url="https://example.com/kaggle-knowledge",
                source=SourcePlatform.kaggle,
                deadline_utc=datetime.now(timezone.utc) + timedelta(days=50),
                domains=["tabular"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="Playground with notebooks.",
                students_only=False,
                country_restrictions=[],
                prize_pool_usd=None,
                has_starter_code=True,
                confidence=ConfidenceLevel.high,
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    return client


def test_health():
    client = _client_with_db()
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "listings_count" in body
    assert "version" in body


def test_match_beginner_india():
    client = _client_with_db()
    response = client.post(
        "/api/match",
        json={
            "skill_level": "beginner",
            "domains": ["web-dev"],
            "country": "IN",
            "students_only_ok": True,
            "prefer_starter_code": True,
            "min_deadline_days": 7,
            "limit": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_candidates"] >= 1
    assert body["matches"][0]["title"] == "Beginner Python Sprint"
    assert "starter" in body["matches"][0]["fit_reason"].lower() or "beginner" in body["matches"][0]["fit_reason"].lower()


def test_listings_default_includes_no_prize():
    client = _client_with_db()
    response = client.get("/api/listings", params={"limit": 20})
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Beginner Python Sprint" in titles
    assert "Advanced CV Challenge" in titles
    assert "Kaggle Knowledge Playground" in titles


def test_listings_prize_only_filter():
    client = _client_with_db()
    response = client.get("/api/listings", params={"limit": 20, "has_prize": "true"})
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Beginner Python Sprint" in titles
    assert "Advanced CV Challenge" in titles
    assert "Kaggle Knowledge Playground" not in titles


def test_listings_include_no_prize():
    client = _client_with_db()
    response = client.get("/api/listings", params={"limit": 20, "has_prize": "false"})
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Kaggle Knowledge Playground" in titles
    assert "Beginner Python Sprint" in titles


def test_profile_and_alerts():
    client = _client_with_db()
    profile_resp = client.post(
        "/api/profiles",
        json={
            "email": "priya@example.com",
            "display_name": "Priya",
            "skill_level": "beginner",
            "domains": ["nlp", "tabular"],
            "country": "IN",
            "alerts_enabled": True,
        },
    )
    assert profile_resp.status_code == 200
    profile_id = profile_resp.json()["id"]

    alert_resp = client.post(
        "/api/alerts/subscribe",
        json={
            "email": "priya@example.com",
            "profile_id": profile_id,
            "skill_level": "beginner",
            "domains": ["nlp"],
            "country": "IN",
        },
    )
    assert alert_resp.status_code == 200
    assert alert_resp.json()["ok"] is True