"""Currency-aware prize parsing.

We store USD (approx) for sorting/filters, and keep an original display string
so ₹ / € / £ prizes are not shown as bare dollar amounts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

# Rough FX → USD. Good enough for ranking; labels keep the original currency.
USD_PER_UNIT = {
    "USD": 1.0,
    "INR": 0.012,  # ~₹83 / $1
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.74,
    "AUD": 0.65,
    "SGD": 0.75,
    "JPY": 0.0067,
    "CHF": 1.12,
    "NZD": 0.60,
    "HKD": 0.13,
}

CURRENCY_SYMBOLS = {
    "₹": "INR",
    "rs.": "INR",
    "rs": "INR",
    "inr": "INR",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "$": "USD",
    "usd": "USD",
    "us$": "USD",
    "cad": "CAD",
    "c$": "CAD",
    "a$": "AUD",
    "aud": "AUD",
    "sgd": "SGD",
    "s$": "SGD",
    "¥": "JPY",
    "jpy": "JPY",
    "chf": "CHF",
    "nzd": "NZD",
    "hkd": "HKD",
    "hk$": "HKD",
}

REWARD_NON_CASH = re.compile(
    r"^(knowledge|swag|kudos|jobs?|internship|experience|prestige|n/?a|none|-)$",
    re.I,
)
AMOUNT_RE = re.compile(
    r"(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<suffix>[kKmMbB])?",
)


@dataclass(frozen=True)
class ParsedPrize:
    amount_original: int
    currency: str
    amount_usd: int
    display: str  # e.g. "₹200,000"


def _strip_html(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    for a, b in (
        ("&amp;", "&"),
        ("&nbsp;", " "),
        ("&#8377;", "₹"),
        ("&#39;", "'"),
        ("&quot;", '"'),
        ("&lt;", "<"),
        ("&gt;", ">"),
    ):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def detect_currency(text: str) -> str:
    lower = text.lower()
    # Prefer explicit codes / words before bare "$".
    for token in (
        "inr",
        "rs.",
        "rs ",
        "₹",
        "eur",
        "€",
        "gbp",
        "£",
        "cad",
        "c$",
        "aud",
        "a$",
        "sgd",
        "s$",
        "jpy",
        "¥",
        "chf",
        "nzd",
        "hkd",
        "hk$",
        "us$",
        "usd",
        "$",
    ):
        if token in lower or token in text:
            key = token.strip()
            return CURRENCY_SYMBOLS.get(key, CURRENCY_SYMBOLS.get(key.lower(), "USD"))
    if "₹" in text:
        return "INR"
    return "USD"


def _parse_amount(text: str) -> Optional[float]:
    match = AMOUNT_RE.search(text.replace(" ", "")) or AMOUNT_RE.search(text)
    if not match:
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            return None
        return float(digits)
    amount = float(match.group("amount").replace(",", ""))
    suffix = (match.group("suffix") or "").lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    elif suffix == "b":
        amount *= 1_000_000_000
    return amount


def format_currency_amount(amount: int, currency: str) -> str:
    symbols = {
        "USD": "$",
        "INR": "₹",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
    }
    symbol = symbols.get(currency)
    numbered = f"{amount:,}"
    if symbol:
        return f"{symbol}{numbered}"
    return f"{numbered} {currency}"


def to_usd(amount: float, currency: str) -> int:
    rate = USD_PER_UNIT.get(currency.upper(), 1.0)
    return int(round(amount * rate))


def parse_prize_money(raw: Any) -> Optional[ParsedPrize]:
    """Parse a free-text / HTML prize into original + USD estimate."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        # Kaggle-style {"id": "USD", "quantity": 20000}
        quantity = raw.get("quantity")
        if quantity is None:
            return None
        try:
            amount = float(quantity)
        except (TypeError, ValueError):
            return None
        if amount <= 0:
            return None
        currency = str(raw.get("id") or raw.get("currency") or "USD").upper()
        if currency not in USD_PER_UNIT:
            currency = "USD"
        whole = int(round(amount))
        return ParsedPrize(
            amount_original=whole,
            currency=currency,
            amount_usd=to_usd(amount, currency),
            display=format_currency_amount(whole, currency),
        )

    text = _strip_html(raw)
    if not text or REWARD_NON_CASH.match(text):
        return None
    amount = _parse_amount(text)
    if amount is None or amount <= 0:
        return None
    currency = detect_currency(text)
    whole = int(round(amount))
    return ParsedPrize(
        amount_original=whole,
        currency=currency,
        amount_usd=to_usd(amount, currency),
        display=format_currency_amount(whole, currency),
    )


def parse_prize_usd(raw: Any) -> Optional[int]:
    """Back-compat helper — returns approximate USD only."""
    parsed = parse_prize_money(raw)
    return parsed.amount_usd if parsed else None


def prize_fields_from_raw(raw: Any) -> Tuple[Optional[int], Optional[str]]:
    """Return (prize_pool_usd, prize_text) for scrapers."""
    parsed = parse_prize_money(raw)
    if not parsed:
        return None, None
    return parsed.amount_usd, parsed.display
