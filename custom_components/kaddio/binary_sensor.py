"""Binary sensor that is on while something is happening in the calendar.

It turns on `lead_minutes` before an entry starts and stays on for
`trail_minutes` after it ends, which is what you usually want for lights
(warm up the room before the client arrives, tidy up after).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import KaddioConfigEntry
from .const import (
    CONF_EVENT_KINDS,
    CONF_LEAD_MINUTES,
    CONF_TRAIL_MINUTES,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TRAIL_MINUTES,
    DOMAIN,
)
from .coordinator import KaddioCoordinator
from .models import KaddioEvent
from .schedule import DEFAULT_KINDS, is_busy, next_boundary


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KaddioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    lead = timedelta(minutes=entry.options.get(CONF_LEAD_MINUTES, DEFAULT_LEAD_MINUTES))
    trail = timedelta(
        minutes=entry.options.get(CONF_TRAIL_MINUTES, DEFAULT_TRAIL_MINUTES)
    )
    kinds = tuple(entry.options.get(CONF_EVENT_KINDS, DEFAULT_KINDS))
    async_add_entities([KaddioBusySensor(entry.runtime_data, entry, lead, trail, kinds)])


class KaddioBusySensor(CoordinatorEntity[KaddioCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "busy"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self,
        coordinator: KaddioCoordinator,
        entry: KaddioConfigEntry,
        lead: timedelta,
        trail: timedelta,
        kinds: tuple[str, ...],
    ) -> None:
        super().__init__(coordinator)
        self._lead = lead
        self._trail = trail
        self._kinds = kinds
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._attr_unique_id = f"{entry.entry_id}-busy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Kaddio",
            "entry_type": "service",
        }

    def _active_event(self, now: datetime) -> KaddioEvent | None:
        return is_busy(self.coordinator.data or [], now, self._lead, self._trail, self._kinds)

    def _next_boundary(self, now: datetime) -> datetime | None:
        return next_boundary(
            self.coordinator.data or [], now, self._lead, self._trail, self._kinds
        )

    @property
    def is_on(self) -> bool:
        return self._active_event(dt_util.utcnow()) is not None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        now = dt_util.utcnow()
        active = self._active_event(now)
        upcoming = self.coordinator.next_event(now)
        return {
            "current_summary": active.summary if active else None,
            "next_start": upcoming.start.isoformat() if upcoming else None,
            "next_summary": upcoming.summary if upcoming else None,
        }

    @callback
    def _schedule_next_change(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        boundary = self._next_boundary(dt_util.utcnow())
        if boundary is not None:
            self._unsub_timer = async_track_point_in_time(
                self.hass, self._handle_boundary, boundary
            )

    @callback
    def _handle_boundary(self, _now: datetime) -> None:
        self._unsub_timer = None
        self.async_write_ha_state()
        self._schedule_next_change()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule_next_change()
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._schedule_next_change()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
