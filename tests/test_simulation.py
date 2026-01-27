"""Tests for simulation/paper-trading mode."""

import json
from unittest.mock import MagicMock

from custom_components.battery_energy_trading.simulation import (
    MAX_ACTION_LOG_SIZE,
    SimulatedAction,
    SimulationState,
    SimulationStats,
    TradingSimulator,
)


class TestSimulatedAction:
    """Tests for SimulatedAction dataclass."""

    def test_create_discharge_action(self):
        """Test creating a discharge action."""
        action = SimulatedAction(
            timestamp="2024-01-26T17:00:00+02:00",
            action="discharge",
            price=0.42,
            battery_level=85.0,
            reason="Price 42c exceeds threshold 15c",
            energy_kwh=2.5,
            would_have_earned=1.05,
        )

        assert action.action == "discharge"
        assert action.price == 0.42
        assert action.battery_level == 85.0
        assert action.energy_kwh == 2.5
        assert action.would_have_earned == 1.05
        assert action.would_have_cost == 0.0

    def test_create_charge_action(self):
        """Test creating a charge action."""
        action = SimulatedAction(
            timestamp="2024-01-26T03:00:00+02:00",
            action="charge",
            price=0.05,
            battery_level=25.0,
            reason="Price 5c below threshold 10c",
            energy_kwh=5.0,
            would_have_cost=0.25,
        )

        assert action.action == "charge"
        assert action.price == 0.05
        assert action.energy_kwh == 5.0
        assert action.would_have_cost == 0.25
        assert action.would_have_earned == 0.0

    def test_to_dict(self):
        """Test converting action to dictionary."""
        action = SimulatedAction(
            timestamp="2024-01-26T17:00:00",
            action="discharge",
            price=0.30,
            battery_level=70.0,
            reason="Test reason",
            energy_kwh=2.0,
            would_have_earned=0.60,
        )

        result = action.to_dict()

        assert isinstance(result, dict)
        assert result["timestamp"] == "2024-01-26T17:00:00"
        assert result["action"] == "discharge"
        assert result["price"] == 0.30
        assert result["energy_kwh"] == 2.0


class TestSimulationStats:
    """Tests for SimulationStats dataclass."""

    def test_default_values(self):
        """Test default values."""
        stats = SimulationStats()

        assert stats.total_simulated_revenue == 0.0
        assert stats.total_simulated_cost == 0.0
        assert stats.total_discharge_events == 0
        assert stats.total_charge_events == 0
        assert stats.net_profit == 0.0

    def test_net_profit_calculation(self):
        """Test net profit calculation."""
        stats = SimulationStats(
            total_simulated_revenue=10.50,
            total_simulated_cost=3.25,
        )

        assert stats.net_profit == 7.25

    def test_net_profit_negative(self):
        """Test negative net profit (loss)."""
        stats = SimulationStats(
            total_simulated_revenue=2.00,
            total_simulated_cost=5.00,
        )

        assert stats.net_profit == -3.00

    def test_to_dict_includes_net_profit(self):
        """Test that to_dict includes calculated net_profit."""
        stats = SimulationStats(
            total_simulated_revenue=15.00,
            total_simulated_cost=5.00,
        )

        result = stats.to_dict()

        assert "net_profit" in result
        assert result["net_profit"] == 10.00


class TestSimulationState:
    """Tests for SimulationState."""

    def test_default_state(self):
        """Test default state."""
        state = SimulationState()

        assert state.enabled is False
        assert len(state.action_log) == 0

    def test_reset(self):
        """Test state reset."""
        state = SimulationState(enabled=True)
        state.stats.total_simulated_revenue = 100.0
        state.action_log.append(
            SimulatedAction(
                timestamp="2024-01-26T12:00:00",
                action="discharge",
                price=0.30,
                battery_level=80.0,
                reason="Test",
            )
        )

        state.reset()

        assert state.stats.total_simulated_revenue == 0.0
        assert len(state.action_log) == 0


class TestTradingSimulator:
    """Tests for TradingSimulator class."""

    def test_init(self):
        """Test simulator initialization."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry_id")

        assert simulator.hass == hass
        assert simulator.entry_id == "test_entry_id"
        assert simulator.is_enabled is False

    def test_enable_disable(self):
        """Test enable/disable simulation mode."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")

        simulator.enable()
        assert simulator.is_enabled is True
        assert simulator.state.stats.simulation_start_time is not None

        simulator.disable()
        assert simulator.is_enabled is False
        # Data is preserved after disable
        assert simulator.state.stats.simulation_start_time is not None

    def test_reset(self):
        """Test reset clears all data."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()
        simulator.simulate_discharge(0.30, 80.0, 5.0, 0.25, "Test")

        simulator.reset()

        assert simulator.state.stats.total_simulated_revenue == 0.0
        assert len(simulator.state.action_log) == 0

    def test_simulate_discharge(self):
        """Test simulating discharge action."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        action = simulator.simulate_discharge(
            price=0.40,
            battery_level=85.0,
            discharge_rate_kw=5.0,
            duration_hours=0.25,  # 15-minute slot
            reason="Price exceeds threshold",
        )

        assert action.action == "discharge"
        assert action.price == 0.40
        assert action.energy_kwh == 1.25  # 5 kW * 0.25 hours
        assert action.would_have_earned == 0.50  # 1.25 kWh * €0.40

        # Check stats updated
        assert simulator.state.stats.total_simulated_revenue == 0.50
        assert simulator.state.stats.total_discharge_events == 1
        assert simulator.state.stats.total_energy_discharged_kwh == 1.25

    def test_simulate_charge(self):
        """Test simulating charge action."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        action = simulator.simulate_charge(
            price=0.05,
            battery_level=30.0,
            charge_rate_kw=5.0,
            duration_hours=0.25,
            reason="Price below threshold",
        )

        assert action.action == "charge"
        assert action.price == 0.05
        assert action.energy_kwh == 1.25
        assert action.would_have_cost == 0.0625  # 1.25 kWh * €0.05

        # Check stats updated
        assert simulator.state.stats.total_simulated_cost == 0.0625
        assert simulator.state.stats.total_charge_events == 1
        assert simulator.state.stats.total_energy_charged_kwh == 1.25

    def test_simulate_idle(self):
        """Test simulating idle (no action)."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        action = simulator.simulate_idle(
            price=0.15,
            battery_level=50.0,
            reason="Price not optimal for trading",
        )

        assert action.action == "idle"
        assert action.energy_kwh == 0.0
        assert action.would_have_earned == 0.0
        assert action.would_have_cost == 0.0

    def test_multiple_actions_accumulate(self):
        """Test that multiple actions accumulate in stats."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Simulate 3 discharge actions
        simulator.simulate_discharge(0.40, 90.0, 5.0, 0.25, "High price")
        simulator.simulate_discharge(0.35, 80.0, 5.0, 0.25, "High price")
        simulator.simulate_discharge(0.45, 70.0, 5.0, 0.25, "High price")

        # Simulate 2 charge actions
        simulator.simulate_charge(0.05, 40.0, 5.0, 0.25, "Low price")
        simulator.simulate_charge(0.03, 50.0, 5.0, 0.25, "Low price")

        stats = simulator.get_stats()

        assert stats["total_discharge_events"] == 3
        assert stats["total_charge_events"] == 2
        assert stats["total_energy_discharged_kwh"] == 3.75  # 3 * 1.25
        assert stats["total_energy_charged_kwh"] == 2.50  # 2 * 1.25

    def test_get_recent_actions(self):
        """Test getting recent actions."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Add several actions
        simulator.simulate_discharge(0.30, 80.0, 5.0, 0.25, "Action 1")
        simulator.simulate_charge(0.05, 50.0, 5.0, 0.25, "Action 2")
        simulator.simulate_idle(0.15, 60.0, "Action 3")

        recent = simulator.get_recent_actions(limit=10)

        # Most recent first
        assert len(recent) == 3
        assert recent[0]["action"] == "idle"
        assert recent[1]["action"] == "charge"
        assert recent[2]["action"] == "discharge"

    def test_get_recent_actions_with_limit(self):
        """Test that limit works correctly."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Add 5 actions
        for i in range(5):
            simulator.simulate_discharge(0.30, 80.0, 5.0, 0.25, f"Action {i}")

        recent = simulator.get_recent_actions(limit=3)

        assert len(recent) == 3

    def test_action_log_max_size(self):
        """Test that action log respects max size."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Add more than MAX_ACTION_LOG_SIZE actions
        for i in range(MAX_ACTION_LOG_SIZE + 100):
            simulator.simulate_idle(0.15, 50.0, f"Action {i}")

        assert len(simulator.state.action_log) == MAX_ACTION_LOG_SIZE

    def test_export_to_json(self):
        """Test JSON export."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()
        simulator.simulate_discharge(0.35, 75.0, 5.0, 0.25, "Test")

        json_str = simulator.export_to_json()
        data = json.loads(json_str)

        assert "enabled" in data
        assert "stats" in data
        assert "actions" in data
        assert "export_time" in data
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action"] == "discharge"

    def test_export_actions_to_csv(self):
        """Test CSV export."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()
        simulator.simulate_discharge(0.40, 80.0, 5.0, 0.25, "High price")
        simulator.simulate_charge(0.05, 40.0, 5.0, 0.25, "Low price")

        csv_str = simulator.export_actions_to_csv()
        lines = csv_str.split("\n")

        assert len(lines) == 3  # Header + 2 data rows
        assert "timestamp,action,price" in lines[0]
        assert "discharge" in lines[1]
        assert "charge" in lines[2]

    def test_export_empty_csv(self):
        """Test CSV export with no actions."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")

        csv_str = simulator.export_actions_to_csv()

        # Should have header only
        assert "timestamp,action,price" in csv_str
        lines = csv_str.strip().split("\n")
        assert len(lines) == 1

    def test_get_stats(self):
        """Test getting stats dictionary."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()
        simulator.simulate_discharge(0.40, 80.0, 5.0, 0.25, "Test")
        simulator.simulate_charge(0.05, 50.0, 5.0, 0.25, "Test")

        stats = simulator.get_stats()

        assert isinstance(stats, dict)
        assert "total_simulated_revenue" in stats
        assert "total_simulated_cost" in stats
        assert "net_profit" in stats
        assert (
            stats["net_profit"] == stats["total_simulated_revenue"] - stats["total_simulated_cost"]
        )


class TestSimulationScenarios:
    """Test realistic simulation scenarios."""

    def test_typical_day_scenario(self):
        """Test a typical day with morning charging and evening discharging."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Morning: charge during low prices (3 slots at 15 min each)
        for _ in range(3):
            simulator.simulate_charge(0.05, 30.0, 5.0, 0.25, "Morning low price")

        # Midday: idle during moderate prices
        for _ in range(8):
            simulator.simulate_idle(0.15, 60.0, "Moderate price - idle")

        # Evening: discharge during peak prices (4 slots)
        for _ in range(4):
            simulator.simulate_discharge(0.45, 80.0, 5.0, 0.25, "Evening peak price")

        stats = simulator.get_stats()

        # Energy: 3 * 1.25 kWh charged, 4 * 1.25 kWh discharged
        assert stats["total_energy_charged_kwh"] == 3.75
        assert stats["total_energy_discharged_kwh"] == 5.0

        # Cost: 3.75 kWh * €0.05 = €0.1875
        assert abs(stats["total_simulated_cost"] - 0.1875) < 0.001

        # Revenue: 5.0 kWh * €0.45 = €2.25
        assert abs(stats["total_simulated_revenue"] - 2.25) < 0.001

        # Net profit: €2.25 - €0.1875 = €2.0625
        assert abs(stats["net_profit"] - 2.0625) < 0.001

    def test_negative_price_scenario(self):
        """Test behavior during negative electricity prices."""
        hass = MagicMock()
        simulator = TradingSimulator(hass, "test_entry")
        simulator.enable()

        # Charging during negative prices (we get paid!)
        action = simulator.simulate_charge(
            price=-0.05,  # Negative price
            battery_level=20.0,
            charge_rate_kw=5.0,
            duration_hours=0.25,
            reason="Negative price - getting paid to charge!",
        )

        # Cost is negative (we earn money by charging)
        assert action.would_have_cost == -0.0625  # 1.25 kWh * -€0.05
        assert simulator.state.stats.total_simulated_cost == -0.0625
