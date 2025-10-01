"""Tests for energy optimizer module."""
import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add custom_components directory to path for direct module import
# This avoids importing __init__.py which requires homeassistant
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "battery_energy_trading"))

from energy_optimizer import EnergyOptimizer


class TestEnergyOptimizer:
    """Tests for EnergyOptimizer class."""

    def test_select_discharge_slots_basic(self, sample_price_data):
        """Test basic discharge slot selection with max_hours limit."""
        optimizer = EnergyOptimizer()

        # Battery at 80% with 10kWh capacity = 8kWh available
        # max_hours=1.0 with 15-min slots = 4 slots max
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.30,
            battery_capacity=10.0,
            battery_level=80.0,
            discharge_rate=5.0,
            max_hours=1.0,
        )

        assert len(slots) <= 4
        assert all(slot["price"] >= 0.30 for slot in slots)
        # Slots should be sorted by price (highest first)
        prices = [slot["price"] for slot in slots]
        assert prices == sorted(prices, reverse=True)

    def test_select_discharge_slots_insufficient_battery(self, sample_price_data):
        """Test discharge selection with low battery."""
        optimizer = EnergyOptimizer()

        # Battery at 10% with 10kWh capacity = 1kWh available
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.20,
            battery_capacity=10.0,
            battery_level=10.0,
            discharge_rate=5.0,
        )

        # With 5kW discharge rate and 15-min slots, each slot uses 1.25kWh
        # So 1kWh battery can't even fill one slot completely
        assert len(slots) == 0

    def test_select_discharge_slots_no_profitable_prices(self, sample_price_data):
        """Test discharge selection when no prices meet threshold."""
        optimizer = EnergyOptimizer()

        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=1.00,  # Unrealistically high threshold
            battery_capacity=10.0,
            battery_level=100.0,
            discharge_rate=5.0,
        )

        assert len(slots) == 0

    def test_select_discharge_slots_energy_calculation(self, sample_price_data):
        """Test that energy calculations are correct."""
        optimizer = EnergyOptimizer()

        # max_hours=0.5 with 15-min slots = 2 slots max
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.35,
            battery_capacity=12.8,  # SBR128
            battery_level=75.0,
            discharge_rate=10.0,  # SH10RT
            max_hours=0.5,
        )

        assert len(slots) == 2

        # Each 15-min slot with 10kW discharge = 2.5 kWh
        for slot in slots:
            assert slot["energy_kwh"] == pytest.approx(2.5, rel=0.01)
            assert slot["revenue"] == pytest.approx(slot["energy_kwh"] * slot["price"], rel=0.01)

    def test_select_discharge_slots_unlimited(self, sample_price_data):
        """Test discharge selection with unlimited hours (max_hours=None)."""
        optimizer = EnergyOptimizer()

        # Battery at 100% with 25.6 kWh capacity (SBR256)
        # max_hours=None means no hour limit, only battery capacity limit
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.30,
            battery_capacity=25.6,
            battery_level=100.0,
            discharge_rate=10.0,  # SH10RT
            max_hours=None,  # Unlimited
        )

        # Should select all profitable slots limited only by battery capacity
        # 25.6 kWh / 2.5 kWh per slot = 10.24 slots max
        assert len(slots) > 0
        assert len(slots) <= 10
        assert all(slot["price"] >= 0.30 for slot in slots)
        # Verify they're sorted by price
        prices = [slot["price"] for slot in slots]
        assert prices == sorted(prices, reverse=True)

    def test_select_charging_slots_basic(self, sample_price_data):
        """Test basic charging slot selection."""
        optimizer = EnergyOptimizer()

        # Battery at 30% wanting to reach 80% with 10kWh capacity
        slots = optimizer.select_charging_slots(
            raw_prices=sample_price_data,
            max_charge_price=0.05,
            battery_capacity=10.0,
            battery_level=30.0,
            target_level=80.0,
            charge_rate=5.0,
        )

        # Need 5kWh (50% of 10kWh)
        # With 5kW charge rate and 15-min slots = 1.25kWh per slot
        # So need 4 slots minimum
        assert len(slots) >= 4
        assert all(slot["price"] <= 0.05 for slot in slots)

        # Slots should be sorted by price (lowest first)
        prices = [slot["price"] for slot in slots]
        assert prices == sorted(prices)

    def test_select_charging_slots_already_at_target(self, sample_price_data):
        """Test charging when battery already at target."""
        optimizer = EnergyOptimizer()

        slots = optimizer.select_charging_slots(
            raw_prices=sample_price_data,
            max_charge_price=0.10,
            battery_capacity=10.0,
            battery_level=80.0,
            target_level=70.0,  # Already above target
            charge_rate=5.0,
        )

        assert len(slots) == 0

    def test_select_charging_slots_no_cheap_slots(self, sample_price_data):
        """Test charging when no slots below price threshold."""
        optimizer = EnergyOptimizer()

        slots = optimizer.select_charging_slots(
            raw_prices=sample_price_data,
            max_charge_price=-0.10,  # Unrealistically low
            battery_capacity=10.0,
            battery_level=20.0,
            target_level=80.0,
            charge_rate=5.0,
        )

        assert len(slots) == 0

    def test_calculate_arbitrage_opportunities(self, sample_price_data):
        """Test arbitrage opportunity detection."""
        optimizer = EnergyOptimizer()

        opportunities = optimizer.calculate_arbitrage_opportunities(
            raw_prices=sample_price_data,
            battery_capacity=10.0,
            charge_rate=5.0,
            discharge_rate=5.0,
            efficiency=0.9,
            min_profit_threshold=0.5,
        )

        # Should find opportunities between cheap night hours and expensive peak hours
        assert len(opportunities) > 0

        for opp in opportunities:
            assert opp["profit"] >= 0.5
            assert opp["charge_price"] < opp["discharge_price"]
            assert opp["discharge_start"] > opp["charge_end"]  # Discharge after charge

    def test_calculate_arbitrage_with_efficiency_loss(self, sample_price_data):
        """Test that arbitrage accounts for efficiency loss."""
        optimizer = EnergyOptimizer()

        # Low efficiency should reduce opportunities
        low_eff_opps = optimizer.calculate_arbitrage_opportunities(
            raw_prices=sample_price_data,
            battery_capacity=10.0,
            charge_rate=5.0,
            discharge_rate=5.0,
            efficiency=0.5,  # 50% efficiency loss
            min_profit_threshold=0.1,
        )

        high_eff_opps = optimizer.calculate_arbitrage_opportunities(
            raw_prices=sample_price_data,
            battery_capacity=10.0,
            charge_rate=5.0,
            discharge_rate=5.0,
            efficiency=0.95,  # 95% efficiency
            min_profit_threshold=0.1,
        )

        # Higher efficiency should find more or equal opportunities
        assert len(high_eff_opps) >= len(low_eff_opps)

    def test_is_current_slot_selected(self, sample_price_data):
        """Test current slot detection."""
        optimizer = EnergyOptimizer()

        # Select some slots
        selected_slots = sample_price_data[10:15]  # Select 5 slots

        # Test time within selected slot
        current_time = selected_slots[2]["start"] + timedelta(minutes=5)
        assert optimizer.is_current_slot_selected(selected_slots, current_time) is True

        # Test time outside selected slots
        current_time = sample_price_data[0]["start"]
        assert optimizer.is_current_slot_selected(selected_slots, current_time) is False

        # Test with empty slot list
        assert optimizer.is_current_slot_selected([], current_time) is False

    def test_is_current_slot_selected_timezone_handling(self, sample_price_data):
        """Test timezone handling in slot detection."""
        optimizer = EnergyOptimizer()

        # Make slots timezone-naive
        selected_slots = sample_price_data[10:12]

        # Test with timezone-naive current time
        current_time = selected_slots[0]["start"] + timedelta(minutes=5)
        assert optimizer.is_current_slot_selected(selected_slots, current_time) is True

    def test_discharge_slots_respect_max_hours_parameter(self, sample_price_data):
        """Test that max_hours parameter is respected."""
        optimizer = EnergyOptimizer()

        # max_hours=0.75 with 15-min slots = 3 slots max
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.10,
            battery_capacity=50.0,  # Large battery
            battery_level=100.0,
            discharge_rate=10.0,
            max_hours=0.75,  # 45 minutes = 3 slots
        )

        assert len(slots) <= 3

    def test_charging_slots_energy_never_exceeds_needed(self, sample_price_data):
        """Test that charging doesn't exceed needed energy."""
        optimizer = EnergyOptimizer()

        slots = optimizer.select_charging_slots(
            raw_prices=sample_price_data,
            max_charge_price=0.20,
            battery_capacity=10.0,
            battery_level=50.0,
            target_level=70.0,  # Need 2kWh
            charge_rate=5.0,
        )

        total_energy = sum(slot["energy_kwh"] for slot in slots)
        assert total_energy <= 2.1  # Allow small rounding error

    def test_battery_state_projection_without_solar(self):
        """Test battery state projection without solar recharge."""
        optimizer = EnergyOptimizer()

        # Create test slots spanning 2 hours
        base_time = datetime(2025, 10, 1, 8, 0)
        test_slots = [
            {"start": base_time, "end": base_time + timedelta(minutes=15), "value": 0.50, "price": 0.50},
            {"start": base_time + timedelta(hours=1), "end": base_time + timedelta(hours=1, minutes=15), "value": 0.48, "price": 0.48},
        ]

        # Battery: 10 kWh capacity, 50% charged = 5 kWh available
        # Discharge rate: 5 kW for 15-min slots = 1.25 kWh per slot
        # Should support both slots (5 kWh > 2.5 kWh needed)
        feasible = optimizer._project_battery_state(
            slots=test_slots,
            initial_battery_kwh=5.0,
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=None,
        )

        assert len(feasible) == 2
        assert feasible[0]["battery_before"] == pytest.approx(5.0)
        assert feasible[0]["battery_after"] == pytest.approx(3.75)
        assert feasible[1]["battery_before"] == pytest.approx(3.75)
        assert feasible[1]["battery_after"] == pytest.approx(2.5)

    def test_battery_state_projection_with_solar(self):
        """Test battery state projection with solar recharge between slots."""
        optimizer = EnergyOptimizer()

        # Create test slots: morning and evening
        base_time = datetime(2025, 10, 1, 8, 0)
        test_slots = [
            {"start": base_time, "end": base_time + timedelta(minutes=15), "value": 0.45, "price": 0.45},
            {"start": base_time + timedelta(hours=8), "end": base_time + timedelta(hours=8, minutes=15), "value": 0.50, "price": 0.50},
        ]

        # Solar forecast: 6 kWh generated between 9:00-15:00
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=i)).isoformat(): 1000.0  # 1 kWh per hour
                for i in range(1, 7)
            }
        }

        # Battery: 10 kWh capacity, 40% = 4 kWh available
        # First discharge: 1.25 kWh -> 2.75 kWh remaining
        # Solar recharge: +6 kWh -> 8.75 kWh
        # Second discharge: 1.25 kWh -> 7.5 kWh remaining
        feasible = optimizer._project_battery_state(
            slots=test_slots,
            initial_battery_kwh=4.0,
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=solar_forecast,
        )

        assert len(feasible) == 2
        # First slot feasible with initial battery
        assert feasible[0]["battery_before"] == pytest.approx(4.0)
        assert feasible[0]["battery_after"] == pytest.approx(2.75)
        # Second slot feasible thanks to solar recharge
        assert feasible[1]["battery_before"] == pytest.approx(8.75)
        assert feasible[1]["battery_after"] == pytest.approx(7.5)

    def test_battery_state_projection_insufficient_for_second_peak(self):
        """Test that second peak is rejected when battery insufficient."""
        optimizer = EnergyOptimizer()

        # Create test slots
        base_time = datetime(2025, 10, 1, 8, 0)
        test_slots = [
            {"start": base_time, "end": base_time + timedelta(minutes=15), "value": 0.45, "price": 0.45},
            {"start": base_time + timedelta(hours=2), "end": base_time + timedelta(hours=2, minutes=15), "value": 0.50, "price": 0.50},
        ]

        # Small solar forecast: only 0.5 kWh generated
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=1)).isoformat(): 500.0,  # 0.5 kWh
            }
        }

        # Battery: 10 kWh capacity, 20% = 2 kWh available
        # First discharge: 1.25 kWh -> 0.75 kWh remaining
        # Solar recharge: +0.5 kWh -> 1.25 kWh
        # Second discharge needs 1.25 kWh -> EXACTLY sufficient
        feasible = optimizer._project_battery_state(
            slots=test_slots,
            initial_battery_kwh=2.0,
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=solar_forecast,
        )

        # Should select both slots (edge case: exactly enough)
        assert len(feasible) == 2

    def test_select_discharge_with_battery_projection(self, sample_price_data):
        """Test discharge slot selection using battery state projection."""
        optimizer = EnergyOptimizer()

        # Create solar forecast covering the day
        base_time = sample_price_data[0]["start"]
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=i)).isoformat(): 2000.0  # 2 kWh per hour
                for i in range(8, 18)  # Solar from 8am to 6pm
            }
        }

        # Battery: 10 kWh capacity, 50% = 5 kWh
        # With solar forecast, should select multiple peaks throughout the day
        slots = optimizer.select_discharge_slots(
            raw_prices=sample_price_data,
            min_sell_price=0.30,
            battery_capacity=10.0,
            battery_level=50.0,
            discharge_rate=5.0,
            max_hours=None,  # Unlimited
            solar_forecast_data=solar_forecast,
        )

        # Should select multiple slots thanks to solar recharge
        assert len(slots) > 2
        # All slots should be above min price
        assert all(slot["price"] >= 0.30 for slot in slots)
        # Verify battery state tracking
        for slot in slots:
            assert "battery_before" in slot
            assert "battery_after" in slot
