"""Authenticated WebSocket boundary for the ZEAL-Dry panel."""

from __future__ import annotations

from dataclasses import replace

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_CLIMATE_ENTITIES,
    CONF_HUMIDITY_ENTITY,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TEMPERATURE_ENTITY,
    DATA_CONTROLLERS,
    DOMAIN,
)
from .hvac import ClimateAdapter
from .settings import NUMBER_SETTINGS, OPTION_SETTINGS, SELECT_SETTINGS

_REGISTERED = f"{DOMAIN}_websocket_registered"


def async_register_commands(hass: HomeAssistant) -> None:
    """Register panel commands once across config-entry reloads."""
    if hass.data.get(_REGISTERED):
        return
    for command in (ws_list_entries, ws_get_configuration, ws_set_profile, ws_save_setup):
        websocket_api.async_register_command(hass, command)
    hass.data[_REGISTERED] = True


def _controller(hass: HomeAssistant, entry_id: str):
    """Return one loaded zone controller."""
    return hass.data.get(DOMAIN, {}).get(DATA_CONTROLLERS, {}).get(entry_id)


def _send_not_found(connection, msg) -> None:
    connection.send_error(
        msg["id"], websocket_api.ERR_NOT_FOUND, "ZEAL-Dry zone is not loaded"
    )


def _remaining_seconds(controller) -> int | None:
    """Return a live protection countdown for the Overview banner."""
    now = dt_util.utcnow()
    snapshot = controller.state_snapshot
    deadline = None
    if snapshot.reason == "minimum_rest_time_active" and snapshot.drying_stopped_at:
        deadline = snapshot.drying_stopped_at + controller.timing.minimum_rest
    elif snapshot.reason == "minimum_run_time_active" and snapshot.drying_started_at:
        deadline = snapshot.drying_started_at + controller.timing.minimum_run
    elif snapshot.state.value == "recovery" and snapshot.drying_stopped_at:
        deadline = snapshot.drying_stopped_at + controller.timing.recovery_period
    if deadline is None:
        return None
    return max(0, int((deadline - now).total_seconds()))


def _status(controller) -> dict:
    """Build one stable, human-readable status contract for the panel."""
    snapshot = controller.state_snapshot
    remaining = _remaining_seconds(controller)
    if controller.command_error or snapshot.state.value == "fault":
        title = "Control fault"
        detail = controller.command_error or snapshot.reason
        tone = "fault"
    elif snapshot.reason == "minimum_rest_time_active":
        title = "Awaiting start"
        detail = (
            "Following restart"
            if controller.rest_cause == "restart"
            else "Minimum ACU rest"
        )
        tone = "waiting"
    elif snapshot.state.value == "drying":
        title = "Drying active"
        detail = snapshot.reason
        tone = "drying"
    elif snapshot.state.value == "inhibited":
        title = "Control inhibited"
        detail = "Operating profile is Off"
        tone = "inhibited"
    elif controller.decision and controller.decision.demand:
        title = "Moisture demand active"
        detail = snapshot.reason
        tone = "demand"
    else:
        title = "Monitoring"
        detail = snapshot.reason
        tone = "normal"
    return {
        "title": title,
        "detail": detail,
        "tone": tone,
        "remaining_seconds": remaining,
    }


def _catalog(hass: HomeAssistant) -> dict:
    """Return eligible entities for administrator Setup selectors."""
    temperature = []
    humidity = []
    climates = []
    for state in hass.states.async_all():
        label = state.attributes.get("friendly_name", state.entity_id)
        item = {"entity_id": state.entity_id, "name": label, "state": state.state}
        if state.domain == "sensor":
            device_class = state.attributes.get("device_class")
            if device_class == "temperature":
                temperature.append(item)
            elif device_class == "humidity":
                humidity.append(item)
        elif state.domain == "climate":
            modes = state.attributes.get("hvac_modes", [])
            if "dry" in modes and "off" in modes:
                climates.append(item)
    key = lambda item: (item["name"].casefold(), item["entity_id"])
    return {
        "temperature_sensors": sorted(temperature, key=key),
        "humidity_sensors": sorted(humidity, key=key),
        "climate_entities": sorted(climates, key=key),
    }


def _configuration(hass: HomeAssistant, entry_id: str) -> dict:
    """Return live state, saved setup and selector catalog."""
    controller = _controller(hass, entry_id)
    entry = hass.config_entries.async_get_entry(entry_id)
    climates = entry.data.get(CONF_CLIMATE_ENTITIES)
    if climates is None:
        climates = (
            [entry.data[CONF_CLIMATE_ENTITY]]
            if entry.data.get(CONF_CLIMATE_ENTITY)
            else []
        )
    reading = controller.environmental_reading
    decision = controller.decision
    return {
        "entry_id": entry_id,
        "title": entry.title,
        "zone_name": controller.zone_name,
        "control_mode": controller.control_mode,
        "status": _status(controller),
        "controller": {
            "state": controller.state_snapshot.state.value,
            "reason": controller.state_snapshot.reason,
            "fault": controller.command_error,
            "risk": decision.risk.value if decision else "unknown",
            "demand": decision.demand if decision else None,
            "temperature_c": reading.temperature_c if reading else None,
            "humidity": reading.relative_humidity if reading else None,
            "dew_point_c": reading.dew_point_c if reading else None,
            "dew_point_spread_c": reading.dew_point_spread_c if reading else None,
            "proposed_target_c": (
                controller.proposed_setpoint.applied_target_c
                if controller.proposed_setpoint
                else None
            ),
            "acus": [
                {
                    "entity_id": adapter.entity_id,
                    "available": adapter.available,
                    "state": (
                        hass.states.get(adapter.entity_id).state
                        if hass.states.get(adapter.entity_id)
                        else "missing"
                    ),
                    "owned": adapter.owned,
                    "last_result": adapter.last_result,
                }
                for adapter in controller._climate_adapters()
            ],
        },
        "setup": {
            "show_in_sidebar": entry.options.get(CONF_SHOW_IN_SIDEBAR, True),
            "temperature_entity": entry.data.get(CONF_TEMPERATURE_ENTITY),
            "humidity_entity": entry.data.get(CONF_HUMIDITY_ENTITY),
            "climate_entities": climates,
            "settings": controller.settings.as_dict(),
        },
        "catalog": _catalog(hass),
    }


@websocket_api.websocket_command({vol.Required("type"): "zeal_dry/list_entries"})
@callback
def ws_list_entries(hass, connection, msg) -> None:
    entries = [
        {"entry_id": entry.entry_id, "title": entry.title}
        for entry in hass.config_entries.async_entries(DOMAIN)
        if _controller(hass, entry.entry_id) is not None
    ]
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal_dry/get_configuration",
        vol.Required("entry_id"): str,
    }
)
@callback
def ws_get_configuration(hass, connection, msg) -> None:
    if _controller(hass, msg["entry_id"]) is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], _configuration(hass, msg["entry_id"]))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal_dry/set_profile",
        vol.Required("entry_id"): str,
        vol.Required("profile"): vol.In(SELECT_SETTINGS["profile"][1]),
    }
)
@websocket_api.async_response
async def ws_set_profile(hass, connection, msg) -> None:
    controller = _controller(hass, msg["entry_id"])
    if controller is None:
        _send_not_found(connection, msg)
        return
    await controller.async_update_settings(profile=msg["profile"])
    connection.send_result(msg["id"], _configuration(hass, msg["entry_id"]))


_SETTING_SCHEMA = {
    vol.Required(key): vol.Coerce(float) for key in NUMBER_SETTINGS | OPTION_SETTINGS
} | {
    vol.Required(key): vol.In(choices) for key, (_, choices) in SELECT_SETTINGS.items()
}


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "zeal_dry/save_setup",
        vol.Required("entry_id"): str,
        vol.Required("temperature_entity"): str,
        vol.Required("humidity_entity"): str,
        vol.Required("climate_entities"): [str],
        vol.Required("show_in_sidebar"): bool,
        vol.Required("settings"): _SETTING_SCHEMA,
    }
)
@websocket_api.async_response
async def ws_save_setup(hass, connection, msg) -> None:
    controller = _controller(hass, msg["entry_id"])
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if controller is None or entry is None:
        _send_not_found(connection, msg)
        return
    try:
        for entity_id, domain in (
            (msg["temperature_entity"], "sensor"),
            (msg["humidity_entity"], "sensor"),
        ):
            state = hass.states.get(entity_id)
            if state is None or state.domain != domain:
                raise ValueError(f"{entity_id} is not available")
        if not msg["climate_entities"]:
            raise ValueError("Select at least one ACU")
        for entity_id in msg["climate_entities"]:
            ClimateAdapter(hass, entity_id).inspect()
        updated_settings = replace(controller.settings, **msg["settings"])
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(err))
        return

    await controller.async_update_settings(**updated_settings.as_dict())
    data = dict(entry.data)
    data.update(
        {
            CONF_TEMPERATURE_ENTITY: msg["temperature_entity"],
            CONF_HUMIDITY_ENTITY: msg["humidity_entity"],
            CONF_CLIMATE_ENTITIES: list(dict.fromkeys(msg["climate_entities"])),
        }
    )
    data.pop(CONF_CLIMATE_ENTITY, None)
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options={
            **dict(entry.options),
            CONF_SHOW_IN_SIDEBAR: msg["show_in_sidebar"],
        },
    )
    connection.send_result(msg["id"], {"saved": True})
