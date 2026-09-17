"""Verify explainable outdoor dew-point outlook levels."""

from datetime import timedelta

from homeassistant.util import dt as dt_util

from custom_components.zeal_dry.decision import MoistureThresholds
from custom_components.zeal_dry.environment import build_environmental_reading
from custom_components.zeal_dry.forecast import (
    ForecastLevel,
    ForecastPoint,
    evaluate_dew_point_outlook,
)


def test_rapid_critical_dew_point_rise_is_critical():
    """A fast rise through the critical threshold should be prominent."""
    now = dt_util.utcnow()
    current = build_environmental_reading(20, 55)
    points = [
        ForecastPoint(now + timedelta(hours=3), build_environmental_reading(27, 70))
    ]

    outlook = evaluate_dew_point_outlook(
        current, points, MoistureThresholds(), now
    )

    assert outlook.level == ForecastLevel.CRITICAL
    assert outlook.rise_c_per_hour >= 0.75
    assert "rise rapidly" in outlook.explanation


def test_moderate_rise_through_high_threshold_is_medium():
    """A meaningful but slower moisture increase should produce Medium."""
    now = dt_util.utcnow()
    current = build_environmental_reading(20, 60)
    points = [
        ForecastPoint(now + timedelta(hours=4), build_environmental_reading(22, 68))
    ]

    outlook = evaluate_dew_point_outlook(
        current, points, MoistureThresholds(), now
    )

    assert outlook.level == ForecastLevel.MEDIUM
    assert "forecast to rise" in outlook.explanation


def test_stable_high_dew_point_is_safe_from_rapid_rise():
    """The outlook describes change, so stable outdoor moisture is not escalation."""
    now = dt_util.utcnow()
    current = build_environmental_reading(24, 70)
    points = [
        ForecastPoint(now + timedelta(hours=3), build_environmental_reading(24, 71))
    ]

    outlook = evaluate_dew_point_outlook(
        current, points, MoistureThresholds(), now
    )

    assert outlook.level == ForecastLevel.SAFE
    assert "No rapid" in outlook.explanation


def test_missing_forecast_is_explicitly_unavailable():
    """Missing forecasts must not be presented as safe."""
    now = dt_util.utcnow()
    outlook = evaluate_dew_point_outlook(
        build_environmental_reading(20, 60), [], MoistureThresholds(), now
    )

    assert outlook.level == ForecastLevel.UNAVAILABLE
