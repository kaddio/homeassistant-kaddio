"""Data coordinator that polls the Kaddio GraphQL API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ALL_LOCATIONS,
    CONF_BASE_URL,
    CONF_LOCATION_ID,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GRAPHQL_FUTURE_DAYS,
    GRAPHQL_PAST_DAYS,
)
from .gql import (
    EVENTS_QUERY,
    LOCATIONS_QUERY,
    GraphQLApiError,
    events_from_response,
    graphql_endpoint,
    locations_from_response,
)
from .models import KaddioEvent

_LOGGER = logging.getLogger(__name__)


async def _post_graphql(
    hass: HomeAssistant, base_url: str, token: str, query: str, variables: dict | None
) -> dict:
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            graphql_endpoint(base_url),
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": token},
            timeout=30,
        ) as response:
            if response.status in (401, 403):
                raise ConfigEntryAuthFailed("Kaddio rejected the API token")
            try:
                return await response.json(content_type=None)
            except ValueError as err:
                raise UpdateFailed(f"Unexpected answer from Kaddio (HTTP {response.status})") from err
    except ClientError as err:
        raise UpdateFailed(f"Could not reach Kaddio: {err}") from err


def _raise_for(err: GraphQLApiError):
    if err.is_auth_error:
        raise ConfigEntryAuthFailed(
            "Kaddio refused the token (needs an admin token and the API module)"
        ) from err
    raise UpdateFailed(str(err)) from err


async def async_fetch_locations(hass: HomeAssistant, base_url: str, token: str) -> dict[str, str]:
    """Return {location_id: name}. Raises ConfigEntryAuthFailed/UpdateFailed."""
    payload = await _post_graphql(hass, base_url, token, LOCATIONS_QUERY, None)
    try:
        return locations_from_response(payload)
    except GraphQLApiError as err:
        _raise_for(err)


async def async_fetch_graphql_events(
    hass: HomeAssistant, base_url: str, token: str, location_id: str | None
) -> list[KaddioEvent]:
    now = dt_util.utcnow()
    variables = {
        "start": (now - timedelta(days=GRAPHQL_PAST_DAYS)).isoformat(),
        "end": (now + timedelta(days=GRAPHQL_FUTURE_DAYS)).isoformat(),
        "locationId": location_id,
    }
    payload = await _post_graphql(hass, base_url, token, EVENTS_QUERY, variables)
    try:
        return events_from_response(payload)
    except GraphQLApiError as err:
        _raise_for(err)


class KaddioCoordinator(DataUpdateCoordinator[list[KaddioEvent]]):
    """Fetches events and offers simple lookups on them."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )

    async def _async_update_data(self) -> list[KaddioEvent]:
        data = self.config_entry.data
        location_id = data[CONF_LOCATION_ID]
        return await async_fetch_graphql_events(
            self.hass,
            data[CONF_BASE_URL],
            data[CONF_TOKEN],
            None if location_id == ALL_LOCATIONS else location_id,
        )

    def events_between(self, start: datetime, end: datetime) -> list[KaddioEvent]:
        return [e for e in self.data or [] if e.end > start and e.start < end]

    def current_event(self, now: datetime) -> KaddioEvent | None:
        for event in self.data or []:
            if event.start <= now < event.end:
                return event
        return None

    def next_event(self, now: datetime) -> KaddioEvent | None:
        for event in self.data or []:
            if event.start > now:
                return event
        return None
