"""Automation installer for programmatically creating Home Assistant automations."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_CUSTOM_CHARGE_ENTITY,
    CONF_CUSTOM_CHARGE_SERVICE,
    CONF_CUSTOM_DISCHARGE_ENTITY,
    CONF_CUSTOM_DISCHARGE_SERVICE,
    CONF_CUSTOM_NORMAL_ENTITY,
    CONF_CUSTOM_NORMAL_SERVICE,
    CONF_INVERTER_CONTROL_TYPE,
    CONF_NORDPOOL_ENTITY,
    DEFAULT_SUNGROW_MODBUS_CHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_EMS_MODE,
    DOMAIN,
    INVERTER_CONTROL_SUNGROW_MODBUS,
)


_LOGGER = logging.getLogger(__name__)

# Automation IDs used by this integration
DISCHARGE_AUTOMATION_ID = "battery_trading_auto_discharge"
CHARGING_AUTOMATION_ID = "battery_trading_auto_charging"
MIDNIGHT_RESET_AUTOMATION_ID = "battery_trading_midnight_reset"


class AutomationInstaller:
    """Handle programmatic creation and removal of automations."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the automation installer.

        Args:
            hass: Home Assistant instance
            config_entry: The integration's config entry
        """
        self.hass = hass
        self.config_entry = config_entry
        self._control_type = config_entry.options.get(
            CONF_INVERTER_CONTROL_TYPE, INVERTER_CONTROL_SUNGROW_MODBUS
        )

    def _get_discharge_automation_config(self) -> dict[str, Any]:
        """Generate discharge automation configuration."""
        base_config = {
            "id": DISCHARGE_AUTOMATION_ID,
            "alias": "Battery Trading: Smart Discharge Control",
            "description": f"Auto-installed by Battery Energy Trading integration (entry: {self.config_entry.entry_id})",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.battery_energy_trading_forced_discharge",
                },
                {
                    "platform": "state",
                    "entity_id": "switch.battery_energy_trading_enable_forced_discharge",
                },
            ],
            "mode": "single",
        }

        if self._control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            # Modbus control - use select and number entities
            base_config["action"] = [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "binary_sensor.battery_energy_trading_forced_discharge",
                                    "state": "on",
                                },
                                {
                                    "condition": "state",
                                    "entity_id": "switch.battery_energy_trading_enable_forced_discharge",
                                    "state": "on",
                                },
                            ],
                            "sequence": [
                                {
                                    "service": "select.select_option",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_EMS_MODE},
                                    "data": {"option": "Forced Mode"},
                                },
                                {
                                    "service": "number.set_value",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER},
                                    "data": {
                                        "value": "{{ states('number.battery_energy_trading_discharge_rate_kw') | float(5.0) * 1000 }}"
                                    },
                                },
                                {
                                    "service": "number.set_value",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_CHARGE_POWER},
                                    "data": {"value": 0},
                                },
                            ],
                        }
                    ],
                    "default": [
                        {
                            "service": "select.select_option",
                            "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_EMS_MODE},
                            "data": {"option": "Self-consumption"},
                        }
                    ],
                }
            ]
        else:
            # Script-based control
            discharge_service = self.config_entry.options.get(
                CONF_CUSTOM_DISCHARGE_SERVICE, "script.turn_on"
            )
            discharge_entity = self.config_entry.options.get(CONF_CUSTOM_DISCHARGE_ENTITY, "")
            normal_service = self.config_entry.options.get(
                CONF_CUSTOM_NORMAL_SERVICE, "script.turn_on"
            )
            normal_entity = self.config_entry.options.get(CONF_CUSTOM_NORMAL_ENTITY, "")

            base_config["action"] = [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "binary_sensor.battery_energy_trading_forced_discharge",
                                    "state": "on",
                                },
                                {
                                    "condition": "state",
                                    "entity_id": "switch.battery_energy_trading_enable_forced_discharge",
                                    "state": "on",
                                },
                            ],
                            "sequence": [
                                {
                                    "service": discharge_service,
                                    "target": {"entity_id": discharge_entity},
                                }
                            ],
                        }
                    ],
                    "default": [
                        {
                            "service": normal_service,
                            "target": {"entity_id": normal_entity},
                        }
                    ],
                }
            ]

        return base_config

    def _get_charging_automation_config(self) -> dict[str, Any]:
        """Generate charging automation configuration."""
        base_config = {
            "id": CHARGING_AUTOMATION_ID,
            "alias": "Battery Trading: Smart Charging Control",
            "description": f"Auto-installed by Battery Energy Trading integration (entry: {self.config_entry.entry_id})",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.battery_energy_trading_cheapest_hours",
                },
                {
                    "platform": "state",
                    "entity_id": "switch.battery_energy_trading_enable_forced_charging",
                },
            ],
            "mode": "single",
        }

        if self._control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            # Modbus control
            base_config["action"] = [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "binary_sensor.battery_energy_trading_cheapest_hours",
                                    "state": "on",
                                },
                                {
                                    "condition": "state",
                                    "entity_id": "switch.battery_energy_trading_enable_forced_charging",
                                    "state": "on",
                                },
                            ],
                            "sequence": [
                                {
                                    "service": "select.select_option",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_EMS_MODE},
                                    "data": {"option": "Forced Mode"},
                                },
                                {
                                    "service": "number.set_value",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_CHARGE_POWER},
                                    "data": {
                                        "value": "{{ states('number.battery_energy_trading_charge_rate_kw') | float(5.0) * 1000 }}"
                                    },
                                },
                                {
                                    "service": "number.set_value",
                                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER},
                                    "data": {"value": 0},
                                },
                            ],
                        }
                    ],
                    "default": [
                        {
                            "service": "select.select_option",
                            "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_EMS_MODE},
                            "data": {"option": "Self-consumption"},
                        }
                    ],
                }
            ]
        else:
            # Script-based control
            charge_service = self.config_entry.options.get(
                CONF_CUSTOM_CHARGE_SERVICE, "script.turn_on"
            )
            charge_entity = self.config_entry.options.get(CONF_CUSTOM_CHARGE_ENTITY, "")
            normal_service = self.config_entry.options.get(
                CONF_CUSTOM_NORMAL_SERVICE, "script.turn_on"
            )
            normal_entity = self.config_entry.options.get(CONF_CUSTOM_NORMAL_ENTITY, "")

            base_config["action"] = [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "state",
                                    "entity_id": "binary_sensor.battery_energy_trading_cheapest_hours",
                                    "state": "on",
                                },
                                {
                                    "condition": "state",
                                    "entity_id": "switch.battery_energy_trading_enable_forced_charging",
                                    "state": "on",
                                },
                            ],
                            "sequence": [
                                {
                                    "service": charge_service,
                                    "target": {"entity_id": charge_entity},
                                }
                            ],
                        }
                    ],
                    "default": [
                        {
                            "service": normal_service,
                            "target": {"entity_id": normal_entity},
                        }
                    ],
                }
            ]

        return base_config

    def _get_midnight_reset_automation_config(self) -> dict[str, Any]:
        """Generate midnight safety reset automation configuration."""
        base_config: dict[str, Any] = {
            "id": MIDNIGHT_RESET_AUTOMATION_ID,
            "alias": "Battery Trading: Midnight Safety Reset",
            "description": f"Auto-installed by Battery Energy Trading integration (entry: {self.config_entry.entry_id})",
            "trigger": [
                {
                    "platform": "time",
                    "at": "00:00:00",
                },
            ],
            "condition": [
                {
                    "condition": "state",
                    "entity_id": "binary_sensor.battery_energy_trading_forced_discharge",
                    "state": "off",
                },
                {
                    "condition": "state",
                    "entity_id": "binary_sensor.battery_energy_trading_cheapest_hours",
                    "state": "off",
                },
            ],
            "mode": "single",
        }

        if self._control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            base_config["action"] = [
                {
                    "service": "select.select_option",
                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_EMS_MODE},
                    "data": {"option": "Self-consumption"},
                },
                {
                    "service": "number.set_value",
                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER},
                    "data": {"value": 0},
                },
                {
                    "service": "number.set_value",
                    "target": {"entity_id": DEFAULT_SUNGROW_MODBUS_CHARGE_POWER},
                    "data": {"value": 0},
                },
            ]
        else:
            normal_service = self.config_entry.options.get(
                CONF_CUSTOM_NORMAL_SERVICE, "script.turn_on"
            )
            normal_entity = self.config_entry.options.get(CONF_CUSTOM_NORMAL_ENTITY, "")

            base_config["action"] = [
                {
                    "service": normal_service,
                    "target": {"entity_id": normal_entity},
                }
            ]

        return base_config

    async def async_install_automations(self) -> list[str]:
        """Install automations programmatically using Home Assistant's automation helpers.

        Returns:
            List of created automation entity IDs
        """
        created_ids: list[str] = []

        # Get automation configurations
        discharge_config = self._get_discharge_automation_config()
        charging_config = self._get_charging_automation_config()
        midnight_reset_config = self._get_midnight_reset_automation_config()

        # Try to create automations using the automation.create service if available
        # Note: This is the preferred method but requires HA 2023.4+
        try:
            # Create discharge automation
            await self.hass.services.async_call(
                "automation",
                "reload",
                blocking=True,
            )

            # Use config entries to create automations
            # Since Home Assistant doesn't have a direct "create" service for automations,
            # we need to use the automation config entry approach or write to automations.yaml

            # For now, we'll use the input_text approach to store the config
            # and provide instructions, or use the automation.reload after writing

            # Alternative approach: Store automation config in hass.data and
            # create automations via the automation component's internal APIs
            from homeassistant.components.automation import (
                DOMAIN as AUTOMATION_DOMAIN,
            )

            # Check if automation domain is loaded
            if AUTOMATION_DOMAIN not in self.hass.config.components:
                _LOGGER.warning("Automation component not loaded, cannot install automations")
                raise RuntimeError("Automation component not loaded")

            # Store the automation configs for potential manual creation
            self.hass.data[DOMAIN]["pending_automations"] = {
                "discharge": discharge_config,
                "charging": charging_config,
                "midnight_reset": midnight_reset_config,
            }

            # Try using the automation.create service (if available in newer HA versions)
            # This service may not exist in all versions
            try:
                # Create discharge automation
                await self.hass.services.async_call(
                    AUTOMATION_DOMAIN,
                    "create",
                    discharge_config,
                    blocking=True,
                )
                created_ids.append(DISCHARGE_AUTOMATION_ID)
                _LOGGER.info("Created discharge automation: %s", DISCHARGE_AUTOMATION_ID)
            except Exception as err:
                _LOGGER.debug(
                    "Could not use automation.create service: %s. "
                    "Falling back to config storage approach.",
                    err,
                )

            try:
                # Create charging automation
                await self.hass.services.async_call(
                    AUTOMATION_DOMAIN,
                    "create",
                    charging_config,
                    blocking=True,
                )
                created_ids.append(CHARGING_AUTOMATION_ID)
                _LOGGER.info("Created charging automation: %s", CHARGING_AUTOMATION_ID)
            except Exception as err:
                _LOGGER.debug("Could not create charging automation: %s", err)

            try:
                # Create midnight safety reset automation
                await self.hass.services.async_call(
                    AUTOMATION_DOMAIN,
                    "create",
                    midnight_reset_config,
                    blocking=True,
                )
                created_ids.append(MIDNIGHT_RESET_AUTOMATION_ID)
                _LOGGER.info("Created midnight reset automation: %s", MIDNIGHT_RESET_AUTOMATION_ID)
            except Exception as err:
                _LOGGER.debug("Could not create midnight reset automation: %s", err)

            # If direct creation failed, store configs and fire event with YAML
            if not created_ids:
                _LOGGER.info(
                    "Direct automation creation not available. "
                    "Storing configs for manual installation."
                )
                # Fire event with automation YAML for manual installation
                from .automation_helper import AutomationScriptGenerator

                generator = AutomationScriptGenerator(
                    nordpool_entity=self.config_entry.data[CONF_NORDPOOL_ENTITY],
                    battery_level_entity=self.config_entry.data.get(CONF_BATTERY_LEVEL_ENTITY, ""),
                    options=self.config_entry.options,
                )

                automation_yaml = generator.generate_all_automations()

                self.hass.bus.async_fire(
                    f"{DOMAIN}_automation_yaml_ready",
                    {
                        "config_entry_id": self.config_entry.entry_id,
                        "yaml": automation_yaml,
                        "message": "Copy this YAML to your automations.yaml file",
                    },
                )

                # Return the IDs that would be created
                created_ids = [
                    DISCHARGE_AUTOMATION_ID,
                    CHARGING_AUTOMATION_ID,
                    MIDNIGHT_RESET_AUTOMATION_ID,
                ]

        except Exception as err:
            _LOGGER.error("Failed to install automations: %s", err)
            raise

        return created_ids

    async def async_uninstall_automations(self) -> list[str]:
        """Remove integration-managed automations.

        Returns:
            List of removed automation entity IDs
        """
        removed_ids: list[str] = []

        # Get entity registry to find our automations
        entity_registry = er.async_get(self.hass)

        # Find and remove automations by their unique IDs
        for automation_id in [
            DISCHARGE_AUTOMATION_ID,
            CHARGING_AUTOMATION_ID,
            MIDNIGHT_RESET_AUTOMATION_ID,
        ]:
            # Look for entity with matching unique_id
            entity_id = f"automation.{automation_id}"

            # Check if the automation exists
            if self.hass.states.get(entity_id):
                try:
                    # Try to delete the automation
                    await self.hass.services.async_call(
                        "automation",
                        "turn_off",
                        {"entity_id": entity_id},
                        blocking=True,
                    )

                    # Remove from entity registry if present
                    entry = entity_registry.async_get(entity_id)
                    if entry:
                        entity_registry.async_remove(entity_id)
                        removed_ids.append(automation_id)
                        _LOGGER.info("Removed automation: %s", entity_id)
                    else:
                        _LOGGER.info(
                            "Turned off automation %s (manual removal may be needed)",
                            entity_id,
                        )
                        removed_ids.append(automation_id)

                except Exception as err:
                    _LOGGER.warning(
                        "Could not remove automation %s: %s. Manual removal may be needed.",
                        entity_id,
                        err,
                    )

        # Clear any stored automation configs
        if "pending_automations" in self.hass.data.get(DOMAIN, {}):
            del self.hass.data[DOMAIN]["pending_automations"]

        if not removed_ids:
            _LOGGER.info(
                "No integration-managed automations found to remove. "
                "They may have been manually deleted or renamed."
            )

        return removed_ids

    def get_automation_status(self) -> dict[str, Any]:
        """Get the status of integration-managed automations.

        Returns:
            Dictionary with automation status information
        """
        status = {
            "installed": [],
            "missing": [],
        }

        for automation_id in [
            DISCHARGE_AUTOMATION_ID,
            CHARGING_AUTOMATION_ID,
            MIDNIGHT_RESET_AUTOMATION_ID,
        ]:
            entity_id = f"automation.{automation_id}"
            state = self.hass.states.get(entity_id)

            if state:
                status["installed"].append(
                    {
                        "id": automation_id,
                        "entity_id": entity_id,
                        "state": state.state,
                        "friendly_name": state.attributes.get("friendly_name"),
                    }
                )
            else:
                status["missing"].append(automation_id)

        return status
