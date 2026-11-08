"""Constants for the Kaddio integration."""

from datetime import timedelta

DOMAIN = "kaddio"

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_PLACE_ID = "place_id"
ALL_PLACES = "__all__"
GRAPHQL_PAST_DAYS = 1
GRAPHQL_FUTURE_DAYS = 60
CONF_LEAD_MINUTES = "lead_minutes"
CONF_TRAIL_MINUTES = "trail_minutes"
CONF_EVENT_KINDS = "event_kinds"

DEFAULT_LEAD_MINUTES = 5
DEFAULT_TRAIL_MINUTES = 5
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

PLATFORMS = ["calendar", "binary_sensor"]
