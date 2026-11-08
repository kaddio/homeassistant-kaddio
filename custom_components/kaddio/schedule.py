"""Busy-window logic (no Home Assistant imports, unit tested on its own)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from .models import KaddioEvent

KIND_BOOKING = "booking"  # individual patient/client meetings
KIND_SESSION = "session"  # group sessions
KIND_CAL = "cal"  # free-form calendar entries (lunch, meetings, ...)
ALL_KINDS = (KIND_BOOKING, KIND_SESSION, KIND_CAL)
DEFAULT_KINDS = (KIND_BOOKING, KIND_SESSION)


def counts(event: KaddioEvent, kinds: Iterable[str]) -> bool:
    return event.kind in kinds


def is_busy(
    events: Iterable[KaddioEvent],
    now: datetime,
    lead: timedelta,
    trail: timedelta,
    kinds: Iterable[str],
) -> KaddioEvent | None:
    """Return an event whose lead/trail window contains `now`.

    Windows of consecutive meetings overlap when the gap is shorter than
    lead + trail, so the result stays truthy across the gap and lights do not
    flicker off between back-to-back appointments.
    """
    kinds = tuple(kinds)
    for event in events:
        if counts(event, kinds) and event.start - lead <= now < event.end + trail:
            return event
    return None


def next_boundary(
    events: Iterable[KaddioEvent],
    now: datetime,
    lead: timedelta,
    trail: timedelta,
    kinds: Iterable[str],
) -> datetime | None:
    """Next instant at which the busy state could flip."""
    kinds = tuple(kinds)
    candidates = [
        moment
        for event in events
        if counts(event, kinds)
        for moment in (event.start - lead, event.end + trail)
        if moment > now
    ]
    return min(candidates) if candidates else None
