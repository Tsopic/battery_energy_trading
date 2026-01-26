"""Tests for feature engineering."""
from datetime import datetime

import numpy as np
import pytest

from custom_components.battery_energy_trading.ai.feature_engineering import (
    FeatureEngineering,
    create_lag_features,
    create_rolling_features,
    create_time_features,
)


class TestFeatureEngineering:
    """Test feature engineering."""

    def test_create_time_features(self) -> None:
        """Test time feature creation."""
        dt = datetime(2025, 6, 15, 14, 30)  # Sunday in June, 14:30
        features = create_time_features(dt)

        assert features["hour"] == 14
        assert features["day_of_week"] == 6  # Sunday
        assert features["month"] == 6
        assert features["is_weekend"] == 1
        assert features["day_of_year"] == 166

    def test_create_time_features_weekday(self) -> None:
        """Test time features on weekday."""
        dt = datetime(2025, 12, 2, 9, 0)  # Tuesday
        features = create_time_features(dt)

        assert features["is_weekend"] == 0
        assert features["day_of_week"] == 1  # Tuesday

    def test_create_time_features_cyclical(self) -> None:
        """Test cyclical time features are in valid range."""
        dt = datetime(2025, 6, 15, 12, 0)
        features = create_time_features(dt)

        # Sin/cos should be between -1 and 1
        assert -1 <= features["hour_sin"] <= 1
        assert -1 <= features["hour_cos"] <= 1
        assert -1 <= features["month_sin"] <= 1
        assert -1 <= features["month_cos"] <= 1

    def test_create_lag_features(self) -> None:
        """Test lag feature creation."""
        values = list(range(200))  # 0, 1, 2, ..., 199
        lags = [1, 24, 168]  # 1 hour, 1 day, 1 week

        features = create_lag_features(values, lags, current_idx=199)

        assert features["lag_1"] == 198
        assert features["lag_24"] == 175
        assert features["lag_168"] == 31

    def test_create_lag_features_insufficient_data(self) -> None:
        """Test lag features with insufficient history."""
        values = [1, 2, 3, 4, 5]
        lags = [1, 24]  # 24 is more than available

        features = create_lag_features(values, lags, current_idx=4)

        assert features["lag_1"] == 4
        assert features["lag_24"] is None  # Not enough data

    @pytest.fixture
    def feature_eng(self) -> FeatureEngineering:
        """Create feature engineering instance."""
        return FeatureEngineering()

    def test_create_rolling_features(self) -> None:
        """Test rolling average features."""
        values = [10.0] * 30  # Constant values
        features = create_rolling_features(values, [4, 24], current_idx=29)

        assert features["rolling_mean_4"] == 10.0
        assert features["rolling_std_4"] == 0.0
        assert features["rolling_mean_24"] == 10.0

    def test_create_rolling_features_varying(self) -> None:
        """Test rolling features with varying values."""
        values = list(range(30))  # 0, 1, 2, ..., 29
        features = create_rolling_features(values, [4], current_idx=29)

        # Rolling mean of last 4 values: 26, 27, 28, 29 = 27.5
        assert features["rolling_mean_4"] == np.mean([26, 27, 28, 29])
        assert features["rolling_std_4"] > 0  # Non-zero std

    def test_create_load_features(self, feature_eng: FeatureEngineering) -> None:
        """Test load feature creation."""
        dt = datetime(2025, 1, 15, 18, 0)  # Winter evening
        load_history = [2000.0] * 200
        heat_pump_history = {
            "3kw": [0] * 200,
            "6kw": [1] * 200,  # 6kW stage active
        }

        features = feature_eng.create_load_features(
            timestamp=dt,
            load_history=load_history,
            temperature=-5.0,  # Cold
            heat_pump_history=heat_pump_history,
            current_idx=199,
        )

        assert features["temperature"] == -5.0
        assert features["temp_below_0"] == 1
        assert features["temp_below_5"] == 1
        assert features["hp_6kw_active"] == 1

    def test_create_load_features_warm(self, feature_eng: FeatureEngineering) -> None:
        """Test load features with warm temperature."""
        dt = datetime(2025, 7, 15, 14, 0)  # Summer afternoon
        load_history = [1500.0] * 200
        heat_pump_history = {}

        features = feature_eng.create_load_features(
            timestamp=dt,
            load_history=load_history,
            temperature=25.0,  # Warm
            heat_pump_history=heat_pump_history,
            current_idx=199,
        )

        assert features["temp_below_0"] == 0
        assert features["temp_below_5"] == 0
        assert features["temp_below_10"] == 0
        assert features["temp_below_15"] == 0

    def test_create_decision_features_price_primary(
        self, feature_eng: FeatureEngineering
    ) -> None:
        """Test decision features with price as primary."""
        dt = datetime(2025, 12, 2, 17, 0)
        # Create prices where 0.40 is clearly in top 20%
        prices = [0.05, 0.10, 0.15, 0.20, 0.40] * 5  # 25 prices

        features = feature_eng.create_decision_features(
            timestamp=dt,
            battery_soc=60.0,
            current_price=0.40,  # Highest price
            prices_24h=prices[:24],
            solar_forecast=0.5,
            load_forecast=2.0,
        )

        assert features["current_price"] == 0.40
        assert features["price_level"] == 4  # Very high (top 20%) - 0.40 is max
        assert features["battery_level"] == 3  # 60% is in 60-80 range = level 3
        assert features["net_forecast"] == -1.5  # Solar - load

    def test_create_decision_features_low_soc(
        self, feature_eng: FeatureEngineering
    ) -> None:
        """Test decision features with low battery."""
        dt = datetime(2025, 12, 2, 3, 0)  # Night
        prices = [0.05] * 24  # Constant low prices

        features = feature_eng.create_decision_features(
            timestamp=dt,
            battery_soc=15.0,  # Low
            current_price=0.05,
            prices_24h=prices,
            solar_forecast=0.0,
            load_forecast=0.5,
        )

        assert features["battery_level"] == 0  # <20% = level 0
        assert features["price_percentile"] == 0.0  # All same price

    def test_create_solar_features(self, feature_eng: FeatureEngineering) -> None:
        """Test solar feature creation."""
        dt = datetime(2025, 6, 15, 12, 0)  # Midday in summer
        solar_history = [1000.0] * 200  # 1kW constant
        forecast_history = [800.0] * 200  # Under-forecast

        features = feature_eng.create_solar_features(
            timestamp=dt,
            solar_history=solar_history,
            forecast_solar=900.0,
            forecast_history=forecast_history,
            weather_data={"cloud_cover": 20, "temperature": 25},
            current_idx=199,
        )

        assert features["forecast_solar"] == 900.0
        assert features["cloud_cover"] == 20
        assert features["temperature"] == 25
        # Forecast error mean should be positive (actual > forecast)
        assert features["forecast_error_mean"] == 200.0  # 1000 - 800

    def test_discretize_soc(self, feature_eng: FeatureEngineering) -> None:
        """Test battery SOC discretization."""
        assert feature_eng._discretize_soc(10) == 0  # <20
        assert feature_eng._discretize_soc(30) == 1  # 20-40
        assert feature_eng._discretize_soc(50) == 2  # 40-60
        assert feature_eng._discretize_soc(70) == 3  # 60-80
        assert feature_eng._discretize_soc(90) == 4  # >80
