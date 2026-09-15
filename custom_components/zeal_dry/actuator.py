"""Supplier-neutral actuator support for ZEAL-Dry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.util import dt as dt_util


@dataclass(slots=True)
class DummyActuator:
    """In-memory ACU actuator used only by ZEAL-Dry test mode."""

    is_on: bool = False
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    _listeners: set[Callable[[], None]] = field(default_factory=set, repr=False)

    @property
    def available(self) -> bool:
        """The built-in dummy actuator is always available."""
        return True

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener and return its unsubscribe callback."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            """Unsubscribe the callback from dummy-actuator changes."""
            self._listeners.discard(listener)

        return remove_listener

    async def async_turn_on(self) -> None:
        """Turn the dummy ACU on."""
        if self.is_on:
            return
        self.is_on = True
        self.started_at = dt_util.utcnow()
        self._notify()

    async def async_turn_off(self) -> None:
        """Turn the dummy ACU off."""
        if not self.is_on:
            return
        self.is_on = False
        self.stopped_at = dt_util.utcnow()
        self._notify()

    def runtime_minutes(self) -> float:
        """Return the current ON-cycle runtime in minutes."""
        if not self.is_on or self.started_at is None:
            return 0.0
        return max(0.0, (dt_util.utcnow() - self.started_at).total_seconds() / 60.0)

    def _notify(self) -> None:
        """Notify entities that the dummy state changed."""
        for listener in tuple(self._listeners):
            listener()
