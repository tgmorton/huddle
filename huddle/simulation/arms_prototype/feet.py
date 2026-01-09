"""
Footwork model for linemen.

In real football, linemen are ALWAYS pumping their feet. The question isn't
"are they stepping" but "can their stepping keep up with the forces applied."

Balance emerges from:
- Step frequency (how fast they can pump feet)
- Step length (how far each step goes)
- External forces (pushes that must be absorbed by stepping)

When forces exceed what footwork can absorb, players lose balance and get driven.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math

from .vec2 import Vec2


class FootPhase(str, Enum):
    """Which phase of the step cycle a foot is in."""
    GROUNDED = "grounded"     # On ground, can bear weight
    LIFTING = "lifting"       # Just starting to lift
    AIRBORNE = "airborne"     # In the air, moving
    PLANTING = "planting"     # About to touch down


@dataclass
class Foot:
    """
    A single foot in continuous stepping motion.

    Feet are always cycling through step phases. The cycle time determines
    how fast a player can pump their feet.
    """
    position: Vec2
    phase: FootPhase = FootPhase.GROUNDED
    weight: float = 0.5  # 0-1, how much body weight on this foot

    # Step cycle
    cycle_progress: float = 0.0  # 0.0 to 1.0 through the step cycle
    step_target: Optional[Vec2] = None  # Where this foot is stepping to
    step_start: Optional[Vec2] = None   # Where the step started from

    # Foot speed attribute (can vary by player)
    step_speed: float = 4.0  # Steps per second capability

    def set_step_target(self, target: Vec2) -> None:
        """Set where this foot should step to next."""
        if self.phase == FootPhase.GROUNDED:
            self.step_start = self.position
            self.step_target = target

    def start_lift(self) -> None:
        """Begin lifting this foot for a step."""
        if self.phase == FootPhase.GROUNDED and self.step_target is not None:
            self.phase = FootPhase.LIFTING
            self.cycle_progress = 0.0
            self.weight = 0.0

    def update(self, dt: float) -> bool:
        """
        Update foot through step cycle.
        Returns True when foot plants (completes a step).
        """
        if self.phase == FootPhase.GROUNDED:
            # Grounded - waiting to lift or bearing weight
            return False

        # Progress through step cycle
        # A full step cycle: lift (0.2) -> airborne (0.5) -> plant (0.3)
        self.cycle_progress += self.step_speed * dt

        if self.cycle_progress < 0.2:
            # Lifting phase
            self.phase = FootPhase.LIFTING
            self.weight = 0.0
        elif self.cycle_progress < 0.7:
            # Airborne phase - foot is moving
            self.phase = FootPhase.AIRBORNE
            self.weight = 0.0
            # Interpolate position
            if self.step_start is not None and self.step_target is not None:
                t = (self.cycle_progress - 0.2) / 0.5  # 0 to 1 during airborne
                self.position = self.step_start.lerp(self.step_target, t)
        elif self.cycle_progress < 1.0:
            # Planting phase
            self.phase = FootPhase.PLANTING
            self.weight = 0.2  # Starting to bear weight
            if self.step_target is not None:
                self.position = self.step_target
        else:
            # Step complete
            self.phase = FootPhase.GROUNDED
            self.cycle_progress = 0.0
            self.weight = 0.5
            if self.step_target is not None:
                self.position = self.step_target
            self.step_target = None
            self.step_start = None
            return True

        return False

    @property
    def is_grounded(self) -> bool:
        return self.phase == FootPhase.GROUNDED

    @property
    def is_in_air(self) -> bool:
        return self.phase in (FootPhase.LIFTING, FootPhase.AIRBORNE)

    @property
    def can_bear_weight(self) -> bool:
        return self.phase in (FootPhase.GROUNDED, FootPhase.PLANTING)


@dataclass
class Stance:
    """
    Two feet in continuous stepping motion.

    Linemen are ALWAYS pumping feet. One foot steps while the other bears weight,
    then they alternate. Balance comes from whether this stepping can keep pace
    with external forces trying to move the player.

    Key concept: "Force debt" - when pushed harder than you can step to absorb,
    you accumulate debt. Too much debt = loss of balance = getting driven.
    """
    left: Foot = field(default_factory=lambda: Foot(position=Vec2(-0.3, 0)))
    right: Foot = field(default_factory=lambda: Foot(position=Vec2(0.3, 0)))

    # Ideal stance width (shoulder width)
    ideal_width: float = 0.5

    # Force debt - accumulated force that hasn't been absorbed by stepping
    # Positive = being pushed, need to step to recover
    force_debt: Vec2 = field(default_factory=Vec2.zero)
    max_debt: float = 0.5  # Beyond this, player starts losing balance

    # Which foot steps next (alternating)
    next_step_left: bool = True

    # Step frequency - how fast this player can pump feet
    # Higher = better athlete, can handle more force
    step_frequency: float = 3.0  # Steps per second per foot

    @property
    def center(self) -> Vec2:
        """Center point between feet."""
        return (self.left.position + self.right.position) * 0.5

    @property
    def width(self) -> float:
        """Current stance width."""
        return self.left.position.distance_to(self.right.position)

    @property
    def stance_vector(self) -> Vec2:
        """Vector from left foot to right foot."""
        return self.right.position - self.left.position

    @property
    def facing_from_feet(self) -> float:
        """Facing direction perpendicular to stance line."""
        stance = self.stance_vector
        return math.atan2(-stance.x, stance.y)

    @property
    def grounded_count(self) -> int:
        """How many feet are grounded (can bear weight)."""
        count = 0
        if self.left.can_bear_weight:
            count += 1
        if self.right.can_bear_weight:
            count += 1
        return count

    @property
    def is_stepping(self) -> bool:
        """True if either foot is in the air."""
        return self.left.is_in_air or self.right.is_in_air

    @property
    def balance_factor(self) -> float:
        """
        How balanced is this stance? 0-1.

        Balance comes from:
        - Force debt (too much = losing balance)
        - Foot grounding (at least one foot down)
        - Stance width (too narrow/wide = unstable)
        """
        # Force debt factor - main balance indicator
        debt_magnitude = self.force_debt.length()
        debt_factor = 1.0 - min(1.0, debt_magnitude / self.max_debt)

        # Grounding factor
        grounded = self.grounded_count
        if grounded == 0:
            ground_factor = 0.2  # Both feet in air - very vulnerable
        elif grounded == 1:
            ground_factor = 0.7  # One foot down - functional but vulnerable
        else:
            ground_factor = 1.0  # Both down - stable

        # Width factor
        width_ratio = self.width / self.ideal_width if self.ideal_width > 0 else 1.0
        if width_ratio < 0.5:
            width_factor = width_ratio * 2
        elif width_ratio > 1.5:
            width_factor = max(0.3, 2.0 - (width_ratio - 1.0))
        else:
            width_factor = 1.0

        return debt_factor * ground_factor * width_factor

    def get_push_power(self, direction: Vec2) -> float:
        """
        How much push power toward a direction?
        Power comes from driving off the back foot.
        """
        if direction.length() < 0.01:
            return 0.5

        dir_norm = direction.normalized()

        # Which foot is "back" relative to push direction?
        left_pos = self.left.position.dot(dir_norm)
        right_pos = self.right.position.dot(dir_norm)

        if left_pos < right_pos:
            drive_foot = self.left
        else:
            drive_foot = self.right

        # Power from drive foot
        power = 0.3
        if drive_foot.can_bear_weight:
            power += 0.5 * drive_foot.weight

        return power * self.balance_factor

    def apply_force(self, force: Vec2, dt: float) -> None:
        """
        Apply external force to stance. This creates "force debt" that must
        be paid off by stepping. If debt exceeds capacity, balance is lost.
        """
        # Add force to debt (scaled by dt)
        self.force_debt = self.force_debt + force * dt * 0.1

    def request_step(self, direction: Vec2, distance: float = 0.3) -> bool:
        """
        Request a step in a direction. The appropriate foot will step
        when it's able to (grounded and ready).

        CRITICAL: Only one foot can be in the air at a time. If a step
        is already in progress, this returns False.
        """
        if direction.length() < 0.01:
            return False

        # Cannot start a new step if one is already in progress
        if self.left.is_in_air or self.right.is_in_air:
            return False

        dir_norm = direction.normalized()

        # Determine which foot should step based on direction
        # Step the foot that's in the direction of movement
        left_dot = (self.left.position - self.center).dot(dir_norm)
        right_dot = (self.right.position - self.center).dot(dir_norm)

        # Prefer the foot in the direction of movement
        if left_dot > right_dot:
            foot_to_step = self.left
            other_foot = self.right
            is_left = True
        else:
            foot_to_step = self.right
            other_foot = self.left
            is_left = False

        # Calculate raw step target
        target = foot_to_step.position + dir_norm * distance

        # === CONSTRAIN STANCE WIDTH ===
        # Don't let feet get more than 2x ideal width apart
        max_width = self.ideal_width * 2.0

        # Calculate what the width would be after this step
        if is_left:
            new_width = other_foot.position.distance_to(target)
        else:
            new_width = other_foot.position.distance_to(target)

        if new_width > max_width:
            # Pull target back toward center to maintain max width
            to_other = other_foot.position - target
            if to_other.length() > 0.01:
                # Move target closer to other foot
                overshoot = new_width - max_width
                target = target + to_other.normalized() * overshoot

        foot_to_step.set_step_target(target)
        foot_to_step.start_lift()

        # Shift weight to the other foot
        other_foot.weight = 1.0
        foot_to_step.weight = 0.0

        return True

    def update(self, dt: float) -> bool:
        """
        Update the continuous stepping cycle.
        Returns True if a foot just planted.
        """
        # Update both feet
        left_planted = self.left.update(dt)
        right_planted = self.right.update(dt)

        # === CONTINUOUS STEPPING ===
        # If we have force debt and a foot is available, step to absorb it
        debt_magnitude = self.force_debt.length()

        if debt_magnitude > 0.05:
            # Need to step to absorb force
            step_dir = self.force_debt.normalized()

            # Try to step if a foot is available
            if self.left.is_grounded or self.right.is_grounded:
                # Step distance proportional to debt
                step_dist = min(0.4, debt_magnitude * 0.5)
                if self.request_step(step_dir, step_dist):
                    # Successfully initiated step - will pay off debt when planted
                    pass

        # === DEBT RECOVERY ONLY ON STEP COMPLETION ===
        # Force debt is paid off by completing steps, not by waiting.
        # When a foot plants, it absorbs some of the accumulated debt.
        if left_planted or right_planted:
            # Completing a step pays off debt proportional to step distance
            # A good step can absorb significant force
            self.force_debt = self.force_debt * 0.4  # Step absorbs 60% of debt

            # Rebalance weight
            if self.left.can_bear_weight and self.right.can_bear_weight:
                self.left.weight = 0.5
                self.right.weight = 0.5

        return left_planted or right_planted

    def set_position(self, center: Vec2, facing: float) -> None:
        """Set stance centered at position with given facing."""
        right_vec = Vec2.from_angle(facing - math.pi / 2)
        half_width = self.ideal_width / 2

        self.left.position = center + right_vec * (-half_width)
        self.right.position = center + right_vec * half_width
        self.left.phase = FootPhase.GROUNDED
        self.right.phase = FootPhase.GROUNDED
        self.left.weight = 0.5
        self.right.weight = 0.5
        self.force_debt = Vec2.zero()
