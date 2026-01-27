"""Historical performance tracking for Battery Energy Trading."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


_LOGGER = logging.getLogger(__name__)

# Maximum number of events to keep in memory
MAX_EVENTS_PER_DAY = 100
MAX_DAYS_IN_MEMORY = 31  # Keep ~1 month of daily data


@dataclass
class TradingEvent:
    """Represents a single trading event (discharge or charge)."""

    timestamp: str
    event_type: str  # "discharge" or "charge"
    energy_kwh: float
    price_per_kwh: float
    total_amount: float  # Revenue for discharge, cost for charge
    duration_minutes: int
    battery_level_start: float
    battery_level_end: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DailyPerformance:
    """Performance metrics for a single day."""

    date: str
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_energy_discharged_kwh: float = 0.0
    total_energy_charged_kwh: float = 0.0
    discharge_events: int = 0
    charge_events: int = 0
    avg_sell_price: float = 0.0
    avg_buy_price: float = 0.0
    currency: str = "EUR"
    events: list[TradingEvent] = field(default_factory=list)

    @property
    def net_profit(self) -> float:
        """Calculate net profit (revenue - cost)."""
        return self.total_revenue - self.total_cost

    def add_discharge_event(self, event: TradingEvent) -> None:
        """Add a discharge event and update totals."""
        self.events.append(event)
        self.total_revenue += event.total_amount
        self.total_energy_discharged_kwh += event.energy_kwh
        self.discharge_events += 1
        self._recalculate_avg_prices()

    def add_charge_event(self, event: TradingEvent) -> None:
        """Add a charge event and update totals."""
        self.events.append(event)
        self.total_cost += event.total_amount
        self.total_energy_charged_kwh += event.energy_kwh
        self.charge_events += 1
        self._recalculate_avg_prices()

    def _recalculate_avg_prices(self) -> None:
        """Recalculate average buy/sell prices."""
        discharge_prices = [e.price_per_kwh for e in self.events if e.event_type == "discharge"]
        charge_prices = [e.price_per_kwh for e in self.events if e.event_type == "charge"]

        if discharge_prices:
            self.avg_sell_price = sum(discharge_prices) / len(discharge_prices)
        if charge_prices:
            self.avg_buy_price = sum(charge_prices) / len(charge_prices)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with calculated fields."""
        data = {
            "date": self.date,
            "total_revenue": self.total_revenue,
            "total_cost": self.total_cost,
            "net_profit": self.net_profit,
            "total_energy_discharged_kwh": self.total_energy_discharged_kwh,
            "total_energy_charged_kwh": self.total_energy_charged_kwh,
            "discharge_events": self.discharge_events,
            "charge_events": self.charge_events,
            "avg_sell_price": self.avg_sell_price,
            "avg_buy_price": self.avg_buy_price,
            "currency": self.currency,
            "events": [e.to_dict() for e in self.events],
        }
        return data


@dataclass
class PerformanceSummary:
    """Summary of performance over multiple periods."""

    daily_profit: float = 0.0
    weekly_profit: float = 0.0
    monthly_profit: float = 0.0
    total_profit: float = 0.0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_energy_discharged_kwh: float = 0.0
    total_energy_charged_kwh: float = 0.0
    total_discharge_events: int = 0
    total_charge_events: int = 0
    days_tracked: int = 0
    avg_daily_profit: float = 0.0
    best_day_profit: float = 0.0
    best_day_date: str | None = None
    worst_day_profit: float = 0.0
    worst_day_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PerformanceTracker:
    """Track historical trading performance.

    Records trading events and calculates performance metrics
    for daily, weekly, monthly, and all-time periods.
    """

    def __init__(self, entry_id: str) -> None:
        """Initialize the performance tracker.

        Args:
            entry_id: Config entry ID for this tracker instance
        """
        self.entry_id = entry_id
        self._daily_data: dict[str, DailyPerformance] = {}
        self._total_revenue: float = 0.0
        self._total_cost: float = 0.0
        self._total_energy_discharged: float = 0.0
        self._total_energy_charged: float = 0.0

    def record_discharge(
        self,
        energy_kwh: float,
        price_per_kwh: float,
        duration_minutes: int,
        battery_level_start: float,
        battery_level_end: float,
    ) -> TradingEvent:
        """Record a discharge (sell) event.

        Args:
            energy_kwh: Energy discharged in kWh
            price_per_kwh: Sell price per kWh
            duration_minutes: Duration of the discharge
            battery_level_start: Battery level at start (%)
            battery_level_end: Battery level at end (%)

        Returns:
            The recorded TradingEvent
        """
        revenue = energy_kwh * price_per_kwh

        event = TradingEvent(
            timestamp=datetime.now().isoformat(),
            event_type="discharge",
            energy_kwh=energy_kwh,
            price_per_kwh=price_per_kwh,
            total_amount=revenue,
            duration_minutes=duration_minutes,
            battery_level_start=battery_level_start,
            battery_level_end=battery_level_end,
        )

        today = self._get_or_create_today()
        today.add_discharge_event(event)

        self._total_revenue += revenue
        self._total_energy_discharged += energy_kwh

        _LOGGER.info(
            "Recorded DISCHARGE: %.2f kWh at €%.4f = €%.4f revenue",
            energy_kwh,
            price_per_kwh,
            revenue,
        )

        return event

    def record_charge(
        self,
        energy_kwh: float,
        price_per_kwh: float,
        duration_minutes: int,
        battery_level_start: float,
        battery_level_end: float,
    ) -> TradingEvent:
        """Record a charge (buy) event.

        Args:
            energy_kwh: Energy charged in kWh
            price_per_kwh: Buy price per kWh
            duration_minutes: Duration of the charge
            battery_level_start: Battery level at start (%)
            battery_level_end: Battery level at end (%)

        Returns:
            The recorded TradingEvent
        """
        cost = energy_kwh * price_per_kwh

        event = TradingEvent(
            timestamp=datetime.now().isoformat(),
            event_type="charge",
            energy_kwh=energy_kwh,
            price_per_kwh=price_per_kwh,
            total_amount=cost,
            duration_minutes=duration_minutes,
            battery_level_start=battery_level_start,
            battery_level_end=battery_level_end,
        )

        today = self._get_or_create_today()
        today.add_charge_event(event)

        self._total_cost += cost
        self._total_energy_charged += energy_kwh

        _LOGGER.info(
            "Recorded CHARGE: %.2f kWh at €%.4f = €%.4f cost",
            energy_kwh,
            price_per_kwh,
            cost,
        )

        return event

    def _get_or_create_today(self) -> DailyPerformance:
        """Get or create today's performance record."""
        today_str = date.today().isoformat()
        if today_str not in self._daily_data:
            self._daily_data[today_str] = DailyPerformance(date=today_str)
            self._cleanup_old_data()
        return self._daily_data[today_str]

    def _cleanup_old_data(self) -> None:
        """Remove data older than MAX_DAYS_IN_MEMORY."""
        if len(self._daily_data) <= MAX_DAYS_IN_MEMORY:
            return

        cutoff_date = (date.today() - timedelta(days=MAX_DAYS_IN_MEMORY)).isoformat()
        old_dates = [d for d in self._daily_data if d < cutoff_date]

        for old_date in old_dates:
            del self._daily_data[old_date]

        _LOGGER.debug("Cleaned up %d old daily records", len(old_dates))

    def get_daily_performance(self, target_date: date | None = None) -> DailyPerformance | None:
        """Get performance for a specific day.

        Args:
            target_date: Date to get performance for (default: today)

        Returns:
            DailyPerformance or None if no data for that day
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()
        return self._daily_data.get(date_str)

    def get_summary(self) -> PerformanceSummary:
        """Calculate performance summary across all periods.

        Returns:
            PerformanceSummary with calculated metrics
        """
        summary = PerformanceSummary()

        today = date.today()
        today_str = today.isoformat()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        month_start = today.replace(day=1).isoformat()

        best_profit = float("-inf")
        worst_profit = float("inf")

        for date_str, perf in self._daily_data.items():
            profit = perf.net_profit

            # Total aggregates
            summary.total_profit += profit
            summary.total_revenue += perf.total_revenue
            summary.total_cost += perf.total_cost
            summary.total_energy_discharged_kwh += perf.total_energy_discharged_kwh
            summary.total_energy_charged_kwh += perf.total_energy_charged_kwh
            summary.total_discharge_events += perf.discharge_events
            summary.total_charge_events += perf.charge_events
            summary.days_tracked += 1

            # Daily
            if date_str == today_str:
                summary.daily_profit = profit

            # Weekly
            if date_str >= week_start:
                summary.weekly_profit += profit

            # Monthly
            if date_str >= month_start:
                summary.monthly_profit += profit

            # Best/worst days
            if profit > best_profit:
                best_profit = profit
                summary.best_day_profit = profit
                summary.best_day_date = date_str

            if profit < worst_profit:
                worst_profit = profit
                summary.worst_day_profit = profit
                summary.worst_day_date = date_str

        # Average daily profit
        if summary.days_tracked > 0:
            summary.avg_daily_profit = summary.total_profit / summary.days_tracked

        return summary

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent trading events across all days.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries (most recent first)
        """
        all_events: list[TradingEvent] = []
        for perf in self._daily_data.values():
            all_events.extend(perf.events)

        # Sort by timestamp descending
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        return [e.to_dict() for e in all_events[:limit]]

    def export_to_json(self) -> str:
        """Export all performance data to JSON.

        Returns:
            JSON string with all performance data
        """
        data = {
            "entry_id": self.entry_id,
            "export_time": datetime.now().isoformat(),
            "summary": self.get_summary().to_dict(),
            "daily_data": {
                date_str: perf.to_dict() for date_str, perf in sorted(self._daily_data.items())
            },
        }
        return json.dumps(data, indent=2)

    def export_to_csv(self) -> str:
        """Export daily performance to CSV format.

        Returns:
            CSV string with daily performance data
        """
        lines = [
            "date,revenue,cost,net_profit,energy_discharged_kwh,energy_charged_kwh,"
            "discharge_events,charge_events,avg_sell_price,avg_buy_price"
        ]

        for date_str, perf in sorted(self._daily_data.items()):
            lines.append(
                f"{date_str},{perf.total_revenue:.4f},{perf.total_cost:.4f},"
                f"{perf.net_profit:.4f},{perf.total_energy_discharged_kwh:.2f},"
                f"{perf.total_energy_charged_kwh:.2f},{perf.discharge_events},"
                f"{perf.charge_events},{perf.avg_sell_price:.4f},{perf.avg_buy_price:.4f}"
            )

        return "\n".join(lines)

    def export_events_to_csv(self) -> str:
        """Export all trading events to CSV format.

        Returns:
            CSV string with all events
        """
        lines = [
            "timestamp,event_type,energy_kwh,price_per_kwh,total_amount,"
            "duration_minutes,battery_level_start,battery_level_end"
        ]

        all_events = self.get_recent_events(limit=10000)  # Get all events
        for event in reversed(all_events):  # Chronological order
            lines.append(
                f"{event['timestamp']},{event['event_type']},{event['energy_kwh']:.2f},"
                f"{event['price_per_kwh']:.4f},{event['total_amount']:.4f},"
                f"{event['duration_minutes']},{event['battery_level_start']:.1f},"
                f"{event['battery_level_end']:.1f}"
            )

        return "\n".join(lines)

    # Properties for sensor values
    @property
    def daily_revenue(self) -> float:
        """Get today's total revenue."""
        today = self.get_daily_performance()
        return today.total_revenue if today else 0.0

    @property
    def daily_cost(self) -> float:
        """Get today's total cost."""
        today = self.get_daily_performance()
        return today.total_cost if today else 0.0

    @property
    def daily_profit(self) -> float:
        """Get today's net profit."""
        today = self.get_daily_performance()
        return today.net_profit if today else 0.0

    @property
    def monthly_profit(self) -> float:
        """Get current month's profit."""
        return self.get_summary().monthly_profit

    @property
    def total_profit(self) -> float:
        """Get all-time total profit."""
        return self._total_revenue - self._total_cost

    @property
    def decisions_today(self) -> int:
        """Get count of trading decisions today."""
        today = self.get_daily_performance()
        if today:
            return today.discharge_events + today.charge_events
        return 0

    @property
    def energy_traded_today_kwh(self) -> float:
        """Get total energy traded today (discharged + charged)."""
        today = self.get_daily_performance()
        if today:
            return today.total_energy_discharged_kwh + today.total_energy_charged_kwh
        return 0.0
