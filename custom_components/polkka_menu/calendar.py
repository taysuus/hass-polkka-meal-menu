"""Calendar platform for the Polkka Aromi Menu integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import PolkkaApiClient, PolkkaApiError
from .const import CONF_PAYLOAD_TEMPLATE, CONF_RESTAURANT_ID, DOMAIN, get_diet_ids
from .coordinator import PolkkaMenuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the calendar entity for this config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PolkkaMenuCalendar(entry, data["coordinator"], data["client"])])


def _day_to_event(day: dict[str, Any]) -> CalendarEvent | None:
    """Turn one day of the RestaurantMeals response into an all-day calendar event."""
    lines: list[str] = []
    meal_names: list[str] = []
    for meal in day.get("Meals") or []:
        dishes = [d["DishName"] for d in (meal.get("Dishes") or []) if d.get("DishName")]
        if not dishes:
            continue
        meal_names.append(meal["MealName"])
        lines.append(f"{meal['MealName']}: {', '.join(dishes)}")

    if not lines:
        return None

    menu_date = dt_util.parse_datetime(day.get("Date", ""))
    if menu_date is None:
        return None

    start = menu_date.date()
    return CalendarEvent(
        start=start,
        end=start + timedelta(days=1),
        summary=", ".join(meal_names),
        description="\n".join(lines),
    )


class PolkkaMenuCalendar(CoordinatorEntity[PolkkaMenuCoordinator], CalendarEntity):
    """Calendar entity showing the daycare's daily menu."""

    _attr_has_entity_name = True
    _attr_name = "Menu"

    def __init__(
        self, entry: ConfigEntry, coordinator: PolkkaMenuCoordinator, client: PolkkaApiClient
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_menu"

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        for day in self.coordinator.data or []:
            event = _day_to_event(day)
            if event and event.start <= today < event.end:
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch menu events live for whatever range the calendar UI requests."""
        try:
            days = await self._client.async_get_meals(
                self._entry.data[CONF_RESTAURANT_ID],
                start_date,
                end_date,
                self._entry.data[CONF_PAYLOAD_TEMPLATE],
                get_diet_ids(self._entry),
            )
        except PolkkaApiError as err:
            _LOGGER.warning("Failed to fetch Polkka menu: %s", err)
            return []

        events = [_day_to_event(day) for day in days]
        return [event for event in events if event is not None]
