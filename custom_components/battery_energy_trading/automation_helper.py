"""Automation script generation helpers."""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    CONF_CUSTOM_CHARGE_ENTITY,
    CONF_CUSTOM_CHARGE_SERVICE,
    CONF_CUSTOM_DISCHARGE_ENTITY,
    CONF_CUSTOM_DISCHARGE_SERVICE,
    CONF_CUSTOM_NORMAL_ENTITY,
    CONF_CUSTOM_NORMAL_SERVICE,
    CONF_INVERTER_CONTROL_TYPE,
    DEFAULT_SUNGROW_MODBUS_CHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_EMS_MODE,
    INVERTER_CONTROL_CUSTOM,
    INVERTER_CONTROL_SUNGROW_MODBUS,
    INVERTER_CONTROL_SUNGROW_SCRIPTS,
)


_LOGGER = logging.getLogger(__name__)

# Template for Sungrow Modbus control (original implementation)
DISCHARGE_AUTOMATION_MODBUS_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Discharge Control"
    description: "Auto-generated: Discharge battery during high-price slots"
    id: battery_trading_auto_discharge
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_discharge
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_forced_discharge
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_discharge
                state: 'on'
            sequence:
              - service: select.select_option
                target:
                  entity_id: {ems_mode_entity}
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: {discharge_power_entity}
                data:
                  value: >
                    {{{{{{ states('{discharge_rate_entity}') | float(5.0) * 1000 }}}}}}
              - service: number.set_value
                target:
                  entity_id: {charge_power_entity}
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: {ems_mode_entity}
            data:
              option: "Self-consumption"
"""

CHARGING_AUTOMATION_MODBUS_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Charging Control"
    description: "Auto-generated: Charge battery during low-price slots"
    id: battery_trading_auto_charging
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_charging
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_cheapest_hours
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_charging
                state: 'on'
            sequence:
              - service: select.select_option
                target:
                  entity_id: {ems_mode_entity}
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: {charge_power_entity}
                data:
                  value: >
                    {{{{{{ states('{charge_rate_entity}') | float(5.0) * 1000 }}}}}}
              - service: number.set_value
                target:
                  entity_id: {discharge_power_entity}
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: {ems_mode_entity}
            data:
              option: "Self-consumption"
"""

# Template for script-based control (Sungrow scripts or custom)
DISCHARGE_AUTOMATION_SCRIPT_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Discharge Control"
    description: "Auto-generated: Discharge battery during high-price slots"
    id: battery_trading_auto_discharge
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_discharge
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_forced_discharge
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_discharge
                state: 'on'
            sequence:
              - service: {discharge_service}
                target:
                  entity_id: {discharge_entity}
        default:
          - service: {normal_service}
            target:
              entity_id: {normal_entity}
"""

CHARGING_AUTOMATION_SCRIPT_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Charging Control"
    description: "Auto-generated: Charge battery during low-price slots"
    id: battery_trading_auto_charging
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_charging
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_cheapest_hours
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_charging
                state: 'on'
            sequence:
              - service: {charge_service}
                target:
                  entity_id: {charge_entity}
        default:
          - service: {normal_service}
            target:
              entity_id: {normal_entity}
"""


class AutomationScriptGenerator:
    """Generate Home Assistant automation scripts for battery trading."""

    def __init__(
        self,
        nordpool_entity: str,
        battery_level_entity: str,
        discharge_rate_entity: str | None = None,
        charge_rate_entity: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Initialize generator with entity IDs.

        Args:
            nordpool_entity: Nord Pool sensor entity ID
            battery_level_entity: Battery level sensor entity ID
            discharge_rate_entity: Discharge rate number entity ID
            charge_rate_entity: Charge rate number entity ID
            options: Config entry options containing inverter control type settings
        """
        self.nordpool_entity = nordpool_entity
        self.battery_level_entity = battery_level_entity
        self.discharge_rate_entity = (
            discharge_rate_entity or "number.battery_energy_trading_discharge_rate_kw"
        )
        self.charge_rate_entity = (
            charge_rate_entity or "number.battery_energy_trading_charge_rate_kw"
        )
        self.options = options or {}

        # Determine control type from options
        self.control_type = self.options.get(
            CONF_INVERTER_CONTROL_TYPE, INVERTER_CONTROL_SUNGROW_MODBUS
        )

    def _get_modbus_entities(self) -> dict[str, str]:
        """Get Modbus entity configuration."""
        return {
            "ems_mode_entity": DEFAULT_SUNGROW_MODBUS_EMS_MODE,
            "discharge_power_entity": DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER,
            "charge_power_entity": DEFAULT_SUNGROW_MODBUS_CHARGE_POWER,
            "discharge_rate_entity": self.discharge_rate_entity,
            "charge_rate_entity": self.charge_rate_entity,
        }

    def _get_script_entities(self) -> dict[str, str]:
        """Get script-based entity configuration from options."""
        return {
            "discharge_service": self.options.get(CONF_CUSTOM_DISCHARGE_SERVICE, "script.turn_on"),
            "discharge_entity": self.options.get(CONF_CUSTOM_DISCHARGE_ENTITY, ""),
            "charge_service": self.options.get(CONF_CUSTOM_CHARGE_SERVICE, "script.turn_on"),
            "charge_entity": self.options.get(CONF_CUSTOM_CHARGE_ENTITY, ""),
            "normal_service": self.options.get(CONF_CUSTOM_NORMAL_SERVICE, "script.turn_on"),
            "normal_entity": self.options.get(CONF_CUSTOM_NORMAL_ENTITY, ""),
        }

    def generate_discharge_automation(self) -> str:
        """Generate discharge automation YAML."""
        if self.control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            entities = self._get_modbus_entities()
            return DISCHARGE_AUTOMATION_MODBUS_TEMPLATE.format(**entities)

        # Script-based control (sungrow_scripts or custom)
        entities = self._get_script_entities()
        return DISCHARGE_AUTOMATION_SCRIPT_TEMPLATE.format(**entities)

    def generate_charging_automation(self) -> str:
        """Generate charging automation YAML."""
        if self.control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            entities = self._get_modbus_entities()
            return CHARGING_AUTOMATION_MODBUS_TEMPLATE.format(**entities)

        # Script-based control (sungrow_scripts or custom)
        entities = self._get_script_entities()
        return CHARGING_AUTOMATION_SCRIPT_TEMPLATE.format(**entities)

    def get_control_type_description(self) -> str:
        """Get a human-readable description of the control type."""
        if self.control_type == INVERTER_CONTROL_SUNGROW_MODBUS:
            return "Sungrow Modbus (EMS mode + power entities)"
        if self.control_type == INVERTER_CONTROL_SUNGROW_SCRIPTS:
            return "Sungrow Scripts (script.sg_set_*)"
        if self.control_type == INVERTER_CONTROL_CUSTOM:
            return "Custom (user-defined services)"
        return "Unknown"

    def generate_all_automations(self) -> str:
        """Generate all automation scripts."""
        return f"""# Battery Energy Trading - Auto-Generated Automations
# Generated for Nord Pool: {self.nordpool_entity}
# Battery Level: {self.battery_level_entity}
# Control Type: {self.get_control_type_description()}

{self.generate_discharge_automation()}

{self.generate_charging_automation()}
"""
