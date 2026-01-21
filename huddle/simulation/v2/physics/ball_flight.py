"""Ball flight physics based on Dzielski & Blackburn (2022).

"Modeling the Dynamics of an American Football and the Stability Due to Spin"

Key physics implemented:
- Drag coefficient (CD ≈ 0.14) reduces deep pass distance
- Spin stability threshold (ω_crit = 7.39 × V) determines spiral quality
- Lateral drift from yaw of repose (right-handed QB → ball drifts right)
- Throw type affects spin rate and drag exposure
"""

import random
from typing import Tuple

# =============================================================================
# CONSTANTS FROM PAPER
# =============================================================================

# Drag coefficient for a football (dimensionless)
DRAG_COEFFICIENT = 0.14

# Spin stability constant: critical spin (rpm) = STABILITY_CONSTANT * velocity (mph)
# Below this threshold, the pass becomes unstable (wobbles)
STABILITY_CONSTANT = 7.39


# =============================================================================
# SPIN RATES BY THROW TYPE (RPM)
# =============================================================================
# Based on research data - tighter spirals for bullet passes
SPIN_RATES: dict[str, Tuple[float, float]] = {
    "BULLET": (550.0, 650.0),  # Tight spiral, fast delivery
    "TOUCH": (450.0, 550.0),   # Medium arc, good spin
    "LOB": (350.0, 450.0),     # High arc, slower spin
}


def calculate_critical_spin(velocity_yps: float) -> float:
    """Calculate minimum spin rate for stable spiral.

    From paper: ω_crit = 7.39 × V where V is velocity in mph.

    Args:
        velocity_yps: Ball velocity in yards per second

    Returns:
        Critical spin rate in RPM
    """
    # Convert yards/second to mph (1 yard/s ≈ 2.045 mph)
    velocity_mph = velocity_yps * 2.045
    return STABILITY_CONSTANT * velocity_mph


def calculate_spin_rate(throw_type: str, throw_power: int) -> float:
    """Calculate spin rate based on throw type and QB arm strength.

    Higher throw_power produces tighter spirals with less variance.

    Args:
        throw_type: "BULLET", "TOUCH", or "LOB"
        throw_power: QB throw_power attribute (50-99 scale)

    Returns:
        Spin rate in RPM
    """
    spin_min, spin_max = SPIN_RATES.get(throw_type.upper(), (450.0, 550.0))

    # Power factor: 0 at throw_power=50, 1 at throw_power=99
    power_factor = max(0.0, min(1.0, (throw_power - 50) / 49))

    # Base spin scales with arm strength
    base_spin = spin_min + power_factor * (spin_max - spin_min)

    # Variance is higher for weaker arms (less consistent mechanics)
    variance = 30 * (1 - power_factor)

    return base_spin + random.gauss(0, variance)


def calculate_drag_factor(distance: float, throw_type: str) -> float:
    """Calculate velocity reduction due to aerodynamic drag.

    Paper shows ~10 yard loss on 70-yard throws (~15% velocity reduction).
    Drag effect is minimal on short throws, increases with distance.

    Args:
        distance: Throw distance in yards
        throw_type: "BULLET", "TOUCH", or "LOB"

    Returns:
        Velocity multiplier (0.85-1.0, where 1.0 = no drag effect)
    """
    if distance < 15:
        # Minimal drag on short throws
        return 1.0

    # Progressive drag: starts at 15 yards, maxes out around 50+ yards
    drag_range = min((distance - 15) / 35, 1.0)  # 0-1 over 15-50 yards

    # LOB has more drag exposure (slower velocity = longer flight time = more air resistance)
    type_factors = {
        "BULLET": 0.10,  # Fast and flat, least drag exposure
        "TOUCH": 0.12,   # Medium arc, moderate drag
        "LOB": 0.15,     # High arc, most drag exposure
    }
    type_factor = type_factors.get(throw_type.upper(), 0.12)

    return 1.0 - (drag_range * type_factor)


def calculate_lateral_drift(distance: float, handedness: str) -> float:
    """Calculate lateral drift from lift force (yaw of repose effect).

    A spinning football generates lift perpendicular to its velocity vector.
    This causes the ball to drift laterally during flight.
    - Right-handed QB → clockwise spin → ball drifts right
    - Left-handed QB → counter-clockwise spin → ball drifts left

    Paper shows ~2-3 yards drift on deep throws.

    Args:
        distance: Throw distance in yards
        handedness: "right" or "left"

    Returns:
        Lateral drift in yards (positive = right, negative = left)
    """
    if distance < 20:
        # Drift is negligible on short/intermediate throws
        return 0.0

    # Progressive drift: ~0.08 yards per yard over 20
    drift = (distance - 20) * 0.08
    drift = min(drift, 3.0)  # Cap at ~3 yards max drift

    # Direction depends on handedness
    return drift if handedness == "right" else -drift


def is_spiral_stable(spin_rate: float, velocity_yps: float) -> bool:
    """Check if pass has enough spin for stable spiral.

    Below the critical spin threshold, the ball wobbles.
    This affects accuracy and makes the pass easier to defend.

    Args:
        spin_rate: Ball spin rate in RPM
        velocity_yps: Ball velocity in yards per second

    Returns:
        True if spiral is stable, False if wobbling
    """
    critical = calculate_critical_spin(velocity_yps)
    return spin_rate > critical


def get_initial_orientation(throw_direction_x: float, throw_direction_y: float) -> Tuple[float, float, float]:
    """Get initial ball orientation (spin axis direction).

    Ball starts with nose pointed slightly upward along throw trajectory.

    Args:
        throw_direction_x: Normalized X component of throw direction
        throw_direction_y: Normalized Y component of throw direction

    Returns:
        (orientation_x, orientation_y, orientation_z) - ball axis unit vector
    """
    # Initial upward tilt of ~17 degrees (0.3 radians worth of Z component)
    initial_z_tilt = 0.3
    return (throw_direction_x, throw_direction_y, initial_z_tilt)


def orientation_at_progress(
    base_orientation_x: float,
    base_orientation_y: float,
    progress: float,
) -> Tuple[float, float, float]:
    """Get ball orientation at flight progress.

    Ball axis rotates to follow trajectory:
    - Nose-up at start (release)
    - Level at apex
    - Nose-down at end (catch)

    Args:
        base_orientation_x: Initial X orientation component
        base_orientation_y: Initial Y orientation component
        progress: Flight progress (0.0 = release, 1.0 = arrival)

    Returns:
        (x, y, z) orientation at current progress
    """
    # Z tilt interpolates: +0.3 at start → -0.3 at end
    z_tilt = 0.3 * (1 - 2 * progress)
    return (base_orientation_x, base_orientation_y, z_tilt)
