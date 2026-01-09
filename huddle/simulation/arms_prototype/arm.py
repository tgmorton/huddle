"""
Arm model for physical interactions.

Arms are the key to blocking, tackling, and physical play.
Each arm has position, extension, and can engage with opponents.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math

from .vec2 import Vec2


class ArmSide(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class HandState(str, Enum):
    """What the hand is doing."""
    FREE = "free"                 # Not engaged, can reach
    REACHING = "reaching"         # Extending toward target
    PLACED = "placed"             # Hand on opponent (neutral)
    CONTROLLING = "controlling"   # Has inside position, driving
    CONTROLLED = "controlled"     # Opponent has control of this arm
    LOCKED = "locked"             # Mutual grip, neither winning


@dataclass
class Arm:
    """
    A single arm with physical presence.

    The arm extends from the shoulder (provided by body) at an angle
    with variable extension. The hand position is calculated from these.
    """
    side: ArmSide

    # Arm configuration (relative to body facing)
    angle: float = 0.0            # Angle relative to body facing (radians)
                                  # 0 = straight ahead, +pi/2 = out to side
    extension: float = 0.5        # 0 = fully retracted, 1 = fully extended

    # Arm length (set from body dimensions)
    max_length: float = 0.85      # Full reach in yards

    # Current state
    hand_state: HandState = HandState.FREE

    # If engaged, reference to what we're engaged with
    engaged_with: Optional[str] = None  # Player ID of opponent
    engaged_arm: Optional[ArmSide] = None  # Which of their arms

    # Physical properties
    power: float = 1.0            # Arm strength (modified by extension)

    # Movement rates
    extension_rate: float = 0.0   # How fast extending/retracting
    angle_rate: float = 0.0       # How fast rotating

    @property
    def current_length(self) -> float:
        """Actual reach based on extension."""
        # Minimum reach even when retracted (elbow out)
        min_reach = self.max_length * 0.3
        return min_reach + (self.max_length - min_reach) * self.extension

    @property
    def effective_power(self) -> float:
        """
        Power adjusted for extension.

        Arms are strongest when slightly bent (extension ~0.4-0.6).
        Fully extended or retracted = weaker.
        """
        # Bell curve centered at 0.5 extension
        extension_factor = 1.0 - 2.0 * abs(self.extension - 0.5)
        extension_factor = max(0.3, extension_factor)  # Floor at 30%
        return self.power * extension_factor

    def get_hand_position(self, shoulder_pos: Vec2, body_facing: float) -> Vec2:
        """
        Calculate world position of the hand.

        Args:
            shoulder_pos: World position of the shoulder (from Body)
            body_facing: Body's facing angle (radians)

        Returns:
            World position of the hand
        """
        # Arm angle in world space = body facing + arm angle
        world_angle = body_facing + self.angle

        # Hand is at shoulder + direction * current_length
        direction = Vec2.from_angle(world_angle)
        return shoulder_pos + direction * self.current_length

    def get_elbow_position(self, shoulder_pos: Vec2, body_facing: float) -> Vec2:
        """Elbow is roughly halfway along the arm."""
        world_angle = body_facing + self.angle
        direction = Vec2.from_angle(world_angle)
        elbow_length = self.current_length * 0.5
        return shoulder_pos + direction * elbow_length

    def reach_toward(self, target: Vec2, shoulder_pos: Vec2, body_facing: float,
                     max_angle_rate: float = 3.0, max_extension_rate: float = 2.0) -> None:
        """
        Set arm to reach toward a target position.

        This sets the rate of change; actual update happens in update().
        """
        hand_pos = self.get_hand_position(shoulder_pos, body_facing)
        to_target = target - shoulder_pos
        target_distance = to_target.length()

        # Target angle (in world space)
        target_world_angle = to_target.angle() if target_distance > 0.01 else body_facing
        target_arm_angle = target_world_angle - body_facing

        # Normalize to [-pi, pi]
        while target_arm_angle > math.pi:
            target_arm_angle -= 2 * math.pi
        while target_arm_angle < -math.pi:
            target_arm_angle += 2 * math.pi

        # Set angle rate to move toward target
        angle_diff = target_arm_angle - self.angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi

        self.angle_rate = max(-max_angle_rate, min(max_angle_rate, angle_diff * 5.0))

        # Set extension rate based on distance
        target_extension = min(1.0, target_distance / self.max_length)
        extension_diff = target_extension - self.extension
        self.extension_rate = max(-max_extension_rate, min(max_extension_rate, extension_diff * 5.0))

        self.hand_state = HandState.REACHING

    def retract(self, rate: float = 2.0) -> None:
        """Pull arm back toward body."""
        self.extension_rate = -rate
        self.angle_rate = -self.angle * 2.0  # Rotate back toward forward

    def update(self, dt: float) -> None:
        """Update arm state for one timestep."""
        # Apply rates
        self.angle += self.angle_rate * dt
        self.extension += self.extension_rate * dt

        # Clamp extension
        self.extension = max(0.0, min(1.0, self.extension))

        # Clamp angle (arms can't rotate behind the body too far)
        max_angle = math.pi * 0.8  # About 145 degrees
        self.angle = max(-max_angle, min(max_angle, self.angle))

        # Decay rates (natural stopping)
        self.angle_rate *= 0.9
        self.extension_rate *= 0.9

    def disengage(self) -> None:
        """Release any grip/engagement."""
        self.hand_state = HandState.FREE
        self.engaged_with = None
        self.engaged_arm = None


@dataclass
class ArmPair:
    """Both arms together for convenience."""
    left: Arm = field(default_factory=lambda: Arm(side=ArmSide.LEFT, angle=0.3))
    right: Arm = field(default_factory=lambda: Arm(side=ArmSide.RIGHT, angle=-0.3))

    def update(self, dt: float) -> None:
        self.left.update(dt)
        self.right.update(dt)

    def get_arm(self, side: ArmSide) -> Arm:
        return self.left if side == ArmSide.LEFT else self.right

    @property
    def any_engaged(self) -> bool:
        return (self.left.hand_state in (HandState.CONTROLLING, HandState.CONTROLLED, HandState.LOCKED) or
                self.right.hand_state in (HandState.CONTROLLING, HandState.CONTROLLED, HandState.LOCKED))

    @property
    def both_hands_inside(self) -> bool:
        """True if both hands are in controlling position (inside hands)."""
        return (self.left.hand_state == HandState.CONTROLLING and
                self.right.hand_state == HandState.CONTROLLING)
