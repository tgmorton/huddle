"""Movement profiles and solver.

Defines player movement capabilities and provides a single solver
for all player movement in the simulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from ..core.vec2 import Vec2


@dataclass
class MovementProfile:
    """Defines how a player CAN move.

    Derived from player attributes (speed, acceleration, agility).
    Used by MovementSolver to compute actual movement.

    Attributes:
        max_speed: Top speed in yards/second
        acceleration: Acceleration in yards/second²
        deceleration: Deceleration rate (usually higher than accel)
        cut_speed_retention: Fraction of speed kept through hard cut (0-1)
        cut_angle_threshold: Angle (radians) that counts as a "cut"
        reaction_time: Seconds before responding to stimulus
    """
    max_speed: float = 6.0
    acceleration: float = 12.0
    deceleration: float = 15.0
    cut_speed_retention: float = 0.6
    cut_angle_threshold: float = 0.5  # ~30 degrees
    reaction_time: float = 0.15

    @classmethod
    def from_attributes(cls, speed: int, acceleration: int, agility: int) -> MovementProfile:
        """Create profile from player attributes (0-99 scale).

        Mapping:
            speed 99 → ~7.5 yards/sec (4.3 forty time)
            speed 75 → ~6.2 yards/sec (4.6 forty time)
            speed 50 → ~5.5 yards/sec (5.0+ forty time)
        """
        # Speed: 4.5 to 7.5 yards/sec based on rating
        # Higher ratings have exponential effect at top end
        speed_factor = speed / 100
        max_speed = 4.5 + (speed_factor ** 1.5) * 3.0

        # Acceleration: 8 to 16 yards/sec²
        accel_factor = acceleration / 100
        accel = 8.0 + accel_factor * 8.0

        # Deceleration is typically 20-30% higher than acceleration
        decel = accel * 1.25

        # Agility affects cut speed retention (40% to 85%)
        agility_factor = agility / 100
        cut_retention = 0.4 + agility_factor * 0.45

        # Reaction time: 100ms to 250ms based on agility
        reaction = 0.25 - agility_factor * 0.15

        return cls(
            max_speed=max_speed,
            acceleration=accel,
            deceleration=decel,
            cut_speed_retention=cut_retention,
            cut_angle_threshold=0.5,
            reaction_time=reaction,
        )

    def time_to_top_speed(self) -> float:
        """Seconds to reach top speed from standstill."""
        return self.max_speed / self.acceleration

    def stopping_distance(self, current_speed: float) -> float:
        """Distance needed to stop from current speed."""
        # v² = 2 * a * d → d = v² / (2a)
        return (current_speed ** 2) / (2 * self.deceleration)

    def speed_after_cut(self, current_speed: float, angle: float) -> float:
        """Speed after making a cut of given angle."""
        if abs(angle) < self.cut_angle_threshold:
            # Gradual turn, no speed loss
            return current_speed

        # Hard cut - lose speed based on cut_speed_retention
        # Larger angles lose more speed
        angle_factor = min(1.0, abs(angle) / math.pi)  # 0 to 1
        retention = self.cut_speed_retention * (1 - angle_factor * 0.3)
        return current_speed * retention

    def __repr__(self) -> str:
        return (
            f"MovementProfile(max_speed={self.max_speed:.1f}, "
            f"accel={self.acceleration:.1f}, "
            f"cut_retention={self.cut_speed_retention:.0%})"
        )


@dataclass
class MovementResult:
    """Result of a movement calculation.

    Contains new position, velocity, and debug info about what happened.
    """
    new_pos: Vec2
    new_vel: Vec2

    # Debug info
    cut_occurred: bool = False
    cut_angle: float = 0.0
    speed_before: float = 0.0
    speed_after: float = 0.0
    at_max_speed: bool = False

    def format_debug(self) -> str:
        """Format for logging."""
        parts = [f"→ {self.new_pos} @ {self.speed_after:.2f} yds/s"]

        if self.cut_occurred:
            parts.append(f"(cut {math.degrees(self.cut_angle):.0f}°, lost {(1 - self.speed_after/max(0.01, self.speed_before)):.0%} speed)")

        if self.at_max_speed:
            parts.append("[MAX SPEED]")

        return " ".join(parts)


class MovementSolver:
    """Solves player movement given current state and target.

    This is the SINGLE source of truth for all player movement.
    Systems set targets, the solver computes where players actually end up.
    """

    def solve(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
        dt: float,
        max_speed_override: Optional[float] = None,
    ) -> MovementResult:
        """Compute movement toward target.

        Args:
            current_pos: Current position
            current_vel: Current velocity
            target_pos: Where the player wants to go
            profile: Player's movement capabilities
            dt: Time step in seconds
            max_speed_override: Optional speed cap (e.g., for jogging)

        Returns:
            MovementResult with new position, velocity, and debug info
        """
        # Get direction to target
        to_target = target_pos - current_pos
        distance = to_target.length()

        # If we're basically there, stop
        if distance < 0.01:
            return MovementResult(
                new_pos=current_pos,
                new_vel=Vec2.zero(),
                speed_after=0.0,
            )

        desired_dir = to_target.normalized()
        current_speed = current_vel.length()
        max_speed = max_speed_override if max_speed_override else profile.max_speed

        # Determine if this is a cut
        cut_occurred = False
        cut_angle = 0.0

        if current_speed > 0.1:
            current_dir = current_vel.normalized()
            cut_angle = current_dir.angle_to(desired_dir)

            if cut_angle > profile.cut_angle_threshold:
                # Hard cut - lose speed
                cut_occurred = True
                current_speed = profile.speed_after_cut(current_speed, cut_angle)

        speed_before = current_speed

        # Accelerate toward max speed (or decelerate if overshooting)
        if current_speed < max_speed:
            # Accelerating
            new_speed = min(max_speed, current_speed + profile.acceleration * dt)
        else:
            # Decelerating
            new_speed = max(max_speed, current_speed - profile.deceleration * dt)

        # Check if we'd overshoot the target
        # If so, cap speed to arrive exactly
        if distance < new_speed * dt:
            new_speed = distance / dt

        # Build new velocity
        new_vel = desired_dir * new_speed

        # Compute new position
        new_pos = current_pos + new_vel * dt

        return MovementResult(
            new_pos=new_pos,
            new_vel=new_vel,
            cut_occurred=cut_occurred,
            cut_angle=cut_angle,
            speed_before=speed_before,
            speed_after=new_speed,
            at_max_speed=abs(new_speed - max_speed) < 0.1,
        )

    def solve_with_arrival(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
        dt: float,
        arrival_threshold: float = 0.5,
        max_speed_override: Optional[float] = None,
    ) -> Tuple[MovementResult, bool]:
        """Solve movement and report if arrived at target.

        Args:
            current_pos: Current position
            current_vel: Current velocity
            target_pos: Where the player wants to go
            profile: Player's movement capabilities
            max_speed_override: Optional speed cap
            dt: Time step in seconds
            arrival_threshold: Distance considered "arrived"

        Returns:
            (MovementResult, has_arrived)
        """
        result = self.solve(current_pos, current_vel, target_pos, profile, dt, max_speed_override)
        arrived = result.new_pos.distance_to(target_pos) < arrival_threshold
        return result, arrived

    def estimate_arrival_time(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
    ) -> float:
        """Estimate time to reach target in seconds.

        This is an approximation that assumes no cuts needed.
        """
        distance = current_pos.distance_to(target_pos)
        current_speed = current_vel.length()

        if distance < 0.1:
            return 0.0

        # Time to accelerate to max speed
        if current_speed < profile.max_speed:
            accel_time = (profile.max_speed - current_speed) / profile.acceleration
            # Distance covered while accelerating: v*t + 0.5*a*t²
            accel_distance = current_speed * accel_time + 0.5 * profile.acceleration * accel_time ** 2

            if accel_distance >= distance:
                # We arrive before reaching max speed
                # Solve: d = v*t + 0.5*a*t² for t
                # Using quadratic formula
                a = 0.5 * profile.acceleration
                b = current_speed
                c = -distance
                discriminant = b ** 2 - 4 * a * c
                if discriminant >= 0:
                    return (-b + math.sqrt(discriminant)) / (2 * a)
                return distance / max(current_speed, 1.0)

            remaining_distance = distance - accel_distance
            return accel_time + remaining_distance / profile.max_speed
        else:
            # Already at max speed
            return distance / profile.max_speed


# =============================================================================
# Preset Profiles
# =============================================================================

def create_wr_profile(speed: int = 90, accel: int = 88, agility: int = 88) -> MovementProfile:
    """Create typical WR movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_rb_profile(speed: int = 88, accel: int = 90, agility: int = 90) -> MovementProfile:
    """Create typical RB movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_te_profile(speed: int = 80, accel: int = 78, agility: int = 75) -> MovementProfile:
    """Create typical TE movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_qb_profile(speed: int = 78, accel: int = 80, agility: int = 78) -> MovementProfile:
    """Create typical QB movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_ol_profile(speed: int = 55, accel: int = 60, agility: int = 55) -> MovementProfile:
    """Create typical OL movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_dl_profile(speed: int = 70, accel: int = 75, agility: int = 70) -> MovementProfile:
    """Create typical DL movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_lb_profile(speed: int = 82, accel: int = 82, agility: int = 80) -> MovementProfile:
    """Create typical LB movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_cb_profile(speed: int = 92, accel: int = 90, agility: int = 92) -> MovementProfile:
    """Create typical CB movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)


def create_s_profile(speed: int = 88, accel: int = 86, agility: int = 85) -> MovementProfile:
    """Create typical Safety movement profile."""
    return MovementProfile.from_attributes(speed, accel, agility)
