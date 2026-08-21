"""Weekly digest send + unsubscribe."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.models.db import AlertSubscription, Listing, UserProfile
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
        session.add(
            Listing(
                title="Beginner NLP Sprint",
                organizer="Devpost",
                url="https://example.com/nlp",
                source=SourcePlatform.devpost,
                deadline_utc=now + timedelta(days=20),
                domains=["nlp"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=2000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.add(
            Listing(
                title="Tabular Playground",
                organizer="Kaggle",
                url="https://example.com/tab",
                source=SourcePlatform.kaggle,
                deadline_utc=now + timedelta(days=14),
                domains=["tabular"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=5000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        profile = UserProfile(
            email="alert@example.com",
            skill_level=SkillLevel.beginner,
            domains=["nlp", "tabular"],
            country="IN",
            alerts_enabled=True,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
        session.add(
            AlertSubscription(
                email="alert@example.com",
                profile_id=profile.id,
                is_active=True,
                unsubscribe_token="tok-unsubscribe-test-001",
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    get_settings.cache_clear()
    return TestClient(app), engine


def test_unsubscribe_deactivates_subscription():
    client, engine = _client_with_db()
    resp = client.post(
        "/api/alerts/unsubscribe",
        json={"token": "tok-unsubscribe-test-001"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    with Session(engine) as session:
        sub = session.exec(
            select(AlertSubscription).where(
                AlertSubscription.unsubscribe_token == "tok-unsubscribe-test-001"
            )
        ).first()
        assert sub is not None
        assert sub.is_active is False
        profile = session.get(UserProfile, sub.profile_id)
        assert profile is not None
        assert profile.alerts_enabled is False


def test_unsubscribe_unknown_token_404():
    client, _engine = _client_with_db()
    resp = client.post("/api/alerts/unsubscribe", json={"token": "does-not-exist-xx"})
    assert resp.status_code == 404


def test_send_weekly_requires_token():
    client, _engine = _client_with_db()
    get_settings.cache_clear()
    # Empty ingest token in tests → _require_ingest_token allows through when unset.
    # Set a token via monkeypatch env for this assertion.
    with patch.dict("os.environ", {"INGEST_TOKEN": "secret-ingest"}):
        get_settings.cache_clear()
        resp = client.post("/api/internal/alerts/send-weekly")
        assert resp.status_code == 401
        ok = client.post(
            "/api/internal/alerts/send-weekly?dry_run=true",
            headers={"X-Ingest-Token": "secret-ingest"},
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["dry_run"] is True
        assert body["sent"] >= 1
    get_settings.cache_clear()


def test_send_weekly_calls_resend(monkeypatch):
    client, engine = _client_with_db()
    monkeypatch.setenv("INGEST_TOKEN", "secret-ingest")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("APP_BASE_URL", "https://example.com")
    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "email_123"}

    with patch("app.services.email.httpx.post", return_value=mock_response) as mocked:
        resp = client.post(
            "/api/internal/alerts/send-weekly?force=true",
            headers={"X-Ingest-Token": "secret-ingest"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] == 1
        assert body["failed"] == 0
        assert mocked.called
        args, kwargs = mocked.call_args
        assert args[0] == "https://api.resend.com/emails"
        assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
        assert "alert@example.com" in kwargs["json"]["to"]

    with Session(engine) as session:
        sub = session.exec(select(AlertSubscription)).first()
        assert sub is not None
        assert sub.last_sent_at is not None

    get_settings.cache_clear()
