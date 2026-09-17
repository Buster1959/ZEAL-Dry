"""Config flow for ZEAL-Dry."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_CLIMATE_ENTITIES,
    CONF_CONTROL_MODE,
    CONF_HUMIDITY_ENTITY,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TEMPERATURE_ENTITY,
    CONF_WEATHER_ENTITY,
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

    def _default_weather_entity(self) -> str | None:
        """Use HA's sole weather entity as the unambiguous default."""
        entities = self.hass.states.async_entity_ids("weather")
        return entities[0] if len(entities) == 1 else None

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

    async def async_step_reconfigure(self, user_input=None):
        """Update sensors and ACUs for an existing non-dummy zone."""
        from homeassistant.exceptions import HomeAssistantError

        from .hvac import ClimateAdapter

        entry = self._get_reconfigure_entry()
        control_mode = entry.data.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE)
        if control_mode == CONTROL_MODE_DUMMY:
            return self.async_abort(reason="dummy_reconfigure_not_supported")

        current_climates = entry.data.get(CONF_CLIMATE_ENTITIES)
        if current_climates is None and entry.data.get(CONF_CLIMATE_ENTITY):
            current_climates = [entry.data[CONF_CLIMATE_ENTITY]]
        weather_default = (
            entry.data.get(CONF_WEATHER_ENTITY) or self._default_weather_entity()
        )
        weather_key = (
            vol.Optional(CONF_WEATHER_ENTITY, default=weather_default)
            if weather_default
            else vol.Optional(CONF_WEATHER_ENTITY)
        )
        schema_fields = {
            vol.Required(
                CONF_TEMPERATURE_ENTITY,
                default=entry.data.get(CONF_TEMPERATURE_ENTITY),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class="temperature"
                )
            ),
            vol.Required(
                CONF_HUMIDITY_ENTITY,
                default=entry.data.get(CONF_HUMIDITY_ENTITY),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
            ),
            weather_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
        }
        if control_mode == CONTROL_MODE_CLIMATE:
            schema_fields[
                vol.Required(CONF_CLIMATE_ENTITIES, default=current_climates or [])
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate", multiple=True)
            )

        errors = {}
        if user_input is not None:
            for key in (CONF_TEMPERATURE_ENTITY, CONF_HUMIDITY_ENTITY):
                if self.hass.states.get(user_input[key]) is None:
                    errors[key] = "entity_not_found"
            weather_entity = user_input.get(CONF_WEATHER_ENTITY)
            if weather_entity and self.hass.states.get(weather_entity) is None:
                errors[CONF_WEATHER_ENTITY] = "entity_not_found"
            if control_mode == CONTROL_MODE_CLIMATE:
                try:
                    if not user_input[CONF_CLIMATE_ENTITIES]:
                        raise HomeAssistantError("climate_entity_required")
                    for entity_id in user_input[CONF_CLIMATE_ENTITIES]:
                        ClimateAdapter(self.hass, entity_id).inspect()
                except HomeAssistantError:
                    errors[CONF_CLIMATE_ENTITIES] = "unsupported_climate"
            if not errors:
                updated_data = dict(entry.data)
                updated_data.update(user_input)
                updated_data.pop(CONF_CLIMATE_ENTITY, None)
                self.hass.config_entries.async_update_entry(
                    entry, data=updated_data
                )
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    async def async_step_sensors(self, user_input=None):
        """Select real indoor sensors for monitoring mode."""
        errors: dict[str, str] = {}
        if user_input is not None:
            temperature_entity = user_input[CONF_TEMPERATURE_ENTITY]
            humidity_entity = user_input[CONF_HUMIDITY_ENTITY]
            weather_entity = user_input.get(CONF_WEATHER_ENTITY)
            if self.hass.states.get(temperature_entity) is None:
                errors[CONF_TEMPERATURE_ENTITY] = "entity_not_found"
            if self.hass.states.get(humidity_entity) is None:
                errors[CONF_HUMIDITY_ENTITY] = "entity_not_found"
            if weather_entity and self.hass.states.get(weather_entity) is None:
                errors[CONF_WEATHER_ENTITY] = "entity_not_found"
            if not errors and self._control_mode == CONTROL_MODE_CLIMATE:
                self._sensors = user_input
                return await self.async_step_climate()
            if not errors:
                return await self._async_create_zone(
                    temperature_entity=temperature_entity,
                    humidity_entity=humidity_entity,
                    weather_entity=weather_entity,
                )

        weather_default = self._default_weather_entity()
        weather_key = (
            vol.Optional(CONF_WEATHER_ENTITY, default=weather_default)
            if weather_default
            else vol.Optional(CONF_WEATHER_ENTITY)
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
                weather_key: selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
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

            entities = user_input[CONF_CLIMATE_ENTITIES]
            try:
                if not entities:
                    raise HomeAssistantError("climate_entity_required")
                for entity in entities:
                    if not entity.startswith("climate."):
                        raise HomeAssistantError("invalid_climate_entity")
                    ClimateAdapter(self.hass, entity).inspect()
            except HomeAssistantError:
                errors[CONF_CLIMATE_ENTITIES] = "unsupported_climate"
            else:
                self._climate_entities = list(entities)
                return await self._async_create_zone(**self._sensors)
        return self.async_show_form(
            step_id="climate",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIMATE_ENTITIES): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate", multiple=True)
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

    async def _async_create_zone(
        self, temperature_entity=None, humidity_entity=None, weather_entity=None
    ):
        """Store a uniquely named zone and its selected entities."""
        await self.async_set_unique_id(self._zone_name.casefold())
        self._abort_if_unique_id_configured()
        data = {
            CONF_ZONE_NAME: self._zone_name,
            CONF_CONTROL_MODE: self._control_mode,
        }
        if self._control_mode == CONTROL_MODE_CLIMATE:
            data[CONF_CLIMATE_ENTITIES] = self._climate_entities
        if temperature_entity is not None:
            data[CONF_TEMPERATURE_ENTITY] = temperature_entity
        if humidity_entity is not None:
            data[CONF_HUMIDITY_ENTITY] = humidity_entity
        if weather_entity is not None:
            data[CONF_WEATHER_ENTITY] = weather_entity
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
            show_in_sidebar = user_input.pop(CONF_SHOW_IN_SIDEBAR)
            try:
                await controller.async_update_settings(**user_input)
            except ValueError:
                errors["base"] = "invalid_settings"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        **dict(self.config_entry.options),
                        CONF_SHOW_IN_SIDEBAR: show_in_sidebar,
                    },
                )
        fields = {
            vol.Required(key, default=getattr(controller.settings, key)): vol.All(
                vol.Coerce(float), vol.Range(min=low, max=high)
            )
            for key, (low, high) in OPTION_SETTINGS.items()
        }
        fields[
            vol.Required(
                CONF_SHOW_IN_SIDEBAR,
                default=self.config_entry.options.get(CONF_SHOW_IN_SIDEBAR, True),
            )
        ] = bool
        schema = vol.Schema(fields)
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
