# ZEAL-Dry

**Intelligent moisture protection for the spaces you leave behind.**

ZEAL-Dry is a Home Assistant custom integration for protecting homes, holiday properties, boats, caravans, cellars, garages and other enclosed spaces from airborne moisture, condensation and mould risk.

> **Keep it dry, not warm.**

## Install with HACS

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Buster1959&repository=ZEAL-Dry&category=integration)

After installing in HACS:

1. Restart Home Assistant.
2. Go to **Settings → Devices & services → Add Integration**.
3. Search for **ZEAL-Dry**.
4. Create your first ZEAL-Dry zone and select its temperature and humidity sensors.

## Current development status

ZEAL-Dry is under active development. The current build is intended for monitoring and dummy-actuator testing before any real HVAC equipment is controlled.

The development test rig is being moved into the integration so HACS installation can remain a single installation path without requiring a separate YAML package.

## Documentation

Detailed project documentation is under [`/docs`](docs/), including:

- Project definition
- Architecture
- Control model
- Entity model
- Development plan
- UI design
- Project positioning

## Important scope boundary

ZEAL-Dry manages airborne moisture, humidity, condensation and associated mould risk. It does not diagnose or cure rising damp, penetrating damp, plumbing leaks, groundwater ingress or other structural water-entry problems.

## License

MIT License. See [`LICENSE`](LICENSE).
