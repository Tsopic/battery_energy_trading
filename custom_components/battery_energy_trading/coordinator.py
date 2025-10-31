"""DataUpdateCoordinator for Battery Energy Trading."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


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

        # Action tracking for automation monitoring
        self._last_action: str | None = None
        self._last_action_time: str | None = None
        self._automation_active: bool = False
        self._next_discharge_slot: str | None = None
        self._next_charge_slot: str | None = None

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
                raise UpdateFailed(f"Nord Pool entity {self._nordpool_entity} not found")

            if state.state in ("unknown", "unavailable"):
                raise UpdateFailed(f"Nord Pool entity {self._nordpool_entity} is {state.state}")

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
                # Action tracking data for automation monitoring
                "last_action": self._last_action,
                "last_action_time": self._last_action_time,
                "automation_active": self._automation_active,
                "next_discharge_slot": self._next_discharge_slot,
                "next_charge_slot": self._next_charge_slot,
            }

        except Exception as err:
            _LOGGER.error("Error updating Nord Pool data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with Nord Pool: {err}") from err

    def record_action(
        self,
        action: str,
        next_discharge_slot: str | None = None,
        next_charge_slot: str | None = None,
    ) -> None:
        """Record automation action for status tracking.

        Args:
            action: Action type ("charge" or "discharge")
            next_discharge_slot: Next scheduled discharge slot time (ISO format)
            next_charge_slot: Next scheduled charge slot time (ISO format)
        """
        self._last_action = action
        self._last_action_time = datetime.now().isoformat()
        self._automation_active = True
        self._next_discharge_slot = next_discharge_slot
        self._next_charge_slot = next_charge_slot

        _LOGGER.info(
            "Recorded automation action: %s at %s", action, self._last_action_time
        )

    def clear_action(self) -> None:
        """Clear automation action status (when automation stops)."""
        self._automation_active = False
        _LOGGER.info("Cleared automation action status")
