"""Generic actuator adapters for ZEAL-Dry.

The switch adapter is intentionally supplier-neutral and is used first with the
versioned dummy ACU test fixture. Real climate control is added separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant


@dataclass(slots=True)
class SwitchActuator:
    """Control a Home Assistant switch as a simple drying actuator."""

    hass: HomeAssistant
    entity_id: str

    @property
    def available(self) -> bool:
        """Return whether the configured switch currently exists."""
        return self.hass.states.get(self.entity_id) is not None

    @property
    def is_on(self) -> bool:
        """Return whether the actuator is currently on."""
        state = self.hass.states.get(self.entity_id)
        return state is not None and state.state == STATE_ON

    async def async_turn_on(self) -> None:
        """Turn on the drying actuator, avoiding duplicate commands."""
        if not self.available or self.is_on:
            return
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": self.entity_id},
            blocking=True,
        )

    async def async_turn_off(self) -> None:
        """Turn off the drying actuator, avoiding duplicate commands."""
        if not self.available or not self.is_on:
            return
        await self.hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": self.entity_id},
            blocking=True,
        )
