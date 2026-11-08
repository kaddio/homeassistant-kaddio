from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from .const import EVENTS_WINDOW_FUTURE, EVENTS_WINDOW_PAST
from .graphql_api import (
    EVENTS_QUERY,
    LOCATIONS_QUERY,
    GraphQLApiError,
    chosen_location_exists,
    graphql_endpoint,
    parse_events,
    parse_locations,
)
from .models import KaddioEvent, Locations

REQUEST_TIMEOUT = ClientTimeout(total=30)
TOKEN_REJECTED_STATUSES = (401, 403)


@dataclass(frozen=True)
class EventsSnapshot:
    events: list[KaddioEvent]
    location_exists: bool


class KaddioClient:
    def __init__(self, hass: HomeAssistant, base_url: str, token: str) -> None:
        self._session = async_get_clientsession(hass)
        self._endpoint = graphql_endpoint(base_url)
        self._token = token

    async def async_list_locations(self) -> Locations:
        payload = await self._async_post(LOCATIONS_QUERY, {})
        try:
            return parse_locations(payload)
        except GraphQLApiError as error:
            raise _to_home_assistant_error(error) from error

    async def async_fetch_events(self, location_id: str | None) -> EventsSnapshot:
        now = dt_util.utcnow()
        variables = {
            "start": (now - EVENTS_WINDOW_PAST).isoformat(),
            "end": (now + EVENTS_WINDOW_FUTURE).isoformat(),
            "locationId": location_id,
        }
        payload = await self._async_post(EVENTS_QUERY, variables)
        try:
            return EventsSnapshot(
                events=parse_events(payload),
                location_exists=chosen_location_exists(payload, location_id),
            )
        except GraphQLApiError as error:
            raise _to_home_assistant_error(error) from error

    async def _async_post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.post(
                self._endpoint,
                json={"query": query, "variables": variables},
                headers={"Authorization": self._token},
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status in TOKEN_REJECTED_STATUSES:
                    raise ConfigEntryAuthFailed("Kaddio rejected the API token")
                return await response.json(content_type=None)
        except ClientError as error:
            raise UpdateFailed(f"Could not reach Kaddio: {error}") from error
        except ValueError as error:
            raise UpdateFailed("Kaddio sent an unreadable answer") from error


def _to_home_assistant_error(error: GraphQLApiError) -> Exception:
    if error.is_auth_error:
        return ConfigEntryAuthFailed(
            "Kaddio refused the token: it must belong to an administrator "
            "at an organization with the API module"
        )
    return UpdateFailed(str(error))
