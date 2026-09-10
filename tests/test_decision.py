"""Tests for the deterministic ZEAL-Dry moisture decision engine."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.zeal_dry.decision import (
    MoistureRisk,
    MoistureThresholds,
    evaluate_moisture,
)
from custom_components.zeal_dry.environment import build_environmental_reading


def test_within_target_is_normal():
    """RH at or below preferred should not demand drying."""
    decision = evaluate_moisture(
        build_environmental_reading(18.0, 58.0),
        MoistureThresholds(),
    )
    assert decision.demand is False
    assert decision.risk is MoistureRisk.NORMAL
    assert decision.reason == "within_target"


def test_between_preferred_and_maximum_is_elevated():
    """Elevated RH should be visible without demanding action."""
    decision = evaluate_moisture(
        build_environmental_reading(18.0, 63.0),
        MoistureThresholds(),
    )
    assert decision.demand is False
    assert decision.risk is MoistureRisk.ELEVATED
    assert decision.reason == "rh_elevated"


def test_maximum_requires_persistence():
    """Normal high humidity should not demand drying immediately."""
    decision = evaluate_moisture(
        build_environmental_reading(18.0, 68.0),
        MoistureThresholds(high_rh_persistence=timedelta(minutes=15)),
        timedelta(minutes=10),
    )
    assert decision.demand is False
    assert decision.reason == "persistence_not_met"


def test_persistent_high_humidity_demands_drying():
    """High RH beyond persistence should create a drying demand."""
    decision = evaluate_moisture(
        build_environmental_reading(18.0, 68.0),
        MoistureThresholds(high_rh_persistence=timedelta(minutes=15)),
        timedelta(minutes=15),
    )
    assert decision.demand is True
    assert decision.risk is MoistureRisk.HIGH
    assert decision.reason == "rh_above_maximum"


def test_critical_humidity_demands_immediate_protection():
    """Critical RH should produce immediate demand in the baseline model."""
    decision = evaluate_moisture(
        build_environmental_reading(18.0, 78.0),
        MoistureThresholds(),
    )
    assert decision.demand is True
    assert decision.risk is MoistureRisk.CRITICAL
    assert decision.reason == "rh_critical"


def test_missing_reading_is_unknown_and_safe():
    """Missing environmental data must not create an active demand."""
    decision = evaluate_moisture(None, MoistureThresholds())
    assert decision.demand is False
    assert decision.risk is MoistureRisk.UNKNOWN
    assert decision.reason == "sensor_unavailable"


@pytest.mark.parametrize(
    ("preferred", "maximum", "critical"),
    [
        (65, 60, 75),
        (60, 75, 75),
        (0, 65, 75),
        (60, 65, 101),
    ],
)
def test_invalid_threshold_order_rejected(preferred, maximum, critical):
    """Thresholds must remain strictly ordered."""
    with pytest.raises(ValueError):
        MoistureThresholds(
            preferred_rh=preferred,
            maximum_rh=maximum,
            critical_rh=critical,
        )
