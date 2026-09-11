"""Runtime controller for one ZEAL-Dry zone."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .actuator import DummyActuator
from .const import CONTROL_MODE_DUMMY
from .decision import DryingDecision, MoistureThresholds, evaluate_moisture
from .environment import (
    EnvironmentalInputError,
    EnvironmentalReading,
    build_environmental_reading,
)
from .setpoint import DrySetpointConfig, DrySetpointResult, calculate_dry_setpoint
from .state_machine import ControllerState, StateSnapshot, TimingConfig, next_state

EVALUATION_INTERVAL = timedelta(minutes=1)


@dataclass(slots=True)
class ZealDryController:
    """Own runtime environmental, decision, state, target, and test actuator data."""

    hass: HomeAssistant
    entry_id: str
    zone_name: str
    temperature_entity: str
    humidity_entity: str
    control_mode: str
    thresholds: MoistureThresholds = field(default_factory=MoistureThresholds)
    timing: TimingConfig = field(default_factory=TimingConfig)
    setpoint_config: DrySetpointConfig = field(default_factory=DrySetpointConfig)
    environmental_reading: EnvironmentalReading | None = None
    decision: DryingDecision | None = None
    state_snapshot: StateSnapshot = field(default_factory=StateSnapshot)
    proposed_setpoint: DrySetpointResult | None = None
    input_error: str | None = None
    last_updated: datetime | None = None
    above_maximum_since: datetime | None = None
    actuator: DummyActuator | None = field(default=None, init=False)
    _remove_listener: object | None = field(default=None, init=False, repr=False)
    _remove_interval: object | None = field(default=None, init=False, repr=False)

    async def async_start(self) -> None:
        """Start observing the configured indoor sensors."""
        if self.control_mode == CONTROL_MODE_DUMMY:
            self.actuator = DummyActuator()

        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self.temperature_entity, self.humidity_entity],
            self._async_sensor_changed,
        )
        self._remove_interval = async_track_time_interval(
            self.hass,
            self._async_periodic_tick,
            EVALUATION_INTERVAL,
        )
        await self._async_refresh_environment()

    async def async_stop(self) -> None:
        """Stop observing sensors and release runtime resources."""
        if self.actuator is not None:
            await self.actuator.async_turn_off()
        if callable(self._remove_listener):
            self._remove_listener()
        if callable(self._remove_interval):
            self._remove_interval()
        self._remove_listener = None
        self._remove_interval = None

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        """Refresh environmental values when either input changes."""
        self.hass.async_create_task(self._async_refresh_environment())

    @callback
    def _async_periodic_tick(self, now: datetime) -> None:
        """Re-evaluate persistence and runtime timers even with static sensors."""
        self.hass.async_create_task(self._async_refresh_environment())

    async def _async_refresh_environment(self) -> None:
        """Read inputs, evaluate moisture/state, then synchronize the test actuator."""
        temperature_state = self.hass.states.get(self.temperature_entity)
        humidity_state = self.hass.states.get(self.humidity_entity)
        now = dt_util.utcnow()

        try:
            temperature_c = self._temperature_c(temperature_state)
            humidity = self._numeric_state(humidity_state, "humidity")
            self.environmental_reading = build_environmental_reading(
                temperature_c,
                humidity,
            )
            self.proposed_setpoint = calculate_dry_setpoint(
                temperature_c,
                self.setpoint_config,
            )
            self.input_error = None

            if humidity >= self.thresholds.maximum_rh:
                if self.above_maximum_since is None:
                    self.above_maximum_since = now
            else:
                self.above_maximum_since = None

            elapsed = (
                now - self.above_maximum_since
                if self.above_maximum_since is not None
                else None
            )
            self.decision = evaluate_moisture(
                self.environmental_reading,
                self.thresholds,
                elapsed,
            )
        except EnvironmentalInputError as err:
            self.environmental_reading = None
            self.proposed_setpoint = None
            self.input_error = str(err)
            self.above_maximum_since = None
            self.decision = evaluate_moisture(None, self.thresholds)

        action_permitted = self.actuator is not None and self.actuator.available
        previous_state = self.state_snapshot.state
        self.state_snapshot = next_state(
            self.state_snapshot,
            self.decision,
            now,
            self.timing,
            action_permitted=action_permitted,
        )

        if self.actuator is not None:
            if self.state_snapshot.state is ControllerState.DRYING:
                await self.actuator.async_turn_on()
            elif previous_state is ControllerState.DRYING:
                await self.actuator.async_turn_off()

        self.last_updated = now

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
