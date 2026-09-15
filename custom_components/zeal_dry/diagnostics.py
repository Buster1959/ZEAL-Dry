"""Diagnostics for ZEAL-Dry."""

from __future__ import annotations

from dataclasses import asdict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_CONTROLLERS, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict:
    """Return non-sensitive diagnostics for one ZEAL-Dry zone."""
    controller = hass.data.get(DOMAIN, {}).get(DATA_CONTROLLERS, {}).get(entry.entry_id)
    if controller is None:
        return {"controller_loaded": False}
    reading = getattr(controller, "environmental_reading", None)
    decision = getattr(controller, "decision", None)
    thresholds = getattr(controller, "thresholds", None)
    state_snapshot = getattr(controller, "state_snapshot", None)
    proposed_setpoint = getattr(controller, "proposed_setpoint", None)
    setpoint_config = getattr(controller, "setpoint_config", None)

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
        },
        "controller_loaded": controller is not None,
        "zone": {
            "name": getattr(controller, "zone_name", None),
            "temperature_entity": getattr(controller, "temperature_entity", None),
            "humidity_entity": getattr(controller, "humidity_entity", None),
        },
        "environment": asdict(reading) if reading is not None else None,
        "decision": asdict(decision) if decision is not None else None,
        "proposed_dry_setpoint": (
            asdict(proposed_setpoint) if proposed_setpoint is not None else None
        ),
        "dry_setpoint_config": (
            asdict(setpoint_config) if setpoint_config is not None else None
        ),
        "controller_state": (
            {
                "state": state_snapshot.state.value,
                "reason": state_snapshot.reason,
                "entered_at": (
                    state_snapshot.entered_at.isoformat()
                    if state_snapshot.entered_at is not None
                    else None
                ),
                "drying_started_at": (
                    state_snapshot.drying_started_at.isoformat()
                    if state_snapshot.drying_started_at is not None
                    else None
                ),
                "drying_stopped_at": (
                    state_snapshot.drying_stopped_at.isoformat()
                    if state_snapshot.drying_stopped_at is not None
                    else None
                ),
            }
            if state_snapshot is not None
            else None
        ),
        "thresholds": (
            {
                "preferred_rh": thresholds.preferred_rh,
                "maximum_rh": thresholds.maximum_rh,
                "critical_rh": thresholds.critical_rh,
                "high_rh_persistence_seconds": int(
                    thresholds.high_rh_persistence.total_seconds()
                ),
            }
            if thresholds is not None
            else None
        ),
        "above_maximum_since": (
            getattr(controller, "above_maximum_since", None).isoformat()
            if getattr(controller, "above_maximum_since", None) is not None
            else None
        ),
        "input_error": getattr(controller, "input_error", None),
        "last_updated": (
            getattr(controller, "last_updated", None).isoformat()
            if getattr(controller, "last_updated", None) is not None
            else None
        ),
        "settings": controller.settings.as_dict(),
        "command_error": controller.command_error,
        "command_result": getattr(controller.actuator, "last_result", None),
        "stop_pending": bool(getattr(controller.actuator, "owned", False)),
        "block": 7,
        "control_active": controller.control_mode == "climate"
        and controller.state_snapshot.state.value == "drying",
    }
