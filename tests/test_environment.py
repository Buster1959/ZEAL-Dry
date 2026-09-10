"""Tests for the pure ZEAL-Dry environmental model."""

from __future__ import annotations

import pytest

from custom_components.zeal_dry.environment import (
    EnvironmentalInputError,
    build_environmental_reading,
    calculate_dew_point_c,
    validate_humidity,
    validate_temperature,
)


@pytest.mark.parametrize(
    ("temperature", "humidity", "expected"),
    [
        (20.0, 50.0, 9.3),
        (17.2, 73.0, 12.4),
        (25.0, 80.0, 21.3),
    ],
)
def test_known_dew_points(temperature, humidity, expected):
    """Known temperature/RH pairs should give expected Magnus dew points."""
    assert calculate_dew_point_c(temperature, humidity) == pytest.approx(expected, abs=0.15)


def test_reading_contains_dew_point_spread():
    """Environmental reading should expose temperature-to-dew-point spread."""
    reading = build_environmental_reading(20.0, 50.0)
    assert reading.dew_point_spread_c == pytest.approx(
        reading.temperature_c - reading.dew_point_c
    )


@pytest.mark.parametrize("value", [0, -1, 101, float("nan"), float("inf")])
def test_invalid_humidity_rejected(value):
    """Invalid humidity must fail safely."""
    with pytest.raises(EnvironmentalInputError):
        validate_humidity(value)


@pytest.mark.parametrize("value", [-51, 81, float("nan"), float("inf")])
def test_invalid_temperature_rejected(value):
    """Implausible/non-finite temperatures must fail safely."""
    with pytest.raises(EnvironmentalInputError):
        validate_temperature(value)
