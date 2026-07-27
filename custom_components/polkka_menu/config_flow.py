"""Config flow for the Polkka Aromi Menu integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PolkkaApiClient, PolkkaApiError
from .const import (
    CONF_DIET_IDS,
    CONF_PAYLOAD_TEMPLATE,
    CONF_RESTAURANT_ID,
    CONF_URL,
    DOMAIN,
    get_diet_ids,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_RESTAURANT_ID): str,
        vol.Required("payload"): selector.TextSelector(
            selector.TextSelectorConfig(multiline=True)
        ),
    }
)


def _parse_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    return payload


def _diet_options_schema(
    diet_options: list[dict[str, Any]], default: list[str]
) -> vol.Schema:
    options = [
        selector.SelectOptionDict(
            value=opt["DietId"], label=f"{opt.get('Name', opt.get('Code'))} ({opt.get('Code')})"
        )
        for opt in diet_options
        if opt.get("DietId")
    ]
    return vol.Schema(
        {
            vol.Optional("diets", default=default): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, multiple=True)
            )
        }
    )


def _diet_ids_from_selection(
    diet_options: list[dict[str, Any]], selected_ids: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "DietId": opt["DietId"],
            "DietType": opt.get("DietType"),
            "IndexNumber": opt.get("IndexNumber"),
        }
        for opt in diet_options
        if opt.get("DietId") in selected_ids
    ]


class PolkkaMenuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Polkka Aromi Menu."""

    VERSION = 1

    def __init__(self) -> None:
        self._url: str | None = None
        self._restaurant_id: str | None = None
        self._payload: dict[str, Any] | None = None
        self._diet_options: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                payload = _parse_payload(user_input["payload"])
            except (json.JSONDecodeError, ValueError):
                errors["payload"] = "invalid_payload"
            else:
                self._url = user_input[CONF_URL].strip()
                self._restaurant_id = user_input[CONF_RESTAURANT_ID].strip()
                payload.pop("SuitabilityDietIds", None)
                payload.pop("IsActiveSuitability", None)
                payload["RestaurantId"] = self._restaurant_id
                self._payload = payload

                diet_group_id = payload.get("DietGroupId")
                if diet_group_id:
                    session = async_get_clientsession(self.hass)
                    client = PolkkaApiClient(session, self._url)
                    try:
                        self._diet_options = await client.async_get_diet_options(
                            diet_group_id
                        )
                    except PolkkaApiError:
                        _LOGGER.warning(
                            "Could not fetch diet restriction list, continuing without it"
                        )
                        self._diet_options = []

                if self._diet_options:
                    return await self.async_step_diet()
                return self._create_entry([])

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_diet(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            diet_ids = _diet_ids_from_selection(
                self._diet_options, user_input.get("diets", [])
            )
            return self._create_entry(diet_ids)

        return self.async_show_form(
            step_id="diet", data_schema=_diet_options_schema(self._diet_options, [])
        )

    def _create_entry(
        self, diet_ids: list[dict[str, Any]]
    ) -> config_entries.ConfigFlowResult:
        assert self._payload is not None
        title = self._payload.get("Name") or "Polkka Menu"
        return self.async_create_entry(
            title=title,
            data={
                CONF_URL: self._url,
                CONF_RESTAURANT_ID: self._restaurant_id,
                CONF_PAYLOAD_TEMPLATE: self._payload,
                CONF_DIET_IDS: diet_ids,
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return PolkkaMenuOptionsFlow()


class PolkkaMenuOptionsFlow(config_entries.OptionsFlow):
    """Let the user change diet restrictions after setup."""

    def __init__(self) -> None:
        self._diet_options: list[dict[str, Any]] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        entry = self.config_entry
        payload = entry.data.get(CONF_PAYLOAD_TEMPLATE, {})
        diet_group_id = payload.get("DietGroupId")

        if diet_group_id and not self._diet_options:
            session = async_get_clientsession(self.hass)
            client = PolkkaApiClient(session, entry.data[CONF_URL])
            try:
                self._diet_options = await client.async_get_diet_options(diet_group_id)
            except PolkkaApiError:
                self._diet_options = []

        if user_input is not None:
            diet_ids = _diet_ids_from_selection(
                self._diet_options, user_input.get("diets", [])
            )
            return self.async_create_entry(title="", data={CONF_DIET_IDS: diet_ids})

        current = [d["DietId"] for d in get_diet_ids(entry)]
        return self.async_show_form(
            step_id="init", data_schema=_diet_options_schema(self._diet_options, current)
        )
