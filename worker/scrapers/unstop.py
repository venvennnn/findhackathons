"""Unstop DOM scraping helpers.

The Modal worker prefers Playwright for JS-rendered Unstop pages.
This module also exposes an httpx fallback for local dry-runs.
"""

from __future__ import annotations

import re
from typing import List

import httpx

from scrapers.base import RawListing

UNSTOP_URL = "https://unstop.com/hackathons"


def fetch_unstop(limit: int = 25) -> List[RawListing]:
    headers = {"User-Agent": "FindHackathonsBot/0.1 (+https://findhackathons.com)"}
    with httpx.Client(timeout=45.0, headers=headers, follow_redirects=True) as client:
        response = client.get(UNSTOP_URL)
        if response.status_code >= 400:
            print(f"[unstop] fetch failed: {response.status_code}")
            return []
        html = response.text

    hrefs = re.findall(r'href="([^"]*(?:hackathon|competition)[^"]*)"', html, flags=re.I)
    urls: List[str] = []
    for href in hrefs:
        if href.startswith("http"):
            urls.append(href.split("?")[0])
        elif href.startswith("/"):
            urls.append(f"https://unstop.com{href.split('?')[0]}")
    urls = sorted(set(urls))[:limit]

    listings: List[RawListing] = []
    for url in urls:
        slug = url.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title() or "Unstop Hackathon"
        listings.append(
            RawListing(
                title=title,
                url=url,
                organizer="Unstop",
                source="unstop",
                raw_text=(
                    f"Unstop hackathon/competition: {title}\n"
                    f"URL: {url}\nPrimary market: India campus\n\nExcerpt:\n{html[:5000]}"
                ),
            )
        )

    if not listings:
        listings.append(
            RawListing(
                title="Unstop Hackathons",
                url=UNSTOP_URL,
                organizer="Unstop",
                source="unstop",
                raw_text=html[:12000],
            )
        )
    return listings[:limit]


async def fetch_unstop_playwright(limit: int = 25) -> List[RawListing]:
    """Playwright path for Modal containers with Chromium."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(UNSTOP_URL, wait_until="networkidle", timeout=60000)
        html = await page.content()
        cards = await page.eval_on_selector_all(
            "a[href*='hackathon'], a[href*='competition']",
            "els => els.slice(0, 40).map(e => ({href: e.href, text: (e.innerText || '').trim()}))",
        )
        await browser.close()

    listings: List[RawListing] = []
    seen = set()
    for card in cards:
        href = (card.get("href") or "").split("?")[0]
        if not href or href in seen:
            continue
        seen.add(href)
        title = (card.get("text") or "").split("\n")[0].strip() or href.rstrip("/").split("/")[-1]
        listings.append(
            RawListing(
                title=title[:160],
                url=href,
                organizer="Unstop",
                source="unstop",
                raw_text=f"Title: {title}\nURL: {href}\n\nPage HTML excerpt:\n{html[:8000]}",
            )
        )
        if len(listings) >= limit:
            break

    return listings or fetch_unstop(limit=limit)