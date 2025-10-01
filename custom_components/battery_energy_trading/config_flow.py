"""Config flow for Battery Energy Trading integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_BATTERY_CAPACITY_ENTITY,
    CONF_SOLAR_POWER_ENTITY,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NORDPOOL_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_BATTERY_LEVEL_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_BATTERY_CAPACITY_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_SOLAR_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Energy Trading."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that entities exist
            for key in [
                CONF_NORDPOOL_ENTITY,
                CONF_BATTERY_LEVEL_ENTITY,
                CONF_BATTERY_CAPACITY_ENTITY,
            ]:
                entity_id = user_input.get(key)
                if entity_id and not self.hass.states.get(entity_id):
                    errors[key] = "entity_not_found"

            if not errors:
                return self.async_create_entry(
                    title="Battery Energy Trading",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
