"""Exercise the actual multi-step configuration flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries

from custom_components.zeal_dry.const import DOMAIN


async def start(hass, mode):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"zone_name": "Test", "control_mode": mode}
    )


@pytest.mark.parametrize("mode", ["monitor_only", "climate"])
async def test_sensor_and_climate_flow(hass, mode):
    hass.states.async_set("sensor.temp", "18")
    hass.states.async_set("sensor.rh", "60")
    hass.states.async_set("climate.test", "off", {"hvac_modes": ["dry", "off"]})
    result = await start(hass, mode)
    assert result["step_id"] == "sensors"
    with patch(
        "custom_components.zeal_dry.async_setup_entry", AsyncMock(return_value=True)
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"temperature_entity": "sensor.temp", "humidity_entity": "sensor.rh"},
        )
        if mode == "climate":
            assert result["step_id"] == "climate"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"climate_entities": ["climate.test"]}
            )
        assert result["type"] == "create_entry"
        assert result["data"]["control_mode"] == mode
        if mode == "climate":
            assert result["data"]["climate_entities"] == ["climate.test"]
        await hass.async_block_till_done()


async def test_missing_entity_is_rejected(hass):
    result = await start(hass, "monitor_only")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "temperature_entity": "sensor.missing",
            "humidity_entity": "sensor.missing_rh",
        },
    )
    assert result["errors"]["temperature_entity"] == "entity_not_found"


async def test_live_flow_accepts_multiple_climate_entities(hass):
    """Store every validated ACU selected for a live-control zone."""
    hass.states.async_set("sensor.temp", "18")
    hass.states.async_set("sensor.rh", "60")
    for entity_id in ("climate.east", "climate.west"):
        hass.states.async_set(entity_id, "off", {"hvac_modes": ["dry", "off"]})
    result = await start(hass, "climate")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"temperature_entity": "sensor.temp", "humidity_entity": "sensor.rh"},
    )
    with patch(
        "custom_components.zeal_dry.async_setup_entry", AsyncMock(return_value=True)
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"climate_entities": ["climate.east", "climate.west"]},
        )
    assert result["type"] == "create_entry"
    assert result["data"]["climate_entities"] == [
        "climate.east",
        "climate.west",
    ]
