"""Register the versioned ZEAL-Dry Home Assistant panel."""

from __future__ import annotations

import asyncio
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    CONF_SHOW_IN_SIDEBAR,
    DATA_CONTROLLERS,
    DOMAIN,
    PANEL_ASSET_VERSION,
    PANEL_COMPONENT,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)

_STATIC_REGISTERED = f"{DOMAIN}_panel_static_registered"
_PANEL_LOCK = f"{DOMAIN}_panel_lock"


def _panel_exists(hass: HomeAssistant) -> bool:
    """Return whether the shared ZEAL-Dry route is registered."""
    return PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})


def _show_in_sidebar(hass: HomeAssistant) -> bool:
    """Show the shared link while any loaded zone requests it."""
    controllers = hass.data.get(DOMAIN, {}).get(DATA_CONTROLLERS, {})
    for entry_id in controllers:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.options.get(CONF_SHOW_IN_SIDEBAR, True):
            return True
    return False


async def async_sync_panel(hass: HomeAssistant) -> None:
    """Expose the panel to authenticated users and Setup to administrators."""
    lock = hass.data.setdefault(_PANEL_LOCK, asyncio.Lock())
    async with lock:
        show_in_sidebar = _show_in_sidebar(hass)
        if _panel_exists(hass):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
        if not hass.data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        PANEL_STATIC_URL,
                        Path(__file__).parent / "frontend",
                        False,
                    )
                ]
            )
            hass.data[_STATIC_REGISTERED] = True
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_COMPONENT,
            module_url=(
                f"{PANEL_STATIC_URL}/zeal-dry-panel.js?v={PANEL_ASSET_VERSION}"
            ),
            sidebar_title="ZEAL-Dry" if show_in_sidebar else None,
            sidebar_icon="mdi:water-percent-alert" if show_in_sidebar else None,
            require_admin=False,
            config_panel_domain=DOMAIN if show_in_sidebar else None,
        )


async def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the route after the final zone unloads."""
    lock = hass.data.setdefault(_PANEL_LOCK, asyncio.Lock())
    async with lock:
        if _panel_exists(hass):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
