"""Controller shell for ZEAL-Dry.

Block 1 intentionally contains no environmental calculations or HVAC control.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant


@dataclass(slots=True)
class ZealDryController:
    """Own the runtime state for one configured ZEAL-Dry zone."""

    hass: HomeAssistant
    entry_id: str
    zone_name: str
    temperature_entity: str
    humidity_entity: str

    async def async_start(self) -> None:
        """Start the controller.

        Runtime listeners and control logic are added by later blocks.
        """

    async def async_stop(self) -> None:
        """Stop the controller and release runtime resources."""
