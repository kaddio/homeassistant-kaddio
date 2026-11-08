from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import KaddioClient
from .const import (
    ALL_LOCATIONS,
    CONF_BASE_URL,
    CONF_LOCATION_ID,
    DOMAIN,
    POLL_INTERVAL,
)
from .models import KaddioEvent

_LOGGER = logging.getLogger(__name__)


def location_missing_issue_id(entry_id: str) -> str:
    return f"location_missing_{entry_id}"


class KaddioCoordinator(DataUpdateCoordinator[list[KaddioEvent]]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=POLL_INTERVAL,
            config_entry=entry,
        )
        self._client = KaddioClient(
            hass, entry.data[CONF_BASE_URL], entry.data[CONF_TOKEN]
        )
        chosen_location = entry.data[CONF_LOCATION_ID]
        self._location_id = None if chosen_location == ALL_LOCATIONS else chosen_location

    async def _async_update_data(self) -> list[KaddioEvent]:
        snapshot = await self._client.async_fetch_events(self._location_id)
        self._sync_missing_location_issue(snapshot.location_exists)
        return snapshot.events

    def events_between(self, start: datetime, end: datetime) -> list[KaddioEvent]:
        return [
            event for event in self.data or [] if event.end > start and event.start < end
        ]

    def find_event_in_progress(self, now: datetime) -> KaddioEvent | None:
        for event in self.data or []:
            if event.start <= now < event.end:
                return event
        return None

    def find_next_event(self, now: datetime) -> KaddioEvent | None:
        for event in self.data or []:
            if event.start > now:
                return event
        return None

    def _sync_missing_location_issue(self, location_exists: bool) -> None:
        issue_id = location_missing_issue_id(self.config_entry.entry_id)
        if location_exists:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="location_missing",
            translation_placeholders={"name": self.config_entry.title},
        )
