"""Extract training data from Home Assistant Long-Term Statistics."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .config import AIConfig


_LOGGER = logging.getLogger(__name__)


def _get_recorder_instance(hass: HomeAssistant) -> Any:
    """Get recorder instance (deferred import to avoid test issues)."""
    from homeassistant.components.recorder import get_instance

    return get_instance(hass)


def _statistics_during_period(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime,
    statistic_ids: list[str],
    period: str,
    units: dict[str, str] | None,
    types: set[str],
) -> dict[str, list[dict[str, Any]]]:
    """Call statistics_during_period (deferred import)."""
    from homeassistant.components.recorder.statistics import statistics_during_period

    return statistics_during_period(
        hass,
        start_time,
        end_time,
        statistic_ids=statistic_ids,
        period=period,
        units=units,
        types=types,
    )


class DataExtractor:
    """Extract training data from Home Assistant statistics."""

    def __init__(self, hass: HomeAssistant, config: AIConfig) -> None:
        """Initialize data extractor."""
        self.hass = hass
        self.config = config

    def get_statistics_entities(self) -> list[str]:
        """Get list of entity IDs to query for statistics."""
        entities = [
            self.config.solar_power_entity,
            self.config.solar_forecast_entity,
            self.config.load_power_entity,
            self.config.battery_level_entity,
            self.config.outdoor_temp_entity,
        ]
        # Add heat pump entities
        entities.extend(self.config.heat_pump_entities.values())
        return entities

    async def extract_training_data(
        self,
        days: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract training data from HA Long-Term Statistics.

        Args:
            days: Number of days of data to extract (default: config.training_days)
            start_time: Optional start time override
            end_time: Optional end time override

        Returns:
            Dictionary mapping entity_id to list of statistic records
        """
        if days is None:
            days = self.config.training_days

        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=days)

        entities = self.get_statistics_entities()

        try:
            instance = _get_recorder_instance(self.hass)
            statistics = await instance.async_add_executor_job(
                self._get_statistics,
                start_time,
                end_time,
                entities,
            )
            return statistics
        except Exception as err:
            _LOGGER.error("Failed to extract training data: %s", err)
            return {}

    def _get_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
        entities: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Get statistics from recorder (runs in executor)."""
        return _statistics_during_period(
            self.hass,
            start_time,
            end_time,
            statistic_ids=entities,
            period="hour",
            units=None,
            types={"mean", "sum"},
        )

    async def extract_recent_data(
        self, hours: int = 24
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract recent data for inference.

        Args:
            hours: Number of hours of recent data

        Returns:
            Dictionary mapping entity_id to list of recent records
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        try:
            instance = _get_recorder_instance(self.hass)
            statistics = await instance.async_add_executor_job(
                self._get_statistics,
                start_time,
                end_time,
                self.get_statistics_entities(),
            )
            return statistics
        except Exception as err:
            _LOGGER.error("Failed to extract recent data: %s", err)
            return {}

    def has_sufficient_data(self, data: dict[str, list[dict[str, Any]]]) -> bool:
        """Check if extracted data is sufficient for training.

        Args:
            data: Extracted statistics data

        Returns:
            True if data meets minimum requirements
        """
        if not data:
            return False

        min_records = self.config.min_training_days * 24  # hourly data

        # Check key entities have enough data
        key_entities = [
            self.config.solar_power_entity,
            self.config.load_power_entity,
            self.config.battery_level_entity,
        ]

        for entity in key_entities:
            if entity not in data:
                _LOGGER.warning("Missing data for %s", entity)
                return False
            if len(data[entity]) < min_records:
                _LOGGER.warning(
                    "Insufficient data for %s: %d records (need %d)",
                    entity,
                    len(data[entity]),
                    min_records,
                )
                return False

        return True
