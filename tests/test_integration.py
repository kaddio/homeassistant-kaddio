from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.kaddio.const import (
    CONF_EVENT_KINDS,
    CONF_LEAD_MINUTES,
    CONF_TRAIL_MINUTES,
    DOMAIN,
)

from conftest import calendar_entry, client_meeting, events_payload, timestamp

MORNING = "2026-11-09T08:00:00+00:00"


def entity_id_of(hass, entry, platform, entity_key):
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}-{entity_key}"
    )


def busy_sensor_id(hass, entry):
    return entity_id_of(hass, entry, "binary_sensor", "busy")


def location_issue(hass, entry):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"location_missing_{entry.entry_id}")


async def set_up(hass, entry, freezer, now=MORNING):
    freezer.move_to(now)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def advance_clock_to(hass, freezer, moment):
    freezer.move_to(moment)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()


def entry_with_options(entry, options):
    return MockConfigEntry(
        domain=DOMAIN,
        title=entry.title,
        unique_id=entry.unique_id,
        data=dict(entry.data),
        options=options,
    )


async def test_setup_creates_a_calendar_and_a_busy_sensor(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(client_meeting("m1", timestamp(10), timestamp(10, 45)))

    await set_up(hass, room_entry, freezer)

    assert room_entry.state is ConfigEntryState.LOADED
    assert entity_id_of(hass, room_entry, "calendar", "calendar")
    assert hass.states.get(busy_sensor_id(hass, room_entry)).state == "off"


async def test_busy_sensor_follows_lead_and_trail_time(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(client_meeting("m1", timestamp(10), timestamp(10, 45)))
    await set_up(hass, room_entry, freezer)
    busy = busy_sensor_id(hass, room_entry)

    await advance_clock_to(hass, freezer, "2026-11-09T09:54:00+00:00")
    assert hass.states.get(busy).state == "off"
    await advance_clock_to(hass, freezer, "2026-11-09T09:56:00+00:00")
    assert hass.states.get(busy).state == "on"
    await advance_clock_to(hass, freezer, "2026-11-09T10:49:00+00:00")
    assert hass.states.get(busy).state == "on"
    await advance_clock_to(hass, freezer, "2026-11-09T10:51:00+00:00")
    assert hass.states.get(busy).state == "off"


async def test_busy_sensor_stays_on_between_back_to_back_meetings(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(
        client_meeting("m1", timestamp(10), timestamp(10, 30)),
        client_meeting("m2", timestamp(10, 35), timestamp(11)),
    )
    await set_up(hass, room_entry, freezer)

    await advance_clock_to(hass, freezer, "2026-11-09T10:32:00+00:00")

    assert hass.states.get(busy_sensor_id(hass, room_entry)).state == "on"


async def test_calendar_entries_do_not_make_the_room_busy_by_default(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(calendar_entry("c1", timestamp(10), timestamp(11)))
    await set_up(hass, room_entry, freezer)

    await advance_clock_to(hass, freezer, "2026-11-09T10:30:00+00:00")

    assert hass.states.get(busy_sensor_id(hass, room_entry)).state == "off"


async def test_calendar_entries_count_when_selected_in_options(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(calendar_entry("c1", timestamp(10), timestamp(11)))
    entry = entry_with_options(room_entry, {CONF_EVENT_KINDS: ["booking", "session", "cal"]})
    await set_up(hass, entry, freezer)

    await advance_clock_to(hass, freezer, "2026-11-09T10:30:00+00:00")

    assert hass.states.get(busy_sensor_id(hass, entry)).state == "on"


async def test_lead_and_trail_minutes_come_from_options(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(client_meeting("m1", timestamp(10), timestamp(10, 45)))
    entry = entry_with_options(room_entry, {CONF_LEAD_MINUTES: 1, CONF_TRAIL_MINUTES: 1})
    await set_up(hass, entry, freezer)
    busy = busy_sensor_id(hass, entry)

    await advance_clock_to(hass, freezer, "2026-11-09T09:56:00+00:00")
    assert hass.states.get(busy).state == "off"
    await advance_clock_to(hass, freezer, "2026-11-09T09:59:30+00:00")
    assert hass.states.get(busy).state == "on"


async def test_next_meeting_attributes_ignore_kinds_that_do_not_count(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(
        calendar_entry("c1", timestamp(9), timestamp(9, 30)),
        client_meeting("m1", timestamp(10), timestamp(10, 45), "Samtal"),
    )

    await set_up(hass, room_entry, freezer)

    attributes = hass.states.get(busy_sensor_id(hass, room_entry)).attributes
    assert attributes["next_summary"] == "Samtal"
    assert attributes["next_start"] == timestamp(10)


async def test_calendar_shows_the_upcoming_meeting(hass, freezer, kaddio_api, room_entry):
    kaddio_api.events = events_payload(
        client_meeting("m1", timestamp(10), timestamp(10, 45), "Samtal")
    )

    await set_up(hass, room_entry, freezer)

    calendar = entity_id_of(hass, room_entry, "calendar", "calendar")
    assert hass.states.get(calendar).attributes["message"] == "Samtal"


async def test_rejected_token_starts_reauthentication(hass, freezer, kaddio_api, room_entry):
    kaddio_api.error = ConfigEntryAuthFailed("revoked")

    await set_up(hass, room_entry, freezer)

    assert room_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_unloading_the_entry_succeeds(hass, freezer, kaddio_api, room_entry):
    await set_up(hass, room_entry, freezer)

    assert await hass.config_entries.async_unload(room_entry.entry_id)

    assert room_entry.state is ConfigEntryState.NOT_LOADED


async def test_notice_appears_when_the_room_is_deleted_and_clears_when_it_returns(hass, freezer, kaddio_api, room_entry):
    kaddio_api.rooms = [{"_id": "room1", "deleted": True}]
    await set_up(hass, room_entry, freezer)
    assert location_issue(hass, room_entry) is not None

    kaddio_api.rooms = [{"_id": "room1", "deleted": False}]
    await room_entry.runtime_data.async_refresh()

    assert location_issue(hass, room_entry) is None


async def test_no_notice_while_the_room_exists(hass, freezer, kaddio_api, room_entry):
    await set_up(hass, room_entry, freezer)

    assert location_issue(hass, room_entry) is None


async def test_notice_is_removed_together_with_the_entry(hass, freezer, kaddio_api, room_entry):
    kaddio_api.rooms = []
    await set_up(hass, room_entry, freezer)
    assert location_issue(hass, room_entry) is not None

    await hass.config_entries.async_remove(room_entry.entry_id)

    assert location_issue(hass, room_entry) is None
