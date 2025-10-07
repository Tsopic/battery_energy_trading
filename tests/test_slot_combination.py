"""Tests for consecutive slot combination logic."""
import pytest
from datetime import datetime, timedelta

from custom_components.battery_energy_trading.energy_optimizer import (
    EnergyOptimizer,
    _merge_slot_group,
)


class TestSlotCombination:
    """Test consecutive slot combination."""

    def test_combine_two_consecutive_discharge_slots(self):
        """Test combining two consecutive 15-minute discharge slots."""
        optimizer = EnergyOptimizer()

        slots = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 20, 15),
                "end": datetime(2025, 1, 1, 20, 30),
                "price": 0.34,
                "energy_kwh": 1.25,
                "revenue": 0.425,
                "duration_hours": 0.25,
            },
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 1
        assert combined[0]["start"] == datetime(2025, 1, 1, 20, 0)
        assert combined[0]["end"] == datetime(2025, 1, 1, 20, 30)
        assert combined[0]["energy_kwh"] == 2.5
        assert combined[0]["revenue"] == pytest.approx(0.8625)
        assert combined[0]["duration_hours"] == 0.5
        assert combined[0]["slot_count"] == 2

    def test_combine_non_consecutive_slots_separately(self):
        """Test that non-consecutive slots are kept separate."""
        optimizer = EnergyOptimizer()

        slots = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 21, 0),  # 45-minute gap
                "end": datetime(2025, 1, 1, 21, 15),
                "price": 0.33,
                "energy_kwh": 1.25,
                "revenue": 0.4125,
                "duration_hours": 0.25,
            },
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 2
        assert combined[0]["start"] == datetime(2025, 1, 1, 20, 0)
        assert combined[1]["start"] == datetime(2025, 1, 1, 21, 0)

    def test_combine_four_consecutive_slots(self):
        """Test combining four consecutive 15-minute slots into one hour."""
        optimizer = EnergyOptimizer()

        slots = []
        start_time = datetime(2025, 1, 1, 19, 0)

        for i in range(4):
            slot_start = start_time + timedelta(minutes=15 * i)
            slot_end = slot_start + timedelta(minutes=15)
            slots.append({
                "start": slot_start,
                "end": slot_end,
                "price": 0.35 - (i * 0.01),  # Slightly decreasing price
                "energy_kwh": 1.25,
                "revenue": 1.25 * (0.35 - (i * 0.01)),
                "duration_hours": 0.25,
            })

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 1
        assert combined[0]["start"] == datetime(2025, 1, 1, 19, 0)
        assert combined[0]["end"] == datetime(2025, 1, 1, 20, 0)
        assert combined[0]["energy_kwh"] == 5.0
        assert combined[0]["duration_hours"] == 1.0
        assert combined[0]["slot_count"] == 4

    def test_combine_mixed_consecutive_and_gaps(self):
        """Test combining slots with multiple consecutive groups."""
        optimizer = EnergyOptimizer()

        slots = [
            # Group 1: Two consecutive
            {
                "start": datetime(2025, 1, 1, 19, 0),
                "end": datetime(2025, 1, 1, 19, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 19, 15),
                "end": datetime(2025, 1, 1, 19, 30),
                "price": 0.34,
                "energy_kwh": 1.25,
                "revenue": 0.425,
                "duration_hours": 0.25,
            },
            # Gap
            # Group 2: Three consecutive
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.36,
                "energy_kwh": 1.25,
                "revenue": 0.45,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 20, 15),
                "end": datetime(2025, 1, 1, 20, 30),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 20, 30),
                "end": datetime(2025, 1, 1, 20, 45),
                "price": 0.34,
                "energy_kwh": 1.25,
                "revenue": 0.425,
                "duration_hours": 0.25,
            },
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 2
        # Group 1
        assert combined[0]["start"] == datetime(2025, 1, 1, 19, 0)
        assert combined[0]["end"] == datetime(2025, 1, 1, 19, 30)
        assert combined[0]["slot_count"] == 2
        # Group 2
        assert combined[1]["start"] == datetime(2025, 1, 1, 20, 0)
        assert combined[1]["end"] == datetime(2025, 1, 1, 20, 45)
        assert combined[1]["slot_count"] == 3

    def test_combine_preserves_battery_state(self):
        """Test that battery state is preserved from first and last slot."""
        optimizer = EnergyOptimizer()

        slots = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
                "battery_before": 10.0,
                "battery_after": 8.75,
            },
            {
                "start": datetime(2025, 1, 1, 20, 15),
                "end": datetime(2025, 1, 1, 20, 30),
                "price": 0.34,
                "energy_kwh": 1.25,
                "revenue": 0.425,
                "duration_hours": 0.25,
                "battery_before": 8.75,
                "battery_after": 7.5,
            },
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 1
        assert combined[0]["battery_before"] == 10.0
        assert combined[0]["battery_after"] == 7.5

    def test_combine_charging_slots(self):
        """Test combining consecutive charging slots."""
        optimizer = EnergyOptimizer()

        slots = [
            {
                "start": datetime(2025, 1, 1, 2, 0),
                "end": datetime(2025, 1, 1, 2, 15),
                "price": 0.05,
                "energy_kwh": 1.25,
                "cost": 0.0625,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 2, 15),
                "end": datetime(2025, 1, 1, 2, 30),
                "price": 0.06,
                "energy_kwh": 1.25,
                "cost": 0.075,
                "duration_hours": 0.25,
            },
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 1
        assert combined[0]["energy_kwh"] == 2.5
        assert combined[0]["cost"] == pytest.approx(0.1375)
        assert combined[0]["slot_count"] == 2

    def test_empty_slots_list(self):
        """Test that empty slots list returns empty list."""
        optimizer = EnergyOptimizer()
        combined = optimizer._combine_consecutive_slots([])
        assert combined == []

    def test_single_slot_unchanged(self):
        """Test that a single slot is returned unchanged."""
        optimizer = EnergyOptimizer()

        slots = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            }
        ]

        combined = optimizer._combine_consecutive_slots(slots)

        assert len(combined) == 1
        assert combined[0] == slots[0]


class TestMergeSlotGroup:
    """Test the _merge_slot_group helper function."""

    def test_merge_single_slot(self):
        """Test that single slot is returned as copy."""
        group = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.35,
                "energy_kwh": 1.25,
                "revenue": 0.4375,
                "duration_hours": 0.25,
            }
        ]

        merged = _merge_slot_group(group)
        assert merged == group[0]
        assert merged is not group[0]  # Should be a copy

    def test_merge_calculates_weighted_average_price(self):
        """Test that weighted average price is calculated correctly."""
        group = [
            {
                "start": datetime(2025, 1, 1, 20, 0),
                "end": datetime(2025, 1, 1, 20, 15),
                "price": 0.40,
                "energy_kwh": 2.0,
                "revenue": 0.8,
                "duration_hours": 0.25,
            },
            {
                "start": datetime(2025, 1, 1, 20, 15),
                "end": datetime(2025, 1, 1, 20, 30),
                "price": 0.30,
                "energy_kwh": 1.0,
                "revenue": 0.3,
                "duration_hours": 0.25,
            },
        ]

        merged = _merge_slot_group(group)

        # Weighted average: (0.8 + 0.3) / (2.0 + 1.0) = 1.1 / 3.0 = 0.366666
        expected_price = 1.1 / 3.0
        assert merged["price"] == pytest.approx(expected_price)
