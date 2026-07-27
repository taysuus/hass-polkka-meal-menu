"""The Polkka Aromi Menu integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PolkkaApiClient
from .const import (
    CONF_PAYLOAD_TEMPLATE,
    CONF_RESTAURANT_ID,
    CONF_URL,
    DOMAIN,
    PLATFORMS,
    get_diet_ids,
)
from .coordinator import PolkkaMenuCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Polkka Aromi Menu from a config entry."""
    session = async_get_clientsession(hass)
    client = PolkkaApiClient(session, entry.data[CONF_URL])
    coordinator = PolkkaMenuCoordinator(
        hass,
        client,
        entry.data[CONF_RESTAURANT_ID],
        entry.data[CONF_PAYLOAD_TEMPLATE],
        get_diet_ids(entry),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Refresh the coordinator when diet restrictions change via the options flow."""
    coordinator: PolkkaMenuCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.diet_ids = get_diet_ids(entry)
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
