"""Setup, busy-sensor timing, options and failure handling, inside Home Assistant."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.kaddio.const import (
    CONF_LEAD_MINUTES,
    CONF_TRAIL_MINUTES,
    DOMAIN,
)

from .conftest import activity, booking, events_payload, iso


def _entity_id(hass, entry, platform, suffix):
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}-{suffix}"
    )


async def _advance(hass, freezer, when):
    freezer.move_to(when)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()


async def _setup(hass, entry, freezer, now="2026-11-09T08:00:00+00:00"):
    freezer.move_to(now)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_calendar_and_busy_sensor(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(booking("b1", iso(10), iso(10, 45)))
    await _setup(hass, config_entry, freezer)

    assert config_entry.state is ConfigEntryState.LOADED
    assert _entity_id(hass, config_entry, "calendar", "calendar")
    busy = _entity_id(hass, config_entry, "binary_sensor", "busy")
    assert hass.states.get(busy).state == "off"


async def test_busy_follows_lead_and_trail(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(booking("b1", iso(10), iso(10, 45)))
    await _setup(hass, config_entry, freezer)
    busy = _entity_id(hass, config_entry, "binary_sensor", "busy")

    await _advance(hass, freezer, "2026-11-09T09:54:00+00:00")
    assert hass.states.get(busy).state == "off"  # default lead is 5 min
    await _advance(hass, freezer, "2026-11-09T09:56:00+00:00")
    assert hass.states.get(busy).state == "on"
    await _advance(hass, freezer, "2026-11-09T10:49:00+00:00")
    assert hass.states.get(busy).state == "on"  # trail
    await _advance(hass, freezer, "2026-11-09T10:51:00+00:00")
    assert hass.states.get(busy).state == "off"


async def test_back_to_back_stays_on(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(
        booking("b1", iso(10), iso(10, 30)), booking("b2", iso(10, 35), iso(11))
    )
    await _setup(hass, config_entry, freezer)
    busy = _entity_id(hass, config_entry, "binary_sensor", "busy")

    await _advance(hass, freezer, "2026-11-09T10:32:00+00:00")  # in the gap
    assert hass.states.get(busy).state == "on"


async def test_activities_ignored_by_default(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(activity("a1", iso(10), iso(11)))
    await _setup(hass, config_entry, freezer)
    busy = _entity_id(hass, config_entry, "binary_sensor", "busy")

    await _advance(hass, freezer, "2026-11-09T10:30:00+00:00")
    assert hass.states.get(busy).state == "off"


async def test_options_change_timing(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(booking("b1", iso(10), iso(10, 45)))
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kaddio",
        unique_id=config_entry.unique_id,
        data=dict(config_entry.data),
        options={CONF_LEAD_MINUTES: 1, CONF_TRAIL_MINUTES: 1},
    )
    await _setup(hass, config_entry, freezer)
    busy = _entity_id(hass, config_entry, "binary_sensor", "busy")

    await _advance(hass, freezer, "2026-11-09T09:56:00+00:00")
    assert hass.states.get(busy).state == "off"  # 1 min lead, not 5
    await _advance(hass, freezer, "2026-11-09T09:59:30+00:00")
    assert hass.states.get(busy).state == "on"


async def test_calendar_shows_event(hass, freezer, mock_api, config_entry):
    mock_api.events = events_payload(booking("b1", iso(10), iso(10, 45), "Samtal"))
    await _setup(hass, config_entry, freezer)
    calendar = _entity_id(hass, config_entry, "calendar", "calendar")

    state = hass.states.get(calendar)
    assert state.attributes["message"] == "Samtal"


async def test_auth_failure_starts_reauth(hass, freezer, mock_api, config_entry):
    mock_api.error = ConfigEntryAuthFailed("revoked")
    await _setup_expect_failure(hass, config_entry, freezer)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def _setup_expect_failure(hass, entry, freezer):
    freezer.move_to("2026-11-09T08:00:00+00:00")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_unload(hass, freezer, mock_api, config_entry):
    await _setup(hass, config_entry, freezer)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
