"""Tests for automation helper."""

import pytest

from custom_components.battery_energy_trading.automation_helper import (
    AutomationScriptGenerator,
)
from custom_components.battery_energy_trading.const import (
    CONF_CUSTOM_CHARGE_ENTITY,
    CONF_CUSTOM_CHARGE_SERVICE,
    CONF_CUSTOM_DISCHARGE_ENTITY,
    CONF_CUSTOM_DISCHARGE_SERVICE,
    CONF_CUSTOM_NORMAL_ENTITY,
    CONF_CUSTOM_NORMAL_SERVICE,
    CONF_INVERTER_CONTROL_TYPE,
    DEFAULT_SUNGROW_SCRIPT_CHARGE,
    DEFAULT_SUNGROW_SCRIPT_DISCHARGE,
    DEFAULT_SUNGROW_SCRIPT_NORMAL,
    INVERTER_CONTROL_CUSTOM,
    INVERTER_CONTROL_SUNGROW_MODBUS,
    INVERTER_CONTROL_SUNGROW_SCRIPTS,
)


@pytest.mark.asyncio
async def test_generate_sungrow_discharge_automation():
    """Test generating Sungrow discharge control automation."""
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        discharge_rate_entity="number.battery_energy_trading_discharge_rate_kw",
    )

    automation_yaml = generator.generate_discharge_automation()

    assert "automation:" in automation_yaml
    assert "binary_sensor.battery_energy_trading_forced_discharge" in automation_yaml
    assert "select.sungrow_ems_mode" in automation_yaml
    assert "number.sungrow_forced_discharging_power" in automation_yaml
    assert "Forced Mode" in automation_yaml


@pytest.mark.asyncio
async def test_generate_charging_automation():
    """Test generating charging control automation."""
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        charge_rate_entity="number.battery_energy_trading_charge_rate_kw",
    )

    automation_yaml = generator.generate_charging_automation()

    assert "binary_sensor.battery_energy_trading_cheapest_hours" in automation_yaml
    assert "number.sungrow_forced_charging_power" in automation_yaml


@pytest.mark.asyncio
async def test_generate_sungrow_scripts_discharge_automation():
    """Test generating Sungrow script-based discharge control automation."""
    options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_SCRIPTS,
        CONF_CUSTOM_DISCHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_DISCHARGE,
        CONF_CUSTOM_CHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_CHARGE,
        CONF_CUSTOM_NORMAL_SERVICE: "script.turn_on",
        CONF_CUSTOM_NORMAL_ENTITY: DEFAULT_SUNGROW_SCRIPT_NORMAL,
    }
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        options=options,
    )

    automation_yaml = generator.generate_discharge_automation()

    assert "automation:" in automation_yaml
    assert "binary_sensor.battery_energy_trading_forced_discharge" in automation_yaml
    assert "script.turn_on" in automation_yaml
    assert DEFAULT_SUNGROW_SCRIPT_DISCHARGE in automation_yaml
    assert DEFAULT_SUNGROW_SCRIPT_NORMAL in automation_yaml
    # Should NOT contain Modbus entities
    assert "select.sungrow_ems_mode" not in automation_yaml
    assert "number.sungrow_forced_discharging_power" not in automation_yaml


@pytest.mark.asyncio
async def test_generate_sungrow_scripts_charging_automation():
    """Test generating Sungrow script-based charging control automation."""
    options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_SCRIPTS,
        CONF_CUSTOM_DISCHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_DISCHARGE,
        CONF_CUSTOM_CHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_CHARGE,
        CONF_CUSTOM_NORMAL_SERVICE: "script.turn_on",
        CONF_CUSTOM_NORMAL_ENTITY: DEFAULT_SUNGROW_SCRIPT_NORMAL,
    }
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        options=options,
    )

    automation_yaml = generator.generate_charging_automation()

    assert "binary_sensor.battery_energy_trading_cheapest_hours" in automation_yaml
    assert "script.turn_on" in automation_yaml
    assert DEFAULT_SUNGROW_SCRIPT_CHARGE in automation_yaml
    assert DEFAULT_SUNGROW_SCRIPT_NORMAL in automation_yaml
    # Should NOT contain Modbus entities
    assert "number.sungrow_forced_charging_power" not in automation_yaml


@pytest.mark.asyncio
async def test_generate_custom_control_automation():
    """Test generating custom script-based control automation."""
    options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_CUSTOM,
        CONF_CUSTOM_DISCHARGE_SERVICE: "homeassistant.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: "input_boolean.my_discharge_mode",
        CONF_CUSTOM_CHARGE_SERVICE: "homeassistant.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: "input_boolean.my_charge_mode",
        CONF_CUSTOM_NORMAL_SERVICE: "homeassistant.turn_off",
        CONF_CUSTOM_NORMAL_ENTITY: "input_boolean.my_discharge_mode",
    }
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.custom_battery_level",
        options=options,
    )

    discharge_yaml = generator.generate_discharge_automation()
    charging_yaml = generator.generate_charging_automation()

    # Discharge automation checks
    assert "homeassistant.turn_on" in discharge_yaml
    assert "input_boolean.my_discharge_mode" in discharge_yaml
    assert "homeassistant.turn_off" in discharge_yaml

    # Charging automation checks
    assert "input_boolean.my_charge_mode" in charging_yaml


@pytest.mark.asyncio
async def test_generate_all_automations_with_control_type():
    """Test that generate_all_automations includes control type description."""
    options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_SCRIPTS,
        CONF_CUSTOM_DISCHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_DISCHARGE,
        CONF_CUSTOM_CHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: DEFAULT_SUNGROW_SCRIPT_CHARGE,
        CONF_CUSTOM_NORMAL_SERVICE: "script.turn_on",
        CONF_CUSTOM_NORMAL_ENTITY: DEFAULT_SUNGROW_SCRIPT_NORMAL,
    }
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        options=options,
    )

    all_yaml = generator.generate_all_automations()

    assert "# Control Type:" in all_yaml
    assert "Sungrow Scripts" in all_yaml
    assert "Battery Trading: Smart Discharge Control" in all_yaml
    assert "Battery Trading: Smart Charging Control" in all_yaml


@pytest.mark.asyncio
async def test_get_control_type_description():
    """Test control type descriptions for all types."""
    # Modbus
    generator_modbus = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool",
        battery_level_entity="sensor.battery",
        options={CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_MODBUS},
    )
    assert "Modbus" in generator_modbus.get_control_type_description()

    # Scripts
    generator_scripts = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool",
        battery_level_entity="sensor.battery",
        options={CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_SCRIPTS},
    )
    assert "Scripts" in generator_scripts.get_control_type_description()

    # Custom
    generator_custom = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool",
        battery_level_entity="sensor.battery",
        options={CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_CUSTOM},
    )
    assert "Custom" in generator_custom.get_control_type_description()


@pytest.mark.asyncio
async def test_default_control_type_is_modbus():
    """Test that default control type is Sungrow Modbus when no options provided."""
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
    )

    automation_yaml = generator.generate_discharge_automation()

    # Should use Modbus control by default
    assert "select.sungrow_ems_mode" in automation_yaml
    assert "number.sungrow_forced_discharging_power" in automation_yaml
