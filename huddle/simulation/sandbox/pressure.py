"""Pressure Clock for QB decision-making.

Tracks pocket pressure over time and provides penalties
that affect QB accuracy and decision thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# Constants (Tunable)
# =============================================================================

# Time pressure ramp
PRESSURE_START_TICK = 20      # When time pressure begins
PRESSURE_FULL_TICK = 50       # When time pressure maxes out

# Penalty magnitudes
ACCURACY_PENALTY_MAX = 0.3    # Up to 30% accuracy reduction at full pressure
DECISION_PENALTY_MAX = 15.0   # Up to -15 points on "hold" utility

# Base pressure thresholds
LOW_PRESSURE = 0.3            # Below this = comfortable pocket
HIGH_PRESSURE = 0.7           # Above this = significant pressure


# =============================================================================
# Pressure Clock
# =============================================================================

@dataclass
class PressureClock:
    """Tracks pocket pressure over time.

    Combines:
    - Time pressure: increases as play goes on
    - Blocking pressure: from blocking simulation (future)
    - Total pressure: combined value affecting QB decisions
    """
    base_pressure: float = 0.0      # From blocking simulation (future)
    time_pressure: float = 0.0      # Increases each tick
    total_pressure: float = 0.0     # Combined pressure level

    # Directional pressure (for accuracy bias)
    pressure_left: float = 0.0
    pressure_right: float = 0.0
    pressure_front: float = 0.0

    # External pressure state (from integrated_sim)
    external_pressure_enabled: bool = False
    eta_ticks: float = float('inf')  # Estimated ticks until sack
    panic_mode: bool = False         # Imminent sack

    # Tracking
    tick: int = 0
    pressure_history: list[float] = field(default_factory=list)

    def update(self, tick: int, blocking_result: Optional[float] = None) -> None:
        """Update pressure state for current tick.

        Args:
            tick: Current simulation tick
            blocking_result: Optional pressure from blocking (0-1)

        Note: If external_pressure_enabled is True, this method only updates
        time_pressure for reference but does NOT overwrite total_pressure,
        which is controlled by set_external_pressure().
        """
        self.tick = tick

        # Time pressure ramps up after PRESSURE_START_TICK
        if tick > PRESSURE_START_TICK:
            # Linear ramp from 0 to 1 between start and full ticks
            progress = (tick - PRESSURE_START_TICK) / (PRESSURE_FULL_TICK - PRESSURE_START_TICK)
            self.time_pressure = min(1.0, max(0.0, progress))
        else:
            self.time_pressure = 0.0

        # If external pressure is enabled, don't overwrite total_pressure
        # External pressure is set by integrated_sim from pocket_sim state
        if self.external_pressure_enabled:
            # Only track history, don't recalculate
            self.pressure_history.append(self.total_pressure)
            return

        # Blocking pressure (standalone mode without integrated_sim)
        self.base_pressure = blocking_result if blocking_result is not None else 0.0

        # Combined pressure (capped at 1.0)
        # Take max of time and blocking pressure, with slight additive bonus
        self.total_pressure = min(1.0, max(self.time_pressure, self.base_pressure) +
                                   (self.time_pressure * self.base_pressure * 0.3))

        # Track history
        self.pressure_history.append(self.total_pressure)

    def get_accuracy_penalty(self) -> float:
        """Get accuracy penalty from pressure.

        Returns:
            Penalty factor 0-1 to multiply against accuracy.
            At 0 pressure: returns 0 (no penalty)
            At 1 pressure: returns ACCURACY_PENALTY_MAX (30% reduction)
        """
        # Linear penalty based on pressure
        return self.total_pressure * ACCURACY_PENALTY_MAX

    def get_accuracy_factor(self) -> float:
        """Get accuracy multiplier from pressure.

        Returns:
            Factor 0.7-1.0 to multiply against accuracy attribute.
        """
        return 1.0 - self.get_accuracy_penalty()

    def get_decision_penalty(self) -> float:
        """Get utility score penalty for "hold" action.

        Under pressure, holding the ball becomes less attractive.

        Returns:
            Negative points to add to hold utility.
            At 0 pressure: returns 0
            At 1 pressure: returns -DECISION_PENALTY_MAX
        """
        return -self.total_pressure * DECISION_PENALTY_MAX

    def get_throw_urgency(self) -> float:
        """Get urgency factor that lowers throw thresholds.

        Under pressure, QB is willing to throw to tighter windows.

        Returns:
            Factor 0-1 indicating urgency level.
        """
        return self.total_pressure

    def is_low_pressure(self) -> bool:
        """Check if currently in low pressure situation."""
        return self.total_pressure < LOW_PRESSURE

    def is_high_pressure(self) -> bool:
        """Check if currently in high pressure situation."""
        return self.total_pressure >= HIGH_PRESSURE

    def get_pressure_level(self) -> str:
        """Get descriptive pressure level."""
        if self.total_pressure < LOW_PRESSURE:
            return "clean"
        elif self.total_pressure < HIGH_PRESSURE:
            return "moderate"
        else:
            return "heavy"

    def set_external_pressure(
        self,
        total: float,
        eta_ticks: float = float('inf'),
        left: float = 0.0,
        right: float = 0.0,
        front: float = 0.0,
        panic: bool = False,
    ) -> None:
        """Set pressure from external source (e.g., pocket_sim).

        Args:
            total: Overall pressure level 0.0-1.0
            eta_ticks: Estimated ticks until rusher reaches QB
            left: Pressure from left side 0.0-1.0
            right: Pressure from right side 0.0-1.0
            front: Pressure from front 0.0-1.0
            panic: Whether QB is in imminent danger
        """
        self.external_pressure_enabled = True
        self.total_pressure = max(0.0, min(1.0, total))
        self.base_pressure = self.total_pressure
        self.eta_ticks = eta_ticks
        self.pressure_left = max(0.0, min(1.0, left))
        self.pressure_right = max(0.0, min(1.0, right))
        self.pressure_front = max(0.0, min(1.0, front))
        self.panic_mode = panic

        # Track history
        self.pressure_history.append(self.total_pressure)

    def disable_external_pressure(self) -> None:
        """Disable external pressure and return to time-based pressure."""
        self.external_pressure_enabled = False
        self.eta_ticks = float('inf')
        self.panic_mode = False
        self.pressure_left = 0.0
        self.pressure_right = 0.0
        self.pressure_front = 0.0

    def get_pressure_direction_bias(self) -> tuple[float, float]:
        """Get directional bias for throw accuracy.

        Returns miss bias based on where pressure is coming from.
        Throws tend to miss away from pressure.

        Returns:
            (x_bias, y_bias) where positive x = right, positive y = downfield
        """
        # If pressure from left, miss right (positive x)
        # If pressure from right, miss left (negative x)
        x_bias = (self.pressure_left - self.pressure_right) * 0.5

        # If pressure from front, miss short (negative y)
        y_bias = -self.pressure_front * 0.3

        return (x_bias, y_bias)

    def reset(self) -> None:
        """Reset pressure clock to initial state."""
        self.base_pressure = 0.0
        self.time_pressure = 0.0
        self.total_pressure = 0.0
        self.pressure_left = 0.0
        self.pressure_right = 0.0
        self.pressure_front = 0.0
        self.external_pressure_enabled = False
        self.eta_ticks = float('inf')
        self.panic_mode = False
        self.tick = 0
        self.pressure_history.clear()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "base_pressure": round(self.base_pressure, 3),
            "time_pressure": round(self.time_pressure, 3),
            "total_pressure": round(self.total_pressure, 3),
            "pressure_left": round(self.pressure_left, 3),
            "pressure_right": round(self.pressure_right, 3),
            "pressure_front": round(self.pressure_front, 3),
            "eta_ticks": round(self.eta_ticks, 1) if self.eta_ticks < 100 else "inf",
            "panic_mode": self.panic_mode,
            "tick": self.tick,
            "pressure_level": self.get_pressure_level(),
            "accuracy_penalty": round(self.get_accuracy_penalty(), 3),
            "decision_penalty": round(self.get_decision_penalty(), 3),
        }


# =============================================================================
# Pressure Integration Helpers
# =============================================================================

def apply_pressure_to_accuracy(
    base_accuracy: int,
    pressure: PressureClock,
) -> int:
    """Apply pressure penalty to accuracy attribute.

    Args:
        base_accuracy: Original accuracy (0-99)
        pressure: Current pressure state

    Returns:
        Modified accuracy after pressure penalty
    """
    factor = pressure.get_accuracy_factor()
    return int(base_accuracy * factor)


def apply_pressure_to_threshold(
    base_threshold: float,
    pressure: PressureClock,
    max_reduction: float = 10.0,
) -> float:
    """Apply pressure urgency to throw threshold.

    Under pressure, QB lowers throw threshold to get ball out faster.

    Args:
        base_threshold: Original throw threshold
        pressure: Current pressure state
        max_reduction: Maximum threshold reduction

    Returns:
        Modified threshold (lower = more willing to throw)
    """
    urgency = pressure.get_throw_urgency()
    reduction = urgency * max_reduction
    return max(0, base_threshold - reduction)


def get_pressure_throw_variance_multiplier(pressure: PressureClock) -> float:
    """Get variance multiplier for throw accuracy under pressure.

    Higher pressure = more variance in throw placement.

    Args:
        pressure: Current pressure state

    Returns:
        Multiplier for throw variance (1.0 = normal, >1.0 = more variance)
    """
    # At full pressure, double the variance
    return 1.0 + pressure.total_pressure
