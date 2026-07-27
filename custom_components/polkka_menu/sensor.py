"""Sensor platform for the Polkka Aromi Menu integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import PolkkaMenuCoordinator

# key -> (display name, icon, keyword matched against the API's MealName, case-insensitive)
MEAL_SENSORS = {
    "breakfast": ("Breakfast", "mdi:coffee", "breakfast"),
    "lunch": ("Lunch", "mdi:food", "lunch"),
    "snack": ("Snack", "mdi:food-apple", "snack"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up today's meal sensors for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        PolkkaMealSensor(entry, coordinator, key, name, icon, keyword)
        for key, (name, icon, keyword) in MEAL_SENSORS.items()
    )


def _today_meal_dishes(
    coordinator_data: list[dict[str, Any]] | None, keyword: str
) -> tuple[str | None, list[str]]:
    """Find today's meal matching keyword and return (meal name, dish names)."""
    if not coordinator_data:
        return None, []
    today = dt_util.now().date()
    for day in coordinator_data:
        menu_date = dt_util.parse_datetime(day.get("Date", ""))
        if menu_date is None or menu_date.date() != today:
            continue
        for meal in day.get("Meals") or []:
            meal_name = meal.get("MealName") or ""
            if keyword in meal_name.lower():
                dishes = [
                    d["DishName"] for d in (meal.get("Dishes") or []) if d.get("DishName")
                ]
                return meal_name, dishes
    return None, []


class PolkkaMealSensor(CoordinatorEntity[PolkkaMenuCoordinator], SensorEntity):
    """Shows today's dishes for one meal (breakfast/lunch/snack)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: PolkkaMenuCoordinator,
        key: str,
        name: str,
        icon: str,
        keyword: str,
    ) -> None:
        super().__init__(coordinator)
        self._keyword = keyword
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Polkka Aromi Menu",
        )

    @property
    def native_value(self) -> str | None:
        _, dishes = _today_meal_dishes(self.coordinator.data, self._keyword)
        if not dishes:
            return None
        value = ", ".join(dishes)
        return value if len(value) <= 255 else value[:252] + "..."

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meal_name, dishes = _today_meal_dishes(self.coordinator.data, self._keyword)
        return {"meal_name": meal_name, "dishes": dishes}
