"""Sungrow integration helper for automatic parameter detection."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Inverter model specifications (based on official Sungrow datasheets)
SUNGROW_INVERTER_SPECS = {
    "SH5.0RT": {"max_charge_kw": 5.0, "max_discharge_kw": 5.0},
    "SH5.0RT-20": {"max_charge_kw": 5.0, "max_discharge_kw": 5.0},
    "SH6.0RT": {"max_charge_kw": 6.0, "max_discharge_kw": 6.0},
    "SH6.0RT-20": {"max_charge_kw": 6.0, "max_discharge_kw": 6.0},
    "SH8.0RT": {"max_charge_kw": 8.0, "max_discharge_kw": 8.0},
    "SH8.0RT-20": {"max_charge_kw": 8.0, "max_discharge_kw": 8.0},
    "SH10RT": {"max_charge_kw": 10.0, "max_discharge_kw": 10.0},
    "SH10RT-20": {"max_charge_kw": 10.0, "max_discharge_kw": 10.0},
    "SH3.6RS": {"max_charge_kw": 3.6, "max_discharge_kw": 3.6},
    "SH4.6RS": {"max_charge_kw": 4.6, "max_discharge_kw": 4.6},
    "SH5.0RS": {"max_charge_kw": 5.0, "max_discharge_kw": 5.0},
    "SH6.0RS": {"max_charge_kw": 6.0, "max_discharge_kw": 6.0},
}


# Common Sungrow Modbus entity patterns
# Based on actual Sungrow-SHx-Inverter-Modbus-Home-Assistant integration
# Patterns are ordered by priority: exact matches first, then fuzzy matches
SUNGROW_ENTITY_PATTERNS = {
    "battery_level": [
        # Exact matches from Sungrow Modbus integration (unique_id: sg_battery_level)
        r"^sensor\.battery_level$",  # Primary: sensor.battery_level (address 13022)
        r"^sensor\.battery_level_nominal$",  # Alternative: calculated between min/max SoC
        # Fuzzy matches for other naming conventions
        r"^sensor\..*sungrow.*battery.*level$",
        r"^sensor\..*sungrow.*battery.*soc$",
        r"^sensor\..*sungrow.*soc$",
        r"^sensor\.sh\d+\.?rt.*battery.*level$",
        r"^sensor\.battery_soc$",
    ],
    "battery_capacity": [
        # Exact matches from Sungrow Modbus integration (unique_id: sg_battery_capacity)
        r"^sensor\.battery_capacity$",  # Primary: sensor.battery_capacity (address 5638)
        r"^sensor\.battery_charge$",  # Alternative: Current charge in kWh
        r"^sensor\.battery_charge_nominal$",  # Alternative: Nominal capacity
        r"^sensor\.battery_charge_health_rated$",  # Alternative: Health-adjusted capacity
        # Fuzzy matches for other naming conventions
        r"^sensor\..*sungrow.*battery.*capacity$",
        r"^sensor\..*sungrow.*capacity$",
        r"^sensor\.sh\d+\.?rt.*capacity$",
    ],
    "solar_power": [
        # Exact matches from Sungrow Modbus integration (unique_id: sg_total_dc_power)
        r"^sensor\.total_dc_power$",  # Primary: sensor.total_dc_power (address 5016) - Total from all MPPT strings
        # Fuzzy matches for other naming conventions
        r"^sensor\..*sungrow.*pv.*power$",
        r"^sensor\..*sungrow.*total.*pv$",
        r"^sensor\..*sungrow.*solar.*power$",
        r"^sensor\..*sungrow.*total.*dc.*power$",
        r"^sensor\.sh\d+\.?rt.*pv.*power$",
        r"^sensor\.pv_power$",
        r"^sensor\.solar_power$",
    ],
    "device_type": [
        # Exact matches from Sungrow Modbus integration (unique_id: sg_sungrow_device_type)
        r"^sensor\.sungrow_device_type$",  # Primary: sensor.sungrow_device_type (template sensor)
        r"^sensor\.sungrow_device_type_code$",  # Alternative: Raw device type code
        # Fuzzy matches for other naming conventions
        r"^sensor\..*sungrow.*device.*type$",
        r"^sensor\..*sungrow.*model$",
        r"^sensor\.sh\d+\.?rt.*type$",
    ],
}


class SungrowHelper:
    """Helper class for Sungrow integration auto-detection."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Sungrow helper."""
        self.hass = hass

    def detect_sungrow_entities(self) -> dict[str, str | None]:
        """
        Auto-detect Sungrow entities in Home Assistant.

        Returns:
            Dictionary with detected entity IDs for battery_level, battery_capacity, and solar_power
        """
        detected = {
            "battery_level": None,
            "battery_capacity": None,
            "solar_power": None,
            "device_type": None,
        }

        all_entities = self.hass.states.async_all()

        for entity_type, patterns in SUNGROW_ENTITY_PATTERNS.items():
            for entity in all_entities:
                entity_id = entity.entity_id.lower()

                # Check if entity matches any pattern
                for pattern in patterns:
                    if re.match(pattern, entity_id):
                        detected[entity_type] = entity.entity_id
                        _LOGGER.info(
                            "Auto-detected Sungrow %s entity: %s",
                            entity_type,
                            entity.entity_id,
                        )
                        break

                if detected[entity_type]:
                    break

        return detected

    def get_inverter_specs(self, model_name: str | None) -> dict[str, float] | None:
        """
        Get inverter specifications based on model name.

        Args:
            model_name: Sungrow inverter model name (e.g., "SH10RT")

        Returns:
            Dictionary with max_charge_kw and max_discharge_kw, or None if not found
        """
        if not model_name:
            return None

        # Normalize model name
        model_name = model_name.upper().strip()

        # Try exact match first
        if model_name in SUNGROW_INVERTER_SPECS:
            return SUNGROW_INVERTER_SPECS[model_name]

        # Try fuzzy match (e.g., extract "SH10RT" from "SH10RT V1.1.2")
        for known_model in SUNGROW_INVERTER_SPECS:
            if known_model in model_name:
                return SUNGROW_INVERTER_SPECS[known_model]

        _LOGGER.warning("Unknown Sungrow inverter model: %s", model_name)
        return None

    def detect_inverter_model_from_entities(self) -> str | None:
        """
        Try to detect inverter model from entity names or attributes.

        Returns:
            Detected inverter model name, or None
        """
        all_entities = self.hass.states.async_all()

        # Look for device type sensor
        for entity in all_entities:
            entity_id = entity.entity_id.lower()

            # Check device type sensors
            if "sungrow" in entity_id and "device" in entity_id:
                state_value = entity.state
                if state_value and state_value.upper().startswith("SH"):
                    return state_value

            # Check entity attributes for model information
            if "sungrow" in entity_id:
                attrs = entity.attributes
                if isinstance(attrs, dict):
                    # Look for model in attributes
                    for key in ["model", "device_model", "inverter_model"]:
                        if key in attrs and attrs[key]:
                            model = attrs[key]
                            if isinstance(model, str) and model.upper().startswith("SH"):
                                return model

            # Try to extract model from entity ID (e.g., sensor.sh10rt_battery_level)
            match = re.search(r"sh\d+\.?\d*rt", entity_id)
            if match:
                model = match.group(0).upper().replace(".", "")
                return model

        return None

    async def async_get_auto_configuration(self) -> dict[str, Any]:
        """
        Get complete auto-configuration for Sungrow systems.

        Returns:
            Dictionary with detected entities and recommended settings
        """
        detected_entities = self.detect_sungrow_entities()
        inverter_model = self.detect_inverter_model_from_entities()

        config = {
            "detected_entities": detected_entities,
            "inverter_model": inverter_model,
            "inverter_specs": None,
            "recommended_charge_rate": 5.0,  # Default
            "recommended_discharge_rate": 5.0,  # Default
            "battery_capacity": None,
        }

        # Get inverter specs if model detected
        if inverter_model:
            specs = self.get_inverter_specs(inverter_model)
            if specs:
                config["inverter_specs"] = specs
                config["recommended_charge_rate"] = specs["max_charge_kw"]
                config["recommended_discharge_rate"] = specs["max_discharge_kw"]

        # Get battery capacity from entity state (dynamically read from actual battery)
        if detected_entities.get("battery_capacity"):
            capacity_entity = self.hass.states.get(detected_entities["battery_capacity"])
            if capacity_entity:
                try:
                    capacity = float(capacity_entity.state)
                    config["battery_capacity"] = capacity
                    _LOGGER.info("Detected battery capacity: %.1f kWh", capacity)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Could not read battery capacity from %s: %s",
                        detected_entities["battery_capacity"],
                        err,
                    )

        _LOGGER.info("Auto-configuration detected: %s", config)
        return config

    def is_sungrow_integration_available(self) -> bool:
        """
        Check if Sungrow integration is installed and has entities.

        Checks for either:
        - Entities with "sungrow" in the name
        - Known Sungrow Modbus entity patterns (battery_level, battery_capacity, total_dc_power)

        Returns:
            True if Sungrow entities are found
        """
        all_entities = self.hass.states.async_all()

        # Check for "sungrow" prefix entities (common pattern)
        if any("sungrow" in entity.entity_id.lower() for entity in all_entities):
            return True

        # Check for exact Sungrow Modbus entity names (address-based entities)
        sungrow_modbus_entities = {
            "sensor.battery_level",  # sg_battery_level
            "sensor.battery_capacity",  # sg_battery_capacity
            "sensor.total_dc_power",  # sg_total_dc_power
            "sensor.sungrow_device_type",  # Template sensor
        }

        entity_ids = {entity.entity_id.lower() for entity in all_entities}
        return any(modbus_entity in entity_ids for modbus_entity in sungrow_modbus_entities)
