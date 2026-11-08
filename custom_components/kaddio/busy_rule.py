from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import EventKind, KaddioEvent


@dataclass(frozen=True)
class BusyRule:
    lead: timedelta
    trail: timedelta
    kinds: frozenset[EventKind]

    def find_active_event(
        self, events: Iterable[KaddioEvent], now: datetime
    ) -> KaddioEvent | None:
        for event in self._counted(events):
            if event.start - self.lead <= now < event.end + self.trail:
                return event
        return None

    def find_next_event(
        self, events: Iterable[KaddioEvent], now: datetime
    ) -> KaddioEvent | None:
        for event in self._counted(events):
            if event.start > now:
                return event
        return None

    def next_state_change(
        self, events: Iterable[KaddioEvent], now: datetime
    ) -> datetime | None:
        upcoming_changes = [
            moment
            for event in self._counted(events)
            for moment in (event.start - self.lead, event.end + self.trail)
            if moment > now
        ]
        return min(upcoming_changes, default=None)

    def _counted(self, events: Iterable[KaddioEvent]) -> Iterator[KaddioEvent]:
        return (event for event in events if event.kind in self.kinds)
