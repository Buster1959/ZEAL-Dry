"""Config flow for ZEAL-Dry."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    DOMAIN,
)


class ZealDryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZEAL-Dry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create one ZEAL-Dry controlled zone."""
        errors: dict[str, str] = {}

        if user_input is not None:
            temperature_entity = user_input[CONF_TEMPERATURE_ENTITY]
            humidity_entity = user_input[CONF_HUMIDITY_ENTITY]

            if self.hass.states.get(temperature_entity) is None:
                errors[CONF_TEMPERATURE_ENTITY] = "entity_not_found"
            if self.hass.states.get(humidity_entity) is None:
                errors[CONF_HUMIDITY_ENTITY] = "entity_not_found"

            if not errors:
                zone_name = user_input[CONF_ZONE_NAME].strip()
                await self.async_set_unique_id(zone_name.casefold())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=zone_name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE_NAME): selector.TextSelector(),
                vol.Required(CONF_TEMPERATURE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                    )
                ),
                vol.Required(CONF_HUMIDITY_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="humidity",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the Block 1 options-flow shell."""
        return ZealDryOptionsFlow()


class ZealDryOptionsFlow(config_entries.OptionsFlow):
    """Options-flow shell for later tuning controls."""

    async def async_step_init(self, user_input=None):
        """Show that no runtime tuning options are defined in Block 1."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
