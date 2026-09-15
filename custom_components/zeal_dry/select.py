"""Persistent profile and setpoint strategy controls."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_CONTROLLERS, DOMAIN
from .entity import ZealDryEntity
from .settings import SELECT_SETTINGS


async def async_setup_entry(hass, entry, async_add_entities):
    controller = hass.data[DOMAIN][DATA_CONTROLLERS][entry.entry_id]
    async_add_entities(
        ZealDrySettingSelect(entry, controller, key) for key in SELECT_SETTINGS
    )


class ZealDrySettingSelect(ZealDryEntity, SelectEntity):
    def __init__(self, entry, controller, key):
        super().__init__(entry, controller, key)
        self.key = key
        self._attr_name, self._attr_options = SELECT_SETTINGS[key]

    @property
    def current_option(self):
        return getattr(self.controller.settings, self.key)

    async def async_select_option(self, option):
        try:
            await self.controller.async_update_settings(**{self.key: option})
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
