"""Seed demo listings for local development and empty databases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.db import Listing
from app.models.enums import ConfidenceLevel, SkillLevel, SourcePlatform


def _deadline(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


# Relative day offsets keep demo data evergreen across restarts.
# URLs use example.com so empty local DBs never ship broken host links.
SEED_SPECS: list[dict] = [
    {
        "title": "CampusCode India: Beginner Web Sprint",
        "organizer": "Devfolio Campus",
        "url": "https://example.com/hackathons/campuscode-india-beginner",
        "source": SourcePlatform.other,
        "deadline_days": 28,
        "domains": ["web-dev"],
        "skill_floor": SkillLevel.beginner,
        "skill_floor_reasoning": "Student-only event with starter React templates and a 36-hour format.",
        "students_only": True,
        "country_restrictions": ["IN"],
        "team_size_max": 4,
        "requires_travel": False,
        "prize_pool_usd": 2500,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Build a portfolio-ready web app with provided starter kits.",
        "team_channel_url": "https://discord.gg/devfolio",
    },
    {
        "title": "Unstop Freshers ML Challenge",
        "organizer": "Unstop",
        "url": "https://example.com/hackathons/freshers-ml-challenge",
        "source": SourcePlatform.other,
        "deadline_days": 35,
        "domains": ["tabular", "nlp"],
        "skill_floor": SkillLevel.beginner,
        "skill_floor_reasoning": "Includes a starter notebook and a small tabular dataset under 1GB.",
        "students_only": True,
        "country_restrictions": ["IN"],
        "team_size_max": 3,
        "requires_travel": False,
        "prize_pool_usd": 1500,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Classify customer tickets with a starter notebook.",
        "team_channel_url": "https://example.com/hackathons/freshers-ml-challenge",
    },
    {
        "title": "Kaggle Playground: Tabular Forecasting",
        "organizer": "Kaggle",
        "url": "https://example.com/competitions/playground-tabular-forecasting",
        "source": SourcePlatform.kaggle,
        "deadline_days": 45,
        "domains": ["tabular"],
        "skill_floor": SkillLevel.beginner,
        "skill_floor_reasoning": "Playground series with public notebooks and standard tabular metrics.",
        "students_only": False,
        "country_restrictions": [],
        "team_size_max": None,
        "requires_travel": False,
        "prize_pool_usd": 0,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Forecast weekly demand using classic ML baselines.",
    },
    {
        "title": "Devpost AI for Good Weekend",
        "organizer": "Devpost",
        "url": "https://example.com/hackathons/ai-for-good-weekend",
        "source": SourcePlatform.other,
        "deadline_days": 21,
        "domains": ["nlp", "web-dev"],
        "skill_floor": SkillLevel.intermediate,
        "skill_floor_reasoning": "Weekend build with optional starter repos; expects working demos.",
        "students_only": False,
        "country_restrictions": [],
        "team_size_max": 5,
        "requires_travel": False,
        "prize_pool_usd": 10000,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.medium,
        "raw_snippet": "Ship an NLP-powered civic tool in 48 hours.",
        "team_channel_url": "https://example.com/hackathons/ai-for-good-weekend",
    },
    {
        "title": "Web3 Campus Buildathon — Mumbai",
        "organizer": "Devfolio",
        "url": "https://example.com/hackathons/web3-campus-mumbai",
        "source": SourcePlatform.other,
        "deadline_days": 40,
        "domains": ["web3", "web-dev"],
        "skill_floor": SkillLevel.intermediate,
        "skill_floor_reasoning": "Requires Solidity basics; starter dapp template provided.",
        "students_only": True,
        "country_restrictions": ["IN"],
        "team_size_max": 4,
        "requires_travel": True,
        "prize_pool_usd": 8000,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.medium,
        "raw_snippet": "In-person Mumbai hackathon with on-chain track.",
    },
    {
        "title": "Computer Vision Defect Detection Sprint",
        "organizer": "Kaggle",
        "url": "https://example.com/competitions/cv-defect-detection",
        "source": SourcePlatform.kaggle,
        "deadline_days": 60,
        "domains": ["cv"],
        "skill_floor": SkillLevel.advanced,
        "skill_floor_reasoning": "No starter code; expects custom architectures and GPU training.",
        "students_only": False,
        "country_restrictions": [],
        "team_size_max": None,
        "requires_travel": False,
        "prize_pool_usd": 25000,
        "has_starter_code": False,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Detect manufacturing defects in high-res imagery.",
    },
    {
        "title": "Unstop Mobile App Ideathon",
        "organizer": "Unstop",
        "url": "https://example.com/hackathons/mobile-app-ideathon",
        "source": SourcePlatform.other,
        "deadline_days": 18,
        "domains": ["mobile"],
        "skill_floor": SkillLevel.beginner,
        "skill_floor_reasoning": "Concept + prototype track aimed at student teams with Flutter starter kit.",
        "students_only": True,
        "country_restrictions": ["IN"],
        "team_size_max": 4,
        "requires_travel": False,
        "prize_pool_usd": 1200,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.medium,
        "raw_snippet": "Prototype a campus utility app for Android/iOS.",
    },
    {
        "title": "LLM Alignment Research Challenge",
        "organizer": "Devpost Labs",
        "url": "https://example.com/hackathons/llm-alignment-research",
        "source": SourcePlatform.other,
        "deadline_days": 50,
        "domains": ["nlp"],
        "skill_floor": SkillLevel.advanced,
        "skill_floor_reasoning": "Research-oriented; no starter notebook and novel eval design expected.",
        "students_only": False,
        "country_restrictions": [],
        "team_size_max": 3,
        "requires_travel": False,
        "prize_pool_usd": 15000,
        "has_starter_code": False,
        "confidence": ConfidenceLevel.medium,
        "raw_snippet": "Propose and evaluate alignment techniques for open models.",
    },
    {
        "title": "Game Jam India Online",
        "organizer": "Devfolio",
        "url": "https://example.com/hackathons/game-jam-india-online",
        "source": SourcePlatform.other,
        "deadline_days": 25,
        "domains": ["game-dev"],
        "skill_floor": SkillLevel.beginner,
        "skill_floor_reasoning": "48-hour jam with Godot starter project and mentor hours.",
        "students_only": False,
        "country_restrictions": ["IN"],
        "team_size_max": 5,
        "requires_travel": False,
        "prize_pool_usd": 3000,
        "has_starter_code": True,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Ship a tiny game around a surprise theme.",
    },
    {
        "title": "Quant Finance Fraud Detection Hack",
        "organizer": "Unstop x FinTech Collective",
        "url": "https://example.com/hackathons/quant-fraud-detection",
        "source": SourcePlatform.other,
        "deadline_days": 32,
        "domains": ["tabular", "other"],
        "skill_floor": SkillLevel.advanced,
        "skill_floor_reasoning": "Domain-specific fraud signals and no beginner templates.",
        "students_only": False,
        "country_restrictions": ["IN"],
        "team_size_max": 3,
        "requires_travel": False,
        "prize_pool_usd": 12000,
        "has_starter_code": False,
        "confidence": ConfidenceLevel.high,
        "raw_snippet": "Build fraud models on anonymized transaction streams.",
    },
]


def _listing_from_spec(spec: dict) -> Listing:
    data = {k: v for k, v in spec.items() if k != "deadline_days"}
    data["deadline_utc"] = _deadline(spec["deadline_days"])
    return Listing(**data)


def seed_if_empty(session: Session) -> int:
    existing = session.exec(select(Listing).limit(1)).first()
    if existing:
        return 0

    for spec in SEED_SPECS:
        session.add(_listing_from_spec(spec))
    session.commit()
    return len(SEED_SPECS)