"""Coordinate system conventions and conversion utilities.

This module defines the unified coordinate system used across all simulations
and provides utilities for coordinate conversion between different conventions.

Unified Coordinate System:
    Origin (0, 0) = Line of scrimmage, center of field

    X-axis (lateral):
        Negative = Left (from offense's perspective, looking downfield)
        Positive = Right
        Range: approximately -26.67 to +26.67 yards (sideline to sideline)

    Y-axis (depth):
        Positive = Downfield (toward defense's end zone)
        Negative = Backfield (toward offense's end zone)
        LOS is at y=0

Note on pocket_sim.py:
    The pocket simulation historically uses the opposite y-convention:
    - y-positive = toward backfield (QB at y=7)
    - y-negative = toward LOS/downfield

    Use the conversion functions when integrating pocket_sim with other modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vec2 import Vec2


# =============================================================================
# Field Dimension Constants
# =============================================================================

# Field width
FIELD_WIDTH = 53.33  # yards (160 feet / 3)
HALF_FIELD_WIDTH = FIELD_WIDTH / 2  # ~26.67 yards

# Sidelines
SIDELINE_LEFT = -HALF_FIELD_WIDTH   # -26.67
SIDELINE_RIGHT = HALF_FIELD_WIDTH   # +26.67

# Hash marks (NFL)
# Hash marks are 70 feet 9 inches from sideline = 23.58 yards from sideline
# Which means ~3.08 yards from center
# Actually NFL hashes are 18.5 feet apart, so 9.25 feet = ~3.08 yards from center
NFL_HASH_DISTANCE = 18.5 / 2 / 3  # ~3.08 yards from center
LEFT_HASH = -NFL_HASH_DISTANCE
RIGHT_HASH = NFL_HASH_DISTANCE

# College hashes are wider: 40 feet apart = 20 feet from center = 6.67 yards
COLLEGE_HASH_DISTANCE = 40 / 2 / 3  # ~6.67 yards from center

# Numbers on field (typically at 12 yards from sideline)
NUMBERS_DISTANCE_FROM_SIDELINE = 12.0
LEFT_NUMBERS = SIDELINE_LEFT + NUMBERS_DISTANCE_FROM_SIDELINE  # ~-14.67
RIGHT_NUMBERS = SIDELINE_RIGHT - NUMBERS_DISTANCE_FROM_SIDELINE  # ~+14.67


# =============================================================================
# Player Position Constants (in unified coordinates)
# =============================================================================

# Quarterback depths (negative y = backfield)
QB_SHOTGUN_DEPTH = -7.0        # 7 yards behind LOS
QB_PISTOL_DEPTH = -4.0         # 4 yards behind LOS
QB_UNDER_CENTER_DEPTH = -1.0   # Just behind center

# Offensive line (just behind LOS)
OL_DEPTH = -0.5  # Half yard behind LOS

# Offensive line lateral spacing (from center)
OL_SPACING = 1.5  # Gap between linemen
LT_X = -3.0      # Left tackle
LG_X = -1.5      # Left guard
C_X = 0.0        # Center
RG_X = 1.5       # Right guard
RT_X = 3.0       # Right tackle

# Defensive line (at or just past LOS)
DL_DEPTH = 0.0   # At LOS
DL_DEPTH_TILTED = 0.25  # Slightly upfield

# Defensive back depths
DB_PRESS_DEPTH = 1.0    # Press coverage
DB_OFF_DEPTH = 5.0      # Off coverage (5 yards)
DB_DEEP_DEPTH = 10.0    # Deep zone safety

# Receiver alignments
WR_OUTSIDE_X = 22.0     # Near sideline
WR_SLOT_X = 8.0         # Slot position
TE_X = 4.5              # Tight end (just outside tackle)


# =============================================================================
# Coordinate Conversion
# =============================================================================

def convert_pocket_to_unified(x: float, y: float) -> tuple[float, float]:
    """Convert pocket_sim coordinates to unified coordinates.

    In pocket_sim: y-positive = toward backfield
    In unified:    y-positive = downfield

    Args:
        x: Lateral position (same in both systems)
        y: Depth in pocket_sim convention (positive = backfield)

    Returns:
        Tuple of (x, y) in unified coordinates
    """
    return (x, -y)


def convert_unified_to_pocket(x: float, y: float) -> tuple[float, float]:
    """Convert unified coordinates to pocket_sim coordinates.

    Args:
        x: Lateral position (same in both systems)
        y: Depth in unified convention (positive = downfield)

    Returns:
        Tuple of (x, y) in pocket_sim coordinates
    """
    return (x, -y)


def convert_pocket_vec2_to_unified(vec: "Vec2") -> "Vec2":
    """Convert a Vec2 from pocket_sim convention to unified.

    Args:
        vec: Vector in pocket_sim coordinates

    Returns:
        New Vec2 in unified coordinates
    """
    from .vec2 import Vec2
    return Vec2(vec.x, -vec.y)


def convert_unified_vec2_to_pocket(vec: "Vec2") -> "Vec2":
    """Convert a Vec2 from unified convention to pocket_sim.

    Args:
        vec: Vector in unified coordinates

    Returns:
        New Vec2 in pocket_sim coordinates
    """
    from .vec2 import Vec2
    return Vec2(vec.x, -vec.y)


# =============================================================================
# Boundary Utilities
# =============================================================================

class FieldSide(str, Enum):
    """Which side of the field (based on hash mark)."""
    LEFT = "left"       # Ball on left hash, more space to right
    MIDDLE = "middle"   # Ball in middle
    RIGHT = "right"     # Ball on right hash, more space to left


def get_field_side(ball_x: float, threshold: float = 2.0) -> FieldSide:
    """Determine which side of the field the ball is on.

    Args:
        ball_x: Ball's lateral position
        threshold: Distance from center to be considered "middle"

    Returns:
        FieldSide enum value
    """
    if ball_x < -threshold:
        return FieldSide.LEFT
    elif ball_x > threshold:
        return FieldSide.RIGHT
    else:
        return FieldSide.MIDDLE


def get_boundary_side(ball_x: float) -> str:
    """Get which sideline is the 'boundary' (closer).

    The boundary is the closer sideline. The 'field' side is the
    side with more room.

    Args:
        ball_x: Ball's lateral position

    Returns:
        "left" or "right" indicating the boundary (closer) sideline
    """
    if ball_x <= 0:
        return "left"
    else:
        return "right"


def get_distance_to_sideline(x: float, sideline: str) -> float:
    """Get distance from position to specified sideline.

    Args:
        x: Lateral position
        sideline: "left" or "right"

    Returns:
        Distance in yards to the sideline
    """
    if sideline == "left":
        return x - SIDELINE_LEFT
    else:
        return SIDELINE_RIGHT - x


def is_in_bounds(x: float, y: float = 0.0, margin: float = 0.0) -> bool:
    """Check if position is within field boundaries.

    Args:
        x: Lateral position
        y: Depth (not typically checked for bounds)
        margin: Additional margin from sideline (default 0)

    Returns:
        True if position is in bounds
    """
    return (SIDELINE_LEFT + margin) <= x <= (SIDELINE_RIGHT - margin)


def clamp_to_field(x: float, margin: float = 0.0) -> float:
    """Clamp lateral position to stay within field boundaries.

    Args:
        x: Lateral position
        margin: Distance from sideline to consider as boundary

    Returns:
        Clamped x position
    """
    min_x = SIDELINE_LEFT + margin
    max_x = SIDELINE_RIGHT - margin
    return max(min_x, min(max_x, x))


# =============================================================================
# Zone Boundaries (for coverage zones)
# =============================================================================

@dataclass
class ZoneBoundary:
    """Defines a rectangular zone on the field."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def contains(self, x: float, y: float) -> bool:
        """Check if point is within this zone."""
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max)

    @property
    def center_x(self) -> float:
        """Get center x of zone."""
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        """Get center y of zone."""
        return (self.y_min + self.y_max) / 2


# Common zone definitions (in unified coordinates: y+ = downfield)
FLAT_LEFT = ZoneBoundary(
    x_min=SIDELINE_LEFT, x_max=-5.0,
    y_min=0.0, y_max=10.0
)

FLAT_RIGHT = ZoneBoundary(
    x_min=5.0, x_max=SIDELINE_RIGHT,
    y_min=0.0, y_max=10.0
)

HOOK_LEFT = ZoneBoundary(
    x_min=-12.0, x_max=-2.0,
    y_min=8.0, y_max=18.0
)

HOOK_RIGHT = ZoneBoundary(
    x_min=2.0, x_max=12.0,
    y_min=8.0, y_max=18.0
)

DEEP_THIRD_LEFT = ZoneBoundary(
    x_min=SIDELINE_LEFT, x_max=-8.0,
    y_min=15.0, y_max=50.0
)

DEEP_THIRD_MIDDLE = ZoneBoundary(
    x_min=-8.0, x_max=8.0,
    y_min=15.0, y_max=50.0
)

DEEP_THIRD_RIGHT = ZoneBoundary(
    x_min=8.0, x_max=SIDELINE_RIGHT,
    y_min=15.0, y_max=50.0
)

DEEP_HALF_LEFT = ZoneBoundary(
    x_min=SIDELINE_LEFT, x_max=0.0,
    y_min=15.0, y_max=50.0
)

DEEP_HALF_RIGHT = ZoneBoundary(
    x_min=0.0, x_max=SIDELINE_RIGHT,
    y_min=15.0, y_max=50.0
)
