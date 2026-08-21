"""Probabilistic ranking helpers for match shortlists."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from app.core.config import get_settings
from app.models.db import Listing
from app.models.enums import SkillLevel
from app.models.schemas import MatchRequest


@dataclass
class RankedListing:
    listing: Listing
    fit_reason: str
    score: float


def _domain_overlap(listing: Listing, request: MatchRequest) -> int:
    if not request.domains:
        return 0
    wanted = {d.value for d in request.domains}
    return len(wanted.intersection(set(listing.domains or [])))


def rank_listings_heuristic(
    listings: List[Listing],
    request: MatchRequest,
) -> List[RankedListing]:
    ranked: List[RankedListing] = []
    skill = request.skill_level or SkillLevel.beginner

    for listing in listings:
        score = 0.0
        overlap = _domain_overlap(listing, request)
        score += overlap * 3.0

        if listing.skill_floor == skill:
            score += 2.0
        elif listing.skill_floor == SkillLevel.beginner and skill != SkillLevel.beginner:
            score += 0.5

        if request.prefer_starter_code and listing.has_starter_code:
            score += 2.5

        if listing.prize_pool_usd:
            score += min(listing.prize_pool_usd / 5000.0, 2.0)

        if listing.confidence.value == "high":
            score += 0.5

        parts: List[str] = []
        if overlap:
            parts.append(f"matches your {', '.join(sorted(set(listing.domains or []) & {d.value for d in request.domains}))} focus")
        if listing.has_starter_code and (request.prefer_starter_code or skill == SkillLevel.beginner):
            parts.append("includes starter code so you can finish faster")
        if listing.skill_floor == SkillLevel.beginner and skill == SkillLevel.beginner:
            parts.append("marked beginner-friendly")
        if not parts:
            parts.append("is still open and fits your eligibility filters")

        reason = "Selected because this challenge " + " and ".join(parts) + "."
        ranked.append(RankedListing(listing=listing, fit_reason=reason, score=score))

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def rank_listings_with_llm(
    listings: List[Listing],
    request: MatchRequest,
) -> List[RankedListing]:
    """Rank with Claude when OPENAI_API_KEY is set (Anthropic key); else heuristic."""
    settings = get_settings()
    if not settings.openai_api_key:
        return rank_listings_heuristic(listings, request)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.openai_api_key)
        payload = [
            {
                "id": listing.id,
                "title": listing.title,
                "domains": listing.domains,
                "skill_floor": listing.skill_floor.value,
                "has_starter_code": listing.has_starter_code,
                "students_only": listing.students_only,
                "prize_pool_usd": listing.prize_pool_usd,
                "skill_floor_reasoning": listing.skill_floor_reasoning,
            }
            for listing in listings
        ]
        profile = {
            "skill_level": (request.skill_level or SkillLevel.beginner).value,
            "domains": [d.value for d in (request.domains or [])],
            "free_text": request.free_text,
            "prefer_starter_code": request.prefer_starter_code,
            "country": request.country,
        }

        model = settings.openai_model or "claude-haiku-4-5-20251001"
        # If someone still has an old gpt-* default, remap to Claude.
        if model.startswith("gpt-"):
            model = "claude-haiku-4-5-20251001"

        message = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0.2,
            system=(
                "You rank hackathons for a developer. Return JSON only: "
                '{"rankings":[{"id":"...","fit_reason":"one sentence","score":0-100}]} '
                "for the top 5 best fits only. Be specific and beginner-friendly when relevant."
            ),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps({"profile": profile, "candidates": payload}),
                },
            ],
        )
        content = ""
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                content += text
        content = content.strip() or "{}"
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        by_id = {listing.id: listing for listing in listings}
        ranked: List[RankedListing] = []
        for item in data.get("rankings", []):
            listing = by_id.get(item.get("id"))
            if not listing:
                continue
            ranked.append(
                RankedListing(
                    listing=listing,
                    fit_reason=item.get("fit_reason")
                    or "Selected because it matches your profile.",
                    score=float(item.get("score", 0)),
                )
            )
        if ranked:
            ranked.sort(key=lambda item: item.score, reverse=True)
            return ranked
    except Exception:
        pass

    return rank_listings_heuristic(listings, request)