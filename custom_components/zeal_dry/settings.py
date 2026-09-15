"""Validated, persistent zone policy shared by entities and options."""

from dataclasses import asdict, dataclass
from math import isfinite

# key: (label, minimum, maximum, step, unit)
NUMBER_SETTINGS = {
    "preferred_rh": ("Preferred RH", 40, 75, 1, "%"),
    "maximum_rh": ("Maximum RH", 45, 85, 1, "%"),
    "critical_rh": ("Critical RH", 55, 95, 1, "%"),
    "offset_c": ("Dry temperature offset", -2, 3, 0.1, "°C"),
    "safety_margin_c": ("Dew-point safety margin", 0.5, 10, 0.1, "°C"),
    "fixed_target_c": ("Fixed Dry temperature", 16, 30, 0.5, "°C"),
}
SELECT_SETTINGS = {
    "profile": ("Operating profile", ["property_protection", "occupied", "off"]),
    "strategy": ("Dry temperature strategy", ["room_offset", "fixed"]),
}
OPTION_SETTINGS = {
    "persistence_minutes": (0, 120),
    "minimum_run_minutes": (1, 120),
    "minimum_rest_minutes": (10, 120),
    "recovery_minutes": (1, 120),
    "maximum_run_minutes": (20, 360),
    "minimum_c": (10, 30),
    "maximum_c": (10, 35),
}


@dataclass(frozen=True)
class ZoneSettings:
    preferred_rh: float = 60
    maximum_rh: float = 65
    critical_rh: float = 75
    offset_c: float = 0.5
    safety_margin_c: float = 3
    fixed_target_c: float = 18
    profile: str = "property_protection"
    strategy: str = "room_offset"
    persistence_minutes: float = 15
    minimum_run_minutes: float = 20
    minimum_rest_minutes: float = 10
    recovery_minutes: float = 10
    maximum_run_minutes: float = 180
    minimum_c: float = 16
    maximum_c: float = 20

    def __post_init__(self):
        for key, (_, low, high, _, _) in NUMBER_SETTINGS.items():
            self._check(key, low, high)
        for key, (low, high) in OPTION_SETTINGS.items():
            self._check(key, low, high)
        for key, (_, choices) in SELECT_SETTINGS.items():
            if getattr(self, key) not in choices:
                raise ValueError(f"Invalid {key}")
        if not self.preferred_rh < self.maximum_rh < self.critical_rh:
            raise ValueError(
                "Preferred RH must be below maximum RH, which must be below critical RH"
            )
        if self.minimum_c > self.maximum_c:
            raise ValueError("Minimum temperature must not exceed maximum temperature")
        if self.minimum_run_minutes > self.maximum_run_minutes:
            raise ValueError("Minimum runtime must not exceed maximum runtime")

    def _check(self, key, low, high):
        value = getattr(self, key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not low <= value <= high
        ):
            raise ValueError(f"{key} must be between {low} and {high}")

    def as_dict(self):
        return asdict(self)
