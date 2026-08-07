"""Devfolio ingestion — India-first campus hackathon source."""

from __future__ import annotations

import re
from typing import List

import httpx

from scrapers.base import RawListing

DEVFOLIO_URL = "https://devfolio.co/hackathons"


def fetch_devfolio(limit: int = 25) -> List[RawListing]:
    headers = {"User-Agent": "FindHackathonsBot/0.1 (+https://findhackathons.com)"}
    with httpx.Client(timeout=45.0, headers=headers, follow_redirects=True) as client:
        response = client.get(DEVFOLIO_URL)
        if response.status_code >= 400:
            print(f"[devfolio] fetch failed: {response.status_code}")
            return []
        html = response.text

    hrefs = re.findall(r'href="([^"]*hackathon[^"]*)"', html, flags=re.I)
    urls: List[str] = []
    for href in hrefs:
        if href.startswith("http"):
            urls.append(href.split("?")[0])
        elif href.startswith("/"):
            urls.append(f"https://devfolio.co{href.split('?')[0]}")
    urls = sorted(set(urls))[:limit]

    listings: List[RawListing] = []
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title() or "Devfolio Hackathon"
        listings.append(
            RawListing(
                title=title,
                url=url,
                organizer="Devfolio",
                source="devfolio",
                raw_text=(
                    f"Devfolio campus/hackathon listing: {title}\n"
                    f"URL: {url}\nRegion focus: India\n\nIndex excerpt:\n{html[:5000]}"
                ),
            )
        )

    if not listings:
        listings.append(
            RawListing(
                title="Devfolio Hackathons",
                url=DEVFOLIO_URL,
                organizer="Devfolio",
                source="devfolio",
                raw_text=html[:12000],
            )
        )
    return listings[:limit]