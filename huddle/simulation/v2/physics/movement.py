"""Movement profiles and solver.

Defines player movement capabilities and provides a single solver
for all player movement in the simulation.

NGS Physics Integration:
Players can't make sharp turns at high speed - turn radius increases with speed.
This affects routes, pursuit, and all player movement. Calibration data from
Next Gen Stats tracking ensures realistic movement physics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

from ..core.vec2 import Vec2
from ..core.variance import execution_precision, is_deterministic
from .calibration import NGSCalibration, RecoveryState, get_calibration


@dataclass
class MovementProfile:
    """Defines how a player CAN move.

    Derived from player attributes (speed, acceleration, agility).
    Used by MovementSolver to compute actual movement.

    NGS Physics Integration:
    - calibration: Position-specific movement constraints from NGS data
    - recovery: Post-cut recovery state (limits acceleration after hard cuts)

    Attributes:
        max_speed: Top speed in yards/second
        acceleration: Acceleration in yards/second²
        deceleration: Deceleration rate (usually higher than accel)
        cut_speed_retention: Fraction of speed kept through hard cut (0-1)
        cut_angle_threshold: Angle (radians) that counts as a "cut"
        reaction_time: Seconds before responding to stimulus
        calibration: NGS calibration data for curvature constraints
        recovery: Post-cut recovery state
    """
    max_speed: float = 6.0
    acceleration: float = 12.0
    deceleration: float = 15.0
    cut_speed_retention: float = 0.6
    cut_angle_threshold: float = 0.5  # ~30 degrees
    reaction_time: float = 0.15

    # NGS Physics
    calibration: Optional[NGSCalibration] = None
    recovery: RecoveryState = field(default_factory=RecoveryState)

    @classmethod
    def from_attributes(
        cls,
        speed: int,
        acceleration: int,
        agility: int,
        position: Optional[str] = None,
    ) -> MovementProfile:
        """Create profile from player attributes (0-99 scale).

        Mapping:
            speed 99 → ~7.5 yards/sec (4.3 forty time)
            speed 75 → ~6.2 yards/sec (4.6 forty time)
            speed 50 → ~5.5 yards/sec (5.0+ forty time)

        Args:
            speed: Speed attribute (0-99)
            acceleration: Acceleration attribute (0-99)
            agility: Agility attribute (0-99)
            position: Optional position string for NGS calibration (e.g., "WR", "CB")
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

        # Get NGS calibration if position provided
        calibration = get_calibration(position) if position else None

        return cls(
            max_speed=max_speed,
            acceleration=accel,
            deceleration=decel,
            cut_speed_retention=cut_retention,
            cut_angle_threshold=0.5,
            reaction_time=reaction,
            calibration=calibration,
        )

    def time_to_top_speed(self) -> float:
        """Seconds to reach top speed from standstill."""
        return self.max_speed / self.acceleration

    def stopping_distance(self, current_speed: float) -> float:
        """Distance needed to stop from current speed."""
        # v² = 2 * a * d → d = v² / (2a)
        return (current_speed ** 2) / (2 * self.deceleration)

    def speed_after_cut(
        self,
        current_speed: float,
        angle: float,
        agility: Optional[int] = None,
    ) -> float:
        """Speed after making a cut of given angle.

        Uses NGS calibration if available for position-specific cut retention.

        Args:
            current_speed: Speed before the cut
            angle: Cut angle in radians
            agility: Player agility for variance (if None, no variance)

        Returns:
            Speed after the cut, with optional variance applied
        """
        if abs(angle) < self.cut_angle_threshold:
            # Gradual turn, no speed loss
            return current_speed

        # Use NGS calibration if available
        if self.calibration:
            retention = self.calibration.get_cut_retention(angle)
            # Start recovery period
            self.recovery.apply_cut(self.calibration)
        else:
            # Fallback to original formula
            # Hard cut - lose speed based on cut_speed_retention
            # Larger angles lose more speed
            angle_factor = min(1.0, abs(angle) / math.pi)  # 0 to 1
            retention = self.cut_speed_retention * (1 - angle_factor * 0.3)

        result_speed = current_speed * retention

        # Apply execution variance if agility provided (and not in deterministic mode)
        if agility is not None and not is_deterministic():
            # Higher agility = more consistent cuts (tighter variance)
            # Variance can make cuts slightly sharper OR sloppier
            result_speed = execution_precision(result_speed, agility)
            # Clamp to reasonable bounds (can't exceed pre-cut speed)
            result_speed = max(0.1, min(result_speed, current_speed))

        return result_speed

    # =========================================================================
    # NGS Curvature Methods
    # =========================================================================

    def max_curvature_at_speed(self, speed: float) -> float:
        """Get max curvature (1/turn_radius) at current speed.

        Higher curvature = tighter turns possible.
        At sprint speed, curvature is low (wide turns only).

        Args:
            speed: Current speed in yards/second

        Returns:
            Max curvature in 1/yards. Fallback is 0.5 (2 yard radius).
        """
        if self.calibration:
            return self.calibration.get_max_curvature(speed)
        # Fallback for non-calibrated profiles
        return 0.5

    def min_turn_radius_at_speed(self, speed: float) -> float:
        """Get minimum turn radius at current speed.

        Args:
            speed: Current speed in yards/second

        Returns:
            Minimum turn radius in yards
        """
        curvature = self.max_curvature_at_speed(speed)
        return 1.0 / max(curvature, 0.01)

    def max_turn_angle_for_tick(self, speed: float, dt: float) -> float:
        """Get maximum direction change for a single tick.

        This is the key physics constraint: at high speed, direction
        changes are limited by curvature physics.

        Args:
            speed: Current speed in yards/second
            dt: Time step in seconds

        Returns:
            Maximum turn angle in radians for this tick
        """
        if self.calibration:
            return self.calibration.get_max_turn_angle(speed, dt)
        # Fallback: realistic max turn for non-calibrated players
        # ~18 degrees per tick at standard dt=0.1s → 180°/sec max turn rate
        # This prevents "physics-defying" instant direction changes
        # Real NFL players max around 400-500°/sec in extreme cuts
        return math.pi / 10  # 18 degrees

    def get_effective_acceleration(self) -> float:
        """Get current effective acceleration, accounting for recovery.

        Returns:
            Effective acceleration (reduced during post-cut recovery)
        """
        return self.recovery.get_effective_acceleration(self.acceleration)

    def tick_recovery(self) -> None:
        """Process one tick of recovery state."""
        self.recovery.tick()

    def is_recovering(self) -> bool:
        """Check if player is in post-cut recovery period."""
        return self.recovery.is_recovering()

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
        agility: Optional[int] = None,
    ) -> MovementResult:
        """Compute movement toward target with NGS physics constraints.

        NGS Physics Integration:
        - Curvature constraint: Players can't turn sharply at high speed.
          Direction change is limited by speed-dependent curvature.
        - Recovery system: After hard cuts, acceleration is limited.

        Args:
            current_pos: Current position
            current_vel: Current velocity
            target_pos: Where the player wants to go
            profile: Player's movement capabilities
            dt: Time step in seconds
            max_speed_override: Optional speed cap (e.g., for jogging)
            agility: Player agility for cut variance (if None, no variance)

        Returns:
            MovementResult with new position, velocity, and debug info
        """
        # Tick recovery state
        profile.tick_recovery()

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
        actual_dir = desired_dir  # Direction we'll actually move

        if current_speed > 0.1:
            current_dir = current_vel.normalized()
            cut_angle = current_dir.angle_to(desired_dir)

            # =====================================================================
            # NGS Curvature Constraint: Limit direction change based on speed
            # =====================================================================
            # At high speed, players physically can't make sharp direction changes.
            # The curvature constraint creates realistic curved paths.
            if profile.calibration and cut_angle > 0.01:
                max_turn = profile.max_turn_angle_for_tick(current_speed, dt)

                if cut_angle > max_turn:
                    # Can't turn that sharply - take curved path instead
                    # Interpolate toward desired direction by the max allowed angle
                    actual_dir = self._interpolate_direction(
                        current_dir, desired_dir, max_turn
                    )

                    # If the desired cut exceeds what physics allows, it's still
                    # a "hard cut" attempt - apply speed loss for the attempted angle
                    if cut_angle > profile.cut_angle_threshold:
                        cut_occurred = True
                        current_speed = profile.speed_after_cut(
                            current_speed, cut_angle, agility
                        )
                else:
                    # Angle is within curvature limit
                    actual_dir = desired_dir
                    if cut_angle > profile.cut_angle_threshold:
                        # Hard cut - lose speed
                        cut_occurred = True
                        current_speed = profile.speed_after_cut(
                            current_speed, cut_angle, agility
                        )
            else:
                # No calibration - use original behavior
                if cut_angle > profile.cut_angle_threshold:
                    # Hard cut - lose speed (with optional variance from agility)
                    cut_occurred = True
                    current_speed = profile.speed_after_cut(
                        current_speed, cut_angle, agility
                    )

        speed_before = current_speed

        # Get effective acceleration (reduced during recovery)
        effective_accel = profile.get_effective_acceleration()

        # Accelerate toward max speed (or decelerate if overshooting)
        if current_speed < max_speed:
            # Accelerating (use effective acceleration)
            new_speed = min(max_speed, current_speed + effective_accel * dt)
        else:
            # Decelerating (always at full rate)
            new_speed = max(max_speed, current_speed - profile.deceleration * dt)

        # Check if we'd overshoot the target
        # If so, cap speed to arrive exactly
        if distance < new_speed * dt:
            new_speed = distance / dt

        # Build new velocity (use actual_dir which respects curvature)
        new_vel = actual_dir * new_speed

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

    def _interpolate_direction(
        self,
        current_dir: Vec2,
        target_dir: Vec2,
        max_angle: float,
    ) -> Vec2:
        """Interpolate from current to target direction by max_angle.

        Used for curvature-constrained movement: when the desired turn
        exceeds what physics allows, we turn as much as possible toward
        the target direction.

        Args:
            current_dir: Current normalized direction
            target_dir: Desired normalized direction
            max_angle: Maximum turn angle in radians

        Returns:
            New direction vector (normalized)
        """
        # Get angle between directions
        full_angle = current_dir.angle_to(target_dir)
        if full_angle < 0.001:
            return target_dir

        # Calculate interpolation factor
        t = min(1.0, max_angle / full_angle)

        # Lerp and normalize
        # We need signed angle to know which way to turn
        cross = current_dir.x * target_dir.y - current_dir.y * target_dir.x
        sign = 1.0 if cross >= 0 else -1.0

        # Rotate current_dir by (sign * max_angle)
        cos_a = math.cos(sign * max_angle)
        sin_a = math.sin(sign * max_angle)
        new_x = current_dir.x * cos_a - current_dir.y * sin_a
        new_y = current_dir.x * sin_a + current_dir.y * cos_a

        return Vec2(new_x, new_y).normalized()

    def solve_with_arrival(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
        dt: float,
        arrival_threshold: float = 0.5,
        max_speed_override: Optional[float] = None,
        agility: Optional[int] = None,
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
            agility: Player agility for cut variance

        Returns:
            (MovementResult, has_arrived)
        """
        result = self.solve(current_pos, current_vel, target_pos, profile, dt, max_speed_override, agility)
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

    def estimate_arrival_time_with_curvature(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
    ) -> float:
        """Estimate time to reach target accounting for turn curvature.

        This method adds a turn penalty when the player needs to change
        direction to reach the target. Players can't instantly redirect -
        the penalty reflects time to slow down, turn, and re-accelerate.

        Use this for:
        - QB arrival time estimates for receivers
        - Defender intercept calculations
        - Pursuit angle evaluations

        Args:
            current_pos: Current position
            current_vel: Current velocity
            target_pos: Target position
            profile: Player's movement profile

        Returns:
            Estimated arrival time in seconds
        """
        # Get base arrival time
        base_time = self.estimate_arrival_time(current_pos, current_vel, target_pos, profile)

        # Calculate turn penalty if player needs to change direction
        current_speed = current_vel.length()

        if current_speed < 0.5 or not profile.calibration:
            # Not moving or no calibration - no turn penalty
            return base_time

        # Get direction to target
        to_target = target_pos - current_pos
        if to_target.length() < 0.1:
            return base_time

        # Calculate angle between current velocity and target direction
        current_dir = current_vel.normalized()
        target_dir = to_target.normalized()
        turn_angle = current_dir.angle_to(target_dir)

        # If small angle, no significant penalty
        if turn_angle < math.radians(15):
            return base_time

        # Calculate turn penalty based on:
        # 1. How sharp the turn is
        # 2. The player's turn rate capability
        # 3. Current speed (faster = longer to turn)

        max_turn_rate = math.radians(profile.calibration.max_turn_rate_deg_sec)

        # Time to complete the turn (at max turn rate)
        turn_time = turn_angle / max_turn_rate

        # Speed penalty: at high speed, must slow down to turn sharply
        # Check if turn exceeds what's possible at current speed
        min_radius = profile.min_turn_radius_at_speed(current_speed)
        distance_to_target = to_target.length()

        # If turn is sharp and we're going fast, add deceleration penalty
        speed_penalty = 0.0
        if turn_angle > math.radians(45) and current_speed > 5.0:
            # Need to slow down for sharp turn
            # Estimate time to decelerate to a speed where turn is possible
            # and then re-accelerate
            target_turn_speed = 4.0  # Speed at which most turns are easy
            decel_time = (current_speed - target_turn_speed) / profile.deceleration
            reaccel_time = (current_speed - target_turn_speed) / profile.acceleration
            speed_penalty = (decel_time + reaccel_time) * 0.5  # Partial penalty

        # Add recovery time after the turn
        recovery_time = profile.calibration.recovery_time_sec if turn_angle > math.radians(45) else 0.0

        return base_time + turn_time + speed_penalty + recovery_time * 0.5


# =============================================================================
# Preset Profiles (with NGS calibration)
# =============================================================================

def create_wr_profile(speed: int = 90, accel: int = 88, agility: int = 88) -> MovementProfile:
    """Create typical WR movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="WR")


def create_rb_profile(speed: int = 88, accel: int = 90, agility: int = 90) -> MovementProfile:
    """Create typical RB movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="RB")


def create_te_profile(speed: int = 80, accel: int = 78, agility: int = 75) -> MovementProfile:
    """Create typical TE movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="TE")


def create_qb_profile(speed: int = 78, accel: int = 80, agility: int = 78) -> MovementProfile:
    """Create typical QB movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="QB")


def create_ol_profile(speed: int = 55, accel: int = 60, agility: int = 55) -> MovementProfile:
    """Create typical OL movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="OL")


def create_dl_profile(speed: int = 70, accel: int = 75, agility: int = 70) -> MovementProfile:
    """Create typical DL movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="DL")


def create_lb_profile(speed: int = 82, accel: int = 82, agility: int = 80) -> MovementProfile:
    """Create typical LB movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="LB")


def create_cb_profile(speed: int = 92, accel: int = 90, agility: int = 92) -> MovementProfile:
    """Create typical CB movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="CB")


def create_s_profile(speed: int = 88, accel: int = 86, agility: int = 85) -> MovementProfile:
    """Create typical Safety movement profile with NGS calibration."""
    return MovementProfile.from_attributes(speed, accel, agility, position="S")
