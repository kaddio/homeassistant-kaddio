"""Unit tests for GraphQL response mapping (no Home Assistant needed)."""

import importlib.util
import pathlib
import sys
import types
import unittest
from datetime import datetime, timezone

base = pathlib.Path(__file__).parent.parent / "custom_components" / "kaddio"
pkg = types.ModuleType("kaddio_pkg")
pkg.__path__ = [str(base)]
sys.modules["kaddio_pkg"] = pkg
for name in ("models", "gql"):
    spec = importlib.util.spec_from_file_location(f"kaddio_pkg.{name}", base / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"kaddio_pkg.{name}"] = mod
    spec.loader.exec_module(mod)
gql = sys.modules["kaddio_pkg.gql"]


def row(i, type_, start, end, title=None, bt=None, note=None):
    return {"_id": i, "type": type_, "start": start, "end": end, "title": title,
            "calNote": note, "placeId": "p1", "bookingType": {"name": bt} if bt else None}


class GqlTest(unittest.TestCase):
    def test_filters_and_maps(self):
        payload = {"data": {"findEventsIndexed": [
            row("2", "booking", "2026-11-09T10:00:00.000Z", "2026-11-09T10:45:00.000Z", bt="Samtal"),
            row("1", "cal", "2026-11-09T08:00:00.000Z", "2026-11-09T09:00:00.000Z", title="Möte", note="Zoom"),
            row("3", "bookable_time", "2026-11-09T11:00:00.000Z", "2026-11-09T12:00:00.000Z"),
            row("4", "unbooking", "2026-11-09T13:00:00.000Z", "2026-11-09T14:00:00.000Z"),
        ]}}
        events = gql.events_from_response(payload)
        self.assertEqual([e.uid for e in events], ["1", "2"])
        self.assertEqual(events[0].summary, "Möte")
        self.assertEqual(events[0].description, "Zoom")
        self.assertEqual(events[1].summary, "Samtal")
        self.assertEqual(events[1].start, datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc))

    def test_auth_error_detected(self):
        with self.assertRaises(gql.GraphQLApiError) as ctx:
            gql.events_from_response({"errors": [{"message": "Not authorized"}]})
        self.assertTrue(ctx.exception.is_auth_error)

    def test_other_error_is_not_auth(self):
        with self.assertRaises(gql.GraphQLApiError) as ctx:
            gql.locations_from_response({"errors": [{"message": "boom"}]})
        self.assertFalse(ctx.exception.is_auth_error)

    def test_locations_rooms_first_places_labelled_deleted_skipped(self):
        payload = {"data": {
            "findRooms": [
                {"_id": "r1", "name": "Köket", "deleted": False},
                {"_id": "r2", "name": "Borttaget", "deleted": True}],
            "findPlaces": [
                {"_id": "p1", "name": "Kaddio Support", "deleted": False},
                {"_id": "p2", "name": "Gammal", "deleted": True}]}}
        result = gql.locations_from_response(payload)
        self.assertEqual(result, {"r1": "Köket", "p1": "Kaddio Support (place)"})
        self.assertEqual(list(result), ["r1", "p1"])

    def test_bad_dates_skipped(self):
        payload = {"data": {"findEventsIndexed": [row("1", "booking", "nope", "x", bt="A")]}}
        self.assertEqual(gql.events_from_response(payload), [])


if __name__ == "__main__":
    unittest.main()
