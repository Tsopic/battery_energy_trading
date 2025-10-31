"""Automation script generation helpers."""

from __future__ import annotations

import logging


_LOGGER = logging.getLogger(__name__)

DISCHARGE_AUTOMATION_TEMPLATE = """
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
                  entity_id: select.sungrow_ems_mode
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_discharging_power
                data:
                  value: >
                    {{{{ states('{discharge_rate_entity}') | float(5.0) * 1000 }}}}
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_charging_power
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: select.sungrow_ems_mode
            data:
              option: "Self-consumption"
"""

CHARGING_AUTOMATION_TEMPLATE = """
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
                  entity_id: select.sungrow_ems_mode
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_charging_power
                data:
                  value: >
                    {{{{ states('{charge_rate_entity}') | float(5.0) * 1000 }}}}
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_discharging_power
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: select.sungrow_ems_mode
            data:
              option: "Self-consumption"
"""


class AutomationScriptGenerator:
    """Generate Home Assistant automation scripts for battery trading."""

    def __init__(
        self,
        nordpool_entity: str,
        battery_level_entity: str,
        discharge_rate_entity: str | None = None,
        charge_rate_entity: str | None = None,
    ) -> None:
        """Initialize generator with entity IDs."""
        self.nordpool_entity = nordpool_entity
        self.battery_level_entity = battery_level_entity
        self.discharge_rate_entity = (
            discharge_rate_entity or "number.battery_energy_trading_discharge_rate_kw"
        )
        self.charge_rate_entity = (
            charge_rate_entity or "number.battery_energy_trading_charge_rate_kw"
        )

    def generate_discharge_automation(self) -> str:
        """Generate discharge automation YAML."""
        return DISCHARGE_AUTOMATION_TEMPLATE.format(
            discharge_rate_entity=self.discharge_rate_entity
        )

    def generate_charging_automation(self) -> str:
        """Generate charging automation YAML."""
        return CHARGING_AUTOMATION_TEMPLATE.format(
            charge_rate_entity=self.charge_rate_entity
        )

    def generate_all_automations(self) -> str:
        """Generate all automation scripts."""
        return f"""# Battery Energy Trading - Auto-Generated Automations
# Generated for Nord Pool: {self.nordpool_entity}
# Battery Level: {self.battery_level_entity}

{self.generate_discharge_automation()}

{self.generate_charging_automation()}
"""
