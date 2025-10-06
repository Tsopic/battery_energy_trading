"""DataUpdateCoordinator for Battery Energy Trading."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_NORDPOOL_ENTITY

_LOGGER = logging.getLogger(__name__)


class BatteryEnergyTradingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Battery Energy Trading data updates.

    Fetches Nord Pool pricing data and makes it available to all entities
    via a single coordinated poll.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        nordpool_entity: str,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            nordpool_entity: Entity ID of the Nord Pool sensor
        """
        super().__init__(
            hass,
            _LOGGER,
            name="Battery Energy Trading",
            update_interval=timedelta(seconds=60),  # Poll every 60 seconds
        )
        self._nordpool_entity = nordpool_entity

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Nord Pool sensor.

        Returns:
            Dictionary containing raw_today and raw_tomorrow price data

        Raises:
            UpdateFailed: If the Nord Pool entity is not available or missing data
        """
        try:
            state = self.hass.states.get(self._nordpool_entity)

            if not state:
                raise UpdateFailed(
                    f"Nord Pool entity {self._nordpool_entity} not found"
                )

            if state.state in ("unknown", "unavailable"):
                raise UpdateFailed(
                    f"Nord Pool entity {self._nordpool_entity} is {state.state}"
                )

            # Extract price data from attributes
            raw_today = state.attributes.get("raw_today")
            raw_tomorrow = state.attributes.get("raw_tomorrow")

            if not raw_today:
                raise UpdateFailed(
                    f"Nord Pool entity {self._nordpool_entity} missing 'raw_today' attribute"
                )

            _LOGGER.debug(
                "Updated Nord Pool data: %d today slots, %d tomorrow slots",
                len(raw_today) if raw_today else 0,
                len(raw_tomorrow) if raw_tomorrow else 0,
            )

            return {
                "raw_today": raw_today,
                "raw_tomorrow": raw_tomorrow,
                "current_price": state.state,
                "unit": state.attributes.get("unit"),
                "currency": state.attributes.get("currency"),
            }

        except Exception as err:
            _LOGGER.error("Error updating Nord Pool data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with Nord Pool: {err}") from err
