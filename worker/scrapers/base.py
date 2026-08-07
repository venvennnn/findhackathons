from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RawListing:
    title: str
    url: str
    organizer: str
    source: str
    raw_text: str
    deadline_hint: Optional[str] = None