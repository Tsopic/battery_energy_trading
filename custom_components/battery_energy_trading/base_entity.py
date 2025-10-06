"""Base entity class for Battery Energy Trading."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION


if TYPE_CHECKING:
    from .coordinator import BatteryEnergyTradingCoordinator

_LOGGER = logging.getLogger(__name__)


class BatteryTradingBaseEntity(CoordinatorEntity["BatteryEnergyTradingCoordinator"], Entity):
    """Base class for all Battery Energy Trading entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entity_type: str,
        coordinator: BatteryEnergyTradingCoordinator | None = None,
    ) -> None:
        """Initialize the base entity.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            entity_type: Type of entity (for unique ID)
            coordinator: Data update coordinator (optional for entities that don't need it)
        """
        # Initialize CoordinatorEntity if coordinator provided
        if coordinator:
            super().__init__(coordinator)
        else:
            Entity.__init__(self)

        self.hass = hass
        self._entry = entry
        self._entity_type = entity_type
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{entity_type}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battery Energy Trading",
            manufacturer="Battery Energy Trading",
            model="Energy Optimizer",
            sw_version=VERSION,
        )

    def _get_float_state(self, entity_id: str | None, default: float = 0.0) -> float:
        """
        Get float value from entity state.

        Args:
            entity_id: Entity ID to query
            default: Default value if entity not found or invalid

        Returns:
            Float value from entity state or default
        """
        if not entity_id:
            _LOGGER.debug("No entity_id provided, returning default: %s", default)
            return default

        try:
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.warning("Entity %s not found", entity_id)
                return default

            if state.state in ("unknown", "unavailable"):
                _LOGGER.debug("Entity %s state is %s", entity_id, state.state)
                return default

            return float(state.state)
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Failed to convert state of %s to float: %s", entity_id, err
            )
            return default

    def _get_switch_state(self, switch_type: str) -> bool:
        """
        Get switch state for this integration.

        Args:
            switch_type: Type of switch (from const.py)

        Returns:
            True if switch is on, False if off, True if not found (fail-safe)
        """
        entity_id = f"switch.{DOMAIN}_{self._entry.entry_id}_{switch_type}"

        try:
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.debug(
                    "Switch %s not found, defaulting to enabled", entity_id
                )
                return True  # Default to enabled if switch not found

            is_on = state.state == "on"
            _LOGGER.debug("Switch %s is %s", entity_id, "on" if is_on else "off")
            return is_on
        except Exception as err:
            _LOGGER.error("Error getting switch state for %s: %s", entity_id, err)
            return True  # Fail-safe: default to enabled

    def _get_number_entity_value(self, number_type: str, default: float) -> float:
        """
        Get value from number entity.

        Args:
            number_type: Type of number entity (from const.py)
            default: Default value if not found

        Returns:
            Number entity value or default
        """
        entity_id = f"number.{DOMAIN}_{self._entry.entry_id}_{number_type}"
        return self._get_float_state(entity_id, default)

    def _safe_get_attribute(
        self,
        entity_id: str,
        attribute: str,
        default: Any = None,
    ) -> Any:
        """
        Safely get attribute from entity state.

        Args:
            entity_id: Entity ID to query
            attribute: Attribute name
            default: Default value if not found

        Returns:
            Attribute value or default
        """
        try:
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.debug("Entity %s not found for attribute %s", entity_id, attribute)
                return default

            value = state.attributes.get(attribute, default)
            _LOGGER.debug(
                "Got attribute %s from %s: %s",
                attribute,
                entity_id,
                "found" if value != default else "not found",
            )
            return value
        except Exception as err:
            _LOGGER.error(
                "Error getting attribute %s from %s: %s", attribute, entity_id, err
            )
            return default
