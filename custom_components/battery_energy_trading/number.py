"""Number platform for Battery Energy Trading."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    NUMBER_FORCED_DISCHARGE_HOURS,
    NUMBER_MIN_EXPORT_PRICE,
    NUMBER_MIN_FORCED_SELL_PRICE,
    NUMBER_MAX_FORCE_CHARGE_PRICE,
    NUMBER_FORCE_CHARGING_HOURS,
    NUMBER_FORCE_CHARGE_TARGET,
    NUMBER_MIN_BATTERY_LEVEL,
    NUMBER_MIN_SOLAR_THRESHOLD,
    NUMBER_DISCHARGE_RATE_KW,
    NUMBER_CHARGE_RATE_KW,
    DEFAULT_MIN_EXPORT_PRICE,
    DEFAULT_MIN_FORCED_SELL_PRICE,
    DEFAULT_MAX_FORCE_CHARGE_PRICE,
    DEFAULT_FORCED_DISCHARGE_HOURS,
    DEFAULT_FORCE_CHARGING_HOURS,
    DEFAULT_FORCE_CHARGE_TARGET,
    DEFAULT_MIN_BATTERY_LEVEL,
    DEFAULT_MIN_SOLAR_THRESHOLD,
    DEFAULT_DISCHARGE_RATE_KW,
    DEFAULT_CHARGE_RATE_KW,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery Energy Trading number entities."""
    # Get auto-detected rates from options if available
    options = entry.options or {}
    discharge_rate_default = options.get("discharge_rate", DEFAULT_DISCHARGE_RATE_KW)
    charge_rate_default = options.get("charge_rate", DEFAULT_CHARGE_RATE_KW)

    numbers = [
        BatteryTradingNumber(
            entry,
            NUMBER_FORCED_DISCHARGE_HOURS,
            "Forced Discharge Hours",
            0,
            24,
            1,
            DEFAULT_FORCED_DISCHARGE_HOURS,
            "hours",
            "mdi:clock-outline",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_MIN_EXPORT_PRICE,
            "Minimum Export Price",
            -0.3,
            0.1,
            0.0001,
            DEFAULT_MIN_EXPORT_PRICE,
            "EUR",
            "mdi:currency-eur",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_MIN_FORCED_SELL_PRICE,
            "Minimum Forced Sell Price",
            0,
            0.5,
            0.01,
            DEFAULT_MIN_FORCED_SELL_PRICE,
            "EUR",
            "mdi:currency-eur",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_MAX_FORCE_CHARGE_PRICE,
            "Maximum Force Charge Price",
            -0.5,
            0.20,
            0.005,
            DEFAULT_MAX_FORCE_CHARGE_PRICE,
            "EUR",
            "mdi:currency-eur",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_FORCE_CHARGING_HOURS,
            "Force Charging Hours",
            0,
            24,
            1,
            DEFAULT_FORCE_CHARGING_HOURS,
            "hours",
            "mdi:clock-outline",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_FORCE_CHARGE_TARGET,
            "Force Charge Target",
            0,
            100,
            1,
            DEFAULT_FORCE_CHARGE_TARGET,
            "%",
            "mdi:battery-charging",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_MIN_BATTERY_LEVEL,
            "Minimum Battery Discharge Level",
            10,
            50,
            1,
            DEFAULT_MIN_BATTERY_LEVEL,
            "%",
            "mdi:battery-low",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_MIN_SOLAR_THRESHOLD,
            "Minimum Solar Power Threshold",
            0,
            5000,
            100,
            DEFAULT_MIN_SOLAR_THRESHOLD,
            "W",
            "mdi:solar-power",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_DISCHARGE_RATE_KW,
            "Battery Discharge Rate",
            1.0,
            20.0,
            0.5,
            discharge_rate_default,  # Use auto-detected value
            "kW",
            "mdi:battery-arrow-up",
        ),
        BatteryTradingNumber(
            entry,
            NUMBER_CHARGE_RATE_KW,
            "Battery Charge Rate",
            1.0,
            20.0,
            0.5,
            charge_rate_default,  # Use auto-detected value
            "kW",
            "mdi:battery-arrow-down",
        ),
    ]

    async_add_entities(numbers)


class BatteryTradingNumber(NumberEntity):
    """Representation of a Battery Energy Trading number entity."""

    def __init__(
        self,
        entry: ConfigEntry,
        number_type: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        default: float,
        unit: str,
        icon: str,
    ) -> None:
        """Initialize the number entity."""
        self._entry = entry
        self._number_type = number_type
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{number_type}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_value = default
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battery Energy Trading",
            manufacturer="Battery Energy Trading",
            model="Energy Optimizer",
            sw_version="0.5.3",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
