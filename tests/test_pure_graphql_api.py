import unittest
from datetime import datetime, timezone

from pure_modules import load_pure_modules

modules = load_pure_modules("kaddio_under_test_api", "models", "graphql_api")
api = modules.graphql_api
EventKind = modules.models.EventKind


def event_row(uid, kind, start, end, title=None, booking_type=None, note=None):
    return {
        "_id": uid,
        "type": kind,
        "start": start,
        "end": end,
        "title": title,
        "calNote": note,
        "placeId": "place-1",
        "bookingType": {"name": booking_type} if booking_type else None,
    }


def events_payload(*rows):
    return {"data": {"findEventsIndexed": list(rows)}}


class ParseEventsTest(unittest.TestCase):
    def test_keeps_meetings_sessions_and_calendar_entries_sorted_by_start(self):
        payload = events_payload(
            event_row("late", "booking", "2026-11-09T10:00:00.000Z", "2026-11-09T10:45:00.000Z", booking_type="Consultation"),
            event_row("early", "cal", "2026-11-09T08:00:00.000Z", "2026-11-09T09:00:00.000Z", title="Meeting", note="Zoom"),
            event_row("group", "session", "2026-11-09T12:00:00.000Z", "2026-11-09T13:00:00.000Z", booking_type="Grupp"),
        )

        events = api.parse_events(payload)

        self.assertEqual([event.uid for event in events], ["early", "late", "group"])
        self.assertEqual(
            [event.kind for event in events],
            [EventKind.CALENDAR_ENTRY, EventKind.CLIENT_MEETING, EventKind.GROUP_SESSION],
        )

    def test_calendar_entry_uses_title_and_note(self):
        payload = events_payload(
            event_row("a", "cal", "2026-11-09T08:00:00Z", "2026-11-09T09:00:00Z", title="Meeting", note="Zoom")
        )

        event = api.parse_events(payload)[0]

        self.assertEqual((event.summary, event.description), ("Meeting", "Zoom"))

    def test_meeting_uses_booking_type_name_and_no_description(self):
        payload = events_payload(
            event_row("a", "booking", "2026-11-09T10:00:00Z", "2026-11-09T10:45:00Z", booking_type="Consultation")
        )

        event = api.parse_events(payload)[0]

        self.assertEqual((event.summary, event.description), ("Consultation", ""))
        self.assertEqual(event.start, datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc))

    def test_ignores_other_event_types(self):
        payload = events_payload(
            event_row("a", "bookable_time", "2026-11-09T10:00:00Z", "2026-11-09T11:00:00Z"),
            event_row("b", "unbooking", "2026-11-09T12:00:00Z", "2026-11-09T13:00:00Z"),
        )

        self.assertEqual(api.parse_events(payload), [])

    def test_skips_rows_with_unreadable_dates(self):
        payload = events_payload(event_row("a", "booking", "nope", "x", booking_type="Consultation"))

        self.assertEqual(api.parse_events(payload), [])

    def test_end_before_start_is_clamped_to_start(self):
        payload = events_payload(
            event_row("a", "booking", "2026-11-09T10:00:00Z", "2026-11-09T09:00:00Z", booking_type="Consultation")
        )

        event = api.parse_events(payload)[0]

        self.assertEqual(event.end, event.start)


class ErrorHandlingTest(unittest.TestCase):
    def test_authorization_errors_are_recognised(self):
        with self.assertRaises(api.GraphQLApiError) as raised:
            api.parse_events({"errors": [{"message": "Not authorized"}]})

        self.assertTrue(raised.exception.is_auth_error)

    def test_other_errors_are_not_authorization_errors(self):
        with self.assertRaises(api.GraphQLApiError) as raised:
            api.parse_locations({"errors": [{"message": "boom"}]})

        self.assertFalse(raised.exception.is_auth_error)


class ParseLocationsTest(unittest.TestCase):
    def test_separates_rooms_from_places_and_skips_deleted(self):
        payload = {
            "data": {
                "findRooms": [
                    {"_id": "r1", "name": "Kitchen", "deleted": False},
                    {"_id": "r2", "name": "Removed room", "deleted": True},
                ],
                "findPlaces": [
                    {"_id": "p1", "name": "Kaddio Support", "deleted": False},
                    {"_id": "p2", "name": "Old place", "deleted": True},
                ],
            }
        }

        locations = api.parse_locations(payload)

        self.assertEqual(locations.rooms, {"r1": "Kitchen"})
        self.assertEqual(locations.places, {"p1": "Kaddio Support"})


class ChosenLocationExistsTest(unittest.TestCase):
    payload = {
        "data": {
            "findRooms": [{"_id": "r1", "deleted": False}, {"_id": "r2", "deleted": True}],
            "findPlaces": [{"_id": "p1", "deleted": False}],
        }
    }

    def test_active_room_and_place_exist(self):
        self.assertTrue(api.chosen_location_exists(self.payload, "r1"))
        self.assertTrue(api.chosen_location_exists(self.payload, "p1"))

    def test_deleted_or_unknown_location_does_not_exist(self):
        self.assertFalse(api.chosen_location_exists(self.payload, "r2"))
        self.assertFalse(api.chosen_location_exists(self.payload, "unknown"))

    def test_whole_organization_always_exists(self):
        self.assertTrue(api.chosen_location_exists(self.payload, None))


if __name__ == "__main__":
    unittest.main()
