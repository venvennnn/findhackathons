"""Devpost hackathon ingestion via public JSON API."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from scrapers.base import RawListing

API_URL = "https://devpost.com/api/hackathons"
HEADERS = {
    "User-Agent": "findhackathons/0.1 (+https://findhackathons.com)",
    "Accept": "application/json",
}
MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        1,
    )
}


def fetch_devpost(limit: int = 80) -> List[RawListing]:
    rows: List[RawListing] = []
    for raw in _fetch_raw(status="open", max_pages=40):
        item = _normalize(raw)
        if not item:
            continue
        rows.append(_to_raw(item))
        if len(rows) >= limit:
            break
    print(f"[devpost] fetched {len(rows)}")
    return rows


def _get(d: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(d, dict) and d.get(name) is not None:
            return d[name]
    return default


def _strip_html(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    for a, b in [
        ("&amp;", "&"),
        ("&nbsp;", " "),
        ("&#39;", "'"),
        ("&quot;", '"'),
        ("&lt;", "<"),
        ("&gt;", ">"),
    ]:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def parse_dates(raw: Any) -> Tuple[Optional[datetime], Optional[datetime]]:
    if not isinstance(raw, str) or not raw.strip():
        return None, None
    text = raw.strip().replace("\u2013", "-").replace("\u2014", "-")
    year_match = re.search(r"(\d{4})", text)
    if not year_match:
        return None, None
    year = int(year_match.group(1))
    parts = re.findall(r"([A-Za-z]{3,})\.?\s+(\d{1,2})", text)
    bare = re.findall(r"-\s*(\d{1,2})\s*,", text)

    def build(mon: str, day: str, yr: int) -> Optional[datetime]:
        month = MONTHS.get(mon[:3].lower())
        if not month:
            return None
        try:
            return datetime(yr, month, int(day), tzinfo=timezone.utc)
        except ValueError:
            return None

    if len(parts) >= 2:
        start, end = build(*parts[0], year), build(*parts[1], year)
        if start and end and end < start:
            start = build(*parts[0], year - 1)
        return start, end
    if len(parts) == 1:
        start = build(*parts[0], year)
        if bare:
            return start, build(parts[0][0], bare[0], year)
        return start, start
    return None, None


def parse_prize(raw: Any) -> Tuple[Optional[str], Optional[int]]:
    text = _strip_html(raw)
    digits = re.sub(r"[^\d]", "", text)
    return (text or None), (int(digits) if digits else None)


def _fetch_raw(status: str = "open", max_pages: int = 40, delay: float = 0.6) -> Iterator[Dict[str, Any]]:
    seen: set[str] = set()
    with httpx.Client(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            try:
                response = client.get(
                    API_URL,
                    params={"page": page, "status[]": status, "order_by": "deadline"},
                )
            except httpx.HTTPError as exc:
                print(f"[devpost] page {page} failed: {exc}")
                return

            if response.status_code == 429:
                time.sleep(8)
                continue
            if response.status_code >= 400:
                print(f"[devpost] HTTP {response.status_code} on page {page}")
                return

            try:
                payload = response.json()
            except ValueError:
                print("[devpost] non-JSON response — endpoint may have changed")
                return

            batch = (
                payload
                if isinstance(payload, list)
                else _get(payload, "hackathons", "results", "data", default=[])
            )
            if not batch:
                return

            fresh = 0
            for item in batch:
                if not isinstance(item, dict):
                    continue
                ident = str(_get(item, "id", "analytics_identifier", default="") or "")
                if ident and ident in seen:
                    continue
                if ident:
                    seen.add(ident)
                fresh += 1
                yield item

            if fresh == 0:
                return
            time.sleep(delay)


def _normalize(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = _strip_html(_get(raw, "title"))
    url = _normalize_devpost_url(_get(raw, "url"))
    if not title or not url:
        return None

    _start, end = parse_dates(_get(raw, "submission_period_dates"))
    prize_text, prize_value = parse_prize(_get(raw, "prize_amount"))
    disp = _get(raw, "displayed_location", default={}) or {}
    loc = _strip_html(disp.get("location")) if isinstance(disp, dict) else None
    is_online = (not loc) or loc.lower() == "online"
    themes = sorted(
        {
            (t.get("name") if isinstance(t, dict) else t)
            for t in (_get(raw, "themes", default=[]) or [])
            if t
        }
    )
    floor = "advanced" if (prize_value or 0) >= 50_000 else "intermediate"
    themes_list = [str(t).lower() for t in themes]
    students_only = _looks_students_only(title, themes_list, loc)

    return {
        "title": title,
        "url": url,
        "organizer": "Devpost",
        "source": "devpost",
        "deadline_utc": end.isoformat() if end else None,
        "prize_pool_usd": prize_value,
        "has_cash_prize": bool(prize_value and prize_value > 0),
        "category": "hackathon",
        "has_starter_code": False,
        "team_size_max": None,
        "requires_travel": not is_online,
        "description": prize_text or "",
        "themes": themes_list,
        "location": loc,
        "skill_floor": floor,
        "students_only": students_only,
    }


def _normalize_devpost_url(raw: Any) -> Optional[str]:
    """Keep subdomain.devpost.com hackathon URLs; drop project /software/ links."""
    if not isinstance(raw, str):
        return None
    url = raw.strip()
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/"):
        url = "https://devpost.com" + url
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url.lstrip("/")
    lower = url.lower()
    # Project gallery pages are not hackathons.
    if "/software/" in lower:
        return None
    if "devpost.com/hackathons" in lower:
        return None
    return url


def _looks_students_only(title: str, themes: List[str], location: Optional[str]) -> bool:
    """Heuristic: Devpost list API rarely exposes eligibility flags."""
    blob = " ".join([title or "", " ".join(themes or []), location or ""]).lower()
    keywords = (
        "student",
        "students only",
        "university",
        "college",
        "campus",
        "high school",
        "undergrad",
        "undergraduate",
        "school students",
    )
    return any(k in blob for k in keywords)


def _map_domains(themes: List[str]) -> List[str]:
    blob = " ".join(themes)
    found: List[str] = []
    rules = [
        ("nlp", r"ai|ml|nlp|language|llm"),
        ("cv", r"vision|image|cv"),
        ("web-dev", r"web|fullstack|javascript|react"),
        ("mobile", r"mobile|android|ios"),
        ("web3", r"web3|crypto|blockchain"),
        ("game-dev", r"game"),
        ("hardware", r"hardware|iot|robot"),
        ("tabular", r"data|analytics|tabular"),
    ]
    for domain, pattern in rules:
        if re.search(pattern, blob, re.I):
            found.append(domain)
    return found or ["other"]


def _to_raw(item: Dict[str, Any]) -> RawListing:
    domains = _map_domains(item.get("themes") or [])
    structured = {
        **item,
        "domains": domains,
        "skill_floor_reasoning": (
            "Large prize pool heuristic → advanced."
            if item.get("skill_floor") == "advanced"
            else "Devpost list metadata; skill floor defaulted to intermediate."
        ),
        "confidence": "medium",
    }
    raw = (
        f"Title: {item['title']}\nURL: {item['url']}\nOrganizer: Devpost\n"
        f"Prize: {item.get('description')}\nPrize USD: {item.get('prize_pool_usd')}\n"
        f"Deadline: {item.get('deadline_utc')}\nLocation: {item.get('location')}\n"
        f"Themes: {', '.join(item.get('themes') or [])}\n"
        f"Structured JSON: {json.dumps(structured, default=str)}\n"
    )
    return RawListing(
        title=item["title"],
        url=item["url"],
        organizer="Devpost",
        source="devpost",
        raw_text=raw,
        deadline_hint=str(item.get("deadline_utc") or ""),
        structured=structured,
    )
