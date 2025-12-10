"""Field position modeling for simulations.

This module provides field context information that affects play execution,
including hash mark position, boundary constraints, and red zone awareness.

Field position affects:
- Receiver splits and route adjustments (compressed toward boundary)
- Coverage leverage (DBs can use sideline as extra defender)
- Throw windows and risk (less margin for error near sideline)
- Route depth (compressed in red zone / goal line)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vec2 import Vec2

from .coordinate import (
    FIELD_WIDTH,
    HALF_FIELD_WIDTH,
    SIDELINE_LEFT,
    SIDELINE_RIGHT,
    LEFT_HASH,
    RIGHT_HASH,
)


# =============================================================================
# Hash Position Enum
# =============================================================================

class HashPosition(str, Enum):
    """Which hash mark the ball is on."""
    LEFT = "left"       # Ball on left hash
    MIDDLE = "middle"   # Ball in middle of field
    RIGHT = "right"     # Ball on right hash


# =============================================================================
# Field Zone Enum
# =============================================================================

class FieldZone(str, Enum):
    """Zone of the field based on yard line."""
    BACKED_UP = "backed_up"       # Inside own 10
    OWN_TERRITORY = "own"         # Own 10 to own 45
    MIDFIELD = "midfield"         # Own 45 to opponent 45
    PLUS_TERRITORY = "plus"       # Opponent 45 to opponent 20
    RED_ZONE = "red_zone"         # Opponent 20 to opponent 5
    GOAL_LINE = "goal_line"       # Inside opponent 5


# =============================================================================
# Field Context
# =============================================================================

@dataclass
class FieldContext:
    """Complete field position context for a play.

    This provides all the field position information needed to adjust
    routes, coverage, and throw decisions.

    Attributes:
        ball_x: Lateral position of ball (-26.67 to 26.67)
        yard_line: Field position (0=own goal, 50=midfield, 100=opponent goal)
        hash_position: Which hash mark the ball is on
        field_zone: Zone classification
    """
    ball_x: float = 0.0
    yard_line: int = 25

    # Derived properties (set in __post_init__)
    hash_position: HashPosition = HashPosition.MIDDLE
    field_zone: FieldZone = FieldZone.OWN_TERRITORY

    def __post_init__(self):
        """Compute derived properties."""
        # Determine hash position
        if self.ball_x <= LEFT_HASH - 1.0:
            self.hash_position = HashPosition.LEFT
        elif self.ball_x >= RIGHT_HASH + 1.0:
            self.hash_position = HashPosition.RIGHT
        else:
            self.hash_position = HashPosition.MIDDLE

        # Determine field zone
        if self.yard_line <= 10:
            self.field_zone = FieldZone.BACKED_UP
        elif self.yard_line <= 45:
            self.field_zone = FieldZone.OWN_TERRITORY
        elif self.yard_line <= 55:
            self.field_zone = FieldZone.MIDFIELD
        elif self.yard_line <= 80:
            self.field_zone = FieldZone.PLUS_TERRITORY
        elif self.yard_line <= 95:
            self.field_zone = FieldZone.RED_ZONE
        else:
            self.field_zone = FieldZone.GOAL_LINE

    # =========================================================================
    # Distance Properties
    # =========================================================================

    @property
    def distance_to_left_sideline(self) -> float:
        """Distance from ball to left sideline in yards."""
        return self.ball_x - SIDELINE_LEFT

    @property
    def distance_to_right_sideline(self) -> float:
        """Distance from ball to right sideline in yards."""
        return SIDELINE_RIGHT - self.ball_x

    @property
    def distance_to_boundary(self) -> float:
        """Distance to nearest sideline (boundary)."""
        return min(self.distance_to_left_sideline, self.distance_to_right_sideline)

    @property
    def distance_to_field_side(self) -> float:
        """Distance to far sideline (field side)."""
        return max(self.distance_to_left_sideline, self.distance_to_right_sideline)

    @property
    def boundary_side(self) -> str:
        """Which sideline is the boundary (closer): 'left' or 'right'."""
        if self.distance_to_left_sideline <= self.distance_to_right_sideline:
            return "left"
        return "right"

    @property
    def field_side(self) -> str:
        """Which sideline is the field side (farther): 'left' or 'right'."""
        if self.distance_to_left_sideline > self.distance_to_right_sideline:
            return "left"
        return "right"

    @property
    def yards_to_goal(self) -> int:
        """Yards remaining to opponent's goal line."""
        return 100 - self.yard_line

    @property
    def yards_to_first_down(self) -> int:
        """Typical first down distance (not tracking actual down/distance)."""
        return 10

    # =========================================================================
    # Zone Properties
    # =========================================================================

    @property
    def is_red_zone(self) -> bool:
        """Is the ball inside opponent's 20 yard line?"""
        return self.yard_line >= 80

    @property
    def is_goal_line(self) -> bool:
        """Is the ball inside opponent's 5 yard line?"""
        return self.yard_line >= 95

    @property
    def is_backed_up(self) -> bool:
        """Is the ball inside own 10 yard line?"""
        return self.yard_line <= 10

    @property
    def is_plus_territory(self) -> bool:
        """Is the ball in opponent's territory?"""
        return self.yard_line > 50

    # =========================================================================
    # Route Adjustment Factors
    # =========================================================================

    def get_boundary_compression(self) -> float:
        """Get compression factor for routes toward boundary side.

        Returns a factor (0.5 to 1.0) to multiply lateral route distances.
        Closer to boundary = more compression.

        Returns:
            Compression factor (1.0 = no compression)
        """
        dist = self.distance_to_boundary
        if dist >= 20:
            return 1.0
        elif dist <= 8:
            return 0.6
        else:
            # Linear interpolation from 0.6 to 1.0
            return 0.6 + (dist - 8) * (0.4 / 12)

    def get_red_zone_depth_factor(self) -> float:
        """Get depth compression factor for red zone routes.

        Routes get shallower as you approach the goal line.

        Returns:
            Depth factor (1.0 = normal depth, <1.0 = compressed)
        """
        if self.yard_line < 80:
            return 1.0
        elif self.yard_line >= 98:
            return 0.3  # Minimal depth for fade routes only
        else:
            # Linear interpolation
            progress = (self.yard_line - 80) / 18
            return 1.0 - (progress * 0.7)

    def should_compress_route(self, receiver_side: str) -> bool:
        """Determine if a receiver's routes should be compressed.

        Args:
            receiver_side: 'left' or 'right' indicating receiver alignment

        Returns:
            True if routes should be compressed toward field center
        """
        # Compress if receiver is on boundary side
        return receiver_side == self.boundary_side

    def get_leverage_advantage(self, receiver_side: str) -> str:
        """Get leverage advantage for a DB covering receiver on given side.

        Args:
            receiver_side: 'left' or 'right' indicating receiver alignment

        Returns:
            'inside', 'outside', or 'none' indicating where DB has advantage
        """
        if receiver_side == self.boundary_side:
            # DB can use sideline, play inside leverage
            return "inside"
        else:
            return "none"

    # =========================================================================
    # Throw Risk Assessment
    # =========================================================================

    def get_throw_risk_to_position(self, target_x: float) -> float:
        """Calculate risk factor for throw to a lateral position.

        Throws near the sideline have less margin for error.

        Args:
            target_x: Target lateral position

        Returns:
            Risk factor 0.0 (safe) to 1.0 (risky)
        """
        # Distance from target to nearest sideline
        dist_left = target_x - SIDELINE_LEFT
        dist_right = SIDELINE_RIGHT - target_x
        dist_to_sideline = min(dist_left, dist_right)

        if dist_to_sideline >= 10:
            return 0.0
        elif dist_to_sideline <= 2:
            return 1.0
        else:
            return 1.0 - (dist_to_sideline - 2) / 8

    def get_vertical_space(self) -> float:
        """Get available vertical space for routes.

        Returns:
            Available depth in yards before end zone
        """
        return float(self.yards_to_goal)

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ball_x": round(self.ball_x, 1),
            "yard_line": self.yard_line,
            "hash_position": self.hash_position.value,
            "field_zone": self.field_zone.value,
            "distance_to_left_sideline": round(self.distance_to_left_sideline, 1),
            "distance_to_right_sideline": round(self.distance_to_right_sideline, 1),
            "boundary_side": self.boundary_side,
            "field_side": self.field_side,
            "is_red_zone": self.is_red_zone,
            "is_backed_up": self.is_backed_up,
            "yards_to_goal": self.yards_to_goal,
        }

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def from_yard_line(
        cls,
        yard_line: int,
        hash_position: HashPosition = HashPosition.MIDDLE,
    ) -> FieldContext:
        """Create field context from yard line and hash position.

        Args:
            yard_line: Field position (0-100)
            hash_position: Which hash the ball is on

        Returns:
            FieldContext with appropriate ball_x
        """
        if hash_position == HashPosition.LEFT:
            ball_x = LEFT_HASH
        elif hash_position == HashPosition.RIGHT:
            ball_x = RIGHT_HASH
        else:
            ball_x = 0.0

        return cls(ball_x=ball_x, yard_line=yard_line)

    @classmethod
    def midfield_center(cls) -> FieldContext:
        """Create context for ball at midfield, center of field."""
        return cls(ball_x=0.0, yard_line=50)

    @classmethod
    def own_25_center(cls) -> FieldContext:
        """Create context for ball at own 25, center of field."""
        return cls(ball_x=0.0, yard_line=25)

    @classmethod
    def red_zone_left_hash(cls) -> FieldContext:
        """Create context for red zone, left hash."""
        return cls(ball_x=LEFT_HASH, yard_line=85)

    @classmethod
    def goal_line_right_hash(cls) -> FieldContext:
        """Create context for goal line, right hash."""
        return cls(ball_x=RIGHT_HASH, yard_line=97)

    @classmethod
    def backed_up_center(cls) -> FieldContext:
        """Create context for backed up inside own 10."""
        return cls(ball_x=0.0, yard_line=5)


# =============================================================================
# Helper Functions
# =============================================================================

def adjust_receiver_alignment(
    base_x: float,
    field_context: FieldContext,
    receiver_side: str,
) -> float:
    """Adjust receiver's lateral alignment based on field position.

    Args:
        base_x: Original alignment X position
        field_context: Current field context
        receiver_side: 'left' or 'right'

    Returns:
        Adjusted X position
    """
    if not field_context.should_compress_route(receiver_side):
        return base_x

    compression = field_context.get_boundary_compression()

    # Only compress the component toward the boundary
    if receiver_side == "left":
        # Left receiver, left boundary - compress leftward distance
        if base_x < 0:
            return base_x * compression
    else:
        # Right receiver, right boundary - compress rightward distance
        if base_x > 0:
            return base_x * compression

    return base_x


def adjust_route_depth(
    base_depth: float,
    field_context: FieldContext,
) -> float:
    """Adjust route depth based on field position.

    Args:
        base_depth: Original route depth
        field_context: Current field context

    Returns:
        Adjusted depth, capped by available space
    """
    # Apply red zone compression
    factor = field_context.get_red_zone_depth_factor()
    adjusted = base_depth * factor

    # Cap by available vertical space (leave 2 yards for receiver to stop)
    max_depth = field_context.get_vertical_space() - 2
    return min(adjusted, max_depth)
