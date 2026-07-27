"""Data update coordinator for the Polkka Aromi Menu integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import PolkkaApiClient, PolkkaApiError
from .const import DOMAIN, LOOKAHEAD_DAYS, LOOKBACK_DAYS, UPDATE_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


class PolkkaMenuCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Periodically refreshes a rolling window of menu data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: PolkkaApiClient,
        restaurant_id: str,
        payload_template: dict[str, Any],
        diet_ids: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self._client = client
        self._restaurant_id = restaurant_id
        self._payload_template = payload_template
        self.diet_ids = diet_ids

    async def _async_update_data(self) -> list[dict[str, Any]]:
        start = dt_util.start_of_local_day() - timedelta(days=LOOKBACK_DAYS)
        end = dt_util.start_of_local_day() + timedelta(days=LOOKAHEAD_DAYS)
        try:
            return await self._client.async_get_meals(
                self._restaurant_id, start, end, self._payload_template, self.diet_ids
            )
        except PolkkaApiError as err:
            raise UpdateFailed(str(err)) from err
