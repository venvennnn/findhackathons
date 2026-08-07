"""Kaggle competition ingestion.

Uses the public competitions list endpoint when credentials are unavailable,
and falls back to a lightweight HTML scrape.
"""

from __future__ import annotations

import os
from typing import List

import httpx

from scrapers.base import RawListing


def fetch_kaggle(limit: int = 25) -> List[RawListing]:
    username = os.getenv("KAGGLE_USERNAME", "")
    key = os.getenv("KAGGLE_KEY", "")

    if username and key:
        return _fetch_kaggle_api(username, key, limit=limit)
    return _fetch_kaggle_public(limit=limit)


def _fetch_kaggle_api(username: str, key: str, limit: int) -> List[RawListing]:
    url = "https://www.kaggle.com/api/v1/competitions/list"
    with httpx.Client(timeout=45.0, auth=(username, key)) as client:
        response = client.get(url, params={"group": "general", "category": "all", "page": 1})
        response.raise_for_status()
        rows = response.json()

    listings: List[RawListing] = []
    for row in rows[:limit]:
        ref = row.get("ref") or row.get("id")
        title = row.get("title") or "Untitled Kaggle Competition"
        competition_url = f"https://www.kaggle.com/competitions/{ref}"
        raw = (
            f"Title: {title}\n"
            f"Description: {row.get('description') or row.get('organizationName') or ''}\n"
            f"Reward: {row.get('reward')}\n"
            f"Deadline: {row.get('deadline') or row.get('enabledDate')}\n"
            f"Category: {row.get('category')}\n"
            f"Organization: {row.get('organizationName')}\n"
        )
        listings.append(
            RawListing(
                title=title,
                url=competition_url,
                organizer=row.get("organizationName") or "Kaggle",
                source="kaggle",
                raw_text=raw,
                deadline_hint=str(row.get("deadline") or ""),
            )
        )
    return listings


def _fetch_kaggle_public(limit: int) -> List[RawListing]:
    """Best-effort public scrape of the competitions listing page."""
    url = "https://www.kaggle.com/competitions"
    headers = {"User-Agent": "FindHackathonsBot/0.1 (+https://findhackathons.com)"}
    with httpx.Client(timeout=45.0, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code >= 400:
            print(f"[kaggle] public fetch failed: {response.status_code}")
            return []
        html = response.text

    # Extremely light extraction — enrichment LLM handles unstructured text.
    # Prefer Modal Playwright path when HTML is JS-rendered.
    if "competition" not in html.lower():
        return []

    return [
        RawListing(
            title="Kaggle Competitions Feed",
            url=url,
            organizer="Kaggle",
            source="kaggle",
            raw_text=html[:15000],
        )
    ][:limit]