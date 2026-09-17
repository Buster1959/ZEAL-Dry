"""Protect the dedicated ZEAL-Dry panel contract."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal_dry.const import (
    CONF_SHOW_IN_SIDEBAR,
    DATA_CONTROLLERS,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_URL_PATH,
)
from custom_components.zeal_dry.panel import async_sync_panel


async def test_panel_can_be_shown_in_sidebar(hass):
    """Register the panel and expose its sidebar link when requested."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"zone_name": "Villa"},
        options={CONF_SHOW_IN_SIDEBAR: True},
    )
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {DATA_CONTROLLERS: {entry.entry_id: object()}}
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())

    with (
        patch(
            "custom_components.zeal_dry.panel.panel_custom.async_register_panel",
            AsyncMock(),
        ) as register,
    ):
        await async_sync_panel(hass)

    assert register.await_args.kwargs["frontend_url_path"] == PANEL_URL_PATH
    assert register.await_args.kwargs["webcomponent_name"] == PANEL_COMPONENT
    assert register.await_args.kwargs["sidebar_title"] == "ZEAL-Dry"
    assert register.await_args.kwargs["config_panel_domain"] == DOMAIN


async def test_panel_route_remains_when_sidebar_is_hidden(hass):
    """Hide only the sidebar link so Configure can restore it later."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"zone_name": "Villa"},
        options={CONF_SHOW_IN_SIDEBAR: False},
    )
    entry.add_to_hass(hass)
    hass.data[DOMAIN] = {DATA_CONTROLLERS: {entry.entry_id: object()}}
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())

    with (
        patch(
            "custom_components.zeal_dry.panel.panel_custom.async_register_panel",
            AsyncMock(),
        ) as register,
    ):
        await async_sync_panel(hass)

    assert register.await_args.kwargs["frontend_url_path"] == PANEL_URL_PATH
    assert register.await_args.kwargs["sidebar_title"] is None
    assert register.await_args.kwargs["config_panel_domain"] is None


def test_frontend_has_focused_tabs_and_status_banner():
    """Keep ZEAL-Dry focused: no Heat scheduling or learning screens."""
    source = (
        Path(__file__).parents[1]
        / "custom_components/zeal_dry/frontend/zeal-dry-panel.js"
    ).read_text()

    for label in ("Overview", "Overrides", "Setup"):
        assert label in source
    for excluded in ("Schedule", "Learning"):
        assert excluded not in source
    assert "remaining_seconds" in source
    assert "elapsed_seconds" in source
    assert 'padStart(2, "0")' in source
    assert "_historyUrl(entityIds)" in source
    assert "Open ${label} history" in source
    assert "Outdoor dew-point outlook" in source
    assert "Show ZEAL-Dry in the Home Assistant sidebar" in source
    assert 'if (!customElements.get("zeal-dry-panel"))' in source
    assert 'customElements.define("zeal-dry-panel", ZealDryPanel);' in source
    assert "@media" in source
