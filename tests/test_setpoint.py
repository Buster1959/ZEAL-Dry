"""Tests for ZEAL-Dry Dry setpoint strategy."""

from __future__ import annotations

import pytest

from custom_components.zeal_dry.setpoint import (
    DrySetpointConfig,
    calculate_dry_setpoint,
)


def test_room_relative_target():
    """17.2 C plus 0.5 C should request 17.7 C and apply 18 C at 1 C steps."""
    result = calculate_dry_setpoint(17.2)
    assert result.raw_target_c == pytest.approx(17.7)
    assert result.applied_target_c == pytest.approx(18.0)


def test_target_clamped_to_minimum():
    """A cold room must not request below the configured Dry minimum."""
    result = calculate_dry_setpoint(12.0)
    assert result.constrained_target_c == 16.0
    assert result.applied_target_c == 16.0


def test_target_clamped_to_maximum():
    """A warm room must not request above the configured Dry maximum."""
    result = calculate_dry_setpoint(24.0)
    assert result.constrained_target_c == 20.0
    assert result.applied_target_c == 20.0


def test_half_degree_equipment_step():
    """Strategy must support equipment with a different setpoint resolution."""
    config = DrySetpointConfig(offset_c=0.5, minimum_c=15.0, maximum_c=22.0, step_c=0.5)
    result = calculate_dry_setpoint(17.2, config)
    assert result.applied_target_c == 17.5


def test_invalid_step_rejected():
    """An invalid equipment step must fail during configuration."""
    with pytest.raises(ValueError):
        DrySetpointConfig(step_c=0)
