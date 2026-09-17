"""Translate controller requests into supplier-neutral climate services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil, floor, isfinite

from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter


@dataclass
class ClimateAdapter:
    """Send climate requests and track whether this zone must stop the AC."""

    hass: HomeAssistant
    entity_id: str
    owned: bool = False
    requested_at: datetime | None = None
    last_command: tuple | None = None
    last_result: str = "not_requested"

    @property
    def available(self):
        """Check that the configured AC exists and reports an available state."""
        state = self.hass.states.get(self.entity_id) if self.entity_id else None
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    def inspect(self):
        """Require Dry and Off modes before returning device capabilities."""
        if not self.available:
            raise HomeAssistantError("equipment_unavailable")
        state = self.hass.states.get(self.entity_id)
        attributes = state.attributes
        if "dry" not in attributes.get("hvac_modes", []):
            raise HomeAssistantError("dry_mode_unsupported")
        if "off" not in attributes.get("hvac_modes", []):
            raise HomeAssistantError("off_mode_unsupported")
        return attributes

    def target(self, target_c, minimum_c, maximum_c):
        """Intersect configured bounds with the device grid, in device units."""
        attributes = self.inspect()
        supported_features = int(attributes.get("supported_features", 0))
        supports_temperature = (
            supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
        )
        if not supports_temperature:
            return None
        unit = attributes.get(
            "temperature_unit", self.hass.config.units.temperature_unit
        )

        def to_device_units(value):
            """Convert the configured Celsius values to the AC's temperature unit."""
            return TemperatureConverter.convert(value, UnitOfTemperature.CELSIUS, unit)

        try:
            device_minimum = float(attributes["min_temp"])
            device_maximum = float(attributes["max_temp"])
            step = float(attributes.get("target_temp_step", 1))
            if (
                not all(isfinite(v) for v in (device_minimum, device_maximum, step))
                or step <= 0
            ):
                raise ValueError
            # Find supported device steps inside both sets of temperature limits.
            # The tiny tolerance prevents floating-point error from dropping a boundary step.
            first_step = ceil(
                (max(device_minimum, to_device_units(minimum_c)) - device_minimum)
                / step
                - 1e-9
            )
            last_step = floor(
                (min(device_maximum, to_device_units(maximum_c)) - device_minimum)
                / step
                + 1e-9
            )
            if first_step > last_step:
                raise ValueError
            requested_step = floor(
                (to_device_units(target_c) - device_minimum) / step + 0.5
            )
            target_step = min(last_step, max(first_step, requested_step))
            return round(device_minimum + target_step * step, 6)
        except (KeyError, TypeError, ValueError) as err:
            raise HomeAssistantError("invalid_device_temperature_limits") from err

    async def _call(self, service, **data):
        """Send one climate service request and wait for Home Assistant to complete it."""
        await self.hass.services.async_call(
            "climate", service, {"entity_id": self.entity_id, **data}, blocking=True
        )

    async def async_dry(self, target_c, minimum_c, maximum_c):
        """Request Dry mode and its supported target, suppressing duplicate requests."""
        target = self.target(target_c, minimum_c, maximum_c)
        command = ("dry", target)
        if self.last_command == command:
            return
        # Mark ownership before any call: a failed request may still reach hardware.
        self.owned = True
        try:
            if self.last_command is None or self.last_command[0] != "dry":
                await self._call("set_hvac_mode", hvac_mode="dry")
            if target is not None:
                await self._call("set_temperature", temperature=target)
        except (HomeAssistantError, TimeoutError):
            self.last_command = None
            self.last_result = "command_failed"
            raise
        self.requested_at = dt_util.utcnow()
        self.last_command = command
        self.last_result = (
            "dry_requested"
            if target is not None
            else "dry_requested_without_temperature_support"
        )

    async def async_turn_off(self):
        """Stop an owned AC; retain ownership if the stop must be retried."""
        if not self.owned:
            return
        if not self.available:
            self.last_command = None
            raise HomeAssistantError("equipment_unavailable_stop_pending")
        try:
            await self._call("set_hvac_mode", hvac_mode="off")
        except (HomeAssistantError, TimeoutError):
            self.last_command = None
            self.last_result = "stop_failed"
            raise
        self.owned = False
        self.last_command = ("off", None)
        self.last_result = "off_requested"


class ClimateGroupAdapter:
    """Coordinate a zone's drying request across multiple climate entities."""

    def __init__(self, adapters: list[ClimateAdapter]) -> None:
        """Keep the individual adapters so ownership remains device-specific."""
        if not adapters:
            raise ValueError("at least one climate adapter is required")
        self.adapters = adapters

    @property
    def available(self) -> bool:
        """Require every configured ACU to be available before starting a run."""
        return all(adapter.available for adapter in self.adapters)

    @property
    def owned(self) -> bool:
        """Report whether this zone is responsible for stopping any ACU."""
        return any(adapter.owned for adapter in self.adapters)

    @owned.setter
    def owned(self, value: bool) -> None:
        """Mark every ACU owned before a coordinated start request."""
        for adapter in self.adapters:
            adapter.owned = value

    @property
    def last_command(self):
        """Return the shared command when all ACUs agree."""
        commands = {adapter.last_command for adapter in self.adapters}
        return commands.pop() if len(commands) == 1 else None

    @property
    def last_result(self):
        """Expose per-ACU command results for diagnostics."""
        return {
            adapter.entity_id: adapter.last_result for adapter in self.adapters
        }

    def inspect(self):
        """Validate every ACU before the group is considered controllable."""
        return {adapter.entity_id: adapter.inspect() for adapter in self.adapters}

    async def async_dry(self, target_c, minimum_c, maximum_c):
        """Request Dry mode on every ACU, stopping all if any request fails."""
        try:
            for adapter in self.adapters:
                await adapter.async_dry(target_c, minimum_c, maximum_c)
        except (HomeAssistantError, TimeoutError):
            try:
                await self.async_turn_off()
            except (HomeAssistantError, TimeoutError):
                pass
            raise

    async def async_turn_off(self):
        """Attempt to stop every owned ACU even when one stop request fails."""
        first_error = None
        for adapter in self.adapters:
            try:
                await adapter.async_turn_off()
            except (HomeAssistantError, TimeoutError) as err:
                first_error = first_error or err
        if first_error is not None:
            raise first_error
