from datetime import UTC, datetime, timedelta

from custom_components.zeal_dry.decision import DryingDecision, MoistureRisk
from custom_components.zeal_dry.restoration import restore
from custom_components.zeal_dry.state_machine import (
    ControllerState,
    StateSnapshot,
    TimingConfig,
    next_state,
)

NOW = datetime(2026, 9, 15, tzinfo=UTC)
DEMAND = DryingDecision(True, MoistureRisk.HIGH, "high", "High moisture")


def test_startup_never_bypasses_rest():
    for data in (None, {}, {"state": "drying"}, {"drying_started_at": "bad"}):
        snapshot = restore(data, NOW)
        assert (
            next_state(
                snapshot, DEMAND, NOW, TimingConfig(), action_permitted=True
            ).state
            != ControllerState.DRYING
        )
        assert (
            next_state(
                snapshot,
                DEMAND,
                NOW + timedelta(minutes=10),
                TimingConfig(),
                action_permitted=True,
            ).state
            == ControllerState.DRYING
        )


def test_fault_and_inhibit_record_stop():
    running = StateSnapshot(ControllerState.DRYING, NOW, NOW)
    fault = next_state(running, DEMAND, NOW, TimingConfig(), action_permitted=False)
    assert fault.state == ControllerState.FAULT
    assert fault.drying_stopped_at == NOW
    assert (
        next_state(fault, DEMAND, NOW, TimingConfig(), action_permitted=True).state
        != ControllerState.DRYING
    )
    inhibited = next_state(
        running, DEMAND, NOW, TimingConfig(), action_permitted=True, inhibited=True
    )
    assert inhibited.drying_stopped_at == NOW
