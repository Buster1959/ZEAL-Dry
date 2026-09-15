"""Binary monitoring sensors for ZEAL-Dry."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_CONTROLLERS, DOMAIN
from .controller import ZealDryController
from .entity import ZealDryEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZEAL-Dry binary sensors."""
    controller = hass.data[DOMAIN][DATA_CONTROLLERS][entry.entry_id]
    async_add_entities(
        [
            ZealDryDemandSensor(entry, controller),
            ZealDryFaultSensor(entry, controller),
            ZealDryCondensationSensor(entry, controller),
        ]
    )


class ZealDryDemandSensor(ZealDryEntity, BinarySensorEntity):
    """Show whether ZEAL-Dry currently wants active drying."""

    _attr_name = "Drying required"
    _attr_icon = "mdi:water-alert"

    def __init__(self, entry: ConfigEntry, controller: ZealDryController) -> None:
        super().__init__(entry, controller, "drying_required")

    @property
    def is_on(self) -> bool | None:
        """Return current drying demand, or unknown when inputs are invalid."""
        if self.controller.decision is None:
            return None
        if self.controller.decision.risk.value == "unknown":
            return None
        return self.controller.decision.demand

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the reason without hiding it in diagnostics."""
        decision = self.controller.decision
        return {
            "risk": decision.risk.value if decision else "unknown",
            "reason": decision.reason if decision else "sensor_unavailable",
            "explanation": decision.explanation
            if decision
            else self.controller.input_error,
        }


class ZealDryFaultSensor(ZealDryEntity, BinarySensorEntity):
    _attr_name = "Fault"
    _attr_device_class = "problem"

    def __init__(self, entry, controller):
        super().__init__(entry, controller, "fault")

    @property
    def is_on(self):
        return (
            self.controller.state_snapshot.state.value == "fault"
            or self.controller.command_error is not None
        )

    @property
    def extra_state_attributes(self):
        return {"reason": self.controller.command_error or self.controller.input_error}


class ZealDryCondensationSensor(ZealDryEntity, BinarySensorEntity):
    _attr_name = "Condensation risk"
    _attr_icon = "mdi:water-alert"

    def __init__(self, entry, controller):
        super().__init__(entry, controller, "condensation_risk")

    @property
    def is_on(self):
        reading = self.controller.environmental_reading
        return (
            reading.dew_point_spread_c <= self.controller.settings.safety_margin_c
            if reading
            else None
        )

    @property
    def extra_state_attributes(self):
        return {
            "criterion": "room_temperature_minus_dew_point",
            "safety_margin_c": self.controller.settings.safety_margin_c,
            "explanation": "Air close to saturation; surface temperatures are not measured.",
        }
