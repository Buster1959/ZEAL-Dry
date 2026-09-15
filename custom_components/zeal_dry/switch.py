"""Switch entities for ZEAL-Dry."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_CONTROLLERS, DOMAIN
from .controller import ZealDryController
from .entity import ZealDryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the built-in dummy ACU when test mode is selected."""
    controller = hass.data[DOMAIN][DATA_CONTROLLERS][entry.entry_id]
    if controller.control_mode != "dummy_acu" or controller.actuator is None:
        return
    async_add_entities([ZealDryDummyAcuSwitch(entry, controller)])


class ZealDryDummyAcuSwitch(ZealDryEntity, SwitchEntity):
    """Visible switch representing the built-in test ACU."""

    _attr_name = "Dummy ACU"
    _attr_icon = "mdi:air-conditioner"

    def __init__(self, entry: ConfigEntry, controller: ZealDryController) -> None:
        super().__init__(entry, controller, "dummy_acu")
        self._remove_actuator_listener = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to controller inputs and dummy actuator changes."""
        await super().async_added_to_hass()
        if self.controller.actuator is not None:
            self._remove_actuator_listener = self.controller.actuator.add_listener(
                self._actuator_changed
            )

    async def async_will_remove_from_hass(self) -> None:
        """Release listeners."""
        if self._remove_actuator_listener is not None:
            self._remove_actuator_listener()
            self._remove_actuator_listener = None
        await super().async_will_remove_from_hass()

    @property
    def is_on(self) -> bool:
        """Return the dummy ACU state."""
        return bool(self.controller.actuator and self.controller.actuator.is_on)

    @property
    def extra_state_attributes(self) -> dict:
        """Expose useful test timing information."""
        actuator = self.controller.actuator
        if actuator is None:
            return {}
        return {
            "test_mode": True,
            "started_at": actuator.started_at,
            "stopped_at": actuator.stopped_at,
            "current_runtime_minutes": round(actuator.runtime_minutes(), 1),
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Manually turn on the dummy actuator for test purposes."""
        if self.controller.actuator is not None:
            await self.controller.actuator.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Manually turn off the dummy actuator for test purposes."""
        if self.controller.actuator is not None:
            await self.controller.actuator.async_turn_off()

    @callback
    def _actuator_changed(self) -> None:
        """Publish an actuator state change immediately."""
        self.async_write_ha_state()
