"""Simulation clock and time management.

Provides consistent time tracking across all systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class Clock:
    """Manages simulation time.

    The clock advances in discrete ticks. Each tick represents a fixed
    amount of real time (default 50ms = 20 ticks/second).

    Attributes:
        tick_rate: Seconds per tick
        current_time: Elapsed time in seconds
        tick_count: Number of ticks elapsed
    """
    tick_rate: float = 0.05  # 50ms per tick = 20 ticks/second
    current_time: float = 0.0
    tick_count: int = 0

    # Event tracking
    _events: dict[str, float] = field(default_factory=dict)

    def tick(self) -> float:
        """Advance time by one tick.

        Returns:
            Delta time (seconds) for this tick
        """
        self.current_time += self.tick_rate
        self.tick_count += 1
        return self.tick_rate

    def reset(self) -> None:
        """Reset clock to initial state."""
        self.current_time = 0.0
        self.tick_count = 0
        self._events.clear()

    # =========================================================================
    # Event Timing
    # =========================================================================

    def mark_event(self, name: str) -> None:
        """Mark the current time for a named event."""
        self._events[name] = self.current_time

    def time_since(self, event_name: str) -> Optional[float]:
        """Seconds since a marked event, or None if event not marked."""
        if event_name not in self._events:
            return None
        return self.current_time - self._events[event_name]

    def ticks_since(self, event_name: str) -> Optional[int]:
        """Ticks since a marked event, or None if event not marked."""
        time_elapsed = self.time_since(event_name)
        if time_elapsed is None:
            return None
        return int(time_elapsed / self.tick_rate)

    def time_at(self, event_name: str) -> Optional[float]:
        """Get the time a named event occurred."""
        return self._events.get(event_name)

    # =========================================================================
    # Utility
    # =========================================================================

    @property
    def seconds(self) -> float:
        """Current time in seconds (alias for current_time)."""
        return self.current_time

    @property
    def dt(self) -> float:
        """Delta time per tick (alias for tick_rate)."""
        return self.tick_rate

    @property
    def ticks(self) -> int:
        """Current tick count (alias for tick_count)."""
        return self.tick_count

    def ticks_to_seconds(self, ticks: int) -> float:
        """Convert ticks to seconds."""
        return ticks * self.tick_rate

    def seconds_to_ticks(self, seconds: float) -> int:
        """Convert seconds to ticks (rounded)."""
        return round(seconds / self.tick_rate)

    def format_time(self) -> str:
        """Format current time as readable string."""
        return f"{self.current_time:.2f}s (tick {self.tick_count})"

    def __repr__(self) -> str:
        return f"Clock(time={self.current_time:.3f}s, tick={self.tick_count})"
