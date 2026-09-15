from unittest.mock import AsyncMock
import pytest
from homeassistant.exceptions import HomeAssistantError
from custom_components.zeal_dry.hvac import ClimateAdapter

@pytest.fixture
def adapter(hass):
    hass.states.async_set('climate.test', 'off', {'hvac_modes':['off','dry'], 'supported_features':1, 'min_temp':16, 'max_temp':30, 'target_temp_step':1})
    return ClimateAdapter(hass, 'climate.test')

async def test_commands_deduplicated(adapter):
    adapter._call = AsyncMock()
    await adapter.async_dry(17.7,16,20)
    await adapter.async_dry(17.7,16,20)
    assert adapter._call.call_count == 2
    adapter._call.assert_called_with('set_temperature', temperature=18)
    await adapter.async_turn_off()
    await adapter.async_turn_off()
    assert adapter._call.call_count == 3

async def test_failure_keeps_stop_ownership(adapter):
    adapter._call = AsyncMock(side_effect=HomeAssistantError('failure'))
    with pytest.raises(HomeAssistantError):
        await adapter.async_dry(18,16,20)
    assert adapter.owned
    assert adapter.last_command is None
    with pytest.raises(HomeAssistantError):
        await adapter.async_turn_off()
    assert adapter.owned
    adapter._call.side_effect = None
    await adapter.async_turn_off()
    assert not adapter.owned

async def test_unavailable_and_unsupported(adapter, hass):
    hass.states.async_set('climate.test','unavailable')
    with pytest.raises(HomeAssistantError, match='equipment_unavailable'):
        await adapter.async_dry(18,16,20)
    hass.states.async_set('climate.test','off', {'hvac_modes':['off','cool']})
    with pytest.raises(HomeAssistantError, match='dry_mode_unsupported'):
        await adapter.async_dry(18,16,20)

async def test_dry_without_temperature_support(adapter,hass):
    hass.states.async_set('climate.test','off', {'hvac_modes':['off','dry'],'supported_features':0})
    adapter._call = AsyncMock()
    await adapter.async_dry(18,16,20)
    adapter._call.assert_awaited_once_with('set_hvac_mode', hvac_mode='dry')

async def test_device_grid_and_fahrenheit(adapter,hass):
    hass.states.async_set('climate.test','off', {'hvac_modes':['off','dry'],'supported_features':1,'min_temp':60,'max_temp':86,'target_temp_step':1,'temperature_unit':'°F'})
    assert adapter.target(18,16,20) == 64
    with pytest.raises(HomeAssistantError,match='invalid_device_temperature_limits'):
        adapter.target(5,0,5)
