"""Conservative restart policy, independent from Home Assistant services."""

from dataclasses import asdict
from datetime import datetime

from .state_machine import ControllerState, StateSnapshot


def serialize(snapshot):
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in asdict(snapshot).items()
    }


def restore(data, now):
    """Never resume an interrupted run; require a fresh rest period on startup."""
    started = None
    if isinstance(data, dict):
        try:
            value = data.get("drying_started_at")
            started = datetime.fromisoformat(value) if value else None
            if started and (started.tzinfo is None or started > now):
                started = None
        except (ValueError, TypeError):
            pass
    return StateSnapshot(
        ControllerState.PROTECTION, now, started, now, "restart_rest_time_active"
    )
