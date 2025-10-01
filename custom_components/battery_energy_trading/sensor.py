"""Sensor platform for Battery Energy Trading."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_BATTERY_CAPACITY_ENTITY,
    SENSOR_ARBITRAGE_OPPORTUNITIES,
    SENSOR_DISCHARGE_HOURS,
    SENSOR_CHARGING_HOURS,
    SENSOR_PROFITABLE_HOURS,
    SENSOR_ECONOMICAL_HOURS,
    NUMBER_MIN_FORCED_SELL_PRICE,
    NUMBER_MAX_FORCE_CHARGE_PRICE,
    NUMBER_FORCE_CHARGE_TARGET,
    NUMBER_FORCED_DISCHARGE_HOURS,
    NUMBER_DISCHARGE_RATE_KW,
    NUMBER_CHARGE_RATE_KW,
    DEFAULT_MIN_FORCED_SELL_PRICE,
    DEFAULT_MAX_FORCE_CHARGE_PRICE,
    DEFAULT_FORCE_CHARGE_TARGET,
    DEFAULT_FORCED_DISCHARGE_HOURS,
    DEFAULT_DISCHARGE_RATE_KW,
    DEFAULT_CHARGE_RATE_KW,
)
from .energy_optimizer import EnergyOptimizer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery Energy Trading sensors."""
    nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]
    battery_level_entity = entry.data[CONF_BATTERY_LEVEL_ENTITY]
    battery_capacity_entity = entry.data[CONF_BATTERY_CAPACITY_ENTITY]

    optimizer = EnergyOptimizer()

    sensors = [
        ArbitrageOpportunitiesSensor(hass, entry, nordpool_entity, battery_capacity_entity, optimizer),
        DischargeHoursSensor(hass, entry, nordpool_entity, battery_level_entity, battery_capacity_entity, optimizer),
        ChargingHoursSensor(hass, entry, nordpool_entity, battery_level_entity, battery_capacity_entity, optimizer),
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
        tracked_entities: list[str] | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._nordpool_entity = nordpool_entity
        self._sensor_type = sensor_type
        self._tracked_entities = tracked_entities or [nordpool_entity]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{sensor_type}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battery Energy Trading",
            manufacturer="Battery Energy Trading",
            model="Energy Optimizer",
            sw_version="0.5.3",
        )

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

    def _get_float_state(self, entity_id: str | None, default: float = 0.0) -> float:
        """Get float value from entity state."""
        if not entity_id:
            return default

        state = self.hass.states.get(entity_id)
        if not state or state.state in ("unknown", "unavailable"):
            return default

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return default

    def _get_number_entity_value(self, number_type: str, default: float) -> float:
        """Get value from number entity."""
        entity_id = f"number.{DOMAIN}_{self._entry.entry_id}_{number_type}"
        return self._get_float_state(entity_id, default)


class ArbitrageOpportunitiesSensor(BatteryTradingSensor):
    """Sensor for detecting arbitrage opportunities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        battery_capacity_entity: str,
        optimizer: EnergyOptimizer,
    ) -> None:
        """Initialize the arbitrage sensor."""
        super().__init__(hass, entry, nordpool_entity, SENSOR_ARBITRAGE_OPPORTUNITIES, [nordpool_entity, battery_capacity_entity])
        self._battery_capacity_entity = battery_capacity_entity
        self._optimizer = optimizer
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

        battery_capacity = self._get_float_state(self._battery_capacity_entity, 10.0)

        opportunities = self._optimizer.calculate_arbitrage_opportunities(
            raw_today,
            battery_capacity,
            min_profit_threshold=0.50,  # Minimum 0.50 EUR profit
        )

        if opportunities:
            best = opportunities[0]
            return f"Charge {best['charge_start'].strftime('%H:%M')}-{best['charge_end'].strftime('%H:%M')}, Discharge {best['discharge_start'].strftime('%H:%M')} (Profit: €{best['profit']:.2f})"

        return "No profitable opportunities found"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return {}

        raw_today = nordpool_state.attributes.get("raw_today", [])
        if not raw_today:
            return {}

        battery_capacity = self._get_float_state(self._battery_capacity_entity, 10.0)

        opportunities = self._optimizer.calculate_arbitrage_opportunities(
            raw_today,
            battery_capacity,
            min_profit_threshold=0.50,
        )

        return {
            "opportunities_count": len(opportunities),
            "best_profit": opportunities[0]["profit"] if opportunities else 0,
            "best_roi": opportunities[0]["roi_percent"] if opportunities else 0,
            "all_opportunities": opportunities[:5],  # Top 5
        }


class DischargeHoursSensor(BatteryTradingSensor):
    """Sensor for selected discharge hours with 15-min slot support."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        battery_level_entity: str,
        battery_capacity_entity: str,
        optimizer: EnergyOptimizer,
    ) -> None:
        """Initialize the discharge hours sensor."""
        super().__init__(
            hass,
            entry,
            nordpool_entity,
            SENSOR_DISCHARGE_HOURS,
            [nordpool_entity, battery_level_entity, battery_capacity_entity],
        )
        self._battery_level_entity = battery_level_entity
        self._battery_capacity_entity = battery_capacity_entity
        self._optimizer = optimizer
        self._attr_name = "Discharge Time Slots"
        self._attr_icon = "mdi:battery-arrow-up"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        slots = self._get_discharge_slots()

        if not slots:
            return "No discharge slots selected"

        # Format: "HH:MM-HH:MM (X.X kWh @ €Y.YY)"
        slot_strs = []
        for slot in slots:
            slot_strs.append(
                f"{slot['start'].strftime('%H:%M')}-{slot['end'].strftime('%H:%M')} "
                f"({slot['energy_kwh']:.1f}kWh @€{slot['price']:.3f})"
            )

        return ", ".join(slot_strs)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        slots = self._get_discharge_slots()

        if not slots:
            return {
                "slot_count": 0,
                "total_energy_kwh": 0,
                "estimated_revenue_eur": 0,
                "slots": [],
            }

        return {
            "slot_count": len(slots),
            "total_energy_kwh": sum(s["energy_kwh"] for s in slots),
            "estimated_revenue_eur": sum(s["revenue"] for s in slots),
            "average_price": sum(s["price"] for s in slots) / len(slots),
            "slots": [
                {
                    "start": s["start"].isoformat(),
                    "end": s["end"].isoformat(),
                    "energy_kwh": s["energy_kwh"],
                    "price": s["price"],
                    "revenue": s["revenue"],
                }
                for s in slots
            ],
        }

    def _get_discharge_slots(self) -> list[dict[str, Any]]:
        """Calculate discharge slots."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return []

        raw_today = nordpool_state.attributes.get("raw_today", [])
        if not raw_today:
            return []

        battery_capacity = self._get_float_state(self._battery_capacity_entity, 10.0)
        battery_level = self._get_float_state(self._battery_level_entity, 0.0)
        min_sell_price = self._get_number_entity_value(
            NUMBER_MIN_FORCED_SELL_PRICE, DEFAULT_MIN_FORCED_SELL_PRICE
        )
        discharge_rate = self._get_number_entity_value(
            NUMBER_DISCHARGE_RATE_KW, DEFAULT_DISCHARGE_RATE_KW
        )
        forced_discharge_hours = self._get_number_entity_value(
            NUMBER_FORCED_DISCHARGE_HOURS, DEFAULT_FORCED_DISCHARGE_HOURS
        )

        # 0 = unlimited (use battery capacity limit only)
        max_hours = None if forced_discharge_hours == 0 else forced_discharge_hours

        return self._optimizer.select_discharge_slots(
            raw_today,
            min_sell_price,
            battery_capacity,
            battery_level,
            discharge_rate=discharge_rate,
            max_hours=max_hours,
        )


class ChargingHoursSensor(BatteryTradingSensor):
    """Sensor for selected charging hours with 15-min slot support."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        nordpool_entity: str,
        battery_level_entity: str,
        battery_capacity_entity: str,
        optimizer: EnergyOptimizer,
    ) -> None:
        """Initialize the charging hours sensor."""
        super().__init__(
            hass,
            entry,
            nordpool_entity,
            SENSOR_CHARGING_HOURS,
            [nordpool_entity, battery_level_entity, battery_capacity_entity],
        )
        self._battery_level_entity = battery_level_entity
        self._battery_capacity_entity = battery_capacity_entity
        self._optimizer = optimizer
        self._attr_name = "Charging Time Slots"
        self._attr_icon = "mdi:battery-arrow-down"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        slots = self._get_charging_slots()

        if not slots:
            return "No charging slots selected"

        slot_strs = []
        for slot in slots:
            slot_strs.append(
                f"{slot['start'].strftime('%H:%M')}-{slot['end'].strftime('%H:%M')} "
                f"({slot['energy_kwh']:.1f}kWh @€{slot['price']:.3f})"
            )

        return ", ".join(slot_strs)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        slots = self._get_charging_slots()

        if not slots:
            return {
                "slot_count": 0,
                "total_energy_kwh": 0,
                "estimated_cost_eur": 0,
                "slots": [],
            }

        return {
            "slot_count": len(slots),
            "total_energy_kwh": sum(s["energy_kwh"] for s in slots),
            "estimated_cost_eur": sum(s["cost"] for s in slots),
            "average_price": sum(s["price"] for s in slots) / len(slots),
            "slots": [
                {
                    "start": s["start"].isoformat(),
                    "end": s["end"].isoformat(),
                    "energy_kwh": s["energy_kwh"],
                    "price": s["price"],
                    "cost": s["cost"],
                }
                for s in slots
            ],
        }

    def _get_charging_slots(self) -> list[dict[str, Any]]:
        """Calculate charging slots."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)
        if not nordpool_state:
            return []

        raw_today = nordpool_state.attributes.get("raw_today", [])
        if not raw_today:
            return []

        battery_capacity = self._get_float_state(self._battery_capacity_entity, 10.0)
        battery_level = self._get_float_state(self._battery_level_entity, 0.0)
        max_charge_price = self._get_number_entity_value(
            NUMBER_MAX_FORCE_CHARGE_PRICE, DEFAULT_MAX_FORCE_CHARGE_PRICE
        )
        target_level = self._get_number_entity_value(
            NUMBER_FORCE_CHARGE_TARGET, DEFAULT_FORCE_CHARGE_TARGET
        )

        return self._optimizer.select_charging_slots(
            raw_today,
            max_charge_price,
            battery_capacity,
            battery_level,
            target_level,
            charge_rate=5.0,  # 5kW charge rate
        )
