"""Calendar platform: exposes the Kaddio feed as a Home Assistant calendar.

Because this is a real calendar entity, the built-in `calendar` automation
trigger (event start/end with an offset) works out of the box.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import KaddioConfigEntry
from .const import DOMAIN
from .coordinator import KaddioCoordinator
from .models import KaddioEvent


def _to_calendar_event(event: KaddioEvent) -> CalendarEvent:
    return CalendarEvent(
        start=event.start,
        end=event.end,
        summary=event.summary or "Kaddio",
        description=event.description or None,
        uid=event.uid,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KaddioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([KaddioCalendar(entry.runtime_data, entry)])


class KaddioCalendar(CoordinatorEntity[KaddioCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: KaddioCoordinator, entry: KaddioConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}-calendar"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Kaddio",
            "entry_type": "service",
        }

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
        current = self.coordinator.current_event(now)
        upcoming = current or self.coordinator.next_event(now)
        return _to_calendar_event(upcoming) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _to_calendar_event(e)
            for e in self.coordinator.events_between(start_date, end_date)
        ]
