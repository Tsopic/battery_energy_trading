"""Tests for automation helper."""

import pytest

from custom_components.battery_energy_trading.automation_helper import (
    AutomationScriptGenerator,
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
