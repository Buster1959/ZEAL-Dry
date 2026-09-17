"""Runtime controller for one ZEAL-Dry zone."""

from __future__ import annotations

from asyncio import Lock
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .actuator import DummyActuator
from .const import (
    CONTROL_MODE_CLIMATE,
    CONTROL_MODE_DUMMY,
    DEFAULT_CONTROL_MODE,
    DEFAULT_TEST_HUMIDITY,
    DEFAULT_TEST_TEMPERATURE_C,
)
from .decision import DryingDecision, MoistureThresholds, evaluate_moisture
from .environment import (
    EnvironmentalInputError,
    EnvironmentalReading,
    build_environmental_reading,
)
from .hvac import ClimateAdapter, ClimateGroupAdapter
from .restoration import restore, serialize
from .setpoint import DrySetpointConfig, DrySetpointResult, calculate_dry_setpoint
from .settings import ZoneSettings
from .state_machine import ControllerState, StateSnapshot, TimingConfig, next_state

EVALUATION_INTERVAL = timedelta(minutes=1)
RECOVERABLE_EQUIPMENT_ERRORS = {
    "equipment_unavailable",
    "dry_mode_unsupported",
    "off_mode_unsupported",
}


@dataclass(slots=True)
class ZealDryController:
    """Own runtime environmental, decision, state, target, and test data."""

    hass: HomeAssistant
    entry_id: str
    zone_name: str
    temperature_entity: str | None = None
    humidity_entity: str | None = None
    climate_entity: str | None = None
    climate_entities: list[str] | None = None
    control_mode: str = DEFAULT_CONTROL_MODE
    command_error: str | None = None
    profile: str = "property_protection"
    settings: ZoneSettings = field(default_factory=ZoneSettings)
    _store: object = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _stopped: bool = field(default=False, init=False)
    thresholds: MoistureThresholds = field(default_factory=MoistureThresholds)
    timing: TimingConfig = field(default_factory=TimingConfig)
    setpoint_config: DrySetpointConfig = field(default_factory=DrySetpointConfig)
    test_temperature_c: float = DEFAULT_TEST_TEMPERATURE_C
    test_humidity: float = DEFAULT_TEST_HUMIDITY
    environmental_reading: EnvironmentalReading | None = None
    decision: DryingDecision | None = None
    state_snapshot: StateSnapshot = field(default_factory=StateSnapshot)
    proposed_setpoint: DrySetpointResult | None = None
    input_error: str | None = None
    last_updated: datetime | None = None
    above_maximum_since: datetime | None = None
    rest_cause: str | None = field(default=None, init=False)
    actuator: DummyActuator | ClimateAdapter | ClimateGroupAdapter | None = field(
        default=None, init=False
    )
    _remove_shutdown: object | None = field(default=None, init=False, repr=False)
    _remove_listener: object | None = field(default=None, init=False, repr=False)
    _remove_interval: object | None = field(default=None, init=False, repr=False)
    _listeners: set[Callable[[], None]] = field(
        default_factory=set, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Normalize legacy single-ACU entries into the multi-ACU representation."""
        configured = list(self.climate_entities or [])
        if self.climate_entity and self.climate_entity not in configured:
            configured.insert(0, self.climate_entity)
        self.climate_entities = configured
        self.climate_entity = configured[0] if configured else None

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity update callback and return its unsubscribe function."""
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    async def async_start(self) -> None:
        """Restore saved policy, prepare the actuator and subscribe to input updates."""
        # Restore policy before preparing any equipment for control.
        self._store = Store(self.hass, 1, f"zeal_dry.{self.entry_id}")
        saved = await self._store.async_load()
        if saved and isinstance(saved, dict):
            try:
                self.settings = ZoneSettings(**saved.get("settings", {}))
            except (TypeError, ValueError):
                self.command_error = "invalid_saved_settings"
        if not isinstance(saved, dict):
            saved = {}
        self._apply_settings()
        # Interrupted live runs must stop and observe a fresh rest period.
        if self.control_mode == CONTROL_MODE_CLIMATE:
            self.rest_cause = "restart"
            self.state_snapshot = restore(saved, dt_util.utcnow())
            saved_owned = set(saved.get("owned_entities", []))
            adapters = [
                ClimateAdapter(
                    self.hass,
                    entity_id,
                    owned=bool(saved.get("owned"))
                    or entity_id in saved_owned
                    or self.hass.states.get(entity_id) is not None
                    and self.hass.states.get(entity_id).state == "dry",
                )
                for entity_id in self.climate_entities
            ]
            self.actuator = (
                adapters[0] if len(adapters) == 1 else ClimateGroupAdapter(adapters)
            )
        if self.control_mode == CONTROL_MODE_DUMMY:
            self.actuator = DummyActuator()
            if saved:
                self.state_snapshot = restore(saved, dt_util.utcnow())
        elif self.temperature_entity and self.humidity_entity:
            self._remove_listener = async_track_state_change_event(
                self.hass,
                [self.temperature_entity, self.humidity_entity],
                self._async_sensor_changed,
            )
        # Sensor changes and periodic ticks both feed the same serialized update.
        self._remove_interval = async_track_time_interval(
            self.hass, self._async_periodic_tick, EVALUATION_INTERVAL
        )
        self._remove_shutdown = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._async_shutdown
        )
        await self.async_refresh()

    async def _async_shutdown(self, event):
        """Stop equipment when Home Assistant shuts down."""
        self._remove_shutdown = None
        await self.async_stop()

    async def async_stop(self) -> None:
        """Stop owned equipment, save state and release subscriptions."""
        async with self._lock:
            self._stopped = True
            if self.actuator is not None:
                try:
                    await self.actuator.async_turn_off()
                except (HomeAssistantError, TimeoutError) as err:
                    self.command_error = str(err)
            await self._safe_save()
        if callable(self._remove_listener):
            self._remove_listener()
        if callable(self._remove_interval):
            self._remove_interval()
        if callable(self._remove_shutdown):
            self._remove_shutdown()
            self._remove_shutdown = None
        self._remove_listener = None
        self._remove_interval = None

    async def async_set_test_temperature(self, value: float) -> None:
        """Change the simulated room temperature and reevaluate the controller."""
        self.test_temperature_c = value
        await self.async_refresh()

    async def async_set_test_humidity(self, value: float) -> None:
        """Change the simulated humidity and reevaluate the controller."""
        self.test_humidity = value
        await self.async_refresh()

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        """Schedule reevaluation when a configured room sensor changes."""
        self.hass.async_create_task(self.async_refresh())

    @callback
    def _async_periodic_tick(self, now: datetime) -> None:
        """Reevaluate timers even when room readings have not changed."""
        self.hass.async_create_task(self.async_refresh())

    def _apply_settings(self):
        """Translate saved user settings into decision, timing and setpoint inputs."""
        settings = self.settings
        self.profile = settings.profile
        self.thresholds = replace(
            self.thresholds,
            preferred_rh=settings.preferred_rh,
            maximum_rh=settings.maximum_rh,
            critical_rh=settings.critical_rh,
            high_rh_persistence=timedelta(minutes=settings.persistence_minutes),
        )
        self.timing = TimingConfig(
            minimum_run=timedelta(minutes=settings.minimum_run_minutes),
            minimum_rest=timedelta(minutes=settings.minimum_rest_minutes),
            recovery_period=timedelta(minutes=settings.recovery_minutes),
            maximum_run=timedelta(minutes=settings.maximum_run_minutes),
        )
        self.setpoint_config = replace(
            self.setpoint_config,
            strategy=settings.strategy,
            fixed_target_c=settings.fixed_target_c,
            offset_c=settings.offset_c,
            minimum_c=settings.minimum_c,
            maximum_c=settings.maximum_c,
        )

    async def async_update_settings(self, **changes):
        """Validate and save a policy change before applying it to the running zone."""
        async with self._lock:
            updated = replace(self.settings, **changes)
            previous = self.settings
            self.settings = updated
            try:
                await self._save()
            except Exception:
                self.settings = previous
                raise
            self._apply_settings()
            # A changed start threshold must earn a new persistence period.
            if any(key in changes for key in ("maximum_rh", "persistence_minutes")):
                self.above_maximum_since = None
            await self._async_refresh()

    async def _save(self):
        """Persist settings, timer history and responsibility for stopping the AC."""
        if self._store is not None:
            await self._store.async_save(
                {
                    **serialize(self.state_snapshot),
                    "settings": self.settings.as_dict(),
                    "owned": isinstance(
                        self.actuator, (ClimateAdapter, ClimateGroupAdapter)
                    )
                    and self.actuator.owned,
                    "owned_entities": [
                        adapter.entity_id
                        for adapter in self._climate_adapters()
                        if adapter.owned
                    ],
                }
            )

    def _record_fault(self, now: datetime) -> None:
        """Record the fault and stop time so recovery cannot bypass the rest timer."""
        self.state_snapshot = replace(
            self.state_snapshot,
            state=ControllerState.FAULT,
            reason=self.command_error,
            drying_stopped_at=now,
        )

    async def _safe_save(self):
        """Latch a fault and request a stop if runtime state cannot be saved."""
        try:
            await self._save()
        except (OSError, HomeAssistantError):
            self.command_error = "storage_write_failed"
            self._record_fault(dt_util.utcnow())
            if self.actuator is not None:
                try:
                    await self.actuator.async_turn_off()
                except (HomeAssistantError, TimeoutError):
                    pass

    async def async_refresh(self) -> None:
        """Serialize evaluations so sensor events cannot overlap equipment commands."""
        async with self._lock:
            if not self._stopped:
                await self._async_refresh()

    async def _async_refresh(self) -> None:
        """Evaluate inputs, enforce protections, command equipment, then publish."""
        now = dt_util.utcnow()
        self._update_environment(now)
        self._update_control_state(now)
        await self._apply_equipment_request(now)
        self.last_updated = now
        for listener in tuple(self._listeners):
            listener()

    def _update_environment(self, now: datetime) -> None:
        """Validate room readings and maintain the high-humidity persistence timer."""
        try:
            if self.control_mode == CONTROL_MODE_DUMMY:
                temperature_c = self.test_temperature_c
                humidity = self.test_humidity
            else:
                temperature_c = self._temperature_c(
                    self.hass.states.get(self.temperature_entity)
                    if self.temperature_entity
                    else None
                )
                humidity = self._numeric_state(
                    self.hass.states.get(self.humidity_entity)
                    if self.humidity_entity
                    else None,
                    "humidity",
                )

            self.environmental_reading = build_environmental_reading(
                temperature_c, humidity
            )
            self.proposed_setpoint = calculate_dry_setpoint(
                temperature_c, self.setpoint_config
            )
            self.input_error = None
            if humidity >= self.thresholds.maximum_rh:
                if self.above_maximum_since is None:
                    self.above_maximum_since = now
            else:
                self.above_maximum_since = None
            elapsed = (
                now - self.above_maximum_since if self.above_maximum_since else None
            )
            self.decision = evaluate_moisture(
                self.environmental_reading, self.thresholds, elapsed
            )
        except EnvironmentalInputError as err:
            self.environmental_reading = None
            self.proposed_setpoint = None
            self.input_error = str(err)
            self.above_maximum_since = None
            self.decision = evaluate_moisture(None, self.thresholds)

    def _update_control_state(self, now: datetime) -> None:
        """Apply timing protections and latch equipment or feedback faults."""
        if isinstance(self.actuator, (ClimateAdapter, ClimateGroupAdapter)):
            try:
                self.actuator.inspect()
            except HomeAssistantError as err:
                self.command_error = str(err)
            else:
                # Availability and capability faults may be transient. Clear only
                # errors produced by inspection; command and storage faults stay latched.
                if self.command_error in RECOVERABLE_EQUIPMENT_ERRORS:
                    self.command_error = None
        self.state_snapshot = next_state(
            self.state_snapshot,
            self.decision,
            now,
            self.timing,
            action_permitted=self.actuator is not None
            and self.actuator.available
            and self.command_error is None,
            inhibited=self.profile == "off",
        )
        if self.state_snapshot.reason != "minimum_rest_time_active":
            self.rest_cause = None
        if self.command_error and self.profile != "off":
            self._record_fault(now)
        # Allow one minute for device feedback before treating a mode mismatch as a fault.
        if (
            isinstance(self.actuator, (ClimateAdapter, ClimateGroupAdapter))
            and self.actuator.owned
        ):
            for adapter in self._climate_adapters():
                observed = self.hass.states.get(adapter.entity_id)
                if (
                    adapter.last_command
                    and adapter.last_command[0] == "dry"
                    and observed is not None
                    and observed.state != "dry"
                    and adapter.requested_at is not None
                    and now - adapter.requested_at >= timedelta(minutes=1)
                ):
                    self.command_error = f"climate_mode_changed:{adapter.entity_id}"
                    self._record_fault(now)
                    break

    async def _apply_equipment_request(self, now: datetime) -> None:
        """Save intent before commanding equipment; stop safely if a request fails."""
        # Persist intent before services, so interrupted starts are stopped on restart.
        if (
            isinstance(self.actuator, (ClimateAdapter, ClimateGroupAdapter))
            and self.state_snapshot.state is ControllerState.DRYING
        ):
            self.actuator.owned = True
        await self._safe_save()
        if self.actuator is not None:
            try:
                if self.state_snapshot.state is ControllerState.DRYING:
                    if isinstance(
                        self.actuator, (ClimateAdapter, ClimateGroupAdapter)
                    ):
                        await self.actuator.async_dry(
                            self.proposed_setpoint.raw_target_c,
                            self.setpoint_config.minimum_c,
                            self.setpoint_config.maximum_c,
                        )
                    else:
                        await self.actuator.async_turn_on()
                else:
                    await self.actuator.async_turn_off()
            except (HomeAssistantError, TimeoutError) as err:
                self.command_error = str(err) or "command_failed"
                self._record_fault(now)
                try:
                    await self.actuator.async_turn_off()
                except (HomeAssistantError, TimeoutError):
                    pass  # Ownership remains set; subsequent ticks retry stopping.
        await self._safe_save()

    def _climate_adapters(self) -> list[ClimateAdapter]:
        """Return individual live adapters for ownership and feedback checks."""
        if isinstance(self.actuator, ClimateGroupAdapter):
            return self.actuator.adapters
        if isinstance(self.actuator, ClimateAdapter):
            return [self.actuator]
        return []

    @staticmethod
    def _numeric_state(state: State | None, label: str) -> float:
        """Reject missing, stale or nonnumeric sensor readings."""
        if state is None:
            raise EnvironmentalInputError(f"{label} entity is missing")
        if dt_util.utcnow() - state.last_reported > timedelta(minutes=30):
            raise EnvironmentalInputError(f"{label} sensor is stale")
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            raise EnvironmentalInputError(f"{label} entity is {state.state}")
        try:
            return float(state.state)
        except (TypeError, ValueError) as err:
            raise EnvironmentalInputError(f"{label} state is not numeric") from err

    @classmethod
    def _temperature_c(cls, state: State | None) -> float:
        """Convert a validated temperature reading to Celsius."""
        value = cls._numeric_state(state, "temperature")
        if state is None:
            raise EnvironmentalInputError("temperature entity is missing")
        unit = state.attributes.get("unit_of_measurement")
        if unit in (None, UnitOfTemperature.CELSIUS):
            return value
        if unit in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
            return TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
        raise EnvironmentalInputError(f"unsupported temperature unit: {unit}")
