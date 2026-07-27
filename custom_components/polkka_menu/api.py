"""Thin async client for the Polkka Aromi Menu (CGI SaaS) API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiohttp


class PolkkaApiError(Exception):
    """Raised when a Polkka Aromi Menu API call fails."""


def _format_dt(value: datetime) -> str:
    """Format a datetime the way the RestaurantMeals endpoint expects it."""
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


class PolkkaApiClient:
    """Talks to a single restaurant's RestaurantMeals endpoint."""

    def __init__(self, session: aiohttp.ClientSession, meals_url: str) -> None:
        self._session = session
        self._meals_url = meals_url.rstrip("/")

    @property
    def _diner_groups_url(self) -> str:
        return self._meals_url.rsplit("/", 1)[0] + "/SuitabilityDinerGroups"

    async def async_get_diet_options(self, diet_group_id: str) -> list[dict[str, Any]]:
        """Fetch the list of selectable diet restrictions for a diet group."""
        try:
            async with self._session.get(
                self._diner_groups_url, params={"id": diet_group_id}
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise PolkkaApiError(str(err)) from err

    async def async_get_meals(
        self,
        restaurant_id: str,
        start: datetime,
        end: datetime,
        payload_template: dict[str, Any],
        diet_ids: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fetch the menu between start and end (inclusive-ish, per the upstream API)."""
        body = dict(payload_template)
        body["RestaurantId"] = restaurant_id
        body["SuitabilityDietIds"] = diet_ids
        body["IsActiveSuitability"] = bool(diet_ids)
        params = {
            "Id": restaurant_id,
            "StartDate": _format_dt(start),
            "EndDate": _format_dt(end),
        }
        try:
            async with self._session.post(
                self._meals_url, params=params, json=body
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise PolkkaApiError(str(err)) from err
