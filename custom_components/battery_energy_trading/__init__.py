"""Battery Energy Trading Integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import CONF_NORDPOOL_ENTITY
from .coordinator import BatteryEnergyTradingCoordinator
from .sungrow_helper import SungrowHelper


_LOGGER = logging.getLogger(__name__)

DOMAIN = "battery_energy_trading"

# This integration is configured via config entries only (UI-based setup)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]

SERVICE_SYNC_SUNGROW_PARAMS = "sync_sungrow_parameters"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:  # noqa: ARG001
    """Set up the Battery Energy Trading component."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_sync_sungrow_params(call: ServiceCall) -> None:
        """Handle the service call to sync Sungrow parameters."""
        entry_id = call.data.get("entry_id")

        if not entry_id:
            # Find the first Sungrow-enabled config entry
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.options.get("auto_detected"):
                    entry_id = entry.entry_id
                    break

        if not entry_id:
            _LOGGER.error("No Battery Energy Trading integration with Sungrow auto-detection found")
            return

        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            _LOGGER.error("Config entry %s not found", entry_id)
            return

        # Get fresh Sungrow configuration
        sungrow_helper = SungrowHelper(hass)
        auto_config = await sungrow_helper.async_get_auto_configuration()

        # Update options with new values
        new_options = dict(entry.options)
        new_options["charge_rate"] = auto_config.get("recommended_charge_rate", 5.0)
        new_options["discharge_rate"] = auto_config.get("recommended_discharge_rate", 5.0)
        new_options["inverter_model"] = auto_config.get("inverter_model")

        hass.config_entries.async_update_entry(entry, options=new_options)

        _LOGGER.info(
            "Synced Sungrow parameters: charge_rate=%.1f kW, discharge_rate=%.1f kW, model=%s",
            new_options["charge_rate"],
            new_options["discharge_rate"],
            new_options["inverter_model"],
        )

    # Register service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_SUNGROW_PARAMS,
        handle_sync_sungrow_params,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
            }
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery Energy Trading from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator for Nord Pool data updates
    nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]
    coordinator = BatteryEnergyTradingCoordinator(hass, nordpool_entity)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and config data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "data": entry.data,
        "options": entry.options,
    }

    # Register automation services (only once)
    async def handle_generate_automation_scripts(call: ServiceCall) -> None:
        """Handle generate_automation_scripts service call."""
        from .automation_helper import AutomationScriptGenerator

        config_entry_id = call.data.get("config_entry_id", entry.entry_id)
        target_entry = hass.config_entries.async_get_entry(config_entry_id)

        if not target_entry:
            _LOGGER.error("Config entry %s not found", config_entry_id)
            return

        generator = AutomationScriptGenerator(
            nordpool_entity=target_entry.data[CONF_NORDPOOL_ENTITY],
            battery_level_entity=target_entry.data.get("battery_level_entity", ""),
        )

        automation_yaml = generator.generate_all_automations()

        # Store in hass.data for retrieval
        hass.data[DOMAIN][f"{config_entry_id}_automations"] = automation_yaml

        _LOGGER.info("Generated automation scripts for entry %s", config_entry_id)

        # Fire event for UI notification
        hass.bus.async_fire(
            f"{DOMAIN}_automation_generated",
            {"config_entry_id": config_entry_id, "yaml": automation_yaml},
        )

    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle force_refresh service call."""
        config_entry_id = call.data.get("config_entry_id", entry.entry_id)
        entry_data = hass.data[DOMAIN].get(config_entry_id)

        if not entry_data:
            _LOGGER.error("Config entry %s not found in hass.data", config_entry_id)
            return

        coord = entry_data["coordinator"]
        await coord.async_request_refresh()
        _LOGGER.info("Forced coordinator refresh for entry %s", config_entry_id)

    # Register services on first setup
    if not hass.services.has_service(DOMAIN, "generate_automation_scripts"):
        hass.services.async_register(
            DOMAIN,
            "generate_automation_scripts",
            handle_generate_automation_scripts,
        )

    if not hass.services.has_service(DOMAIN, "force_refresh"):
        hass.services.async_register(
            DOMAIN,
            "force_refresh",
            handle_force_refresh,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
