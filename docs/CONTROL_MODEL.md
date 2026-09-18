# ZEAL-Dry — Control Model

## Status

This document defines the deterministic V1 control model. It should be agreed before the decision engine and state machine are implemented.

The initial objective is building protection with minimum unnecessary HVAC runtime, not comfort-temperature control.

---

## 1. Primary Measurements

Per controlled zone:

- Room temperature `T` in °C
- Relative humidity `RH` in %

Optional measurements may be added later, but V1 core control must work with these two measurements alone.

---

## 2. Dew Point

ZEAL-Dry calculates dew point using a documented Magnus approximation.

Conceptually:

```text
gamma = ln(RH / 100) + (a × T) / (b + T)
dew_point = (b × gamma) / (a - gamma)
```

Implementation constants must be defined once, covered by tests, and not duplicated across modules.

The controller also calculates:

```text
dew_point_spread = room_temperature - dew_point
```

A smaller spread indicates air conditions closer to saturation.

---

## 3. RH Targets

V1 uses three conceptual humidity bands:

### Preferred
The desired normal upper range.

Example starting value: `60% RH`.

### Maximum
Above this level, persistent humidity should normally create a drying demand.

Example starting value: `65% RH`.

### Critical
Conditions requiring stronger/urgent building-protection action.

Example starting value: `75% RH`.

These are proposed defaults for development/testing and must remain configurable rather than being treated as universal scientific limits.

---

## 4. Hysteresis

ZEAL-Dry must not start and stop at the same threshold.

Example principle:

```text
Start drying when RH >= maximum threshold for required persistence time.
Stop normal drying only after RH <= preferred threshold and minimum run time has elapsed.
```

This produces a deliberate dead band between start and stop conditions.

The exact defaults should be validated during villa testing.

---

## 5. Persistence

A single high reading must not automatically start the AC.

V1 should support a configurable persistence period for normal high humidity.

Critical conditions may use a shorter persistence time, but must still reject clearly invalid/transient sensor values.

Persistence belongs in controller/state timing, not HA YAML automations.

---

## 6. Moisture Risk Classification

Proposed deterministic risk levels:

### `normal`
RH and dew-point conditions are acceptable.

### `elevated`
Conditions are worse than preferred but do not yet justify active drying.

### `high`
Maximum humidity threshold/persistence or another defined moisture criterion has been met.

### `critical`
Critical threshold or another explicit protection condition has been met.

### `unknown`
Inputs are unavailable, stale or invalid.

### Dew-point spread risk

ZEAL-Dry classifies the room temperature minus dew point as Normal above 6 °C,
Elevated from 4–6 °C, High from 2–4 °C, and Critical at 2 °C or less. The final
moisture risk is the highest level indicated by RH, absolute dew point or this
spread. The selected Drying response then permits demand from Elevated (Early
protection), High (Balanced) or Critical (Economy). Critical RH and absolute
dew point remain immediate protection conditions for every response.

Risk is an assessment. It is not identical to controller state.

For example, risk can be `elevated` while controller state is `monitoring`.

---

## 7. Drying Demand

The decision engine returns a structured result rather than a bare Boolean.

Conceptually:

```text
DryingDecision:
    demand: true/false
    risk: normal/elevated/high/critical/unknown
    reason: machine-readable code
    explanation: human-readable text
```

Possible reason codes include:

- `within_target`
- `rh_elevated`
- `rh_above_maximum`
- `rh_critical`
- `persistence_not_met`
- `recovering`
- `sensor_unavailable`
- `sensor_stale`
- `equipment_unavailable`

Reason codes should be stable enough for diagnostics/tests; UI text may be translated separately.

---

## 8. Dry Temperature Strategy

The first dynamic strategy is:

```text
requested_target = room_temperature + configured_offset
```

The requested target is then:

1. constrained to configured/device minimum and maximum;
2. rounded to the supported device step.

Example:

```text
Room temperature:       17.2 °C
Offset:                  +0.5 °C
Raw target:              17.7 °C
Device step:              1.0 °C
Applied target:          18.0 °C
```

The reason for using a room-relative setpoint is to avoid blindly imposing a fixed Dry temperature that may cause unnecessary cooling when the property is already cool.

This remains a testable control hypothesis, not an assumption that it is always the most energy-efficient GREE strategy.

---

## 9. Proposed State Behaviour

### IDLE
No intervention required.

Transitions:
- to `MONITORING` when conditions become elevated;
- to `DRYING` when demand is confirmed and action is permitted;
- to `FAULT` for invalid required inputs after the defined fault policy.

### MONITORING
Conditions are elevated but persistence/other criteria are not yet met.

Transitions:
- to `IDLE` if conditions recover;
- to `DRYING` when demand is confirmed;
- to `FAULT`/`INHIBITED` when appropriate.

### DRYING
Drying operation has been requested.

Rules:
- respect minimum run time;
- avoid repeated identical commands;
- stop when recovery criteria are met and minimum run time permits;
- obey maximum continuous runtime protection.

Transitions normally to `RECOVERY` after stopping.

### RECOVERY
Observe environmental response after a drying cycle.

Transitions:
- to `IDLE` when conditions remain acceptable;
- to `MONITORING` if humidity rises but demand is not yet confirmed;
- back to `DRYING` only when rest-time and demand criteria permit.

### PROTECTION
Reserved for conditions where moisture protection is needed but normal Dry operation is unsuitable/unavailable and an alternative request may be required.

V1 may expose the state before implementing alternative heat/cool action.

### INHIBITED
Automatic control is intentionally blocked.

Examples:
- profile Off;
- explicit equipment arbiter elsewhere;
- configured interlock.

### FAULT
Required control inputs are not trustworthy or required equipment cannot be controlled according to policy.

A fault must always have a reason.

---

## 10. Timing Protections

V1 controller needs configurable values for:

- normal high-RH persistence
- minimum Dry run time
- minimum off/rest time
- recovery observation time
- maximum continuous Dry runtime

Defaults must be conservative and documented when selected.

No timing protection may depend solely on an in-memory timer that disappears on Home Assistant restart.

---

## 11. Sensor Validity

The controller must reject:

- unavailable states
- unknown states
- non-numeric values
- impossible RH values outside 0–100%
- implausible/unsupported temperature input according to a documented broad safety range
- stale measurements when timestamp information permits staleness detection

Loss of optional power/energy sensors does not create a moisture-control fault.

---

## 12. Energy Boundary

Power consumption does not decide whether moisture risk exists.

During early releases energy data is used to answer:

> What did this drying cycle cost and what environmental improvement followed?

It is explicitly not used yet to automatically change thresholds or select learned strategies.

---

## 13. Initial Control Sequence

Conceptual deterministic flow:

```text
Read T and RH
   │
Validate inputs
   │
Calculate dew point and spread
   │
Classify moisture risk
   │
Apply persistence/hysteresis
   │
Determine drying demand
   │
State machine checks timing/interlocks
   │
If action permitted:
   calculate Dry target
   │
HVAC adapter requests Dry operation
   │
Continue monitoring
   │
When recovery criteria achieved:
   respect minimum run time
   stop Dry operation
   enter recovery
```

---

## 14. Questions Deliberately Left for Real-World Testing

The architecture must allow these to change without rewriting the integration:

- Best preferred/max/critical RH defaults.
- Best persistence time.
- Best Dry temperature offset.
- Whether GREE Dry behaviour changes materially with requested target.
- Whether a fixed target is cheaper than a dynamic offset in some temperature bands.
- Whether external dew point materially improves decisions.
- Whether heating support is useful/necessary in cold humid conditions.

These are empirical questions. V1 should collect evidence rather than pretend they are already solved.

---

## 15. V1 Principle

> ZEAL-Dry should take the smallest deterministic action justified by persistent moisture risk, protect the HVAC equipment from unnecessary cycling, and explain exactly why it acted.
## Controlled prototype safety policy (Blocks 6–7)

Live zones wait a full minimum rest period on every startup/reload, including
missing or malformed timer history. Interrupted owned runs are stopped before
new work. Service intent and ownership are saved before starting equipment.
Faults and inhibition record a stop time; elevated conditions retain an existing
run until both preferred targets are recovered (subject to maximum runtime).
Inputs not reported for 30 minutes are rejected. A service/equipment fault latches
until integration reload; pending stops continue to be retried each minute.
Select equipment dedicated to this controller; competing automations are unsupported.
An unexpected mode change during an owned run latches a fault and requests Off.
The adapter requires Dry and Off support, and sends temperature only when the
climate entity advertises target-temperature support. Configured limits are
intersected with the device grid in its own temperature units.
