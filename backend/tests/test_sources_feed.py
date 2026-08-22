"""Default feed excludes Unstop; /api/sources returns per-platform counts."""

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
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        rows = [
            ("Kaggle Prize", SourcePlatform.kaggle, 1000),
            ("Devpost Hack", SourcePlatform.devpost, 500),
            ("Devfolio Open", SourcePlatform.devfolio, 200),
            ("Unstop Near", SourcePlatform.unstop, 300),
            ("Manual Add", SourcePlatform.manual, 100),
        ]
        for title, source, prize in rows:
            session.add(
                Listing(
                    title=title,
                    organizer="Test",
                    url=f"https://example.com/{source.value}/{title.replace(' ', '-')}",
                    source=source,
                    deadline_utc=now + timedelta(days=14),
                    domains=["other"],
                    skill_floor=SkillLevel.beginner,
                    skill_floor_reasoning="test",
                    students_only=False,
                    country_restrictions=[],
                    prize_pool_usd=prize,
                    has_starter_code=False,
                    confidence=ConfidenceLevel.high,
                    is_active=True,
                )
            )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    get_settings.cache_clear()
    return TestClient(app)


def test_default_listings_are_kaggle_and_community():
    client = _client_with_db()
    response = client.get("/api/listings", params={"limit": 50, "has_prize": "true"})
    assert response.status_code == 200
    sources = {item["source"] for item in response.json()}
    assert "unstop" not in sources
    assert "devpost" not in sources
    assert "devfolio" not in sources
    assert "kaggle" in sources
    assert "manual" in sources


def test_include_unstop_flag():
    client = _client_with_db()
    response = client.get(
        "/api/listings",
        params={"limit": 50, "has_prize": "true", "include_unstop": "true"},
    )
    assert response.status_code == 200
    sources = {item["source"] for item in response.json()}
    # Explicit include still works for legacy rows, but default feed does not.
    assert "unstop" in sources


def test_sources_query_param():
    client = _client_with_db()
    response = client.get(
        "/api/listings",
        params={"limit": 50, "has_prize": "true", "sources": "unstop"},
    )
    assert response.status_code == 200
    sources = {item["source"] for item in response.json()}
    assert sources == {"unstop"}


def test_sources_endpoint_counts():
    client = _client_with_db()
    response = client.get("/api/sources")
    assert response.status_code == 200
    body = response.json()
    by_source = {row["source"]: row["count"] for row in body["sources"]}
    assert by_source.get("kaggle", 0) >= 1
    assert "kaggle" in body["default_sources"]
    assert "devpost" not in body["default_sources"]
    assert "devfolio" not in body["default_sources"]
    assert "unstop" not in body["default_sources"]


def test_max_deadline_days_default_hides_far_listings():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            Listing(
                title="Soon Comp",
                organizer="Test",
                url="https://example.com/soon",
                source=SourcePlatform.kaggle,
                deadline_utc=now + timedelta(days=30),
                domains=["other"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=1000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.add(
            Listing(
                title="Far Comp",
                organizer="Test",
                url="https://example.com/far",
                source=SourcePlatform.kaggle,
                deadline_utc=now + timedelta(days=180),
                domains=["other"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=2000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.add(
            Listing(
                title="Student Comp",
                organizer="Test",
                url="https://example.com/student",
                source=SourcePlatform.kaggle,
                deadline_utc=now + timedelta(days=20),
                domains=["other"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                students_only=True,
                prize_pool_usd=500,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    get_settings.cache_clear()
    client = TestClient(app)

    default = client.get("/api/listings", params={"limit": 50, "has_prize": "true"})
    titles = {row["title"] for row in default.json()}
    assert "Soon Comp" in titles
    assert "Student Comp" in titles
    assert "Far Comp" not in titles

    wide = client.get(
        "/api/listings",
        params={"limit": 50, "has_prize": "true", "max_deadline_days": 0},
    )
    wide_titles = {row["title"] for row in wide.json()}
    assert "Far Comp" in wide_titles

    students = client.get(
        "/api/listings",
        params={"limit": 50, "has_prize": "true", "students_only": "true"},
    )
    student_titles = {row["title"] for row in students.json()}
    assert student_titles == {"Student Comp"}