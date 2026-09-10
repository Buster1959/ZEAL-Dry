"""Pure environmental calculations for ZEAL-Dry.

This module contains no Home Assistant service calls and no HVAC control.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log


class EnvironmentalInputError(ValueError):
    """Raised when environmental input cannot be used safely."""


@dataclass(frozen=True, slots=True)
class EnvironmentalReading:
    """Validated environmental values for one point in time."""

    temperature_c: float
    relative_humidity: float
    dew_point_c: float
    dew_point_spread_c: float


def validate_temperature(value: float) -> float:
    """Validate a Celsius temperature reading."""
    value = float(value)
    if not isfinite(value):
        raise EnvironmentalInputError("temperature is not finite")
    if value < -50.0 or value > 80.0:
        raise EnvironmentalInputError("temperature is outside the supported range")
    return value


def validate_humidity(value: float) -> float:
    """Validate a relative-humidity percentage."""
    value = float(value)
    if not isfinite(value):
        raise EnvironmentalInputError("humidity is not finite")
    if value <= 0.0 or value > 100.0:
        raise EnvironmentalInputError("humidity must be greater than 0 and at most 100")
    return value


def calculate_dew_point_c(temperature_c: float, relative_humidity: float) -> float:
    """Calculate dew point in Celsius using the Magnus approximation."""
    temperature_c = validate_temperature(temperature_c)
    relative_humidity = validate_humidity(relative_humidity)

    a = 17.62
    b = 243.12
    gamma = log(relative_humidity / 100.0) + (a * temperature_c) / (b + temperature_c)
    return (b * gamma) / (a - gamma)


def build_environmental_reading(
    temperature_c: float,
    relative_humidity: float,
) -> EnvironmentalReading:
    """Build one validated environmental reading."""
    temperature_c = validate_temperature(temperature_c)
    relative_humidity = validate_humidity(relative_humidity)
    dew_point_c = calculate_dew_point_c(temperature_c, relative_humidity)

    return EnvironmentalReading(
        temperature_c=temperature_c,
        relative_humidity=relative_humidity,
        dew_point_c=dew_point_c,
        dew_point_spread_c=temperature_c - dew_point_c,
    )
