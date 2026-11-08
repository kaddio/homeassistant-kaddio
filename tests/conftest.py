from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_TOKEN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kaddio.const import CONF_BASE_URL, CONF_LOCATION_ID, DOMAIN

BASE_URL = "https://clinic.kaddio.com"
ROOM_ID = "room1"
PLACE_ID = "place1"


@pytest.fixture(autouse=True)
def enable_kaddio_integration(enable_custom_integrations):
    yield


def timestamp(hour: int, minute: int = 0) -> str:
    return datetime(2026, 11, 9, hour, minute, tzinfo=timezone.utc).isoformat()


def events_payload(*rows: dict) -> dict:
    return {"data": {"findEventsIndexed": list(rows)}}


def client_meeting(uid: str, start: str, end: str, booking_type: str = "Samtal") -> dict:
    return {
        "_id": uid,
        "type": "booking",
        "start": start,
        "end": end,
        "title": None,
        "calNote": None,
        "placeId": PLACE_ID,
        "bookingType": {"name": booking_type},
    }


def calendar_entry(uid: str, start: str, end: str, title: str = "Lunch") -> dict:
    return {
        "_id": uid,
        "type": "cal",
        "start": start,
        "end": end,
        "title": title,
        "calNote": None,
        "placeId": PLACE_ID,
        "bookingType": None,
    }


@pytest.fixture
def kaddio_api():
    api = SimpleNamespace(
        events=events_payload(),
        rooms=[{"_id": ROOM_ID, "deleted": False}],
        places=[{"_id": PLACE_ID, "deleted": False}],
        error=None,
    )

    async def answer(query: str, variables: dict) -> dict:
        if api.error is not None:
            raise api.error
        data = {**api.events["data"], "findRooms": api.rooms, "findPlaces": api.places}
        return {"data": data}

    with patch(
        "custom_components.kaddio.client.KaddioClient._async_post",
        new=AsyncMock(side_effect=answer),
    ):
        yield api


@pytest.fixture
def room_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Kaddio",
        unique_id=f"{BASE_URL}|{ROOM_ID}",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_TOKEN: "x" * 45,
            CONF_LOCATION_ID: ROOM_ID,
        },
    )
