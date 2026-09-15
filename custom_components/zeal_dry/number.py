"""Adjustable ZEAL-Dry test environment controls."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CONTROL_MODE, CONTROL_MODE_DUMMY, DATA_CONTROLLERS, DOMAIN
from .entity import ZealDryEntity
from .settings import NUMBER_SETTINGS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    controller = hass.data[DOMAIN][DATA_CONTROLLERS][entry.entry_id]
    entities = [ZealDrySettingNumber(entry, controller, key) for key in NUMBER_SETTINGS]
    if entry.data.get(CONF_CONTROL_MODE) == CONTROL_MODE_DUMMY:
        entities.extend(
            [
                ZealDryTestTemperature(entry, controller),
                ZealDryTestHumidity(entry, controller),
            ]
        )
    async_add_entities(entities)


class ZealDrySettingNumber(ZealDryEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, controller, key):
        super().__init__(entry, controller, key)
        self.key = key
        (
            self._attr_name,
            self._attr_native_min_value,
            self._attr_native_max_value,
            self._attr_native_step,
            self._attr_native_unit_of_measurement,
        ) = NUMBER_SETTINGS[key]

    @property
    def native_value(self):
        return getattr(self.controller.settings, self.key)

    async def async_set_native_value(self, value):
        try:
            await self.controller.async_update_settings(**{self.key: value})
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err


class ZealDryTestTemperature(ZealDryEntity, NumberEntity):
    """Adjustable simulated room temperature."""

    _attr_name = "Test temperature"
    _attr_native_min_value = 5.0
    _attr_native_max_value = 35.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:thermometer"

    def __init__(self, entry, controller):
        super().__init__(entry, controller, "test_temperature")

    @property
    def native_value(self):
        return self.controller.test_temperature_c

    async def async_set_native_value(self, value: float) -> None:
        await self.controller.async_set_test_temperature(value)


class ZealDryTestHumidity(ZealDryEntity, NumberEntity):
    """Adjustable simulated relative humidity."""

    _attr_name = "Test humidity"
    _attr_native_min_value = 20.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:water-percent"

    def __init__(self, entry, controller):
        super().__init__(entry, controller, "test_humidity")

    @property
    def native_value(self):
        return self.controller.test_humidity

    async def async_set_native_value(self, value: float) -> None:
        await self.controller.async_set_test_humidity(value)
