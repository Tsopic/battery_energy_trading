"""Feature engineering for AI models."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np


_LOGGER = logging.getLogger(__name__)


def create_time_features(dt: datetime) -> dict[str, int | float]:
    """Create time-based features from datetime.

    Args:
        dt: Datetime to extract features from

    Returns:
        Dictionary of time features
    """
    return {
        "hour": dt.hour,
        "day_of_week": dt.weekday(),
        "day_of_year": dt.timetuple().tm_yday,
        "month": dt.month,
        "is_weekend": 1 if dt.weekday() >= 5 else 0,
        "hour_sin": np.sin(2 * np.pi * dt.hour / 24),
        "hour_cos": np.cos(2 * np.pi * dt.hour / 24),
        "month_sin": np.sin(2 * np.pi * dt.month / 12),
        "month_cos": np.cos(2 * np.pi * dt.month / 12),
    }


def create_lag_features(
    values: list[float],
    lags: list[int],
    current_idx: int,
) -> dict[str, float | None]:
    """Create lag features from time series.

    Args:
        values: List of historical values
        lags: List of lag periods (e.g., [1, 24, 168] for 1h, 1d, 1w)
        current_idx: Current position in values list

    Returns:
        Dictionary of lag features
    """
    features: dict[str, float | None] = {}
    for lag in lags:
        idx = current_idx - lag
        if 0 <= idx < len(values):
            features[f"lag_{lag}"] = values[idx]
        else:
            features[f"lag_{lag}"] = None
    return features


def create_rolling_features(
    values: list[float],
    windows: list[int],
    current_idx: int,
) -> dict[str, float | None]:
    """Create rolling average features.

    Args:
        values: List of historical values
        windows: List of window sizes (e.g., [4, 24] for 4h, 24h averages)
        current_idx: Current position in values list

    Returns:
        Dictionary of rolling features
    """
    features: dict[str, float | None] = {}
    for window in windows:
        start_idx = max(0, current_idx - window + 1)
        if start_idx < current_idx:
            window_values = values[start_idx : current_idx + 1]
            features[f"rolling_mean_{window}"] = float(np.mean(window_values))
            features[f"rolling_std_{window}"] = float(np.std(window_values))
        else:
            features[f"rolling_mean_{window}"] = None
            features[f"rolling_std_{window}"] = None
    return features


class FeatureEngineering:
    """Feature engineering for AI training and inference."""

    def __init__(self) -> None:
        """Initialize feature engineering."""
        self.lags = [1, 24, 168]  # 1h, 1d, 1w
        self.windows = [4, 24, 168]  # 4h, 1d, 1w rolling averages

    def create_solar_features(
        self,
        timestamp: datetime,
        solar_history: list[float],
        forecast_solar: float,
        forecast_history: list[float],
        weather_data: dict[str, float],
        current_idx: int,
    ) -> dict[str, Any]:
        """Create features for solar prediction model.

        Args:
            timestamp: Current timestamp
            solar_history: Historical solar production values
            forecast_solar: Forecast.Solar prediction
            forecast_history: Historical forecast values
            weather_data: Weather features (cloud_cover, temperature)
            current_idx: Current index in history arrays

        Returns:
            Feature dictionary for solar model
        """
        features: dict[str, Any] = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Forecast.Solar as primary input
        features["forecast_solar"] = forecast_solar

        # Historical forecast error (actual - forecast)
        if len(solar_history) > 0 and len(forecast_history) > 0:
            min_len = min(len(solar_history), len(forecast_history))
            errors = [
                solar_history[i] - forecast_history[i]
                for i in range(min_len)
                if solar_history[i] is not None and forecast_history[i] is not None
            ]
            if errors:
                features["forecast_error_mean"] = float(np.mean(errors[-168:]))
                features["forecast_error_std"] = float(np.std(errors[-168:]))
            else:
                features["forecast_error_mean"] = 0.0
                features["forecast_error_std"] = 0.0
        else:
            features["forecast_error_mean"] = 0.0
            features["forecast_error_std"] = 0.0

        # Weather features
        features["cloud_cover"] = weather_data.get("cloud_cover", 0)
        features["temperature"] = weather_data.get("temperature", 20)

        # Lag features from actual solar
        if solar_history:
            lag_features = create_lag_features(solar_history, self.lags, current_idx)
            features.update({f"solar_{k}": v for k, v in lag_features.items()})

        return features

    def create_load_features(
        self,
        timestamp: datetime,
        load_history: list[float],
        temperature: float,
        heat_pump_history: dict[str, list[int]],
        current_idx: int,
    ) -> dict[str, Any]:
        """Create features for load prediction model.

        Args:
            timestamp: Current timestamp
            load_history: Historical load values
            temperature: Current outdoor temperature
            heat_pump_history: Historical heat pump stage states
            current_idx: Current index in history arrays

        Returns:
            Feature dictionary for load model
        """
        features: dict[str, Any] = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Temperature (key predictor for heat pump)
        features["temperature"] = temperature
        features["temp_squared"] = temperature**2  # Non-linear relationship

        # Temperature bands for heat pump prediction
        features["temp_below_0"] = 1 if temperature < 0 else 0
        features["temp_below_5"] = 1 if temperature < 5 else 0
        features["temp_below_10"] = 1 if temperature < 10 else 0
        features["temp_below_15"] = 1 if temperature < 15 else 0

        # Historical load patterns
        if load_history:
            features.update(create_lag_features(load_history, self.lags, current_idx))
            features.update(create_rolling_features(load_history, self.windows, current_idx))

        # Heat pump stage indicators
        for stage, history in heat_pump_history.items():
            if history and current_idx < len(history):
                features[f"hp_{stage}_active"] = history[current_idx]
            else:
                features[f"hp_{stage}_active"] = 0

        return features

    def create_decision_features(
        self,
        timestamp: datetime,
        battery_soc: float,
        current_price: float,
        prices_24h: list[float],
        solar_forecast: float,
        load_forecast: float,
    ) -> dict[str, Any]:
        """Create features for Q-learning decision model.

        Nord Pool prices are PRIMARY - included prominently.

        Args:
            timestamp: Current timestamp
            battery_soc: Battery state of charge (0-100)
            current_price: Current Nord Pool price
            prices_24h: Next 24 hours of prices
            solar_forecast: Predicted solar for next hour
            load_forecast: Predicted load for next hour

        Returns:
            Feature dictionary for decision model
        """
        features: dict[str, Any] = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Battery state (discretized)
        features["battery_soc"] = battery_soc
        features["battery_level"] = self._discretize_soc(battery_soc)

        # PRICES ARE PRIMARY
        features["current_price"] = current_price
        features["price_level"] = self._discretize_price(current_price, prices_24h)

        # Price statistics
        if prices_24h:
            features["price_mean_24h"] = float(np.mean(prices_24h))
            features["price_std_24h"] = float(np.std(prices_24h))
            features["price_min_24h"] = float(np.min(prices_24h))
            features["price_max_24h"] = float(np.max(prices_24h))
            features["price_percentile"] = self._price_percentile(current_price, prices_24h)

            # Price trend (next 6 hours vs current)
            if len(prices_24h) >= 6:
                features["price_trend_6h"] = float(np.mean(prices_24h[:6]) - current_price)
            else:
                features["price_trend_6h"] = 0.0
        else:
            features["price_mean_24h"] = current_price
            features["price_std_24h"] = 0.0
            features["price_min_24h"] = current_price
            features["price_max_24h"] = current_price
            features["price_percentile"] = 50.0
            features["price_trend_6h"] = 0.0

        # Solar and load forecasts
        features["solar_forecast"] = solar_forecast
        features["load_forecast"] = load_forecast
        features["net_forecast"] = solar_forecast - load_forecast

        return features

    def _discretize_soc(self, soc: float) -> int:
        """Discretize battery SOC into 5 levels."""
        if soc < 20:
            return 0
        if soc < 40:
            return 1
        if soc < 60:
            return 2
        if soc < 80:
            return 3
        return 4

    def _discretize_price(self, price: float, prices_24h: list[float]) -> int:
        """Discretize price into 5 levels based on distribution."""
        if not prices_24h:
            return 2  # Medium

        percentile = self._price_percentile(price, prices_24h)
        if percentile < 20:
            return 0  # Very low
        if percentile < 40:
            return 1  # Low
        if percentile < 60:
            return 2  # Medium
        if percentile < 80:
            return 3  # High
        return 4  # Very high

    def _price_percentile(self, price: float, prices: list[float]) -> float:
        """Calculate percentile of price in distribution."""
        if not prices:
            return 50.0
        below = sum(1 for p in prices if p < price)
        return (below / len(prices)) * 100
