"""Unstop ingestion via public opportunity search API.

By product policy we only keep the latest ~20 open listings with nearest deadlines.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from scrapers.base import RawListing

API_URL = "https://unstop.com/api/public/opportunity/search-result"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; findhackathons/0.1)",
    "Accept": "application/json",
}


def fetch_unstop(limit: int = 20) -> List[RawListing]:
    """Fetch open Unstop hackathons, keep nearest deadlines only (default 20)."""
    now = datetime.now(timezone.utc)
    candidates: List[Dict[str, Any]] = []
    for rec in _fetch_raw(max_pages=8, per_page=50):
        if rec.get("regn_open") != 1:
            continue
        item = _normalize(rec)
        if not item:
            continue
        deadline = item.get("_deadline_dt")
        if deadline and deadline <= now:
            continue
        candidates.append(item)

    candidates.sort(
        key=lambda row: row.get("_deadline_dt") or datetime.max.replace(tzinfo=timezone.utc)
    )
    rows = [_to_raw(item) for item in candidates[:limit]]
    print(f"[unstop] kept {len(rows)} nearest open (from {len(candidates)} candidates)")
    return rows


def fetch_unstop_playwright(limit: int = 20) -> List[RawListing]:
    """Sync alias kept for Modal compatibility — API path is preferred."""
    return fetch_unstop(limit=limit)


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


def _prize_to_text(prizes: Any) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    from scrapers.prizes import parse_prize_money

    if not isinstance(prizes, list) or not prizes:
        return None, None, None
    total_usd = 0
    displays: list[str] = []
    for prize in prizes:
        if not isinstance(prize, dict):
            continue
        raw_val = None
        currency_hint = prize.get("currency") or prize.get("currency_code")
        for key in ("amount", "value", "cash", "prize_amount", "rewards"):
            value = prize.get(key)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                raw_val = f"{currency_hint or 'INR'} {value}".strip()
            else:
                raw_val = str(value)
            break
        if raw_val is None:
            continue
        parsed = parse_prize_money(raw_val)
        if parsed:
            total_usd += parsed.amount_usd
            displays.append(parsed.display)
    if not total_usd:
        return None, None, None
    text = f"{len(prizes)} prizes"
    display = displays[0] if len(displays) == 1 else f"~${total_usd:,}"
    return text, total_usd, display


def _fetch_raw(max_pages: int = 8, per_page: int = 50) -> Iterator[Dict[str, Any]]:
    params = {"opportunity": "hackathons", "per_page": per_page}
    seen: set[Any] = set()
    with httpx.Client(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            try:
                response = client.get(API_URL, params={**params, "page": page})
            except httpx.HTTPError as exc:
                print(f"[unstop] page {page}: {exc}")
                return
            if response.status_code >= 400:
                print(f"[unstop] HTTP {response.status_code}: {response.text[:200]}")
                return
            data = response.json().get("data") or {}
            recs = data.get("data") or []
            if page == 1:
                print(f"[unstop] total={data.get('total')} last_page={data.get('last_page')}")
            if not recs:
                return
            fresh = 0
            for rec in recs:
                rid = rec.get("id")
                if rid in seen:
                    continue
                seen.add(rid)
                fresh += 1
                yield rec
            if fresh == 0 or not data.get("next_page_url"):
                return
            time.sleep(0.4)


def _normalize(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title, rid = rec.get("title"), rec.get("id")
    if not title or not rid:
        return None
    details = _strip_html(rec.get("details") or "")
    end = _parse_dt(rec.get("end_date"))
    org = rec.get("organisation")
    org_name = org.get("name") if isinstance(org, dict) else org
    prize_text, prize_value, prize_display = _prize_to_text(rec.get("prizes"))
    path = rec.get("public_url") or rec.get("seo_url") or ""
    url = f"https://unstop.com/{path.lstrip('/')}" if path else "https://unstop.com"
    skills = [
        str(s.get("name") if isinstance(s, dict) else s).lower()
        for s in (rec.get("required_skills") or [])
        if s
    ]
    return {
        "title": str(title),
        "url": url,
        "organizer": org_name or "Unstop",
        "source": "unstop",
        "deadline_utc": end.isoformat() if end else None,
        "_deadline_dt": end,
        "prize_pool_usd": prize_value,
        "prize_text": prize_display,
        "has_cash_prize": bool(prize_value and prize_value > 0),
        "category": rec.get("subtype") or "hackathon",
        "has_starter_code": False,
        "team_size_max": None,
        "requires_travel": str(rec.get("region", "")).lower() != "online",
        "description": details[:2000],
        "themes": skills,
        "skill_floor": "intermediate",
        "students_only": any(
            k in details.lower()
            for k in ("college", "university", "enrolled student", "students only")
        ),
    }


def _map_domains(themes: List[str]) -> List[str]:
    blob = " ".join(themes)
    found: List[str] = []
    for domain, pattern in [
        ("nlp", r"nlp|ml|ai|python|data"),
        ("web-dev", r"web|javascript|react|java"),
        ("cv", r"vision|image|opencv"),
        ("mobile", r"android|ios|flutter"),
        ("tabular", r"excel|sql|analytics"),
        ("web3", r"blockchain|web3"),
    ]:
        if re.search(pattern, blob, re.I):
            found.append(domain)
    return found or ["other"]


def _to_raw(item: Dict[str, Any]) -> RawListing:
    domains = _map_domains(item.get("themes") or [])
    structured = {k: v for k, v in item.items() if not k.startswith("_")}
    structured.update(
        {
            "domains": domains,
            "skill_floor_reasoning": "Unstop list metadata; skill floor pending enrichment.",
            "confidence": "low",
        }
    )
    raw = (
        f"Title: {item['title']}\nURL: {item['url']}\nOrganizer: {item['organizer']}\n"
        f"Deadline: {item.get('deadline_utc')}\nPrize USD: {item.get('prize_pool_usd')}\n"
        f"Description: {(item.get('description') or '')[:1500]}\n"
        f"Structured JSON: {json.dumps(structured, default=str)}\n"
    )
    return RawListing(
        title=item["title"],
        url=item["url"],
        organizer=str(item["organizer"]),
        source="unstop",
        raw_text=raw,
        deadline_hint=str(item.get("deadline_utc") or ""),
        structured=structured,
    )
