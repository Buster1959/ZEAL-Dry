# ZEAL-Dry — Architecture

## Architectural Goal

ZEAL-Dry must separate environmental reasoning from Home Assistant device control.

The core controller should be testable with plain Python values and should not need a running Home Assistant instance to decide whether drying is required or which target temperature is appropriate.

---

## Components

### 1. Config Layer
Owns:
- selected temperature sensor
- selected humidity sensor
- selected climate/dehumidifier entity
- optional power/energy entities
- thresholds and timing options
- operating profile

Does not own:
- calculations
- state transitions
- service calls

### 2. Environmental Model
Inputs:
- temperature
- relative humidity
- timestamps/history

Outputs:
- dew point
- dew-point spread
- temperature trend
- humidity trend
- input validity/staleness

Must be implemented as pure/testable logic where practical.

### 3. Moisture Decision Engine
Inputs:
- environmental model output
- configured targets/thresholds

Outputs:
- moisture risk
- drying demand
- urgency
- decision reason

It must not call Home Assistant services.

### 4. State Machine
Inputs:
- drying demand
- current controller state
- timers
- equipment/input availability

Outputs:
- next state
- requested action
- transition reason

Owns anti-short-cycle and recovery timing.

### 5. Dry Setpoint Strategy
Inputs:
- room temperature
- configured strategy
- configured offset
- device/configured min/max
- temperature step/resolution

Output:
- requested target temperature

Initial strategies:
- fixed target
- room-temperature offset

Must remain independent from the HVAC service-call layer.

### 6. HVAC Adapter
Owns interaction with Home Assistant climate/dehumidifier entities.

Responsibilities:
- inspect supported capabilities
- request HVAC mode
- request setpoint
- avoid unnecessary duplicate commands
- surface command failures
- report equipment availability

Device quirks belong here or in device-specific adapters, never in the moisture model.

### 7. Zone Controller
Orchestrates one controlled space.

It combines:
- environmental model
- moisture decision engine
- state machine
- setpoint strategy
- HVAC adapter
- cycle recorder

One zone controller must never hold mutable state belonging to another zone.

### 8. Entity Layer
Exposes controller values into Home Assistant using standard platforms such as:
- sensor
- binary_sensor
- number
- select

Entities reflect controller state; they should not become a second control engine.

### 9. Cycle Recorder
Records drying-cycle measurements for diagnostics and later optimisation.

It must not influence control decisions in the initial deterministic releases.

### 10. Diagnostics
Reads controller state and configuration and presents a redacted support snapshot.

Diagnostics must not change controller behaviour.

### 11. ZEAL Bridge — optional future module

Owns only the interoperability contract between ZEAL-Dry and ZEAL.

ZEAL-Dry core code must not import ZEAL modules.

---

## Data Flow

```text
HA sensors
   │
   ▼
Input validation
   │
   ▼
Environmental model
   │
   ▼
Moisture decision engine
   │
   ▼
State machine
   │
   ├──── no action ────> entities/diagnostics
   │
   ▼
Dry setpoint strategy
   │
   ▼
HVAC adapter
   │
   ▼
HA climate/dehumidifier entity
```

Energy/power data flows to the cycle recorder initially, not back into the decision engine.

---

## Suggested Package Structure

```text
custom_components/zeal_dry/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── coordinator.py
├── diagnostics.py
├── models.py
├── environmental.py
├── decision.py
├── state_machine.py
├── setpoint.py
├── hvac_adapter.py
├── cycle.py
├── sensor.py
├── binary_sensor.py
├── number.py
├── select.py
├── translations/
│   └── en.json
└── strings.json

tests/
├── test_config_flow.py
├── test_environmental.py
├── test_decision.py
├── test_state_machine.py
├── test_setpoint.py
├── test_hvac_adapter.py
└── test_diagnostics.py
```

This is a starting structure, not permission to create empty modules prematurely. A file should be added when the corresponding block is implemented.

---

## Dependency Direction

Allowed:

```text
Entity layer
    ↓
Zone controller
    ↓
Decision / State / Setpoint
    ↓
Environmental/model utilities
```

HVAC adapter is called by the controller but should remain isolated from decision logic.

Not allowed:
- environmental calculations importing Home Assistant climate services
- state machine reading entity registry directly
- entity classes duplicating the control algorithm
- ZEAL-Dry core importing ZEAL
- energy recorder changing thresholds before optimisation is explicitly introduced

---

## Restart Behaviour

Persist only state required to preserve safe behaviour across Home Assistant restarts.

At minimum the design must consider:
- last compressor/device start time
- last stop time
- current/previous controller state
- recovery timer context

On restart, ZEAL-Dry must reconstruct enough timing information to avoid treating a restarted Home Assistant instance as permission to immediately cycle equipment.

---

## Design Principle

The central rule is:

> Sensors describe the environment. The model interprets it. The state machine decides what kind of action is allowed. The adapter controls the equipment.

No layer should quietly perform the responsibility of another.