from unittest.mock import AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.zeal_dry import async_setup_entry, async_unload_entry
from custom_components.zeal_dry.const import DOMAIN

async def test_setup_and_unload_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN,data={'zone_name':'Test','control_mode':'monitor_only'},unique_id='test')
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries,'async_forward_entry_setups',AsyncMock()), patch.object(hass.config_entries,'async_unload_platforms',AsyncMock(return_value=True)):
        assert await async_setup_entry(hass,entry)
        assert entry.entry_id in hass.data[DOMAIN]['controllers']
        assert await async_unload_entry(hass,entry)
        assert entry.entry_id not in hass.data[DOMAIN]['controllers']
