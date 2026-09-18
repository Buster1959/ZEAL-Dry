"""Enforce exclusive ownership of climate equipment across ZEAL-Dry zones."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLIMATE_ENTITIES, CONF_CLIMATE_ENTITY, DOMAIN


def climate_entities(entry: ConfigEntry) -> set[str]:
    """Return current and legacy climate assignments for one zone."""
    configured = set(entry.data.get(CONF_CLIMATE_ENTITIES) or [])
    legacy = entry.data.get(CONF_CLIMATE_ENTITY)
    if legacy:
        configured.add(legacy)
    return configured


def find_climate_owner(
    hass: HomeAssistant,
    entity_ids: Iterable[str],
    *,
    exclude_entry_id: str | None = None,
) -> tuple[str, ConfigEntry] | None:
    """Return the first selected ACU already owned by another zone."""
    requested = set(entity_ids)
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        overlap = requested & climate_entities(entry)
        if overlap:
            return sorted(overlap)[0], entry
    return None


def climate_conflict_message(entity_id: str, owner: ConfigEntry) -> str:
    """Explain how to resolve an exclusive-ownership conflict."""
    return (
        f"{entity_id} is already assigned to ZEAL-Dry zone '{owner.title}'. "
        "Remove it from that zone before assigning it here."
    )
