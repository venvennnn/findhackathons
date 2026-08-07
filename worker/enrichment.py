"""LLM enrichment via instructor + OpenAI."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

from schemas import HackathonListing


ENRICHMENT_SYSTEM_PROMPT = """
You extract structured metadata from hackathon / data science competition listings.
Assign skill_floor using these proxies:
- beginner: starter notebooks/repos, student-only tags, dataset <1GB, standard tabular/classification
- advanced: no starter code, novel architectures, GPU/hardware demands, research criteria
- intermediate: everything in between
Use confidence=low when guessing. Prefer ISO country codes for eligibility.
""".strip()


def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def enrich_listing(raw_text: str, *, source_url: str, organizer_hint: str = "") -> HackathonListing:
    """Enrich unstructured listing text into a strict Pydantic model."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for enrichment")

    import instructor
    from openai import OpenAI

    client = instructor.from_openai(OpenAI(api_key=api_key))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    return client.chat.completions.create(
        model=model,
        response_model=HackathonListing,
        messages=[
            {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Source URL: {source_url}\n"
                    f"Organizer hint: {organizer_hint or 'unknown'}\n\n"
                    f"Listing text:\n{raw_text[:12000]}"
                ),
            },
        ],
        max_retries=2,
    )


def enrich_or_none(raw_text: str, *, source_url: str, organizer_hint: str = "") -> Optional[HackathonListing]:
    try:
        return enrich_listing(raw_text, source_url=source_url, organizer_hint=organizer_hint)
    except Exception as exc:  # noqa: BLE001
        print(f"[enrichment] failed for {source_url}: {exc}")
        return None