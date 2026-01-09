"""
Player model combining body, arms, and feet.

A player is a physical entity. Their power comes from their feet,
transmitted through their body and arms.

Attributes (STR, AGI) drive the physical systems:
- STR: Force generation, resistance, debt capacity
- AGI: Step frequency, hand speed, move execution
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math

from .vec2 import Vec2
from .body import Body, BodyDimensions, Stance
from .arm import Arm, ArmPair, ArmSide, HandState
from .feet import Stance as FootStance, FootPhase
from .attributes import PhysicalAttributes


class PlayerRole(str, Enum):
    """What this player is trying to do."""
    BLOCKER = "blocker"       # OL - prevent defender from reaching target
    RUSHER = "rusher"         # DL - get past blocker to target
    BALL_CARRIER = "ball_carrier"
    TACKLER = "tackler"


@dataclass
class Player:
    """
    A complete player with body, arms, and feet.

    Power flows from the ground up:
    - Feet planted = can generate force
    - Feet stepping = vulnerable but moving
    - Balance comes from foot position

    Attributes drive capability:
    - STR: Force generation, anchor strength, debt capacity
    - AGI: Step frequency, hand speed
    """
    id: str
    role: PlayerRole

    # Physical components
    body: Body = field(default_factory=Body)
    arms: ArmPair = field(default_factory=ArmPair)
    feet: FootStance = field(default_factory=FootStance)

    # Attributes - the engine that powers the physical systems
    attributes: PhysicalAttributes = field(default_factory=PhysicalAttributes)

    def __post_init__(self):
        # Set arm properties from body dimensions and attributes
        self.arms.left.max_length = self.body.dimensions.arm_length
        self.arms.right.max_length = self.body.dimensions.arm_length

        # Wire STR to arm power
        self.arms.left.power = self.attributes.str_force_mult
        self.arms.right.power = self.attributes.str_force_mult

        # Wire AGI to feet
        self.feet.step_frequency = self.attributes.agi_step_frequency
        self.feet.left.step_speed = self.attributes.agi_step_frequency * 1.3  # Individual foot faster
        self.feet.right.step_speed = self.attributes.agi_step_frequency * 1.3

        # Wire STR to force debt capacity
        self.feet.max_debt = self.attributes.str_debt_capacity

        # Initialize feet at body position
        self.feet.set_position(self.body.center, self.body.facing)

    # =========================================================================
    # Position/Movement Properties
    # =========================================================================

    @property
    def position(self) -> Vec2:
        return self.body.center

    @position.setter
    def position(self, value: Vec2):
        self.body.center = value

    @property
    def facing(self) -> float:
        return self.body.facing

    @facing.setter
    def facing(self, value: float):
        self.body.facing = value

    @property
    def velocity(self) -> Vec2:
        return self.body.velocity

    @velocity.setter
    def velocity(self, value: Vec2):
        self.body.velocity = value

    # =========================================================================
    # Arm/Hand Positions
    # =========================================================================

    @property
    def left_hand_pos(self) -> Vec2:
        return self.arms.left.get_hand_position(
            self.body.left_shoulder, self.body.facing
        )

    @property
    def right_hand_pos(self) -> Vec2:
        return self.arms.right.get_hand_position(
            self.body.right_shoulder, self.body.facing
        )

    @property
    def left_shoulder(self) -> Vec2:
        return self.body.left_shoulder

    @property
    def right_shoulder(self) -> Vec2:
        return self.body.right_shoulder

    # =========================================================================
    # Combat/Engagement Properties
    # =========================================================================

    @property
    def has_inside_hands(self) -> bool:
        """True if this player has inside hand position (controlling)."""
        return self.arms.both_hands_inside

    @property
    def is_engaged(self) -> bool:
        return self.arms.any_engaged

    @property
    def leverage(self) -> float:
        """Overall leverage factor (pad level + balance from feet)."""
        return self.body.leverage_factor * self.feet.balance_factor

    @property
    def effective_power(self) -> float:
        """Combined power from body and arms."""
        body_power = self.body.effective_strength
        arm_power = (self.arms.left.effective_power + self.arms.right.effective_power) / 2
        return body_power * arm_power

    @property
    def is_stepping(self) -> bool:
        """True if either foot is in the air."""
        return self.feet.is_stepping

    @property
    def can_generate_power(self) -> bool:
        """Can generate power when at least one foot is grounded with good balance."""
        return self.feet.grounded_count > 0 and self.feet.balance_factor > 0.4

    @property
    def force_debt(self) -> float:
        """How much force debt have we accumulated? High = losing the battle."""
        return self.feet.force_debt.length()

    def get_push_power_toward(self, target: Vec2) -> float:
        """How much push power toward a target?"""
        direction = target - self.position
        return self.feet.get_push_power(direction)

    # =========================================================================
    # Actions
    # =========================================================================

    def reach_with(self, side: ArmSide, target: Vec2) -> None:
        """Reach one arm toward a target position."""
        arm = self.arms.get_arm(side)
        shoulder = self.left_shoulder if side == ArmSide.LEFT else self.right_shoulder
        arm.reach_toward(target, shoulder, self.body.facing)

    def reach_both_toward(self, target: Vec2) -> None:
        """Reach both arms toward a target (like engaging a blocker)."""
        self.reach_with(ArmSide.LEFT, target)
        self.reach_with(ArmSide.RIGHT, target)

    def punch(self, side: ArmSide) -> None:
        """Quick extension - the OL punch."""
        arm = self.arms.get_arm(side)
        arm.extension_rate = 4.0  # Fast extension
        arm.hand_state = HandState.REACHING

    def punch_both(self) -> None:
        """Double-hand punch."""
        self.punch(ArmSide.LEFT)
        self.punch(ArmSide.RIGHT)

    def retract_arms(self) -> None:
        """Pull both arms back."""
        self.arms.left.retract()
        self.arms.right.retract()

    def lower_pad_level(self, amount: float = 0.1) -> None:
        """Get lower (better leverage)."""
        self.body.pad_level = max(0.0, self.body.pad_level - amount)

    def raise_pad_level(self, amount: float = 0.1) -> None:
        """Stand up (worse leverage but more mobility)."""
        self.body.pad_level = min(1.0, self.body.pad_level + amount)

    def face_toward(self, target: Vec2, rate: float = 5.0) -> None:
        """Turn to face a target position."""
        to_target = target - self.position
        if to_target.length() < 0.01:
            return
        target_facing = to_target.angle()

        # Shortest rotation direction
        diff = target_facing - self.body.facing
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi

        self.body.angular_velocity = diff * rate

    def move_toward(self, target: Vec2, speed: float) -> None:
        """
        Set velocity toward target.
        This is the simple version - for more realistic movement, use step methods.
        """
        to_target = target - self.position
        dist = to_target.length()
        if dist < 0.01:
            self.velocity = Vec2.zero()
            return
        direction = to_target.normalized()
        self.velocity = direction * min(speed, dist * 10)  # Slow down near target

    # =========================================================================
    # Footwork Actions
    # =========================================================================

    def kick_step(self, direction: Vec2) -> bool:
        """
        OL kick step - step to intercept/mirror rusher.
        Maintains balance while moving laterally or backward.
        """
        return self.feet.request_step(direction, distance=0.4)

    def drive_step(self, direction: Vec2) -> bool:
        """
        Drive step - step forward to generate push power.
        Used when driving an opponent.
        """
        return self.feet.request_step(direction, distance=0.3)

    def shuffle_toward(self, target: Vec2) -> bool:
        """
        Shuffle step toward target - maintains stance while moving.
        Slower than running but keeps you in position to fight.
        """
        direction = target - self.position
        if direction.length() < 0.1:
            return False
        return self.feet.request_step(direction, distance=0.25)

    def set_feet(self) -> None:
        """
        Plant feet at current position.
        Call after moving to establish base.
        """
        self.feet.set_position(self.body.center, self.body.facing)

    def apply_force(self, force: Vec2, dt: float) -> None:
        """
        Apply external force. This creates "force debt" that must be
        absorbed by stepping. If we can't step fast enough, we get pushed.
        """
        # Force goes to feet as debt
        self.feet.apply_force(force, dt)
        # Also apply to body physics for immediate effect
        self.body.apply_force(force * 0.3, dt)  # Reduced - most absorbed by stepping

    # =========================================================================
    # Update
    # =========================================================================

    def update(self, dt: float) -> None:
        """
        Update all physics for one timestep.

        TWO MODES:
        1. ENGAGED (fighting someone): Force creates debt, feet absorb it
        2. FREE RUNNING: Feet step proactively, body follows

        The distinction captures the difference between:
        - Compensatory: reacting to external forces (engaged)
        - Intentional: executing movement commands (running)
        """
        # Update arms
        self.arms.update(dt)

        if self.is_engaged:
            # === ENGAGED MODE: Compensatory stepping ===
            # External forces create debt, feet step to absorb

            # Feet update (may auto-step to absorb debt)
            foot_planted = self.feet.update(dt)

            # Body tracks toward feet center
            feet_center = self.feet.center
            body_to_feet = feet_center - self.body.center
            if body_to_feet.length() > 0.02:
                catch_up_rate = min(0.5, body_to_feet.length() * 2.0)
                self.body.center = self.body.center + body_to_feet * catch_up_rate

            # Apply body physics
            old_pos = self.body.center
            self.body.update(dt)
            new_pos = self.body.center

            # Movement from physics creates force debt
            forced_movement = new_pos - old_pos
            if forced_movement.length() > 0.01:
                push_force = forced_movement * 5.0
                self.feet.apply_force(push_force, dt)

            # If overwhelmed by debt, drift in that direction
            if self.feet.force_debt.length() > self.feet.max_debt * 1.5:
                drift = self.feet.force_debt.normalized() * 0.1
                self.body.center = self.body.center + drift

        else:
            # === FREE RUNNING MODE: Intentional stepping ===
            # Velocity sets intention, feet step to execute

            # If we have velocity, step in that direction
            if self.velocity.length() > 0.5:
                move_dir = self.velocity.normalized()
                # Proactively step toward movement direction
                self.feet.request_step(move_dir, distance=0.3)

            # Feet update
            foot_planted = self.feet.update(dt)

            # Apply body physics (velocity moves us)
            self.body.update(dt)

            # Feet follow body when running free
            # (opposite of engaged - body leads, feet catch up)
            self.feet.set_position(self.body.center, self.body.facing)

        # === BALANCE FROM FEET ===
        self.body.balance = self.feet.balance_factor

        # Update feet ideal width from body dimensions
        self.feet.ideal_width = self.body.dimensions.shoulder_width

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create_lineman(
        cls,
        id: str,
        role: PlayerRole,
        position: Vec2,
        facing: float,
        weight: int = 310,
        attributes: PhysicalAttributes | None = None,
    ) -> Player:
        """
        Create an OL or DL player.

        Args:
            id: Player identifier
            role: BLOCKER or RUSHER
            position: Starting position
            facing: Facing angle in radians
            weight: Weight in pounds (affects mass/momentum)
            attributes: Physical attributes (STR, AGI). If None, uses average.
        """
        body = Body(
            center=position,
            facing=facing,
            pad_level=0.4,  # Linemen start low
            stance=Stance.TWO_POINT,
            dimensions=BodyDimensions.lineman(weight_lbs=weight),
        )

        # Default to average attributes if not provided
        if attributes is None:
            if role == PlayerRole.BLOCKER:
                attributes = PhysicalAttributes.average_ol()
            else:
                attributes = PhysicalAttributes.average_dt()

        return cls(id=id, role=role, body=body, attributes=attributes)

    @classmethod
    def create_skill_player(
        cls,
        id: str,
        role: PlayerRole,
        position: Vec2,
        facing: float,
        weight: int = 200,
        attributes: PhysicalAttributes | None = None,
    ) -> Player:
        """Create a skill position player."""
        body = Body(
            center=position,
            facing=facing,
            pad_level=0.6,  # More upright
            stance=Stance.ATHLETIC,
            dimensions=BodyDimensions.skill_player(weight_lbs=weight),
        )

        if attributes is None:
            attributes = PhysicalAttributes()  # Average

        return cls(id=id, role=role, body=body, attributes=attributes)
