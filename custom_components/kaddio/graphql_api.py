from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import EventKind, KaddioEvent, Locations

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
  findRooms { _id deleted }
  findPlaces { _id deleted }
}
"""

AUTH_ERROR_MARKERS = ("not authorized", "unauthorized", "unauthenticated")


class GraphQLApiError(Exception):
    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages

    @property
    def is_auth_error(self) -> bool:
        joined_messages = " ".join(self.messages).lower()
        return any(marker in joined_messages for marker in AUTH_ERROR_MARKERS)


def graphql_endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/graphql"


def extract_data(payload: dict[str, Any]) -> dict[str, Any]:
    errors = payload.get("errors")
    if errors:
        raise GraphQLApiError([str(error.get("message", error)) for error in errors])
    return payload.get("data") or {}


def parse_locations(payload: dict[str, Any]) -> Locations:
    data = extract_data(payload)
    return Locations(
        rooms=_names_of_active(data.get("findRooms")),
        places=_names_of_active(data.get("findPlaces")),
    )


def chosen_location_exists(payload: dict[str, Any], location_id: str | None) -> bool:
    if location_id is None:
        return True
    data = extract_data(payload)
    locations = [*(data.get("findRooms") or []), *(data.get("findPlaces") or [])]
    return any(
        location["_id"] == location_id and not location.get("deleted")
        for location in locations
    )


def parse_events(payload: dict[str, Any]) -> list[KaddioEvent]:
    rows = extract_data(payload).get("findEventsIndexed") or []
    events = [event for row in rows if (event := _parse_event(row)) is not None]
    return sorted(events, key=lambda event: (event.start, event.end, event.uid))


def _parse_event(row: dict[str, Any]) -> KaddioEvent | None:
    try:
        kind = EventKind(row["type"])
        start = _parse_timestamp(row["start"])
        end = _parse_timestamp(row["end"])
    except (KeyError, ValueError):
        return None
    is_calendar_entry = kind is EventKind.CALENDAR_ENTRY
    summary = row.get("title") if is_calendar_entry else _booking_type_name(row)
    description = row.get("calNote") if is_calendar_entry else None
    return KaddioEvent(
        uid=row["_id"],
        start=start,
        end=max(start, end),
        summary=summary or "",
        description=description or "",
        kind=kind,
    )


def _booking_type_name(row: dict[str, Any]) -> str | None:
    return (row.get("bookingType") or {}).get("name")


def _names_of_active(rows: list[dict[str, Any]] | None) -> dict[str, str]:
    return {row["_id"]: row["name"] for row in rows or [] if not row.get("deleted")}


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
