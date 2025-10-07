"""Tests for __init__.py integration setup."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from homeassistant.const import Platform
from homeassistant.core import ServiceCall

from custom_components.battery_energy_trading import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
    DOMAIN,
    PLATFORMS,
    SERVICE_SYNC_SUNGROW_PARAMS,
)


@pytest.mark.asyncio
async def test_async_setup(mock_hass):
    """Test async_setup registers service."""
    config = {}

    result = await async_setup(mock_hass, config)

    assert result is True
    # Verify domain data initialized
    assert DOMAIN in mock_hass.data
    # Verify service registered
    assert mock_hass.services.async_register.called


@pytest.mark.asyncio
@patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
async def test_async_setup_entry(mock_coordinator_class, mock_hass_with_nordpool, mock_config_entry):
    """Test async_setup_entry forwards platforms."""
    # Mock coordinator instance
    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator_class.return_value = mock_coordinator

    mock_hass_with_nordpool.config_entries.async_forward_entry_setups = AsyncMock()

    result = await async_setup_entry(mock_hass_with_nordpool, mock_config_entry)

    assert result is True
    # Verify domain data stored
    assert DOMAIN in mock_hass_with_nordpool.data
    assert mock_config_entry.entry_id in mock_hass_with_nordpool.data[DOMAIN]
    assert mock_hass_with_nordpool.data[DOMAIN][mock_config_entry.entry_id]["data"] == mock_config_entry.data
    assert mock_hass_with_nordpool.data[DOMAIN][mock_config_entry.entry_id]["options"] == mock_config_entry.options

    # Verify platforms forwarded
    mock_hass_with_nordpool.config_entries.async_forward_entry_setups.assert_called_once_with(
        mock_config_entry, PLATFORMS
    )


@pytest.mark.asyncio
@patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
async def test_async_setup_entry_initializes_domain_data(
    mock_coordinator_class, mock_hass_with_nordpool, mock_config_entry
):
    """Test async_setup_entry initializes domain data if not present."""
    # Mock coordinator instance
    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator_class.return_value = mock_coordinator

    # Ensure domain data not already set
    mock_hass_with_nordpool.data = {}
    mock_hass_with_nordpool.config_entries.async_forward_entry_setups = AsyncMock()

    result = await async_setup_entry(mock_hass_with_nordpool, mock_config_entry)

    assert result is True
    assert DOMAIN in mock_hass_with_nordpool.data


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test async_unload_entry unloads platforms."""
    # Setup initial data
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {"data": {}, "options": {}}}
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    # Verify platforms unloaded
    mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
        mock_config_entry, PLATFORMS
    )
    # Verify domain data removed
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_failure(mock_hass, mock_config_entry):
    """Test async_unload_entry when platform unload fails."""
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {"data": {}, "options": {}}}
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is False
    # Verify domain data NOT removed on failure
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]


class TestPlatforms:
    """Test platform configuration."""

    def test_platforms_defined(self):
        """Test all platforms are defined."""
        assert Platform.SENSOR in PLATFORMS
        assert Platform.BINARY_SENSOR in PLATFORMS
        assert Platform.NUMBER in PLATFORMS
        assert Platform.SWITCH in PLATFORMS
        assert len(PLATFORMS) == 4


class TestSyncSungrowParamsService:
    """Test sync_sungrow_parameters service."""

    @pytest.mark.asyncio
    async def test_service_registration(self, mock_hass):
        """Test service is registered during setup."""
        config = {}
        await async_setup(mock_hass, config)

        # Verify service registered with correct name
        mock_hass.services.async_register.assert_called_once()
        call_args = mock_hass.services.async_register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == SERVICE_SYNC_SUNGROW_PARAMS

    @pytest.mark.asyncio
    async def test_handle_sync_with_entry_id(self, mock_hass, mock_config_entry_sungrow):
        """Test service call with explicit entry_id."""
        config = {}
        await async_setup(mock_hass, config)

        # Get the registered service handler
        service_handler = mock_hass.services.async_register.call_args[0][2]

        # Setup mocks
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_config_entry_sungrow)
        mock_hass.config_entries.async_update_entry = Mock()

        # Mock SungrowHelper
        with patch("custom_components.battery_energy_trading.SungrowHelper") as mock_helper_class:
            mock_helper = mock_helper_class.return_value
            mock_helper.async_get_auto_configuration = AsyncMock(
                return_value={
                    "recommended_charge_rate": 10.0,
                    "recommended_discharge_rate": 10.0,
                    "inverter_model": "SH10RT",
                }
            )

            # Call service
            call = ServiceCall(
                domain=DOMAIN,
                service=SERVICE_SYNC_SUNGROW_PARAMS,
                data={"entry_id": "test_sungrow_entry"},
            )
            await service_handler(call)

            # Verify entry was updated
            mock_hass.config_entries.async_update_entry.assert_called_once()
            updated_entry = mock_hass.config_entries.async_update_entry.call_args[0][0]
            updated_options = mock_hass.config_entries.async_update_entry.call_args[1]["options"]

            assert updated_entry == mock_config_entry_sungrow
            assert updated_options["charge_rate"] == 10.0
            assert updated_options["discharge_rate"] == 10.0
            assert updated_options["inverter_model"] == "SH10RT"

    @pytest.mark.asyncio
    async def test_handle_sync_without_entry_id_finds_auto_detected(
        self, mock_hass, mock_config_entry_sungrow
    ):
        """Test service call without entry_id finds auto-detected entry."""
        config = {}
        await async_setup(mock_hass, config)

        service_handler = mock_hass.services.async_register.call_args[0][2]

        # Mock config entries list with auto-detected entry
        mock_hass.config_entries.async_entries = Mock(return_value=[mock_config_entry_sungrow])
        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_config_entry_sungrow)
        mock_hass.config_entries.async_update_entry = Mock()

        with patch("custom_components.battery_energy_trading.SungrowHelper") as mock_helper_class:
            mock_helper = mock_helper_class.return_value
            mock_helper.async_get_auto_configuration = AsyncMock(
                return_value={
                    "recommended_charge_rate": 8.0,
                    "recommended_discharge_rate": 8.0,
                    "inverter_model": "SH8.0RT",
                }
            )

            # Call service without entry_id
            call = ServiceCall(
                domain=DOMAIN,
                service=SERVICE_SYNC_SUNGROW_PARAMS,
                data={},
            )
            await service_handler(call)

            # Should have found and updated the auto-detected entry
            mock_hass.config_entries.async_update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_sync_no_auto_detected_entry(self, mock_hass, mock_config_entry):
        """Test service call when no auto-detected entry exists."""
        config = {}
        await async_setup(mock_hass, config)

        service_handler = mock_hass.services.async_register.call_args[0][2]

        # Mock config entries with non-auto-detected entry
        mock_config_entry.options = {}  # No auto_detected flag
        mock_hass.config_entries.async_entries = Mock(return_value=[mock_config_entry])

        # Call service without entry_id
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SYNC_SUNGROW_PARAMS,
            data={},
        )
        await service_handler(call)

        # Should not try to update entry (logs error instead)
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_handle_sync_entry_not_found(self, mock_hass):
        """Test service call when specified entry_id not found."""
        config = {}
        await async_setup(mock_hass, config)

        service_handler = mock_hass.services.async_register.call_args[0][2]

        # Mock entry not found
        mock_hass.config_entries.async_get_entry = Mock(return_value=None)

        # Call service with non-existent entry_id
        call = ServiceCall(
            domain=DOMAIN,
            service=SERVICE_SYNC_SUNGROW_PARAMS,
            data={"entry_id": "non_existent"},
        )
        await service_handler(call)

        # Should log error but not raise exception

    @pytest.mark.asyncio
    async def test_handle_sync_preserves_other_options(
        self, mock_hass, mock_config_entry_sungrow
    ):
        """Test service call preserves other options."""
        config = {}
        await async_setup(mock_hass, config)

        service_handler = mock_hass.services.async_register.call_args[0][2]

        # Add extra option to entry
        mock_config_entry_sungrow.options = {
            **mock_config_entry_sungrow.options,
            "custom_option": "custom_value",
        }

        mock_hass.config_entries.async_get_entry = Mock(return_value=mock_config_entry_sungrow)
        mock_hass.config_entries.async_update_entry = Mock()

        with patch("custom_components.battery_energy_trading.SungrowHelper") as mock_helper_class:
            mock_helper = mock_helper_class.return_value
            mock_helper.async_get_auto_configuration = AsyncMock(
                return_value={
                    "recommended_charge_rate": 5.0,
                    "recommended_discharge_rate": 5.0,
                    "inverter_model": "SH5.0RT",
                }
            )

            call = ServiceCall(
                domain=DOMAIN,
                service=SERVICE_SYNC_SUNGROW_PARAMS,
                data={"entry_id": "test_sungrow_entry"},
            )
            await service_handler(call)

            # Verify custom_option was preserved
            updated_options = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
            assert updated_options["custom_option"] == "custom_value"
            assert updated_options["charge_rate"] == 5.0


class TestDomainData:
    """Test domain data management."""

    @pytest.mark.asyncio
    @patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
    async def test_domain_data_structure(
        self, mock_coordinator_class, mock_hass_with_nordpool, mock_config_entry
    ):
        """Test domain data has correct structure."""
        # Mock coordinator instance
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass_with_nordpool.config_entries.async_forward_entry_setups = AsyncMock()

        await async_setup_entry(mock_hass_with_nordpool, mock_config_entry)

        entry_data = mock_hass_with_nordpool.data[DOMAIN][mock_config_entry.entry_id]
        assert "data" in entry_data
        assert "options" in entry_data
        assert entry_data["data"] == mock_config_entry.data
        assert entry_data["options"] == mock_config_entry.options

    @pytest.mark.asyncio
    @patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
    async def test_multiple_entries(
        self,
        mock_coordinator_class,
        mock_hass_with_nordpool_and_sungrow,
        mock_config_entry,
        mock_config_entry_sungrow,
    ):
        """Test multiple config entries are stored separately."""
        # Mock coordinator instance
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass_with_nordpool_and_sungrow.config_entries.async_forward_entry_setups = AsyncMock()

        await async_setup_entry(mock_hass_with_nordpool_and_sungrow, mock_config_entry)
        await async_setup_entry(mock_hass_with_nordpool_and_sungrow, mock_config_entry_sungrow)

        # Both entries should be in domain data
        assert mock_config_entry.entry_id in mock_hass_with_nordpool_and_sungrow.data[DOMAIN]
        assert mock_config_entry_sungrow.entry_id in mock_hass_with_nordpool_and_sungrow.data[DOMAIN]

        # Verify data is separate
        assert (
            mock_hass_with_nordpool_and_sungrow.data[DOMAIN][mock_config_entry.entry_id]["data"]
            != mock_hass_with_nordpool_and_sungrow.data[DOMAIN][mock_config_entry_sungrow.entry_id]["data"]
        )


class TestIntegrationLifecycle:
    """Test integration setup and teardown lifecycle."""

    @pytest.mark.asyncio
    @patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
    async def test_full_lifecycle(
        self, mock_coordinator_class, mock_hass_with_nordpool, mock_config_entry
    ):
        """Test full setup and unload cycle."""
        # Mock coordinator instance
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass_with_nordpool.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass_with_nordpool.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        # Setup
        setup_result = await async_setup_entry(mock_hass_with_nordpool, mock_config_entry)
        assert setup_result is True
        assert mock_config_entry.entry_id in mock_hass_with_nordpool.data[DOMAIN]

        # Unload
        unload_result = await async_unload_entry(mock_hass_with_nordpool, mock_config_entry)
        assert unload_result is True
        assert mock_config_entry.entry_id not in mock_hass_with_nordpool.data[DOMAIN]

    @pytest.mark.asyncio
    @patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator")
    async def test_setup_without_prior_async_setup(
        self, mock_coordinator_class, mock_hass_with_nordpool, mock_config_entry
    ):
        """Test async_setup_entry works without prior async_setup call."""
        # Mock coordinator instance
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        # Don't call async_setup first
        mock_hass_with_nordpool.data = {}  # Empty hass data
        mock_hass_with_nordpool.config_entries.async_forward_entry_setups = AsyncMock()

        result = await async_setup_entry(mock_hass_with_nordpool, mock_config_entry)

        assert result is True
        assert DOMAIN in mock_hass_with_nordpool.data
        assert mock_config_entry.entry_id in mock_hass_with_nordpool.data[DOMAIN]
