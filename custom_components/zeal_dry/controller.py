"""Runtime controller for one ZEAL-Dry zone.

Block 2 observes indoor temperature and humidity and produces environmental
measurements only. It does not make moisture decisions or control HVAC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .environment import (
    EnvironmentalInputError,
    EnvironmentalReading,
    build_environmental_reading,
)


@dataclass(slots=True)
class ZealDryController:
    """Own the runtime environmental state for one configured zone."""

    hass: HomeAssistant
    entry_id: str
    zone_name: str
    temperature_entity: str
    humidity_entity: str
    environmental_reading: EnvironmentalReading | None = None
    input_error: str | None = None
    last_updated: datetime | None = None
    _remove_listener: object | None = field(default=None, init=False, repr=False)

    async def async_start(self) -> None:
        """Start observing the configured indoor sensors."""
        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self.temperature_entity, self.humidity_entity],
            self._async_sensor_changed,
        )
        self._refresh_environment()

    async def async_stop(self) -> None:
        """Stop observing sensors and release runtime resources."""
        if callable(self._remove_listener):
            self._remove_listener()
        self._remove_listener = None

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        """Refresh environmental values when either input changes."""
        self._refresh_environment()

    @callback
    def _refresh_environment(self) -> None:
        """Read and validate the current indoor environment."""
        temperature_state = self.hass.states.get(self.temperature_entity)
        humidity_state = self.hass.states.get(self.humidity_entity)

        try:
            temperature_c = self._temperature_c(temperature_state)
            humidity = self._numeric_state(humidity_state, "humidity")
            self.environmental_reading = build_environmental_reading(
                temperature_c,
                humidity,
            )
            self.input_error = None
        except EnvironmentalInputError as err:
            self.environmental_reading = None
            self.input_error = str(err)

        self.last_updated = dt_util.utcnow()

    @staticmethod
    def _numeric_state(state: State | None, label: str) -> float:
        """Return a numeric state or fail safely."""
        if state is None:
            raise EnvironmentalInputError(f"{label} entity is missing")
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            raise EnvironmentalInputError(f"{label} entity is {state.state}")
        try:
            return float(state.state)
        except (TypeError, ValueError) as err:
            raise EnvironmentalInputError(f"{label} state is not numeric") from err

    @classmethod
    def _temperature_c(cls, state: State | None) -> float:
        """Read a Home Assistant temperature state and normalize it to Celsius."""
        value = cls._numeric_state(state, "temperature")
        if state is None:
            raise EnvironmentalInputError("temperature entity is missing")

        unit = state.attributes.get("unit_of_measurement")
        if unit in (None, UnitOfTemperature.CELSIUS):
            return value
        if unit in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
            return TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
        raise EnvironmentalInputError(f"unsupported temperature unit: {unit}")
