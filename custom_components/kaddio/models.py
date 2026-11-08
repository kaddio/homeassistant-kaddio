"""Data model shared by the integration (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KaddioEvent:
    """A single calendar entry from the Kaddio API."""

    uid: str
    start: datetime
    end: datetime
    summary: str
    description: str
    kind: str  # "booking", "session" or "cal"
