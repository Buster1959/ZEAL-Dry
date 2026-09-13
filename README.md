<p align="center">
  <img src="docs/brand/ZEAL-Dry-logo-approved.png" width="240" alt="ZEAL-Dry approved logo">
</p>

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
4. Create a zone.
5. Choose **Monitoring only** to use real temperature and humidity sensors, or **Test / Dummy ACU** for the built-in adjustable test bench.

## Current development status

ZEAL-Dry is under active development. The current build is intended for monitoring and dummy-actuator testing before any real HVAC equipment is controlled.

The built-in test mode provides adjustable temperature and humidity values plus a dummy ACU so the moisture and dew-point control logic can be exercised without external YAML or real equipment.

## Documentation

Detailed project documentation is under [`/docs`](docs/), including:

- Project definition
- Architecture
- Control model
- Entity model
- Development plan
- UI design
- Project positioning
- Brand assets

## Important scope boundary

ZEAL-Dry manages airborne moisture, humidity, condensation and associated mould risk. It does not diagnose or cure rising damp, penetrating damp, plumbing leaks, groundwater ingress or other structural water-entry problems.

## License

MIT License. See [`LICENSE`](LICENSE).
