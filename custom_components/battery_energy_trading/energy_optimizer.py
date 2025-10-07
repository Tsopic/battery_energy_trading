"""Energy optimization logic for Battery Energy Trading."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any


_LOGGER = logging.getLogger(__name__)


class EnergyOptimizer:
    """Handles energy trading optimization calculations."""

    def __init__(self) -> None:
        """Initialize the optimizer."""
        self._battery_discharge_rate = 5.0  # kW default discharge rate
        self._cache: dict[str, tuple[datetime, Any]] = {}  # Cache with timestamp
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def _get_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """Generate cache key from method name and arguments."""
        # Create a stable hash of arguments
        cache_data = {
            "method": method_name,
            "args": str(args),
            "kwargs": {k: v for k, v in kwargs.items() if not isinstance(v, datetime | list)},
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _clean_expired_cache(self) -> None:
        """Remove expired entries from cache to prevent memory leak."""
        now = datetime.now()
        expired_keys = [
            key
            for key, (cached_time, _) in self._cache.items()
            if now - cached_time >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            _LOGGER.debug(
                "Cleaned %d expired cache entries (cache size: %d)",
                len(expired_keys),
                len(self._cache),
            )

    def _get_cached(self, cache_key: str) -> Any | None:
        """Get cached result if still valid."""
        # Periodic cleanup to prevent unbounded cache growth
        self._clean_expired_cache()

        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                _LOGGER.debug("Cache hit for key %s", cache_key[:8])
                return cached_result
            _LOGGER.debug("Cache expired for key %s", cache_key[:8])
            del self._cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, result: Any) -> None:
        """Store result in cache."""
        self._cache[cache_key] = (datetime.now(), result)
        _LOGGER.debug("Cached result for key %s (cache size: %d)", cache_key[:8], len(self._cache))

    @staticmethod
    def _validate_inputs(
        battery_capacity: float,
        battery_level: float,
        rate: float,
    ) -> tuple[float, float, float]:
        """Validate and clamp input parameters to safe ranges.

        Args:
            battery_capacity: Battery capacity in kWh
            battery_level: Battery level in percentage (0-100)
            rate: Charge or discharge rate in kW

        Returns:
            Tuple of validated (battery_capacity, battery_level, rate)
        """
        battery_capacity = max(0.0, battery_capacity)
        battery_level = max(0.0, min(100.0, battery_level))
        rate = max(0.0, rate)
        return battery_capacity, battery_level, rate

    @staticmethod
    def _merge_price_data(
        raw_today: list[dict[str, Any]], raw_tomorrow: list[dict[str, Any]] | None = None
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
            raw_tomorrow = [slot for slot in raw_tomorrow if slot["start"] >= last_today_time]

        return raw_today + raw_tomorrow

    @staticmethod
    def _normalize_datetime_key(dt: datetime) -> str:
        """Normalize datetime to ISO format for consistent lookups.

        Args:
            dt: Datetime object to normalize

        Returns:
            Normalized ISO format string without timezone
        """
        if dt.tzinfo:
            return dt.replace(tzinfo=None).isoformat()
        return dt.isoformat()

    @staticmethod
    def _create_normalized_solar_dict(wh_hours: dict[str, Any]) -> dict[str, float]:
        """Pre-normalize solar forecast keys for fast O(1) lookups.

        Args:
            wh_hours: Solar forecast dict with datetime keys and watt-hour values

        Returns:
            Dictionary with normalized keys and float values
        """
        normalized = {}
        for key, value in wh_hours.items():
            try:
                # Try parsing as ISO format datetime string
                if isinstance(key, str):
                    dt = datetime.fromisoformat(
                        key.replace("+00:00", "").replace("+01:00", "").replace("+02:00", "")
                    )
                    normalized_key = EnergyOptimizer._normalize_datetime_key(dt)
                    normalized[normalized_key] = float(value)
                elif isinstance(key, datetime):
                    normalized_key = EnergyOptimizer._normalize_datetime_key(key)
                    normalized[normalized_key] = float(value)
            except (ValueError, TypeError, AttributeError):
                continue
        return normalized

    @staticmethod
    def _calculate_slot_duration(raw_prices: list[dict[str, Any]]) -> float:
        """Calculate slot duration from price data.

        Args:
            raw_prices: List of price data with 'start', 'end', 'value' keys

        Returns:
            Slot duration in hours (0.25 for 15-min, 1.0 for hourly)
        """
        if len(raw_prices) > 1:
            return (raw_prices[1]["start"] - raw_prices[0]["start"]).total_seconds() / 3600.0
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

        try:
            # Get hourly solar forecast from sensor attributes
            # Forecast.Solar and Solcast provide "wh_hours" with hourly estimates
            wh_hours = solar_forecast_data.get("wh_hours", {})

            if not wh_hours:
                _LOGGER.debug("Solar forecast has no wh_hours data, skipping solar estimation")
                return battery_levels

            _LOGGER.debug("Solar forecast wh_hours has %d entries", len(wh_hours))

            # Pre-normalize all solar forecast keys once for O(1) lookups
            normalized_wh = EnergyOptimizer._create_normalized_solar_dict(wh_hours)

            current_level = current_battery_level
            estimates_count = 0

            for slot in price_slots:
                slot_start = slot["start"]

                # Normalize slot start time and lookup directly
                normalized_key = EnergyOptimizer._normalize_datetime_key(slot_start)
                solar_wh = normalized_wh.get(normalized_key, 0.0)

                if solar_wh > 0:
                    solar_kwh = solar_wh / 1000.0
                    estimates_count += 1

                    # Estimate battery charge from solar (simplified - assumes all solar goes to battery)
                    # In reality, household consumption would reduce this
                    level_increase = (solar_kwh / battery_capacity) * 100.0
                    current_level = min(100.0, current_level + level_increase)

                battery_levels[slot_start] = current_level

            if estimates_count > 0:
                _LOGGER.debug(
                    "Applied solar estimates for %d/%d slots", estimates_count, len(price_slots)
                )
            else:
                _LOGGER.warning(
                    "No matching solar forecast entries found - check datetime format compatibility"
                )

        except Exception as err:
            _LOGGER.error("Error estimating solar impact: %s", err, exc_info=True)
            return {}

        return battery_levels

    def _calculate_solar_between_slots(
        self,
        slot1: dict[str, Any],
        slot2: dict[str, Any],
        solar_forecast_data: dict[str, Any],
    ) -> float:
        """Calculate expected solar generation between two slots.

        Args:
            slot1: Earlier slot with 'end' datetime
            slot2: Later slot with 'start' datetime
            solar_forecast_data: Forecast with 'wh_hours' attribute

        Returns:
            Solar energy in kWh generated between slot1.end and slot2.start
        """
        if not solar_forecast_data or "wh_hours" not in solar_forecast_data:
            return 0.0

        wh_hours = solar_forecast_data["wh_hours"]
        start_time = slot1["end"]
        end_time = slot2["start"]

        # Pre-normalize solar forecast keys for fast lookups
        normalized_wh = EnergyOptimizer._create_normalized_solar_dict(wh_hours)

        total_wh = 0.0
        current_hour = start_time.replace(minute=0, second=0, microsecond=0)

        while current_hour < end_time:
            # Normalize and lookup directly
            normalized_key = EnergyOptimizer._normalize_datetime_key(current_hour)
            total_wh += normalized_wh.get(normalized_key, 0.0)
            current_hour += timedelta(hours=1)

        return total_wh / 1000.0  # Convert Wh to kWh

    def _project_battery_state(
        self,
        slots: list[dict[str, Any]],
        initial_battery_kwh: float,
        battery_capacity_kwh: float,
        discharge_rate_kw: float,
        slot_duration_hours: float,
        solar_forecast_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Project battery state through selected slots accounting for solar recharge.

        Args:
            slots: List of candidate discharge slots (sorted by time)
            initial_battery_kwh: Starting battery energy
            battery_capacity_kwh: Maximum battery capacity
            discharge_rate_kw: Discharge rate in kW
            slot_duration_hours: Duration of each slot in hours
            solar_forecast_data: Solar forecast with hourly generation

        Returns:
            List of slots with projected battery state and feasibility
        """
        current_battery = initial_battery_kwh
        feasible_slots = []

        # Sort slots by time (earliest first) for sequential projection
        time_sorted = sorted(slots, key=lambda x: x["start"])

        for i, slot in enumerate(time_sorted):
            # Calculate solar generation between previous slot and this slot
            if i > 0 and solar_forecast_data:
                solar_kwh = self._calculate_solar_between_slots(
                    time_sorted[i - 1], slot, solar_forecast_data
                )
                if solar_kwh > 0:
                    current_battery = min(current_battery + solar_kwh, battery_capacity_kwh)
                    _LOGGER.debug(
                        "Solar recharge +%.2f kWh between %s and %s (battery: %.2f kWh)",
                        solar_kwh,
                        time_sorted[i - 1]["end"].strftime("%H:%M"),
                        slot["start"].strftime("%H:%M"),
                        current_battery,
                    )

            # Calculate energy needed for this slot
            energy_needed = discharge_rate_kw * slot_duration_hours

            # Check if we have enough battery for this slot
            if current_battery >= energy_needed:
                slot_copy = slot.copy()
                slot_copy["battery_before"] = current_battery
                current_battery -= energy_needed
                slot_copy["battery_after"] = current_battery
                slot_copy["feasible"] = True
                slot_copy["energy_kwh"] = energy_needed
                # Ensure 'price' key exists (use 'value' if that's what's in the slot)
                if "price" not in slot_copy and "value" in slot_copy:
                    slot_copy["price"] = slot_copy["value"]
                feasible_slots.append(slot_copy)
                _LOGGER.debug(
                    "Slot %s feasible: %.2f kWh -> %.2f kWh (discharge %.2f kWh)",
                    slot["start"].strftime("%H:%M"),
                    slot_copy["battery_before"],
                    slot_copy["battery_after"],
                    energy_needed,
                )
            else:
                _LOGGER.debug(
                    "Slot %s NOT feasible: insufficient battery (%.2f kWh < %.2f kWh needed)",
                    slot["start"].strftime("%H:%M"),
                    current_battery,
                    energy_needed,
                )

        return feasible_slots

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
        min_battery_reserve_percent: float = 25.0,
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
            min_battery_reserve_percent: Minimum battery reserve to maintain (default 25%)

        Returns:
            List of selected discharge slots with calculated energy amounts, combined
            into consecutive periods. Partial discharge is applied automatically if
            needed to respect the minimum battery reserve.
        """
        # Validate inputs
        battery_capacity, battery_level, discharge_rate = self._validate_inputs(
            battery_capacity, battery_level, discharge_rate
        )

        _LOGGER.debug(
            "Selecting discharge slots: min_price=%.3f EUR/kWh, capacity=%.1f kWh, level=%.1f%%, rate=%.1f kW, max_hours=%s",
            min_sell_price,
            battery_capacity,
            battery_level,
            discharge_rate,
            max_hours,
        )

        # Check cache
        cache_key = self._get_cache_key(
            "select_discharge_slots",
            len(raw_prices),
            min_sell_price,
            battery_capacity,
            battery_level,
            discharge_rate,
            max_hours,
        )
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            return cached_result

        if not raw_prices:
            _LOGGER.warning("No price data available for discharge slot selection")
            return []

        # Merge today + tomorrow if multi-day optimization is enabled
        if multiday_enabled and raw_tomorrow:
            all_prices = self._merge_price_data(raw_prices, raw_tomorrow)
            _LOGGER.debug(
                "Multi-day optimization enabled: %d today slots + %d tomorrow slots = %d total",
                len(raw_prices),
                len(raw_tomorrow),
                len(all_prices),
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
                _LOGGER.debug(
                    "Solar forecast impact: battery levels estimated for %d slots",
                    len(solar_battery_estimates),
                )

        # Calculate available energy in battery
        available_energy = (battery_capacity * battery_level) / 100.0  # kWh

        if available_energy <= 0:
            _LOGGER.info("No energy available in battery for discharge")
            return []

        # Determine slot duration (15min or 60min)
        slot_duration_hours = self._calculate_slot_duration(all_prices)

        # Energy per slot based on discharge rate and duration
        energy_per_slot = discharge_rate * slot_duration_hours  # kWh

        # Prevent division by zero if discharge rate is 0
        if energy_per_slot <= 0:
            _LOGGER.warning(
                "Invalid discharge rate or slot duration (energy per slot: %.2f kWh)",
                energy_per_slot,
            )
            return []

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
        profitable_slots = [slot for slot in all_prices if slot["value"] >= min_sell_price]

        if not profitable_slots:
            _LOGGER.info(
                "No profitable discharge slots found (min price: %.4f EUR/kWh)",
                min_sell_price,
            )
            return []

        # Use battery state projection for intelligent multi-peak selection
        if solar_forecast_data:
            _LOGGER.debug(
                "Using battery state projection with solar forecast for feasibility analysis"
            )

            # Project battery state through all profitable slots (sorted by time)
            feasible_slots = self._project_battery_state(
                profitable_slots,
                available_energy,
                battery_capacity,
                discharge_rate,
                slot_duration_hours,
                solar_forecast_data,
            )

            if not feasible_slots:
                _LOGGER.info("No feasible discharge slots found after battery state projection")
                return []

            # Re-sort feasible slots by price (highest first) for selection
            price_sorted = sorted(feasible_slots, key=lambda x: x["price"], reverse=True)

            # Apply max_hours limit if specified
            if max_hours is not None and max_hours > 0:
                max_slots_from_hours = int(max_hours / slot_duration_hours)
                selected_slots = []
                total_hours = 0.0

                for slot in price_sorted:
                    if total_hours + slot_duration_hours <= max_hours:
                        selected_slots.append(
                            {
                                "start": slot["start"],
                                "end": slot["end"],
                                "price": slot["price"],
                                "energy_kwh": slot["energy_kwh"],
                                "revenue": slot["energy_kwh"] * slot["price"],
                                "duration_hours": slot_duration_hours,
                                "battery_before": slot["battery_before"],
                                "battery_after": slot["battery_after"],
                            }
                        )
                        total_hours += slot_duration_hours
            else:
                # No hour limit - return all feasible slots
                selected_slots = [
                    {
                        "start": slot["start"],
                        "end": slot["end"],
                        "price": slot["price"],
                        "energy_kwh": slot["energy_kwh"],
                        "revenue": slot["energy_kwh"] * slot["price"],
                        "duration_hours": slot_duration_hours,
                        "battery_before": slot["battery_before"],
                        "battery_after": slot["battery_after"],
                    }
                    for slot in price_sorted
                ]
        else:
            # Legacy behavior: simple price-based selection without battery projection
            _LOGGER.debug("No solar forecast - using legacy price-based selection")

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
            sum(s["energy_kwh"] for s in selected_slots),
            sum(s["revenue"] for s in selected_slots),
            " (with battery state projection)" if solar_forecast_data else "",
        )

        # Combine consecutive slots into longer discharge periods
        # Respects user-configured minimum battery reserve
        combined_slots = self._combine_consecutive_slots(
            selected_slots,
            min_battery_reserve_percent=min_battery_reserve_percent,
            battery_capacity_kwh=battery_capacity,
        )

        # Cache the result
        self._set_cached(cache_key, combined_slots)

        return combined_slots

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
        # Validate inputs
        battery_capacity, battery_level, charge_rate = self._validate_inputs(
            battery_capacity, battery_level, charge_rate
        )
        battery_capacity, target_level, _ = self._validate_inputs(
            battery_capacity, target_level, 0.0
        )

        # Check cache
        cache_key = self._get_cache_key(
            "select_charging_slots",
            len(raw_prices),
            max_charge_price,
            battery_capacity,
            battery_level,
            target_level,
            charge_rate,
            max_slots,
        )
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            return cached_result

        if not raw_prices:
            _LOGGER.warning("No price data available for charging slot selection")
            return []

        # Merge today + tomorrow if multi-day optimization is enabled
        if multiday_enabled and raw_tomorrow:
            all_prices = self._merge_price_data(raw_prices, raw_tomorrow)
            _LOGGER.debug(
                "Multi-day charging optimization: %d today slots + %d tomorrow slots = %d total",
                len(raw_prices),
                len(raw_tomorrow),
                len(all_prices),
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
                _LOGGER.debug(
                    "Solar forecast reduces charging need - battery levels estimated for %d slots",
                    len(solar_battery_estimates),
                )

        # Calculate needed energy (accounting for solar if forecast available)
        current_energy = (battery_capacity * battery_level) / 100.0
        target_energy = (battery_capacity * target_level) / 100.0
        needed_energy = max(0, target_energy - current_energy)

        # If we have solar estimates, we may need less grid charging
        if solar_battery_estimates:
            # Find the maximum estimated battery level from solar alone
            max_solar_level = max(solar_battery_estimates.values(), default=battery_level)
            if max_solar_level >= target_level:
                _LOGGER.info(
                    "Solar forecast shows battery will reach target (%.1f%%) without grid charging",
                    max_solar_level,
                )
                return []
            # Reduce needed energy by expected solar contribution
            solar_energy_contribution = (
                battery_capacity * (max_solar_level - battery_level)
            ) / 100.0
            needed_energy = max(0, needed_energy - solar_energy_contribution)
            _LOGGER.debug(
                "Solar forecast reduces charging need by %.2f kWh (%.1f%% -> %.1f%%)",
                solar_energy_contribution,
                battery_level,
                max_solar_level,
            )

        if needed_energy <= 0:
            _LOGGER.info("Battery already at or above target level")
            return []

        # Determine slot duration
        slot_duration_hours = self._calculate_slot_duration(all_prices)

        # Energy per slot
        energy_per_slot = charge_rate * slot_duration_hours

        # Prevent division by zero if charge rate is 0
        if energy_per_slot <= 0:
            _LOGGER.warning(
                "Invalid charge rate or slot duration (energy per slot: %.2f kWh)", energy_per_slot
            )
            return []

        # Calculate slots needed
        slots_needed = int((needed_energy + energy_per_slot - 0.001) / energy_per_slot)

        # Filter slots below max price
        economical_slots = [slot for slot in all_prices if slot["value"] <= max_charge_price]

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

        # Combine consecutive slots into longer charging periods
        # Note: Reserve doesn't apply to charging, but kept for consistency
        combined_slots = self._combine_consecutive_slots(
            selected_slots,
            min_battery_reserve_percent=0.0,  # No reserve limit for charging
            battery_capacity_kwh=battery_capacity,
        )

        # Cache the result
        self._set_cached(cache_key, combined_slots)

        return combined_slots

    def calculate_arbitrage_opportunities(
        self,
        raw_prices: list[dict[str, Any]],
        battery_capacity: float,
        charge_rate: float = 5.0,
        discharge_rate: float = 5.0,
        efficiency: float = 0.7,
        min_profit_threshold: float = 0.05,
    ) -> list[dict[str, Any]]:
        """
        Find arbitrage opportunities considering battery capacity and efficiency losses.

        Accounts for realistic round-trip efficiency of 70% (30% total energy loss):
        - Charging losses: ~10% (AC to DC conversion, heat)
        - Discharging losses: ~10% (DC to AC conversion, heat)
        - Inverter losses: ~5-10% (switching, transformation)
        - Total combined loss: ~30%

        Args:
            raw_prices: List of price data
            battery_capacity: Battery capacity in kWh
            charge_rate: Charging rate in kW
            discharge_rate: Discharging rate in kW
            efficiency: Round-trip efficiency (0-1), default 0.7 = 30% loss
            min_profit_threshold: Minimum profit threshold in EUR

        Returns:
            List of arbitrage opportunities with charge/discharge windows,
            accounting for energy losses during charge/discharge cycles
        """
        if not raw_prices or len(raw_prices) < 3:
            return []

        opportunities = []

        # Determine slot duration
        slot_duration_hours = self._calculate_slot_duration(raw_prices)

        # Energy per slot
        charge_energy_per_slot = charge_rate * slot_duration_hours
        discharge_energy_per_slot = discharge_rate * slot_duration_hours  # noqa: F841

        # Find charging windows and matching discharge windows
        for charge_start_idx in range(len(raw_prices) - 2):
            # Calculate charge window (could be multiple consecutive slots)
            charge_slots_needed = max(1, int(battery_capacity / charge_energy_per_slot))
            charge_end_idx = min(charge_start_idx + charge_slots_needed, len(raw_prices))

            # Calculate average charge price
            charge_window = raw_prices[charge_start_idx:charge_end_idx]
            avg_charge_price = sum(s["value"] for s in charge_window) / len(charge_window)

            # Look for discharge opportunities after charging window
            for discharge_idx in range(charge_end_idx + 1, len(raw_prices)):
                discharge_price = raw_prices[discharge_idx]["value"]

                # Calculate profit considering efficiency
                energy_charged = min(battery_capacity, charge_energy_per_slot * len(charge_window))
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

    @staticmethod
    def _combine_consecutive_slots(
        slots: list[dict[str, Any]],
        min_battery_reserve_percent: float = 10.0,
        battery_capacity_kwh: float | None = None,
    ) -> list[dict[str, Any]]:
        """Combine consecutive profitable slots into longer discharge periods.

        This creates longer discharge windows when multiple consecutive slots are
        profitable, respecting battery capacity and reserve constraints. When battery
        runs low during a period, the last slot is automatically reduced to partial
        discharge to avoid violating the minimum reserve.

        Args:
            slots: List of individual slots sorted by start time
            min_battery_reserve_percent: Minimum battery level to maintain (user configurable)
            battery_capacity_kwh: Battery capacity for reserve calculation (optional)

        Returns:
            List of combined slots with merged consecutive periods, with partial
            discharge applied to final slot if needed to respect battery reserve
        """
        if not slots:
            return []

        # Sort by start time to ensure consecutive detection works
        sorted_slots = sorted(slots, key=lambda x: x["start"])

        combined = []
        current_group = [sorted_slots[0]]

        for slot in sorted_slots[1:]:
            # Check if this slot is consecutive with the previous one
            last_slot = current_group[-1]

            # Slots are consecutive if the end time of the last slot equals the start time of this slot
            if last_slot["end"] == slot["start"]:
                current_group.append(slot)
            else:
                # Not consecutive - finalize the current group and start a new one
                combined.append(
                    _merge_slot_group(
                        current_group, min_battery_reserve_percent, battery_capacity_kwh
                    )
                )
                current_group = [slot]

        # Don't forget the last group
        if current_group:
            combined.append(
                _merge_slot_group(current_group, min_battery_reserve_percent, battery_capacity_kwh)
            )

        _LOGGER.info(
            "Combined %d individual slots into %d consecutive discharge periods (min reserve: %.0f%%)",
            len(slots),
            len(combined),
            min_battery_reserve_percent,
        )

        return combined


def _merge_slot_group(
    group: list[dict[str, Any]],
    min_battery_reserve_percent: float = 10.0,
    battery_capacity_kwh: float | None = None,
) -> dict[str, Any]:
    """Merge a group of consecutive slots into a single combined slot.

    Implements partial slot discharge: if the combined discharge would violate
    the minimum battery reserve, the last slot is automatically reduced to stop
    at the reserve threshold.

    Args:
        group: List of consecutive slots to merge
        min_battery_reserve_percent: Minimum battery level to maintain
        battery_capacity_kwh: Battery capacity for reserve calculation

    Returns:
        Single merged slot combining all periods in the group, with partial
        discharge applied if needed to respect battery reserve
    """
    if len(group) == 1:
        slot = group[0].copy()
        # Check if single slot needs partial discharge
        if battery_capacity_kwh and "battery_after" in slot:
            min_reserve_kwh = (battery_capacity_kwh * min_battery_reserve_percent) / 100.0
            if slot["battery_after"] < min_reserve_kwh:
                # Reduce energy to stop at reserve
                battery_before = slot.get("battery_before", 0)
                available_energy = max(0, battery_before - min_reserve_kwh)
                if available_energy < slot["energy_kwh"]:
                    # Apply partial discharge
                    reduction_ratio = (
                        available_energy / slot["energy_kwh"] if slot["energy_kwh"] > 0 else 0
                    )
                    slot["energy_kwh"] = available_energy
                    slot["revenue"] = slot.get("revenue", 0) * reduction_ratio
                    slot["cost"] = slot.get("cost", 0) * reduction_ratio
                    slot["duration_hours"] = slot.get("duration_hours", 0) * reduction_ratio
                    slot["battery_after"] = min_reserve_kwh
                    slot["partial_discharge"] = True
                    _LOGGER.info(
                        "Applied partial discharge to slot %s: reduced to %.2f kWh to respect %.0f%% reserve",
                        slot["start"],
                        available_energy,
                        min_battery_reserve_percent,
                    )
        return slot

    # Calculate combined metrics
    total_energy = sum(slot.get("energy_kwh", 0) for slot in group)
    total_revenue = sum(slot.get("revenue", 0) for slot in group)
    total_cost = sum(slot.get("cost", 0) for slot in group)
    total_duration = sum(slot.get("duration_hours", 0) for slot in group)

    # Calculate weighted average price
    if total_energy > 0:
        weighted_price = (total_revenue if total_revenue > 0 else total_cost) / total_energy
    else:
        weighted_price = sum(slot.get("price", 0) for slot in group) / len(group)

    # Create merged slot
    merged = {
        "start": group[0]["start"],
        "end": group[-1]["end"],
        "price": weighted_price,
        "energy_kwh": total_energy,
        "duration_hours": total_duration,
        "slot_count": len(group),  # Track how many original slots were merged
    }

    # Add revenue or cost depending on what's present
    if total_revenue > 0:
        merged["revenue"] = total_revenue
    if total_cost > 0:
        merged["cost"] = total_cost

    # Preserve battery state from first and last slot if available
    if "battery_before" in group[0]:
        merged["battery_before"] = group[0]["battery_before"]
    if "battery_after" in group[-1]:
        battery_after = group[-1]["battery_after"]

        # Check if combined discharge violates minimum reserve
        if battery_capacity_kwh:
            min_reserve_kwh = (battery_capacity_kwh * min_battery_reserve_percent) / 100.0
            if battery_after < min_reserve_kwh:
                # Need to reduce total energy to respect reserve
                battery_before = group[0]["battery_before"]
                available_energy = max(0, battery_before - min_reserve_kwh)

                if available_energy < total_energy:
                    # Apply partial discharge to the combined period
                    reduction_ratio = available_energy / total_energy if total_energy > 0 else 0
                    merged["energy_kwh"] = available_energy
                    merged["revenue"] = total_revenue * reduction_ratio
                    merged["cost"] = total_cost * reduction_ratio
                    merged["duration_hours"] = total_duration * reduction_ratio
                    battery_after = min_reserve_kwh
                    merged["partial_discharge"] = True
                    _LOGGER.info(
                        "Applied partial discharge to combined period %s-%s: reduced from %.2f to %.2f kWh to respect %.0f%% reserve",
                        group[0]["start"],
                        group[-1]["end"],
                        total_energy,
                        available_energy,
                        min_battery_reserve_percent,
                    )

        merged["battery_after"] = battery_after

    return merged
