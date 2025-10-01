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
    CONF_SOLAR_FORECAST_ENTITY,
    DEFAULT_CHARGE_RATE_KW,
    DEFAULT_DISCHARGE_RATE_KW,
)
from .sungrow_helper import SungrowHelper

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
        vol.Optional(CONF_SOLAR_FORECAST_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Energy Trading."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._sungrow_config: dict[str, Any] | None = None
        self._detected_entities: dict[str, str | None] | None = None

    def _is_nordpool_available(self) -> bool:
        """Check if Nord Pool integration is available."""
        all_entities = self.hass.states.async_all()
        # Look for Nord Pool sensor entities (they typically have 'nordpool' in the entity ID)
        nordpool_sensors = [
            entity for entity in all_entities
            if entity.entity_id.startswith("sensor.nordpool")
            or "nordpool" in entity.entity_id.lower()
        ]

        if nordpool_sensors:
            # Check if any Nord Pool sensor has the required 'raw_today' attribute
            for sensor in nordpool_sensors:
                if sensor.attributes.get("raw_today"):
                    return True

        return False

    def _validate_entities(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> None:
        """Validate that required entities exist and have correct attributes.

        Args:
            user_input: User configuration input
            errors: Dictionary to populate with validation errors
        """
        # Validate that entities exist
        for key in [
            CONF_NORDPOOL_ENTITY,
            CONF_BATTERY_LEVEL_ENTITY,
            CONF_BATTERY_CAPACITY_ENTITY,
        ]:
            entity_id = user_input.get(key)
            if entity_id and not self.hass.states.get(entity_id):
                errors[key] = "entity_not_found"

        # Validate Nord Pool entity has required attributes
        if CONF_NORDPOOL_ENTITY in user_input and not errors.get(CONF_NORDPOOL_ENTITY):
            nordpool_state = self.hass.states.get(user_input[CONF_NORDPOOL_ENTITY])
            if nordpool_state and not nordpool_state.attributes.get("raw_today"):
                errors[CONF_NORDPOOL_ENTITY] = "nordpool_missing_raw_today"
                _LOGGER.error(
                    "Nord Pool entity %s does not have 'raw_today' attribute. "
                    "Make sure you're using a valid Nord Pool price sensor.",
                    user_input[CONF_NORDPOOL_ENTITY]
                )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - check for Nord Pool integration and Sungrow auto-detection."""
        # First check if Nord Pool integration is available
        if not self._is_nordpool_available():
            return self.async_abort(
                reason="nordpool_not_found",
                description_placeholders={
                    "error": "Nord Pool integration not found. Please install and configure the Nord Pool integration first."
                },
            )

        # Check if Sungrow integration is available
        sungrow_helper = SungrowHelper(self.hass)

        if sungrow_helper.is_sungrow_integration_available():
            _LOGGER.info("Sungrow integration detected, offering auto-configuration")
            return await self.async_step_sungrow_detect()

        # No Sungrow detected, proceed with manual configuration
        return await self.async_step_manual()

    async def async_step_sungrow_detect(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Offer Sungrow auto-detection."""
        if user_input is not None:
            if user_input.get("use_auto_detection"):
                return await self.async_step_sungrow_auto()
            else:
                return await self.async_step_manual()

        return self.async_show_form(
            step_id="sungrow_detect",
            data_schema=vol.Schema(
                {
                    vol.Required("use_auto_detection", default=True): bool,
                }
            ),
            description_placeholders={
                "info": "Sungrow inverter detected! Would you like to automatically configure entities and parameters?"
            },
        )

    async def async_step_sungrow_auto(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Auto-configure using detected Sungrow entities."""
        sungrow_helper = SungrowHelper(self.hass)
        auto_config = await sungrow_helper.async_get_auto_configuration()

        self._sungrow_config = auto_config
        self._detected_entities = auto_config["detected_entities"]

        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate entities using extracted method
            self._validate_entities(user_input, errors)

            if not errors:
                # Store auto-detected charge/discharge rates in options
                return self.async_create_entry(
                    title="Battery Energy Trading (Sungrow)",
                    data=user_input,
                    options={
                        "charge_rate": auto_config.get("recommended_charge_rate", DEFAULT_CHARGE_RATE_KW),
                        "discharge_rate": auto_config.get("recommended_discharge_rate", DEFAULT_DISCHARGE_RATE_KW),
                        "inverter_model": auto_config.get("inverter_model"),
                        "auto_detected": True,
                    },
                )

        # Build schema with auto-detected defaults
        suggested_values = {
            CONF_BATTERY_LEVEL_ENTITY: self._detected_entities.get("battery_level"),
            CONF_BATTERY_CAPACITY_ENTITY: self._detected_entities.get("battery_capacity"),
            CONF_SOLAR_POWER_ENTITY: self._detected_entities.get("solar_power"),
        }

        # Create description with detected info
        description = []
        if auto_config.get("inverter_model"):
            description.append(f"Detected inverter: {auto_config['inverter_model']}")
        if auto_config.get("recommended_charge_rate"):
            description.append(f"Recommended charge rate: {auto_config['recommended_charge_rate']} kW")
            description.append(f"Recommended discharge rate: {auto_config['recommended_discharge_rate']} kW")

        schema_dict = {
            vol.Required(CONF_NORDPOOL_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_BATTERY_LEVEL_ENTITY,
                default=suggested_values.get(CONF_BATTERY_LEVEL_ENTITY),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_BATTERY_CAPACITY_ENTITY,
                default=suggested_values.get(CONF_BATTERY_CAPACITY_ENTITY),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                CONF_SOLAR_POWER_ENTITY,
                default=suggested_values.get(CONF_SOLAR_POWER_ENTITY),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }

        return self.async_show_form(
            step_id="sungrow_auto",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "detected_info": "\n".join(description) if description else "Auto-detecting Sungrow configuration..."
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate entities using extracted method
            self._validate_entities(user_input, errors)

            if not errors:
                return self.async_create_entry(
                    title="Battery Energy Trading",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
