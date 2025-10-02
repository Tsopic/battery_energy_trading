"""Binary sensor platform for Battery Energy Trading."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    VERSION,
    CONF_NORDPOOL_ENTITY,
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_BATTERY_CAPACITY_ENTITY,
    CONF_SOLAR_POWER_ENTITY,
    CONF_SOLAR_FORECAST_ENTITY,
    BINARY_SENSOR_FORCED_DISCHARGE,
    BINARY_SENSOR_LOW_PRICE,
    BINARY_SENSOR_EXPORT_PROFITABLE,
    BINARY_SENSOR_CHEAPEST_HOURS,
    BINARY_SENSOR_BATTERY_LOW,
    BINARY_SENSOR_SOLAR_AVAILABLE,
    NUMBER_MIN_EXPORT_PRICE,
    NUMBER_MIN_FORCED_SELL_PRICE,
    NUMBER_MAX_FORCE_CHARGE_PRICE,
    NUMBER_MIN_BATTERY_LEVEL,
    NUMBER_MIN_SOLAR_THRESHOLD,
    NUMBER_FORCE_CHARGE_TARGET,
    NUMBER_FORCED_DISCHARGE_HOURS,
    NUMBER_DISCHARGE_RATE_KW,
    NUMBER_CHARGE_RATE_KW,
    NUMBER_BATTERY_LOW_THRESHOLD,
    SWITCH_ENABLE_FORCED_CHARGING,
    SWITCH_ENABLE_FORCED_DISCHARGE,
    SWITCH_ENABLE_EXPORT_MANAGEMENT,
    SWITCH_ENABLE_MULTIDAY_OPTIMIZATION,
    DEFAULT_MIN_EXPORT_PRICE,
    DEFAULT_MIN_FORCED_SELL_PRICE,
    DEFAULT_MAX_FORCE_CHARGE_PRICE,
    DEFAULT_MIN_BATTERY_LEVEL,
    DEFAULT_MIN_SOLAR_THRESHOLD,
    DEFAULT_FORCE_CHARGE_TARGET,
    DEFAULT_FORCED_DISCHARGE_HOURS,
    DEFAULT_DISCHARGE_RATE_KW,
    DEFAULT_CHARGE_RATE_KW,
    DEFAULT_BATTERY_LOW_THRESHOLD,
)
from .energy_optimizer import EnergyOptimizer
from .base_entity import BatteryTradingBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery Energy Trading binary sensors."""
    nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]
    battery_level_entity = entry.data[CONF_BATTERY_LEVEL_ENTITY]
    battery_capacity_entity = entry.data[CONF_BATTERY_CAPACITY_ENTITY]
    solar_power_entity = entry.data.get(CONF_SOLAR_POWER_ENTITY)
    solar_forecast_entity = entry.data.get(CONF_SOLAR_FORECAST_ENTITY)

    optimizer = EnergyOptimizer()

    sensors = [
        ForcedDischargeSensor(
            hass, entry, nordpool_entity, battery_level_entity, battery_capacity_entity,
            solar_power_entity, solar_forecast_entity, optimizer
        ),
        LowPriceSensor(hass, entry, nordpool_entity),
        ExportProfitableSensor(hass, entry, nordpool_entity),
        CheapestHoursSensor(hass, entry, nordpool_entity, battery_level_entity, battery_capacity_entity, solar_forecast_entity, optimizer),
        BatteryLowSensor(hass, entry, battery_level_entity),
    ]

    if solar_power_entity:
        sensors.append(SolarAvailableSensor(hass, entry, solar_power_entity))

    async_add_entities(sensors)


class BatteryTradingBinarySensor(BatteryTradingBaseEntity, BinarySensorEntity):
    """Base class for Battery Energy Trading binary sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        sensor_type: str,
        tracked_entities: list[str],
    ) -> None:
        """Initialize the binary sensor."""
        # Initialize base entity first
        super().__init__(hass, entry, sensor_type)

        # Add binary sensor-specific attributes
        self._sensor_type = sensor_type
        self._tracked_entities = tracked_entities
        self._attr_suggested_object_id = f"{DOMAIN}_{sensor_type}"

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        @callback
        def sensor_state_listener(event):
            """Handle state changes."""
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._tracked_entities, sensor_state_listener
            )
        )


class ForcedDischargeSensor(BatteryTradingBinarySensor):
    """Binary sensor for forced discharge timer."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        battery_level_entity: str,
        battery_capacity_entity: str,
        solar_power_entity: str | None,
        solar_forecast_entity: str | None,
        optimizer: EnergyOptimizer,
    ) -> None:
        """Initialize the forced discharge sensor."""
        tracked = [nordpool_entity, battery_level_entity, battery_capacity_entity]
        if solar_power_entity:
            tracked.append(solar_power_entity)
        if solar_forecast_entity:
            tracked.append(solar_forecast_entity)

        super().__init__(hass, entry, BINARY_SENSOR_FORCED_DISCHARGE, tracked)
        self._nordpool_entity = nordpool_entity
        self._battery_level_entity = battery_level_entity
        self._battery_capacity_entity = battery_capacity_entity
        self._solar_power_entity = solar_power_entity
        self._solar_forecast_entity = solar_forecast_entity
        self._optimizer = optimizer
        self._attr_name = "Forced Discharge"
        self._attr_device_class = "power"

    @property
    def is_on(self) -> bool:
        """Return true if forced discharge should be active."""
        try:
            # Check if forced discharge is enabled
            if not self._get_switch_state(SWITCH_ENABLE_FORCED_DISCHARGE):
                return False

            # Get configuration values from number entities
            min_battery_level = self._get_number_entity_value(NUMBER_MIN_BATTERY_LEVEL, DEFAULT_MIN_BATTERY_LEVEL)
            min_solar_threshold = self._get_number_entity_value(NUMBER_MIN_SOLAR_THRESHOLD, DEFAULT_MIN_SOLAR_THRESHOLD)
            min_sell_price = self._get_number_entity_value(NUMBER_MIN_FORCED_SELL_PRICE, DEFAULT_MIN_FORCED_SELL_PRICE)
            discharge_rate = self._get_number_entity_value(NUMBER_DISCHARGE_RATE_KW, DEFAULT_DISCHARGE_RATE_KW)
            forced_discharge_hours = self._get_number_entity_value(NUMBER_FORCED_DISCHARGE_HOURS, DEFAULT_FORCED_DISCHARGE_HOURS)

            # Get entity states
            battery_capacity = self._get_float_state(self._battery_capacity_entity, 0)
            battery_level = self._get_float_state(self._battery_level_entity, 0)
            solar_power = self._get_float_state(self._solar_power_entity, 0) if self._solar_power_entity else 0

            # Check basic conditions
            if battery_capacity <= 0:
                return False

            # Allow discharge if battery is above minimum OR solar is generating
            if battery_level <= min_battery_level and solar_power < min_solar_threshold:
                return False

            # Check if current time is in high-price discharge slots
            nordpool_state = self.hass.states.get(self._nordpool_entity)
            if not nordpool_state:
                return False

            raw_today = nordpool_state.attributes.get("raw_today", [])
            if not raw_today:
                return False

            # Get tomorrow's prices and multi-day optimization setting
            raw_tomorrow = nordpool_state.attributes.get("raw_tomorrow")
            multiday_enabled = self._get_switch_state(SWITCH_ENABLE_MULTIDAY_OPTIMIZATION)

            # Get solar forecast data if available
            solar_forecast_data = None
            if self._solar_forecast_entity and multiday_enabled:
                solar_forecast_state = self.hass.states.get(self._solar_forecast_entity)
                if solar_forecast_state:
                    solar_forecast_data = solar_forecast_state.attributes

            # 0 = unlimited (use battery capacity limit only)
            max_hours = None if forced_discharge_hours == 0 else forced_discharge_hours

            # Get discharge slots using shared optimizer with multi-day support
            discharge_slots = self._optimizer.select_discharge_slots(
                raw_today,
                min_sell_price,
                battery_capacity,
                battery_level,
                discharge_rate=discharge_rate,
                max_hours=max_hours,
                raw_tomorrow=raw_tomorrow,
                solar_forecast_data=solar_forecast_data,
                multiday_enabled=multiday_enabled,
            )

            # Check if we're currently in a discharge slot
            return self._optimizer.is_current_slot_selected(discharge_slots)
        except Exception as err:
            _LOGGER.error("Error checking forced discharge state: %s", err, exc_info=True)
            return False

class LowPriceSensor(BatteryTradingBinarySensor):
    """Binary sensor for low price detection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the low price sensor."""
        super().__init__(hass, entry, BINARY_SENSOR_LOW_PRICE, [nordpool_entity])
        self._nordpool_entity = nordpool_entity
        self._attr_name = "Low Price Mode"
        self._attr_icon = "mdi:currency-eur-off"

    @property
    def is_on(self) -> bool:
        """Return true if price is low."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return False

        try:
            current_price = float(nordpool_state.state)
            return current_price <= DEFAULT_MIN_EXPORT_PRICE
        except (ValueError, TypeError):
            return False


class ExportProfitableSensor(BatteryTradingBinarySensor):
    """Binary sensor for export profitable detection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the export profitable sensor."""
        super().__init__(hass, entry, BINARY_SENSOR_EXPORT_PROFITABLE, [nordpool_entity])
        self._nordpool_entity = nordpool_entity
        self._attr_name = "Export Profitable"
        self._attr_icon = "mdi:transmission-tower-export"

    @property
    def is_on(self) -> bool:
        """Return true if export is profitable."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return False

        try:
            current_price = float(nordpool_state.state)
            return current_price > DEFAULT_MIN_EXPORT_PRICE
        except (ValueError, TypeError):
            return False


class CheapestHoursSensor(BatteryTradingBinarySensor):
    """Binary sensor for cheapest hours detection."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        battery_level_entity: str,
        battery_capacity_entity: str,
        solar_forecast_entity: str | None,
        optimizer: EnergyOptimizer,
    ) -> None:
        """Initialize the cheapest hours sensor."""
        tracked = [nordpool_entity, battery_level_entity, battery_capacity_entity]
        if solar_forecast_entity:
            tracked.append(solar_forecast_entity)
        super().__init__(hass, entry, BINARY_SENSOR_CHEAPEST_HOURS, tracked)
        self._nordpool_entity = nordpool_entity
        self._battery_level_entity = battery_level_entity
        self._battery_capacity_entity = battery_capacity_entity
        self._solar_forecast_entity = solar_forecast_entity
        self._optimizer = optimizer
        self._attr_name = "Cheapest Hours"
        self._attr_icon = "mdi:clock-check"

    @property
    def is_on(self) -> bool:
        """Return true if current time is in cheapest charging hours."""
        # Check if forced charging is enabled
        if not self._get_switch_state(SWITCH_ENABLE_FORCED_CHARGING):
            return False

        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return False

        raw_today = nordpool_state.attributes.get("raw_today", [])
        if not raw_today:
            return False

        # Get tomorrow's prices and multi-day optimization setting
        raw_tomorrow = nordpool_state.attributes.get("raw_tomorrow")
        multiday_enabled = self._get_switch_state(SWITCH_ENABLE_MULTIDAY_OPTIMIZATION)

        # Get solar forecast data if available
        solar_forecast_data = None
        if self._solar_forecast_entity and multiday_enabled:
            solar_forecast_state = self.hass.states.get(self._solar_forecast_entity)
            if solar_forecast_state:
                solar_forecast_data = solar_forecast_state.attributes

        # Get configuration values from number entities
        battery_capacity = self._get_float_state(self._battery_capacity_entity, 10.0)
        battery_level = self._get_float_state(self._battery_level_entity, 0.0)
        max_charge_price = self._get_number_entity_value(NUMBER_MAX_FORCE_CHARGE_PRICE, DEFAULT_MAX_FORCE_CHARGE_PRICE)
        target_level = self._get_number_entity_value(NUMBER_FORCE_CHARGE_TARGET, DEFAULT_FORCE_CHARGE_TARGET)
        charge_rate = self._get_number_entity_value(NUMBER_CHARGE_RATE_KW, DEFAULT_CHARGE_RATE_KW)

        # Get charging slots from optimizer with multi-day support
        charging_slots = self._optimizer.select_charging_slots(
            raw_today,
            max_charge_price,
            battery_capacity,
            battery_level,
            target_level,
            charge_rate=charge_rate,
            raw_tomorrow=raw_tomorrow,
            solar_forecast_data=solar_forecast_data,
            multiday_enabled=multiday_enabled,
        )

        # Check if we're currently in a charging slot
        return self._optimizer.is_current_slot_selected(charging_slots)


class BatteryLowSensor(BatteryTradingBinarySensor):
    """Binary sensor for low battery detection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, battery_level_entity: str) -> None:
        """Initialize the battery low sensor."""
        super().__init__(hass, entry, BINARY_SENSOR_BATTERY_LOW, [battery_level_entity])
        self._battery_level_entity = battery_level_entity
        self._attr_name = "Battery Low"
        self._attr_device_class = "battery"

    @property
    def is_on(self) -> bool:
        """Return true if battery is below configured threshold."""
        state = self.hass.states.get(self._battery_level_entity)
        if not state or state.state in ("unknown", "unavailable"):
            return False

        try:
            battery_level = float(state.state)
            threshold = self._get_number_entity_value(NUMBER_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD)
            return battery_level < threshold
        except (ValueError, TypeError):
            return False


class SolarAvailableSensor(BatteryTradingBinarySensor):
    """Binary sensor for solar power availability."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, solar_power_entity: str) -> None:
        """Initialize the solar available sensor."""
        super().__init__(hass, entry, BINARY_SENSOR_SOLAR_AVAILABLE, [solar_power_entity])
        self._solar_power_entity = solar_power_entity
        self._attr_name = "Solar Power Available"
        self._attr_icon = "mdi:solar-power"

    @property
    def is_on(self) -> bool:
        """Return true if solar power is available."""
        state = self.hass.states.get(self._solar_power_entity)
        if not state or state.state in ("unknown", "unavailable"):
            return False

        try:
            solar_power = float(state.state)
            return solar_power >= DEFAULT_MIN_SOLAR_THRESHOLD
        except (ValueError, TypeError):
            return False
