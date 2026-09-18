"""Tests for Block 2 sensor observation."""

from __future__ import annotations

import pytest

from homeassistant.const import UnitOfTemperature
from homeassistant.util import dt as dt_util

from custom_components.zeal_dry.const import (
    SENSOR_CONTROL_FRESHNESS_SECONDS,
    SENSOR_OFFLINE_DEBOUNCE_SECONDS,
    SENSOR_STALE_THRESHOLD_SECONDS,
)
from custom_components.zeal_dry.controller import ZealDryController
from custom_components.zeal_dry.environment import EnvironmentalInputError


async def test_controller_builds_environmental_reading(hass):
    """Valid indoor sensors should produce a reading without any control action."""
    hass.states.async_set(
        "sensor.room_temperature",
        "17.2",
        {"unit_of_measurement": UnitOfTemperature.CELSIUS},
    )
    hass.states.async_set("sensor.room_humidity", "73")

    controller = ZealDryController(
        hass=hass,
        entry_id="test",
        zone_name="Test Zone",
        temperature_entity="sensor.room_temperature",
        humidity_entity="sensor.room_humidity",
    )
    await controller.async_start()

    assert controller.input_error is None
    assert controller.environmental_reading is not None
    assert controller.environmental_reading.temperature_c == 17.2
    assert controller.environmental_reading.relative_humidity == 73.0

    await controller.async_stop()


async def test_unavailable_input_clears_reading(hass):
    """Unavailable inputs must invalidate the environmental reading safely."""
    hass.states.async_set(
        "sensor.room_temperature",
        "17.2",
        {"unit_of_measurement": UnitOfTemperature.CELSIUS},
    )
    hass.states.async_set("sensor.room_humidity", "unavailable")

    controller = ZealDryController(
        hass=hass,
        entry_id="test",
        zone_name="Test Zone",
        temperature_entity="sensor.room_temperature",
        humidity_entity="sensor.room_humidity",
    )
    await controller.async_start()

    assert controller.environmental_reading is None
    assert controller.input_error == "humidity entity is unavailable"

    await controller.async_stop()


async def test_quiet_sensor_uses_heat_availability_period(hass, freezer):
    """A quiet battery-style reading is not falsely unavailable after 30 minutes."""
    hass.states.async_set("sensor.room_humidity", "63")
    state = hass.states["sensor.room_humidity"]

    freezer.tick(SENSOR_STALE_THRESHOLD_SECONDS - 1)
    assert ZealDryController._numeric_state(state, "humidity") == 63.0

    freezer.tick(2)
    with pytest.raises(EnvironmentalInputError, match="humidity sensor is stale"):
        ZealDryController._numeric_state(state, "humidity")


async def test_old_reading_cannot_authorise_dry_control(hass, freezer):
    """Retain the 30-minute energy safeguard separately from sensor health."""
    hass.states.async_set("sensor.room_temperature", "18")
    hass.states.async_set("sensor.room_humidity", "70")
    controller = ZealDryController(
        hass=hass,
        entry_id="test",
        zone_name="Test Zone",
        temperature_entity="sensor.room_temperature",
        humidity_entity="sensor.room_humidity",
    )

    freezer.tick(SENSOR_CONTROL_FRESHNESS_SECONDS + 1)

    assert controller._numeric_state(
        hass.states["sensor.room_humidity"], "humidity"
    ) == 70
    assert controller._inputs_fresh_for_control(dt_util.utcnow()) is False


async def test_explicit_power_source_identifies_mains_sensor(hass):
    """Use HA power metadata before deciding whether an active probe is safe."""
    hass.states.async_set(
        "sensor.room_temperature", "18", {"power_source": "mains"}
    )
    controller = ZealDryController(hass=hass, entry_id="test", zone_name="Test")

    assert controller._sensor_power_source("sensor.room_temperature") == "mains"


async def test_sensor_warning_is_debounced_once_and_dismissed(hass, freezer):
    """Match ZEAL-Heat's five-minute warning and automatic recovery dismissal."""
    creates: list[dict] = []
    dismisses: list[dict] = []

    async def create(call):
        creates.append(dict(call.data))

    async def dismiss(call):
        dismisses.append(dict(call.data))

    hass.services.async_register("persistent_notification", "create", create)
    hass.services.async_register("persistent_notification", "dismiss", dismiss)
    hass.states.async_set("sensor.room_temperature", "18")
    hass.states.async_set("sensor.room_humidity", "unavailable")
    controller = ZealDryController(
        hass=hass,
        entry_id="test",
        zone_name="Test Zone",
        temperature_entity="sensor.room_temperature",
        humidity_entity="sensor.room_humidity",
    )

    await controller._async_check_sensor_health(dt_util.utcnow())
    assert creates == []
    freezer.tick(SENSOR_OFFLINE_DEBOUNCE_SECONDS + 1)
    await controller._async_check_sensor_health(dt_util.utcnow())
    await controller._async_check_sensor_health(dt_util.utcnow())
    assert len(creates) == 1
    assert "sensor.room_humidity" in creates[0]["message"]

    hass.states.async_set("sensor.room_humidity", "62")
    await controller._async_check_sensor_health(dt_util.utcnow())
    assert len(dismisses) == 1


async def test_weather_entity_adds_external_context_without_changing_demand(hass):
    """Evaluate outdoor dew point separately from the indoor control reading."""
    hass.states.async_set(
        "sensor.room_temperature",
        "24",
        {"unit_of_measurement": UnitOfTemperature.CELSIUS},
    )
    hass.states.async_set("sensor.room_humidity", "70")
    hass.states.async_set(
        "weather.home",
        "rainy",
        {
            "temperature": 22.4,
            "temperature_unit": UnitOfTemperature.CELSIUS,
            "humidity": 77,
        },
    )

    controller = ZealDryController(
        hass=hass,
        entry_id="test",
        zone_name="Test Zone",
        temperature_entity="sensor.room_temperature",
        humidity_entity="sensor.room_humidity",
        weather_entity="weather.home",
    )
    await controller.async_start()

    assert controller.decision.reason == "dew_point_critical"
    assert controller.external_environmental_reading is not None
    assert controller.external_environmental_reading.temperature_c == 22.4
    assert controller.external_environmental_reading.relative_humidity == 77
    assert controller.external_input_error is None

    await controller.async_stop()
