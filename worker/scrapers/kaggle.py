"""Kaggle competition ingestion.

Primary path: official Competitions API (KAGGLE_USERNAME + KAGGLE_KEY, or
KAGGLE_API_TOKEN). Fetches featured / research / playground / getting-started
and community competitions with pagination.

Fallback: Playwright against Kaggle's internal ListCompetitions endpoint
(works on residential / Modal IPs; often blocked by reCAPTCHA from datacenters).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote

import httpx

from scrapers.base import RawListing

# Official REST API
KAGGLE_LIST_URL = "https://www.kaggle.com/api/v1/competitions/list"

# Internal web API used by kaggle.com/competitions
KAGGLE_INTERNAL_LIST_URL = (
    "https://www.kaggle.com/api/i/competitions.CompetitionService/ListCompetitions"
)

# Host segments roughly: 1=featured, 2=research, 5=getting started,
# 8=playground-ish / masters variants, 10=community. 0 = all active.
INTERNAL_HOST_SEGMENTS = (0, 1, 2, 5, 8, 10)

# Official API category + group sweeps so we cover normal + community comps.
API_SWEEPS: Tuple[Tuple[str, str], ...] = (
    ("general", "featured"),
    ("general", "research"),
    ("general", "recruitment"),
    ("general", "gettingStarted"),
    ("general", "playground"),
    ("general", "masters"),
    ("general", "unspecified"),
    ("community", "unspecified"),
    ("community", "featured"),
    ("community", "research"),
    ("community", "playground"),
)

REWARD_NON_CASH = re.compile(
    r"^(knowledge|swag|kudos|jobs?|internship|experience|prestige|n/?a|none|-)$",
    re.I,
)
REWARD_MONEY = re.compile(
    r"(?P<currency>\$|USD|EUR|GBP|₹|INR|¥|JPY)?\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<suffix>[kKmMbB])?",
)


def fetch_kaggle(limit: int = 200) -> List[RawListing]:
    """Fetch open Kaggle competitions (API first, Playwright fallback)."""
    rows = _fetch_kaggle_api(limit=limit)
    if rows:
        return rows

    print("[kaggle] official API returned nothing; trying Playwright fallback")
    try:
        rows = asyncio.run(_fetch_kaggle_playwright(limit=limit))
    except RuntimeError:
        # Already inside an event loop (e.g. Modal / notebook)
        loop = asyncio.new_event_loop()
        try:
            rows = loop.run_until_complete(_fetch_kaggle_playwright(limit=limit))
        finally:
            loop.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[kaggle] playwright fallback failed: {exc}")
        rows = []

    if not rows:
        print(
            "[kaggle] no competitions fetched. Set KAGGLE_USERNAME + KAGGLE_KEY "
            "(or KAGGLE_API_TOKEN). Unauthenticated HTML is reCAPTCHA-gated."
        )
    return rows


def parse_prize_usd(reward: Any) -> Optional[int]:
    """Parse Kaggle reward field into an integer USD prize pool.

    Returns None for Knowledge / Swag / empty (no cash prize).
    """
    if reward is None:
        return None

    if isinstance(reward, dict):
        currency = str(reward.get("id") or reward.get("currency") or "USD").upper()
        quantity = reward.get("quantity")
        if quantity is None:
            return None
        try:
            amount = float(quantity)
        except (TypeError, ValueError):
            return None
        return _to_usd(amount, currency)

    text = str(reward).strip()
    if not text or REWARD_NON_CASH.match(text):
        return None

    match = REWARD_MONEY.search(text.replace(" ", ""))
    if not match:
        # Try with spaces: "$ 25,000"
        match = REWARD_MONEY.search(text)
    if not match:
        return None

    raw_amount = match.group("amount").replace(",", "")
    try:
        amount = float(raw_amount)
    except ValueError:
        return None

    suffix = (match.group("suffix") or "").lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    elif suffix == "b":
        amount *= 1_000_000_000

    currency = (match.group("currency") or "USD").upper()
    if currency == "$":
        currency = "USD"
    if currency == "₹":
        currency = "INR"
    if currency == "¥":
        currency = "JPY"

    return _to_usd(amount, currency)


def competition_to_raw(row: Dict[str, Any], *, source_tag: str = "api") -> RawListing:
    """Convert a competition dict (API or internal) into a RawListing."""
    ref = (
        row.get("ref")
        or row.get("competitionName")
        or row.get("competitionSlug")
        or row.get("slug")
        or row.get("id")
    )
    ref_str = str(ref or "").strip("/")
    if ref_str.startswith("http"):
        url = ref_str
        # Extract slug from URL when possible
        parts = ref_str.rstrip("/").split("/")
        ref_str = parts[-1] if parts else ref_str
    else:
        url = f"https://www.kaggle.com/competitions/{ref_str}" if ref_str else "https://www.kaggle.com/competitions"

    title = (
        row.get("title")
        or row.get("competitionTitle")
        or row.get("displayName")
        or "Untitled Kaggle Competition"
    )
    organizer = row.get("organizationName")
    if not organizer:
        org = row.get("organization")
        if isinstance(org, dict):
            organizer = org.get("name")
        else:
            organizer = org
    organizer = organizer or "Kaggle"

    reward = row.get("reward") or row.get("rewardDisplay") or row.get("prize")
    prize_usd = parse_prize_usd(reward)
    deadline = (
        row.get("deadline")
        or row.get("submissionDeadline")
        or row.get("enabledDate")
        or ""
    )
    category = (
        row.get("category")
        or row.get("hostSegment")
        or row.get("hostSegmentName")
        or ""
    )
    description = (
        row.get("description")
        or row.get("briefDescription")
        or row.get("subtitle")
        or ""
    )
    team_size = row.get("maxTeamSize") or row.get("maxTeamSizeJoin")
    has_scripts = bool(row.get("hasScripts") or row.get("hasKernels") or row.get("kernelCount"))
    is_hackathon = bool(row.get("hackathon"))
    team_count = row.get("teamCount") or row.get("totalTeams")

    structured = {
        "title": title,
        "url": url,
        "organizer": organizer,
        "source": "kaggle",
        "deadline_utc": _normalize_deadline(deadline),
        "prize_pool_usd": prize_usd,
        "has_cash_prize": prize_usd is not None and prize_usd > 0,
        "category": str(category),
        "has_starter_code": has_scripts or str(category).lower() in {"getting started", "gettingstarted", "playground"},
        "team_size_max": int(team_size) if team_size else None,
        "is_hackathon": is_hackathon,
        "is_community": "community" in str(category).lower()
        or bool(row.get("isCommunity"))
        or source_tag == "community",
        "description": description,
        "team_count": team_count,
        "ref": ref_str,
    }

    raw = (
        f"Title: {title}\n"
        f"URL: {url}\n"
        f"Organizer: {organizer}\n"
        f"Category: {category}\n"
        f"Reward: {reward}\n"
        f"Prize USD: {prize_usd}\n"
        f"Deadline: {deadline}\n"
        f"Description: {description}\n"
        f"Max team size: {team_size}\n"
        f"Has scripts/kernels: {has_scripts}\n"
        f"Hackathon flag: {is_hackathon}\n"
        f"Team count: {team_count}\n"
        f"Structured JSON: {json.dumps(structured, default=str)}\n"
    )

    return RawListing(
        title=title,
        url=url,
        organizer=str(organizer),
        source="kaggle",
        raw_text=raw,
        deadline_hint=str(deadline or ""),
        structured=structured,
    )


# ---------------------------------------------------------------------------
# Official API
# ---------------------------------------------------------------------------


def _auth() -> Optional[Tuple[str, str]]:
    username = os.getenv("KAGGLE_USERNAME", "").strip()
    key = os.getenv("KAGGLE_KEY", "").strip()
    if username and key:
        return username, key
    return None


def _api_token() -> str:
    return os.getenv("KAGGLE_API_TOKEN", "").strip()


def _fetch_kaggle_api(limit: int) -> List[RawListing]:
    auth = _auth()
    token = _api_token()
    if not auth and not token:
        print("[kaggle] no KAGGLE_USERNAME/KAGGLE_KEY or KAGGLE_API_TOKEN set")
        return []

    headers = {
        "User-Agent": "FindHackathonsBot/0.2 (+https://findhackathons.com)",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen: Dict[str, RawListing] = {}
    with httpx.Client(timeout=45.0, auth=auth, headers=headers, follow_redirects=True) as client:
        for group, category in API_SWEEPS:
            page = 1
            while len(seen) < limit and page <= 20:
                params = {
                    "group": group,
                    "category": category,
                    "page": page,
                    "sortBy": "prize",
                }
                try:
                    response = client.get(KAGGLE_LIST_URL, params=params)
                except httpx.HTTPError as exc:
                    print(f"[kaggle] API error {group}/{category} p{page}: {exc}")
                    break

                if response.status_code == 401:
                    print("[kaggle] API auth failed (401). Check credentials.")
                    return []
                if response.status_code >= 400:
                    # Some group/category combos are invalid — skip quietly.
                    if response.status_code == 400:
                        break
                    print(
                        f"[kaggle] API {group}/{category} p{page}: "
                        f"{response.status_code} {response.text[:160]}"
                    )
                    break

                rows = _normalize_api_rows(response.json())
                if not rows:
                    break

                for row in rows:
                    listing = competition_to_raw(
                        row,
                        source_tag="community" if group == "community" else "api",
                    )
                    seen.setdefault(listing.url, listing)

                if len(rows) < 20:
                    break
                page += 1

    listings = list(seen.values())
    # Prize comps first in the batch so downstream limit_per_source keeps them.
    listings.sort(
        key=lambda item: (
            0 if (item.structured or {}).get("has_cash_prize") else 1,
            -((item.structured or {}).get("prize_pool_usd") or 0),
            item.title.lower(),
        )
    )
    print(
        f"[kaggle] API fetched {len(listings)} unique comps "
        f"({sum(1 for x in listings if (x.structured or {}).get('has_cash_prize'))} with cash prizes)"
    )
    return listings[:limit]


def _normalize_api_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("competitions", "items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


# ---------------------------------------------------------------------------
# Playwright internal API fallback
# ---------------------------------------------------------------------------


async def _fetch_kaggle_playwright(limit: int = 200) -> List[RawListing]:
    from playwright.async_api import async_playwright

    seen: Dict[str, RawListing] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900},
            locale="en-US",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()
        await page.goto(
            "https://www.kaggle.com/competitions",
            wait_until="domcontentloaded",
            timeout=90_000,
        )

        xsrf = ""
        for _ in range(20):
            cookies = await context.cookies()
            token = next((c["value"] for c in cookies if c["name"] == "XSRF-TOKEN"), "")
            body = (await page.inner_text("body"))[:80]
            if token and "Checking your browser" not in body:
                xsrf = unquote(token)
                break
            await page.wait_for_timeout(1500)

        if not xsrf:
            print("[kaggle] playwright: no XSRF token (likely reCAPTCHA-blocked)")
            await browser.close()
            return []

        for host in INTERNAL_HOST_SEGMENTS:
            page_token = ""
            for _ in range(15):
                if len(seen) >= limit:
                    break
                payload = {
                    "selector": {
                        "competitionIds": [],
                        "listOption": "LIST_OPTION_ACTIVE",
                        "hostSegmentIdFilter": host,
                        "pageSize": 100,
                        "pageToken": page_token,
                    }
                }
                result = await page.evaluate(
                    """async ({url, payload, xsrf}) => {
                      const res = await fetch(url, {
                        method: 'POST',
                        headers: {
                          'content-type': 'application/json',
                          'x-xsrf-token': xsrf,
                          'accept': 'application/json',
                        },
                        body: JSON.stringify(payload),
                        credentials: 'include',
                      });
                      const text = await res.text();
                      return {status: res.status, text};
                    }""",
                    {"url": KAGGLE_INTERNAL_LIST_URL, "payload": payload, "xsrf": xsrf},
                )
                if result.get("status") != 200 or not (result.get("text") or "").strip().startswith("{"):
                    print(
                        f"[kaggle] playwright host={host} status={result.get('status')} "
                        f"body={(result.get('text') or '')[:120]!r}"
                    )
                    break

                data = json.loads(result["text"])
                comps = (
                    data.get("competitions")
                    or data.get("competitionList")
                    or data.get("items")
                    or []
                )
                if not comps and data.get("totalResults") and not data.get("competitions"):
                    # Soft-empty response — stop this host.
                    break

                for row in comps:
                    if not isinstance(row, dict):
                        continue
                    listing = competition_to_raw(
                        row,
                        source_tag="community" if host == 10 else "playwright",
                    )
                    seen.setdefault(listing.url, listing)

                page_token = data.get("nextPageToken") or data.get("pageToken") or ""
                if not page_token or not comps:
                    break

        await browser.close()

    listings = list(seen.values())
    listings.sort(
        key=lambda item: (
            0 if (item.structured or {}).get("has_cash_prize") else 1,
            -((item.structured or {}).get("prize_pool_usd") or 0),
            item.title.lower(),
        )
    )
    print(f"[kaggle] playwright fetched {len(listings)} unique comps")
    return listings[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_usd(amount: float, currency: str) -> Optional[int]:
    if amount <= 0:
        return None
    # Rough FX — good enough for ranking; exact conversion isn't the product.
    rates = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.27,
        "INR": 0.012,
        "JPY": 0.0067,
    }
    rate = rates.get(currency.upper(), 1.0 if currency.upper() in {"USD", ""} else None)
    if rate is None:
        # Unknown currency code on a numeric reward — treat as USD quantity.
        rate = 1.0
    return int(round(amount * rate))


def _normalize_deadline(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        # epoch millis or seconds
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
        return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    except ValueError:
        return text


def iter_prize_stats(listings: Iterable[RawListing]) -> Dict[str, int]:
    rows = list(listings)
    return {
        "total": len(rows),
        "with_prize": sum(1 for r in rows if (r.structured or {}).get("has_cash_prize")),
        "no_prize": sum(1 for r in rows if not (r.structured or {}).get("has_cash_prize")),
    }
