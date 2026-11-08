from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import KaddioConfigEntry
from .coordinator import KaddioCoordinator
from .entity import KaddioEntity
from .models import KaddioEvent

PARALLEL_UPDATES = 0

FALLBACK_SUMMARY = "Kaddio"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KaddioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([KaddioCalendar(entry.runtime_data)])


def to_calendar_event(event: KaddioEvent) -> CalendarEvent:
    return CalendarEvent(
        start=event.start,
        end=event.end,
        summary=event.summary or FALLBACK_SUMMARY,
        description=event.description or None,
        uid=event.uid,
    )


class KaddioCalendar(KaddioEntity, CalendarEntity):
    _attr_name = None

    def __init__(self, coordinator: KaddioCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
        relevant = self.coordinator.find_event_in_progress(
            now
        ) or self.coordinator.find_next_event(now)
        return to_calendar_event(relevant) if relevant else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            to_calendar_event(event)
            for event in self.coordinator.events_between(start_date, end_date)
        ]
