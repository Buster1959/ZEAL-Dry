"""Tests for the ZEAL-Dry config-entry lifecycle."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.zeal_dry import async_setup_entry, async_unload_entry
from custom_components.zeal_dry.const import (
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    DATA_CONTROLLERS,
    DOMAIN,
)


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """A zone controller is created and removed with its config entry."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Undercroft Bedroom",
        data={
            CONF_ZONE_NAME: "Undercroft Bedroom",
            CONF_TEMPERATURE_ENTITY: "sensor.test_temperature",
            CONF_HUMIDITY_ENTITY: "sensor.test_humidity",
        },
        options={},
        source="user",
        entry_id="test_entry",
        discovery_keys={},
        unique_id="undercroft bedroom",
    )

    assert await async_setup_entry(hass, entry)
    assert entry.entry_id in hass.data[DOMAIN][DATA_CONTROLLERS]

    assert await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN][DATA_CONTROLLERS]
