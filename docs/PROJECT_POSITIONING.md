# ZEAL-Dry — Project Positioning

## Elevator pitch

**ZEAL-Dry — intelligent moisture protection for the spaces you leave behind.**

ZEAL-Dry is a Home Assistant integration designed to help protect homes, holiday properties, boats, caravans, cellars, garages and other enclosed spaces from airborne moisture, condensation and mould risk.

Rather than simply switching a dehumidifier or air conditioner on when humidity reaches a fixed percentage, ZEAL-Dry considers temperature, relative humidity and dew point to decide **when drying is actually needed — and when it isn't**.

ZEAL-Dry is manufacturer-independent and adaptable. It works with capabilities exposed through Home Assistant, allowing it to work with GREE and other air-conditioning systems, dehumidifiers and future drying equipment without tying the core system to a particular manufacturer.

Its objective is simple:

> **Keep the space dry enough to protect it, while using as little energy as reasonably possible.**

## Short tagline

> **Keep it dry, not warm.**

## Scope boundary

ZEAL-Dry manages **airborne moisture, humidity, condensation and associated mould risk**.

It is not intended to diagnose or cure moisture entering through the structure. Rising damp, penetrating damp, plumbing leaks, groundwater ingress and similar building defects require diagnosis and treatment of their underlying cause.

This distinction is important: ZEAL-Dry is a moisture-management controller, not a substitute for building repairs or waterproofing.

## Where ZEAL-Dry fits

Potential applications include:

- Holiday and intermittently occupied homes
- Boats and yachts
- Caravans and motorhomes
- Cellars and basements
- Garages and workshops
- Storage rooms and outbuildings
- Permanently occupied homes with condensation-prone areas

## Adaptability principle

> **ZEAL-Dry controls capabilities, not brands.**

GREE equipment is the first reference/test platform, but the core environmental model and decision logic must remain manufacturer-independent.

Equipment-specific behaviour belongs behind a small capability/adapter layer. The environmental model, moisture decision engine, controller state machine and energy strategy must not contain manufacturer-specific logic.

This allows ZEAL-Dry to evolve to support different air conditioners, dehumidifiers, ventilation equipment and other moisture-control devices without redesigning the core controller.

## Product philosophy

ZEAL-Dry should remain simple to understand at the front while using environmental information intelligently underneath.

A user should be able to answer three questions immediately:

1. Is this space currently safe from moisture risk?
2. Does ZEAL-Dry think drying is required?
3. What is ZEAL-Dry doing about it, and why?

The longer-term aim is not simply to reduce relative humidity. It is to provide **energy-aware building protection** using the least intervention reasonably required to maintain a safe moisture environment.
