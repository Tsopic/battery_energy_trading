"""Simulation/paper-trading mode for Battery Energy Trading."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Maximum number of actions to keep in the log
MAX_ACTION_LOG_SIZE = 1000


@dataclass
class SimulatedAction:
    """Represents a simulated trading action."""

    timestamp: str
    action: str  # "discharge", "charge", "idle"
    price: float
    battery_level: float
    reason: str
    energy_kwh: float = 0.0
    would_have_earned: float = 0.0
    would_have_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SimulationStats:
    """Accumulated simulation statistics."""

    total_simulated_revenue: float = 0.0
    total_simulated_cost: float = 0.0
    total_discharge_events: int = 0
    total_charge_events: int = 0
    total_energy_discharged_kwh: float = 0.0
    total_energy_charged_kwh: float = 0.0
    simulation_start_time: str | None = None
    last_action_time: str | None = None

    @property
    def net_profit(self) -> float:
        """Calculate net profit (revenue - cost)."""
        return self.total_simulated_revenue - self.total_simulated_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with calculated fields."""
        data = asdict(self)
        data["net_profit"] = self.net_profit
        return data


@dataclass
class SimulationState:
    """Complete simulation state including actions and stats."""

    enabled: bool = False
    stats: SimulationStats = field(default_factory=SimulationStats)
    action_log: deque[SimulatedAction] = field(
        default_factory=lambda: deque(maxlen=MAX_ACTION_LOG_SIZE)
    )

    def reset(self) -> None:
        """Reset simulation state."""
        self.stats = SimulationStats()
        self.action_log.clear()
        _LOGGER.info("Simulation state reset")


class TradingSimulator:
    """Simulator for battery trading decisions.

    Tracks what actions would be taken without actually controlling the inverter.
    Useful for testing strategies, validating thresholds, and debugging.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the simulator.

        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID for storing simulation state
        """
        self.hass = hass
        self.entry_id = entry_id
        self.state = SimulationState()

    def enable(self) -> None:
        """Enable simulation mode."""
        if not self.state.enabled:
            self.state.enabled = True
            self.state.stats.simulation_start_time = datetime.now().isoformat()
            _LOGGER.info("Simulation mode enabled for entry %s", self.entry_id)

    def disable(self) -> None:
        """Disable simulation mode (keeps data for review)."""
        self.state.enabled = False
        _LOGGER.info("Simulation mode disabled for entry %s", self.entry_id)

    def reset(self) -> None:
        """Reset all simulation data."""
        self.state.reset()

    @property
    def is_enabled(self) -> bool:
        """Check if simulation is enabled."""
        return self.state.enabled

    def simulate_discharge(
        self,
        price: float,
        battery_level: float,
        discharge_rate_kw: float,
        duration_hours: float,
        reason: str,
    ) -> SimulatedAction:
        """Simulate a discharge action.

        Args:
            price: Current electricity price (EUR/kWh)
            battery_level: Current battery level (%)
            discharge_rate_kw: Discharge power (kW)
            duration_hours: Duration of discharge slot (hours)
            reason: Reason for the action

        Returns:
            SimulatedAction record
        """
        energy_kwh = discharge_rate_kw * duration_hours
        revenue = energy_kwh * price

        action = SimulatedAction(
            timestamp=datetime.now().isoformat(),
            action="discharge",
            price=price,
            battery_level=battery_level,
            reason=reason,
            energy_kwh=energy_kwh,
            would_have_earned=revenue,
        )

        self._record_action(action)

        # Update stats
        self.state.stats.total_simulated_revenue += revenue
        self.state.stats.total_discharge_events += 1
        self.state.stats.total_energy_discharged_kwh += energy_kwh
        self.state.stats.last_action_time = action.timestamp

        _LOGGER.info(
            "Simulated DISCHARGE: %.2f kWh at €%.4f/kWh = €%.4f",
            energy_kwh,
            price,
            revenue,
        )

        return action

    def simulate_charge(
        self,
        price: float,
        battery_level: float,
        charge_rate_kw: float,
        duration_hours: float,
        reason: str,
    ) -> SimulatedAction:
        """Simulate a charge action.

        Args:
            price: Current electricity price (EUR/kWh)
            battery_level: Current battery level (%)
            charge_rate_kw: Charge power (kW)
            duration_hours: Duration of charge slot (hours)
            reason: Reason for the action

        Returns:
            SimulatedAction record
        """
        energy_kwh = charge_rate_kw * duration_hours
        cost = energy_kwh * price

        action = SimulatedAction(
            timestamp=datetime.now().isoformat(),
            action="charge",
            price=price,
            battery_level=battery_level,
            reason=reason,
            energy_kwh=energy_kwh,
            would_have_cost=cost,
        )

        self._record_action(action)

        # Update stats
        self.state.stats.total_simulated_cost += cost
        self.state.stats.total_charge_events += 1
        self.state.stats.total_energy_charged_kwh += energy_kwh
        self.state.stats.last_action_time = action.timestamp

        _LOGGER.info(
            "Simulated CHARGE: %.2f kWh at €%.4f/kWh = €%.4f cost",
            energy_kwh,
            price,
            cost,
        )

        return action

    def simulate_idle(
        self,
        price: float,
        battery_level: float,
        reason: str,
    ) -> SimulatedAction:
        """Record an idle decision (no action taken).

        Args:
            price: Current electricity price (EUR/kWh)
            battery_level: Current battery level (%)
            reason: Reason for not taking action

        Returns:
            SimulatedAction record
        """
        action = SimulatedAction(
            timestamp=datetime.now().isoformat(),
            action="idle",
            price=price,
            battery_level=battery_level,
            reason=reason,
        )

        self._record_action(action)
        self.state.stats.last_action_time = action.timestamp

        _LOGGER.debug("Simulated IDLE: %s", reason)

        return action

    def _record_action(self, action: SimulatedAction) -> None:
        """Record an action to the log."""
        self.state.action_log.append(action)

    def get_recent_actions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent actions from the log.

        Args:
            limit: Maximum number of actions to return

        Returns:
            List of action dictionaries (most recent first)
        """
        actions = list(self.state.action_log)
        # Return most recent first
        return [a.to_dict() for a in reversed(actions[-limit:])]

    def get_stats(self) -> dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation statistics
        """
        return self.state.stats.to_dict()

    def export_to_json(self) -> str:
        """Export simulation data to JSON string.

        Returns:
            JSON string with all simulation data
        """
        data = {
            "enabled": self.state.enabled,
            "stats": self.state.stats.to_dict(),
            "actions": [a.to_dict() for a in self.state.action_log],
            "export_time": datetime.now().isoformat(),
        }
        return json.dumps(data, indent=2)

    def export_actions_to_csv(self) -> str:
        """Export action log to CSV format.

        Returns:
            CSV string with action log
        """
        if not self.state.action_log:
            return "timestamp,action,price,battery_level,reason,energy_kwh,would_have_earned,would_have_cost\n"

        lines = [
            "timestamp,action,price,battery_level,reason,energy_kwh,would_have_earned,would_have_cost"
        ]
        for action in self.state.action_log:
            lines.append(
                f"{action.timestamp},{action.action},{action.price:.4f},"
                f"{action.battery_level:.1f},{action.reason},{action.energy_kwh:.2f},"
                f"{action.would_have_earned:.4f},{action.would_have_cost:.4f}"
            )
        return "\n".join(lines)
