"""Solar forecast integration for smarter battery scheduling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Default values for solar forecast settings
DEFAULT_SOLAR_RESERVE_FACTOR = 0.3  # 30% of forecast to reserve
DEFAULT_MIN_FORECAST_FOR_RESERVE = 10.0  # kWh minimum forecast to activate reserve
DEFAULT_EVENING_CONSUMPTION_ESTIMATE = 5.0  # kWh average evening consumption


@dataclass
class SolarForecastData:
    """Container for solar forecast data."""

    today_remaining_kwh: float
    today_total_kwh: float
    tomorrow_total_kwh: float
    is_sunny_tomorrow: bool
    forecast_confidence: float  # 0.0 - 1.0
    last_updated: datetime | None


@dataclass
class SolarDecision:
    """Decision result from solar forecast analysis."""

    should_discharge: bool
    should_charge: bool
    reason: str
    solar_influence: str  # "none", "minor", "major"
    forecast_summary: str


class SolarForecastAnalyzer:
    """Analyze solar forecasts for battery management decisions.

    Integrates with common solar forecast integrations:
    - Forecast.Solar
    - Solcast
    - OpenWeatherMap solar radiation
    - Custom template sensors
    """

    def __init__(
        self,
        hass: HomeAssistant,
        solar_forecast_entity: str | None = None,
        reserve_factor: float = DEFAULT_SOLAR_RESERVE_FACTOR,
        min_forecast_for_reserve: float = DEFAULT_MIN_FORECAST_FOR_RESERVE,
        evening_consumption_estimate: float = DEFAULT_EVENING_CONSUMPTION_ESTIMATE,
    ) -> None:
        """Initialize the solar forecast analyzer.

        Args:
            hass: Home Assistant instance
            solar_forecast_entity: Entity ID of solar forecast sensor
            reserve_factor: Portion of battery to reserve for sunny days (0-1)
            min_forecast_for_reserve: Minimum kWh forecast to activate reserve mode
            evening_consumption_estimate: Expected evening consumption in kWh
        """
        self.hass = hass
        self.solar_forecast_entity = solar_forecast_entity
        self.reserve_factor = max(0.0, min(1.0, reserve_factor))
        self.min_forecast_for_reserve = max(0.0, min_forecast_for_reserve)
        self.evening_consumption_estimate = max(0.0, evening_consumption_estimate)

    async def async_get_forecast_data(self) -> SolarForecastData | None:
        """Get current solar forecast data from configured entity.

        Returns:
            SolarForecastData if available, None if no forecast entity configured
        """
        if not self.solar_forecast_entity:
            return None

        state = self.hass.states.get(self.solar_forecast_entity)
        if not state or state.state in ("unknown", "unavailable"):
            _LOGGER.warning("Solar forecast entity %s not available", self.solar_forecast_entity)
            return None

        # Extract forecast data - support multiple integration formats
        attrs = state.attributes

        # Try common attribute names for today's forecast
        today_total = self._extract_value(
            attrs,
            [
                "forecast_today",
                "energy_production_today",
                "today",
                "energy_today",
                "pv_estimate",
            ],
        )

        # Try common attribute names for tomorrow's forecast
        tomorrow_total = self._extract_value(
            attrs,
            [
                "forecast_tomorrow",
                "energy_production_tomorrow",
                "tomorrow",
                "energy_tomorrow",
                "pv_estimate_tomorrow",
            ],
        )

        # Estimate remaining production today
        today_remaining = self._estimate_remaining_today(today_total, attrs)

        # Determine if tomorrow is considered "sunny"
        is_sunny = tomorrow_total >= self.min_forecast_for_reserve

        # Extract confidence if available
        confidence = self._extract_value(attrs, ["confidence", "probability"], default=0.8)

        return SolarForecastData(
            today_remaining_kwh=today_remaining,
            today_total_kwh=today_total,
            tomorrow_total_kwh=tomorrow_total,
            is_sunny_tomorrow=is_sunny,
            forecast_confidence=confidence,
            last_updated=datetime.now(),
        )

    def _extract_value(
        self,
        attrs: dict[str, Any],
        keys: list[str],
        default: float = 0.0,
    ) -> float:
        """Extract a value from attributes, trying multiple keys.

        Args:
            attrs: Attribute dictionary
            keys: List of possible keys to try
            default: Default value if not found

        Returns:
            Extracted value or default
        """
        for key in keys:
            if key in attrs:
                try:
                    return float(attrs[key])
                except (TypeError, ValueError):
                    continue
        return default

    def _estimate_remaining_today(
        self,
        today_total: float,
        attrs: dict[str, Any],
    ) -> float:
        """Estimate remaining solar production for today.

        Args:
            today_total: Total expected production today
            attrs: Entity attributes

        Returns:
            Estimated remaining kWh
        """
        # If we have explicit remaining data, use it
        remaining = self._extract_value(
            attrs, ["remaining_today", "forecast_remaining"], default=-1
        )
        if remaining >= 0:
            return remaining

        # Otherwise estimate based on time of day
        now = datetime.now()
        # Assume solar production from 6 AM to 8 PM (14 hours)
        solar_start = now.replace(hour=6, minute=0, second=0, microsecond=0)
        solar_end = now.replace(hour=20, minute=0, second=0, microsecond=0)

        if now < solar_start:
            return today_total
        if now > solar_end:
            return 0.0

        # Calculate remaining portion of solar day
        total_solar_hours = (solar_end - solar_start).total_seconds() / 3600
        remaining_hours = (solar_end - now).total_seconds() / 3600

        # Production is not linear - peak is midday. Simple approximation:
        # Assume 50% of production happens in the middle 50% of the day
        # This is a rough heuristic, actual production curves vary
        remaining_fraction = remaining_hours / total_solar_hours

        return today_total * remaining_fraction

    def analyze_discharge_decision(
        self,
        current_price: float,
        min_sell_price: float,
        battery_level: float,
        forecast: SolarForecastData | None,
    ) -> SolarDecision:
        """Analyze whether to discharge based on price and solar forecast.

        Args:
            current_price: Current electricity price (EUR/kWh)
            min_sell_price: Minimum price threshold for selling
            battery_level: Current battery level (%)
            forecast: Solar forecast data (optional)

        Returns:
            SolarDecision with recommendation
        """
        # Base decision without solar
        base_should_discharge = current_price >= min_sell_price

        if not forecast:
            return SolarDecision(
                should_discharge=base_should_discharge,
                should_charge=False,
                reason=(
                    f"Price €{current_price:.4f} {'exceeds' if base_should_discharge else 'below'} "
                    f"threshold €{min_sell_price:.4f}"
                ),
                solar_influence="none",
                forecast_summary="No solar forecast available",
            )

        # Solar-aware decision making
        solar_influence = "minor"
        reason_parts = []

        # Check if we should preserve battery for tomorrow
        if forecast.is_sunny_tomorrow and current_price < min_sell_price * 1.5:
            # Tomorrow is sunny and price is only moderately good
            # Consider preserving battery for self-consumption tomorrow
            reserve_threshold = 100 * self.reserve_factor
            if battery_level <= reserve_threshold:
                return SolarDecision(
                    should_discharge=False,
                    should_charge=False,
                    reason=(
                        f"Preserving battery for tomorrow's sunny forecast "
                        f"({forecast.tomorrow_total_kwh:.1f} kWh). "
                        f"Battery at {battery_level:.0f}% below reserve {reserve_threshold:.0f}%"
                    ),
                    solar_influence="major",
                    forecast_summary=self._format_forecast_summary(forecast),
                )
            solar_influence = "minor"
            reason_parts.append(f"Tomorrow sunny ({forecast.tomorrow_total_kwh:.1f} kWh)")

        # Check if today's remaining solar can cover evening consumption
        # Solar will cover evening demand, maybe skip discharge
        if (
            forecast.today_remaining_kwh > self.evening_consumption_estimate
            and current_price < min_sell_price * 1.3
        ):
            return SolarDecision(
                should_discharge=False,
                should_charge=False,
                reason=(
                    f"Remaining solar ({forecast.today_remaining_kwh:.1f} kWh) "
                    f"exceeds evening consumption estimate ({self.evening_consumption_estimate:.1f} kWh). "
                    f"Price €{current_price:.4f} not high enough to override."
                ),
                solar_influence="major",
                forecast_summary=self._format_forecast_summary(forecast),
            )

        # Default: use price-based decision with solar context
        reason = f"Price €{current_price:.4f} {'exceeds' if base_should_discharge else 'below'} threshold €{min_sell_price:.4f}"
        if reason_parts:
            reason += f" (Note: {', '.join(reason_parts)})"

        return SolarDecision(
            should_discharge=base_should_discharge,
            should_charge=False,
            reason=reason,
            solar_influence=solar_influence,
            forecast_summary=self._format_forecast_summary(forecast),
        )

    def analyze_charge_decision(
        self,
        current_price: float,
        max_charge_price: float,
        battery_level: float,
        target_level: float,
        forecast: SolarForecastData | None,
    ) -> SolarDecision:
        """Analyze whether to charge based on price and solar forecast.

        Args:
            current_price: Current electricity price (EUR/kWh)
            max_charge_price: Maximum price for grid charging
            battery_level: Current battery level (%)
            target_level: Target battery level (%)
            forecast: Solar forecast data (optional)

        Returns:
            SolarDecision with recommendation
        """
        # Already at target
        if battery_level >= target_level:
            return SolarDecision(
                should_discharge=False,
                should_charge=False,
                reason=f"Battery at {battery_level:.0f}% already exceeds target {target_level:.0f}%",
                solar_influence="none",
                forecast_summary=self._format_forecast_summary(forecast)
                if forecast
                else "No forecast",
            )

        # Base decision
        base_should_charge = current_price <= max_charge_price

        if not forecast:
            return SolarDecision(
                should_discharge=False,
                should_charge=base_should_charge,
                reason=(
                    f"Price €{current_price:.4f} {'below' if base_should_charge else 'exceeds'} "
                    f"max charge price €{max_charge_price:.4f}"
                ),
                solar_influence="none",
                forecast_summary="No solar forecast available",
            )

        # Solar-aware charging decision
        solar_influence = "minor"
        reason_parts = []

        # If tomorrow is cloudy, we should charge more aggressively
        if not forecast.is_sunny_tomorrow:
            # Cloudy tomorrow - increase charging priority
            adjusted_max_price = max_charge_price * 1.2  # 20% higher tolerance
            if current_price <= adjusted_max_price and not base_should_charge:
                return SolarDecision(
                    should_discharge=False,
                    should_charge=True,
                    reason=(
                        f"Charging despite price €{current_price:.4f} exceeding normal max €{max_charge_price:.4f} "
                        f"because tomorrow is cloudy ({forecast.tomorrow_total_kwh:.1f} kWh forecast)"
                    ),
                    solar_influence="major",
                    forecast_summary=self._format_forecast_summary(forecast),
                )
            reason_parts.append(f"Tomorrow cloudy ({forecast.tomorrow_total_kwh:.1f} kWh)")

        # If remaining solar today can charge the battery, skip grid charging
        energy_needed = (target_level - battery_level) / 100 * 10  # Assume 10 kWh battery
        if (
            forecast.today_remaining_kwh > energy_needed * 1.2  # 20% buffer
            and base_should_charge
        ):
            return SolarDecision(
                should_discharge=False,
                should_charge=False,
                reason=(
                    f"Skipping grid charge - remaining solar ({forecast.today_remaining_kwh:.1f} kWh) "
                    f"can charge battery (need ~{energy_needed:.1f} kWh)"
                ),
                solar_influence="major",
                forecast_summary=self._format_forecast_summary(forecast),
            )

        # Default decision with solar context
        reason = (
            f"Price €{current_price:.4f} {'below' if base_should_charge else 'exceeds'} "
            f"max charge price €{max_charge_price:.4f}"
        )
        if reason_parts:
            reason += f" (Note: {', '.join(reason_parts)})"

        return SolarDecision(
            should_discharge=False,
            should_charge=base_should_charge,
            reason=reason,
            solar_influence=solar_influence,
            forecast_summary=self._format_forecast_summary(forecast),
        )

    def _format_forecast_summary(self, forecast: SolarForecastData) -> str:
        """Format forecast data as a human-readable summary.

        Args:
            forecast: Solar forecast data

        Returns:
            Formatted summary string
        """
        return (
            f"Today: {forecast.today_total_kwh:.1f} kWh total, "
            f"{forecast.today_remaining_kwh:.1f} kWh remaining. "
            f"Tomorrow: {forecast.tomorrow_total_kwh:.1f} kWh "
            f"({'sunny' if forecast.is_sunny_tomorrow else 'cloudy'})"
        )

    def calculate_optimal_reserve(
        self,
        forecast: SolarForecastData | None,
        battery_capacity_kwh: float,
    ) -> float:
        """Calculate optimal battery reserve level based on forecast.

        Args:
            forecast: Solar forecast data
            battery_capacity_kwh: Battery capacity in kWh

        Returns:
            Recommended reserve level as percentage (0-100)
        """
        if not forecast:
            return 0.0  # No reserve if no forecast

        # Base reserve on tomorrow's forecast
        if forecast.is_sunny_tomorrow:
            # Sunny tomorrow - reserve more for self-consumption
            # Reserve enough for evening + overnight consumption
            reserve_kwh = self.evening_consumption_estimate * 1.5
            reserve_percent = (reserve_kwh / battery_capacity_kwh) * 100
            return min(50.0, max(15.0, reserve_percent))  # Clamp 15-50%

        # Cloudy tomorrow - minimal reserve
        return 15.0  # Just basic reserve


def estimate_solar_production_value(
    forecast_kwh: float,
    avg_price: float,
    self_consumption_rate: float = 0.6,
) -> float:
    """Estimate the economic value of forecasted solar production.

    Args:
        forecast_kwh: Forecasted solar production in kWh
        avg_price: Average electricity price (EUR/kWh)
        self_consumption_rate: Portion of solar used directly (0-1)

    Returns:
        Estimated value in EUR
    """
    # Self-consumed solar saves buying from grid
    self_consumption_value = forecast_kwh * self_consumption_rate * avg_price

    # Exported solar earns feed-in tariff (typically lower than purchase price)
    export_rate = avg_price * 0.6  # Assume feed-in is 60% of retail
    export_value = forecast_kwh * (1 - self_consumption_rate) * export_rate

    return self_consumption_value + export_value
