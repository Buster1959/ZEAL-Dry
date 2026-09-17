"""Tests for Block 2 sensor observation."""

from __future__ import annotations

from homeassistant.const import UnitOfTemperature

from custom_components.zeal_dry.controller import ZealDryController


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
