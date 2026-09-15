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
) -> DryingDecision:
    """Evaluate both relative humidity and actual airborne moisture via dew point."""
    if reading is None:
        return DryingDecision(
            False,
            MoistureRisk.UNKNOWN,
            "sensor_unavailable",
            "Indoor environmental readings are not currently trustworthy.",
        )

    rh = reading.relative_humidity
    dp = reading.dew_point_c

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
    if dp >= thresholds.maximum_dew_point_c:
        return DryingDecision(
            True,
            MoistureRisk.HIGH,
            "dew_point_high",
            f"Dew point is {dp:.1f} °C, showing a high absolute moisture load above the {thresholds.maximum_dew_point_c:.1f} °C threshold.",
        )

    if rh >= thresholds.maximum_rh:
        elapsed = above_maximum_for or timedelta(0)
        if elapsed >= thresholds.high_rh_persistence:
            minutes = int(elapsed.total_seconds() // 60)
            return DryingDecision(
                True,
                MoistureRisk.HIGH,
                "rh_above_maximum",
                f"Relative humidity is {rh:.1f}% and has remained at or above {thresholds.maximum_rh:.1f}% for {minutes} minutes.",
            )
        required = int(thresholds.high_rh_persistence.total_seconds() // 60)
        return DryingDecision(
            False,
            MoistureRisk.ELEVATED,
            "persistence_not_met",
            f"Relative humidity is {rh:.1f}% above maximum, but the {required}-minute persistence period has not been met; dew point is {dp:.1f} °C.",
        )

    if dp > thresholds.preferred_dew_point_c:
        return DryingDecision(
            False,
            MoistureRisk.ELEVATED,
            "dew_point_elevated",
            f"Dew point is {dp:.1f} °C, above the preferred {thresholds.preferred_dew_point_c:.1f} °C moisture level but below the drying threshold.",
        )
    if rh > thresholds.preferred_rh:
        return DryingDecision(
            False,
            MoistureRisk.ELEVATED,
            "rh_elevated",
            f"Relative humidity is {rh:.1f}%, above the preferred {thresholds.preferred_rh:.1f}% level.",
        )

    return DryingDecision(
        False,
        MoistureRisk.NORMAL,
        "within_target",
        f"Airborne moisture is within target: {rh:.1f}% RH and {dp:.1f} °C dew point.",
    )
