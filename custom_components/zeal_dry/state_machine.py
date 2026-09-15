"""Deterministic ZEAL-Dry controller state machine.

The state machine decides controller state only. It never calls Home Assistant
services and contains no supplier-specific equipment logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .decision import DryingDecision, MoistureRisk


class ControllerState(StrEnum):
    """ZEAL-Dry controller states."""

    IDLE = "idle"
    MONITORING = "monitoring"
    DRYING = "drying"
    RECOVERY = "recovery"
    PROTECTION = "protection"
    INHIBITED = "inhibited"
    FAULT = "fault"


@dataclass(frozen=True, slots=True)
class TimingConfig:
    """Timing protections used by the state machine."""

    minimum_run: timedelta = timedelta(minutes=20)
    minimum_rest: timedelta = timedelta(minutes=10)
    recovery_period: timedelta = timedelta(minutes=10)
    maximum_run: timedelta = timedelta(hours=3)


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """State and timestamps required to make the next transition."""

    state: ControllerState = ControllerState.IDLE
    entered_at: datetime | None = None
    drying_started_at: datetime | None = None
    drying_stopped_at: datetime | None = None
    reason: str = "initial"


def next_state(
    snapshot: StateSnapshot,
    decision: DryingDecision,
    now: datetime,
    timing: TimingConfig,
    *,
    action_permitted: bool,
    inhibited: bool = False,
) -> StateSnapshot:
    """Return the next deterministic controller state."""
    if inhibited:
        return _change(snapshot, ControllerState.INHIBITED, now, "automatic_control_inhibited")

    if decision.risk is MoistureRisk.UNKNOWN:
        return _change(snapshot, ControllerState.FAULT, now, decision.reason)

    if snapshot.state is ControllerState.DRYING and not action_permitted:
        return _change(snapshot, ControllerState.FAULT, now, "equipment_unavailable")

    if snapshot.state is ControllerState.DRYING:
        if snapshot.drying_started_at is not None:
            runtime = now - snapshot.drying_started_at
            if runtime >= timing.maximum_run:
                return StateSnapshot(
                    state=ControllerState.PROTECTION,
                    entered_at=now,
                    drying_started_at=snapshot.drying_started_at,
                    drying_stopped_at=now,
                    reason="maximum_run_time_reached",
                )
            if not decision.demand and runtime < timing.minimum_run:
                return StateSnapshot(
                    state=ControllerState.DRYING,
                    entered_at=snapshot.entered_at,
                    drying_started_at=snapshot.drying_started_at,
                    drying_stopped_at=snapshot.drying_stopped_at,
                    reason="minimum_run_time_active",
                )

        if decision.demand or decision.risk is MoistureRisk.ELEVATED:
            return StateSnapshot(
                state=ControllerState.DRYING,
                entered_at=snapshot.entered_at,
                drying_started_at=snapshot.drying_started_at or now,
                drying_stopped_at=snapshot.drying_stopped_at,
                reason=decision.reason,
            )

        return StateSnapshot(
            state=ControllerState.RECOVERY,
            entered_at=now,
            drying_started_at=snapshot.drying_started_at,
            drying_stopped_at=now,
            reason="drying_demand_cleared",
        )

    if snapshot.state is ControllerState.RECOVERY:
        stopped_at = snapshot.drying_stopped_at or snapshot.entered_at
        if stopped_at is not None and now - stopped_at < timing.recovery_period:
            return snapshot

    if decision.demand:
        if not action_permitted:
            return _change(snapshot, ControllerState.MONITORING, now, "drying_required_control_not_enabled")

        if snapshot.drying_stopped_at is not None:
            if now - snapshot.drying_stopped_at < timing.minimum_rest:
                return _change(snapshot, ControllerState.MONITORING, now, "minimum_rest_time_active")

        return StateSnapshot(
            state=ControllerState.DRYING,
            entered_at=now,
            drying_started_at=now,
            drying_stopped_at=snapshot.drying_stopped_at,
            reason=decision.reason,
        )

    if decision.risk is MoistureRisk.ELEVATED:
        return _change(snapshot, ControllerState.MONITORING, now, decision.reason)

    return _change(snapshot, ControllerState.IDLE, now, decision.reason)


def _change(
    snapshot: StateSnapshot,
    state: ControllerState,
    now: datetime,
    reason: str,
) -> StateSnapshot:
    """Change state while preserving timing history."""
    return StateSnapshot(
        state=state,
        entered_at=snapshot.entered_at if snapshot.state is state else now,
        drying_started_at=snapshot.drying_started_at,
        drying_stopped_at=(now if snapshot.state is ControllerState.DRYING and state is not ControllerState.DRYING else snapshot.drying_stopped_at),
        reason=reason,
    )
