"""Unit tests for Kaggle prize parsing + URL normalization (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from enrichment import listing_from_structured
from scrapers.devpost import _normalize_devpost_url
from scrapers.kaggle import (
    competition_slug,
    competition_to_raw,
    competition_url,
    parse_prize_usd,
)


def test_parse_prize_usd_cash():
    assert parse_prize_usd("$25,000") == 25000
    assert parse_prize_usd("$1,048,576") == 1048576
    assert parse_prize_usd("USD 5000") == 5000
    assert parse_prize_usd("$50k") == 50000
    assert parse_prize_usd("10,000 Usd") == 10000
    assert parse_prize_usd({"id": "USD", "quantity": 20000}) == 20000


def test_parse_prize_usd_non_cash():
    assert parse_prize_usd("Knowledge") is None
    assert parse_prize_usd("Swag") is None
    assert parse_prize_usd("Kudos") is None
    assert parse_prize_usd("") is None
    assert parse_prize_usd(None) is None


def test_competition_url_from_full_ref():
    raw = {
        "ref": "https://www.kaggle.com/competitions/cuhk-x-competition-large-model-track",
        "title": "CUHK-X Competition Large Model Track",
        "url": "https://www.kaggle.com/competitions/cuhk-x-competition-large-model-track",
        "reward": "10,000 Usd",
        "deadline": "2026-09-15T15:55:00Z",
        "category": "Community",
        "description": "Using Powerful Model to answer questions",
    }
    assert competition_slug(raw["ref"]) == "cuhk-x-competition-large-model-track"
    assert (
        competition_url(raw)
        == "https://www.kaggle.com/competitions/cuhk-x-competition-large-model-track"
    )
    listing = competition_to_raw(raw, is_community=True)
    assert listing.url.endswith("/cuhk-x-competition-large-model-track")
    assert listing.structured["has_cash_prize"] is True
    assert listing.structured["prize_pool_usd"] == 10000


def test_competition_to_raw_marks_cash_prize():
    row = {
        "ref": "arc-prize-2025",
        "title": "ARC Prize 2025",
        "organizationName": "ARC Prize",
        "reward": "$1,000,000",
        "deadline": "2026-11-01T23:59:00Z",
        "category": "Featured",
        "description": "Abstract reasoning challenge",
        "hasScripts": True,
        "maxTeamSize": 5,
    }
    listing = competition_to_raw(row)
    assert listing.url.endswith("/arc-prize-2025")
    assert listing.structured is not None
    assert listing.structured["has_cash_prize"] is True
    assert listing.structured["prize_pool_usd"] == 1000000


def test_competition_to_raw_knowledge():
    row = {
        "ref": "playground-series-s5e3",
        "title": "Playground Series",
        "reward": "Knowledge",
        "category": "Playground",
        "hasScripts": True,
    }
    listing = competition_to_raw(row)
    assert listing.structured is not None
    assert listing.structured["has_cash_prize"] is False
    assert listing.structured["prize_pool_usd"] is None


def test_devpost_rejects_software_gallery_urls():
    assert _normalize_devpost_url("https://devpost.com/software/ai-for-good-weekend") is None
    assert (
        _normalize_devpost_url("https://suvidha-ai-virtual-hackathon.devpost.com/")
        == "https://suvidha-ai-virtual-hackathon.devpost.com/"
    )
    assert _normalize_devpost_url("//foo.devpost.com/") == "https://foo.devpost.com/"


def test_listing_from_structured_beginner_playground():
    structured = {
        "title": "Playground Tabular",
        "url": "https://www.kaggle.com/competitions/playground-x",
        "organizer": "Kaggle",
        "category": "Playground",
        "description": "Forecast demand with tabular data",
        "prize_pool_usd": None,
        "has_starter_code": True,
        "deadline_utc": "2026-12-01T00:00:00+00:00",
        "team_size_max": 3,
    }
    listing = listing_from_structured(structured)
    assert listing.skill_floor.value == "beginner"
    assert listing.prize_pool_usd is None
    assert listing.has_starter_code is True
    assert any(d.value == "tabular" for d in listing.domain)
