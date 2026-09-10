"""Tests for the ZEAL-Dry controller state machine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.zeal_dry.decision import DryingDecision, MoistureRisk
from custom_components.zeal_dry.state_machine import (
    ControllerState,
    StateSnapshot,
    TimingConfig,
    next_state,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
TIMING = TimingConfig(
    minimum_run=timedelta(minutes=20),
    minimum_rest=timedelta(minutes=10),
    recovery_period=timedelta(minutes=10),
    maximum_run=timedelta(hours=3),
)


def decision(demand: bool, risk: MoistureRisk, reason: str) -> DryingDecision:
    return DryingDecision(demand=demand, risk=risk, reason=reason, explanation=reason)


def test_normal_condition_is_idle():
    result = next_state(
        StateSnapshot(),
        decision(False, MoistureRisk.NORMAL, "within_target"),
        NOW,
        TIMING,
        action_permitted=False,
    )
    assert result.state is ControllerState.IDLE


def test_elevated_condition_is_monitoring():
    result = next_state(
        StateSnapshot(),
        decision(False, MoistureRisk.ELEVATED, "rh_elevated"),
        NOW,
        TIMING,
        action_permitted=False,
    )
    assert result.state is ControllerState.MONITORING


def test_demand_without_control_remains_monitoring():
    result = next_state(
        StateSnapshot(),
        decision(True, MoistureRisk.HIGH, "rh_above_maximum"),
        NOW,
        TIMING,
        action_permitted=False,
    )
    assert result.state is ControllerState.MONITORING
    assert result.reason == "drying_required_control_not_enabled"


def test_demand_with_control_enters_drying():
    result = next_state(
        StateSnapshot(),
        decision(True, MoistureRisk.HIGH, "rh_above_maximum"),
        NOW,
        TIMING,
        action_permitted=True,
    )
    assert result.state is ControllerState.DRYING
    assert result.drying_started_at == NOW


def test_minimum_run_prevents_early_stop():
    snapshot = StateSnapshot(
        state=ControllerState.DRYING,
        entered_at=NOW,
        drying_started_at=NOW,
        reason="rh_above_maximum",
    )
    result = next_state(
        snapshot,
        decision(False, MoistureRisk.NORMAL, "within_target"),
        NOW + timedelta(minutes=5),
        TIMING,
        action_permitted=True,
    )
    assert result.state is ControllerState.DRYING
    assert result.reason == "minimum_run_time_active"


def test_drying_moves_to_recovery_after_minimum_run():
    snapshot = StateSnapshot(
        state=ControllerState.DRYING,
        entered_at=NOW,
        drying_started_at=NOW,
        reason="rh_above_maximum",
    )
    result = next_state(
        snapshot,
        decision(False, MoistureRisk.NORMAL, "within_target"),
        NOW + timedelta(minutes=25),
        TIMING,
        action_permitted=True,
    )
    assert result.state is ControllerState.RECOVERY


def test_maximum_runtime_moves_to_protection():
    snapshot = StateSnapshot(
        state=ControllerState.DRYING,
        entered_at=NOW,
        drying_started_at=NOW,
        reason="rh_above_maximum",
    )
    result = next_state(
        snapshot,
        decision(True, MoistureRisk.CRITICAL, "rh_critical"),
        NOW + timedelta(hours=3),
        TIMING,
        action_permitted=True,
    )
    assert result.state is ControllerState.PROTECTION
    assert result.reason == "maximum_run_time_reached"


def test_unknown_inputs_go_to_fault():
    result = next_state(
        StateSnapshot(),
        decision(False, MoistureRisk.UNKNOWN, "sensor_unavailable"),
        NOW,
        TIMING,
        action_permitted=False,
    )
    assert result.state is ControllerState.FAULT
