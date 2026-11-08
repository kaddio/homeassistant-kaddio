import unittest
from datetime import datetime, timedelta, timezone

from pure_modules import load_pure_modules

modules = load_pure_modules("kaddio_under_test_rule", "models", "busy_rule")
EventKind = modules.models.EventKind
KaddioEvent = modules.models.KaddioEvent
BusyRule = modules.busy_rule.BusyRule

FIVE_MINUTES = timedelta(minutes=5)
PATIENT_KINDS = frozenset({EventKind.CLIENT_MEETING, EventKind.GROUP_SESSION})
EVERY_KIND = frozenset(EventKind)


def at(hour, minute=0):
    return datetime(2026, 11, 9, hour, minute, tzinfo=timezone.utc)


def make_event(uid, start, end, kind=EventKind.CLIENT_MEETING):
    return KaddioEvent(uid, start, end, "summary", "", kind)


def make_rule(kinds=PATIENT_KINDS, lead=FIVE_MINUTES, trail=FIVE_MINUTES):
    return BusyRule(lead=lead, trail=trail, kinds=kinds)


class FindActiveEventTest(unittest.TestCase):
    def test_active_from_lead_until_trail_has_passed(self):
        events = [make_event("a", at(10), at(11))]
        rule = make_rule()

        self.assertIsNone(rule.find_active_event(events, at(9, 54)))
        self.assertIsNotNone(rule.find_active_event(events, at(9, 55)))
        self.assertIsNotNone(rule.find_active_event(events, at(11, 4)))
        self.assertIsNone(rule.find_active_event(events, at(11, 5)))

    def test_back_to_back_meetings_leave_no_gap(self):
        events = [make_event("a", at(10), at(11)), make_event("b", at(11, 5), at(12))]
        rule = make_rule()

        for minutes_after_ten in range(0, 65):
            now = at(10) + timedelta(minutes=minutes_after_ten)
            self.assertIsNotNone(rule.find_active_event(events, now), minutes_after_ten)

    def test_gap_longer_than_lead_plus_trail_turns_off(self):
        events = [make_event("a", at(10), at(11)), make_event("b", at(11, 30), at(12))]

        self.assertIsNone(make_rule().find_active_event(events, at(11, 10)))

    def test_calendar_entries_count_only_when_their_kind_is_selected(self):
        events = [make_event("lunch", at(12), at(13), EventKind.CALENDAR_ENTRY)]

        self.assertIsNone(make_rule(PATIENT_KINDS).find_active_event(events, at(12, 30)))
        self.assertIsNotNone(make_rule(EVERY_KIND).find_active_event(events, at(12, 30)))


class FindNextEventTest(unittest.TestCase):
    def test_skips_kinds_that_do_not_count(self):
        events = [
            make_event("lunch", at(9), at(9, 30), EventKind.CALENDAR_ENTRY),
            make_event("meeting", at(10), at(11)),
        ]

        next_event = make_rule().find_next_event(events, at(8))

        self.assertEqual(next_event.uid, "meeting")

    def test_none_when_nothing_is_left(self):
        events = [make_event("a", at(10), at(11))]

        self.assertIsNone(make_rule().find_next_event(events, at(12)))


class NextStateChangeTest(unittest.TestCase):
    def test_returns_the_nearest_upcoming_lead_or_trail_moment(self):
        events = [
            make_event("a", at(10), at(11)),
            make_event("lunch", at(9), at(9, 30), EventKind.CALENDAR_ENTRY),
        ]
        rule = make_rule()

        self.assertEqual(rule.next_state_change(events, at(8)), at(9, 55))
        self.assertEqual(rule.next_state_change(events, at(10, 1)), at(11, 5))
        self.assertIsNone(rule.next_state_change(events, at(12)))


if __name__ == "__main__":
    unittest.main()
