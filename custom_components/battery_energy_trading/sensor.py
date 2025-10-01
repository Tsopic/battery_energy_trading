"""Sensor platform for Battery Energy Trading."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    SENSOR_ARBITRAGE_OPPORTUNITIES,
    SENSOR_DISCHARGE_HOURS,
    SENSOR_CHARGING_HOURS,
    SENSOR_PROFITABLE_HOURS,
    SENSOR_ECONOMICAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery Energy Trading sensors."""
    nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]

    sensors = [
        ArbitrageOpportunitiesSensor(hass, entry, nordpool_entity),
        DischargeHoursSensor(hass, entry, nordpool_entity),
        ChargingHoursSensor(hass, entry, nordpool_entity),
        ProfitableHoursSensor(hass, entry, nordpool_entity),
        EconomicalHoursSensor(hass, entry, nordpool_entity),
    ]

    async_add_entities(sensors)


class BatteryTradingSensor(SensorEntity):
    """Base class for Battery Energy Trading sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._nordpool_entity = nordpool_entity
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{sensor_type}"
        self._attr_has_entity_name = True

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        @callback
        def sensor_state_listener(event):
            """Handle state changes."""
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._nordpool_entity], sensor_state_listener
            )
        )


class ArbitrageOpportunitiesSensor(BatteryTradingSensor):
    """Sensor for detecting arbitrage opportunities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the arbitrage sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_ARBITRAGE_OPPORTUNITIES)
        self._attr_name = "Arbitrage Opportunities"
        self._attr_icon = "mdi:chart-line"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return "No data available"

        raw_today = nordpool_state.attributes.get("raw_today", [])
        if not raw_today or len(raw_today) < 3:
            return "Insufficient data"

        threshold = 100  # Price difference threshold in points
        best_opportunity = {
            "charge_start_hour": 0,
            "charge_end_hour": 1,
            "discharge_hour": 2,
            "difference": 0,
        }

        for i in range(len(raw_today) - 2):
            charge_price = (raw_today[i]["value"] + raw_today[i + 1]["value"]) / 2

            for j in range(i + 2, len(raw_today)):
                discharge_price = raw_today[j]["value"]
                price_difference = (discharge_price - charge_price) * 1000

                if price_difference > threshold and price_difference > best_opportunity["difference"]:
                    best_opportunity = {
                        "charge_start_hour": raw_today[i]["start"].hour,
                        "charge_end_hour": raw_today[i + 1]["end"].hour,
                        "discharge_hour": raw_today[j]["start"].hour,
                        "difference": price_difference,
                    }

        if best_opportunity["difference"] > 0:
            return f"Charge {best_opportunity['charge_start_hour']}-{best_opportunity['charge_end_hour']}, Discharge {best_opportunity['discharge_hour']} ({best_opportunity['difference']:.0f} points)"

        return f"No opportunities (threshold: {threshold} points)"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"threshold": 100, "unit": "points"}


class DischargeHoursSensor(BatteryTradingSensor):
    """Sensor for selected discharge hours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the discharge hours sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_DISCHARGE_HOURS)
        self._attr_name = "Selected Discharge Hours"
        self._attr_icon = "mdi:battery-arrow-up"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        # Implementation similar to template sensor logic
        return "Implementation pending"


class ChargingHoursSensor(BatteryTradingSensor):
    """Sensor for selected charging hours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the charging hours sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_CHARGING_HOURS)
        self._attr_name = "Selected Charging Hours"
        self._attr_icon = "mdi:battery-arrow-down"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return "Implementation pending"


class ProfitableHoursSensor(BatteryTradingSensor):
    """Sensor for profitable sell hours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the profitable hours sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_PROFITABLE_HOURS)
        self._attr_name = "Profitable Sell Hours"
        self._attr_icon = "mdi:currency-eur"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return "Implementation pending"


class EconomicalHoursSensor(BatteryTradingSensor):
    """Sensor for economical charge hours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, nordpool_entity: str) -> None:
        """Initialize the economical hours sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_ECONOMICAL_HOURS)
        self._attr_name = "Economical Charge Hours"
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return "Implementation pending"
