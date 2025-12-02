"""Tests for Q-learning decision optimizer."""
import tempfile
from pathlib import Path

import numpy as np
import pytest

from custom_components.battery_energy_trading.ai.models.decision_optimizer import (
    Action,
    DecisionOptimizer,
)


class TestDecisionOptimizer:
    """Test Q-learning decision optimizer."""

    @pytest.fixture
    def optimizer(self) -> DecisionOptimizer:
        """Create decision optimizer."""
        return DecisionOptimizer(
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.1,
        )

    def test_init(self, optimizer: DecisionOptimizer) -> None:
        """Test optimizer initialization."""
        assert optimizer.name == "decision_optimizer"
        assert len(optimizer.q_table) == 0

    def test_actions(self) -> None:
        """Test action enum."""
        assert Action.CHARGE_HIGH.value == 0
        assert Action.HOLD.value == 2
        assert Action.DISCHARGE_HIGH.value == 4

    def test_get_action_training_mode(self, optimizer: DecisionOptimizer) -> None:
        """Test action selection in training mode."""
        state = (2, 3, 1)  # Example state tuple
        action = optimizer.get_action(state, training=True)
        assert isinstance(action, Action)

    def test_get_action_inference_mode(self, optimizer: DecisionOptimizer) -> None:
        """Test action selection in inference mode."""
        state = (2, 3, 1)
        # Set a Q value
        optimizer.q_table[state] = {Action.DISCHARGE_HIGH: 10.0}
        action = optimizer.get_action(state, training=False)
        assert action == Action.DISCHARGE_HIGH

    def test_get_action_unknown_state(self, optimizer: DecisionOptimizer) -> None:
        """Test action for unknown state returns HOLD."""
        state = (99, 99, 99)  # Unknown state
        action = optimizer.get_action(state, training=False)
        assert action == Action.HOLD

    def test_update_q_value(self, optimizer: DecisionOptimizer) -> None:
        """Test Q-value update."""
        state = (2, 3, 1)
        action = Action.DISCHARGE_HIGH
        next_state = (1, 2, 1)
        reward = 5.0

        initial_q = optimizer.get_q_value(state, action)
        optimizer.update(state, action, reward, next_state)
        updated_q = optimizer.get_q_value(state, action)

        assert updated_q != initial_q

    def test_get_q_value_unknown(self, optimizer: DecisionOptimizer) -> None:
        """Test Q-value for unknown state-action is 0."""
        q_value = optimizer.get_q_value((99, 99, 99), Action.HOLD)
        assert q_value == 0.0

    def test_price_primary_in_reward(self, optimizer: DecisionOptimizer) -> None:
        """Test that price is primary factor in reward calculation."""
        # High price discharge should be rewarded
        reward_high = optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.40,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

        # Low price discharge should be penalized
        reward_low = optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.05,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

        assert reward_high > reward_low  # Price matters!

    def test_charge_reward_low_price_bonus(
        self, optimizer: DecisionOptimizer
    ) -> None:
        """Test charging at low price gets bonus."""
        reward_very_low = optimizer.calculate_reward(
            action=Action.CHARGE_HIGH,
            price=0.03,
            energy_kwh=5.0,
            battery_change=5.0,
        )

        reward_normal = optimizer.calculate_reward(
            action=Action.CHARGE_HIGH,
            price=0.15,
            energy_kwh=5.0,
            battery_change=5.0,
        )

        assert reward_very_low > reward_normal

    def test_discharge_reward_low_price_penalty(
        self, optimizer: DecisionOptimizer
    ) -> None:
        """Test discharging at low price gets penalty."""
        reward = optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.05,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

        # Should have penalty for discharging at low price
        assert reward < 0 or reward < optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.20,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

    def test_hold_with_solar_bonus(self, optimizer: DecisionOptimizer) -> None:
        """Test HOLD action with solar gets small bonus."""
        reward_with_solar = optimizer.calculate_reward(
            action=Action.HOLD,
            price=0.15,
            energy_kwh=0.0,
            battery_change=0.0,
            solar_available=5000.0,
        )

        reward_no_solar = optimizer.calculate_reward(
            action=Action.HOLD,
            price=0.15,
            energy_kwh=0.0,
            battery_change=0.0,
            solar_available=0.0,
        )

        assert reward_with_solar > reward_no_solar

    def test_train_from_experience(self, optimizer: DecisionOptimizer) -> None:
        """Test training from experience list."""
        experiences = [
            ((2, 3, 1, 1, 2), Action.DISCHARGE_HIGH, 5.0, (1, 2, 1, 1, 2)),
            ((1, 2, 1, 1, 2), Action.HOLD, 0.5, (1, 2, 1, 1, 3)),
            ((3, 1, 2, 0, 4), Action.CHARGE_HIGH, 2.0, (4, 1, 2, 0, 5)),
        ]

        metrics = optimizer.train_from_experience(experiences)

        assert metrics["experiences_processed"] == 3
        assert optimizer.is_trained is True
        assert len(optimizer.q_table) > 0

    def test_train_placeholder(self, optimizer: DecisionOptimizer) -> None:
        """Test train() placeholder method."""
        X = np.random.randn(10, 5)
        y = np.random.randn(10)

        metrics = optimizer.train(X, y)

        assert "q_table_size" in metrics
        assert optimizer.is_trained is True

    def test_predict(self, optimizer: DecisionOptimizer) -> None:
        """Test predict method."""
        # Set up some Q values
        optimizer.q_table[(2, 3, 1, 1, 2)] = {Action.DISCHARGE_HIGH: 10.0}

        X = np.array([[2, 3, 1, 1, 2], [0, 0, 0, 0, 0]])
        actions = optimizer.predict(X)

        assert actions.shape == (2,)
        assert actions[0] == Action.DISCHARGE_HIGH.value
        assert actions[1] == Action.HOLD.value  # Default for unknown state

    def test_get_recommendation(self, optimizer: DecisionOptimizer) -> None:
        """Test getting action recommendation with confidence."""
        optimizer.q_table[(2, 3, 1, 1, 2)] = {
            Action.DISCHARGE_HIGH: 10.0,
            Action.HOLD: 2.0,
        }

        action, confidence = optimizer.get_recommendation(
            battery_level=2,
            price_level=3,
            solar_level=1,
            load_level=1,
            hour_period=2,
        )

        assert action == Action.DISCHARGE_HIGH
        assert 0.0 <= confidence <= 1.0

    def test_get_recommendation_unknown_state(
        self, optimizer: DecisionOptimizer
    ) -> None:
        """Test recommendation for unknown state."""
        action, confidence = optimizer.get_recommendation(
            battery_level=4,
            price_level=4,
            solar_level=3,
            load_level=2,
            hour_period=5,
        )

        assert action == Action.HOLD  # Default
        assert confidence == 0.5  # Default confidence

    def test_save_and_load(self, optimizer: DecisionOptimizer) -> None:
        """Test saving and loading optimizer."""
        # Train with some experiences
        experiences = [
            ((2, 3, 1, 1, 2), Action.DISCHARGE_HIGH, 5.0, (1, 2, 1, 1, 2)),
            ((1, 2, 1, 1, 2), Action.HOLD, 0.5, (1, 2, 1, 1, 3)),
        ]
        optimizer.train_from_experience(experiences)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            optimizer.save(path)

            new_optimizer = DecisionOptimizer()
            new_optimizer.load(path)

            assert new_optimizer.is_trained is True
            assert len(new_optimizer.q_table) == len(optimizer.q_table)
            assert (
                new_optimizer.learning_rate == optimizer.learning_rate
            )

    def test_load_missing_file(self, optimizer: DecisionOptimizer) -> None:
        """Test loading from missing file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                optimizer.load(Path(tmpdir))

    def test_q_learning_convergence(self, optimizer: DecisionOptimizer) -> None:
        """Test Q-values converge with repeated updates."""
        state = (2, 3, 1)
        action = Action.DISCHARGE_HIGH
        next_state = (1, 2, 1)

        # Multiple updates with same reward should converge
        q_values = []
        for _ in range(100):
            optimizer.update(state, action, 5.0, next_state)
            q_values.append(optimizer.get_q_value(state, action))

        # Q-value should stabilize
        assert abs(q_values[-1] - q_values[-10]) < abs(q_values[10] - q_values[0])
