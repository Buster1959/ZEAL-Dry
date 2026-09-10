"""Deterministic moisture decision engine for ZEAL-Dry.

This module evaluates environmental measurements only. It does not know about
Home Assistant entities, HVAC equipment, brands, or service calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from .environment import EnvironmentalReading


class MoistureRisk(StrEnum):
    """Moisture-risk classification."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MoistureThresholds:
    """Configurable humidity thresholds used by the decision engine."""

    preferred_rh: float = 60.0
    maximum_rh: float = 65.0
    critical_rh: float = 75.0
    high_rh_persistence: timedelta = timedelta(minutes=15)

    def __post_init__(self) -> None:
        """Reject threshold combinations that cannot behave predictably."""
        if not 0 < self.preferred_rh < self.maximum_rh < self.critical_rh <= 100:
            raise ValueError(
                "RH thresholds must satisfy 0 < preferred < maximum < critical <= 100"
            )
        if self.high_rh_persistence < timedelta(0):
            raise ValueError("high-RH persistence cannot be negative")


@dataclass(frozen=True, slots=True)
class DryingDecision:
    """Structured result returned by the moisture decision engine."""

    demand: bool
    risk: MoistureRisk
    reason: str
    explanation: str


def evaluate_moisture(
    reading: EnvironmentalReading | None,
    thresholds: MoistureThresholds,
    above_maximum_for: timedelta | None = None,
) -> DryingDecision:
    """Evaluate moisture risk and whether drying demand is justified."""
    if reading is None:
        return DryingDecision(
            demand=False,
            risk=MoistureRisk.UNKNOWN,
            reason="sensor_unavailable",
            explanation="Indoor environmental readings are not currently trustworthy.",
        )

    rh = reading.relative_humidity

    if rh >= thresholds.critical_rh:
        return DryingDecision(
            demand=True,
            risk=MoistureRisk.CRITICAL,
            reason="rh_critical",
            explanation=(
                f"Relative humidity is {rh:.1f}%, at or above the "
                f"{thresholds.critical_rh:.1f}% critical threshold."
            ),
        )

    if rh >= thresholds.maximum_rh:
        elapsed = above_maximum_for or timedelta(0)
        if elapsed >= thresholds.high_rh_persistence:
            minutes = int(elapsed.total_seconds() // 60)
            return DryingDecision(
                demand=True,
                risk=MoistureRisk.HIGH,
                reason="rh_above_maximum",
                explanation=(
                    f"Relative humidity is {rh:.1f}% and has remained at or above "
                    f"{thresholds.maximum_rh:.1f}% for {minutes} minutes."
                ),
            )

        required_minutes = int(thresholds.high_rh_persistence.total_seconds() // 60)
        return DryingDecision(
            demand=False,
            risk=MoistureRisk.ELEVATED,
            reason="persistence_not_met",
            explanation=(
                f"Relative humidity is {rh:.1f}%, above the "
                f"{thresholds.maximum_rh:.1f}% maximum, but the "
                f"{required_minutes}-minute persistence period has not yet been met."
            ),
        )

    if rh > thresholds.preferred_rh:
        return DryingDecision(
            demand=False,
            risk=MoistureRisk.ELEVATED,
            reason="rh_elevated",
            explanation=(
                f"Relative humidity is {rh:.1f}%, above the preferred "
                f"{thresholds.preferred_rh:.1f}% level but below the maximum threshold."
            ),
        )

    return DryingDecision(
        demand=False,
        risk=MoistureRisk.NORMAL,
        reason="within_target",
        explanation=(
            f"Relative humidity is {rh:.1f}%, within the preferred "
            f"{thresholds.preferred_rh:.1f}% target."
        ),
    )
