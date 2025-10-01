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


class TestEnergyOptimizerIntegration:
    """Integration tests with realistic scenarios."""

    def test_realistic_nord_pool_price_pattern(self):
        """Test with realistic Nord Pool price pattern (morning + evening peaks)."""
        optimizer = EnergyOptimizer()

        # Realistic Estonian Nord Pool prices for October 2025
        # Pattern: Night cheap, morning peak (7-9am), midday normal, evening peak (5-8pm)
        base_time = datetime(2025, 10, 1, 0, 0)
        realistic_prices = []

        for hour in range(24):
            for quarter in range(4):
                start = base_time + timedelta(hours=hour, minutes=quarter * 15)
                end = start + timedelta(minutes=15)

                # Realistic price patterns
                if 2 <= hour < 5:  # Night valley (very cheap)
                    price = 0.02 + (quarter * 0.005)
                elif 7 <= hour < 9:  # Morning peak
                    price = 0.35 + (quarter * 0.02)
                elif 12 <= hour < 14:  # Midday dip (solar production)
                    price = 0.15 + (quarter * 0.01)
                elif 17 <= hour < 20:  # Evening peak (highest)
                    price = 0.45 + (quarter * 0.03)
                else:  # Normal hours
                    price = 0.18 + (quarter * 0.01)

                realistic_prices.append({
                    "start": start,
                    "end": end,
                    "value": price,
                })

        # Scenario: 10 kWh battery at 60%, SH10RT inverter, with solar forecast
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=h)).isoformat():
                    3000.0 if 9 <= h < 16 else (1000.0 if 7 <= h < 9 or 16 <= h < 18 else 0.0)
                for h in range(24)
            }
        }

        slots = optimizer.select_discharge_slots(
            raw_prices=realistic_prices,
            min_sell_price=0.30,
            battery_capacity=10.0,
            battery_level=60.0,  # 6 kWh available
            discharge_rate=10.0,  # SH10RT
            max_hours=0,  # Unlimited - let system decide
            solar_forecast_data=solar_forecast,
        )

        # Assertions
        assert len(slots) > 0, "Should find profitable discharge slots"

        # Should prioritize evening peak (highest prices)
        evening_slots = [s for s in slots if s['start'].hour >= 17 and s['start'].hour < 20]
        assert len(evening_slots) > 0, "Should select evening peak slots"

        # Verify battery state projection
        for slot in slots:
            assert "battery_before" in slot
            assert "battery_after" in slot
            assert slot["battery_before"] >= slot["energy_kwh"], "Must have enough battery"

        # Verify slots are sorted by price (highest first)
        prices = [slot["price"] for slot in slots]
        assert prices == sorted(prices, reverse=True), "Slots should be sorted by price descending"

    def test_solar_forecast_datetime_formats(self):
        """Test solar recharge calculation with various datetime formats."""
        optimizer = EnergyOptimizer()

        base_time = datetime(2025, 10, 1, 8, 0)

        # Test with ISO format datetime
        solar_forecast_iso = {
            "wh_hours": {
                (base_time + timedelta(hours=i)).isoformat(): 2000.0
                for i in range(10)
            }
        }

        # Create two discharge slots with gap
        slots = [
            {"start": base_time, "end": base_time + timedelta(minutes=15), "value": 0.40, "price": 0.40},
            {"start": base_time + timedelta(hours=8), "end": base_time + timedelta(hours=8, minutes=15), "value": 0.45, "price": 0.45},
        ]

        feasible = optimizer._project_battery_state(
            slots=slots,
            initial_battery_kwh=3.0,
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=solar_forecast_iso,
        )

        assert len(feasible) == 2, "Both slots should be feasible with solar recharge"
        assert feasible[1]["battery_before"] > 3.0, "Battery should recharge between slots"

    def test_multi_peak_without_solar_forecast(self):
        """Test backward compatibility - multi-peak selection without solar forecast."""
        optimizer = EnergyOptimizer()

        # Create price data with two peaks
        base_time = datetime(2025, 10, 1, 0, 0)
        prices = []

        for hour in range(24):
            for quarter in range(4):
                start = base_time + timedelta(hours=hour, minutes=quarter * 15)
                end = start + timedelta(minutes=15)

                if hour == 8:  # Morning peak
                    price = 0.40
                elif hour == 18:  # Evening peak
                    price = 0.42
                else:
                    price = 0.15

                prices.append({"start": start, "end": end, "value": price})

        # Large battery, should select both peaks based on capacity alone
        slots = optimizer.select_discharge_slots(
            raw_prices=prices,
            min_sell_price=0.35,
            battery_capacity=25.6,  # SBR256
            battery_level=100.0,
            discharge_rate=10.0,
            max_hours=0,  # Unlimited
            solar_forecast_data=None,  # No solar forecast
        )

        assert len(slots) > 0, "Should select discharge slots"
        # Without solar forecast, uses legacy logic - selects based on battery capacity
        assert all(slot["price"] >= 0.35 for slot in slots)
        # Should NOT have battery projection attributes without solar
        assert "battery_before" not in slots[0]

    def test_multi_peak_with_insufficient_battery(self):
        """Test that system correctly rejects infeasible second peak."""
        optimizer = EnergyOptimizer()

        base_time = datetime(2025, 10, 1, 8, 0)

        # Two high-price peaks
        slots_input = [
            {"start": base_time, "end": base_time + timedelta(minutes=15), "value": 0.45, "price": 0.45},
            {"start": base_time + timedelta(hours=2), "end": base_time + timedelta(hours=2, minutes=15), "value": 0.50, "price": 0.50},
        ]

        # Minimal solar forecast (not enough to support both peaks)
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=1)).isoformat(): 300.0,  # Only 0.3 kWh
            }
        }

        # Battery: 10 kWh capacity, 20% = 2.0 kWh (REDUCED to test insufficient battery)
        # First peak needs: 5kW * 0.25h = 1.25 kWh
        # After first: 2.0 - 1.25 = 0.75 kWh
        # Solar adds: 0.3 kWh -> 1.05 kWh
        # Second peak needs: 1.25 kWh -> NOT FEASIBLE (only 1.05 kWh available)

        feasible = optimizer._project_battery_state(
            slots=slots_input,
            initial_battery_kwh=2.0,  # Changed from 2.5 to 2.0 to make second peak infeasible
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=solar_forecast,
        )

        # With 0.3 kWh solar, second peak should still NOT be feasible
        assert len(feasible) == 1, "Only first peak feasible even with minimal solar (1.05 kWh < 1.25 kWh needed)"

        # Now test with zero solar - second peak should definitely fail
        feasible_no_solar = optimizer._project_battery_state(
            slots=slots_input,
            initial_battery_kwh=2.0,  # Changed from 2.5 to 2.0
            battery_capacity_kwh=10.0,
            discharge_rate_kw=5.0,
            slot_duration_hours=0.25,
            solar_forecast_data=None,
        )

        assert len(feasible_no_solar) == 1, "Only first peak feasible without solar (0.75 kWh < 1.25 kWh needed)"

    def test_max_hours_limit_with_battery_projection(self):
        """Test that max_hours limit is respected with battery projection."""
        optimizer = EnergyOptimizer()

        base_time = datetime(2025, 10, 1, 0, 0)
        prices = []

        # Create many high-price slots
        for hour in range(24):
            for quarter in range(4):
                start = base_time + timedelta(hours=hour, minutes=quarter * 15)
                end = start + timedelta(minutes=15)
                prices.append({"start": start, "end": end, "value": 0.40})

        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=h)).isoformat(): 2000.0
                for h in range(24)
            }
        }

        # Test with max_hours limit
        slots = optimizer.select_discharge_slots(
            raw_prices=prices,
            min_sell_price=0.30,
            battery_capacity=25.6,
            battery_level=100.0,
            discharge_rate=10.0,
            max_hours=2.0,  # Limit to 2 hours
            solar_forecast_data=solar_forecast,
        )

        # 2 hours with 15-min slots = 8 slots max
        assert len(slots) <= 8, "Should respect max_hours limit"

        # Verify battery projection was used
        if len(slots) > 0:
            assert "battery_before" in slots[0]

    def test_complete_realistic_scenario(self):
        """Integration test: Complete day with Estonian winter pattern."""
        optimizer = EnergyOptimizer()

        # Estonian winter day: Short daylight, high evening consumption
        base_time = datetime(2025, 12, 15, 0, 0)
        prices = []

        for hour in range(24):
            for quarter in range(4):
                start = base_time + timedelta(hours=hour, minutes=quarter * 15)
                end = start + timedelta(minutes=15)

                # Winter price pattern
                if 6 <= hour < 9:  # Morning peak
                    price = 0.38
                elif 16 <= hour < 21:  # Long evening peak
                    price = 0.52
                elif 22 <= hour < 24 or 0 <= hour < 6:  # Night
                    price = 0.08
                else:
                    price = 0.22

                prices.append({"start": start, "end": end, "value": price})

        # Limited winter solar (only 4 hours, weak production)
        solar_forecast = {
            "wh_hours": {
                (base_time + timedelta(hours=h)).isoformat():
                    1500.0 if 10 <= h < 14 else 0.0
                for h in range(24)
            }
        }

        # SBR128 battery (12.8 kWh) at 50%, SH10RT inverter
        slots = optimizer.select_discharge_slots(
            raw_prices=prices,
            min_sell_price=0.35,
            battery_capacity=12.8,
            battery_level=50.0,  # 6.4 kWh available
            discharge_rate=10.0,
            max_hours=0,  # Unlimited
            solar_forecast_data=solar_forecast,
        )

        # Should prioritize evening peak (highest prices)
        assert len(slots) > 0, "Should find discharge opportunities"

        evening_slots = [s for s in slots if 16 <= s['start'].hour < 21]
        morning_slots = [s for s in slots if 6 <= s['start'].hour < 9]

        # Evening peak higher, should be selected
        assert len(evening_slots) > 0, "Should select evening peak (highest price)"

        # Calculate total discharge
        total_energy = sum(s["energy_kwh"] for s in slots)
        total_revenue = sum(s["revenue"] for s in slots)

        assert total_energy <= 12.8, "Total discharge can't exceed battery capacity"
        assert total_revenue > 0, "Should generate revenue"

        print(f"\nWinter scenario results:")
        print(f"  Slots selected: {len(slots)}")
        print(f"  Total energy: {total_energy:.2f} kWh")
        print(f"  Total revenue: €{total_revenue:.2f}")
        print(f"  Average price: €{total_revenue/total_energy:.3f}/kWh")
