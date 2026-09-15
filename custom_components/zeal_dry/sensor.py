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
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DATA_CONTROLLERS, DOMAIN
from .controller import ZealDryController
from .entity import ZealDryEntity
from .hvac import ClimateAdapter


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
        value_fn=lambda controller: (
            round(controller.environmental_reading.temperature_c, 1)
            if controller.environmental_reading
            else None
        ),
    ),
    ZealDrySensorDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class="humidity",
        state_class="measurement",
        value_fn=lambda controller: (
            round(controller.environmental_reading.relative_humidity, 1)
            if controller.environmental_reading
            else None
        ),
    ),
    ZealDrySensorDescription(
        key="dew_point",
        name="Dew point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        state_class="measurement",
        value_fn=lambda controller: (
            round(controller.environmental_reading.dew_point_c, 1)
            if controller.environmental_reading
            else None
        ),
    ),
    ZealDrySensorDescription(
        key="dew_point_spread",
        name="Dew point spread",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class="measurement",
        value_fn=lambda controller: (
            round(controller.environmental_reading.dew_point_spread_c, 1)
            if controller.environmental_reading
            else None
        ),
    ),
    ZealDrySensorDescription(
        key="moisture_risk",
        name="Moisture risk",
        value_fn=lambda controller: (
            controller.decision.risk.value if controller.decision else "unknown"
        ),
    ),
    ZealDrySensorDescription(
        key="controller_state",
        name="Controller state",
        value_fn=lambda controller: controller.state_snapshot.state.value,
    ),
    ZealDrySensorDescription(
        key="decision_reason",
        name="Decision reason",
        value_fn=lambda controller: controller.state_snapshot.reason,
    ),
    ZealDrySensorDescription(
        key="proposed_dry_target",
        name="Proposed Dry target",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class="temperature",
        value_fn=lambda controller: (
            round(controller.proposed_setpoint.applied_target_c, 1)
            if controller.proposed_setpoint
            else None
        ),
    ),
    ZealDrySensorDescription(
        key="control_mode",
        name="Control mode",
        value_fn=lambda controller: controller.control_mode,
    ),
    ZealDrySensorDescription(
        key="dummy_acu_runtime",
        name="Dummy ACU runtime",
        native_unit_of_measurement="min",
        state_class="measurement",
        value_fn=lambda controller: (
            round(controller.actuator.runtime_minutes(), 1)
            if controller.control_mode == "dummy_acu"
            and controller.actuator is not None
            else None
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
        """Bind this entity to its zone controller and stable entity identifier."""
        super().__init__(entry, controller, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the current calculated/observed value."""
        controller = self.controller
        if self.entity_description.key == "proposed_dry_target" and isinstance(
            controller.actuator, ClimateAdapter
        ):
            command = controller.actuator.last_command
            if not command or command[0] != "dry" or command[1] is None:
                return None
            state = controller.hass.states.get(controller.climate_entity)
            unit = (
                state.attributes.get(
                    "temperature_unit", controller.hass.config.units.temperature_unit
                )
                if state
                else controller.hass.config.units.temperature_unit
            )
            return round(
                TemperatureConverter.convert(
                    command[1], unit, UnitOfTemperature.CELSIUS
                ),
                2,
            )
        return self.entity_description.value_fn(controller)

    @property
    def extra_state_attributes(self):
        """Expose the reason and supporting values for this status."""
        if self.entity_description.key not in ("controller_state", "decision_reason"):
            return None
        controller = self.controller
        return {
            "moisture_reason": controller.decision.reason
            if controller.decision
            else None,
            "moisture_explanation": controller.decision.explanation
            if controller.decision
            else controller.input_error,
            "command_error": controller.command_error,
            "drying_started_at": controller.state_snapshot.drying_started_at,
            "drying_stopped_at": controller.state_snapshot.drying_stopped_at,
            "minimum_run_minutes": controller.settings.minimum_run_minutes,
            "minimum_rest_minutes": controller.settings.minimum_rest_minutes,
            "maximum_run_minutes": controller.settings.maximum_run_minutes,
        }
