"""Diagnostics for ZEAL-Dry."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_CONTROLLERS, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict:
    """Return non-sensitive Block 1 diagnostics for one ZEAL-Dry zone."""
    controller = hass.data.get(DOMAIN, {}).get(DATA_CONTROLLERS, {}).get(entry.entry_id)

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
        },
        "controller_loaded": controller is not None,
        "zone": {
            "name": getattr(controller, "zone_name", None),
            "temperature_entity": getattr(controller, "temperature_entity", None),
            "humidity_entity": getattr(controller, "humidity_entity", None),
        },
        "block": 1,
        "control_active": False,
    }
