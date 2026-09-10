# ZEAL-Dry — UI Design

## 1. Design Standard

ZEAL-Dry should follow the same design philosophy established by ZEAL:

- simple and reassuring at the front;
- sophisticated logic underneath;
- clear separation between day-to-day control and setup;
- explainable decisions rather than opaque state changes;
- Home Assistant-native terminology and entities;
- mobile-friendly quick understanding, with richer detail available on desktop;
- supplier-independent presentation.

The UI should feel like a member of the ZEAL family, but ZEAL-Dry must remain a standalone integration.

A user should be able to answer three questions immediately from the main interface:

1. Is the property/room currently safe from a moisture perspective?
2. Is ZEAL-Dry doing anything about it?
3. Why is it doing, or not doing, that action?

---

## 2. Top-Level Navigation

Preferred navigation:

```text
Overview | Control | Areas | Performance | Setup
```

Diagnostics should be available from Setup rather than occupying a top-level navigation tab.

No dedicated scheduler page is required for V1. ZEAL-Dry is primarily condition-driven, not time-driven. Home Assistant automations can change profiles where scheduling is needed.

---

## 3. Overview

The Overview is the primary status page and should provide a whole-property or whole-installation summary.

### 3.1 Overall status

The page should begin with a strong, human-readable overall state such as:

- `PROPERTY PROTECTED`
- `MONITORING`
- `DRYING`
- `MOISTURE RISK`
- `ACTION INHIBITED`
- `FAULT`

Example:

```text
ZEAL Dry
PROPERTY PROTECTED ✓
```

The visual treatment should make normal/safe states immediately distinguishable from warning/fault states without requiring the user to interpret raw values.

### 3.2 Indoor summary

Show key indoor conditions:

- current temperature;
- current relative humidity;
- indoor dew point;
- optional humidity trend;
- optional temperature-to-dew-point margin.

Example:

```text
Indoor
17.4 °C
62 % RH
Dew point 10.1 °C
```

### 3.3 Outdoor summary

Where an external environment source is configured, show:

- outdoor temperature;
- outdoor relative humidity where available;
- outdoor dew point;
- dew-point difference between indoors and outdoors;
- simple interpretation such as `Outside air drier` or `Outside air wetter`.

Example:

```text
Outside
14.6 °C
Dew point 8.4 °C
Outdoor drying potential: Favourable
```

The external data source must remain supplier-independent. The UI should not be branded around Pirate Weather, OpenWeatherMap, AEMET or any other provider.

### 3.4 System summary

Show:

- controller state;
- current action;
- current requested target;
- current drying device state;
- drying energy today where available;
- last control decision/reason.

Example:

```text
System
Monitoring
No drying required
0.42 kWh today
```

### 3.5 Area cards

Each configured area should appear as a compact card showing the values needed to judge its condition quickly.

Suggested card contents:

- area name;
- temperature;
- RH;
- indoor dew point;
- outdoor dew point or dew-point differential where configured;
- current controller state;
- current drying target;
- current drying device state;
- concise reason text.

---

## 4. Control

The Control page is the day-to-day user interaction page, equivalent in philosophy to ZEAL's Quick Change functionality.

It should deliberately avoid engineering parameters.

### 4.1 Operating profile

Initial profile selector:

- `Occupied`
- `Property Protection`
- `Off`

`Property Protection` is expected to be the main unattended-building mode.

### 4.2 User-facing moisture targets

Expose only the controls that make sense to a normal user, such as:

- preferred RH;
- maximum acceptable RH.

Advanced thresholds and internal hysteresis should remain in Setup unless later user testing demonstrates that they belong here.

### 4.3 Manual override

A manual Dry override may be provided, for example:

- Dry now for 1 hour;
- Dry now for 2 hours;
- Dry now for 4 hours;
- Cancel manual drying.

Any manual override must remain subject to equipment safety, sensor validity and anti-short-cycle rules.

### 4.4 Current request and explanation

The page should clearly show:

- what ZEAL-Dry currently wants the equipment to do;
- whether that action has actually been applied;
- the reason for the decision.

Example:

```text
Drying required
Humidity has remained above the 65 % target for 18 minutes.
Indoor dew point is 12.3 °C.
Outdoor dew point is 9.1 °C.
Dry mode requested at 18 °C.
```

When no action is required:

```text
No action required
Humidity is 62 % and falling.
The room remains within the Property Protection target.
```

---

## 5. Areas

The Areas page provides detailed status for each logical controlled area or room.

The design should remain based on Home Assistant areas wherever practical rather than introducing a separate proprietary room database.

Each area view should include:

### Environment

- room temperature;
- RH;
- indoor dew point;
- temperature-to-dew-point margin;
- temperature trend;
- humidity trend.

### External comparison

Where configured:

- outdoor temperature;
- outdoor RH;
- outdoor dew point;
- indoor/outdoor dew-point difference;
- interpretation of outdoor drying potential.

### Controller

- current ZEAL-Dry state;
- current drying demand;
- demand reason;
- requested drying target;
- applied device target;
- time in current state;
- time since last drying cycle.

### Equipment

- configured drying device;
- current HA-reported operating mode/state;
- whether the requested action was accepted/applied;
- current power where available;
- current cycle energy where available.

Example compact area summary:

```text
Bedroom
17.4 °C | 72 % RH
Indoor DP 12.3 °C
Outdoor DP 9.1 °C
Drying potential: Good
State: Drying
Target: 18 °C
Reason: RH above 65 % target
```

---

## 6. Performance

The Performance page is important because ZEAL-Dry is intended not only to protect the building but to do so with minimal unnecessary energy use.

V1 should concentrate on observation and measurement rather than automatic optimisation.

Useful charts and statistics include:

- room RH over time;
- room temperature over time;
- indoor dew point over time;
- outdoor dew point over time;
- drying cycles;
- HVAC/dehumidifier power;
- drying energy by day;
- runtime by day;
- time spent above target RH;
- time spent in each controller state.

Later versions may add derived efficiency metrics such as:

- RH improvement per kWh;
- dew-point reduction per kWh;
- comparison of Dry target strategies;
- comparison of equipment/actions;
- cost per drying cycle.

Performance data should be used to prove whether strategies such as `room temperature + 0.5 °C` or `room temperature + 1.0 °C` are actually effective and economical rather than assuming they are.

---

## 7. Setup

Setup contains configuration and engineering controls that are not needed during normal operation.

### 7.1 Area configuration

Per controlled area:

- Home Assistant Area;
- indoor temperature sensor;
- indoor humidity sensor;
- drying/HVAC device;
- optional power sensor;
- optional energy sensor;
- optional external environment source.

### 7.2 Moisture thresholds

- preferred RH;
- maximum RH;
- critical RH;
- dew-point safety margin;
- persistence times;
- hysteresis.

### 7.3 Dry strategy

- dry target strategy;
- room-temperature offset;
- configured minimum target if discovery is unavailable;
- configured maximum target if discovery is unavailable;
- setpoint resolution/rounding only where required.

The core UI and control logic must not use supplier names.

### 7.4 Runtime/equipment protection

- minimum run time;
- minimum off/rest time;
- maximum continuous runtime;
- post-drying observation/recovery period.

### 7.5 External environment

ZEAL-Dry should ask for an optional generic external weather/environment entity or sensors.

The UI should refer to:

```text
External environment source
```

or

```text
External weather entity
```

not to a specific provider such as Pirate Weather.

The adapter should consume standard Home Assistant values where available and calculate outdoor dew point itself from temperature and humidity when needed.

Pirate Weather may be used as the initial real-world test source but must never become a required dependency or UI concept.

---

## 8. Diagnostics

Diagnostics should be reachable from Setup and should explain the controller in detail.

The aim is that a user can understand a decision without enabling debug logging.

A diagnostic decision view should be able to show:

```text
State: DRYING
Room temperature: 17.2 °C
Relative humidity: 73 %
Indoor dew point: 12.3 °C
Outdoor dew point: 9.1 °C
RH target: 65 %
Dry strategy: room + 0.5 °C
Requested target: 17.7 °C
Applied target: 18 °C
Equipment mode: Dry
Reason: humidity above maximum threshold for persistence period
```

Diagnostics should also expose:

- unavailable or stale sensors;
- device capability discovery;
- configured fallback limits;
- timers and lockouts;
- last state transition;
- last command issued;
- last command result where available;
- energy sensor availability;
- external environment availability;
- controller fault/inhibition reason.

Home Assistant diagnostic downloads must redact sensitive identifiers in accordance with HA conventions.

---

## 9. Supplier Independence in the UI

Supplier independence is a mandatory design rule.

ZEAL-Dry should present capabilities and entities, never brands.

Use labels such as:

- `Drying device`
- `Climate entity`
- `External environment source`
- `Power sensor`
- `Energy sensor`

Do not build user-facing flows around labels such as:

- `GREE air conditioner`
- `Pirate Weather settings`
- `Daikin Dry mode`

Manufacturer-specific accommodations may exist only in the equipment adapter/capability layer and should not leak into the core UI unless absolutely required to explain an unsupported capability.

The rule is:

> ZEAL-Dry controls capabilities, not brands.

---

## 10. Mobile and Desktop Behaviour

The UI should follow ZEAL's principle of making mobile suitable for rapid status checks and quick changes while allowing desktop to expose richer detail.

### Mobile priorities

- overall protection status;
- current RH and dew point;
- current action;
- profile selector;
- manual override;
- concise area cards;
- warning/fault visibility.

### Desktop priorities

- multi-area overview;
- charts and performance data;
- full diagnostics;
- detailed setup;
- side-by-side indoor/outdoor comparison.

The same information architecture should be preserved across screen sizes rather than creating two fundamentally different applications.

---

## 11. V1 UI Boundary

### V1 should include

- Overview;
- Control;
- Areas;
- Performance basic metrics/charts;
- Setup;
- Diagnostics;
- profile selection;
- manual Dry override;
- indoor/outdoor dew-point display;
- clear human-readable decision explanations;
- supplier-independent labels and flows;
- responsive mobile/desktop layouts.

### V1 should not include

- a scheduler;
- machine-learning controls;
- automatic strategy optimisation controls;
- supplier-specific configuration pages;
- complex whole-property optimisation controls;
- excessive engineering options on the Control page.

---

## 12. UI Acceptance Principles

Before the frontend is considered complete for a build block, it should satisfy these checks:

1. A normal user can tell whether the property is protected within a few seconds.
2. The current action and reason are visible without opening diagnostics.
3. Setup and day-to-day control are clearly separated.
4. Supplier names do not appear in generic configuration flows.
5. External environment data is optional and provider-independent.
6. Missing optional sensors degrade gracefully.
7. Mobile remains useful without needing desktop access.
8. The UI never implies that lower RH necessarily means moisture was physically removed.
9. Performance data is observational in V1 and does not silently alter control behaviour.
10. The UI reflects the controller's actual state rather than inventing presentation-only states.

---

## 13. Core UI Philosophy

The ZEAL-Dry UI should embody one principle above all:

> Simple at the front, sophistication underneath.

The user should not need to understand psychrometrics, dew-point mathematics, compressor behaviour or supplier-specific quirks to know whether the property is protected.

At the same time, every important control decision must be explainable when the user chooses to look deeper.
