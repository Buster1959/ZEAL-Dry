"""Verify exclusive ACU ownership across independently controlled zones."""

from types import SimpleNamespace

from custom_components.zeal_dry.ownership import (
    climate_conflict_message,
    climate_entities,
    find_climate_owner,
)


def _entry(entry_id, title, data):
    return SimpleNamespace(entry_id=entry_id, title=title, data=data)


def test_current_and_legacy_assignments_are_both_owned():
    current = _entry("a", "A", {"climate_entities": ["climate.one"]})
    legacy = _entry("b", "B", {"climate_entity": "climate.two"})
    assert climate_entities(current) == {"climate.one"}
    assert climate_entities(legacy) == {"climate.two"}


def test_other_zone_ownership_is_found_but_current_zone_is_excluded():
    lounge = _entry("lounge", "Lounge", {"climate_entities": ["climate.lounge"]})
    bedroom = _entry(
        "bedroom", "Bedroom", {"climate_entities": ["climate.bedroom"]}
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [lounge, bedroom])
    )

    conflict = find_climate_owner(
        hass, ["climate.lounge"], exclude_entry_id="bedroom"
    )
    assert conflict == ("climate.lounge", lounge)
    assert (
        find_climate_owner(
            hass, ["climate.bedroom"], exclude_entry_id="bedroom"
        )
        is None
    )
    assert "already assigned" in climate_conflict_message(*conflict)
