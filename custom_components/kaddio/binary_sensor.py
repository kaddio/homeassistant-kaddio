from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from . import KaddioConfigEntry
from .busy_rule import BusyRule
from .const import (
    CONF_EVENT_KINDS,
    CONF_LEAD_MINUTES,
    CONF_TRAIL_MINUTES,
    DEFAULT_BUSY_KINDS,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TRAIL_MINUTES,
)
from .coordinator import KaddioCoordinator
from .entity import KaddioEntity
from .models import EventKind, KaddioEvent

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KaddioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    rule = busy_rule_from_options(entry.options)
    async_add_entities([KaddioBusySensor(entry.runtime_data, rule)])


def busy_rule_from_options(options: Mapping[str, Any]) -> BusyRule:
    return BusyRule(
        lead=timedelta(minutes=options.get(CONF_LEAD_MINUTES, DEFAULT_LEAD_MINUTES)),
        trail=timedelta(minutes=options.get(CONF_TRAIL_MINUTES, DEFAULT_TRAIL_MINUTES)),
        kinds=frozenset(
            EventKind(kind) for kind in options.get(CONF_EVENT_KINDS, DEFAULT_BUSY_KINDS)
        ),
    )


class KaddioBusySensor(KaddioEntity, BinarySensorEntity):
    _attr_translation_key = "busy"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, coordinator: KaddioCoordinator, rule: BusyRule) -> None:
        super().__init__(coordinator, "busy")
        self._rule = rule
        self._cancel_state_change_timer: CALLBACK_TYPE | None = None

    @property
    def is_on(self) -> bool:
        return self._rule.find_active_event(self._events, dt_util.utcnow()) is not None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        now = dt_util.utcnow()
        active = self._rule.find_active_event(self._events, now)
        upcoming = self._rule.find_next_event(self._events, now)
        return {
            "current_summary": active.summary if active else None,
            "next_start": upcoming.start.isoformat() if upcoming else None,
            "next_summary": upcoming.summary if upcoming else None,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._schedule_next_state_change()

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_scheduled_state_change()

    @property
    def _events(self) -> list[KaddioEvent]:
        return self.coordinator.data or []

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule_next_state_change()
        super()._handle_coordinator_update()

    @callback
    def _schedule_next_state_change(self) -> None:
        self._cancel_scheduled_state_change()
        change_at = self._rule.next_state_change(self._events, dt_util.utcnow())
        if change_at is not None:
            self._cancel_state_change_timer = async_track_point_in_time(
                self.hass, self._handle_state_change_due, change_at
            )

    @callback
    def _handle_state_change_due(self, _now: datetime) -> None:
        self._cancel_state_change_timer = None
        self.async_write_ha_state()
        self._schedule_next_state_change()

    def _cancel_scheduled_state_change(self) -> None:
        if self._cancel_state_change_timer:
            self._cancel_state_change_timer()
            self._cancel_state_change_timer = None
