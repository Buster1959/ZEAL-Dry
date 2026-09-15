from unittest.mock import AsyncMock
from datetime import timedelta
from dataclasses import replace
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from custom_components.zeal_dry.controller import ZealDryController

async def test_live_restart_failure_and_stop_retry(hass):
    hass.states.async_set('sensor.t','25')
    hass.states.async_set('sensor.h','80')
    hass.states.async_set('climate.ac','off',{'hvac_modes':['off','dry'],'supported_features':1,'min_temp':16,'max_temp':30})
    c = ZealDryController(hass,'live','Live',temperature_entity='sensor.t',humidity_entity='sensor.h',climate_entity='climate.ac',control_mode='climate')
    await c.async_start()
    assert c.state_snapshot.state != 'drying'
    c.actuator._call = AsyncMock(side_effect=HomeAssistantError('failed'))
    c.state_snapshot = replace(c.state_snapshot,drying_stopped_at=dt_util.utcnow()-timedelta(minutes=11))
    await c.async_refresh()
    assert c.state_snapshot.state == 'fault'
    assert c.actuator.owned
    saved = await c._store.async_load()
    assert saved['owned']
    c.actuator._call.side_effect = None
    await c.async_refresh()
    assert not c.actuator.owned
    assert c.state_snapshot.state == 'fault'
    await c.async_stop()
