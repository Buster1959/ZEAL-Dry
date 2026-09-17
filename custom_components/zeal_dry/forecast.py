"""Explain near-term outdoor dew-point changes without overriding indoor safety."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .decision import MoistureThresholds
from .environment import EnvironmentalReading

FORECAST_HORIZON = timedelta(hours=6)
MEDIUM_RISE_C_PER_HOUR = 0.35
CRITICAL_RISE_C_PER_HOUR = 0.75


class ForecastLevel(StrEnum):
    """Summarise how urgently the outdoor moisture load is increasing."""

    SAFE = "safe"
    MEDIUM = "medium"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """Represent one timestamped outdoor forecast reading."""

    at: datetime
    reading: EnvironmentalReading


@dataclass(frozen=True, slots=True)
class DewPointOutlook:
    """Describe the most significant outdoor dew-point rise in the horizon."""

    level: ForecastLevel
    explanation: str
    maximum_dew_point_c: float | None = None
    maximum_rise_c: float | None = None
    rise_c_per_hour: float | None = None
    hours_ahead: float | None = None


def evaluate_dew_point_outlook(
    current: EnvironmentalReading | None,
    points: list[ForecastPoint],
    thresholds: MoistureThresholds,
    now: datetime,
) -> DewPointOutlook:
    """Classify a rapid forecast rise over the next six hours."""
    if current is None:
        return DewPointOutlook(
            ForecastLevel.UNAVAILABLE,
            "Current outdoor temperature and humidity are unavailable.",
        )

    candidates = [
        point
        for point in points
        if now < point.at <= now + FORECAST_HORIZON
    ]
    if not candidates:
        return DewPointOutlook(
            ForecastLevel.UNAVAILABLE,
            "No usable hourly temperature and humidity forecast is available.",
        )

    maximum = max(candidates, key=lambda point: point.reading.dew_point_c)
    hours = max((maximum.at - now).total_seconds() / 3600, 1 / 60)
    rise = maximum.reading.dew_point_c - current.dew_point_c
    rate = rise / hours

    if (
        maximum.reading.dew_point_c >= thresholds.critical_dew_point_c
        and rate >= CRITICAL_RISE_C_PER_HOUR
    ):
        level = ForecastLevel.CRITICAL
        prefix = "Outdoor dew point is forecast to rise rapidly"
    elif (
        maximum.reading.dew_point_c >= thresholds.maximum_dew_point_c
        and rate >= MEDIUM_RISE_C_PER_HOUR
    ):
        level = ForecastLevel.MEDIUM
        prefix = "Outdoor dew point is forecast to rise"
    else:
        level = ForecastLevel.SAFE
        prefix = "No rapid outdoor dew-point rise is forecast"

    return DewPointOutlook(
        level=level,
        explanation=(
            f"{prefix}: {current.dew_point_c:.1f} °C now to "
            f"{maximum.reading.dew_point_c:.1f} °C in {hours:.1f} hours "
            f"({rate:+.1f} °C/hour)."
        ),
        maximum_dew_point_c=maximum.reading.dew_point_c,
        maximum_rise_c=rise,
        rise_c_per_hour=rate,
        hours_ahead=hours,
    )
