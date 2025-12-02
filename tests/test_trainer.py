"""Tests for training orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.battery_energy_trading.ai.config import AIConfig
from custom_components.battery_energy_trading.ai.training.trainer import AITrainer


class TestAITrainer:
    """Test AI training orchestrator."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant."""
        hass = MagicMock()
        hass.config.path = MagicMock(return_value="/tmp/hass")
        hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        return hass

    @pytest.fixture
    def config(self) -> AIConfig:
        """Create test config."""
        return AIConfig()

    @pytest.fixture
    def trainer(self, mock_hass: MagicMock, config: AIConfig) -> AITrainer:
        """Create trainer instance."""
        return AITrainer(mock_hass, config)

    def test_init(self, trainer: AITrainer) -> None:
        """Test trainer initialization."""
        assert trainer.hass is not None
        assert trainer.config is not None
        assert trainer.is_training is False
        assert trainer.solar_predictor is None
        assert trainer.load_forecaster is None
        assert trainer.decision_optimizer is None

    def test_get_model_path(self, trainer: AITrainer) -> None:
        """Test model path generation."""
        # The path method is called with the subdirectory path
        # and returns the full path. We just verify it's a Path.
        path = trainer.get_model_path()
        assert isinstance(path, Path)
        # The path argument passed to hass.config.path contains the subdir
        trainer.hass.config.path.assert_called_once()
        call_args = trainer.hass.config.path.call_args[0][0]
        assert "battery_energy_trading" in call_args
        assert "models" in call_args

    @pytest.mark.asyncio
    async def test_train_all_models_insufficient_data(self, trainer: AITrainer) -> None:
        """Test training fails with insufficient data."""
        with patch.object(
            trainer.data_extractor,
            "extract_training_data",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await trainer.train_all_models()
            assert result["success"] is False
            assert "insufficient" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_train_all_models_already_training(self, trainer: AITrainer) -> None:
        """Test training returns error if already in progress."""
        trainer._is_training = True
        result = await trainer.train_all_models()
        assert result["success"] is False
        assert "already in progress" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_train_all_models_success(self, trainer: AITrainer) -> None:
        """Test successful training flow."""
        # Create mock data with sufficient samples
        mock_data = {
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000 + h * 100} for h in range(24)
            ]
            * 10,  # 240 samples
            trainer.config.solar_forecast_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 900 + h * 90} for h in range(24)
            ]
            * 10,
            trainer.config.load_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 2000 + h * 50} for h in range(24)
            ]
            * 10,
            trainer.config.outdoor_temp_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 15.0} for h in range(24)
            ]
            * 10,
            trainer.config.battery_level_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 50.0} for h in range(24)
            ]
            * 10,
            trainer.config.nordpool_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 0.10 + h * 0.01} for h in range(24)
            ]
            * 10,
        }

        with (
            patch.object(
                trainer.data_extractor,
                "extract_training_data",
                new_callable=AsyncMock,
                return_value=mock_data,
            ),
            patch.object(
                trainer.data_extractor,
                "has_sufficient_data",
                return_value=True,
            ),
        ):
            result = await trainer.train_all_models()

            assert result["success"] is True
            assert "models" in result
            assert "duration_seconds" in result
            assert trainer.is_training is False

    @pytest.mark.asyncio
    async def test_train_solar_model(self, trainer: AITrainer) -> None:
        """Test solar model training."""
        mock_data = {
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000 + h * 100} for h in range(24)
            ]
            * 10,
            trainer.config.solar_forecast_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 900 + h * 90} for h in range(24)
            ]
            * 10,
        }

        result = await trainer._train_solar_model(mock_data)
        assert result["trained"] is True
        assert "metrics" in result
        assert trainer.solar_predictor is not None
        assert trainer.solar_predictor.is_trained is True

    @pytest.mark.asyncio
    async def test_train_solar_model_insufficient_data(self, trainer: AITrainer) -> None:
        """Test solar model training with insufficient data."""
        mock_data = {
            trainer.config.solar_power_entity: [{"start": "2024-01-01T12:00:00", "mean": 1000}],
            trainer.config.solar_forecast_entity: [{"start": "2024-01-01T12:00:00", "mean": 900}],
        }

        result = await trainer._train_solar_model(mock_data)
        assert result["trained"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_train_load_model(self, trainer: AITrainer) -> None:
        """Test load model training."""
        mock_data = {
            trainer.config.load_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 2000 + h * 50} for h in range(24)
            ]
            * 10,
            trainer.config.outdoor_temp_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 15.0} for h in range(24)
            ]
            * 10,
        }

        result = await trainer._train_load_model(mock_data)
        assert result["trained"] is True
        assert "metrics" in result
        assert trainer.load_forecaster is not None
        assert trainer.load_forecaster.is_trained is True

    @pytest.mark.asyncio
    async def test_train_load_model_insufficient_data(self, trainer: AITrainer) -> None:
        """Test load model training with insufficient data."""
        mock_data = {
            trainer.config.load_power_entity: [{"start": "2024-01-01T12:00:00", "mean": 2000}],
        }

        result = await trainer._train_load_model(mock_data)
        assert result["trained"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_train_decision_model(self, trainer: AITrainer) -> None:
        """Test decision model training."""
        mock_data = {
            trainer.config.battery_level_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 50.0 + h} for h in range(24)
            ]
            * 10,
            trainer.config.nordpool_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 0.10 + h * 0.01} for h in range(24)
            ]
            * 10,
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000} for h in range(24)
            ]
            * 10,
            trainer.config.load_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 2000} for h in range(24)
            ]
            * 10,
        }

        result = await trainer._train_decision_model(mock_data)
        assert result["trained"] is True
        assert "metrics" in result
        assert trainer.decision_optimizer is not None

    @pytest.mark.asyncio
    async def test_train_decision_model_insufficient_data(self, trainer: AITrainer) -> None:
        """Test decision model training with insufficient data."""
        mock_data = {
            trainer.config.battery_level_entity: [{"start": "2024-01-01T12:00:00", "mean": 50.0}],
        }

        result = await trainer._train_decision_model(mock_data)
        assert result["trained"] is False
        assert "error" in result

    def test_prepare_solar_data(self, trainer: AITrainer) -> None:
        """Test solar data preparation."""
        mock_data = {
            trainer.config.solar_power_entity: [
                {"start": f"2024-06-15T{h:02d}:00:00", "mean": 1000 + h * 100} for h in range(24)
            ],
            trainer.config.solar_forecast_entity: [
                {"start": f"2024-06-15T{h:02d}:00:00", "mean": 900 + h * 90} for h in range(24)
            ],
        }

        X, y = trainer._prepare_solar_data(mock_data)
        assert len(X) > 0
        assert len(y) > 0
        assert X.shape[0] == y.shape[0]

    def test_prepare_solar_data_missing_entities(self, trainer: AITrainer) -> None:
        """Test solar data preparation with missing entities."""
        mock_data = {}

        X, y = trainer._prepare_solar_data(mock_data)
        assert len(X) == 0
        assert len(y) == 0

    def test_prepare_load_data(self, trainer: AITrainer) -> None:
        """Test load data preparation."""
        mock_data = {
            trainer.config.load_power_entity: [
                {"start": f"2024-06-15T{h:02d}:00:00", "mean": 2000 + h * 50} for h in range(24)
            ],
            trainer.config.outdoor_temp_entity: [
                {"start": f"2024-06-15T{h:02d}:00:00", "mean": 15.0 + h * 0.5} for h in range(24)
            ],
        }

        X, y = trainer._prepare_load_data(mock_data)
        assert len(X) == 24
        assert len(y) == 24
        assert X.shape[1] == 5  # hour, day_of_week, month, is_weekend, temp

    def test_prepare_load_data_missing_temp(self, trainer: AITrainer) -> None:
        """Test load data preparation without temperature."""
        mock_data = {
            trainer.config.load_power_entity: [
                {"start": f"2024-06-15T{h:02d}:00:00", "mean": 2000 + h * 50} for h in range(24)
            ],
        }

        X, y = trainer._prepare_load_data(mock_data)
        assert len(X) == 24
        # Temperature defaults to 15

    def test_prepare_decision_experiences(self, trainer: AITrainer) -> None:
        """Test decision experience preparation."""
        mock_data = {
            trainer.config.battery_level_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 50.0 + h} for h in range(24)
            ],
            trainer.config.nordpool_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 0.10 + h * 0.01} for h in range(24)
            ],
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000} for h in range(24)
            ],
            trainer.config.load_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 2000} for h in range(24)
            ],
        }

        experiences = trainer._prepare_decision_experiences(mock_data)
        # Should return list of experiences (can be empty if not enough data)
        assert isinstance(experiences, list)

    @pytest.mark.asyncio
    async def test_save_models(self, trainer: AITrainer) -> None:
        """Test model saving."""
        # Train models first
        mock_data = {
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000 + h * 100} for h in range(24)
            ]
            * 10,
            trainer.config.solar_forecast_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 900 + h * 90} for h in range(24)
            ]
            * 10,
        }

        await trainer._train_solar_model(mock_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            trainer.hass.config.path = MagicMock(return_value=tmpdir)

            # Should not raise
            await trainer._save_models()

    @pytest.mark.asyncio
    async def test_load_models_no_models(self, trainer: AITrainer) -> None:
        """Test loading models when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer.hass.config.path = MagicMock(return_value=tmpdir)

            result = await trainer.load_models()
            assert result is False

    @pytest.mark.asyncio
    async def test_load_models_success(self, trainer: AITrainer) -> None:
        """Test successful model loading."""
        # First train and save all models
        mock_data = {
            trainer.config.solar_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 1000 + h * 100} for h in range(24)
            ]
            * 10,
            trainer.config.solar_forecast_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 900 + h * 90} for h in range(24)
            ]
            * 10,
            trainer.config.load_power_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 2000 + h * 50} for h in range(24)
            ]
            * 10,
            trainer.config.outdoor_temp_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 15.0} for h in range(24)
            ]
            * 10,
            trainer.config.battery_level_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 50.0 + h} for h in range(24)
            ]
            * 10,
            trainer.config.nordpool_entity: [
                {"start": f"2024-01-01T{h:02d}:00:00", "mean": 0.10 + h * 0.01} for h in range(24)
            ]
            * 10,
        }

        await trainer._train_solar_model(mock_data)
        await trainer._train_load_model(mock_data)
        await trainer._train_decision_model(mock_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            trainer.hass.config.path = MagicMock(return_value=tmpdir)

            await trainer._save_models()

            # Clear models
            trainer.solar_predictor = None
            trainer.load_forecaster = None
            trainer.decision_optimizer = None

            # Load them back
            result = await trainer.load_models()
            assert result is True
            assert trainer.solar_predictor is not None
            assert trainer.load_forecaster is not None
            assert trainer.decision_optimizer is not None

    def test_last_training_property(self, trainer: AITrainer) -> None:
        """Test last_training property."""
        assert trainer.last_training is None

    def test_training_metrics_property(self, trainer: AITrainer) -> None:
        """Test training_metrics property."""
        assert trainer.training_metrics == {}
