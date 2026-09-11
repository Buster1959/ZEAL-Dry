"""Shared Home Assistant entity support for ZEAL-Dry."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .controller import ZealDryController


class ZealDryEntity(Entity):
    """Base entity backed by one ZEAL-Dry zone controller."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, controller: ZealDryController, key: str) -> None:
        self._entry = entry
        self.controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=controller.zone_name,
            manufacturer="ZEAL-Dry",
            model="Moisture Protection Zone",
        )
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        """Update after each complete controller evaluation."""
        self._remove_listener = self.controller.add_listener(self._async_controller_updated)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _async_controller_updated(self) -> None:
        self.async_write_ha_state()
