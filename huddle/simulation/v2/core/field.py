"""Field geometry and coordinate system.

Single, unified coordinate system used throughout the simulation.
All measurements in yards.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .vec2 import Vec2


# =============================================================================
# Field Dimensions (yards)
# =============================================================================

FIELD_LENGTH = 100.0        # Goal line to goal line
FIELD_WIDTH = 53.333        # 53 1/3 yards
ENDZONE_DEPTH = 10.0

# Sidelines
LEFT_SIDELINE = -FIELD_WIDTH / 2    # -26.667
RIGHT_SIDELINE = FIELD_WIDTH / 2    # +26.667

# Hash marks (NFL)
HASH_WIDTH = 6.167          # 18'6" from center
LEFT_HASH = -HASH_WIDTH
RIGHT_HASH = HASH_WIDTH

# Numbers (for reference/visualization)
NUMBERS_FROM_SIDELINE = 6.0
LEFT_NUMBERS = LEFT_SIDELINE + NUMBERS_FROM_SIDELINE
RIGHT_NUMBERS = RIGHT_SIDELINE - NUMBERS_FROM_SIDELINE

# Coordinate system:
#   Origin (0, 0) = Center of field at line of scrimmage
#   +X = Right (offense's perspective)
#   +Y = Downfield (toward opponent's end zone)
#   -Y = Backfield (toward own end zone)


# =============================================================================
# Gap Definitions
# =============================================================================

class Gap(str, Enum):
    """Standard gap naming for run plays."""
    A_LEFT = "A_left"       # Between C and LG
    A_RIGHT = "A_right"     # Between C and RG
    B_LEFT = "B_left"       # Between LG and LT
    B_RIGHT = "B_right"     # Between RG and RT
    C_LEFT = "C_left"       # Outside LT
    C_RIGHT = "C_right"     # Outside RT
    D_LEFT = "D_left"       # Wide left (outside TE/WR)
    D_RIGHT = "D_right"     # Wide right


# =============================================================================
# Field Context
# =============================================================================

class HashPosition(str, Enum):
    """Ball position relative to hash marks."""
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


class FieldZone(str, Enum):
    """Vertical zones of the field."""
    OWN_ENDZONE = "own_endzone"
    OWN_REDZONE = "own_redzone"      # Own 1-20
    OWN_TERRITORY = "own_territory"  # Own 21-49
    MIDFIELD = "midfield"            # 45-55
    OPP_TERRITORY = "opp_territory"  # Opp 49-21
    OPP_REDZONE = "opp_redzone"      # Opp 20-1
    OPP_ENDZONE = "opp_endzone"


@dataclass
class Field:
    """Field state for a given play.

    The field is positioned so that:
    - Origin (0, 0) is at the center of the LOS
    - +Y is downfield (toward opponent's goal)
    - The offense attacks in the +Y direction

    Attributes:
        line_of_scrimmage: Yard line (0-100, where 0 = own goal line)
        ball_hash: Where the ball is spotted laterally
        yards_to_goal: Distance to opponent's goal line
        yards_to_first: Distance to first down marker
    """
    line_of_scrimmage: float = 25.0
    ball_hash: HashPosition = HashPosition.MIDDLE
    yards_to_goal: float = 75.0
    yards_to_first: float = 10.0

    @property
    def ball_x(self) -> float:
        """X coordinate of ball based on hash position."""
        if self.ball_hash == HashPosition.LEFT:
            return LEFT_HASH
        elif self.ball_hash == HashPosition.RIGHT:
            return RIGHT_HASH
        return 0.0

    @property
    def first_down_line(self) -> float:
        """Y coordinate of first down marker."""
        return self.yards_to_first

    @property
    def goal_line(self) -> float:
        """Y coordinate of opponent's goal line."""
        return self.yards_to_goal

    @property
    def own_goal_line(self) -> float:
        """Y coordinate of own goal line (always negative from LOS)."""
        return -self.line_of_scrimmage

    @property
    def zone(self) -> FieldZone:
        """Current field zone based on yard line."""
        if self.line_of_scrimmage <= 0:
            return FieldZone.OWN_ENDZONE
        elif self.line_of_scrimmage <= 20:
            return FieldZone.OWN_REDZONE
        elif self.line_of_scrimmage <= 45:
            return FieldZone.OWN_TERRITORY
        elif self.line_of_scrimmage <= 55:
            return FieldZone.MIDFIELD
        elif self.line_of_scrimmage <= 80:
            return FieldZone.OPP_TERRITORY
        elif self.line_of_scrimmage < 100:
            return FieldZone.OPP_REDZONE
        else:
            return FieldZone.OPP_ENDZONE

    def is_in_bounds(self, pos: Vec2) -> bool:
        """Check if position is within field boundaries."""
        return (
            LEFT_SIDELINE <= pos.x <= RIGHT_SIDELINE and
            self.own_goal_line - ENDZONE_DEPTH <= pos.y <= self.goal_line + ENDZONE_DEPTH
        )

    def is_past_los(self, pos: Vec2) -> bool:
        """Check if position is past the line of scrimmage."""
        return pos.y > 0

    def is_in_endzone(self, pos: Vec2) -> bool:
        """Check if position is in opponent's end zone."""
        return pos.y >= self.goal_line

    def is_in_own_endzone(self, pos: Vec2) -> bool:
        """Check if position is in own end zone (safety territory)."""
        return pos.y < self.own_goal_line

    def distance_to_sideline(self, pos: Vec2) -> float:
        """Distance to nearest sideline."""
        return min(pos.x - LEFT_SIDELINE, RIGHT_SIDELINE - pos.x)

    def nearest_sideline(self, pos: Vec2) -> str:
        """Which sideline is nearest."""
        if pos.x < 0:
            return "left"
        return "right"

    def clamp_to_field(self, pos: Vec2) -> Vec2:
        """Clamp position to field boundaries."""
        x = max(LEFT_SIDELINE, min(RIGHT_SIDELINE, pos.x))
        y = max(self.own_goal_line - ENDZONE_DEPTH, min(self.goal_line + ENDZONE_DEPTH, pos.y))
        return Vec2(x, y)

    def describe_position(self, pos: Vec2) -> str:
        """Human-readable description of a field position."""
        # Lateral position
        if pos.x < LEFT_HASH:
            lateral = "left of hash"
        elif pos.x > RIGHT_HASH:
            lateral = "right of hash"
        else:
            lateral = "between hashes"

        # Depth
        if pos.y < -5:
            depth = f"{abs(pos.y):.1f} yards deep in backfield"
        elif pos.y < 0:
            depth = f"{abs(pos.y):.1f} yards behind LOS"
        elif pos.y < self.yards_to_first:
            depth = f"{pos.y:.1f} yards downfield"
        elif pos.y < self.goal_line:
            to_go = self.goal_line - pos.y
            depth = f"{pos.y:.1f} yards downfield ({to_go:.1f} to goal)"
        else:
            depth = "in end zone"

        return f"{lateral}, {depth}"

    # =========================================================================
    # Boundary Awareness (Route Compression)
    # =========================================================================

    def get_boundary_compression(self, player_x: float) -> float:
        """Get compression factor for routes near the sideline.

        Routes running toward a nearby sideline need to be compressed
        to prevent receivers from running out of bounds.

        Compression values (from sandbox FieldContext):
        - >= 20 yards from sideline: 1.0 (no compression)
        - 12 yards from sideline: 0.73
        - <= 8 yards from sideline: 0.6 (max compression)

        Args:
            player_x: X coordinate of the receiver

        Returns:
            Compression factor (0.6 to 1.0)
        """
        dist = self.distance_to_sideline(Vec2(player_x, 0))
        if dist >= 20:
            return 1.0
        elif dist <= 8:
            return 0.6
        else:
            # Linear interpolation: 8yd->0.6, 20yd->1.0
            return 0.6 + (dist - 8) * (0.4 / 12)

    def get_red_zone_depth_factor(self) -> float:
        """Get depth compression factor for red zone plays.

        Routes near the goal line need depth compression to prevent
        endpoints from going into/through the end zone.

        Compression values:
        - Line of scrimmage < 80: 1.0 (normal)
        - Line of scrimmage 85: 0.81
        - Line of scrimmage 90: 0.61
        - Line of scrimmage 95: 0.42
        - Line of scrimmage >= 98: 0.3 (fade routes only)

        Returns:
            Depth factor (0.3 to 1.0)
        """
        if self.line_of_scrimmage < 80:
            return 1.0
        elif self.line_of_scrimmage >= 98:
            return 0.3
        else:
            # Linear interpolation: 80->1.0, 98->0.3
            progress = (self.line_of_scrimmage - 80) / 18
            return 1.0 - (progress * 0.7)

    def get_available_depth(self) -> float:
        """Get available vertical space before the end zone.

        Returns the yards to goal minus a 2-yard buffer to keep
        route endpoints on the playing field.

        Returns:
            Available depth in yards (minimum 0)
        """
        return max(0, self.yards_to_goal - 2)

    def get_leverage_advantage(self, receiver_x: float) -> str:
        """Determine if DB has leverage advantage from sideline.

        When a receiver is within 12 yards of the sideline, the DB
        can use the sideline as an "extra defender" by playing
        inside leverage - the sideline takes away outside routes.

        Args:
            receiver_x: X coordinate of the receiver

        Returns:
            "inside" if sideline provides leverage, "none" otherwise
        """
        dist = self.distance_to_sideline(Vec2(receiver_x, 0))
        return "inside" if dist <= 12 else "none"


# =============================================================================
# Position Landmarks
# =============================================================================

# Offensive line positions (relative to ball at x=0)
OL_SPACING = 1.2  # Center-to-center spacing between OL (yards) - realistic NFL spacing

# Pre-snap depths
QB_UNDER_CENTER_DEPTH = -1.0
QB_SHOTGUN_DEPTH = -5.0
QB_PISTOL_DEPTH = -4.0
RB_I_FORM_DEPTH = -7.0
RB_OFFSET_DEPTH = -6.0

# Receiver alignments
WR_OUTSIDE_X = 23.0     # Near sideline
WR_SLOT_X = 8.0         # Inside slot
TE_INLINE_X = 4.0       # Tight to tackle

# DB alignments
DB_PRESS_DEPTH = 0.5    # At LOS
DB_OFF_DEPTH = 5.0      # Cushion
DB_DEEP_DEPTH = 12.0    # Deep zone
