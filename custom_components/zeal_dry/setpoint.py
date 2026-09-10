"""Supplier-neutral Dry setpoint strategies for ZEAL-Dry."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True, slots=True)
class DrySetpointConfig:
    """Configuration for the room-relative Dry target strategy."""

    offset_c: float = 0.5
    minimum_c: float = 16.0
    maximum_c: float = 20.0
    step_c: float = 1.0

    def __post_init__(self) -> None:
        if self.minimum_c > self.maximum_c:
            raise ValueError("minimum Dry target cannot exceed maximum")
        if self.step_c <= 0:
            raise ValueError("Dry target step must be greater than zero")


@dataclass(frozen=True, slots=True)
class DrySetpointResult:
    """Calculated Dry target before any equipment command is issued."""

    room_temperature_c: float
    offset_c: float
    raw_target_c: float
    constrained_target_c: float
    applied_target_c: float


def calculate_dry_setpoint(
    room_temperature_c: float,
    config: DrySetpointConfig | None = None,
) -> DrySetpointResult:
    """Calculate a room-relative Dry target, clamp it, then round to device step."""
    config = config or DrySetpointConfig()
    raw = float(room_temperature_c) + config.offset_c
    constrained = min(max(raw, config.minimum_c), config.maximum_c)

    steps = (constrained - config.minimum_c) / config.step_c
    rounded_steps = floor(steps + 0.5)
    applied = config.minimum_c + (rounded_steps * config.step_c)
    applied = min(max(applied, config.minimum_c), config.maximum_c)

    return DrySetpointResult(
        room_temperature_c=float(room_temperature_c),
        offset_c=config.offset_c,
        raw_target_c=raw,
        constrained_target_c=constrained,
        applied_target_c=applied,
    )
