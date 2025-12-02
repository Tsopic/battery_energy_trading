"""Q-learning decision optimizer for battery control."""
from __future__ import annotations

import logging
import pickle
from enum import Enum
from pathlib import Path

import numpy as np

from .base import BaseModel

_LOGGER = logging.getLogger(__name__)


class Action(Enum):
    """Battery control actions."""

    CHARGE_HIGH = 0  # Charge at max rate
    CHARGE_LOW = 1  # Charge at half rate
    HOLD = 2  # Self-consumption mode
    DISCHARGE_LOW = 3  # Discharge at half rate
    DISCHARGE_HIGH = 4  # Discharge at max rate


class DecisionOptimizer(BaseModel):
    """Q-learning agent for optimal charge/discharge decisions.

    CRITICAL: Nord Pool prices are the PRIMARY decision driver.
    This agent learns to optimize timing within price-selected windows.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        exploration_rate: float = 0.1,
    ) -> None:
        """Initialize Q-learning optimizer.

        Args:
            learning_rate: Alpha - how much new info overrides old
            discount_factor: Gamma - importance of future rewards
            exploration_rate: Epsilon - probability of random action
        """
        super().__init__(name="decision_optimizer")
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate

        # Q-table: state -> {action -> q_value}
        self.q_table: dict[tuple, dict[Action, float]] = {}

    def get_q_value(self, state: tuple, action: Action) -> float:
        """Get Q-value for state-action pair.

        Args:
            state: State tuple
            action: Action

        Returns:
            Q-value (0.0 if not seen before)
        """
        if state not in self.q_table:
            return 0.0
        return self.q_table[state].get(action, 0.0)

    def get_action(self, state: tuple, training: bool = False) -> Action:
        """Select action using epsilon-greedy policy.

        Args:
            state: Current state tuple
            training: Whether in training mode (exploration enabled)

        Returns:
            Selected action
        """
        # Exploration in training mode
        if training and np.random.random() < self.exploration_rate:
            return np.random.choice(list(Action))

        # Exploitation: select best action
        if state not in self.q_table:
            return Action.HOLD  # Default to safe action

        q_values = self.q_table[state]
        if not q_values:
            return Action.HOLD

        best_action = max(q_values.keys(), key=lambda a: q_values[a])
        return best_action

    def update(
        self,
        state: tuple,
        action: Action,
        reward: float,
        next_state: tuple,
    ) -> None:
        """Update Q-value using Q-learning update rule.

        Q(s,a) = Q(s,a) + α * (r + γ * max(Q(s',a')) - Q(s,a))

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Resulting state
        """
        # Initialize state if needed
        if state not in self.q_table:
            self.q_table[state] = {}

        # Current Q value
        current_q = self.get_q_value(state, action)

        # Max Q value for next state
        if next_state in self.q_table and self.q_table[next_state]:
            max_next_q = max(self.q_table[next_state].values())
        else:
            max_next_q = 0.0

        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )

        self.q_table[state][action] = new_q

    def calculate_reward(
        self,
        action: Action,
        price: float,
        energy_kwh: float,
        battery_change: float,
        solar_available: float = 0.0,
    ) -> float:
        """Calculate reward for action taken.

        PRICE IS PRIMARY FACTOR.

        Args:
            action: Action taken
            price: Current electricity price (EUR/kWh)
            energy_kwh: Energy transferred (positive = to grid)
            battery_change: Change in battery level
            solar_available: Solar power available

        Returns:
            Reward value
        """
        reward = 0.0

        # PRIMARY: Price-based revenue/cost
        if action in [Action.DISCHARGE_HIGH, Action.DISCHARGE_LOW]:
            # Revenue from selling at current price
            revenue = energy_kwh * price
            reward += revenue * 10  # Scale up price importance

            # Penalty for discharging at low prices
            if price < 0.10:
                reward -= 2.0

        elif action in [Action.CHARGE_HIGH, Action.CHARGE_LOW]:
            # Cost of buying at current price
            cost = energy_kwh * price
            reward -= cost * 10  # Scale up price importance

            # Bonus for charging at low prices
            if price < 0.05:
                reward += 2.0

        # Secondary: Battery cycle penalty
        cycle_penalty = abs(battery_change) * 0.01
        reward -= cycle_penalty

        # Secondary: Solar utilization bonus
        if action == Action.HOLD and solar_available > 0:
            reward += solar_available * 0.001  # Small bonus

        return reward

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Train from historical data.

        For Q-learning, training is done through experience replay.

        Args:
            X: State features (unused, states come from experience)
            y: Actions/rewards (unused, come from experience)

        Returns:
            Training metrics
        """
        # Q-learning trains through update() calls, not batch training
        self._is_trained = True
        return {"q_table_size": len(self.q_table)}

    def train_from_experience(
        self,
        experiences: list[tuple[tuple, Action, float, tuple]],
    ) -> dict[str, float]:
        """Train from list of experiences.

        Args:
            experiences: List of (state, action, reward, next_state) tuples

        Returns:
            Training metrics
        """
        _LOGGER.info("Training from %d experiences", len(experiences))

        for state, action, reward, next_state in experiences:
            self.update(state, action, reward, next_state)

        self._is_trained = True

        return {
            "experiences_processed": len(experiences),
            "q_table_size": len(self.q_table),
            "unique_states": len(self.q_table),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict best actions for states.

        Args:
            X: State features (converted to tuples internally)

        Returns:
            Action indices
        """
        actions = []
        for row in X:
            state = tuple(row.astype(int))
            action = self.get_action(state, training=False)
            actions.append(action.value)
        return np.array(actions)

    def get_recommendation(
        self,
        battery_level: int,
        price_level: int,
        solar_level: int,
        load_level: int,
        hour_period: int,
    ) -> tuple[Action, float]:
        """Get action recommendation with confidence.

        Args:
            battery_level: Discretized SOC (0-4)
            price_level: Discretized price (0-4)
            solar_level: Discretized solar (0-3)
            load_level: Discretized load (0-2)
            hour_period: Time period (0-5)

        Returns:
            Tuple of (recommended_action, confidence)
        """
        state = (battery_level, price_level, solar_level, load_level, hour_period)

        # Get action
        action = self.get_action(state, training=False)

        # Calculate confidence based on Q-value spread
        if state in self.q_table and len(self.q_table[state]) > 1:
            q_values = list(self.q_table[state].values())
            q_range = max(q_values) - min(q_values)
            confidence = min(q_range / 10.0, 1.0)  # Normalize to 0-1
        else:
            confidence = 0.5  # Default medium confidence

        return action, confidence

    def save(self, path: Path) -> None:
        """Save Q-table to disk."""
        path.mkdir(parents=True, exist_ok=True)
        model_path = path / "decision_optimizer.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(
                {
                    "q_table": self.q_table,
                    "learning_rate": self.learning_rate,
                    "discount_factor": self.discount_factor,
                    "exploration_rate": self.exploration_rate,
                },
                f,
            )

        _LOGGER.info("Saved decision optimizer to %s", model_path)

    def load(self, path: Path) -> None:
        """Load Q-table from disk."""
        model_path = path / "decision_optimizer.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.q_table = data["q_table"]
        self.learning_rate = data["learning_rate"]
        self.discount_factor = data["discount_factor"]
        self.exploration_rate = data["exploration_rate"]
        self._is_trained = True

        _LOGGER.info("Loaded decision optimizer from %s", model_path)
