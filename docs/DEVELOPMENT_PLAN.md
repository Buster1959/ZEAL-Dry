# ZEAL-Dry — Modular Development Plan

## Purpose

ZEAL-Dry will be built in small, independently testable blocks. Each block has a defined responsibility, interface, and acceptance criteria. A later block may depend on an earlier block, but earlier blocks must not contain hidden dependencies on later functionality.

The development rule is:

> Foundation first. Deterministic control second. Device control third. Optimisation last.

No energy learning, weather prediction, ZEAL cooperation, or advanced UI should be added until the base moisture controller is proven reliable.

---

## Foundation Phase — freeze before coding

Before production code is written, the following documents form the agreed design contract:

1. `PROJECT_DEFINITION.md` — what ZEAL-Dry is and is not.
2. `CONTROL_MODEL.md` — environmental calculations, states, transitions, hysteresis and timing.
3. `ENTITY_MODEL.md` — Home Assistant inputs, outputs and configuration entities.
4. `ARCHITECTURE.md` — component boundaries and ownership of responsibilities.
5. `DEVELOPMENT_PLAN.md` — coding blocks and acceptance gates.

Changes to core behaviour after coding starts should first update the relevant design document.

---

# Coding Blocks

## Block 1 — Integration Skeleton

### Goal
Create a clean Home Assistant custom integration that installs, loads, unloads and reloads correctly.

### Includes
- manifest
- constants
- config flow
- options flow framework
- coordinator/controller object shell
- diagnostics framework
- translations
- basic tests

### Does not include
- HVAC commands
- dew-point decisions
- state transitions
- energy optimisation

### Acceptance gate
- Integration can be installed through the UI.
- A config entry can be created and removed.
- Reload works without restarting Home Assistant.
- Invalid entities are rejected cleanly.
- Tests pass.

---

## Block 2 — Environmental Model

### Goal
Turn temperature and humidity inputs into reliable environmental measurements.

### Includes
- temperature validation
- humidity validation
- Magnus dew-point calculation
- temperature-to-dew-point spread
- humidity trend
- temperature trend
- stale/unavailable input handling

### Outputs
Pure calculated values only. No equipment is commanded.

### Acceptance gate
- Known temperature/RH pairs produce expected dew points.
- Invalid and unavailable sensor values fail safely.
- Calculations are unit tested independently of Home Assistant services.
- No climate service call exists in this block.

---

## Block 3 — Moisture Decision Engine

### Goal
Decide whether a controlled space needs intervention.

### Includes
- preferred RH
- maximum RH
- critical RH
- hysteresis
- persistence timers
- moisture-risk classification
- drying demand
- human-readable reason

### Does not include
Actual HVAC control.

### Acceptance gate
Given a series of synthetic sensor readings, the engine consistently returns the expected demand, risk and reason.

The same inputs must always produce the same result.

---

## Block 4 — Controller State Machine

### Goal
Convert moisture demand into safe operating states.

### States
- `idle`
- `monitoring`
- `drying`
- `recovery`
- `protection`
- `inhibited`
- `fault`

### Includes
- state transitions
- minimum run time
- minimum rest time
- maximum continuous run time
- recovery observation period
- restart-safe timers/state restoration
- explicit transition reasons

### Acceptance gate
- Every permitted transition is tested.
- Invalid transitions are rejected.
- Restart cannot bypass anti-short-cycle protection.
- Sensor loss has a deterministic safe outcome.

---

## Block 5 — Dry Setpoint Strategy

### Goal
Calculate the target requested from a Dry-capable climate device.

### Initial strategy
`room temperature + configurable offset`

Then:
- clamp to configured/device limits
- round to supported device resolution

### Includes
- fixed target strategy for comparison/testing
- dynamic room-offset strategy
- configurable min/max
- configurable offset
- setpoint rounding

### Acceptance gate
Examples such as room 17.2 °C + 0.5 °C result in the expected device-supported target after rounding and clamping.

Setpoint calculation remains a pure function and does not itself call Home Assistant services.

---

## Block 6 — HVAC Adapter

### Goal
Safely command a Home Assistant climate entity without embedding device-specific logic in the controller.

### Includes
- supported-feature inspection
- Dry-mode availability check
- mode command
- temperature command
- command de-duplication
- command failure handling
- device availability handling

### Architecture rule
The controller requests an action. The adapter translates that request into Home Assistant climate services.

GREE-specific quirks must not leak into the generic decision engine.

### Acceptance gate
- Fake/test climate entities can be controlled.
- Duplicate commands are suppressed.
- Unsupported Dry mode is reported clearly.
- Service-call failure moves the controller to a safe diagnostic state.

---

## Block 7 — Home Assistant Entity Layer

### Goal
Expose the controller clearly in Home Assistant.

### Initial entities
Sensors:
- dew point
- dew-point margin
- moisture risk
- controller state
- decision reason
- requested Dry temperature

Binary sensors:
- drying required
- condensation risk
- fault

Numbers:
- preferred RH
- maximum RH
- Dry temperature offset
- dew-point safety margin

Select:
- operating profile
- Dry temperature strategy

### Acceptance gate
A user can understand what ZEAL-Dry is doing from entity states without enabling debug logging.

---

## Block 8 — Cycle Measurement and Energy

### Goal
Measure what each drying cycle actually achieved.

### Includes
- cycle start/end snapshots
- duration
- start/end temperature
- start/end RH
- start/end dew point
- optional energy consumed
- optional average/peak power

### Important boundary
This block records performance. It does not yet automatically change control parameters.

### Acceptance gate
A complete drying cycle generates a coherent cycle record even if power/energy sensors are not configured.

---

## Block 9 — Diagnostics and Resilience

### Goal
Make failures and decisions understandable.

### Includes
- Home Assistant diagnostics download
- redaction
- last decision
- last transition
- current timer state
- selected entities
- device capabilities
- calculation values
- command result

### Acceptance gate
A fault or unexpected action can be investigated from diagnostics without needing custom debug instrumentation.

---

## Block 10 — Multi-Zone Support

### Goal
Allow multiple independent controlled spaces without coupling their control loops.

### Includes
- one controller per configured zone
- independent entities and settings
- predictable naming/device grouping

### Not yet included
Whole-property optimisation or choosing which AC should run first.

### Acceptance gate
Two zones can operate simultaneously without sharing state or commands accidentally.

---

## Block 11 — Optional ZEAL Cooperation

### Goal
Allow ZEAL and ZEAL-Dry to cooperate without making either integration dependent on the other.

### Includes
A documented demand/status contract such as:
- moisture demand
- recommended mode
- urgency/risk
- active/inhibited status

### Architecture rule
ZEAL-Dry must continue to function when ZEAL is absent.

If ZEAL is configured as HVAC arbiter, ZEAL-Dry emits demand rather than independently fighting for the climate entity.

### Acceptance gate
Installing or removing ZEAL does not break ZEAL-Dry.

---

## Block 12 — Optimisation / Learning

### Goal
Only after deterministic operation has been validated, use measured performance to improve efficiency.

Possible later work:
- compare Dry targets
- compare cycle energy
- tune Dry offset
- external dew-point comparison
- tariff-aware control
- weather-aware prediction

### Gate before starting
Real-world cycle data must demonstrate that there is a useful optimisation problem to solve.

---

# Release Milestones

## 0.1.x — Foundation / laboratory build
Blocks 1–5.

No live autonomous HVAC control required.

## 0.2.x — Controlled HVAC prototype
Blocks 6–7.

Live Dry-mode operation with conservative safeguards.

## 0.3.x — Villa trial
Blocks 8–9.

Collect real environmental and energy data and validate control behaviour.

## 0.4.x — Multi-zone
Block 10.

## 0.5.x — ZEAL cooperation
Block 11 if required.

## 1.0.0 — Stable deterministic ZEAL-Dry
Release only after the controller has demonstrated safe restart behaviour, reliable moisture control, understandable diagnostics and stable multi-zone operation.

Optimisation/learning is explicitly not a requirement for 1.0.0.

---

# Development Discipline

For every coding block:

1. Confirm the block contract.
2. Implement only the stated responsibility.
3. Add unit tests before moving on.
4. Test failure/unavailable states as well as success.
5. Update documentation when behaviour changes.
6. Commit the completed block independently.
7. Do not begin the next block until its predecessor passes its acceptance gate.

This is intended to prevent feature creep and AI-generated code bloat while keeping the project understandable enough to maintain manually.