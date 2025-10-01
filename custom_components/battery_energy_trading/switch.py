"""Switch platform for Battery Energy Trading."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    SWITCH_ENABLE_FORCED_CHARGING,
    SWITCH_ENABLE_FORCED_DISCHARGE,
    SWITCH_ENABLE_EXPORT_MANAGEMENT,
    SWITCH_ENABLE_MULTIDAY_OPTIMIZATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery Energy Trading switches."""
    switches = [
        BatteryTradingSwitch(
            entry,
            SWITCH_ENABLE_FORCED_CHARGING,
            "Enable Forced Charging",
            "mdi:battery-charging",
            "Allow automatic battery charging during cheap price periods",
            False,  # Default: disabled for solar-only usage
        ),
        BatteryTradingSwitch(
            entry,
            SWITCH_ENABLE_FORCED_DISCHARGE,
            "Enable Forced Discharge",
            "mdi:battery-arrow-up",
            "Allow automatic battery discharge during high price periods",
            True,  # Default: enabled for selling excess solar
        ),
        BatteryTradingSwitch(
            entry,
            SWITCH_ENABLE_EXPORT_MANAGEMENT,
            "Enable Export Management",
            "mdi:transmission-tower-export",
            "Manage grid export based on price thresholds",
            True,  # Default: enabled
        ),
        BatteryTradingSwitch(
            entry,
            SWITCH_ENABLE_MULTIDAY_OPTIMIZATION,
            "Enable Multi-Day Optimization",
            "mdi:calendar-multiple",
            "Optimize across today + tomorrow using price forecasts and solar estimates",
            True,  # Default: enabled - maximizes revenue potential
        ),
    ]

    async_add_entities(switches)


class BatteryTradingSwitch(SwitchEntity, RestoreEntity):
    """Representation of a Battery Energy Trading switch."""

    def __init__(
        self,
        entry: ConfigEntry,
        switch_type: str,
        name: str,
        icon: str,
        description: str,
        default_state: bool,
    ) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._switch_type = switch_type
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{switch_type}"
        self._attr_icon = icon
        self._description = description
        self._attr_is_on = default_state
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battery Energy Trading",
            manufacturer="Battery Energy Trading",
            model="Energy Optimizer",
            sw_version="0.6.1",
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "description": self._description,
            "switch_type": self._switch_type,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self.async_write_ha_state()
        _LOGGER.info("Enabled %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._attr_is_on = False
        self.async_write_ha_state()
        _LOGGER.info("Disabled %s", self._attr_name)
