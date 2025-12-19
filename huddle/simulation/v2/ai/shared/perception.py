"""Shared perception utilities for AI brains.

Implements cognitive science principles:
- Easterbrook Hypothesis: Pressure narrows attention/perception
- Fatigue degrades peripheral awareness
- Vision attribute affects base perception radius
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.vec2 import Vec2


@dataclass
class VisionParams:
    """Effective vision parameters after modifiers."""
    radius: float           # How far player can see (yards)
    angle: float            # Field of view (degrees)
    peripheral_quality: float  # 0-1, quality of peripheral detection


def calculate_effective_vision(
    base_vision: int,
    pressure_level: float = 0.0,  # 0.0 = clean, 1.0 = critical
    fatigue: float = 0.0,         # 0.0 = fresh, 1.0 = exhausted
) -> VisionParams:
    """Calculate effective vision parameters under pressure.

    Implements the Easterbrook Hypothesis: under high arousal/stress,
    peripheral perception degrades. Athletes under pressure literally
    see less of the field.

    Args:
        base_vision: Player's vision attribute (0-100)
        pressure_level: Current pressure (0.0 = clean, 1.0 = critical)
        fatigue: Current fatigue level (0.0 = fresh, 1.0 = exhausted)

    Returns:
        VisionParams with effective radius, angle, and peripheral quality
    """
    # Base vision radius scales with vision attribute
    # QB needs to see receivers 30-40 yards downfield
    # Vision 60 = 30 yards, Vision 80 = 35 yards, Vision 100 = 40 yards
    base_radius = 20.0 + (base_vision / 5.0)

    # Pressure narrows perception (up to 25% reduction at critical)
    pressure_modifier = 1.0 - (pressure_level * 0.25)

    # Fatigue further degrades (smaller effect, up to 10% reduction)
    fatigue_modifier = 1.0 - (fatigue * 0.10)

    effective_radius = base_radius * pressure_modifier * fatigue_modifier

    # Vision angle (peripheral narrowing under pressure)
    # Base is 120 degrees, can narrow to 84 degrees under critical pressure
    base_angle = 120.0
    effective_angle = base_angle * (1.0 - pressure_level * 0.30)

    # Peripheral quality degrades faster than central vision
    # At critical pressure, peripheral detection drops to 60% quality
    peripheral_quality = 1.0 - (pressure_level * 0.40)
    peripheral_quality = max(0.2, peripheral_quality)  # Never below 20%

    return VisionParams(
        radius=effective_radius,
        angle=effective_angle,
        peripheral_quality=peripheral_quality,
    )


def angle_between(facing: 'Vec2', to_target: 'Vec2') -> float:
    """Calculate angle in degrees between facing direction and target direction.

    Args:
        facing: Unit vector of direction player is facing
        to_target: Unit vector toward target

    Returns:
        Angle in degrees (0-180)
    """
    if facing.length() < 0.001 or to_target.length() < 0.001:
        return 0.0

    # Normalize vectors
    f = facing.normalized()
    t = to_target.normalized()

    # Dot product gives cos(angle)
    dot = f.x * t.x + f.y * t.y

    # Clamp to avoid floating point errors with acos
    dot = max(-1.0, min(1.0, dot))

    # Convert to degrees
    return math.degrees(math.acos(dot))


def is_in_vision(
    my_pos: 'Vec2',
    my_facing: 'Vec2',
    target_pos: 'Vec2',
    vision_params: VisionParams,
) -> tuple[bool, bool, float]:
    """Check if target is within player's effective vision.

    Args:
        my_pos: Player's position
        my_facing: Direction player is facing (unit vector)
        target_pos: Position of target to check
        vision_params: Current effective vision parameters

    Returns:
        Tuple of (is_visible, is_peripheral, detection_quality)
        - is_visible: True if target is within vision cone
        - is_peripheral: True if target is in peripheral vision (>45 degrees)
        - detection_quality: 0-1 quality of detection (lower for peripheral)
    """
    to_target = target_pos - my_pos
    distance = to_target.length()

    # Outside vision radius
    if distance > vision_params.radius:
        return False, False, 0.0

    # Calculate angle to target
    if distance < 0.1:
        # Target is on top of us
        return True, False, 1.0

    angle = angle_between(my_facing, to_target.normalized())

    # Outside vision angle
    if angle > vision_params.angle / 2:
        return False, False, 0.0

    # Determine if peripheral (outside 45 degree central cone)
    is_peripheral = angle > 45.0

    # Detection quality
    if is_peripheral:
        detection_quality = vision_params.peripheral_quality
    else:
        detection_quality = 1.0

    return True, is_peripheral, detection_quality
