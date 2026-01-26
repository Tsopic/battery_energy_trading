"""Tests for historical performance tracking."""

import json

from custom_components.battery_energy_trading.performance_tracker import (
    MAX_DAYS_IN_MEMORY,
    DailyPerformance,
    PerformanceSummary,
    PerformanceTracker,
    TradingEvent,
)


class TestTradingEvent:
    """Tests for TradingEvent dataclass."""

    def test_create_discharge_event(self):
        """Test creating a discharge event."""
        event = TradingEvent(
            timestamp="2024-01-26T17:00:00",
            event_type="discharge",
            energy_kwh=5.0,
            price_per_kwh=0.40,
            total_amount=2.00,
            duration_minutes=60,
            battery_level_start=80.0,
            battery_level_end=50.0,
        )

        assert event.event_type == "discharge"
        assert event.energy_kwh == 5.0
        assert event.total_amount == 2.00

    def test_create_charge_event(self):
        """Test creating a charge event."""
        event = TradingEvent(
            timestamp="2024-01-26T03:00:00",
            event_type="charge",
            energy_kwh=8.0,
            price_per_kwh=0.05,
            total_amount=0.40,
            duration_minutes=120,
            battery_level_start=20.0,
            battery_level_end=80.0,
        )

        assert event.event_type == "charge"
        assert event.energy_kwh == 8.0
        assert event.total_amount == 0.40

    def test_to_dict(self):
        """Test converting event to dictionary."""
        event = TradingEvent(
            timestamp="2024-01-26T17:00:00",
            event_type="discharge",
            energy_kwh=5.0,
            price_per_kwh=0.40,
            total_amount=2.00,
            duration_minutes=60,
            battery_level_start=80.0,
            battery_level_end=50.0,
        )

        result = event.to_dict()

        assert isinstance(result, dict)
        assert result["event_type"] == "discharge"
        assert result["energy_kwh"] == 5.0


class TestDailyPerformance:
    """Tests for DailyPerformance dataclass."""

    def test_default_values(self):
        """Test default values."""
        perf = DailyPerformance(date="2024-01-26")

        assert perf.total_revenue == 0.0
        assert perf.total_cost == 0.0
        assert perf.net_profit == 0.0
        assert len(perf.events) == 0

    def test_net_profit_calculation(self):
        """Test net profit calculation."""
        perf = DailyPerformance(
            date="2024-01-26",
            total_revenue=10.50,
            total_cost=3.25,
        )

        assert perf.net_profit == 7.25

    def test_add_discharge_event(self):
        """Test adding a discharge event."""
        perf = DailyPerformance(date="2024-01-26")

        event = TradingEvent(
            timestamp="2024-01-26T17:00:00",
            event_type="discharge",
            energy_kwh=5.0,
            price_per_kwh=0.40,
            total_amount=2.00,
            duration_minutes=60,
            battery_level_start=80.0,
            battery_level_end=50.0,
        )

        perf.add_discharge_event(event)

        assert perf.total_revenue == 2.00
        assert perf.total_energy_discharged_kwh == 5.0
        assert perf.discharge_events == 1
        assert perf.avg_sell_price == 0.40

    def test_add_charge_event(self):
        """Test adding a charge event."""
        perf = DailyPerformance(date="2024-01-26")

        event = TradingEvent(
            timestamp="2024-01-26T03:00:00",
            event_type="charge",
            energy_kwh=8.0,
            price_per_kwh=0.05,
            total_amount=0.40,
            duration_minutes=120,
            battery_level_start=20.0,
            battery_level_end=80.0,
        )

        perf.add_charge_event(event)

        assert perf.total_cost == 0.40
        assert perf.total_energy_charged_kwh == 8.0
        assert perf.charge_events == 1
        assert perf.avg_buy_price == 0.05

    def test_to_dict(self):
        """Test converting to dictionary."""
        perf = DailyPerformance(
            date="2024-01-26",
            total_revenue=5.0,
            total_cost=1.0,
        )

        result = perf.to_dict()

        assert result["date"] == "2024-01-26"
        assert result["total_revenue"] == 5.0
        assert result["net_profit"] == 4.0
        assert "events" in result


class TestPerformanceSummary:
    """Tests for PerformanceSummary dataclass."""

    def test_default_values(self):
        """Test default values."""
        summary = PerformanceSummary()

        assert summary.daily_profit == 0.0
        assert summary.total_profit == 0.0
        assert summary.days_tracked == 0

    def test_to_dict(self):
        """Test converting to dictionary."""
        summary = PerformanceSummary(
            daily_profit=5.0,
            monthly_profit=150.0,
            total_profit=500.0,
        )

        result = summary.to_dict()

        assert result["daily_profit"] == 5.0
        assert result["monthly_profit"] == 150.0


class TestPerformanceTracker:
    """Tests for PerformanceTracker class."""

    def test_init(self):
        """Test initialization."""
        tracker = PerformanceTracker("test_entry_id")

        assert tracker.entry_id == "test_entry_id"
        assert tracker.daily_revenue == 0.0
        assert tracker.daily_cost == 0.0

    def test_record_discharge(self):
        """Test recording a discharge event."""
        tracker = PerformanceTracker("test_entry")

        event = tracker.record_discharge(
            energy_kwh=5.0,
            price_per_kwh=0.40,
            duration_minutes=60,
            battery_level_start=80.0,
            battery_level_end=50.0,
        )

        assert event.event_type == "discharge"
        assert event.energy_kwh == 5.0
        assert event.total_amount == 2.00
        assert tracker.daily_revenue == 2.00
        assert tracker._total_revenue == 2.00

    def test_record_charge(self):
        """Test recording a charge event."""
        tracker = PerformanceTracker("test_entry")

        event = tracker.record_charge(
            energy_kwh=8.0,
            price_per_kwh=0.05,
            duration_minutes=120,
            battery_level_start=20.0,
            battery_level_end=80.0,
        )

        assert event.event_type == "charge"
        assert event.energy_kwh == 8.0
        assert event.total_amount == 0.40
        assert tracker.daily_cost == 0.40
        assert tracker._total_cost == 0.40

    def test_multiple_events_accumulate(self):
        """Test that multiple events accumulate correctly."""
        tracker = PerformanceTracker("test_entry")

        # Record multiple discharges
        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_discharge(3.0, 0.35, 45, 50.0, 35.0)

        # Record charges
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)

        assert tracker.daily_revenue == 3.05  # 2.00 + 1.05
        assert tracker.daily_cost == 0.40
        assert tracker.daily_profit == 2.65  # 3.05 - 0.40
        assert tracker.decisions_today == 3

    def test_energy_traded_today(self):
        """Test energy traded today calculation."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)

        assert tracker.energy_traded_today_kwh == 13.0  # 5.0 + 8.0

    def test_get_daily_performance(self):
        """Test getting daily performance."""
        tracker = PerformanceTracker("test_entry")

        # Should be None before any events
        perf_before = tracker.get_daily_performance()
        assert perf_before is None

        # Record an event
        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)

        # Should have data now
        perf_after = tracker.get_daily_performance()
        assert perf_after is not None
        assert perf_after.total_revenue == 2.00

    def test_get_summary(self):
        """Test getting performance summary."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)

        summary = tracker.get_summary()

        assert summary.daily_profit == 1.60  # 2.00 - 0.40
        assert summary.total_discharge_events == 1
        assert summary.total_charge_events == 1
        assert summary.days_tracked == 1

    def test_get_recent_events(self):
        """Test getting recent events."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)
        tracker.record_discharge(3.0, 0.35, 45, 70.0, 55.0)

        events = tracker.get_recent_events(limit=2)

        assert len(events) == 2
        # Most recent first
        assert events[0]["event_type"] == "discharge"

    def test_export_to_json(self):
        """Test JSON export."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)

        json_str = tracker.export_to_json()
        data = json.loads(json_str)

        assert data["entry_id"] == "test_entry"
        assert "summary" in data
        assert "daily_data" in data
        assert "export_time" in data

    def test_export_to_csv(self):
        """Test CSV export."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)

        csv_str = tracker.export_to_csv()
        lines = csv_str.split("\n")

        assert len(lines) == 2  # Header + 1 data row
        assert "date,revenue,cost" in lines[0]

    def test_export_events_to_csv(self):
        """Test events CSV export."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)

        csv_str = tracker.export_events_to_csv()
        lines = csv_str.split("\n")

        assert len(lines) == 3  # Header + 2 events
        assert "timestamp,event_type" in lines[0]


class TestPerformanceTrackerProperties:
    """Tests for PerformanceTracker properties."""

    def test_daily_properties_empty(self):
        """Test daily properties when no data."""
        tracker = PerformanceTracker("test_entry")

        assert tracker.daily_revenue == 0.0
        assert tracker.daily_cost == 0.0
        assert tracker.daily_profit == 0.0
        assert tracker.decisions_today == 0
        assert tracker.energy_traded_today_kwh == 0.0

    def test_total_profit(self):
        """Test total profit calculation."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)  # €2.00
        tracker.record_charge(8.0, 0.05, 120, 20.0, 80.0)  # €0.40

        assert tracker.total_profit == 1.60  # 2.00 - 0.40

    def test_monthly_profit(self):
        """Test monthly profit from summary."""
        tracker = PerformanceTracker("test_entry")

        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)

        assert tracker.monthly_profit == 2.00


class TestPerformanceScenarios:
    """Test realistic performance scenarios."""

    def test_typical_day_trading(self):
        """Test a typical day with morning charging and evening discharging."""
        tracker = PerformanceTracker("test_entry")

        # Morning: cheap charging
        tracker.record_charge(6.0, 0.05, 60, 25.0, 55.0)
        tracker.record_charge(4.0, 0.04, 45, 55.0, 75.0)

        # Evening: expensive discharging
        tracker.record_discharge(5.0, 0.45, 60, 90.0, 60.0)
        tracker.record_discharge(4.0, 0.40, 50, 60.0, 35.0)

        # Calculate expected values
        # Cost: 6*0.05 + 4*0.04 = 0.30 + 0.16 = 0.46
        # Revenue: 5*0.45 + 4*0.40 = 2.25 + 1.60 = 3.85
        # Profit: 3.85 - 0.46 = 3.39

        assert abs(tracker.daily_cost - 0.46) < 0.01
        assert abs(tracker.daily_revenue - 3.85) < 0.01
        assert abs(tracker.daily_profit - 3.39) < 0.01

        # Check summary
        summary = tracker.get_summary()
        assert summary.total_discharge_events == 2
        assert summary.total_charge_events == 2
        assert summary.total_energy_discharged_kwh == 9.0
        assert summary.total_energy_charged_kwh == 10.0

    def test_negative_price_scenario(self):
        """Test behavior during negative electricity prices."""
        tracker = PerformanceTracker("test_entry")

        # Charging during negative prices (we get paid!)
        event = tracker.record_charge(
            energy_kwh=10.0,
            price_per_kwh=-0.05,  # Negative price
            duration_minutes=120,
            battery_level_start=20.0,
            battery_level_end=80.0,
        )

        # Cost is negative (we earn money by charging)
        assert event.total_amount == -0.50
        assert tracker.daily_cost == -0.50
        assert tracker.daily_profit == 0.50  # 0 revenue - (-0.50 cost) = 0.50

    def test_profitable_vs_unprofitable_days(self):
        """Test best/worst day tracking."""
        tracker = PerformanceTracker("test_entry")

        # Simulate today's trading (profitable)
        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)  # €2.00 revenue
        tracker.record_charge(5.0, 0.10, 60, 30.0, 60.0)  # €0.50 cost
        # Net: €1.50 profit

        summary = tracker.get_summary()

        # With only one day, it's both best and worst
        assert summary.best_day_profit == 1.50
        assert summary.worst_day_profit == 1.50
        assert summary.best_day_date is not None


class TestDataCleanup:
    """Tests for data cleanup functionality."""

    def test_cleanup_preserves_recent_data(self):
        """Test that recent data is preserved."""
        tracker = PerformanceTracker("test_entry")

        # Record event today
        tracker.record_discharge(5.0, 0.40, 60, 80.0, 50.0)

        # Manually trigger cleanup
        tracker._cleanup_old_data()

        # Today's data should still be there
        assert tracker.get_daily_performance() is not None

    def test_max_days_constant(self):
        """Test that MAX_DAYS_IN_MEMORY is reasonable."""
        assert MAX_DAYS_IN_MEMORY >= 7  # At least a week
        assert MAX_DAYS_IN_MEMORY <= 365  # At most a year
