"""
Physical body model for players.

A body has actual dimensions - torso, shoulders, hips.
Players are no longer abstract points; they're physical shapes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math

from .vec2 import Vec2


class Stance(str, Enum):
    """Player stance affects body shape and capability."""
    UPRIGHT = "upright"       # Standing tall, moving freely
    ATHLETIC = "athletic"     # Slight crouch, ready position
    THREE_POINT = "three_point"  # Lineman stance, one hand down
    TWO_POINT = "two_point"   # Lineman stance, both hands up
    ENGAGED = "engaged"       # Locked with opponent


@dataclass
class BodyDimensions:
    """Physical measurements that don't change during play."""
    height: float           # Total height in yards (~2.0 for 6'0")
    shoulder_width: float   # Width across shoulders in yards (~0.5)
    arm_length: float       # Full arm extension in yards (~0.85 for 33")
    torso_depth: float      # Front-to-back thickness in yards (~0.3)
    mass: float             # Weight in pounds (affects momentum/strength)

    @classmethod
    def lineman(cls, height_inches: int = 76, weight_lbs: int = 310, arm_inches: int = 34) -> BodyDimensions:
        """Typical OL/DL body."""
        return cls(
            height=height_inches / 36,  # inches to yards
            shoulder_width=0.55,        # ~20 inches
            arm_length=arm_inches / 36,
            torso_depth=0.35,           # thick torso
            mass=weight_lbs,
        )

    @classmethod
    def skill_player(cls, height_inches: int = 72, weight_lbs: int = 200, arm_inches: int = 32) -> BodyDimensions:
        """WR, DB, RB body."""
        return cls(
            height=height_inches / 36,
            shoulder_width=0.45,
            arm_length=arm_inches / 36,
            torso_depth=0.25,
            mass=weight_lbs,
        )


@dataclass
class Body:
    """
    A player's physical body in space.

    The body has:
    - A center position (where the player "is")
    - A facing direction (where they're looking/moving)
    - Pad level (how low they're playing, affects leverage)
    - Derived shoulder/hip positions based on the above
    """
    # Core state
    center: Vec2                          # Center of mass position
    facing: float                         # Facing angle in radians (0 = right, pi/2 = up)
    pad_level: float = 0.5                # 0 = very low (good), 1 = upright (vulnerable)
    stance: Stance = Stance.ATHLETIC

    # Physical dimensions (set once)
    dimensions: BodyDimensions = field(default_factory=BodyDimensions.lineman)

    # Velocity
    velocity: Vec2 = field(default_factory=Vec2.zero)
    angular_velocity: float = 0.0         # Rotation speed (rad/s)

    # Balance/stability (0 = falling, 1 = perfectly stable)
    balance: float = 1.0

    @property
    def facing_vector(self) -> Vec2:
        """Unit vector in facing direction."""
        return Vec2.from_angle(self.facing)

    @property
    def right_vector(self) -> Vec2:
        """Unit vector to player's right (perpendicular to facing)."""
        return Vec2.from_angle(self.facing - math.pi / 2)

    @property
    def left_shoulder(self) -> Vec2:
        """World position of left shoulder."""
        offset = self.right_vector * (-self.dimensions.shoulder_width / 2)
        return self.center + offset

    @property
    def right_shoulder(self) -> Vec2:
        """World position of right shoulder."""
        offset = self.right_vector * (self.dimensions.shoulder_width / 2)
        return self.center + offset

    @property
    def chest_center(self) -> Vec2:
        """Front of chest (where hands make contact in blocking)."""
        # Slightly in front of center
        return self.center + self.facing_vector * (self.dimensions.torso_depth / 2)

    @property
    def back_center(self) -> Vec2:
        """Back of torso."""
        return self.center - self.facing_vector * (self.dimensions.torso_depth / 2)

    @property
    def leverage_factor(self) -> float:
        """
        Leverage advantage from pad level.
        Lower = better leverage = higher factor.

        Returns 0.5 (upright, poor) to 1.5 (very low, excellent).
        """
        # Invert pad_level: low pad_level (0) = good leverage
        return 1.5 - self.pad_level

    @property
    def effective_strength(self) -> float:
        """
        Strength modified by leverage and balance.
        Mass matters, but pad level is a multiplier.
        """
        base_strength = self.dimensions.mass / 200  # Normalize around 200 lbs
        return base_strength * self.leverage_factor * self.balance

    def get_bounding_box(self) -> tuple[Vec2, Vec2]:
        """
        Axis-aligned bounding box for broad-phase collision.
        Returns (min_corner, max_corner).
        """
        # Get all corner points
        half_width = self.dimensions.shoulder_width / 2
        half_depth = self.dimensions.torso_depth / 2

        corners = [
            self.center + self.facing_vector * half_depth + self.right_vector * half_width,
            self.center + self.facing_vector * half_depth - self.right_vector * half_width,
            self.center - self.facing_vector * half_depth + self.right_vector * half_width,
            self.center - self.facing_vector * half_depth - self.right_vector * half_width,
        ]

        min_x = min(c.x for c in corners)
        max_x = max(c.x for c in corners)
        min_y = min(c.y for c in corners)
        max_y = max(c.y for c in corners)

        return Vec2(min_x, min_y), Vec2(max_x, max_y)

    def point_in_torso(self, point: Vec2) -> bool:
        """Check if a point is inside the torso rectangle."""
        # Transform point to local space
        local = point - self.center

        # Project onto facing and right vectors
        forward_dist = local.dot(self.facing_vector)
        right_dist = local.dot(self.right_vector)

        half_depth = self.dimensions.torso_depth / 2
        half_width = self.dimensions.shoulder_width / 2

        return abs(forward_dist) <= half_depth and abs(right_dist) <= half_width

    def update(self, dt: float) -> None:
        """Update body state for one timestep."""
        # Apply velocity
        self.center = self.center + self.velocity * dt

        # Apply angular velocity
        self.facing += self.angular_velocity * dt

        # Normalize facing to [-pi, pi]
        while self.facing > math.pi:
            self.facing -= 2 * math.pi
        while self.facing < -math.pi:
            self.facing += 2 * math.pi

    def apply_force(self, force: Vec2, dt: float) -> None:
        """Apply a force to the body (affects velocity based on mass)."""
        # F = ma, so a = F/m
        acceleration = force / self.dimensions.mass
        self.velocity = self.velocity + acceleration * dt

    def apply_torque(self, torque: float, dt: float) -> None:
        """Apply rotational force."""
        # Simplified: heavier players rotate slower
        angular_acceleration = torque / (self.dimensions.mass * 0.1)
        self.angular_velocity += angular_acceleration * dt
