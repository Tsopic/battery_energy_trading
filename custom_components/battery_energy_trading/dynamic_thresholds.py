"""Dynamic price threshold calculation based on NordPool data analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .const import DEFAULT_BUY_PERCENTILE, DEFAULT_MIN_SPREAD, DEFAULT_SELL_PERCENTILE


_LOGGER = logging.getLogger(__name__)


@dataclass
class DynamicThresholds:
    """Container for calculated dynamic thresholds."""

    sell_threshold: float | None
    buy_threshold: float | None
    spread: float | None
    trading_recommended: bool
    price_count: int
    min_price: float | None
    max_price: float | None
    avg_price: float | None
    calculated_at: datetime


class DynamicThresholdCalculator:
    """Calculate dynamic price thresholds from NordPool data."""

    def __init__(
        self,
        sell_percentile: float = DEFAULT_SELL_PERCENTILE,
        buy_percentile: float = DEFAULT_BUY_PERCENTILE,
        min_spread: float = DEFAULT_MIN_SPREAD,
    ) -> None:
        """Initialize the calculator.

        Args:
            sell_percentile: Percentile for sell threshold (default 80 = top 20%)
            buy_percentile: Percentile for buy threshold (default 20 = bottom 20%)
            min_spread: Minimum spread required for trading to be profitable (EUR)
        """
        self.sell_percentile = max(0.0, min(100.0, sell_percentile))
        self.buy_percentile = max(0.0, min(100.0, buy_percentile))
        self.min_spread = max(0.0, min_spread)

    def calculate_percentile(self, prices: list[float], percentile: float) -> float:
        """Calculate the percentile value from a list of prices.

        Uses linear interpolation between closest ranks for non-integer percentiles.

        Args:
            prices: List of price values
            percentile: Percentile to calculate (0-100)

        Returns:
            The percentile value
        """
        if not prices:
            return 0.0

        sorted_prices = sorted(prices)
        n = len(sorted_prices)

        if n == 1:
            return sorted_prices[0]

        # Calculate the index for the percentile
        # Using the "inclusive" method (same as numpy's default)
        index = (percentile / 100.0) * (n - 1)
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, n - 1)

        # Linear interpolation
        fraction = index - lower_idx
        return sorted_prices[lower_idx] * (1 - fraction) + sorted_prices[upper_idx] * fraction

    def calculate_thresholds(
        self,
        raw_today: list[dict[str, Any]] | None,
        raw_tomorrow: list[dict[str, Any]] | None = None,
    ) -> DynamicThresholds:
        """Calculate dynamic thresholds from NordPool price data.

        Args:
            raw_today: Today's price data from NordPool sensor (list of dicts with 'value')
            raw_tomorrow: Tomorrow's price data (optional, available after ~14:00)

        Returns:
            DynamicThresholds object with calculated values
        """
        now = datetime.now()

        # Combine today and tomorrow data if available
        all_prices: list[dict[str, Any]] = []
        if raw_today:
            all_prices.extend(raw_today)
        if raw_tomorrow:
            all_prices.extend(raw_tomorrow)

        if not all_prices:
            _LOGGER.warning("No price data available for dynamic threshold calculation")
            return DynamicThresholds(
                sell_threshold=None,
                buy_threshold=None,
                spread=None,
                trading_recommended=False,
                price_count=0,
                min_price=None,
                max_price=None,
                avg_price=None,
                calculated_at=now,
            )

        # Extract price values
        prices = [slot.get("value", 0.0) for slot in all_prices if "value" in slot]

        if not prices:
            _LOGGER.warning("No valid price values found in data")
            return DynamicThresholds(
                sell_threshold=None,
                buy_threshold=None,
                spread=None,
                trading_recommended=False,
                price_count=0,
                min_price=None,
                max_price=None,
                avg_price=None,
                calculated_at=now,
            )

        # Calculate statistics
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)

        # Calculate dynamic thresholds based on percentiles
        sell_threshold = self.calculate_percentile(prices, self.sell_percentile)
        buy_threshold = self.calculate_percentile(prices, self.buy_percentile)

        # Calculate spread
        spread = sell_threshold - buy_threshold

        # Determine if trading is recommended (spread exceeds minimum)
        trading_recommended = spread >= self.min_spread

        _LOGGER.debug(
            "Dynamic thresholds calculated: sell=%.4f (P%d), buy=%.4f (P%d), spread=%.4f, trading=%s",
            sell_threshold,
            int(self.sell_percentile),
            buy_threshold,
            int(self.buy_percentile),
            spread,
            "recommended" if trading_recommended else "not recommended",
        )

        return DynamicThresholds(
            sell_threshold=sell_threshold,
            buy_threshold=buy_threshold,
            spread=spread,
            trading_recommended=trading_recommended,
            price_count=len(prices),
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            calculated_at=now,
        )

    def get_effective_thresholds(
        self,
        raw_today: list[dict[str, Any]] | None,
        raw_tomorrow: list[dict[str, Any]] | None,
        static_sell_price: float,
        static_buy_price: float,
        use_dynamic: bool = True,
    ) -> tuple[float, float, bool]:
        """Get effective thresholds, falling back to static if dynamic fails.

        Args:
            raw_today: Today's price data
            raw_tomorrow: Tomorrow's price data
            static_sell_price: Static sell price threshold (fallback)
            static_buy_price: Static buy price threshold (fallback)
            use_dynamic: Whether to use dynamic thresholds

        Returns:
            Tuple of (sell_threshold, buy_threshold, is_dynamic)
        """
        if not use_dynamic:
            return static_sell_price, static_buy_price, False

        thresholds = self.calculate_thresholds(raw_today, raw_tomorrow)

        # If dynamic calculation failed, fall back to static
        if thresholds.sell_threshold is None or thresholds.buy_threshold is None:
            _LOGGER.info(
                "Dynamic thresholds unavailable, using static: sell=%.4f, buy=%.4f",
                static_sell_price,
                static_buy_price,
            )
            return static_sell_price, static_buy_price, False

        # If trading is not recommended due to low spread, fall back to static
        if not thresholds.trading_recommended:
            _LOGGER.info(
                "Dynamic spread too low (%.4f < %.4f), using static thresholds",
                thresholds.spread,
                self.min_spread,
            )
            return static_sell_price, static_buy_price, False

        return thresholds.sell_threshold, thresholds.buy_threshold, True


def analyze_price_volatility(prices: list[float]) -> dict[str, float]:
    """Analyze price volatility for trading strategy decisions.

    Args:
        prices: List of price values

    Returns:
        Dictionary with volatility metrics
    """
    if not prices or len(prices) < 2:
        return {
            "std_dev": 0.0,
            "coefficient_of_variation": 0.0,
            "price_range": 0.0,
            "interquartile_range": 0.0,
        }

    n = len(prices)
    mean = sum(prices) / n
    variance = sum((p - mean) ** 2 for p in prices) / n
    std_dev = variance**0.5

    sorted_prices = sorted(prices)
    price_range = sorted_prices[-1] - sorted_prices[0]

    # Calculate quartiles
    q1_idx = int(0.25 * (n - 1))
    q3_idx = int(0.75 * (n - 1))
    q1 = sorted_prices[q1_idx]
    q3 = sorted_prices[q3_idx]
    iqr = q3 - q1

    return {
        "std_dev": std_dev,
        "coefficient_of_variation": std_dev / mean if mean > 0 else 0.0,
        "price_range": price_range,
        "interquartile_range": iqr,
    }
