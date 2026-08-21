"""Currency-aware prize parsing (INR / EUR / etc. → USD + display)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.devpost import parse_prize
from scrapers.prizes import parse_prize_money, prize_fields_from_raw


def test_innovik_style_inr_html():
    """Devpost often returns e.g. '₹ <span>200,000</span>' — not USD."""
    parsed = parse_prize_money("₹ <span>200,000</span>")
    assert parsed is not None
    assert parsed.currency == "INR"
    assert parsed.amount_original == 200_000
    assert parsed.amount_usd == 2_400  # 200000 * 0.012
    assert parsed.display == "₹200,000"


def test_devpost_parse_prize_tuple():
    raw, usd, display = parse_prize("₹ <span>200,000</span>")
    assert "200,000" in (raw or "")
    assert usd == 2_400
    assert display == "₹200,000"


def test_usd_and_k_suffix():
    assert parse_prize_money("$25,000").amount_usd == 25_000
    assert parse_prize_money("$50k").amount_usd == 50_000
    assert parse_prize_money("USD 5000").display == "$5,000"


def test_eur_gbp():
    eur = parse_prize_money("€50,000")
    assert eur.currency == "EUR"
    assert eur.amount_usd == 54_000
    gbp = parse_prize_money("£10k")
    assert gbp.currency == "GBP"
    assert gbp.amount_usd == 12_700


def test_indian_numbering_rs():
    parsed = parse_prize_money("Rs. 2,00,000")
    assert parsed.currency == "INR"
    assert parsed.amount_original == 200_000
    assert parsed.display == "₹200,000"


def test_non_cash():
    assert parse_prize_money("Knowledge") is None
    assert parse_prize_money("Kudos") is None
    assert prize_fields_from_raw(None) == (None, None)


def test_kaggle_dict_reward():
    parsed = parse_prize_money({"id": "USD", "quantity": 20000})
    assert parsed.amount_usd == 20_000
    assert parsed.display == "$20,000"
