"""Tests for load forecasting model."""
import tempfile
from pathlib import Path

import numpy as np
import pytest

from custom_components.battery_energy_trading.ai.models.load_forecaster import (
    LoadForecaster,
)


class TestLoadForecaster:
    """Test load forecaster model."""

    @pytest.fixture
    def forecaster(self) -> LoadForecaster:
        """Create load forecaster."""
        return LoadForecaster(n_estimators=10)  # Small for tests

    @pytest.fixture
    def training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Create synthetic training data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 15

        X = np.random.randn(n_samples, n_features)
        # Target is load based on temperature and time
        y = 2000 + 500 * X[:, 0] + np.random.randn(n_samples) * 100
        y = np.clip(y, 500, 10000)

        return X, y

    def test_init(self, forecaster: LoadForecaster) -> None:
        """Test forecaster initialization."""
        assert forecaster.name == "load_forecaster"
        assert forecaster.is_trained is False

    def test_train(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test model training."""
        X, y = training_data
        metrics = forecaster.train(X, y)

        assert forecaster.is_trained is True
        assert "mse" in metrics
        assert "mape" in metrics

    def test_train_single_model(
        self, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test training with single model (no ensemble)."""
        forecaster = LoadForecaster(n_estimators=10, use_ensemble=False)
        X, y = training_data
        metrics = forecaster.train(X, y)

        assert forecaster.is_trained is True
        assert metrics["n_models"] == 1

    def test_predict_load(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test load prediction."""
        X, y = training_data
        forecaster.train(X, y)

        predictions = forecaster.predict(X[:10])
        assert predictions.shape == (10,)
        assert np.all(predictions > 0)  # Load should be positive

    def test_predict_before_train(self, forecaster: LoadForecaster) -> None:
        """Test prediction fails before training."""
        X = np.random.randn(10, 15)
        with pytest.raises(RuntimeError):
            forecaster.predict(X)

    def test_predict_heat_pump_stage(self, forecaster: LoadForecaster) -> None:
        """Test heat pump stage prediction."""
        assert hasattr(forecaster, "predict_heat_pump_stage")

        # Test temperature to stage mapping
        stage = forecaster.predict_heat_pump_stage(-10.0)  # Very cold
        assert stage in [12, 15]  # Should be high stage

        stage = forecaster.predict_heat_pump_stage(20.0)  # Warm
        assert stage == 0  # Heat pump off

    def test_predict_heat_pump_stages_all(
        self, forecaster: LoadForecaster
    ) -> None:
        """Test all heat pump stage thresholds."""
        # Above 15°C: off
        assert forecaster.predict_heat_pump_stage(20.0) == 0
        assert forecaster.predict_heat_pump_stage(16.0) == 0

        # 10-15°C: 3kW
        assert forecaster.predict_heat_pump_stage(12.0) == 3

        # 5-10°C: 6kW
        assert forecaster.predict_heat_pump_stage(7.0) == 6

        # 0-5°C: 9kW
        assert forecaster.predict_heat_pump_stage(2.0) == 9

        # -5-0°C: 12kW
        assert forecaster.predict_heat_pump_stage(-3.0) == 12

        # Below -5°C: 15kW
        assert forecaster.predict_heat_pump_stage(-10.0) == 15

    def test_predict_with_heat_pump(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test combined prediction with heat pump."""
        X, y = training_data
        forecaster.train(X, y)

        temperatures = np.array([-5.0, 0.0, 10.0, 20.0, 30.0])
        base_load, hp_load = forecaster.predict_with_heat_pump(X[:5], temperatures)

        assert base_load.shape == (5,)
        assert hp_load.shape == (5,)
        # Cold temperatures should have higher HP load
        assert hp_load[0] > hp_load[-1]

    def test_save_and_load(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test saving and loading model."""
        X, y = training_data
        forecaster.train(X, y)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            forecaster.save(path)

            new_forecaster = LoadForecaster()
            new_forecaster.load(path)

            assert new_forecaster.is_trained is True
            # Predictions should match
            original_pred = forecaster.predict(X[:5])
            loaded_pred = new_forecaster.predict(X[:5])
            np.testing.assert_array_almost_equal(original_pred, loaded_pred)

    def test_save_untrained_fails(self, forecaster: LoadForecaster) -> None:
        """Test saving untrained model raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError):
                forecaster.save(Path(tmpdir))

    def test_load_missing_file(self, forecaster: LoadForecaster) -> None:
        """Test loading from missing file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                forecaster.load(Path(tmpdir))

    def test_set_feature_names(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test setting feature names."""
        X, y = training_data
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        forecaster.set_feature_names(feature_names)
        forecaster.train(X, y)

        # Feature names should be preserved
        assert forecaster._feature_names == feature_names

    def test_predictions_non_negative(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test predictions are always non-negative."""
        X, y = training_data
        forecaster.train(X, y)

        # Use extreme negative inputs that might push predictions negative
        extreme_X = np.ones((5, 15)) * -100
        predictions = forecaster.predict(extreme_X)

        assert np.all(predictions >= 0)
