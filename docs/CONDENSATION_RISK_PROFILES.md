# Condensation risk and Drying response

ZEAL-Dry keeps the measured condition separate from the owner's cost and
protection preference. The Overview reports the highest risk found from
relative humidity, absolute dew point and dew-point spread. Setup controls when
that risk is allowed to create normal Dry demand.

## Dew-point spread scale

Dew-point spread is room temperature minus dew point. A smaller value means the
air is closer to saturation. It does not measure the temperature of walls,
windows or other surfaces, so the scale describes airborne condensation risk
rather than guaranteeing that condensation cannot occur.

| Risk | Dew-point spread | Meaning |
| --- | ---: | --- |
| Normal | Above 6 °C | Air is comparatively far from saturation. |
| Elevated | Above 4 °C to 6 °C | Moisture deserves attention; early protection may act. |
| High | Above 2 °C to 4 °C | Air is close enough to saturation for the Balanced response to act. |
| Critical | 2 °C or less | Air is very close to saturation; every response permits Dry demand. |

ZEAL-Dry also evaluates relative humidity and absolute dew point. The displayed
risk is the highest risk produced by any of these measurements. Warming can
lower relative humidity without removing water, which is why RH is never used
alone.

## Drying response choices

| Setup choice | Normal action threshold | Cost/protection trade-off |
| --- | --- | --- |
| Early protection | Elevated or higher | Starts earliest and may use the most energy. |
| Balanced | High or Critical | Default compromise between protection and runtime. |
| Economy | Critical only | Minimises normal runtime but accepts a narrower margin before action. |

Critical relative humidity and critical absolute dew point remain immediate
protection conditions under every response. The response selector cannot turn
off sensor validation, minimum run/rest periods, maximum runtime or equipment
fault protection. Use the separate **Off** operating profile when monitoring is
required without automatic ACU control.

## Example

At 24 °C and 60% RH, the dew point is approximately 15.8 °C. That crosses the
default High absolute-dew-point threshold even though the spread is wider:

- Early protection permits Dry demand.
- Balanced permits Dry demand.
- Economy continues monitoring unless RH or absolute dew point independently
  reaches a Critical threshold.

Actual runtime depends on changing room conditions, ACU behaviour, minimum
runtime, rest periods and the configured maximum continuous runtime. The
profiles do not estimate or guarantee energy cost.
