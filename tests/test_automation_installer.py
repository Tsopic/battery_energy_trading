"""Tests for automation installer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.battery_energy_trading.automation_installer import (
    CHARGING_AUTOMATION_ID,
    DISCHARGE_AUTOMATION_ID,
    AutomationInstaller,
)
from custom_components.battery_energy_trading.const import (
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_CUSTOM_CHARGE_ENTITY,
    CONF_CUSTOM_CHARGE_SERVICE,
    CONF_CUSTOM_DISCHARGE_ENTITY,
    CONF_CUSTOM_DISCHARGE_SERVICE,
    CONF_CUSTOM_NORMAL_ENTITY,
    CONF_CUSTOM_NORMAL_SERVICE,
    CONF_INVERTER_CONTROL_TYPE,
    CONF_NORDPOOL_ENTITY,
    DEFAULT_SUNGROW_MODBUS_CHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER,
    DEFAULT_SUNGROW_MODBUS_EMS_MODE,
    INVERTER_CONTROL_CUSTOM,
    INVERTER_CONTROL_SUNGROW_MODBUS,
    INVERTER_CONTROL_SUNGROW_SCRIPTS,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config.components = {"automation"}
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=None)
    hass.bus.async_fire = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry_modbus():
    """Create mock config entry with Modbus control type."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {
        CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
        CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
    }
    entry.options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_MODBUS,
    }
    return entry


@pytest.fixture
def mock_config_entry_scripts():
    """Create mock config entry with script control type."""
    entry = MagicMock()
    entry.entry_id = "test_entry_456"
    entry.data = {
        CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
        CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
    }
    entry.options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_SUNGROW_SCRIPTS,
        CONF_CUSTOM_DISCHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: "script.sg_set_forced_discharge_battery_mode",
        CONF_CUSTOM_CHARGE_SERVICE: "script.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: "script.sg_set_forced_charge_battery_mode",
        CONF_CUSTOM_NORMAL_SERVICE: "script.turn_on",
        CONF_CUSTOM_NORMAL_ENTITY: "script.sg_set_self_consumption_mode",
    }
    return entry


@pytest.fixture
def mock_config_entry_custom():
    """Create mock config entry with custom control type."""
    entry = MagicMock()
    entry.entry_id = "test_entry_789"
    entry.data = {
        CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
        CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
    }
    entry.options = {
        CONF_INVERTER_CONTROL_TYPE: INVERTER_CONTROL_CUSTOM,
        CONF_CUSTOM_DISCHARGE_SERVICE: "homeassistant.turn_on",
        CONF_CUSTOM_DISCHARGE_ENTITY: "input_boolean.discharge_mode",
        CONF_CUSTOM_CHARGE_SERVICE: "homeassistant.turn_on",
        CONF_CUSTOM_CHARGE_ENTITY: "input_boolean.charge_mode",
        CONF_CUSTOM_NORMAL_SERVICE: "homeassistant.turn_off",
        CONF_CUSTOM_NORMAL_ENTITY: "input_boolean.discharge_mode",
    }
    return entry


class TestAutomationInstallerInit:
    """Tests for AutomationInstaller initialization."""

    def test_init_modbus_control_type(self, mock_hass, mock_config_entry_modbus):
        """Test initialization with Modbus control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)

        assert installer.hass == mock_hass
        assert installer.config_entry == mock_config_entry_modbus
        assert installer._control_type == INVERTER_CONTROL_SUNGROW_MODBUS

    def test_init_scripts_control_type(self, mock_hass, mock_config_entry_scripts):
        """Test initialization with scripts control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_scripts)

        assert installer._control_type == INVERTER_CONTROL_SUNGROW_SCRIPTS

    def test_init_custom_control_type(self, mock_hass, mock_config_entry_custom):
        """Test initialization with custom control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_custom)

        assert installer._control_type == INVERTER_CONTROL_CUSTOM


class TestDischargeAutomationConfig:
    """Tests for discharge automation configuration generation."""

    def test_modbus_discharge_config(self, mock_hass, mock_config_entry_modbus):
        """Test discharge config for Modbus control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)
        config = installer._get_discharge_automation_config()

        assert config["id"] == DISCHARGE_AUTOMATION_ID
        assert config["alias"] == "Battery Trading: Smart Discharge Control"
        assert "Auto-installed" in config["description"]
        assert len(config["trigger"]) == 2
        assert config["trigger"][0]["entity_id"] == (
            "binary_sensor.battery_energy_trading_forced_discharge"
        )

        # Check Modbus-specific actions
        action = config["action"][0]
        assert "choose" in action
        sequence = action["choose"][0]["sequence"]
        assert sequence[0]["service"] == "select.select_option"
        assert sequence[0]["target"]["entity_id"] == DEFAULT_SUNGROW_MODBUS_EMS_MODE
        assert sequence[1]["target"]["entity_id"] == DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER

    def test_scripts_discharge_config(self, mock_hass, mock_config_entry_scripts):
        """Test discharge config for script control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_scripts)
        config = installer._get_discharge_automation_config()

        action = config["action"][0]
        sequence = action["choose"][0]["sequence"]

        # Should use script service
        assert sequence[0]["service"] == "script.turn_on"
        assert sequence[0]["target"]["entity_id"] == "script.sg_set_forced_discharge_battery_mode"

    def test_custom_discharge_config(self, mock_hass, mock_config_entry_custom):
        """Test discharge config for custom control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_custom)
        config = installer._get_discharge_automation_config()

        action = config["action"][0]
        sequence = action["choose"][0]["sequence"]

        # Should use custom service
        assert sequence[0]["service"] == "homeassistant.turn_on"
        assert sequence[0]["target"]["entity_id"] == "input_boolean.discharge_mode"


class TestChargingAutomationConfig:
    """Tests for charging automation configuration generation."""

    def test_modbus_charging_config(self, mock_hass, mock_config_entry_modbus):
        """Test charging config for Modbus control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)
        config = installer._get_charging_automation_config()

        assert config["id"] == CHARGING_AUTOMATION_ID
        assert config["alias"] == "Battery Trading: Smart Charging Control"
        assert len(config["trigger"]) == 2
        assert config["trigger"][0]["entity_id"] == (
            "binary_sensor.battery_energy_trading_cheapest_hours"
        )

        # Check Modbus-specific actions
        action = config["action"][0]
        sequence = action["choose"][0]["sequence"]
        assert sequence[1]["target"]["entity_id"] == DEFAULT_SUNGROW_MODBUS_CHARGE_POWER

    def test_scripts_charging_config(self, mock_hass, mock_config_entry_scripts):
        """Test charging config for script control type."""
        installer = AutomationInstaller(mock_hass, mock_config_entry_scripts)
        config = installer._get_charging_automation_config()

        action = config["action"][0]
        sequence = action["choose"][0]["sequence"]

        assert sequence[0]["service"] == "script.turn_on"
        assert sequence[0]["target"]["entity_id"] == "script.sg_set_forced_charge_battery_mode"


class TestAutomationStatus:
    """Tests for automation status checking."""

    def test_get_automation_status_none_installed(self, mock_hass, mock_config_entry_modbus):
        """Test status when no automations are installed."""
        mock_hass.states.get.return_value = None

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)
        status = installer.get_automation_status()

        assert len(status["installed"]) == 0
        assert len(status["missing"]) == 2
        assert DISCHARGE_AUTOMATION_ID in status["missing"]
        assert CHARGING_AUTOMATION_ID in status["missing"]

    def test_get_automation_status_one_installed(self, mock_hass, mock_config_entry_modbus):
        """Test status when one automation is installed."""

        def mock_state_get(entity_id):
            if entity_id == f"automation.{DISCHARGE_AUTOMATION_ID}":
                state = MagicMock()
                state.state = "on"
                state.attributes = {"friendly_name": "Battery Trading: Smart Discharge"}
                return state
            return None

        mock_hass.states.get = mock_state_get

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)
        status = installer.get_automation_status()

        assert len(status["installed"]) == 1
        assert len(status["missing"]) == 1
        assert status["installed"][0]["id"] == DISCHARGE_AUTOMATION_ID
        assert CHARGING_AUTOMATION_ID in status["missing"]

    def test_get_automation_status_all_installed(self, mock_hass, mock_config_entry_modbus):
        """Test status when all automations are installed."""

        def mock_state_get(entity_id):
            state = MagicMock()
            state.state = "on"
            state.attributes = {"friendly_name": "Battery Trading Automation"}
            return state

        mock_hass.states.get = mock_state_get

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)
        status = installer.get_automation_status()

        assert len(status["installed"]) == 2
        assert len(status["missing"]) == 0


class TestInstallAutomations:
    """Tests for automation installation."""

    @pytest.mark.asyncio
    async def test_install_automations_success(self, mock_hass, mock_config_entry_modbus):
        """Test successful automation installation."""
        mock_hass.data["battery_energy_trading"] = {}

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)

        # Mock service calls to succeed (simulating automation.create service)
        mock_hass.services.async_call = AsyncMock()

        created_ids = await installer.async_install_automations()

        # Should return the automation IDs
        assert len(created_ids) >= 1

    @pytest.mark.asyncio
    async def test_install_automations_returns_ids(self, mock_hass, mock_config_entry_modbus):
        """Test that installation returns automation IDs."""
        mock_hass.data["battery_energy_trading"] = {}

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)

        created_ids = await installer.async_install_automations()

        # Should return both automation IDs
        assert DISCHARGE_AUTOMATION_ID in created_ids
        assert CHARGING_AUTOMATION_ID in created_ids


class TestUninstallAutomations:
    """Tests for automation uninstallation."""

    @pytest.mark.asyncio
    async def test_uninstall_automations_none_found(self, mock_hass, mock_config_entry_modbus):
        """Test uninstall when no automations exist."""
        mock_hass.states.get.return_value = None
        mock_hass.data["battery_energy_trading"] = {}

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)

        with patch(
            "custom_components.battery_energy_trading.automation_installer.er.async_get"
        ) as mock_registry:
            mock_registry.return_value = MagicMock()
            removed_ids = await installer.async_uninstall_automations()

        assert len(removed_ids) == 0

    @pytest.mark.asyncio
    async def test_uninstall_automations_found(self, mock_hass, mock_config_entry_modbus):
        """Test uninstall when automations exist."""
        # Mock that automations exist
        state = MagicMock()
        state.state = "on"
        mock_hass.states.get.return_value = state
        mock_hass.data["battery_energy_trading"] = {}

        installer = AutomationInstaller(mock_hass, mock_config_entry_modbus)

        with patch(
            "custom_components.battery_energy_trading.automation_installer.er.async_get"
        ) as mock_registry:
            mock_entity_registry = MagicMock()
            mock_entity_registry.async_get.return_value = MagicMock()
            mock_entity_registry.async_remove = MagicMock()
            mock_registry.return_value = mock_entity_registry

            removed_ids = await installer.async_uninstall_automations()

        # Should have attempted to remove both automations
        assert len(removed_ids) == 2
        assert DISCHARGE_AUTOMATION_ID in removed_ids
        assert CHARGING_AUTOMATION_ID in removed_ids
