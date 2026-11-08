"""The Kaddio integration: use a Kaddio calendar to drive Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, PLATFORMS
from .coordinator import KaddioCoordinator, location_issue_id

type KaddioConfigEntry = ConfigEntry[KaddioCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: KaddioConfigEntry) -> bool:
    coordinator = KaddioCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def _async_reload_on_options(hass: HomeAssistant, entry: KaddioConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: KaddioConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: KaddioConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, location_issue_id(entry.entry_id))
