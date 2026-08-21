"""LLM enrichment via instructor + Claude (Anthropic), plus deterministic mapping.

Auth still uses the env var name OPENAI_API_KEY (holds an Anthropic API key).
Optional OPENAI_MODEL overrides the Claude model id.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from schemas import (
    ConfidenceLevel,
    DomainCategory,
    Eligibility,
    HackathonListing,
    SkillLevel,
)


ENRICHMENT_SYSTEM_PROMPT = """
You extract structured metadata from hackathon / data science competition listings.
Assign skill_floor using these proxies:
- beginner: starter notebooks/repos, student-only tags, dataset <1GB, standard tabular/classification
- advanced: no starter code, novel architectures, GPU/hardware demands, research criteria
- intermediate: everything in between
Use confidence=low when guessing. Prefer ISO country codes for eligibility.
""".strip()

# Env var names stay OPENAI_* for compatibility; values are Anthropic/Claude.
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def enrich_listing(raw_text: str, *, source_url: str, organizer_hint: str = "") -> HackathonListing:
    """Enrich unstructured listing text into a strict Pydantic model via Claude."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for enrichment "
            "(put your Anthropic/Claude API key in this env var)"
        )

    import instructor
    from anthropic import Anthropic

    client = instructor.from_anthropic(Anthropic(api_key=api_key))
    model = os.getenv("OPENAI_MODEL", DEFAULT_CLAUDE_MODEL)

    return client.messages.create(
        model=model,
        max_tokens=2048,
        max_retries=2,
        response_model=HackathonListing,
        system=ENRICHMENT_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Source URL: {source_url}\n"
                    f"Organizer hint: {organizer_hint or 'unknown'}\n\n"
                    f"Listing text:\n{raw_text[:12000]}"
                ),
            },
        ],
    )


def enrich_or_none(
    raw_text: str,
    *,
    source_url: str,
    organizer_hint: str = "",
    structured: Optional[Dict[str, Any]] = None,
) -> Optional[HackathonListing]:
    if structured:
        try:
            return listing_from_structured(structured, raw_text=raw_text)
        except Exception as exc:  # noqa: BLE001
            print(f"[enrichment] structured map failed for {source_url}: {exc}")

    try:
        return enrich_listing(raw_text, source_url=source_url, organizer_hint=organizer_hint)
    except Exception as exc:  # noqa: BLE001
        print(f"[enrichment] failed for {source_url}: {exc}")
        return None


def listing_from_structured(
    structured: Dict[str, Any],
    *,
    raw_text: str = "",
) -> HackathonListing:
    """Deterministic HackathonListing from scraper-provided structured fields."""
    title = str(structured.get("title") or "Untitled")
    url = str(structured.get("url") or "")
    organizer = str(structured.get("organizer") or "Kaggle")
    category = str(structured.get("category") or "")
    description = str(structured.get("description") or "")
    prize_pool: Optional[int] = None
    prize = structured.get("prize_pool_usd")
    if prize not in (None, "", 0, "0"):
        try:
            prize_pool = int(prize)
            if prize_pool <= 0:
                prize_pool = None
        except (TypeError, ValueError):
            prize_pool = None

    skill_hint = str(structured.get("skill_floor") or "").lower()
    if skill_hint in {s.value for s in SkillLevel}:
        skill = SkillLevel(skill_hint)
        reasoning = str(
            structured.get("skill_floor_reasoning")
            or _skill_reasoning(skill, category, bool(structured.get("has_starter_code")))
        )
    else:
        skill = _infer_skill(category, bool(structured.get("has_starter_code")), description, title)
        reasoning = _skill_reasoning(skill, category, bool(structured.get("has_starter_code")))

    raw_domains = structured.get("domains") or []
    domains: List[DomainCategory] = []
    if isinstance(raw_domains, list) and raw_domains:
        valid = {d.value for d in DomainCategory}
        for item in raw_domains:
            value = getattr(item, "value", item)
            if str(value) in valid:
                domains.append(DomainCategory(str(value)))
    if not domains:
        domains = _infer_domains(title, description, category)
    deadline = _parse_deadline(structured.get("deadline_utc"))

    team_size = structured.get("team_size_max")
    try:
        team_size_max = int(team_size) if team_size is not None else None
    except (TypeError, ValueError):
        team_size_max = None

    has_starter = bool(structured.get("has_starter_code"))
    conf_raw = str(structured.get("confidence") or "medium").lower()
    confidence = (
        ConfidenceLevel(conf_raw)
        if conf_raw in {c.value for c in ConfidenceLevel}
        else ConfidenceLevel.medium
    )

    return HackathonListing(
        title=title,
        organizer=organizer,
        url=url,
        deadline_utc=deadline,
        domain=domains,
        skill_floor=skill,
        skill_floor_reasoning=reasoning,
        eligibility=Eligibility(
            students_only=bool(structured.get("students_only", False)),
            country_restrictions=[],
            team_size_max=team_size_max,
            requires_travel=bool(structured.get("requires_travel", False)),
        ),
        prize_pool_usd=prize_pool if prize_pool and prize_pool > 0 else None,
        has_starter_code=has_starter,
        confidence=confidence,
    )


def _infer_skill(
    category: str,
    has_starter: bool,
    description: str,
    title: str,
) -> SkillLevel:
    cat = category.lower().replace(" ", "")
    blob = f"{title} {description}".lower()
    if cat in {"gettingstarted", "playground"} or "getting started" in category.lower():
        return SkillLevel.beginner
    if cat in {"research", "masters"} or any(
        word in blob for word in ("research", "novel", "foundation model", "llm agent")
    ):
        return SkillLevel.advanced if not has_starter else SkillLevel.intermediate
    if has_starter:
        return SkillLevel.beginner
    if cat in {"featured", "recruitment"}:
        return SkillLevel.intermediate
    return SkillLevel.intermediate


def _skill_reasoning(skill: SkillLevel, category: str, has_starter: bool) -> str:
    bits = [f"Kaggle {category or 'competition'}"]
    if has_starter:
        bits.append("public notebooks/scripts available")
    bits.append(f"mapped to {skill.value}")
    return "; ".join(bits) + "."


def _infer_domains(title: str, description: str, category: str) -> List[DomainCategory]:
    blob = f"{title} {description} {category}".lower()
    found: List[DomainCategory] = []
    rules = [
        (DomainCategory.nlp, r"\b(nlp|language|llm|text|speech|translation|prompt)\b"),
        (DomainCategory.cv, r"\b(vision|image|cv|segmentation|detection|satellite|photo)\b"),
        (DomainCategory.tabular, r"\b(tabular|forecast|time.?series|credit|churn|classification|regression)\b"),
        (DomainCategory.hardware, r"\b(hardware|robot|iot|embedded)\b"),
        (DomainCategory.game_dev, r"\b(game|rl|reinforcement)\b"),
        (DomainCategory.web_dev, r"\b(web|dashboard|app)\b"),
    ]
    for domain, pattern in rules:
        if re.search(pattern, blob):
            found.append(domain)
    if not found:
        # Default DS competitions to tabular/other.
        if "playground" in category.lower() or "getting" in category.lower():
            found = [DomainCategory.tabular]
        else:
            found = [DomainCategory.other]
    return found


def _parse_deadline(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
