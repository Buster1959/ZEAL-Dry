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
    hass: HomeAssistant
    entity_id: str
    owned: bool = False
    requested_at: datetime | None = None
    last_command: tuple | None = None
    last_result: str = "not_requested"

    @property
    def available(self):
        state = self.hass.states.get(self.entity_id) if self.entity_id else None
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    def inspect(self):
        if not self.available:
            raise HomeAssistantError("equipment_unavailable")
        state = self.hass.states.get(self.entity_id)
        attrs = state.attributes
        if "dry" not in attrs.get("hvac_modes", []):
            raise HomeAssistantError("dry_mode_unsupported")
        if "off" not in attrs.get("hvac_modes", []):
            raise HomeAssistantError("off_mode_unsupported")
        return attrs

    def target(self, target_c, minimum_c, maximum_c):
        """Intersect configured bounds with the device grid, in device units."""
        attrs = self.inspect()
        if (
            not int(attrs.get("supported_features", 0))
            & ClimateEntityFeature.TARGET_TEMPERATURE
        ):
            return None
        unit = attrs.get("temperature_unit", self.hass.config.units.temperature_unit)
        convert = lambda value: TemperatureConverter.convert(
            value, UnitOfTemperature.CELSIUS, unit
        )
        try:
            low = float(attrs["min_temp"])
            high = float(attrs["max_temp"])
            step = float(attrs.get("target_temp_step", 1))
            if not all(isfinite(v) for v in (low, high, step)) or step <= 0:
                raise ValueError
            first = ceil((max(low, convert(minimum_c)) - low) / step - 1e-9)
            last = floor((min(high, convert(maximum_c)) - low) / step + 1e-9)
            if first > last:
                raise ValueError
            index = min(last, max(first, floor((convert(target_c) - low) / step + 0.5)))
            return round(low + index * step, 6)
        except (KeyError, TypeError, ValueError) as err:
            raise HomeAssistantError("invalid_device_temperature_limits") from err

    async def _call(self, service, **data):
        await self.hass.services.async_call(
            "climate", service, {"entity_id": self.entity_id, **data}, blocking=True
        )

    async def async_dry(self, target_c, minimum_c, maximum_c):
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
