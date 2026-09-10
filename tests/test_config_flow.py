"""Tests for the ZEAL-Dry config flow."""

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant

from custom_components.zeal_dry.const import (
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    DOMAIN,
)


async def test_user_flow_creates_zone(hass: HomeAssistant) -> None:
    """A valid pair of indoor sensors creates one zone entry."""
    hass.states.async_set(
        "sensor.test_temperature",
        "17.2",
        {"device_class": "temperature", "unit_of_measurement": UnitOfTemperature.CELSIUS},
    )
    hass.states.async_set(
        "sensor.test_humidity",
        "68",
        {"device_class": "humidity", "unit_of_measurement": PERCENTAGE},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZONE_NAME: "Undercroft Bedroom",
            CONF_TEMPERATURE_ENTITY: "sensor.test_temperature",
            CONF_HUMIDITY_ENTITY: "sensor.test_humidity",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Undercroft Bedroom"
    assert result["data"][CONF_TEMPERATURE_ENTITY] == "sensor.test_temperature"
    assert result["data"][CONF_HUMIDITY_ENTITY] == "sensor.test_humidity"


async def test_missing_entity_is_rejected(hass: HomeAssistant) -> None:
    """Unavailable selected entities are rejected cleanly."""
    hass.states.async_set(
        "sensor.test_humidity",
        "68",
        {"device_class": "humidity", "unit_of_measurement": PERCENTAGE},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZONE_NAME: "Undercroft Bedroom",
            CONF_TEMPERATURE_ENTITY: "sensor.missing_temperature",
            CONF_HUMIDITY_ENTITY: "sensor.test_humidity",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"][CONF_TEMPERATURE_ENTITY] == "entity_not_found"
