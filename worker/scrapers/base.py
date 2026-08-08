from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RawListing:
    title: str
    url: str
    organizer: str
    source: str
    raw_text: str
    deadline_hint: Optional[str] = None
    # When a scraper already extracted structured fields (e.g. Kaggle API),
    # the pipeline can skip LLM enrichment.
    structured: Optional[Dict[str, Any]] = field(default=None)