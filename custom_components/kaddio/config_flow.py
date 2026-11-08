from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
from homeassistant.helpers.update_coordinator import UpdateFailed

from . import KaddioConfigEntry
from .client import KaddioClient
from .const import (
    ALL_LOCATIONS,
    ALL_LOCATIONS_LABEL,
    CONF_BASE_URL,
    CONF_EVENT_KINDS,
    CONF_LEAD_MINUTES,
    CONF_LOCATION_ID,
    CONF_TRAIL_MINUTES,
    DEFAULT_BUSY_KINDS,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TRAIL_MINUTES,
    DOMAIN,
    MAX_BUSY_MARGIN_MINUTES,
    PLACE_LABEL_SUFFIX,
)
from .models import EventKind, Locations


def normalize_base_url(raw_address: str) -> str | None:
    address = raw_address.strip()
    if "://" not in address:
        address = f"https://{address}"
    parsed = urlparse(address)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return f"https://{parsed.netloc}"


class KaddioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url = ""
        self._token = ""
        self._locations = Locations(rooms={}, places={})

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = normalize_base_url(user_input[CONF_BASE_URL])
            token = user_input[CONF_TOKEN].strip()
            if base_url is None:
                errors[CONF_BASE_URL] = "invalid_base_url"
            else:
                locations, errors = await self._async_load_locations(base_url, token)
                if not errors:
                    self._base_url, self._token, self._locations = base_url, token, locations
                    return await self.async_step_location()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_BASE_URL): str, vol.Required(CONF_TOKEN): str}
            ),
            errors=errors,
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            location_id = user_input[CONF_LOCATION_ID]
            await self.async_set_unique_id(f"{self._base_url}|{location_id}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_BASE_URL: self._base_url,
                    CONF_TOKEN: self._token,
                    CONF_LOCATION_ID: location_id,
                },
            )
        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Kaddio"): str,
                    vol.Required(CONF_LOCATION_ID, default=ALL_LOCATIONS): vol.In(
                        self._location_choices()
                    ),
                }
            ),
        )

    async def async_step_reauth(
        self, _entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            _, errors = await self._async_load_locations(entry.data[CONF_BASE_URL], token)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: KaddioConfigEntry) -> OptionsFlow:
        return KaddioOptionsFlow()

    async def _async_load_locations(
        self, base_url: str, token: str
    ) -> tuple[Locations, dict[str, str]]:
        client = KaddioClient(self.hass, base_url, token)
        try:
            return await client.async_list_locations(), {}
        except ConfigEntryAuthFailed:
            return Locations(rooms={}, places={}), {CONF_TOKEN: "invalid_token"}
        except UpdateFailed:
            return Locations(rooms={}, places={}), {"base": "cannot_connect"}

    def _location_choices(self) -> dict[str, str]:
        places = {
            place_id: f"{name}{PLACE_LABEL_SUFFIX}"
            for place_id, name in self._locations.places.items()
        }
        return {ALL_LOCATIONS: ALL_LOCATIONS_LABEL, **self._locations.rooms, **places}


class KaddioOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=self._options_schema(self.config_entry.options)
        )

    @staticmethod
    def _options_schema(options: Mapping[str, Any]) -> vol.Schema:
        minutes = vol.All(int, vol.Range(min=0, max=MAX_BUSY_MARGIN_MINUTES))
        kinds_selector = SelectSelector(
            SelectSelectorConfig(
                options=[kind.value for kind in EventKind],
                multiple=True,
                translation_key="event_kinds",
            )
        )
        return vol.Schema(
            {
                vol.Required(
                    CONF_EVENT_KINDS,
                    default=[
                        EventKind(kind).value
                        for kind in options.get(CONF_EVENT_KINDS, DEFAULT_BUSY_KINDS)
                    ],
                ): kinds_selector,
                vol.Required(
                    CONF_LEAD_MINUTES,
                    default=options.get(CONF_LEAD_MINUTES, DEFAULT_LEAD_MINUTES),
                ): minutes,
                vol.Required(
                    CONF_TRAIL_MINUTES,
                    default=options.get(CONF_TRAIL_MINUTES, DEFAULT_TRAIL_MINUTES),
                ): minutes,
            }
        )
