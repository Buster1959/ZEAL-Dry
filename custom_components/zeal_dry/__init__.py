"""ZEAL-Dry Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    DATA_CONTROLLERS,
    DOMAIN,
)
from .controller import ZealDryController


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the ZEAL-Dry integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one ZEAL-Dry zone from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    controllers = hass.data[DOMAIN].setdefault(DATA_CONTROLLERS, {})

    controller = ZealDryController(
        hass=hass,
        entry_id=entry.entry_id,
        zone_name=entry.data[CONF_ZONE_NAME],
        temperature_entity=entry.data[CONF_TEMPERATURE_ENTITY],
        humidity_entity=entry.data[CONF_HUMIDITY_ENTITY],
    )
    controllers[entry.entry_id] = controller
    await controller.async_start()

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one ZEAL-Dry zone."""
    controller = hass.data[DOMAIN][DATA_CONTROLLERS].pop(entry.entry_id, None)
    if controller is not None:
        await controller.async_stop()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload ZEAL-Dry when its config entry is updated."""
    await hass.config_entries.async_reload(entry.entry_id)
