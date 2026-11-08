from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kaddio.const import (
    ALL_LOCATIONS,
    CONF_BASE_URL,
    CONF_LOCATION_ID,
    DOMAIN,
)
from custom_components.kaddio.models import Locations

LIST_LOCATIONS = "custom_components.kaddio.client.KaddioClient.async_list_locations"
KITCHEN_AND_SUPPORT = Locations(rooms={"room1": "Kitchen"}, places={"place1": "Kaddio Support"})


async def start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def submit_credentials(hass, flow_id, base_url="https://clinic.kaddio.com", token="token"):
    return await hass.config_entries.flow.async_configure(
        flow_id, {CONF_BASE_URL: base_url, CONF_TOKEN: token}
    )


async def test_full_flow_creates_an_entry_for_the_chosen_room(hass):
    flow = await start_flow(hass)
    assert flow["step_id"] == "user"

    with patch(LIST_LOCATIONS, AsyncMock(return_value=KITCHEN_AND_SUPPORT)):
        flow = await submit_credentials(hass, flow["flow_id"], "clinic.kaddio.com", "  secret  ")
    assert flow["step_id"] == "location"

    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_NAME: "Kitchen", CONF_LOCATION_ID: "room1"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen"
    assert result["data"] == {
        CONF_BASE_URL: "https://clinic.kaddio.com",
        CONF_TOKEN: "secret",
        CONF_LOCATION_ID: "room1",
    }


async def test_location_choices_list_everything_then_rooms_then_places(hass):
    flow = await start_flow(hass)
    with patch(LIST_LOCATIONS, AsyncMock(return_value=KITCHEN_AND_SUPPORT)):
        flow = await submit_credentials(hass, flow["flow_id"])

    choices = flow["data_schema"].schema[CONF_LOCATION_ID].container

    assert list(choices) == [ALL_LOCATIONS, "room1", "place1"]
    assert choices["place1"] == "Kaddio Support (place)"


async def test_rejected_token_is_reported_on_the_token_field(hass):
    flow = await start_flow(hass)

    with patch(LIST_LOCATIONS, AsyncMock(side_effect=ConfigEntryAuthFailed("no"))):
        result = await submit_credentials(hass, flow["flow_id"], token="bad")

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_TOKEN: "invalid_token"}


async def test_unreachable_kaddio_is_reported_as_connection_error(hass):
    flow = await start_flow(hass)

    with patch(LIST_LOCATIONS, AsyncMock(side_effect=UpdateFailed("down"))):
        result = await submit_credentials(hass, flow["flow_id"])

    assert result["errors"] == {"base": "cannot_connect"}


async def test_plain_http_address_is_rejected(hass):
    flow = await start_flow(hass)

    result = await submit_credentials(hass, flow["flow_id"], base_url="http://clinic.kaddio.com")

    assert result["errors"] == {CONF_BASE_URL: "invalid_base_url"}
