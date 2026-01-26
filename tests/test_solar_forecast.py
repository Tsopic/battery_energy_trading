"""Tests for solar forecast integration."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from custom_components.battery_energy_trading.solar_forecast import (
    DEFAULT_EVENING_CONSUMPTION_ESTIMATE,
    DEFAULT_MIN_FORECAST_FOR_RESERVE,
    DEFAULT_SOLAR_RESERVE_FACTOR,
    SolarDecision,
    SolarForecastAnalyzer,
    SolarForecastData,
    estimate_solar_production_value,
)


class TestSolarForecastData:
    """Tests for SolarForecastData dataclass."""

    def test_create_forecast_data(self):
        """Test creating forecast data."""
        forecast = SolarForecastData(
            today_remaining_kwh=8.5,
            today_total_kwh=15.0,
            tomorrow_total_kwh=20.0,
            is_sunny_tomorrow=True,
            forecast_confidence=0.85,
            last_updated=datetime.now(),
        )

        assert forecast.today_remaining_kwh == 8.5
        assert forecast.today_total_kwh == 15.0
        assert forecast.tomorrow_total_kwh == 20.0
        assert forecast.is_sunny_tomorrow is True
        assert forecast.forecast_confidence == 0.85


class TestSolarDecision:
    """Tests for SolarDecision dataclass."""

    def test_create_discharge_decision(self):
        """Test creating a discharge decision."""
        decision = SolarDecision(
            should_discharge=True,
            should_charge=False,
            reason="Price exceeds threshold",
            solar_influence="minor",
            forecast_summary="Today: 15.0 kWh, Tomorrow: 20.0 kWh (sunny)",
        )

        assert decision.should_discharge is True
        assert decision.should_charge is False
        assert "Price exceeds" in decision.reason


class TestSolarForecastAnalyzer:
    """Tests for SolarForecastAnalyzer class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        assert analyzer.reserve_factor == DEFAULT_SOLAR_RESERVE_FACTOR
        assert analyzer.min_forecast_for_reserve == DEFAULT_MIN_FORECAST_FOR_RESERVE
        assert analyzer.evening_consumption_estimate == DEFAULT_EVENING_CONSUMPTION_ESTIMATE

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(
            hass,
            solar_forecast_entity="sensor.solcast_forecast",
            reserve_factor=0.5,
            min_forecast_for_reserve=15.0,
            evening_consumption_estimate=8.0,
        )

        assert analyzer.solar_forecast_entity == "sensor.solcast_forecast"
        assert analyzer.reserve_factor == 0.5
        assert analyzer.min_forecast_for_reserve == 15.0
        assert analyzer.evening_consumption_estimate == 8.0

    def test_init_clamps_reserve_factor(self):
        """Test that reserve factor is clamped to 0-1."""
        hass = MagicMock()

        analyzer_high = SolarForecastAnalyzer(hass, reserve_factor=1.5)
        assert analyzer_high.reserve_factor == 1.0

        analyzer_low = SolarForecastAnalyzer(hass, reserve_factor=-0.5)
        assert analyzer_low.reserve_factor == 0.0


class TestExtractValue:
    """Tests for _extract_value helper method."""

    def test_extract_value_first_key(self):
        """Test extracting value with first matching key."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        attrs = {"forecast_today": 15.5, "energy_today": 10.0}
        result = analyzer._extract_value(attrs, ["forecast_today", "energy_today"])

        assert result == 15.5

    def test_extract_value_fallback_key(self):
        """Test extracting value with fallback key."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        attrs = {"energy_today": 10.0}
        result = analyzer._extract_value(attrs, ["forecast_today", "energy_today"])

        assert result == 10.0

    def test_extract_value_default(self):
        """Test default value when no key found."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        attrs = {"other_key": 5.0}
        result = analyzer._extract_value(attrs, ["forecast_today"], default=0.0)

        assert result == 0.0

    def test_extract_value_invalid_type(self):
        """Test handling invalid type in attribute."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        attrs = {"forecast_today": "not_a_number", "energy_today": 10.0}
        result = analyzer._extract_value(attrs, ["forecast_today", "energy_today"])

        assert result == 10.0


class TestEstimateRemainingToday:
    """Tests for _estimate_remaining_today method."""

    def test_explicit_remaining_value(self):
        """Test using explicit remaining value from attributes."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        attrs = {"remaining_today": 5.0}
        result = analyzer._estimate_remaining_today(15.0, attrs)

        assert result == 5.0

    def test_estimate_returns_valid_value(self):
        """Test that estimation returns a valid non-negative value."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        # Without mocking, just verify the result is valid
        result = analyzer._estimate_remaining_today(15.0, {})
        # Result should be between 0 and total
        assert 0.0 <= result <= 15.0

    def test_estimate_zero_total(self):
        """Test estimation with zero total production."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        result = analyzer._estimate_remaining_today(0.0, {})
        assert result == 0.0


class TestAnalyzeDischargeDecision:
    """Tests for discharge decision analysis."""

    def test_discharge_no_forecast(self):
        """Test discharge decision without forecast."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        decision = analyzer.analyze_discharge_decision(
            current_price=0.35,
            min_sell_price=0.30,
            battery_level=80.0,
            forecast=None,
        )

        assert decision.should_discharge is True
        assert decision.solar_influence == "none"
        assert "exceeds" in decision.reason

    def test_discharge_below_threshold_no_forecast(self):
        """Test no discharge when price below threshold."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        decision = analyzer.analyze_discharge_decision(
            current_price=0.20,
            min_sell_price=0.30,
            battery_level=80.0,
            forecast=None,
        )

        assert decision.should_discharge is False
        assert "below" in decision.reason

    def test_discharge_preserve_for_sunny_tomorrow(self):
        """Test preserving battery when tomorrow is sunny."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass, reserve_factor=0.5)

        forecast = SolarForecastData(
            today_remaining_kwh=5.0,
            today_total_kwh=15.0,
            tomorrow_total_kwh=25.0,  # Sunny tomorrow
            is_sunny_tomorrow=True,
            forecast_confidence=0.9,
            last_updated=datetime.now(),
        )

        decision = analyzer.analyze_discharge_decision(
            current_price=0.35,  # Moderate price (< 0.30 * 1.5 = 0.45)
            min_sell_price=0.30,
            battery_level=40.0,  # Below reserve (50%)
            forecast=forecast,
        )

        assert decision.should_discharge is False
        assert decision.solar_influence == "major"
        assert "Preserving battery" in decision.reason
        assert "sunny" in decision.reason.lower()

    def test_discharge_remaining_solar_covers_evening(self):
        """Test skipping discharge when remaining solar covers evening."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass, evening_consumption_estimate=5.0)

        forecast = SolarForecastData(
            today_remaining_kwh=8.0,  # More than evening consumption
            today_total_kwh=15.0,
            tomorrow_total_kwh=12.0,
            is_sunny_tomorrow=True,
            forecast_confidence=0.85,
            last_updated=datetime.now(),
        )

        decision = analyzer.analyze_discharge_decision(
            current_price=0.35,  # Moderate price (< 0.30 * 1.3 = 0.39)
            min_sell_price=0.30,
            battery_level=70.0,
            forecast=forecast,
        )

        assert decision.should_discharge is False
        assert decision.solar_influence == "major"
        assert "Remaining solar" in decision.reason


class TestAnalyzeChargeDecision:
    """Tests for charge decision analysis."""

    def test_charge_no_forecast(self):
        """Test charge decision without forecast."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        decision = analyzer.analyze_charge_decision(
            current_price=0.05,
            max_charge_price=0.10,
            battery_level=30.0,
            target_level=80.0,
            forecast=None,
        )

        assert decision.should_charge is True
        assert decision.solar_influence == "none"
        assert "below" in decision.reason

    def test_charge_above_threshold_no_forecast(self):
        """Test no charge when price above threshold."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        decision = analyzer.analyze_charge_decision(
            current_price=0.15,
            max_charge_price=0.10,
            battery_level=30.0,
            target_level=80.0,
            forecast=None,
        )

        assert decision.should_charge is False
        assert "exceeds" in decision.reason

    def test_charge_already_at_target(self):
        """Test no charge when already at target level."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        decision = analyzer.analyze_charge_decision(
            current_price=0.05,
            max_charge_price=0.10,
            battery_level=85.0,
            target_level=80.0,
            forecast=None,
        )

        assert decision.should_charge is False
        assert "exceeds target" in decision.reason

    def test_charge_more_when_cloudy_tomorrow(self):
        """Test increased charging tolerance when tomorrow is cloudy."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        forecast = SolarForecastData(
            today_remaining_kwh=3.0,
            today_total_kwh=8.0,
            tomorrow_total_kwh=5.0,  # Cloudy tomorrow
            is_sunny_tomorrow=False,
            forecast_confidence=0.8,
            last_updated=datetime.now(),
        )

        decision = analyzer.analyze_charge_decision(
            current_price=0.11,  # Above normal max but within adjusted (0.10 * 1.2 = 0.12)
            max_charge_price=0.10,
            battery_level=40.0,
            target_level=80.0,
            forecast=forecast,
        )

        assert decision.should_charge is True
        assert decision.solar_influence == "major"
        assert "cloudy" in decision.reason.lower()

    def test_skip_charge_when_solar_can_charge(self):
        """Test skipping grid charge when solar can fill battery."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        forecast = SolarForecastData(
            today_remaining_kwh=15.0,  # Plenty of solar remaining
            today_total_kwh=20.0,
            tomorrow_total_kwh=18.0,
            is_sunny_tomorrow=True,
            forecast_confidence=0.9,
            last_updated=datetime.now(),
        )

        decision = analyzer.analyze_charge_decision(
            current_price=0.05,  # Good price
            max_charge_price=0.10,
            battery_level=50.0,  # Need ~3 kWh (assuming 10 kWh battery)
            target_level=80.0,
            forecast=forecast,
        )

        assert decision.should_charge is False
        assert decision.solar_influence == "major"
        assert "solar" in decision.reason.lower()


class TestCalculateOptimalReserve:
    """Tests for optimal reserve calculation."""

    def test_no_forecast_no_reserve(self):
        """Test no reserve when no forecast available."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        reserve = analyzer.calculate_optimal_reserve(None, 10.0)
        assert reserve == 0.0

    def test_sunny_tomorrow_higher_reserve(self):
        """Test higher reserve when tomorrow is sunny."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass, evening_consumption_estimate=5.0)

        forecast = SolarForecastData(
            today_remaining_kwh=5.0,
            today_total_kwh=15.0,
            tomorrow_total_kwh=20.0,
            is_sunny_tomorrow=True,
            forecast_confidence=0.9,
            last_updated=datetime.now(),
        )

        reserve = analyzer.calculate_optimal_reserve(forecast, 10.0)

        # Reserve should be between 15% and 50%
        assert 15.0 <= reserve <= 50.0

    def test_cloudy_tomorrow_minimal_reserve(self):
        """Test minimal reserve when tomorrow is cloudy."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass)

        forecast = SolarForecastData(
            today_remaining_kwh=3.0,
            today_total_kwh=8.0,
            tomorrow_total_kwh=5.0,
            is_sunny_tomorrow=False,
            forecast_confidence=0.8,
            last_updated=datetime.now(),
        )

        reserve = analyzer.calculate_optimal_reserve(forecast, 10.0)
        assert reserve == 15.0  # Minimal reserve


class TestEstimateSolarProductionValue:
    """Tests for solar production value estimation."""

    def test_estimate_value_default_self_consumption(self):
        """Test value estimation with default self-consumption rate."""
        # 10 kWh at €0.30, 60% self-consumed
        # Self-consumption: 10 * 0.6 * 0.30 = €1.80
        # Export: 10 * 0.4 * (0.30 * 0.6) = €0.72
        # Total: €2.52
        value = estimate_solar_production_value(10.0, 0.30)
        assert abs(value - 2.52) < 0.01

    def test_estimate_value_high_self_consumption(self):
        """Test value with high self-consumption rate."""
        # 10 kWh at €0.30, 90% self-consumed
        # Self-consumption: 10 * 0.9 * 0.30 = €2.70
        # Export: 10 * 0.1 * (0.30 * 0.6) = €0.18
        # Total: €2.88
        value = estimate_solar_production_value(10.0, 0.30, self_consumption_rate=0.9)
        assert abs(value - 2.88) < 0.01

    def test_estimate_value_zero_production(self):
        """Test value with zero production."""
        value = estimate_solar_production_value(0.0, 0.30)
        assert value == 0.0


class TestAsyncGetForecastData:
    """Tests for async_get_forecast_data method."""

    @pytest.mark.asyncio
    async def test_no_entity_configured(self):
        """Test when no forecast entity is configured."""
        hass = MagicMock()
        analyzer = SolarForecastAnalyzer(hass, solar_forecast_entity=None)

        result = await analyzer.async_get_forecast_data()
        assert result is None

    @pytest.mark.asyncio
    async def test_entity_unavailable(self):
        """Test when forecast entity is unavailable."""
        hass = MagicMock()
        state = MagicMock()
        state.state = "unavailable"
        hass.states.get.return_value = state

        analyzer = SolarForecastAnalyzer(hass, solar_forecast_entity="sensor.solar_forecast")

        result = await analyzer.async_get_forecast_data()
        assert result is None

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        """Test when forecast entity doesn't exist."""
        hass = MagicMock()
        hass.states.get.return_value = None

        analyzer = SolarForecastAnalyzer(hass, solar_forecast_entity="sensor.solar_forecast")

        result = await analyzer.async_get_forecast_data()
        assert result is None

    @pytest.mark.asyncio
    async def test_successful_forecast_data(self):
        """Test successful forecast data retrieval."""
        hass = MagicMock()
        state = MagicMock()
        state.state = "15.5"
        state.attributes = {
            "forecast_today": 15.5,
            "forecast_tomorrow": 20.0,
            "confidence": 0.85,
        }
        hass.states.get.return_value = state

        analyzer = SolarForecastAnalyzer(
            hass,
            solar_forecast_entity="sensor.solar_forecast",
            min_forecast_for_reserve=10.0,
        )

        result = await analyzer.async_get_forecast_data()

        assert result is not None
        assert result.today_total_kwh == 15.5
        assert result.tomorrow_total_kwh == 20.0
        assert result.is_sunny_tomorrow is True  # 20 > 10
        assert result.forecast_confidence == 0.85
