"""Devfolio ingestion via search API."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from scrapers.base import RawListing

API_URL = "https://api.devfolio.co/api/search/hackathons"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; findhackathons/0.1)",
    "Accept": "application/json",
}


def fetch_devfolio(limit: int = 80) -> List[RawListing]:
    now = datetime.now(timezone.utc)
    rows: List[RawListing] = []
    for src in _fetch_raw("application_open"):
        item = _normalize(src)
        if not item:
            continue
        if item.get("is_restricted"):
            continue
        deadline = item.get("_deadline_dt")
        if deadline and deadline <= now:
            continue
        rows.append(_to_raw(item))
        if len(rows) >= limit:
            break
    print(f"[devfolio] fetched {len(rows)}")
    return rows


def _parse_dt(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _strip_html(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()


def _prize_to_text(prizes: Any) -> Tuple[Optional[str], Optional[int]]:
    if not isinstance(prizes, list) or not prizes:
        return None, None
    total = 0
    for prize in prizes:
        if not isinstance(prize, dict):
            continue
        for key in ("amount", "value", "cash", "prize_amount", "rewards"):
            value = prize.get(key)
            if isinstance(value, (int, float)):
                total += int(value)
                break
            if isinstance(value, str):
                digits = re.sub(r"[^\d]", "", value)
                if digits:
                    total += int(digits)
                break
    text = f"{len(prizes)} prizes" + (f" (~{total:,})" if total else "")
    return text, (total or None)


def _fetch_raw(app_type: str = "application_open", page_size: int = 20, max_pages: int = 20) -> Iterator[Dict[str, Any]]:
    with httpx.Client(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        total = None
        for page in range(max_pages):
            body = {"type": app_type, "from": page * page_size, "size": page_size}
            try:
                response = client.post(API_URL, json=body)
            except httpx.HTTPError as exc:
                print(f"[devfolio] page {page}: {exc}")
                return
            if response.status_code >= 400:
                print(f"[devfolio] HTTP {response.status_code}: {response.text[:200]}")
                return
            hits = (response.json().get("hits") or {})
            if total is None:
                total = (hits.get("total") or {}).get("value")
                print(f"[devfolio] total={total}")
            recs = hits.get("hits") or []
            if not recs:
                return
            for rec in recs:
                src = rec.get("_source", rec)
                if isinstance(src, dict):
                    yield src
            if total and (page + 1) * page_size >= total:
                return
            time.sleep(0.35)


def _normalize(src: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name, slug = src.get("name"), src.get("slug")
    if not name or not slug:
        return None
    setting = src.get("hackathon_setting") or {}
    reg_ends = _parse_dt(setting.get("reg_ends_at"))
    ends_at = _parse_dt(src.get("ends_at"))
    deadline = reg_ends or ends_at
    prize_text, prize_value = _prize_to_text(src.get("prizes"))
    themes = [
        str(t.get("name") if isinstance(t, dict) else t).lower()
        for t in (src.get("themes") or [])
        if t
    ]
    subdomain = setting.get("subdomain") or slug
    return {
        "title": str(name),
        "url": f"https://{subdomain}.devfolio.co",
        "organizer": src.get("hosted_by") or "Devfolio",
        "source": "devfolio",
        "deadline_utc": deadline.isoformat() if deadline else None,
        "_deadline_dt": deadline,
        "prize_pool_usd": prize_value,
        "has_cash_prize": bool(prize_value and prize_value > 0),
        "category": "hackathon",
        "has_starter_code": False,
        "team_size_max": src.get("team_size") if isinstance(src.get("team_size"), int) else None,
        "requires_travel": not bool(src.get("is_online")),
        "description": _strip_html(src.get("desc") or src.get("tagline") or ""),
        "themes": themes,
        "skill_floor": "intermediate",
        "is_restricted": bool(src.get("private")) or bool(setting.get("women_only")),
    }


def _map_domains(themes: List[str]) -> List[str]:
    blob = " ".join(themes)
    found: List[str] = []
    for domain, pattern in [
        ("web-dev", r"web|frontend|backend|fullstack"),
        ("web3", r"web3|blockchain|crypto"),
        ("mobile", r"mobile|android|ios"),
        ("nlp", r"ai|ml|nlp|llm"),
        ("cv", r"vision|image"),
        ("hardware", r"iot|hardware|robot"),
        ("game-dev", r"game"),
        ("tabular", r"data"),
    ]:
        if re.search(pattern, blob, re.I):
            found.append(domain)
    return found or ["web-dev", "other"]


def _to_raw(item: Dict[str, Any]) -> RawListing:
    domains = _map_domains(item.get("themes") or [])
    structured = {
        k: v
        for k, v in item.items()
        if not k.startswith("_")
    }
    structured.update(
        {
            "domains": domains,
            "skill_floor_reasoning": "Devfolio list metadata; skill floor pending enrichment.",
            "confidence": "medium",
            "students_only": False,
        }
    )
    raw = (
        f"Title: {item['title']}\nURL: {item['url']}\nOrganizer: {item['organizer']}\n"
        f"Deadline: {item.get('deadline_utc')}\nPrize USD: {item.get('prize_pool_usd')}\n"
        f"Themes: {', '.join(item.get('themes') or [])}\n"
        f"Description: {(item.get('description') or '')[:1500]}\n"
        f"Structured JSON: {json.dumps(structured, default=str)}\n"
    )
    return RawListing(
        title=item["title"],
        url=item["url"],
        organizer=str(item["organizer"]),
        source="devfolio",
        raw_text=raw,
        deadline_hint=str(item.get("deadline_utc") or ""),
        structured=structured,
    )
