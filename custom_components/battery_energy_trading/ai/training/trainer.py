"""Training orchestrator for AI models."""

from __future__ import annotations

import gc
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..config import AIConfig
from ..data_extractor import DataExtractor
from ..feature_engineering import create_time_features
from ..models.decision_optimizer import Action, DecisionOptimizer
from ..models.load_forecaster import LoadForecaster
from ..models.solar_predictor import SolarPredictor


_LOGGER = logging.getLogger(__name__)


class AITrainer:
    """Orchestrates training of all AI models.

    Handles sequential training to stay within Raspberry Pi 4 memory limits.
    Uses garbage collection between model training steps.
    """

    def __init__(self, hass: HomeAssistant, config: AIConfig) -> None:
        """Initialize trainer.

        Args:
            hass: Home Assistant instance
            config: AI configuration
        """
        self.hass = hass
        self.config = config
        self.data_extractor = DataExtractor(hass, config)

        # Models
        self.solar_predictor: SolarPredictor | None = None
        self.load_forecaster: LoadForecaster | None = None
        self.decision_optimizer: DecisionOptimizer | None = None

        self._is_training = False
        self._last_training: datetime | None = None
        self._training_metrics: dict[str, Any] = {}

    @property
    def is_training(self) -> bool:
        """Check if training is in progress."""
        return self._is_training

    @property
    def last_training(self) -> datetime | None:
        """Get last training timestamp."""
        return self._last_training

    @property
    def training_metrics(self) -> dict[str, Any]:
        """Get training metrics from last run."""
        return self._training_metrics

    def get_model_path(self) -> Path:
        """Get path for model storage."""
        return Path(self.hass.config.path("custom_components/battery_energy_trading/models"))

    async def train_all_models(self) -> dict[str, Any]:
        """Train all AI models sequentially.

        Returns:
            Training result with metrics
        """
        if self._is_training:
            return {"success": False, "error": "Training already in progress"}

        self._is_training = True
        start_time = datetime.now()
        results: dict[str, Any] = {"success": True, "models": {}}

        try:
            _LOGGER.info("Starting AI model training")

            # Step 1: Extract data
            _LOGGER.info("Extracting training data...")
            data = await self.data_extractor.extract_training_data()

            if not self.data_extractor.has_sufficient_data(data):
                return {
                    "success": False,
                    "error": "Insufficient historical data for training",
                }

            # Step 2: Train solar predictor
            _LOGGER.info("Training solar predictor...")
            solar_result = await self._train_solar_model(data)
            results["models"]["solar"] = solar_result
            gc.collect()  # Free memory

            # Step 3: Train load forecaster
            _LOGGER.info("Training load forecaster...")
            load_result = await self._train_load_model(data)
            results["models"]["load"] = load_result
            gc.collect()

            # Step 4: Update Q-learning agent
            _LOGGER.info("Updating decision optimizer...")
            decision_result = await self._train_decision_model(data)
            results["models"]["decision"] = decision_result
            gc.collect()

            # Step 5: Save models
            await self._save_models()

            self._last_training = datetime.now()
            self._training_metrics = results.get("models", {})
            results["duration_seconds"] = (datetime.now() - start_time).total_seconds()

            _LOGGER.info(
                "Training completed in %.1f seconds",
                results["duration_seconds"],
            )

        except Exception as err:
            _LOGGER.exception("Training failed: %s", err)
            results["success"] = False
            results["error"] = str(err)

        finally:
            self._is_training = False

        return results

    async def _train_solar_model(self, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Train solar predictor model."""
        # Prepare features and targets
        X, y = self._prepare_solar_data(data)

        if len(X) < 100:
            return {"trained": False, "error": "Not enough solar data"}

        self.solar_predictor = SolarPredictor(
            n_estimators=self.config.solar_model_estimators,
            max_depth=self.config.solar_model_max_depth,
        )

        # Run training in executor to avoid blocking
        metrics = await self.hass.async_add_executor_job(self.solar_predictor.train, X, y)

        return {"trained": True, "metrics": metrics}

    async def _train_load_model(self, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Train load forecaster model."""
        X, y = self._prepare_load_data(data)

        if len(X) < 100:
            return {"trained": False, "error": "Not enough load data"}

        self.load_forecaster = LoadForecaster(
            n_estimators=self.config.load_model_estimators,
        )

        metrics = await self.hass.async_add_executor_job(self.load_forecaster.train, X, y)

        return {"trained": True, "metrics": metrics}

    async def _train_decision_model(self, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Train/update Q-learning decision optimizer."""
        experiences = self._prepare_decision_experiences(data)

        if len(experiences) < 50:
            return {"trained": False, "error": "Not enough decision data"}

        if self.decision_optimizer is None:
            self.decision_optimizer = DecisionOptimizer(
                learning_rate=self.config.q_learning_rate,
                discount_factor=self.config.q_discount_factor,
                exploration_rate=self.config.q_exploration_rate,
            )

        metrics = self.decision_optimizer.train_from_experience(experiences)
        return {"trained": True, "metrics": metrics}

    def _prepare_solar_data(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare solar training data.

        Returns:
            Tuple of (features, targets)
        """
        solar_key = self.config.solar_power_entity
        forecast_key = self.config.solar_forecast_entity

        if solar_key not in data or forecast_key not in data:
            return np.array([]), np.array([])

        solar_data = data[solar_key]
        forecast_data = data[forecast_key]

        features = []
        targets = []

        for i, record in enumerate(solar_data):
            if i >= len(forecast_data):
                break

            actual = record.get("mean", 0) or 0
            forecast = forecast_data[i].get("mean", 0) or 0

            if forecast > 0:
                # Target is correction factor
                correction = actual / forecast
                correction = np.clip(correction, 0.5, 1.5)

                # Create features
                dt = datetime.fromisoformat(record["start"])
                time_features = create_time_features(dt)
                feature_vec = [
                    forecast,
                    time_features["hour"],
                    time_features["month"],
                    time_features["is_weekend"],
                ]
                features.append(feature_vec)
                targets.append(correction)

        return np.array(features), np.array(targets)

    def _prepare_load_data(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare load training data."""
        load_key = self.config.load_power_entity
        temp_key = self.config.outdoor_temp_entity

        if load_key not in data:
            return np.array([]), np.array([])

        load_data = data[load_key]
        temp_data = data.get(temp_key, [])

        features = []
        targets = []

        for i, record in enumerate(load_data):
            load = record.get("mean", 0) or 0
            temp = temp_data[i].get("mean", 15) if i < len(temp_data) else 15

            dt = datetime.fromisoformat(record["start"])
            time_features = create_time_features(dt)

            feature_vec = [
                time_features["hour"],
                time_features["day_of_week"],
                time_features["month"],
                time_features["is_weekend"],
                temp,
            ]
            features.append(feature_vec)
            targets.append(load)

        return np.array(features), np.array(targets)

    def _prepare_decision_experiences(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[tuple[tuple, Action, float, tuple]]:
        """Prepare experiences for Q-learning from historical data.

        Reconstructs state-action-reward sequences from historical data.
        Uses price changes to infer optimal actions.
        """
        battery_key = self.config.battery_level_entity
        price_key = self.config.nordpool_entity
        solar_key = self.config.solar_power_entity
        load_key = self.config.load_power_entity

        # Check required data
        if battery_key not in data or price_key not in data:
            return []

        battery_data = data[battery_key]
        price_data = data[price_key]
        solar_data = data.get(solar_key, [])
        load_data = data.get(load_key, [])

        experiences: list[tuple[tuple, Action, float, tuple]] = []

        # Need at least 2 consecutive points to create experiences
        min_len = min(len(battery_data), len(price_data))
        if min_len < 2:
            return []

        for i in range(min_len - 1):
            try:
                # Current state
                battery_level = battery_data[i].get("mean", 50) or 50
                current_price = price_data[i].get("mean", 0.10) or 0.10
                solar = solar_data[i].get("mean", 0) if i < len(solar_data) else 0
                load = load_data[i].get("mean", 0) if i < len(load_data) else 0

                # Next state
                next_battery = battery_data[i + 1].get("mean", 50) or 50
                next_price = price_data[i + 1].get("mean", 0.10) or 0.10

                # Discretize states
                battery_discrete = self._discretize_battery(battery_level)
                price_discrete = self._discretize_price(current_price, price_data)
                solar_discrete = self._discretize_solar(solar)
                load_discrete = self._discretize_load(load)

                # Get hour from timestamp
                dt = datetime.fromisoformat(battery_data[i]["start"])
                hour_period = dt.hour // 4  # 0-5 for 6 periods

                state = (
                    battery_discrete,
                    price_discrete,
                    solar_discrete,
                    load_discrete,
                    hour_period,
                )

                # Infer action from battery change
                battery_change = next_battery - battery_level
                action = self._infer_action(battery_change, solar, load)

                # Calculate reward based on price
                energy_kwh = abs(battery_change) / 100 * 10  # Assume 10kWh battery
                reward = self._calculate_experience_reward(
                    action, current_price, energy_kwh, battery_change, solar
                )

                # Next state discretization
                next_battery_discrete = self._discretize_battery(next_battery)
                next_price_discrete = self._discretize_price(next_price, price_data)
                next_solar = solar_data[i + 1].get("mean", 0) if i + 1 < len(solar_data) else 0
                next_solar_discrete = self._discretize_solar(next_solar)
                next_load = load_data[i + 1].get("mean", 0) if i + 1 < len(load_data) else 0
                next_load_discrete = self._discretize_load(next_load)
                next_dt = datetime.fromisoformat(battery_data[i + 1]["start"])
                next_hour_period = next_dt.hour // 4

                next_state = (
                    next_battery_discrete,
                    next_price_discrete,
                    next_solar_discrete,
                    next_load_discrete,
                    next_hour_period,
                )

                experiences.append((state, action, reward, next_state))

            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Skipping data point %d: %s", i, err)
                continue

        return experiences

    def _discretize_battery(self, level: float) -> int:
        """Discretize battery level to 0-4."""
        if level < 20:
            return 0
        if level < 40:
            return 1
        if level < 60:
            return 2
        if level < 80:
            return 3
        return 4

    def _discretize_price(self, price: float, price_data: list[dict[str, Any]]) -> int:
        """Discretize price to 0-4 based on percentile."""
        prices = [p.get("mean", 0) or 0 for p in price_data]
        if not prices:
            return 2

        percentile = sum(1 for p in prices if p < price) / len(prices) * 100
        if percentile < 20:
            return 0  # Very cheap
        if percentile < 40:
            return 1  # Cheap
        if percentile < 60:
            return 2  # Normal
        if percentile < 80:
            return 3  # Expensive
        return 4  # Very expensive

    def _discretize_solar(self, power: float) -> int:
        """Discretize solar power to 0-3."""
        if power < 500:
            return 0  # No/low solar
        if power < 2000:
            return 1  # Medium solar
        if power < 5000:
            return 2  # Good solar
        return 3  # High solar

    def _discretize_load(self, power: float) -> int:
        """Discretize load power to 0-2."""
        if power < 1500:
            return 0  # Low load
        if power < 4000:
            return 1  # Medium load
        return 2  # High load

    def _infer_action(self, battery_change: float, _solar: float, _load: float) -> Action:
        """Infer action from battery state change.

        Note: solar and load parameters reserved for future enhanced inference.
        """
        if battery_change > 5:
            return Action.CHARGE_HIGH if battery_change > 15 else Action.CHARGE_LOW
        if battery_change < -5:
            return Action.DISCHARGE_HIGH if battery_change < -15 else Action.DISCHARGE_LOW
        return Action.HOLD

    def _calculate_experience_reward(
        self,
        action: Action,
        price: float,
        energy_kwh: float,
        battery_change: float,
        solar: float,
    ) -> float:
        """Calculate reward for historical experience.

        PRICE IS PRIMARY - matches DecisionOptimizer.calculate_reward().
        """
        reward = 0.0

        if action in [Action.DISCHARGE_HIGH, Action.DISCHARGE_LOW]:
            # Revenue from selling
            revenue = energy_kwh * price
            reward += revenue * 10

            if price < 0.10:
                reward -= 2.0

        elif action in [Action.CHARGE_HIGH, Action.CHARGE_LOW]:
            # Cost of charging
            cost = energy_kwh * price
            reward -= cost * 10

            if price < 0.05:
                reward += 2.0

        # Battery cycle penalty
        cycle_penalty = abs(battery_change) * 0.01
        reward -= cycle_penalty

        # Solar utilization bonus
        if action == Action.HOLD and solar > 0:
            reward += solar * 0.001

        return reward

    async def _save_models(self) -> None:
        """Save trained models to disk."""
        model_path = self.get_model_path()
        model_path.mkdir(parents=True, exist_ok=True)

        if self.solar_predictor and self.solar_predictor.is_trained:
            await self.hass.async_add_executor_job(self.solar_predictor.save, model_path)

        if self.load_forecaster and self.load_forecaster.is_trained:
            await self.hass.async_add_executor_job(self.load_forecaster.save, model_path)

        if self.decision_optimizer and self.decision_optimizer.is_trained:
            await self.hass.async_add_executor_job(self.decision_optimizer.save, model_path)

    async def load_models(self) -> bool:
        """Load previously trained models.

        Returns:
            True if models loaded successfully
        """
        model_path = self.get_model_path()

        if not model_path.exists():
            _LOGGER.info("No saved models found")
            return False

        try:
            # Load solar predictor
            self.solar_predictor = SolarPredictor()
            await self.hass.async_add_executor_job(self.solar_predictor.load, model_path)

            # Load load forecaster
            self.load_forecaster = LoadForecaster()
            await self.hass.async_add_executor_job(self.load_forecaster.load, model_path)

            # Load decision optimizer
            self.decision_optimizer = DecisionOptimizer()
            await self.hass.async_add_executor_job(self.decision_optimizer.load, model_path)

            _LOGGER.info("Loaded AI models from %s", model_path)
            return True

        except Exception as err:
            _LOGGER.warning("Failed to load some models: %s", err)
            return False
