"""ZEAL-Dry Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_CLIMATE_ENTITIES,
    CONF_CONTROL_MODE,
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_WEATHER_ENTITY,
    CONF_ZONE_NAME,
    DATA_CONTROLLERS,
    DEFAULT_CONTROL_MODE,
    DOMAIN,
)
from .controller import ZealDryController
from .panel import async_remove_panel, async_sync_panel
from .websocket_api import async_register_commands

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Create the integration data container."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start the zone controller and load its Home Assistant entity platforms."""
    hass.data.setdefault(DOMAIN, {})
    controllers = hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})
    controller = ZealDryController(
        hass=hass,
        entry_id=entry.entry_id,
        zone_name=entry.data[CONF_ZONE_NAME],
        temperature_entity=entry.data.get(CONF_TEMPERATURE_ENTITY),
        humidity_entity=entry.data.get(CONF_HUMIDITY_ENTITY),
        weather_entity=entry.data.get(CONF_WEATHER_ENTITY),
        climate_entity=entry.data.get(CONF_CLIMATE_ENTITY),
        climate_entities=entry.data.get(CONF_CLIMATE_ENTITIES),
        control_mode=entry.data.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE),
    )
    controllers[entry.entry_id] = controller
    async_register_commands(hass)
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await async_sync_panel(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload zone entities and stop the associated controller."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    controller = hass.data[DOMAIN][DATA_CONTROLLERS].pop(entry.entry_id, None)
    if controller is not None:
        await controller.async_stop()
    if not hass.data[DOMAIN][DATA_CONTROLLERS]:
        await async_remove_panel(hass)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the zone after its config-entry options change."""
    await hass.config_entries.async_reload(entry.entry_id)
