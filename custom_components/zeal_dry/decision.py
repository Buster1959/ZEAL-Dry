"""Deterministic moisture decision engine for ZEAL-Dry.

Evaluate moisture conditions only; no Home Assistant or equipment knowledge lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from .environment import EnvironmentalReading


class MoistureRisk(StrEnum):
    """Name the moisture severity independently of equipment state."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


RISK_RANK = {
    MoistureRisk.NORMAL: 0,
    MoistureRisk.ELEVATED: 1,
    MoistureRisk.HIGH: 2,
    MoistureRisk.CRITICAL: 3,
    MoistureRisk.UNKNOWN: -1,
}

RESPONSE_THRESHOLD = {
    "early_protection": MoistureRisk.ELEVATED,
    "balanced": MoistureRisk.HIGH,
    "economy": MoistureRisk.CRITICAL,
}


@dataclass(frozen=True, slots=True)
class MoistureThresholds:
    """Configurable RH and dew-point thresholds."""

    preferred_rh: float = 60.0
    maximum_rh: float = 65.0
    critical_rh: float = 75.0
    high_rh_persistence: timedelta = timedelta(minutes=15)
    preferred_dew_point_c: float = 12.0
    maximum_dew_point_c: float = 15.0
    critical_dew_point_c: float = 17.0

    def __post_init__(self) -> None:
        """Require increasing RH and dew-point thresholds and nonnegative persistence."""
        if not 0 < self.preferred_rh < self.maximum_rh < self.critical_rh <= 100:
            raise ValueError(
                "RH thresholds must satisfy 0 < preferred < maximum < critical <= 100"
            )
        if (
            not self.preferred_dew_point_c
            < self.maximum_dew_point_c
            < self.critical_dew_point_c
        ):
            raise ValueError(
                "dew-point thresholds must satisfy preferred < maximum < critical"
            )
        if self.high_rh_persistence < timedelta(0):
            raise ValueError("high-RH persistence cannot be negative")


@dataclass(frozen=True, slots=True)
class DryingDecision:
    """Carry drying demand, moisture risk and an explanation of the decision."""

    demand: bool
    risk: MoistureRisk
    reason: str
    explanation: str


def evaluate_moisture(
    reading: EnvironmentalReading | None,
    thresholds: MoistureThresholds,
    above_maximum_for: timedelta | None = None,
    response_profile: str = "balanced",
) -> DryingDecision:
    """Classify combined moisture risk and apply the selected response threshold."""
    if response_profile not in RESPONSE_THRESHOLD:
        raise ValueError(f"Invalid response profile: {response_profile}")
    if reading is None:
        return DryingDecision(
            False,
            MoistureRisk.UNKNOWN,
            "sensor_unavailable",
            "Indoor environmental readings are not currently trustworthy.",
        )

    rh = reading.relative_humidity
    dp = reading.dew_point_c
    spread = reading.dew_point_spread_c

    # Dew point represents actual airborne moisture. A critical DP does not wait
    # for an RH persistence timer because warming alone cannot remove that water.
    if dp >= thresholds.critical_dew_point_c:
        return DryingDecision(
            True,
            MoistureRisk.CRITICAL,
            "dew_point_critical",
            f"Dew point is {dp:.1f} °C, at or above the {thresholds.critical_dew_point_c:.1f} °C critical moisture threshold.",
        )
    if rh >= thresholds.critical_rh:
        return DryingDecision(
            True,
            MoistureRisk.CRITICAL,
            "rh_critical",
            f"Relative humidity is {rh:.1f}%, at or above the {thresholds.critical_rh:.1f}% critical threshold.",
        )

    candidates: list[tuple[MoistureRisk, str, str]] = []
    if dp >= thresholds.maximum_dew_point_c:
        candidates.append(
            (
                MoistureRisk.HIGH,
                "dew_point_high",
                f"Dew point is {dp:.1f} °C, showing a high absolute moisture load above the {thresholds.maximum_dew_point_c:.1f} °C threshold.",
            )
        )
    elif dp > thresholds.preferred_dew_point_c:
        candidates.append(
            (
                MoistureRisk.ELEVATED,
                "dew_point_elevated",
                f"Dew point is {dp:.1f} °C, above the preferred {thresholds.preferred_dew_point_c:.1f} °C moisture level.",
            )
        )

    if rh >= thresholds.maximum_rh:
        elapsed = above_maximum_for or timedelta(0)
        if elapsed >= thresholds.high_rh_persistence:
            minutes = int(elapsed.total_seconds() // 60)
            candidates.append(
                (
                    MoistureRisk.HIGH,
                    "rh_above_maximum",
                    f"Relative humidity is {rh:.1f}% and has remained at or above {thresholds.maximum_rh:.1f}% for {minutes} minutes.",
                )
            )
        else:
            required = int(thresholds.high_rh_persistence.total_seconds() // 60)
            candidates.append(
                (
                    MoistureRisk.ELEVATED,
                    "persistence_not_met",
                    f"Relative humidity is {rh:.1f}% above maximum, but the {required}-minute persistence period has not been met.",
                )
            )
    elif rh > thresholds.preferred_rh:
        candidates.append(
            (
                MoistureRisk.ELEVATED,
                "rh_elevated",
                f"Relative humidity is {rh:.1f}%, above the preferred {thresholds.preferred_rh:.1f}% level.",
            )
        )

    if spread <= 2.0:
        candidates.append(
            (MoistureRisk.CRITICAL, "spread_critical", f"Dew-point spread is {spread:.1f} °C, at or below the 2.0 °C critical boundary.")
        )
    elif spread <= 4.0:
        candidates.append(
            (MoistureRisk.HIGH, "spread_high", f"Dew-point spread is {spread:.1f} °C, within the 2–4 °C high-risk band.")
        )
    elif spread <= 6.0:
        candidates.append(
            (MoistureRisk.ELEVATED, "spread_elevated", f"Dew-point spread is {spread:.1f} °C, within the 4–6 °C elevated-risk band.")
        )

    if not candidates:
        return DryingDecision(
            False,
            MoistureRisk.NORMAL,
            "within_target",
            f"Airborne moisture is within target: {rh:.1f}% RH, {dp:.1f} °C dew point and {spread:.1f} °C spread.",
        )

    risk, reason, explanation = max(candidates, key=lambda item: RISK_RANK[item[0]])
    threshold = RESPONSE_THRESHOLD[response_profile]
    demand = RISK_RANK[risk] >= RISK_RANK[threshold]
    if demand:
        explanation += f" The {response_profile.replace('_', ' ')} response permits Dry demand at {risk.value} risk."
    else:
        explanation += f" The {response_profile.replace('_', ' ')} response continues monitoring until {threshold.value} risk."
    return DryingDecision(demand, risk, reason, explanation)
