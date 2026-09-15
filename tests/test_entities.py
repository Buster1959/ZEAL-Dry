from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal_dry.const import DOMAIN


async def test_real_platform_setup_and_controls(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"zone_name": "Test", "control_mode": "dummy_acu"},
        unique_id="test",
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    states = hass.states.async_all()
    assert any(s.entity_id.startswith("select.") for s in states)
    assert any(s.name.endswith("Fault") for s in states)
    c = hass.data[DOMAIN]["controllers"][entry.entry_id]
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.test_preferred_rh", "value": 55},
        blocking=True,
    )
    assert c.settings.preferred_rh == 55
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_operating_profile", "option": "off"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(s.state == "off" for s in hass.states.async_all("select"))
    assert await hass.config_entries.async_unload(entry.entry_id)
