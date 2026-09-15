"""Config flow for ZEAL-Dry."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_CONTROL_MODE,
    CONF_HUMIDITY_ENTITY,
    CONF_TEMPERATURE_ENTITY,
    CONF_ZONE_NAME,
    CONTROL_MODE_CLIMATE,
    CONTROL_MODE_DUMMY,
    CONTROL_MODE_MONITOR,
    DEFAULT_CONTROL_MODE,
    DOMAIN,
)


class ZealDryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZEAL-Dry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Choose the zone name and operating mode."""
        if user_input is not None:
            self._zone_name = user_input[CONF_ZONE_NAME].strip()
            self._control_mode = user_input[CONF_CONTROL_MODE]
            if not self._zone_name:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._user_schema(user_input),
                    errors={CONF_ZONE_NAME: "zone_name_required"},
                )
            if self._control_mode == CONTROL_MODE_DUMMY:
                return await self.async_step_dummy()
            return await self.async_step_sensors()

        return self.async_show_form(step_id="user", data_schema=self._user_schema())

    def _user_schema(self, suggested=None):
        """Build the zone-name and operating-mode form."""
        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE_NAME): selector.TextSelector(),
                vol.Required(
                    CONF_CONTROL_MODE, default=DEFAULT_CONTROL_MODE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": CONTROL_MODE_CLIMATE,
                                "label": "Live climate control",
                            },
                            {"value": CONTROL_MODE_MONITOR, "label": "Monitoring only"},
                            {"value": CONTROL_MODE_DUMMY, "label": "Test / Dummy ACU"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.add_suggested_values_to_schema(schema, suggested)

    async def async_step_sensors(self, user_input=None):
        """Select real indoor sensors for monitoring mode."""
        errors: dict[str, str] = {}
        if user_input is not None:
            temperature_entity = user_input[CONF_TEMPERATURE_ENTITY]
            humidity_entity = user_input[CONF_HUMIDITY_ENTITY]
            if self.hass.states.get(temperature_entity) is None:
                errors[CONF_TEMPERATURE_ENTITY] = "entity_not_found"
            if self.hass.states.get(humidity_entity) is None:
                errors[CONF_HUMIDITY_ENTITY] = "entity_not_found"
            if not errors and self._control_mode == CONTROL_MODE_CLIMATE:
                self._sensors = user_input
                return await self.async_step_climate()
            if not errors:
                return await self._async_create_zone(
                    temperature_entity=temperature_entity,
                    humidity_entity=humidity_entity,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TEMPERATURE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Required(CONF_HUMIDITY_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="sensors",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_climate(self, user_input=None):
        """Validate the selected AC before creating a live-control zone."""
        errors = {}
        if user_input is not None:
            from homeassistant.exceptions import HomeAssistantError

            from .hvac import ClimateAdapter

            entity = user_input[CONF_CLIMATE_ENTITY]
            try:
                if not entity.startswith("climate."):
                    raise HomeAssistantError("invalid_climate_entity")
                ClimateAdapter(self.hass, entity).inspect()
            except HomeAssistantError:
                errors[CONF_CLIMATE_ENTITY] = "unsupported_climate"
            else:
                self._climate_entity = entity
                return await self._async_create_zone(**self._sensors)
        return self.async_show_form(
            step_id="climate",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIMATE_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate")
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_dummy(self, user_input=None):
        """Confirm creation of the self-contained test bench."""
        if user_input is not None:
            return await self._async_create_zone()
        return self.async_show_form(step_id="dummy", data_schema=vol.Schema({}))

    async def _async_create_zone(self, temperature_entity=None, humidity_entity=None):
        """Store a uniquely named zone and its selected entities."""
        await self.async_set_unique_id(self._zone_name.casefold())
        self._abort_if_unique_id_configured()
        data = {
            CONF_ZONE_NAME: self._zone_name,
            CONF_CONTROL_MODE: self._control_mode,
        }
        if self._control_mode == CONTROL_MODE_CLIMATE:
            data[CONF_CLIMATE_ENTITY] = self._climate_entity
        if temperature_entity is not None:
            data[CONF_TEMPERATURE_ENTITY] = temperature_entity
        if humidity_entity is not None:
            data[CONF_HUMIDITY_ENTITY] = humidity_entity
        return self.async_create_entry(title=self._zone_name, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Provide the timing and temperature-limit options form."""
        return ZealDryOptionsFlow()


class ZealDryOptionsFlow(config_entries.OptionsFlow):
    """Less frequently changed timing and target bounds."""

    async def async_step_init(self, user_input=None):
        """Validate and apply less frequently changed timing and target limits."""
        from .const import DATA_CONTROLLERS
        from .settings import OPTION_SETTINGS

        controller = self.hass.data[DOMAIN][DATA_CONTROLLERS][
            self.config_entry.entry_id
        ]
        errors = {}
        if user_input is not None:
            try:
                await controller.async_update_settings(**user_input)
            except ValueError:
                errors["base"] = "invalid_settings"
            else:
                return self.async_create_entry(
                    title="", data=dict(self.config_entry.options)
                )
        schema = vol.Schema(
            {
                vol.Required(key, default=getattr(controller.settings, key)): vol.All(
                    vol.Coerce(float), vol.Range(min=low, max=high)
                )
                for key, (low, high) in OPTION_SETTINGS.items()
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
