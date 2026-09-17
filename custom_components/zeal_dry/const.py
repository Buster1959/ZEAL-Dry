"""Constants for ZEAL-Dry."""

DOMAIN = "zeal_dry"

CONF_ZONE_NAME = "zone_name"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_CONTROL_MODE = "control_mode"

CONTROL_MODE_MONITOR = "monitor_only"
CONTROL_MODE_DUMMY = "dummy_acu"
DEFAULT_CONTROL_MODE = CONTROL_MODE_MONITOR

DEFAULT_TEST_TEMPERATURE_C = 18.0
DEFAULT_TEST_HUMIDITY = 55.0

DATA_CONTROLLERS = "controllers"

CONF_CLIMATE_ENTITY = "climate_entity"
CONF_CLIMATE_ENTITIES = "climate_entities"
CONTROL_MODE_CLIMATE = "climate"
