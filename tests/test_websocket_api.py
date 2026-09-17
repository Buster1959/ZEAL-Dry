"""Test the panel's live status contract."""

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.util import dt as dt_util

from custom_components.zeal_dry.websocket_api import _status


def test_restart_rest_countdown_is_explained():
    """A protected restart must look like a countdown, not an unexplained fault."""
    stopped_at = dt_util.utcnow() - timedelta(minutes=2)
    controller = SimpleNamespace(
        command_error=None,
        decision=SimpleNamespace(demand=True),
        rest_cause="restart",
        timing=SimpleNamespace(
            minimum_rest=timedelta(minutes=10),
            minimum_run=timedelta(minutes=20),
            recovery_period=timedelta(minutes=10),
        ),
        state_snapshot=SimpleNamespace(
            state=SimpleNamespace(value="idle"),
            reason="minimum_rest_time_active",
            drying_started_at=None,
            drying_stopped_at=stopped_at,
        ),
    )

    status = _status(controller)

    assert status["title"] == "Awaiting start"
    assert status["detail"] == "Following restart"
    assert 470 <= status["remaining_seconds"] <= 480


def test_drying_status_reports_elapsed_runtime():
    """Expose the current Dry run age for the live HH:MM:SS display."""
    started_at = dt_util.utcnow() - timedelta(hours=1, minutes=2, seconds=3)
    controller = SimpleNamespace(
        command_error=None,
        decision=SimpleNamespace(demand=True),
        rest_cause=None,
        timing=SimpleNamespace(
            minimum_rest=timedelta(minutes=10),
            minimum_run=timedelta(minutes=20),
            recovery_period=timedelta(minutes=10),
        ),
        state_snapshot=SimpleNamespace(
            state=SimpleNamespace(value="drying"),
            reason="moisture_demand",
            drying_started_at=started_at,
            drying_stopped_at=None,
        ),
    )

    status = _status(controller)

    assert status["title"] == "Drying active"
    assert 3722 <= status["elapsed_seconds"] <= 3723
