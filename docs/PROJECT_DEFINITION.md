# ZEAL-Dry — Project Definition

## 1. Purpose

ZEAL-Dry is a standalone Home Assistant custom integration for protecting buildings and rooms from excessive humidity, condensation and damp while minimising unnecessary heating, cooling and electrical energy use.

The initial use case is an intermittently occupied property in a warm, humid climate where split air-conditioning units can operate in Dry mode. The property may be empty for extended periods and the objective is not primarily occupant comfort; it is to keep the building fabric and contents in a safe moisture range at the lowest practical running cost.

ZEAL-Dry must be capable of operating independently of ZEAL. Where both integrations are installed, they should cooperate through clearly defined interfaces so that two controllers do not compete for the same HVAC equipment.

---

## 2. Problem Statement

A fixed automation such as:

> If humidity exceeds 70%, turn on Dry mode.

is too simplistic for an unoccupied building.

Relative humidity changes with temperature. Heating a room can lower relative humidity without removing moisture, while cooling can bring surfaces closer to dew point. An air-conditioner's Dry mode may remove water efficiently, but the available Dry temperature range may be constrained by the appliance.

The controller therefore needs to consider several variables together:

- room air temperature;
- relative humidity;
- calculated dew point;
- safe margin above dew point;
- external environmental conditions where available;
- current HVAC state;
- the capabilities and limits of the controlled device;
- measured electrical energy use where Home Assistant provides it;
- occupancy / away state;
- recent moisture and temperature trends;
- minimum run and rest periods to prevent short cycling.

ZEAL-Dry should make a continuous building-protection decision rather than execute isolated threshold automations.

---

## 3. Core Design Principle

ZEAL-Dry is a **building moisture controller**, not a conventional comfort thermostat.

Its primary question is:

> What is the lowest-energy safe action required to keep this space dry and reduce condensation or mould risk?

Possible answers include:

- do nothing;
- run Dry mode;
- change the Dry-mode temperature target;
- request heating support;
- request cooling/dehumidification support;
- stop HVAC because the target condition has been achieved;
- inhibit an action because it could create condensation risk.

The integration must distinguish between:

1. **Relative humidity reduction caused only by warming the air**, and
2. **Actual moisture removal from the air/building through dehumidification.**

Energy consumption may be used as an optimisation and diagnostic input but should not be the sole indication that moisture has been removed.

---

## 4. Relationship to ZEAL

### 4.1 Independent operation

ZEAL-Dry must not require ZEAL.

A user should be able to install ZEAL-Dry and configure:

- one or more rooms/areas;
- a temperature sensor;
- a humidity sensor;
- an optional external temperature/humidity source;
- a controllable climate entity, dehumidifier or other supported drying device;
- an optional power/energy sensor.

This makes the integration useful for:

- holiday homes;
- basements and cellars;
- garages;
- workshops;
- boats;
- caravans;
- storage rooms;
- outbuildings;
- apartments;
- any intermittently occupied damp-prone space.

### 4.2 Cooperation with ZEAL

When ZEAL is present, ZEAL-Dry should communicate a **moisture-control requirement** rather than blindly seize control of shared HVAC equipment.

ZEAL should remain capable of acting as the whole-building HVAC arbiter when heat/cool/dry requests compete.

The interface should therefore expose explicit demand and state entities rather than rely on hidden coupling.

Potential interface entities include:

- `binary_sensor.zeal_dry_demand`
- `sensor.zeal_dry_risk`
- `sensor.zeal_dry_dew_point`
- `sensor.zeal_dry_state`
- `sensor.zeal_dry_recommended_mode`

ZEAL may consume those entities without ZEAL-Dry importing or depending on ZEAL code.

The integrations must never silently fight by repeatedly commanding different modes or setpoints on the same climate entity.

---

## 5. Initial Device Use Case — GREE / Split AC

The initial reference system uses GREE-compatible split air-conditioning units exposed to Home Assistant as climate entities.

The current observed Dry-mode temperature range is approximately **16–20 °C**. ZEAL-Dry must not hard-code these values globally; device-specific limits should be discovered from Home Assistant where possible or configurable by the user.

A key control concept to test is dynamic Dry-mode temperature targeting relative to the actual room temperature rather than always using a fixed setpoint.

Example:

```text
Room temperature = 17.2 °C
Configured Dry offset = +0.5 °C
Requested Dry target = 17.7 °C
Device-supported resolution = 1 °C
Applied target = 18 °C
```

The resulting value must be constrained by the device's supported minimum and maximum Dry-mode temperatures.

Conceptually:

```text
requested_dry_temperature = room_temperature + configured_offset
applied_temperature = clamp(requested_dry_temperature, dry_minimum, dry_maximum)
```

This behaviour is a hypothesis to be validated against real GREE operation and measured power consumption. The integration architecture should support alternative strategies if testing shows that a different relationship between room temperature and Dry setpoint is more efficient.

---

## 6. Control Inputs

### Required per controlled room/zone

- Room temperature
- Relative humidity
- Controllable drying/HVAC device

### Calculated

- Dew point
- Dew-point margin
- Humidity trend
- Temperature trend
- Moisture-risk state
- Drying demand

### Optional

- HVAC power sensor
- HVAC energy sensor
- Outdoor temperature
- Outdoor humidity
- Outdoor dew point
- Occupancy / away state
- Door/window state
- Additional surface-temperature sensors

No optional sensor should be required for basic operation.

---

## 7. User Configuration

The integration should expose sensible defaults but allow control parameters to be changed from Home Assistant rather than YAML wherever practical.

Initial configuration candidates:

### Moisture targets

- Preferred relative humidity
- Maximum acceptable relative humidity
- Critical relative humidity
- Dew-point safety margin

### Dry-mode control

- Dry temperature strategy
- Dry temperature offset from room temperature
- Minimum Dry temperature
- Maximum Dry temperature
- Setpoint rounding/resolution

### Runtime protection

- Minimum run time
- Minimum off/rest time
- Maximum continuous run time
- Post-drying observation period

### Energy optimisation

- Enable energy-aware optimisation
- Power entity
- Energy entity
- Optional maximum daily energy budget

### Occupancy

- Occupied profile
- Unoccupied/property-protection profile

The initial version should prioritise reliable automatic operation over exposing every possible tuning parameter.

---

## 8. Proposed Controller States

ZEAL-Dry should have an explicit state machine so its behaviour is understandable and diagnosable.

Proposed initial states:

### `idle`
Conditions are acceptable and no moisture-control action is required.

### `monitoring`
Conditions are elevated but remain inside acceptable limits. Trends are monitored before committing to HVAC operation.

### `drying`
Dry/dehumidification operation is active.

### `recovery`
The target has been achieved and the controller is observing the room before deciding whether another drying cycle is required.

### `protection`
Conditions require intervention but the preferred drying action cannot safely or effectively be used. This may result in a heat/cool request to ZEAL or another supported action.

### `inhibited`
Control is intentionally suspended because of a user setting, unavailable sensor, open door/window, equipment state or another configured interlock.

### `fault`
Required inputs or equipment are unavailable or invalid for long enough that automatic control can no longer be trusted.

---

## 9. Humidity and Dew-Point Logic

ZEAL-Dry must calculate dew point from room temperature and relative humidity.

A suitable standard approximation such as the Magnus formula should be used and documented in the implementation.

The controller must not treat relative humidity alone as the complete measure of moisture risk.

For example, a rise in room temperature can cause RH to fall while absolute moisture remains almost unchanged. Conversely, cooling air towards its dew point can create condensation even though the controller is attempting to remove moisture.

The decision engine should therefore use:

- relative humidity;
- dew point;
- temperature-to-dew-point spread;
- rate of change;
- persistence above thresholds.

Future versions may add absolute humidity or humidity ratio if testing shows it improves control decisions.

---

## 10. Energy-Aware Control

One of ZEAL-Dry's design goals is to learn which available intervention protects the property at the lowest practical cost.

Where Home Assistant supplies HVAC power or energy data, ZEAL-Dry should record enough information to compare drying cycles, including:

- start time;
- stop time;
- starting temperature;
- starting RH;
- starting dew point;
- ending temperature;
- ending RH;
- ending dew point;
- energy consumed;
- selected operating mode;
- selected target temperature;
- amount of moisture-condition improvement achieved.

Initial releases should use this information primarily for diagnostics and reporting.

Automatic optimisation/learning should be introduced only after deterministic control is proven reliable.

The project should avoid assuming that instantaneous power consumption directly represents moisture removal. The useful metric is the environmental improvement achieved for the energy consumed over a complete control cycle.

---

## 11. Home Assistant Entity Model

Exact names will be determined during implementation, but an individual ZEAL-Dry zone could expose entities similar to:

### Sensors

- Current dew point
- Dew-point margin
- Moisture risk
- Controller state
- Drying demand/reason
- Current requested Dry temperature
- Last drying-cycle duration
- Last drying-cycle energy
- Daily drying energy

### Binary sensors

- Drying required
- Condensation risk
- Controller fault

### Numbers

- Preferred RH
- Maximum RH
- Dew-point margin
- Dry temperature offset

### Selects

- Operating profile: `Occupied`, `Property Protection`, `Off`
- Dry temperature strategy

### Switches

Only where a genuine persistent enable/disable control is appropriate. Controller states should not be represented as switches merely for UI convenience.

---

## 12. Areas, Rooms and Zones

ZEAL-Dry should use Home Assistant-native concepts wherever possible.

A ZEAL-Dry controlled space should preferably reference a Home Assistant Area rather than create a separate proprietary room database.

Multiple areas may later be grouped into a ZEAL-Dry zone where one HVAC unit influences several spaces.

The initial implementation should avoid unnecessary floor/zone complexity until a genuine control requirement exists.

---

## 13. Multiple AC Units

A property may contain several independently controlled AC units.

ZEAL-Dry should support one controller instance per logical controlled area/device while allowing future whole-property coordination.

Whole-property coordination could later consider:

- whether drying one room affects neighbouring rooms;
- simultaneous-start electrical load;
- selecting the most efficient unit first;
- circulation between spaces;
- shared outdoor conditions.

These are not required for V1 unless testing demonstrates they are necessary.

---

## 14. Safety and Failure Behaviour

ZEAL-Dry must fail conservatively and visibly.

Examples:

- Invalid humidity reading must not cause indefinite HVAC operation.
- Unavailable temperature data should inhibit calculations that depend on it.
- Loss of a power sensor must not disable basic moisture protection.
- Loss of ZEAL must not prevent standalone ZEAL-Dry operation unless ZEAL is explicitly configured as the equipment arbiter.
- Restarting Home Assistant must not immediately cause repeated compressor start/stop cycling.
- Device commands must respect minimum run/rest periods.

Every inhibited or failed decision should have a human-readable reason available in diagnostics.

---

## 15. Diagnostics

Diagnostics are a first-class requirement.

For every control decision, the integration should be able to explain conceptually:

```text
State: DRYING
Room temperature: 17.2 °C
Relative humidity: 73 %
Dew point: 12.3 °C
RH target: 65 %
Dry strategy: room + 0.5 °C
Requested target: 17.7 °C
Applied device target: 18 °C
Reason: humidity above maximum threshold for configured persistence period
```

Diagnostics should make it possible to determine why ZEAL-Dry acted without enabling debug logging for normal investigation.

Home Assistant diagnostics downloads must redact identifiers and sensitive data in accordance with Home Assistant conventions.

---

## 16. Automation Boundary

ZEAL-Dry should replace complex humidity-management automations, not prevent users from automating around it.

The integration owns:

- moisture calculations;
- dew-point calculations;
- control state;
- hysteresis;
- persistence/timing;
- dynamic Dry setpoint selection;
- equipment protection;
- energy-cycle measurement;
- decision making.

Home Assistant automations remain appropriate for higher-level events such as:

- property occupied/unoccupied;
- holiday mode;
- special tariffs;
- alarm state;
- notifying the owner;
- unusual environmental events.

The architecture should avoid requiring users to reproduce the control algorithm in YAML.

---

## 17. V1 Scope

The first release should prove the controller rather than attempt to solve every humidity-control scenario.

### V1 must provide

- Home Assistant custom integration installation and config flow;
- one or more independently configured controlled areas;
- temperature and humidity sensor selection;
- dew-point calculation;
- RH/dew-point based drying demand;
- climate entity selection;
- Dry-mode operation;
- dynamic/configurable Dry temperature targeting;
- device min/max clamping;
- hysteresis and anti-short-cycle timing;
- explicit controller state;
- useful HA entities;
- optional power/energy measurement;
- diagnostics;
- restart-safe behaviour;
- no dependency on ZEAL.

### V1 should not include

- machine-learning control;
- automatic long-term optimisation;
- weather forecasting as a required control input;
- complex whole-property optimisation;
- proprietary cloud services;
- mandatory ZEAL integration;
- a separate scheduler unless a genuine requirement emerges.

---

## 18. Future Development

Potential later releases may add:

### V2 — Measurement and optimisation

- drying-cycle history;
- comparative energy efficiency;
- automatic tuning of Dry temperature offset;
- external dew-point comparison;
- ventilation opportunity detection;
- richer dashboards/statistics.

### V3 — Predictive building protection

- weather forecast inputs;
- predicted humidity risk;
- tariff-aware pre-drying;
- thermal/moisture response modelling;
- coordinated multi-room operation.

### ZEAL cooperation

- formal demand API/entity contract;
- whole-home arbitration between Heat, Cool and Dry;
- shared occupied/away state where explicitly configured;
- ZEAL UI indication of active moisture-protection demand.

The standalone ZEAL-Dry controller must remain usable even as ZEAL cooperation becomes richer.

---

## 19. Development Principles

1. **Home Assistant native first.** Use standard climate, sensor, area, device and config-flow mechanisms wherever possible.
2. **Standalone by design.** ZEAL integration is optional cooperation, never a hidden dependency.
3. **Deterministic before intelligent.** Prove understandable rules before adding learning or optimisation.
4. **Explain every decision.** The user should be able to see why the controller is running.
5. **Protect the building first.** Energy optimisation must never override configured moisture-safety limits.
6. **Avoid competing control.** There must be a defined owner/arbitration mechanism for shared HVAC entities.
7. **No unnecessary YAML.** Normal configuration and tuning should be possible through the Home Assistant UI.
8. **Avoid project bloat.** Features should be added because they support the moisture-control problem, not merely because the data is available.

---

## 20. Reference Architecture

```text
                 Home Assistant
                       │
       ┌───────────────┼────────────────┐
       │               │                │
 Temperature        Humidity       Power/Energy
   sensor             sensor          (optional)
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                 ZEAL-Dry Zone
                       │
              ┌────────┴─────────┐
              │                  │
        Moisture model      State machine
       RH / dew point       timers / limits
              │                  │
              └────────┬─────────┘
                       ▼
                Decision engine
                       │
             ┌─────────┴──────────┐
             │                    │
      Standalone control      ZEAL demand
      climate/dehumidifier    (if configured)
             │                    │
             └─────────┬──────────┘
                       ▼
                 HVAC equipment
```

---

## 21. Definition of Success

ZEAL-Dry is successful when an owner can leave a property unattended and confidently answer all of the following from Home Assistant:

- Is the property currently at risk from excessive humidity or condensation?
- Is ZEAL-Dry doing anything about it?
- Why did it choose that action?
- What Dry temperature is it requesting and why?
- Is the room actually becoming safer rather than simply warmer?
- How much energy is moisture protection consuming?
- Can it operate safely without a collection of interdependent automations?

The goal is not to maintain hotel-room comfort in an empty building.

The goal is to maintain a **dry, protected building with the minimum sensible energy input**.
