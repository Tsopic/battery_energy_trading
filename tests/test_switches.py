"""Tests for switch platform."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock

from custom_components.battery_energy_trading.switch import (
    async_setup_entry,
    BatteryTradingSwitch,
)
from custom_components.battery_energy_trading.const import (
    DOMAIN,
    VERSION,
    SWITCH_ENABLE_FORCED_CHARGING,
    SWITCH_ENABLE_FORCED_DISCHARGE,
    SWITCH_ENABLE_EXPORT_MANAGEMENT,
    SWITCH_ENABLE_MULTIDAY_OPTIMIZATION,
)


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test switch platform setup."""
    async_add_entities = Mock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify switches were added
    assert async_add_entities.called
    switches = async_add_entities.call_args[0][0]
    assert len(switches) == 4
    for switch in switches:
        assert isinstance(switch, BatteryTradingSwitch)


class TestBatteryTradingSwitch:
    """Test BatteryTradingSwitch entity."""

    @pytest.fixture
    def switch_entity(self, mock_config_entry):
        """Create a switch entity for testing."""
        return BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="test_switch",
            name="Test Switch",
            icon="mdi:test",
            description="Test switch description",
            default_state=True,
        )

    def test_init(self, switch_entity, mock_config_entry):
        """Test switch initialization."""
        assert switch_entity._entry == mock_config_entry
        assert switch_entity._switch_type == "test_switch"
        assert switch_entity._attr_name == "Test Switch"
        assert (
            switch_entity._attr_unique_id
            == f"{DOMAIN}_{mock_config_entry.entry_id}_test_switch"
        )
        assert switch_entity._attr_suggested_object_id == f"{DOMAIN}_test_switch"
        assert switch_entity._attr_icon == "mdi:test"
        assert switch_entity._description == "Test switch description"
        assert switch_entity._attr_is_on is True
        assert switch_entity._attr_has_entity_name is True

    def test_device_info(self, switch_entity, mock_config_entry):
        """Test device info generation."""
        device_info = switch_entity._attr_device_info
        assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
        assert device_info["name"] == "Battery Energy Trading"
        assert device_info["manufacturer"] == "Battery Energy Trading"
        assert device_info["model"] == "Energy Optimizer"
        assert device_info["sw_version"] == VERSION

    def test_extra_state_attributes(self, switch_entity):
        """Test extra state attributes."""
        attrs = switch_entity.extra_state_attributes
        assert attrs["description"] == "Test switch description"
        assert attrs["switch_type"] == "test_switch"

    @pytest.mark.asyncio
    async def test_async_turn_on(self, switch_entity):
        """Test turning switch on."""
        switch_entity.async_write_ha_state = Mock()
        switch_entity._attr_is_on = False

        await switch_entity.async_turn_on()

        assert switch_entity._attr_is_on is True
        switch_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_turn_off(self, switch_entity):
        """Test turning switch off."""
        switch_entity.async_write_ha_state = Mock()
        switch_entity._attr_is_on = True

        await switch_entity.async_turn_off()

        assert switch_entity._attr_is_on is False
        switch_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_added_to_hass_no_previous_state(self, switch_entity):
        """Test entity added with no previous state."""
        switch_entity.async_get_last_state = AsyncMock(return_value=None)

        await switch_entity.async_added_to_hass()

        # Should keep default state (True)
        assert switch_entity._attr_is_on is True

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restore_on(self, switch_entity):
        """Test entity added with previous 'on' state."""
        mock_last_state = MagicMock()
        mock_last_state.state = "on"
        switch_entity.async_get_last_state = AsyncMock(return_value=mock_last_state)
        switch_entity._attr_is_on = False  # Different from saved state

        await switch_entity.async_added_to_hass()

        # Should restore to 'on'
        assert switch_entity._attr_is_on is True

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restore_off(self, switch_entity):
        """Test entity added with previous 'off' state."""
        mock_last_state = MagicMock()
        mock_last_state.state = "off"
        switch_entity.async_get_last_state = AsyncMock(return_value=mock_last_state)
        switch_entity._attr_is_on = True  # Different from saved state

        await switch_entity.async_added_to_hass()

        # Should restore to 'off'
        assert switch_entity._attr_is_on is False


class TestForcedChargingSwitch:
    """Test forced charging switch specific configuration."""

    def test_forced_charging_defaults(self, mock_config_entry):
        """Test forced charging switch defaults."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type=SWITCH_ENABLE_FORCED_CHARGING,
            name="Enable Forced Charging",
            icon="mdi:battery-charging",
            description="Allow automatic battery charging during cheap price periods",
            default_state=False,
        )

        assert switch._switch_type == SWITCH_ENABLE_FORCED_CHARGING
        assert switch._attr_name == "Enable Forced Charging"
        assert switch._attr_icon == "mdi:battery-charging"
        assert switch._attr_is_on is False  # Default: disabled for solar-only
        assert "charging" in switch._description.lower()


class TestForcedDischargeSwitch:
    """Test forced discharge switch specific configuration."""

    def test_forced_discharge_defaults(self, mock_config_entry):
        """Test forced discharge switch defaults."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type=SWITCH_ENABLE_FORCED_DISCHARGE,
            name="Enable Forced Discharge",
            icon="mdi:battery-arrow-up",
            description="Allow automatic battery discharge during high price periods",
            default_state=True,
        )

        assert switch._switch_type == SWITCH_ENABLE_FORCED_DISCHARGE
        assert switch._attr_name == "Enable Forced Discharge"
        assert switch._attr_icon == "mdi:battery-arrow-up"
        assert switch._attr_is_on is True  # Default: enabled
        assert "discharge" in switch._description.lower()


class TestExportManagementSwitch:
    """Test export management switch specific configuration."""

    def test_export_management_defaults(self, mock_config_entry):
        """Test export management switch defaults."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type=SWITCH_ENABLE_EXPORT_MANAGEMENT,
            name="Enable Export Management",
            icon="mdi:transmission-tower-export",
            description="Manage grid export based on price thresholds",
            default_state=True,
        )

        assert switch._switch_type == SWITCH_ENABLE_EXPORT_MANAGEMENT
        assert switch._attr_name == "Enable Export Management"
        assert switch._attr_icon == "mdi:transmission-tower-export"
        assert switch._attr_is_on is True  # Default: enabled
        assert "export" in switch._description.lower()


class TestMultidayOptimizationSwitch:
    """Test multi-day optimization switch specific configuration."""

    def test_multiday_optimization_defaults(self, mock_config_entry):
        """Test multi-day optimization switch defaults."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type=SWITCH_ENABLE_MULTIDAY_OPTIMIZATION,
            name="Enable Multi-Day Optimization (Experimental)",
            icon="mdi:calendar-multiple",
            description="Optimize across today + tomorrow using price forecasts and solar estimates",
            default_state=False,
        )

        assert switch._switch_type == SWITCH_ENABLE_MULTIDAY_OPTIMIZATION
        assert switch._attr_name == "Enable Multi-Day Optimization (Experimental)"
        assert switch._attr_icon == "mdi:calendar-multiple"
        assert switch._attr_is_on is False  # Default: disabled - experimental
        assert "optimize" in switch._description.lower()


class TestSwitchStateManagement:
    """Test switch state management scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_toggles(self, mock_config_entry):
        """Test multiple on/off toggles."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="test_switch",
            name="Test",
            icon="mdi:test",
            description="Test",
            default_state=False,
        )
        switch.async_write_ha_state = Mock()

        # Initial state: off
        assert switch._attr_is_on is False

        # Turn on
        await switch.async_turn_on()
        assert switch._attr_is_on is True

        # Turn off
        await switch.async_turn_off()
        assert switch._attr_is_on is False

        # Turn on again
        await switch.async_turn_on()
        assert switch._attr_is_on is True

        # Should have written state 3 times
        assert switch.async_write_ha_state.call_count == 3

    @pytest.mark.asyncio
    async def test_redundant_turn_on(self, mock_config_entry):
        """Test turning on when already on."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="test_switch",
            name="Test",
            icon="mdi:test",
            description="Test",
            default_state=True,
        )
        switch.async_write_ha_state = Mock()

        # Already on
        assert switch._attr_is_on is True

        # Turn on again
        await switch.async_turn_on()
        assert switch._attr_is_on is True

        # Should still write state (idempotent)
        switch.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_redundant_turn_off(self, mock_config_entry):
        """Test turning off when already off."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="test_switch",
            name="Test",
            icon="mdi:test",
            description="Test",
            default_state=False,
        )
        switch.async_write_ha_state = Mock()

        # Already off
        assert switch._attr_is_on is False

        # Turn off again
        await switch.async_turn_off()
        assert switch._attr_is_on is False

        # Should still write state (idempotent)
        switch.async_write_ha_state.assert_called_once()


class TestSwitchUniqueIDs:
    """Test switch unique ID generation."""

    def test_unique_id_format(self, mock_config_entry):
        """Test unique ID follows expected format."""
        switch = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="custom_switch",
            name="Custom",
            icon="mdi:test",
            description="Test",
            default_state=False,
        )

        unique_id = switch._attr_unique_id
        assert unique_id.startswith(DOMAIN)
        assert "_test_entry_id_" in unique_id
        assert unique_id.endswith("custom_switch")

    def test_unique_ids_differ(self, mock_config_entry):
        """Test different switches have different unique IDs."""
        switch1 = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="switch_a",
            name="A",
            icon="mdi:test",
            description="Test",
            default_state=False,
        )

        switch2 = BatteryTradingSwitch(
            entry=mock_config_entry,
            switch_type="switch_b",
            name="B",
            icon="mdi:test",
            description="Test",
            default_state=False,
        )

        assert switch1._attr_unique_id != switch2._attr_unique_id
