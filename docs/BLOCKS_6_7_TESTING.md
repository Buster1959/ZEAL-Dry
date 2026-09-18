# ZEAL-Dry 0.2.0 — Blocks 6–7

## Install this test build

1. Back up your existing `config/custom_components/zeal_dry` folder.
2. Extract the supplied archive. Copy its `custom_components/zeal_dry` folder
   into Home Assistant's `config/custom_components`, replacing the existing folder.
3. Restart Home Assistant. Existing monitoring and dummy zones keep their modes.
4. Open your ZEAL-Dry device. It now includes saved number/select settings and
   fault/condensation status. There is no need to recreate the dummy zone.
5. For real control, add a separate zone and explicitly choose **Live climate
   control**, then select indoor sensors and a Dry/Off-capable climate entity.
   Do not configure another ZEAL-Dry zone or another automation to command that AC.

This archive is a locally produced test build; it has not been published to HACS
or installed in your Home Assistant instance.

## Block 6

- Supplier-neutral Dry/Off commands and optional temperature support.
- Device bounds/resolution and Celsius/Fahrenheit conversion.
- Duplicate command suppression and a one-minute allowance for mode feedback.
- Equipment/service faults latch until integration reload. Pending stops retry
  each minute while the controller remains loaded. A successful service call is
  not proof that physical equipment obeyed; verify the AC during the first test.
- Every live startup/reload waits a full minimum rest period, at least ten minutes.
  A previously owned run, or a Dry mode observed at startup, is stopped first.
- Sensor loss, stale readings (30 minutes since the last Home Assistant
  `last_reported` timestamp), maximum runtime,
  profile Off and storage-write failures stop active control.
- State/ownership is saved before equipment starts. Abrupt shutdown cannot cause
  the next startup to bypass its fresh rest period.

## Block 7

Numbers: preferred RH, maximum RH, critical RH, Dry offset, dew-point safety
margin, fixed Dry temperature. Invalid threshold ordering is rejected.

Selectors: `property_protection`, `occupied`, `off`; and `room_offset`, `fixed`.
The two active profiles deliberately use the same deterministic thresholds in
this release. Off immediately stops an owned run and inhibits starting.

Options: RH persistence, minimum run/rest, recovery, maximum run, min/max target.
Defaults: 15 / 20 / 10 / 10 / 180 minutes and 16–20 °C targets. Minimum rest
cannot be set below ten minutes. Fixed targets are clamped to configured/device
limits; changing the fixed number alone does not expand those limits.

Status: fault, condensation risk, controller reason, moisture explanation and
run/rest timestamps. For live zones the proposed-target sensor shows the last
requested device target converted to Celsius; it is unknown when no temperature
command is applicable. Condensation risk means air spread is at or below the
configured margin (default 3 °C); it is an indicator, not a measured surface
condensation prediction, and does not independently command the AC.

## Acceptance checks in Home Assistant

1. Existing dummy zone: raise test RH to 90%; demand becomes true and dummy starts
   (after any restored rest period). Set profile Off; it stops immediately.
2. Change preferred RH and Dry offset; reload the integration and confirm both
   values and profile Off persist. Invalid preferred/maximum/critical ordering
   must be rejected without changing the previous values.
3. Select fixed strategy and 18 °C; the dummy target should be 18 °C independently
   of test room temperature, within configured limits.
4. Inspect fault and condensation sensors and the controller-reason attributes.
5. Live zone: check that the AC receives no start during its initial ten-minute
   rest. At confirmed moisture demand, verify Dry mode and the supported target
   on the actual AC. Watch the first complete cycle.
6. During a live run select Off and verify the AC stops. Reload and confirm no
   immediate restart. Restore an active profile only when ready for another run.
7. Temporarily make an input unavailable: expect fault and a stop request.
   Equipment/service failures require correction and an integration reload.

## Automated validation

Tested with Python 3.14 and Home Assistant 2026.9.2 using
`pytest-homeassistant-custom-component==0.13.365`.

Run `python -m pip install -r requirements-test.txt` then `python -m pytest -q`.
Validation result: **68 tests passed**.

Tests cover adapter requests/failures, grid conversion, restart rest protection,
state transitions, settings validation/restoration, full HA platform setup and
number/select service calls. Real hardware operation remains to be verified.

API references: [Climate entity](https://developers.home-assistant.io/docs/core/entity/climate/)
and [Home Assistant storage](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py).

## Readability revision

This revised 0.2.0 build retains the existing control behavior and test cases.
The controller update is organized into input evaluation, protection checks and
equipment requests. Local names are clearer, repeated fault updates share one
method, and the unused switch actuator has been removed.

Every production module, class and function now has a purpose annotation; the
static audit covers 19 modules and 130 classes/functions. Additional comments
explain restart protection, persistence and device rounding. `AGENTS.md` records
the human-readable, annotated, no-bloat rules for future work.

Retest: **68 passed**, plus import/unused-code lint and whitespace checks.
