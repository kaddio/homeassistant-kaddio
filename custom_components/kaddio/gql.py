"""Kaddio GraphQL helpers (queries and response mapping, no Home Assistant imports).

Uses the organization-wide API: `findEventsIndexed` (admin token, org must have
the API module enabled) and `findRooms`/`findPlaces`. Client data is deliberately never
requested; only titles, times and the booking type name.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import KaddioEvent

LOCATIONS_QUERY = """
query {
  findRooms { _id name deleted }
  findPlaces { _id name deleted }
}
"""

EVENTS_QUERY = """
query ($start: Date!, $end: Date!, $locationId: ID) {
  findEventsIndexed(start: $start, end: $end, locationId: $locationId) {
    _id start end type title calNote placeId
    bookingType { name }
  }
}
"""

# Entries that mean "something is happening". Bookable time, cancellations,
# reservations and no-shows are intentionally left out.
BUSY_EVENT_TYPES = frozenset({"booking", "session", "cal"})

AUTH_ERROR_MARKERS = ("not authorized", "unauthorized", "unauthenticated")


class GraphQLApiError(Exception):
    """The API answered with GraphQL errors."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages

    @property
    def is_auth_error(self) -> bool:
        text = " ".join(self.messages).lower()
        return any(marker in text for marker in AUTH_ERROR_MARKERS)


def graphql_endpoint(base_url: str) -> str:
    return base_url.rstrip("/") + "/graphql"


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    errors = payload.get("errors")
    if errors:
        raise GraphQLApiError([str(e.get("message", e)) for e in errors])
    return payload.get("data") or {}


def locations_from_response(payload: dict[str, Any]) -> dict[str, str]:
    """Return {id: label}: rooms first, then places (labelled as such).

    The events query filters on either kind of id (`locationId`).
    """
    data = unwrap(payload)
    rooms = {r["_id"]: r["name"] for r in data.get("findRooms") or [] if not r.get("deleted")}
    places = {
        p["_id"]: f"{p['name']} (place)"
        for p in data.get("findPlaces") or []
        if not p.get("deleted")
    }
    return rooms | places


def events_from_response(payload: dict[str, Any]) -> list[KaddioEvent]:
    rows = unwrap(payload).get("findEventsIndexed") or []
    events: list[KaddioEvent] = []
    for row in rows:
        if row.get("type") not in BUSY_EVENT_TYPES:
            continue
        try:
            start, end = _parse_iso(row["start"]), _parse_iso(row["end"])
        except (KeyError, ValueError):
            continue
        booking_type = (row.get("bookingType") or {}).get("name")
        is_cal = row.get("type") == "cal"
        summary = (row.get("title") if is_cal else booking_type) or row.get("title") or ""
        events.append(
            KaddioEvent(
                uid=row["_id"],
                start=start,
                end=max(end, start),
                summary=summary,
                description=(row.get("calNote") or "") if is_cal else "",
                kind=row["type"],
            )
        )
    return sorted(events, key=lambda e: (e.start, e.end, e.uid))
