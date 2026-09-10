# ZEAL-Dry — Home Assistant Entity Model

## Purpose

This document defines the V1 Home Assistant-facing contract for one ZEAL-Dry controlled zone.

The controller logic must remain independent from entity classes. Entities expose configuration, status and diagnostics; they do not contain duplicate decision logic.

---

## Required Configuration Inputs

Per zone:

- Home Assistant Area or friendly zone name
- Temperature sensor entity
- Humidity sensor entity
- Dry-capable climate entity or supported drying device

Optional:

- Power sensor
- Energy sensor
- External temperature sensor
- External humidity sensor
- Occupancy input
- Door/window interlock

V1 basic operation must not depend on any optional sensor.

---

## Device Grouping

Each configured ZEAL-Dry zone should appear as one Home Assistant device containing the entities belonging to that controller.

Example device name:

`ZEAL-Dry — Undercroft Lounge`

Entity unique IDs must be based on a stable config-entry/zone identifier, not the user-visible room name alone.

---

## Sensors

### Dew Point
Suggested entity:

`sensor.<zone>_zeal_dry_dew_point`

Properties:
- device class: temperature
- unit follows HA temperature system where appropriate
- diagnostic/category decision to follow HA convention

### Dew-Point Spread
Suggested entity:

`sensor.<zone>_zeal_dry_dew_point_spread`

Represents:

`room temperature - dew point`

### Moisture Risk
Suggested entity:

`sensor.<zone>_zeal_dry_moisture_risk`

States:
- `normal`
- `elevated`
- `high`
- `critical`
- `unknown`

### Controller State
Suggested entity:

`sensor.<zone>_zeal_dry_state`

States:
- `idle`
- `monitoring`
- `drying`
- `recovery`
- `protection`
- `inhibited`
- `fault`

### Decision Reason
Suggested entity:

`sensor.<zone>_zeal_dry_reason`

Exposes a concise stable reason code. Human-readable explanation may be supplied in attributes.

### Requested Dry Temperature
Suggested entity:

`sensor.<zone>_zeal_dry_requested_temperature`

Shows the target calculated by the setpoint strategy after clamping/rounding.

### Last Cycle Duration
Added when cycle recording is implemented.

### Last Cycle Energy
Added only when an energy source is configured and cycle measurement is implemented.

---

## Binary Sensors

### Drying Required
Suggested entity:

`binary_sensor.<zone>_zeal_dry_drying_required`

True when the decision engine has confirmed active drying demand, regardless of whether equipment is temporarily prevented from starting by a rest timer/interlock.

### Condensation Risk
Suggested entity:

`binary_sensor.<zone>_zeal_dry_condensation_risk`

True only when a defined dew-point/condensation criterion is met. It must not simply mirror high RH.

### Fault
Suggested entity:

`binary_sensor.<zone>_zeal_dry_fault`

True when the controller is in a fault condition requiring attention or preventing trusted automatic operation.

---

## Number Entities

Initial user-tunable controls should be deliberately limited.

### Preferred RH
Suggested range:
- 40–75%

Purpose:
Normal recovery/stop target.

### Maximum RH
Suggested range:
- 45–85%

Purpose:
Persistent humidity above this level can create drying demand.

Validation rule:
`maximum_rh` must remain above `preferred_rh` by a defined minimum separation.

### Critical RH
Suggested range:
- 55–95%

Validation rule:
Must be greater than `maximum_rh`.

### Dry Temperature Offset
Suggested initial range:
- -2.0 to +3.0 °C

Initial default hypothesis:
`+0.5 °C`

This range is configuration flexibility, not a recommendation that every value is safe/effective for every device.

### Dew-Point Safety Margin
Used when condensation-risk logic requires a configurable spread.

### Timing Controls
Timing parameters may initially live in the options flow rather than each becoming a permanently visible number entity. This avoids cluttering Home Assistant with tuning controls that are rarely changed.

---

## Select Entities

### Operating Profile
Suggested values:
- `property_protection`
- `occupied`
- `off`

For V1, `property_protection` is the primary developed profile. `occupied` may initially share the deterministic controller with different configurable targets rather than introduce separate comfort logic.

### Dry Temperature Strategy
Initial values:
- `room_offset`
- `fixed`

No adaptive/learning strategy should appear until it actually exists and is validated.

---

## Switch Entities

Avoid switches unless a true persistent Boolean function exists.

Do not create switches for:
- current drying state
- fault state
- moisture demand

Those are observations and belong as sensor/binary_sensor entities.

---

## Attributes

Keep primary state in entity state values, not buried in attributes.

Useful diagnostic attributes may include:
- current room temperature
- current RH
- dew point
- dew-point spread
- threshold responsible for demand
- persistence elapsed/required
- remaining minimum run/rest time
- raw requested target
- applied target
- configured climate entity

Avoid large mutable state dumps in attributes.

---

## Availability

Calculated environmental entities should become unavailable when the required underlying values cannot be trusted.

Controller/status entities may remain available where useful so they can explicitly report states such as `fault` or `unknown` rather than disappearing entirely.

Loss of optional energy data must not make the core controller unavailable.

---

## Configuration vs Runtime Controls

### Config Flow
Use for identity and primary entity binding:
- zone/Area
- temperature sensor
- humidity sensor
- controlled device
- optional energy/power sensors

### Options Flow
Use for less frequently changed policy/tuning:
- persistence times
- run/rest protections
- configured min/max device target if discovery is inadequate
- critical thresholds

### Entities
Use for values the user may reasonably want to tune or inspect directly from the HA UI:
- preferred RH
- maximum RH
- offset
- profile
- strategy

The exact split can be adjusted during Block 1/7 implementation while preserving the semantic contract.

---

## ZEAL Interoperability Contract

ZEAL must not need to inspect ZEAL-Dry internals.

The minimum public information required for future cooperation is expected to be represented by normal HA entities:

- drying demand
- moisture risk
- controller state
- recommended action/mode if later added

Any richer API must be documented separately before implementation.

---

## V1 Entity Principle

> Expose enough information to understand and control ZEAL-Dry without turning every internal variable into a Home Assistant entity.