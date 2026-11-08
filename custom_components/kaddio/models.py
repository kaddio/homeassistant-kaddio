from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventKind(str, Enum):
    CLIENT_MEETING = "booking"
    GROUP_SESSION = "session"
    CALENDAR_ENTRY = "cal"


@dataclass(frozen=True)
class KaddioEvent:
    uid: str
    start: datetime
    end: datetime
    summary: str
    description: str
    kind: EventKind


@dataclass(frozen=True)
class Locations:
    rooms: dict[str, str]
    places: dict[str, str]
