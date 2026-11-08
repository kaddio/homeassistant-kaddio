"""Config flow tests."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kaddio.const import (
    CONF_BASE_URL,
    CONF_LOCATION_ID,
    CONF_TOKEN,
    DOMAIN,
)

FETCH = "custom_components.kaddio.config_flow.async_fetch_locations"


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_full_flow_creates_entry(hass, mock_api):
    result = await _start(hass)
    assert result["type"] == FlowResultType.FORM and result["step_id"] == "user"

    with patch(FETCH, AsyncMock(return_value={"room1": "Köket"})):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BASE_URL: "clinic.kaddio.com", CONF_TOKEN: "  secret  "},
        )
    assert result["step_id"] == "location"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Köket", CONF_LOCATION_ID: "room1"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Köket"
    assert result["data"] == {
        CONF_BASE_URL: "https://clinic.kaddio.com",  # bare host accepted and normalised
        CONF_TOKEN: "secret",  # whitespace trimmed
        CONF_LOCATION_ID: "room1",
    }


async def test_invalid_token(hass):
    result = await _start(hass)
    with patch(FETCH, AsyncMock(side_effect=ConfigEntryAuthFailed("no"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BASE_URL: "https://clinic.kaddio.com", CONF_TOKEN: "bad"},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_TOKEN: "invalid_token"}


async def test_cannot_connect(hass):
    result = await _start(hass)
    with patch(FETCH, AsyncMock(side_effect=UpdateFailed("down"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BASE_URL: "https://clinic.kaddio.com", CONF_TOKEN: "t"},
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_rejects_non_https_address(hass):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: "http://clinic.kaddio.com", CONF_TOKEN: "t"},
    )
    assert result["errors"] == {CONF_BASE_URL: "invalid_base_url"}
