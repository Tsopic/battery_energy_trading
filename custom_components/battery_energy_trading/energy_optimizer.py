"""Energy optimization logic for Battery Energy Trading."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import logging

_LOGGER = logging.getLogger(__name__)


class EnergyOptimizer:
    """Handles energy trading optimization calculations."""

    def __init__(self) -> None:
        """Initialize the optimizer."""
        self._battery_discharge_rate = 5.0  # kW default discharge rate

    @staticmethod
    def _merge_price_data(
        raw_today: list[dict[str, Any]],
        raw_tomorrow: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Merge today and tomorrow price data.

        Args:
            raw_today: Today's price data
            raw_tomorrow: Tomorrow's price data (optional)

        Returns:
            Combined list of price slots
        """
        if not raw_tomorrow:
            return raw_today

        # Filter out any overlapping slots (tomorrow's data might include end of today)
        if raw_today:
            last_today_time = raw_today[-1]["end"]
            raw_tomorrow = [
                slot for slot in raw_tomorrow
                if slot["start"] >= last_today_time
            ]

        return raw_today + raw_tomorrow

    @staticmethod
    def _calculate_slot_duration(raw_prices: list[dict[str, Any]]) -> float:
        """Calculate slot duration from price data.

        Args:
            raw_prices: List of price data with 'start', 'end', 'value' keys

        Returns:
            Slot duration in hours (0.25 for 15-min, 1.0 for hourly)
        """
        if len(raw_prices) > 1:
            return (
                raw_prices[1]["start"] - raw_prices[0]["start"]
            ).total_seconds() / 3600.0
        return 0.25  # Default to 15 minutes

    @staticmethod
    def _estimate_solar_impact(
        price_slots: list[dict[str, Any]],
        solar_forecast_data: dict[str, Any] | None,
        battery_capacity: float,
        current_battery_level: float,
    ) -> dict[datetime, float]:
        """Estimate battery level changes from solar forecast.

        Args:
            price_slots: List of price slots to evaluate
            solar_forecast_data: Solar forecast data with hourly estimates
            battery_capacity: Battery capacity in kWh
            current_battery_level: Current battery level in %

        Returns:
            Dictionary mapping datetime to estimated battery level (%)
        """
        battery_levels = {}

        if not solar_forecast_data or not price_slots:
            return battery_levels

        # Get hourly solar forecast from sensor attributes
        # Forecast.Solar and Solcast provide "wh_hours" with hourly estimates
        wh_hours = solar_forecast_data.get("wh_hours", {})

        current_level = current_battery_level
        for slot in price_slots:
            slot_start = slot["start"]

            # Get solar generation estimate for this hour (convert Wh to kWh)
            hour_key = slot_start.strftime("%Y-%m-%d %H:%M:%S")
            solar_kwh = wh_hours.get(hour_key, 0) / 1000.0

            # Estimate battery charge from solar (simplified - assumes all solar goes to battery)
            # In reality, household consumption would reduce this
            if solar_kwh > 0:
                level_increase = (solar_kwh / battery_capacity) * 100.0
                current_level = min(100.0, current_level + level_increase)

            battery_levels[slot_start] = current_level

        return battery_levels

    def select_discharge_slots(
        self,
        raw_prices: list[dict[str, Any]],
        min_sell_price: float,
        battery_capacity: float,
        battery_level: float,
        discharge_rate: float = 5.0,
        max_hours: float | None = None,
        raw_tomorrow: list[dict[str, Any]] | None = None,
        solar_forecast_data: dict[str, Any] | None = None,
        multiday_enabled: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Intelligently select discharge time slots based on price and battery capacity.

        Args:
            raw_prices: List of price data with 'start', 'end', 'value' keys
            min_sell_price: Minimum price threshold for selling (EUR/kWh)
            battery_capacity: Total battery capacity in kWh
            battery_level: Current battery level in percentage (0-100)
            discharge_rate: Battery discharge rate in kW (default 5.0 kW)
            max_hours: Maximum hours to discharge (None = unlimited, 0 = use battery capacity limit only)
            raw_tomorrow: Tomorrow's price data (optional, for multi-day optimization)
            solar_forecast_data: Solar forecast data (optional, for battery level estimation)
            multiday_enabled: Enable multi-day optimization across today + tomorrow

        Returns:
            List of selected discharge slots with calculated energy amounts
        """
        if not raw_prices:
            _LOGGER.warning("No price data available for discharge slot selection")
            return []

        # Merge today + tomorrow if multi-day optimization is enabled
        if multiday_enabled and raw_tomorrow:
            all_prices = self._merge_price_data(raw_prices, raw_tomorrow)
            _LOGGER.debug(
                "Multi-day optimization enabled: %d today slots + %d tomorrow slots = %d total",
                len(raw_prices), len(raw_tomorrow), len(all_prices)
            )
        else:
            all_prices = raw_prices

        # Estimate battery levels from solar forecast if provided
        solar_battery_estimates = {}
        if solar_forecast_data and multiday_enabled:
            solar_battery_estimates = self._estimate_solar_impact(
                all_prices, solar_forecast_data, battery_capacity, battery_level
            )
            if solar_battery_estimates:
                _LOGGER.debug("Solar forecast impact: battery levels estimated for %d slots", len(solar_battery_estimates))

        # Calculate available energy in battery
        available_energy = (battery_capacity * battery_level) / 100.0  # kWh

        if available_energy <= 0:
            _LOGGER.info("No energy available in battery for discharge")
            return []

        # Determine slot duration (15min or 60min)
        slot_duration_hours = self._calculate_slot_duration(all_prices)

        # Energy per slot based on discharge rate and duration
        energy_per_slot = discharge_rate * slot_duration_hours  # kWh

        # Calculate how many slots we can discharge (accounting for solar recharge)
        # If we have solar estimates, we may have more energy available in future slots
        max_discharge_slots = int(available_energy / energy_per_slot)

        if max_discharge_slots == 0 and not solar_battery_estimates:
            _LOGGER.info(
                "Battery capacity too low for discharge: %.2f kWh available, %.2f kWh per slot",
                available_energy,
                energy_per_slot,
            )
            return []

        # Filter slots above minimum price
        profitable_slots = [
            slot for slot in all_prices if slot["value"] >= min_sell_price
        ]

        if not profitable_slots:
            _LOGGER.info(
                "No profitable discharge slots found (min price: %.4f EUR/kWh)",
                min_sell_price,
            )
            return []

        # Sort by price (highest first)
        sorted_slots = sorted(profitable_slots, key=lambda x: x["value"], reverse=True)

        # Calculate max slots from max_hours if specified
        if max_hours is not None and max_hours > 0:
            max_slots_from_hours = int(max_hours / slot_duration_hours)
            num_slots = min(len(sorted_slots), max_discharge_slots, max_slots_from_hours)
        else:
            # No hour limit - use battery capacity as the only limit
            num_slots = min(len(sorted_slots), max_discharge_slots)

        selected_slots = []
        total_energy_to_discharge = 0.0

        for slot in sorted_slots[:num_slots]:
            # Check if solar forecast predicts higher battery level at this time
            slot_battery_level = solar_battery_estimates.get(slot["start"])
            if slot_battery_level is not None:
                # Recalculate available energy based on solar forecast
                slot_available_energy = (battery_capacity * slot_battery_level) / 100.0
            else:
                slot_available_energy = available_energy

            energy_this_slot = min(
                energy_per_slot, slot_available_energy - total_energy_to_discharge
            )

            if energy_this_slot > 0:
                selected_slots.append(
                    {
                        "start": slot["start"],
                        "end": slot["end"],
                        "price": slot["value"],
                        "energy_kwh": energy_this_slot,
                        "revenue": energy_this_slot * slot["value"],
                        "duration_hours": slot_duration_hours,
                        "estimated_battery_level": slot_battery_level,
                    }
                )
                total_energy_to_discharge += energy_this_slot

        _LOGGER.info(
            "Selected %d discharge slots, total energy: %.2f kWh, estimated revenue: %.2f EUR%s",
            len(selected_slots),
            total_energy_to_discharge,
            sum(s["revenue"] for s in selected_slots),
            " (multi-day with solar forecast)" if solar_battery_estimates else "",
        )

        return selected_slots

    def select_charging_slots(
        self,
        raw_prices: list[dict[str, Any]],
        max_charge_price: float,
        battery_capacity: float,
        battery_level: float,
        target_level: float,
        charge_rate: float = 5.0,
        max_slots: int | None = None,
        raw_tomorrow: list[dict[str, Any]] | None = None,
        solar_forecast_data: dict[str, Any] | None = None,
        multiday_enabled: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Intelligently select charging time slots based on price and battery needs.

        Args:
            raw_prices: List of price data with 'start', 'end', 'value' keys
            max_charge_price: Maximum price threshold for charging (EUR/kWh)
            battery_capacity: Total battery capacity in kWh
            battery_level: Current battery level in percentage (0-100)
            target_level: Target battery level in percentage (0-100)
            charge_rate: Battery charge rate in kW (default 5.0 kW)
            max_slots: Maximum number of slots to select (optional)
            raw_tomorrow: Tomorrow's price data (optional, for multi-day optimization)
            solar_forecast_data: Solar forecast data (optional, reduces charging need)
            multiday_enabled: Enable multi-day optimization across today + tomorrow

        Returns:
            List of selected charging slots with calculated energy amounts
        """
        if not raw_prices:
            _LOGGER.warning("No price data available for charging slot selection")
            return []

        # Merge today + tomorrow if multi-day optimization is enabled
        if multiday_enabled and raw_tomorrow:
            all_prices = self._merge_price_data(raw_prices, raw_tomorrow)
            _LOGGER.debug(
                "Multi-day charging optimization: %d today slots + %d tomorrow slots = %d total",
                len(raw_prices), len(raw_tomorrow), len(all_prices)
            )
        else:
            all_prices = raw_prices

        # Estimate battery levels from solar forecast if provided
        solar_battery_estimates = {}
        if solar_forecast_data and multiday_enabled:
            solar_battery_estimates = self._estimate_solar_impact(
                all_prices, solar_forecast_data, battery_capacity, battery_level
            )
            if solar_battery_estimates:
                _LOGGER.debug("Solar forecast reduces charging need - battery levels estimated for %d slots", len(solar_battery_estimates))

        # Calculate needed energy (accounting for solar if forecast available)
        current_energy = (battery_capacity * battery_level) / 100.0
        target_energy = (battery_capacity * target_level) / 100.0
        needed_energy = max(0, target_energy - current_energy)

        # If we have solar estimates, we may need less grid charging
        if solar_battery_estimates:
            # Find the maximum estimated battery level from solar alone
            max_solar_level = max(solar_battery_estimates.values(), default=battery_level)
            if max_solar_level >= target_level:
                _LOGGER.info("Solar forecast shows battery will reach target (%.1f%%) without grid charging", max_solar_level)
                return []
            # Reduce needed energy by expected solar contribution
            solar_energy_contribution = (battery_capacity * (max_solar_level - battery_level)) / 100.0
            needed_energy = max(0, needed_energy - solar_energy_contribution)
            _LOGGER.debug("Solar forecast reduces charging need by %.2f kWh (%.1f%% -> %.1f%%)", solar_energy_contribution, battery_level, max_solar_level)

        if needed_energy <= 0:
            _LOGGER.info("Battery already at or above target level")
            return []

        # Determine slot duration
        slot_duration_hours = self._calculate_slot_duration(all_prices)

        # Energy per slot
        energy_per_slot = charge_rate * slot_duration_hours

        # Calculate slots needed
        slots_needed = int((needed_energy + energy_per_slot - 0.001) / energy_per_slot)

        # Filter slots below max price
        economical_slots = [
            slot for slot in all_prices if slot["value"] <= max_charge_price
        ]

        if not economical_slots:
            _LOGGER.info(
                "No economical charging slots found (max price: %.4f EUR/kWh)",
                max_charge_price,
            )
            return []

        # Sort by price (lowest first)
        sorted_slots = sorted(economical_slots, key=lambda x: x["value"])

        # Limit by needed energy or max_slots
        if max_slots:
            num_slots = min(len(sorted_slots), slots_needed, max_slots)
        else:
            num_slots = min(len(sorted_slots), slots_needed)

        selected_slots = []
        total_energy_to_charge = 0.0

        for slot in sorted_slots[:num_slots]:
            energy_this_slot = min(energy_per_slot, needed_energy - total_energy_to_charge)

            if energy_this_slot > 0:
                selected_slots.append(
                    {
                        "start": slot["start"],
                        "end": slot["end"],
                        "price": slot["value"],
                        "energy_kwh": energy_this_slot,
                        "cost": energy_this_slot * slot["value"],
                        "duration_hours": slot_duration_hours,
                    }
                )
                total_energy_to_charge += energy_this_slot

        _LOGGER.info(
            "Selected %d charging slots, total energy: %.2f kWh, estimated cost: %.2f EUR%s",
            len(selected_slots),
            total_energy_to_charge,
            sum(s["cost"] for s in selected_slots),
            " (multi-day with solar forecast)" if solar_battery_estimates else "",
        )

        return selected_slots

    def calculate_arbitrage_opportunities(
        self,
        raw_prices: list[dict[str, Any]],
        battery_capacity: float,
        charge_rate: float = 5.0,
        discharge_rate: float = 5.0,
        efficiency: float = 0.9,
        min_profit_threshold: float = 0.05,
    ) -> list[dict[str, Any]]:
        """
        Find arbitrage opportunities considering battery capacity and efficiency.

        Args:
            raw_prices: List of price data
            battery_capacity: Battery capacity in kWh
            charge_rate: Charging rate in kW
            discharge_rate: Discharging rate in kW
            efficiency: Round-trip efficiency (0-1)
            min_profit_threshold: Minimum profit threshold in EUR

        Returns:
            List of arbitrage opportunities with charge/discharge windows
        """
        if not raw_prices or len(raw_prices) < 3:
            return []

        opportunities = []

        # Determine slot duration
        slot_duration_hours = self._calculate_slot_duration(raw_prices)

        # Energy per slot
        charge_energy_per_slot = charge_rate * slot_duration_hours
        discharge_energy_per_slot = discharge_rate * slot_duration_hours

        # Find charging windows and matching discharge windows
        for charge_start_idx in range(len(raw_prices) - 2):
            # Calculate charge window (could be multiple consecutive slots)
            charge_slots_needed = max(
                1, int(battery_capacity / charge_energy_per_slot)
            )
            charge_end_idx = min(charge_start_idx + charge_slots_needed, len(raw_prices))

            # Calculate average charge price
            charge_window = raw_prices[charge_start_idx:charge_end_idx]
            avg_charge_price = sum(s["value"] for s in charge_window) / len(
                charge_window
            )

            # Look for discharge opportunities after charging window
            for discharge_idx in range(charge_end_idx + 1, len(raw_prices)):
                discharge_price = raw_prices[discharge_idx]["value"]

                # Calculate profit considering efficiency
                energy_charged = min(
                    battery_capacity, charge_energy_per_slot * len(charge_window)
                )
                energy_discharged = energy_charged * efficiency

                charge_cost = energy_charged * avg_charge_price
                discharge_revenue = energy_discharged * discharge_price
                profit = discharge_revenue - charge_cost

                if profit >= min_profit_threshold:
                    opportunities.append(
                        {
                            "charge_start": charge_window[0]["start"],
                            "charge_end": charge_window[-1]["end"],
                            "charge_price": avg_charge_price,
                            "discharge_start": raw_prices[discharge_idx]["start"],
                            "discharge_end": raw_prices[discharge_idx]["end"],
                            "discharge_price": discharge_price,
                            "energy_kwh": energy_discharged,
                            "profit": profit,
                            "roi_percent": (profit / charge_cost) * 100,
                        }
                    )

        # Sort by profit (highest first)
        opportunities.sort(key=lambda x: x["profit"], reverse=True)

        return opportunities

    def is_current_slot_selected(
        self, selected_slots: list[dict[str, Any]], current_time: datetime | None = None
    ) -> bool:
        """
        Check if current time is within selected slots.

        Args:
            selected_slots: List of selected discharge/charge slots
            current_time: Current datetime (defaults to now())

        Returns:
            True if current time is in a selected slot
        """
        if not selected_slots:
            return False

        if current_time is None:
            current_time = datetime.now()

        for slot in selected_slots:
            # Handle timezone-aware and naive datetimes
            start = slot["start"]
            end = slot["end"]

            # Make comparison timezone-aware if needed
            if start.tzinfo is None and current_time.tzinfo is not None:
                # Convert current_time to naive for comparison
                current_time = current_time.replace(tzinfo=None)

            if start <= current_time < end:
                return True

        return False
