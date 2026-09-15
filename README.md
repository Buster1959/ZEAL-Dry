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
5. Choose **Monitoring only**, **Test / Dummy ACU**, or **Live climate control**.
6. For the 0.2.0 test build, follow [installation and acceptance checks](docs/BLOCKS_6_7_TESTING.md).

## Current development status

Version 0.2.0 implements Blocks 6–7: a Dry-capable climate adapter, restart protection, persistent settings, and Home Assistant status/control entities. Live operation is a controlled prototype and still needs a supervised test on your AC.

The built-in test mode provides adjustable temperature and humidity values plus a dummy ACU so the moisture and dew-point control logic can be exercised without external YAML or real equipment.

## Documentation

- [Wiki — Getting Started](../../wiki/Getting-Started)
- [Wiki — Instructions for Use](../../wiki/Instructions-for-Use)
- [Wiki — Moisture Demand and Protection](../../wiki/Moisture-Demand-and-Protection)
- [Wiki — Troubleshooting](../../wiki/Troubleshooting)
- [Wiki — Documentation Ownership](../../wiki/Documentation-Ownership)

Detailed project documentation is under [`/docs`](docs/), including:

- [Project definition](docs/PROJECT_DEFINITION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Control model](docs/CONTROL_MODEL.md)
- [Entity model](docs/ENTITY_MODEL.md)
- [Development plan](docs/DEVELOPMENT_PLAN.md)
- [UI design](docs/UI_DESIGN.md)
- [Project positioning](docs/PROJECT_POSITIONING.md)
- [Brand assets](docs/brand/README.md)

## Important scope boundary

ZEAL-Dry manages airborne moisture, humidity, condensation and associated mould risk. It does not diagnose or cure rising damp, penetrating damp, plumbing leaks, groundwater ingress or other structural water-entry problems.

## License

MIT License. See [`LICENSE`](LICENSE).

The [wiki](../../wiki) is a separate Git repository. Clone both for complete
offline user and technical documentation:

```bash
git clone https://github.com/Buster1959/ZEAL-Dry.git
git clone https://github.com/Buster1959/ZEAL-Dry.wiki.git
```
