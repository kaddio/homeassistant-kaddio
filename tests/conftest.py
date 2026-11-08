"""Fixtures for the Home Assistant level tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kaddio.const import (
    CONF_BASE_URL,
    CONF_LOCATION_ID,
    CONF_TOKEN,
    DOMAIN,
)

BASE_URL = "https://clinic.kaddio.com"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/kaddio in every test."""
    yield


def iso(hour: int, minute: int = 0) -> str:
    return datetime(2026, 11, 9, hour, minute, tzinfo=timezone.utc).isoformat()


def locations_payload() -> dict:
    return {
        "data": {
            "findRooms": [{"_id": "room1", "name": "Köket", "deleted": False}],
            "findPlaces": [{"_id": "place1", "name": "Kaddio Support", "deleted": False}],
        }
    }


def events_payload(*rows: dict) -> dict:
    return {"data": {"findEventsIndexed": list(rows)}}


def booking(uid: str, start: str, end: str, name: str = "Samtal") -> dict:
    return {
        "_id": uid, "type": "booking", "start": start, "end": end,
        "title": None, "calNote": None, "placeId": "place1",
        "bookingType": {"name": name},
    }


def activity(uid: str, start: str, end: str, title: str = "Lunch") -> dict:
    return {
        "_id": uid, "type": "cal", "start": start, "end": end,
        "title": title, "calNote": None, "placeId": "place1", "bookingType": None,
    }


@pytest.fixture
def mock_api():
    """Patch the single HTTP function; tests set `mock_api.events`."""
    state = types_namespace()

    async def fake_post(hass, base_url, token, query, variables):
        if state.error is not None:
            raise state.error
        if "findEventsIndexed" not in query:
            return locations_payload()
        data = {**state.events["data"], "findRooms": state.rooms, "findPlaces": state.places}
        return {"data": data}

    with patch(
        "custom_components.kaddio.coordinator._post_graphql",
        new=AsyncMock(side_effect=fake_post),
    ):
        yield state


def types_namespace():
    class State:
        events = events_payload()
        error = None
        rooms = [{"_id": "room1", "deleted": False}]
        places = [{"_id": "place1", "deleted": False}]

    return State()


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Kaddio",
        unique_id=f"{BASE_URL}|room1",
        data={CONF_BASE_URL: BASE_URL, CONF_TOKEN: "x" * 45, CONF_LOCATION_ID: "room1"},
    )
