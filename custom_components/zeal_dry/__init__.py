"""ZEAL-Dry Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_CONTROL_MODE,
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    DATA_CONTROLLERS,
    DEFAULT_CONTROL_MODE,
    DOMAIN,
)
from .controller import ZealDryController

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    controllers = hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})
    controller = ZealDryController(
        hass=hass,
        entry_id=entry.entry_id,
        zone_name=entry.data[CONF_ZONE_NAME],
        temperature_entity=entry.data.get(CONF_TEMPERATURE_ENTITY),
        humidity_entity=entry.data.get(CONF_HUMIDITY_ENTITY),
        climate_entity=entry.data.get(CONF_CLIMATE_ENTITY),
        control_mode=entry.data.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE),
    )
    controllers[entry.entry_id] = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    controller = hass.data[DOMAIN][DATA_CONTROLLERS].pop(entry.entry_id, None)
    if controller is not None:
        await controller.async_stop()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
