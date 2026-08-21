"""Broken demo URL cleanup."""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.db import Listing
from app.models.enums import ConfidenceLevel, SkillLevel, SourcePlatform
from app.services.cleanup import deactivate_broken_demo_listings


def test_deactivate_broken_demo_listings():
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
                title="Bad Devpost",
                organizer="Devpost",
                url="https://devpost.com/software/ai-for-good-weekend",
                source=SourcePlatform.devpost,
                deadline_utc=now + timedelta(days=10),
                domains=["nlp"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=1000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.add(
            Listing(
                title="Bad Devfolio path",
                organizer="Devfolio",
                url="https://devfolio.co/hackathons/web3-campus-mumbai",
                source=SourcePlatform.devfolio,
                deadline_utc=now + timedelta(days=10),
                domains=["web3"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=1000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.add(
            Listing(
                title="Good Devfolio",
                organizer="Devfolio",
                url="https://tum.devfolio.co",
                source=SourcePlatform.devfolio,
                deadline_utc=now + timedelta(days=10),
                domains=["web3"],
                skill_floor=SkillLevel.beginner,
                skill_floor_reasoning="t",
                prize_pool_usd=1000,
                confidence=ConfidenceLevel.high,
                is_active=True,
            )
        )
        session.commit()
        deactivated = deactivate_broken_demo_listings(session)
        assert len(deactivated) == 2
        active = {
            row.url: row.is_active
            for row in session.exec(select(Listing)).all()
        }
        assert active["https://devpost.com/software/ai-for-good-weekend"] is False
        assert active["https://devfolio.co/hackathons/web3-campus-mumbai"] is False
        assert active["https://tum.devfolio.co"] is True
