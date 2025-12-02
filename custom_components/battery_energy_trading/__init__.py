"""Battery Energy Trading Integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .ai import AIConfig, AITrainer
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

    async def handle_generate_automation_scripts(call: ServiceCall) -> None:
        """Handle generate_automation_scripts service call."""
        from .automation_helper import AutomationScriptGenerator

        config_entry_id = call.data.get("config_entry_id")

        # Find first entry if not specified
        if not config_entry_id:
            entries = hass.config_entries.async_entries(DOMAIN)
            if entries:
                config_entry_id = entries[0].entry_id
            else:
                _LOGGER.error("No Battery Energy Trading config entries found")
                return

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
        config_entry_id = call.data.get("config_entry_id")

        # Find first entry if not specified
        if not config_entry_id:
            entries = hass.config_entries.async_entries(DOMAIN)
            if entries:
                config_entry_id = entries[0].entry_id
            else:
                _LOGGER.error("No Battery Energy Trading config entries found")
                return

        entry_data = hass.data[DOMAIN].get(config_entry_id)

        if not entry_data:
            _LOGGER.error("Config entry %s not found in hass.data", config_entry_id)
            return

        coord = entry_data["coordinator"]
        await coord.async_request_refresh()
        _LOGGER.info("Forced coordinator refresh for entry %s", config_entry_id)

    # Register services
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

    hass.services.async_register(
        DOMAIN,
        "generate_automation_scripts",
        handle_generate_automation_scripts,
    )

    hass.services.async_register(
        DOMAIN,
        "force_refresh",
        handle_force_refresh,
    )

    # AI Services
    async def handle_train_ai_models(call: ServiceCall) -> None:
        """Handle train AI models service."""
        entry_data = next(iter(hass.data.get(DOMAIN, {}).values()), None)
        if not entry_data or "ai_trainer" not in entry_data:
            raise HomeAssistantError("AI trainer not available")

        trainer = entry_data["ai_trainer"]
        _days = call.data.get("days_of_data", 90)

        result = await trainer.train_all_models()

        hass.bus.async_fire(
            f"{DOMAIN}_ai_training_complete",
            {"success": result["success"], "metrics": result.get("models", {})},
        )

    async def handle_get_ai_prediction(call: ServiceCall) -> dict[str, Any]:  # noqa: ARG001
        """Handle get AI prediction service."""
        entry_data = next(iter(hass.data.get(DOMAIN, {}).values()), None)
        if not entry_data or "ai_trainer" not in entry_data:
            raise HomeAssistantError("AI trainer not available")

        trainer = entry_data["ai_trainer"]
        coordinator = entry_data["coordinator"]

        if not trainer.decision_optimizer or not trainer.decision_optimizer.is_trained:
            return {"recommendation": "HOLD", "confidence": 0, "reason": "AI not trained"}

        # Get current state from coordinator
        current_price = coordinator.data.get("current_price", 0.10)
        prices_today = coordinator.data.get("raw_today", [])

        # Get battery level from config (would need actual entity state in production)
        battery_level = 50  # Default placeholder

        # Get recommendation
        action, confidence = trainer.decision_optimizer.get_recommendation(
            battery_level=int(battery_level / 20),  # Discretize
            price_level=_get_price_level(current_price, prices_today),
            solar_level=1,  # Placeholder
            load_level=1,  # Placeholder
            hour_period=_get_hour_period(),
        )

        return {
            "recommendation": action.name,
            "confidence": round(confidence, 2),
            "reason": f"Based on current price {current_price:.3f} EUR/kWh",
        }

    async def handle_set_ai_mode(call: ServiceCall) -> None:
        """Handle set AI mode service."""
        enabled = call.data.get("enabled", False)

        for entry_data in hass.data.get(DOMAIN, {}).values():
            if isinstance(entry_data, dict):
                entry_data["ai_enabled"] = enabled

        hass.bus.async_fire(f"{DOMAIN}_ai_mode_changed", {"enabled": enabled})

    hass.services.async_register(
        DOMAIN,
        "train_ai_models",
        handle_train_ai_models,
        schema=vol.Schema(
            {
                vol.Optional("days_of_data", default=90): vol.All(
                    vol.Coerce(int), vol.Range(min=30, max=365)
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        "get_ai_prediction",
        handle_get_ai_prediction,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "set_ai_mode",
        handle_set_ai_mode,
        schema=vol.Schema(
            {
                vol.Required("enabled"): cv.boolean,
            }
        ),
    )

    return True


def _get_price_level(price: float, prices: list[dict[str, Any]]) -> int:
    """Get price level (0-4) based on percentile."""
    from datetime import datetime

    values = [p.get("value", 0) for p in prices if isinstance(p.get("start"), datetime)]
    if not values:
        return 2

    percentile = sum(1 for v in values if v < price) / len(values) * 100
    if percentile < 20:
        return 0
    if percentile < 40:
        return 1
    if percentile < 60:
        return 2
    if percentile < 80:
        return 3
    return 4


def _get_hour_period() -> int:
    """Get current hour period (0-5)."""
    from datetime import datetime

    return datetime.now().hour // 4


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery Energy Trading from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator for Nord Pool data updates
    nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]
    coordinator = BatteryEnergyTradingCoordinator(hass, nordpool_entity)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Initialize AI trainer
    ai_config = AIConfig(
        nordpool_entity=nordpool_entity,
        battery_level_entity=entry.data.get("battery_level_entity", ""),
        battery_capacity_entity=entry.data.get("battery_capacity_entity", ""),
        solar_power_entity=entry.data.get("solar_power_entity", ""),
        load_power_entity=entry.data.get("load_power_entity", ""),
    )
    ai_trainer = AITrainer(hass, ai_config)

    # Try to load existing models
    try:
        await ai_trainer.load_models()
    except Exception as err:
        _LOGGER.debug("Could not load AI models: %s", err)

    # Store coordinator, config data, and AI trainer
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "data": entry.data,
        "options": entry.options,
        "ai_trainer": ai_trainer,
        "ai_enabled": False,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
