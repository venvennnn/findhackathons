"""Devpost hackathon ingestion via public search pages."""

from __future__ import annotations

import re
from typing import List

import httpx

from scrapers.base import RawListing

DEVPOST_SEARCH = "https://devpost.com/hackathons?challenge_type=online&status=upcoming&status=open"


def fetch_devpost(limit: int = 25) -> List[RawListing]:
    headers = {"User-Agent": "FindHackathonsBot/0.1 (+https://findhackathons.com)"}
    with httpx.Client(timeout=45.0, headers=headers, follow_redirects=True) as client:
        response = client.get(DEVPOST_SEARCH)
        if response.status_code >= 400:
            print(f"[devpost] fetch failed: {response.status_code}")
            return []
        html = response.text

    # Pull hackathon URLs from the page
    urls = sorted(set(re.findall(r"https://[a-z0-9-]+\.devpost\.com/?", html)))
    listings: List[RawListing] = []
    for url in urls[:limit]:
        slug = url.rstrip("/").split("//")[-1].split(".")[0]
        title = slug.replace("-", " ").title()
        listings.append(
            RawListing(
                title=title,
                url=url,
                organizer="Devpost",
                source="devpost",
                raw_text=f"Devpost hackathon page candidate: {title}\nURL: {url}\n\nPage index excerpt:\n{html[:4000]}",
            )
        )

    if not listings:
        listings.append(
            RawListing(
                title="Devpost Open Hackathons",
                url=DEVPOST_SEARCH,
                organizer="Devpost",
                source="devpost",
                raw_text=html[:12000],
            )
        )
    return listings[:limit]