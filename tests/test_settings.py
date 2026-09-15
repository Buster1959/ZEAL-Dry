from unittest.mock import AsyncMock

import pytest

from custom_components.zeal_dry.controller import ZealDryController
from custom_components.zeal_dry.setpoint import (
    DrySetpointConfig,
    calculate_dry_setpoint,
)
from custom_components.zeal_dry.settings import ZoneSettings


@pytest.mark.parametrize(
    "values",
    [
        {"preferred_rh": 65},
        {"maximum_rh": 75},
        {"offset_c": float("nan")},
        {"minimum_run_minutes": 120, "maximum_run_minutes": 20},
        {"minimum_rest_minutes": 0},
        {"profile": "other"},
        {"minimum_c": 30, "maximum_c": 20},
    ],
)
def test_reject_invalid_settings(values):
    with pytest.raises(ValueError):
        ZoneSettings(**values)


def test_fixed_strategy_clamps():
    assert (
        calculate_dry_setpoint(
            25, DrySetpointConfig(strategy="fixed", fixed_target_c=18)
        ).applied_target_c
        == 18
    )
    assert (
        calculate_dry_setpoint(
            25, DrySetpointConfig(strategy="fixed", fixed_target_c=30)
        ).applied_target_c
        == 20
    )


async def test_settings_survive_restart_and_off_stops(hass):
    c = ZealDryController(hass, "settings", "Test", control_mode="dummy_acu")
    await c.async_start()
    await c.async_set_test_humidity(90)
    assert c.actuator.is_on
    await c.async_update_settings(profile="off", offset_c=1.2)
    assert not c.actuator.is_on
    assert c.state_snapshot.state == "inhibited"
    await c.async_stop()
    restored = ZealDryController(hass, "settings", "Test", control_mode="dummy_acu")
    await restored.async_start()
    assert restored.settings.offset_c == 1.2
    assert restored.profile == "off"
    assert not restored.actuator.is_on
    await restored.async_stop()


async def test_failed_setting_write_preserves_policy(hass):
    c = ZealDryController(hass, "settings", "Test", control_mode="dummy_acu")
    await c.async_start()
    previous = c.settings
    c._store.async_save = AsyncMock(side_effect=OSError("disk error"))
    with pytest.raises(OSError):
        await c.async_update_settings(preferred_rh=55)
    assert c.settings == previous
    c._store.async_save.side_effect = None
    await c.async_stop()
