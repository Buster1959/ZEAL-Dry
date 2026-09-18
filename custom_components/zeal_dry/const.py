"""Constants for ZEAL-Dry."""


DOMAIN = "zeal_dry"


PANEL_COMPONENT = "zeal-dry-panel"
PANEL_URL_PATH = "zeal-dry"
PANEL_STATIC_URL = "/zeal_dry_static"
PANEL_ASSET_VERSION = "9"


CONF_ZONE_NAME = "zone_name"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_CONTROL_MODE = "control_mode"
CONF_SHOW_IN_SIDEBAR = "show_in_sidebar"


CONTROL_MODE_MONITOR = "monitor_only"
CONTROL_MODE_DUMMY = "dummy_acu"
DEFAULT_CONTROL_MODE = CONTROL_MODE_MONITOR


DEFAULT_TEST_TEMPERATURE_C = 18.0
DEFAULT_TEST_HUMIDITY = 55.0


# ``last_reported`` distinguishes a quiet healthy sensor from one that has
# stopped reporting. Device health matches ZEAL-Heat so sleeping battery
# sensors are not falsely declared offline. The shorter control limit is
# checked separately before a reading can justify energy-consuming Dry operation.
SENSOR_OFFLINE_DEBOUNCE_SECONDS = 5 * 60
SENSOR_STALE_THRESHOLD_SECONDS = 4 * 60 * 60
SENSOR_CONTROL_FRESHNESS_SECONDS = 90 * 60
SENSOR_PROBE_INTERVAL_SECONDS = 30 * 60


DATA_CONTROLLERS = "controllers"


CONF_CLIMATE_ENTITY = "climate_entity"
CONF_CLIMATE_ENTITIES = "climate_entities"
CONTROL_MODE_CLIMATE = "climate"
