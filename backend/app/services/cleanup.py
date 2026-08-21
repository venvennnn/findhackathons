"""Helpers to deactivate known-bad / demo seed URLs that break the live feed."""

from __future__ import annotations

from typing import List

from sqlmodel import Session, col, select

from app.models.db import Listing, utcnow

# Demo seed URLs shipped before scrapers were reliable — many 404 in browsers.
BROKEN_URL_SUBSTRINGS = (
    "devpost.com/software/",
    "devfolio.co/hackathons/",
)

# Exact fake URLs from seed.py that never pointed at real open events.
BROKEN_EXACT_URLS = {
    "https://devfolio.co/hackathons/campuscode-india-beginner",
    "https://unstop.com/hackathons/freshers-ml-challenge",
    "https://www.kaggle.com/competitions/playground-tabular-forecasting",
    "https://devpost.com/software/ai-for-good-weekend",
    "https://devfolio.co/hackathons/web3-campus-mumbai",
    "https://www.kaggle.com/competitions/cv-defect-detection",
    "https://unstop.com/hackathons/mobile-app-ideathon",
    "https://devpost.com/software/llm-alignment-research",
    "https://devfolio.co/hackathons/game-jam-india-online",
    "https://unstop.com/hackathons/quant-fraud-detection",
}


def deactivate_broken_demo_listings(session: Session) -> List[str]:
    """Mark broken demo/seed listings inactive. Safe to run on every boot."""
    deactivated: List[str] = []
    rows = list(
        session.exec(select(Listing).where(Listing.is_active == True)).all()  # noqa: E712
    )
    now = utcnow()
    for listing in rows:
        url = (listing.url or "").strip()
        bad = url in BROKEN_EXACT_URLS or any(s in url for s in BROKEN_URL_SUBSTRINGS)
        if not bad:
            continue
        listing.is_active = False
        listing.updated_at = now
        session.add(listing)
        deactivated.append(url)
    if deactivated:
        session.commit()
    return deactivated
