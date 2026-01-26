"""Tests for solar prediction model."""
import tempfile
from pathlib import Path

import numpy as np
import pytest

from custom_components.battery_energy_trading.ai.models.solar_predictor import (
    SolarPredictor,
)


class TestSolarPredictor:
    """Test solar predictor model."""

    @pytest.fixture
    def predictor(self) -> SolarPredictor:
        """Create solar predictor."""
        return SolarPredictor(n_estimators=10, max_depth=3)  # Small for tests

    @pytest.fixture
    def training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Create synthetic training data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 10

        X = np.random.randn(n_samples, n_features)
        # Target is correction factor based on some features
        y = 0.9 + 0.2 * X[:, 0] + np.random.randn(n_samples) * 0.05
        y = np.clip(y, 0.5, 1.5)  # Correction factors between 0.5 and 1.5

        return X, y

    def test_init(self, predictor: SolarPredictor) -> None:
        """Test predictor initialization."""
        assert predictor.name == "solar_predictor"
        assert predictor.is_trained is False

    def test_train(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test model training."""
        X, y = training_data
        metrics = predictor.train(X, y)

        assert predictor.is_trained is True
        assert "mse" in metrics
        assert "mae" in metrics
        assert metrics["mse"] >= 0

    def test_predict_before_train(self, predictor: SolarPredictor) -> None:
        """Test prediction fails before training."""
        X = np.random.randn(10, 10)
        with pytest.raises(RuntimeError):
            predictor.predict(X)

    def test_predict_after_train(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test prediction after training."""
        X, y = training_data
        predictor.train(X, y)

        predictions = predictor.predict(X[:10])
        assert predictions.shape == (10,)
        assert np.all(predictions > 0)  # Correction factors should be positive

    def test_predictions_clipped(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test predictions are clipped to valid range."""
        X, y = training_data
        predictor.train(X, y)

        # Use extreme inputs
        extreme_X = np.ones((5, 10)) * 100
        predictions = predictor.predict(extreme_X)

        # Should be clipped between 0.5 and 1.5
        assert np.all(predictions >= 0.5)
        assert np.all(predictions <= 1.5)

    def test_save_and_load(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test saving and loading model."""
        X, y = training_data
        predictor.train(X, y)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            predictor.save(path)

            new_predictor = SolarPredictor()
            new_predictor.load(path)

            assert new_predictor.is_trained is True
            # Predictions should match
            original_pred = predictor.predict(X[:5])
            loaded_pred = new_predictor.predict(X[:5])
            np.testing.assert_array_almost_equal(original_pred, loaded_pred)

    def test_save_untrained_fails(self, predictor: SolarPredictor) -> None:
        """Test saving untrained model raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError):
                predictor.save(Path(tmpdir))

    def test_load_missing_file(self, predictor: SolarPredictor) -> None:
        """Test loading from missing file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                predictor.load(Path(tmpdir))

    def test_correct_forecast(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test applying correction to forecast."""
        X, y = training_data
        predictor.train(X, y)

        forecast_value = 5.0  # 5 kWh
        features = X[0]

        corrected, factor = predictor.correct_forecast(forecast_value, features)

        assert 0.5 <= factor <= 1.5
        assert corrected == forecast_value * factor

    def test_correct_forecast_untrained(self, predictor: SolarPredictor) -> None:
        """Test correction returns original when not trained."""
        features = np.random.randn(10)
        corrected, factor = predictor.correct_forecast(5.0, features)

        assert corrected == 5.0
        assert factor == 1.0

    def test_get_feature_importance(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test getting feature importance."""
        X, y = training_data
        predictor.train(X, y)

        importance = predictor.get_feature_importance()
        assert importance is not None
        assert len(importance) == X.shape[1]
        assert sum(importance.values()) > 0

    def test_set_feature_names(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test setting feature names."""
        X, y = training_data
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        predictor.set_feature_names(feature_names)
        predictor.train(X, y)

        importance = predictor.get_feature_importance()
        assert importance is not None
        assert list(importance.keys()) == feature_names
