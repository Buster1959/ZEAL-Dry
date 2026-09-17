"""Verify ZEAL-Dry monitoring sensor setup."""

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zeal_dry.const import DATA_CONTROLLERS, DOMAIN
from custom_components.zeal_dry.controller import ZealDryController
from custom_components.zeal_dry.sensor import async_setup_entry


async def test_live_zone_removes_obsolete_dummy_runtime_entity(hass):
    """Remove the dummy-only entity left by versions before multi-ACU support."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"zone_name": "Live", "control_mode": "climate"},
    )
    entry.add_to_hass(hass)
    controller = ZealDryController(hass, entry.entry_id, "Live", control_mode="climate")
    hass.data.setdefault(DOMAIN, {})[DATA_CONTROLLERS] = {
        entry.entry_id: controller
    }
    registry = er.async_get(hass)
    obsolete = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_dummy_acu_runtime",
        config_entry=entry,
    )

    entities = []
    await async_setup_entry(hass, entry, entities.extend)

    assert registry.async_get(obsolete.entity_id) is None
    assert all(
        entity.entity_description.key != "dummy_acu_runtime" for entity in entities
    )
