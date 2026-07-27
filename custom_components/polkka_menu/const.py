"""Constants for the Polkka Aromi Menu integration."""
from __future__ import annotations

from typing import Any

DOMAIN = "polkka_menu"
PLATFORMS = ["calendar", "sensor"]

# How far back/forward to pull menu data for the background refresh.
# async_get_events() always fetches live for whatever range the calendar UI asks for,
# this window is only used to populate the entity's current/next "event" state.
LOOKBACK_DAYS = 1
LOOKAHEAD_DAYS = 14

UPDATE_INTERVAL_HOURS = 6

CONF_URL = "url"
CONF_RESTAURANT_ID = "restaurant_id"
CONF_PAYLOAD_TEMPLATE = "payload_template"
CONF_DIET_IDS = "diet_ids"


def get_diet_ids(entry: Any) -> list[dict[str, Any]]:
    """Return the effective diet restriction list, options override data."""
    return entry.options.get(CONF_DIET_IDS, entry.data.get(CONF_DIET_IDS, []))
