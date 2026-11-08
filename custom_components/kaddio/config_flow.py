"""Config flow: Kaddio address + admin API token, then pick a room."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
from homeassistant.helpers.update_coordinator import UpdateFailed

from . import KaddioConfigEntry
from .const import (
    ALL_PLACES,
    CONF_BASE_URL,
    CONF_EVENT_KINDS,
    CONF_LEAD_MINUTES,
    CONF_PLACE_ID,
    CONF_TOKEN,
    CONF_TRAIL_MINUTES,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TRAIL_MINUTES,
    DOMAIN,
)
from .coordinator import async_fetch_places
from .schedule import ALL_KINDS, DEFAULT_KINDS


def _normalize_base_url(raw: str) -> str | None:
    parsed = urlparse(raw.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return f"https://{parsed.netloc}"


class KaddioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str | None = None
        self._token: str | None = None
        self._places: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = _normalize_base_url(user_input[CONF_BASE_URL])
            if base_url is None:
                errors[CONF_BASE_URL] = "invalid_base_url"
            else:
                token = user_input[CONF_TOKEN].strip()
                try:
                    places = await async_fetch_places(self.hass, base_url, token)
                except ConfigEntryAuthFailed:
                    errors[CONF_TOKEN] = "invalid_token"
                except UpdateFailed:
                    errors["base"] = "cannot_connect"
                else:
                    self._base_url, self._token, self._places = base_url, token, places
                    return await self.async_step_place()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_BASE_URL): str, vol.Required(CONF_TOKEN): str}
            ),
            errors=errors,
        )

    async def async_step_place(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            place_id = user_input[CONF_PLACE_ID]
            await self.async_set_unique_id(f"{self._base_url}|{place_id}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    CONF_BASE_URL: self._base_url,
                    CONF_TOKEN: self._token,
                    CONF_PLACE_ID: place_id,
                },
            )
        options = {ALL_PLACES: "All rooms / places"} | self._places
        return self.async_show_form(
            step_id="place",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default="Kaddio"): str,
                    vol.Required(CONF_PLACE_ID, default=ALL_PLACES): vol.In(options),
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            try:
                await async_fetch_places(self.hass, entry.data[CONF_BASE_URL], token)
            except ConfigEntryAuthFailed:
                errors[CONF_TOKEN] = "invalid_token"
            except UpdateFailed:
                errors["base"] = "cannot_connect"
            else:
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


class KaddioOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EVENT_KINDS,
                        default=list(options.get(CONF_EVENT_KINDS, DEFAULT_KINDS)),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(ALL_KINDS),
                            multiple=True,
                            translation_key="event_kinds",
                        )
                    ),
                    vol.Required(
                        CONF_LEAD_MINUTES,
                        default=options.get(CONF_LEAD_MINUTES, DEFAULT_LEAD_MINUTES),
                    ): vol.All(int, vol.Range(min=0, max=240)),
                    vol.Required(
                        CONF_TRAIL_MINUTES,
                        default=options.get(CONF_TRAIL_MINUTES, DEFAULT_TRAIL_MINUTES),
                    ): vol.All(int, vol.Range(min=0, max=240)),
                }
            ),
        )
