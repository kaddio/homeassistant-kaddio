from datetime import timedelta

from .models import EventKind

DOMAIN = "kaddio"

CONF_BASE_URL = "base_url"
CONF_LOCATION_ID = "location_id"
CONF_LEAD_MINUTES = "lead_minutes"
CONF_TRAIL_MINUTES = "trail_minutes"
CONF_EVENT_KINDS = "event_kinds"

ALL_LOCATIONS = "__all__"
ALL_LOCATIONS_LABEL = "All rooms and places"
PLACE_LABEL_SUFFIX = " (place)"

DEFAULT_LEAD_MINUTES = 5
DEFAULT_TRAIL_MINUTES = 5
MAX_BUSY_MARGIN_MINUTES = 240
DEFAULT_BUSY_KINDS = (EventKind.CLIENT_MEETING, EventKind.GROUP_SESSION)

POLL_INTERVAL = timedelta(minutes=15)
EVENTS_WINDOW_PAST = timedelta(days=1)
EVENTS_WINDOW_FUTURE = timedelta(days=60)

PLATFORMS = ["calendar", "binary_sensor"]
