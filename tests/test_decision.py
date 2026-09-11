"""Tests for the deterministic ZEAL-Dry moisture decision engine."""

from datetime import timedelta
import pytest

from custom_components.zeal_dry.decision import MoistureRisk, MoistureThresholds, evaluate_moisture
from custom_components.zeal_dry.environment import build_environmental_reading


def test_within_target_is_normal():
    decision = evaluate_moisture(build_environmental_reading(18.0, 58.0), MoistureThresholds())
    assert decision.demand is False
    assert decision.risk is MoistureRisk.NORMAL


def test_high_rh_still_requires_persistence_when_dew_point_is_safe():
    decision = evaluate_moisture(build_environmental_reading(18.0, 68.0), MoistureThresholds(), timedelta(minutes=10))
    assert decision.demand is False
    assert decision.reason == "persistence_not_met"


def test_persistent_high_rh_demands_drying():
    decision = evaluate_moisture(build_environmental_reading(18.0, 68.0), MoistureThresholds(), timedelta(minutes=15))
    assert decision.demand is True
    assert decision.reason == "rh_above_maximum"


def test_critical_rh_demands_immediate_drying():
    decision = evaluate_moisture(build_environmental_reading(18.0, 78.0), MoistureThresholds())
    assert decision.demand is True
    assert decision.risk is MoistureRisk.CRITICAL


def test_high_dew_point_demands_drying_even_when_rh_is_below_maximum():
    # Warm air can carry substantial moisture while RH looks comparatively benign.
    decision = evaluate_moisture(build_environmental_reading(26.0, 60.0), MoistureThresholds())
    assert decision.demand is True
    assert decision.reason == "dew_point_high"


def test_critical_dew_point_is_immediate():
    decision = evaluate_moisture(build_environmental_reading(28.0, 60.0), MoistureThresholds())
    assert decision.demand is True
    assert decision.risk is MoistureRisk.CRITICAL
    assert decision.reason == "dew_point_critical"


def test_same_rh_can_produce_different_moisture_decisions():
    cool = evaluate_moisture(build_environmental_reading(12.0, 60.0), MoistureThresholds())
    warm = evaluate_moisture(build_environmental_reading(26.0, 60.0), MoistureThresholds())
    assert cool.demand is False
    assert warm.demand is True


def test_missing_reading_is_unknown_and_safe():
    decision = evaluate_moisture(None, MoistureThresholds())
    assert decision.demand is False
    assert decision.risk is MoistureRisk.UNKNOWN


@pytest.mark.parametrize("preferred,maximum,critical", [(65,60,75),(60,75,75),(0,65,75),(60,65,101)])
def test_invalid_rh_threshold_order_rejected(preferred, maximum, critical):
    with pytest.raises(ValueError):
        MoistureThresholds(preferred_rh=preferred, maximum_rh=maximum, critical_rh=critical)


def test_invalid_dew_point_threshold_order_rejected():
    with pytest.raises(ValueError):
        MoistureThresholds(preferred_dew_point_c=15.0, maximum_dew_point_c=12.0, critical_dew_point_c=17.0)
