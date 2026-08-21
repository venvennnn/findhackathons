"""Kaggle competition ingestion via official API.

PARAMETER NOTES (from live API):
  - group validates strictly: general | community | entered
  - category only for group=general; omit entirely for community
  - Auth: LEGACY username + 32-hex key via basic auth (not KGAT_ tokens)
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from scrapers.base import RawListing

API_BASE = "https://www.kaggle.com/api/v1"
PAGE_SIZE_HINT = 20

CATEGORY_TO_FLOOR = {
    "gettingstarted": "beginner",
    "playground": "beginner",
    "featured": "intermediate",
    "recruitment": "intermediate",
    "analytics": "intermediate",
    "research": "advanced",
    "masters": "advanced",
}
OFFICIAL_CATEGORIES = ("gettingStarted", "playground", "featured", "research")

REWARD_NON_CASH = re.compile(
    r"^(knowledge|swag|kudos|jobs?|internship|experience|prestige|n/?a|none|-)$",
    re.I,
)
REWARD_MONEY = re.compile(
    r"(?P<currency>\$|USD|EUR|GBP|₹|INR|¥|JPY)?\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<suffix>[kKmMbB])?",
)


def fetch_kaggle(limit: int = 500) -> List[RawListing]:
    auth = _auth()
    if not auth:
        print("[kaggle] set KAGGLE_USERNAME + KAGGLE_KEY (legacy API credentials)")
        return []

    now = datetime.now(timezone.utc)
    rows: Dict[str, RawListing] = {}
    headers = {"User-Agent": "findhackathons/0.1 (+https://findhackathons.com)"}

    with httpx.Client(timeout=30.0, auth=auth, headers=headers, follow_redirects=True) as client:
        for category in OFFICIAL_CATEGORIES:
            count = 0
            for raw in _fetch_raw(client, group="general", category=category):
                item = _normalize(raw, is_community=False)
                if not item:
                    continue
                deadline = item.get("_deadline_dt")
                if deadline and deadline <= now:
                    continue
                listing = _to_raw(item)
                rows[listing.url] = listing
                count += 1
            print(f"[kaggle] general/{category}: {count}")

        kept = 0
        for raw in _fetch_raw(client, group="community", category=None):
            item = _normalize(raw, is_community=True)
            if not item:
                continue
            deadline = item.get("_deadline_dt")
            if deadline and deadline <= now:
                continue
            # Keep every open community comp — feed horizon filtering is UI/API-side.
            if item.get("_deadline_dt") is None:
                continue
            listing = _to_raw(item)
            rows.setdefault(listing.url, listing)
            kept += 1
        print(f"[kaggle] community: {kept} open kept")

    listings = list(rows.values())
    listings.sort(
        key=lambda item: (
            0 if (item.structured or {}).get("has_cash_prize") else 1,
            -((item.structured or {}).get("prize_pool_usd") or 0),
            item.title.lower(),
        )
    )
    print(f"[kaggle] total unique: {len(listings)}")
    return listings[:limit]


def parse_prize_usd(reward: Any) -> Optional[int]:
    if reward is None:
        return None
    if isinstance(reward, dict):
        quantity = reward.get("quantity")
        if quantity is None:
            return None
        try:
            amount = float(quantity)
        except (TypeError, ValueError):
            return None
        return int(round(amount)) if amount > 0 else None

    text = str(reward).strip()
    if not text or REWARD_NON_CASH.match(text):
        return None
    match = REWARD_MONEY.search(text.replace(" ", "")) or REWARD_MONEY.search(text)
    if not match:
        return None
    amount = float(match.group("amount").replace(",", ""))
    suffix = (match.group("suffix") or "").lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    return int(round(amount)) if amount > 0 else None


def _auth() -> Optional[Tuple[str, str]]:
    username = os.getenv("KAGGLE_USERNAME", "").strip()
    key = os.getenv("KAGGLE_KEY", "").strip()
    if username and key:
        return username, key
    return None


def _get(d: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(d, dict) and d.get(name) is not None:
            return d[name]
    return default


def _parse_dt(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _fetch_raw(
    client: httpx.Client,
    *,
    group: str,
    category: Optional[str],
    max_pages: int = 40,
    delay: float = 0.4,
) -> Iterator[Dict[str, Any]]:
    for page in range(1, max_pages + 1):
        params: Dict[str, Any] = {"group": group, "sortBy": "latestDeadline", "page": page}
        if category:
            params["category"] = category
        try:
            response = client.get(f"{API_BASE}/competitions/list", params=params)
        except httpx.HTTPError as exc:
            print(f"[kaggle] {group}/{category or '-'} page {page}: {exc}")
            return
        if response.status_code == 401:
            print("[kaggle] 401 — use LEGACY username+key, not KGAT_ tokens")
            return
        if response.status_code == 429:
            time.sleep(5)
            continue
        if response.status_code >= 400:
            print(
                f"[kaggle] HTTP {response.status_code} on {group}/{category or '-'}: "
                f"{response.text[:200]}"
            )
            return
        try:
            batch = response.json()
        except ValueError:
            return
        if not isinstance(batch, list) or not batch:
            return
        for row in batch:
            if isinstance(row, dict):
                yield row
        if len(batch) < PAGE_SIZE_HINT:
            return
        time.sleep(delay)


def _domains(raw: Dict[str, Any]) -> List[str]:
    tags = {
        str(t.get("name") if isinstance(t, dict) else t).lower()
        for t in (_get(raw, "tags", default=[]) or [])
        if t
    }
    blob = f"{_get(raw, 'title', default='')} {_get(raw, 'description', default='')}".lower()
    found: List[str] = []
    rules = [
        ("nlp", ("nlp", "text", "language", "llm", "prompt")),
        ("cv", ("image", "vision", "detection", "segmentation")),
        ("tabular", ("tabular", "regression", "classification", "forecast")),
        ("other", ("audio", "speech", "reinforcement")),
    ]
    pool = tags or set()
    for domain, toks in rules:
        if any(t in blob or t in " ".join(pool) for t in toks):
            found.append(domain)
    if tags and not found:
        return ["other"]
    return found or ["tabular"]


def _normalize(raw: Dict[str, Any], *, is_community: bool) -> Optional[Dict[str, Any]]:
    ref = _get(raw, "ref", "id")
    title = _get(raw, "title")
    if not ref or not title:
        return None
    category = str(_get(raw, "category", default="") or "").lower()
    deadline = _parse_dt(_get(raw, "deadline"))
    teams = _get(raw, "teamCount", "team_count")
    reward = _get(raw, "reward")
    description = str(_get(raw, "description", default="") or "")
    notebooks_only = bool(
        _get(raw, "isKernelsSubmissionsOnly", "is_kernels_submissions_only", default=False)
    )
    prize = parse_prize_usd(reward)
    if is_community:
        floor = "intermediate"
        reasoning = "Community host category is not a reliable difficulty signal."
    else:
        floor = CATEGORY_TO_FLOOR.get(category, "intermediate")
        reasoning = f"Kaggle category={category or 'unknown'} → {floor}."

    max_team = _get(raw, "maxTeamSize", "max_team_size")
    url = _get(raw, "url") or f"https://www.kaggle.com/competitions/{ref}"
    return {
        "title": str(title),
        "url": str(url),
        "organizer": _get(raw, "organizationName", "organization_name") or "Kaggle",
        "source": "kaggle",
        "deadline_utc": deadline.isoformat() if deadline else None,
        "_deadline_dt": deadline,
        "prize_pool_usd": prize,
        "has_cash_prize": bool(prize and prize > 0),
        "category": category,
        "has_starter_code": (not is_community and category == "gettingstarted") or notebooks_only,
        "team_size_max": int(max_team) if isinstance(max_team, int) else None,
        "requires_travel": False,
        "description": description,
        "domains": _domains(raw),
        "skill_floor": floor,
        "skill_floor_reasoning": reasoning,
        "confidence": "high" if not is_community else "medium",
        "team_count": teams if isinstance(teams, int) else None,
        "desc_len": len(description),
        "is_community": is_community,
        "days_left": (deadline - datetime.now(timezone.utc)).days if deadline else None,
    }


def _community_usable(item: Dict[str, Any]) -> Tuple[bool, str]:
    """Legacy helper — community ingest now keeps all open comps with a deadline."""
    if item.get("_deadline_dt") is None:
        return False, "no_deadline"
    return True, ""


def _to_raw(item: Dict[str, Any]) -> RawListing:
    structured = {k: v for k, v in item.items() if not k.startswith("_")}
    raw = (
        f"Title: {item['title']}\nURL: {item['url']}\nOrganizer: {item['organizer']}\n"
        f"Category: {item.get('category')}\nReward USD: {item.get('prize_pool_usd')}\n"
        f"Deadline: {item.get('deadline_utc')}\nCommunity: {item.get('is_community')}\n"
        f"Description: {(item.get('description') or '')[:1500]}\n"
        f"Structured JSON: {json.dumps(structured, default=str)}\n"
    )
    return RawListing(
        title=item["title"],
        url=item["url"],
        organizer=str(item["organizer"]),
        source="kaggle",
        raw_text=raw,
        deadline_hint=str(item.get("deadline_utc") or ""),
        structured=structured,
    )


def iter_prize_stats(listings: List[RawListing]) -> Dict[str, int]:
    rows = list(listings)
    return {
        "total": len(rows),
        "with_prize": sum(1 for r in rows if (r.structured or {}).get("has_cash_prize")),
        "no_prize": sum(1 for r in rows if not (r.structured or {}).get("has_cash_prize")),
    }
