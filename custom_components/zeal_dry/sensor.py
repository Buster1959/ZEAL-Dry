"""Monitoring sensors for ZEAL-Dry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_CONTROLLERS, DOMAIN
from .controller import ZealDryController
from .entity import ZealDryEntity


@dataclass(frozen=True, kw_only=True)
class ZealDrySensorDescription(SensorEntityDescription):
    """Describe a ZEAL-Dry monitoring sensor."""

    value_fn: Callable[[ZealDryController], Any]


SENSORS = (
    ZealDrySensorDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        state_class="measurement",
        value_fn=lambda c: (
            round(c.environmental_reading.temperature_c, 1)
            if c.environmental_reading else None
        ),
    ),
    ZealDrySensorDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class="humidity",
        state_class="measurement",
        value_fn=lambda c: (
            round(c.environmental_reading.relative_humidity, 1)
            if c.environmental_reading else None
        ),
    ),
    ZealDrySensorDescription(
        key="dew_point",
        name="Dew point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        state_class="measurement",
        value_fn=lambda c: (
            round(c.environmental_reading.dew_point_c, 1)
            if c.environmental_reading else None
        ),
    ),
    ZealDrySensorDescription(
        key="dew_point_spread",
        name="Dew point spread",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class="measurement",
        value_fn=lambda c: (
            round(c.environmental_reading.dew_point_spread_c, 1)
            if c.environmental_reading else None
        ),
    ),
    ZealDrySensorDescription(
        key="moisture_risk",
        name="Moisture risk",
        value_fn=lambda c: c.decision.risk.value if c.decision else "unknown",
    ),
    ZealDrySensorDescription(
        key="controller_state",
        name="Controller state",
        value_fn=lambda c: c.state_snapshot.state.value,
    ),
    ZealDrySensorDescription(
        key="decision_reason",
        name="Decision reason",
        value_fn=lambda c: c.decision.reason if c.decision else c.input_error,
    ),
    ZealDrySensorDescription(
        key="proposed_dry_target",
        name="Proposed Dry target",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        value_fn=lambda c: (
            round(c.proposed_setpoint.applied_target_c, 1)
            if c.proposed_setpoint else None
        ),
    ),
    ZealDrySensorDescription(
        key="control_mode",
        name="Control mode",
        value_fn=lambda c: c.control_mode,
    ),
    ZealDrySensorDescription(
        key="dummy_acu_runtime",
        name="Dummy ACU runtime",
        native_unit_of_measurement="min",
        state_class="measurement",
        value_fn=lambda c: (
            round(c.actuator.runtime_minutes(), 1) if c.control_mode == "dummy_acu" and c.actuator is not None else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZEAL-Dry monitoring sensors."""
    controller = hass.data[DOMAIN][DATA_CONTROLLERS][entry.entry_id]
    async_add_entities(
        ZealDrySensor(entry, controller, description) for description in SENSORS
    )


class ZealDrySensor(ZealDryEntity, SensorEntity):
    """One live ZEAL-Dry monitoring sensor."""

    entity_description: ZealDrySensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        controller: ZealDryController,
        description: ZealDrySensorDescription,
    ) -> None:
        super().__init__(entry, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the current calculated/observed value."""
        return self.entity_description.value_fn(self.controller)
