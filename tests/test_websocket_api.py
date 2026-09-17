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
