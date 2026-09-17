from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.zeal_dry.controller import ZealDryController


async def test_live_restart_failure_and_stop_retry(hass):
    hass.states.async_set("sensor.t", "25")
    hass.states.async_set("sensor.h", "80")
    hass.states.async_set(
        "climate.ac",
        "off",
        {
            "hvac_modes": ["off", "dry"],
            "supported_features": 1,
            "min_temp": 16,
            "max_temp": 30,
        },
    )
    c = ZealDryController(
        hass,
        "live",
        "Live",
        temperature_entity="sensor.t",
        humidity_entity="sensor.h",
        climate_entity="climate.ac",
        control_mode="climate",
    )
    await c.async_start()
    assert c.state_snapshot.state != "drying"
    c.actuator._call = AsyncMock(side_effect=HomeAssistantError("failed"))
    c.state_snapshot = replace(
        c.state_snapshot, drying_stopped_at=dt_util.utcnow() - timedelta(minutes=11)
    )
    await c.async_refresh()
    assert c.state_snapshot.state == "fault"
    assert c.actuator.owned
    saved = await c._store.async_load()
    assert saved["owned"]
    c.actuator._call.side_effect = None
    await c.async_refresh()
    assert not c.actuator.owned
    assert c.state_snapshot.state == "fault"
    await c.async_stop()


async def test_storage_failure_stops_active_dummy(hass):
    c = ZealDryController(hass, "disk", "Test", control_mode="dummy_acu")
    await c.async_start()
    await c.async_set_test_humidity(90)
    assert c.actuator.is_on
    c._store.async_save = AsyncMock(side_effect=OSError("disk full"))
    await c.async_refresh()
    assert c.state_snapshot.state == "fault"
    assert not c.actuator.is_on
    c._store.async_save.side_effect = None
    await c.async_stop()


async def test_live_mode_feedback_grace(hass):
    hass.states.async_set("sensor.t", "25")
    hass.states.async_set("sensor.h", "80")
    attrs = {
        "hvac_modes": ["off", "dry"],
        "supported_features": 1,
        "min_temp": 16,
        "max_temp": 30,
    }
    hass.states.async_set("climate.ac", "off", attrs)
    c = ZealDryController(
        hass,
        "grace",
        "Live",
        temperature_entity="sensor.t",
        humidity_entity="sensor.h",
        climate_entity="climate.ac",
        control_mode="climate",
    )
    await c.async_start()
    c.actuator._call = AsyncMock()
    c.state_snapshot = replace(
        c.state_snapshot, drying_stopped_at=dt_util.utcnow() - timedelta(minutes=11)
    )
    await c.async_refresh()
    assert c.state_snapshot.state == "drying"
    await c.async_refresh()
    assert c.state_snapshot.state == "drying"
    assert c.actuator._call.call_count == 2
    c.actuator.requested_at -= timedelta(minutes=2)
    await c.async_refresh()
    assert c.state_snapshot.state == "fault"
    assert not c.actuator.owned
    await c.async_stop()


async def test_startup_stops_observed_dry_without_saved_ownership(hass):
    from unittest.mock import patch

    hass.states.async_set("sensor.t", "25")
    hass.states.async_set("sensor.h", "80")
    hass.states.async_set("climate.ac", "dry", {"hvac_modes": ["off", "dry"]})
    c = ZealDryController(
        hass,
        "startup",
        "Live",
        temperature_entity="sensor.t",
        humidity_entity="sensor.h",
        climate_entity="climate.ac",
        control_mode="climate",
    )
    with patch(
        "custom_components.zeal_dry.hvac.ClimateAdapter._call", new_callable=AsyncMock
    ) as call:
        await c.async_start()
        call.assert_awaited_once_with("set_hvac_mode", hvac_mode="off")
        assert c.state_snapshot.state != "drying"
        await c.async_stop()


async def test_live_cycle_through_home_assistant_services(hass):
    from homeassistant.core import callback

    attrs = {
        "hvac_modes": ["off", "dry"],
        "supported_features": 1,
        "min_temp": 16,
        "max_temp": 30,
        "target_temp_step": 1,
    }
    hass.states.async_set("sensor.t", "25")
    hass.states.async_set("sensor.h", "80")
    hass.states.async_set("climate.ac", "off", attrs)
    calls = []

    @callback
    def command(call):
        calls.append((call.service, dict(call.data)))
        if call.service == "set_hvac_mode":
            hass.states.async_set("climate.ac", call.data["hvac_mode"], attrs)

    hass.services.async_register("climate", "set_hvac_mode", command)
    hass.services.async_register("climate", "set_temperature", command)
    c = ZealDryController(
        hass,
        "cycle",
        "Live",
        temperature_entity="sensor.t",
        humidity_entity="sensor.h",
        climate_entity="climate.ac",
        control_mode="climate",
    )
    await c.async_start()
    c.state_snapshot = replace(
        c.state_snapshot, drying_stopped_at=dt_util.utcnow() - timedelta(minutes=11)
    )
    await c.async_refresh()
    assert hass.states.get("climate.ac").state == "dry"
    assert calls[-1] == (
        "set_temperature",
        {"entity_id": "climate.ac", "temperature": 20},
    )
    await c.async_refresh()
    assert len(calls) == 2
    c.state_snapshot = replace(
        c.state_snapshot, drying_started_at=dt_util.utcnow() - timedelta(minutes=21)
    )
    hass.states.async_set("sensor.t", "18")
    hass.states.async_set("sensor.h", "50")
    await c.async_refresh()
    assert c.state_snapshot.state == "recovery"
    assert hass.states.get("climate.ac").state == "off"
    assert not c.actuator.owned
    await c.async_stop()


async def test_live_cycle_controls_multiple_acus(hass):
    """Start and stop every ACU selected for the same protected zone."""
    from homeassistant.core import callback

    attrs = {
        "hvac_modes": ["off", "dry"],
        "supported_features": 1,
        "min_temp": 16,
        "max_temp": 30,
    }
    hass.states.async_set("sensor.t", "25")
    hass.states.async_set("sensor.h", "80")
    for entity_id in ("climate.east", "climate.west"):
        hass.states.async_set(entity_id, "off", attrs)
    calls = []

    @callback
    def command(call):
        calls.append((call.service, dict(call.data)))
        if call.service == "set_hvac_mode":
            hass.states.async_set(
                call.data["entity_id"], call.data["hvac_mode"], attrs
            )

    hass.services.async_register("climate", "set_hvac_mode", command)
    hass.services.async_register("climate", "set_temperature", command)
    controller = ZealDryController(
        hass,
        "multi",
        "Multi",
        temperature_entity="sensor.t",
        humidity_entity="sensor.h",
        climate_entities=["climate.east", "climate.west"],
        control_mode="climate",
    )
    await controller.async_start()
    controller.state_snapshot = replace(
        controller.state_snapshot,
        drying_stopped_at=dt_util.utcnow() - timedelta(minutes=11),
    )
    await controller.async_refresh()
    assert hass.states.get("climate.east").state == "dry"
    assert hass.states.get("climate.west").state == "dry"
    assert {data["entity_id"] for _, data in calls} == {
        "climate.east",
        "climate.west",
    }
    await controller.async_stop()
    assert hass.states.get("climate.east").state == "off"
    assert hass.states.get("climate.west").state == "off"
