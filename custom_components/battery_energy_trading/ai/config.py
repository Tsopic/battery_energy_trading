"""AI configuration and entity mappings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIConfig:
    """Configuration for AI models."""

    # Entity IDs (from Home Assistant)
    solar_power_entity: str = "sensor.total_dc_power"
    solar_forecast_entity: str = "sensor.energy_production_today"
    load_power_entity: str = "sensor.load_power"
    battery_level_entity: str = "sensor.battery_level"
    battery_capacity_entity: str = "sensor.battery_capacity"
    nordpool_entity: str = "sensor.nordpool_kwh_ee_eur_3_10_022"
    outdoor_temp_entity: str = "sensor.karksi_outdoor_temperature"

    # Heat pump power stage entities
    heat_pump_entities: dict[str, str] = field(default_factory=lambda: {
        "3kw": "binary_sensor.karksi_3kw_power_status",
        "6kw": "binary_sensor.karksi_6kw_power_status",
        "9kw": "binary_sensor.karksi_9kw_power_status",
        "12kw": "binary_sensor.karksi_12kw_power_status",
        "15kw": "binary_sensor.karksi_15kw_power_status",
    })

    # Training configuration
    training_days: int = 90
    min_training_days: int = 30
    training_schedule: str = "0 3 * * 0"  # Sunday 03:00

    # Model configuration
    solar_model_estimators: int = 50
    solar_model_max_depth: int = 5
    load_model_estimators: int = 50
    q_learning_rate: float = 0.1
    q_discount_factor: float = 0.95
    q_exploration_rate: float = 0.1

    @classmethod
    def from_config_entry(cls, entry_data: dict[str, Any]) -> AIConfig:
        """Create config from Home Assistant config entry."""
        return cls(
            solar_power_entity=entry_data.get(
                "solar_power_entity", cls.solar_power_entity
            ),
            nordpool_entity=entry_data.get("nordpool_entity", cls.nordpool_entity),
            battery_level_entity=entry_data.get(
                "battery_level_entity", cls.battery_level_entity
            ),
            battery_capacity_entity=entry_data.get(
                "battery_capacity_entity", cls.battery_capacity_entity
            ),
        )
