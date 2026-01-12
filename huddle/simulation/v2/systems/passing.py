"""Passing system for v2 simulation.

Handles:
- Ball flight physics (velocity, trajectory)
- Throw mechanics (accuracy, lead on receiver)
- Catch resolution (contested/uncontested, interceptions)
- Defender ball tracking
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple, Dict, Any

from ..core.vec2 import Vec2
from ..core.entities import Player, Ball, BallState, Team, ThrowType
from ..core.clock import Clock
from ..core.events import EventBus, EventType
from ..core.ratings import get_matchup_modifier


# =============================================================================
# Constants
# =============================================================================

# Ball velocity by throw type (yards per second)
# NFL passes average 50-60 mph = 24-29 yds/s
THROW_VELOCITY = {
    ThrowType.BULLET: (22.0, 29.0),  # Fast, tight spiral
    ThrowType.TOUCH: (18.0, 24.0),   # Softer, more arc
    ThrowType.LOB: (14.0, 20.0),     # High arc, slower
}

# Peak height by throw type (yards above baseline trajectory)
THROW_ARC_HEIGHT = {
    ThrowType.BULLET: (0.5, 2.0),   # Nearly flat
    ThrowType.TOUCH: (3.0, 6.0),    # Nice arc over defenders
    ThrowType.LOB: (8.0, 14.0),     # High rainbow
}

# Distance thresholds for throw type selection (yards)
BULLET_MAX_DISTANCE = 15.0   # Use bullet for short throws
TOUCH_MAX_DISTANCE = 30.0    # Use touch for intermediate
# Beyond TOUCH_MAX_DISTANCE, use lob

# Throw accuracy variance (yards)
BASE_ACCURACY_VARIANCE = 1.5  # Max inaccuracy for poor QB
MIN_ACCURACY_VARIANCE = 0.2   # Best case for elite QB

# Catch resolution
# Aligned with QB brain's CONTESTED_THRESHOLD (1.5 yards)
# If QB considers a throw "contested but throwable", catch resolution should agree
CONTESTED_CATCH_RADIUS = 1.5  # Defender within this = contested
REACH_FALLOFF_CENTER = 1.5    # 50% catch at this distance (yards from ball)
REACH_FALLOFF_RATE = 0.5      # Steepness of falloff (higher = more gradual)

# Contest factors - calibrated to NFL contested catch rates (~45-50%)
CONTEST_BASE = 0.45           # Offense advantage at equal position
CONTEST_SEPARATION_WEIGHT = 0.15
CONTEST_SKILL_WEIGHT = 0.15

# Interception
INT_BASE_CHANCE = 0.10
INT_MIN_CHANCE = 0.03
INT_MAX_CHANCE = 0.20

# Uncontested catch - calibrated to NFL completion rates
# NFL data: 0-5 yards = 74%, 6-10 = 63%, 11-15 = 57%, 16-20 = 52%, 20+ = 35%
# These are BASE rates before accuracy/skill modifiers
UNCONTESTED_BASE_CATCH = 0.72  # Base catch rate (adjusted down from 0.90)
UNCONTESTED_SKILL_BONUS = 0.08  # Bonus for good receivers

# Depth-based catch penalty (per 10 yards of depth)
# Deeper passes are harder to complete even when open
DEPTH_CATCH_PENALTY_PER_10YDS = 0.08  # 8% penalty per 10 yards

# Ball tracking for defenders
BALL_TRACK_REACTION_TICKS = 3  # Ticks before defender reacts to ball
BALL_TRACK_SPEED_PENALTY = 0.7  # Speed while tracking ball

# QB decision making - Read Progression
MIN_THROW_TIME = 0.8  # Minimum time before throwing (snap to throw)
MAX_HOLD_TIME = 3.5  # Forced to throw after this time (pressure/sack coming)

# Separation thresholds (yards)
OPEN_THRESHOLD = 2.5  # Receiver is "open" - throw it
CONTESTED_THRESHOLD = 1.5  # Receiver is contested but throwable
COVERED_THRESHOLD = 1.0  # Too tight, move to next read

# Route timing (used to calculate when receiver hits break point)
AVERAGE_RECEIVER_SPEED = 6.5  # Yards per second (used if speed unknown)
PRE_BREAK_SPEED_FACTOR = 0.8  # Receiver runs slower before break (selling stem)


# =============================================================================
# Enums and Data Structures
# =============================================================================

class CatchResult(str, Enum):
    """Possible catch outcomes."""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"


class PassState(str, Enum):
    """State of a pass play."""
    PRE_THROW = "pre_throw"
    IN_FLIGHT = "in_flight"
    RESOLVED = "resolved"


@dataclass
class ThrowResult:
    """Result of a throw attempt."""
    success: bool
    target_pos: Vec2
    actual_target: Vec2  # After accuracy applied
    velocity: float  # yards/second
    flight_time: float  # seconds
    accuracy_variance: float  # How much it missed by


@dataclass
class CatchContext:
    """Context for catch resolution."""
    receiver_dist_to_ball: float
    defender_dist_to_ball: float
    throw_accuracy: float  # 0-1, 1 = perfect
    is_contested: bool
    receiver_catch_rating: int
    defender_coverage_rating: int
    separation: float  # Positive = receiver advantage


@dataclass
class CatchResolution:
    """Result of catch resolution."""
    result: CatchResult
    probability: float
    catch_probability: float
    int_probability: float
    context: CatchContext
    roll: float


@dataclass
class ReceiverWindow:
    """Info about a receiver's throw window."""
    receiver: Player
    separation: float  # Distance from nearest defender
    nearest_defender: Optional[Player]
    score: float  # Overall quality of window (higher = better)
    route_phase: str = ""  # Current phase of route (stem, break, post_break, complete)
    at_or_past_break: bool = False  # Has receiver hit their break point?


# =============================================================================
# Helper Functions
# =============================================================================

def logistic(x: float, center: float = 0, rate: float = 1) -> float:
    """Logistic curve for probability falloff."""
    z = (x - center) / rate
    z = max(-20, min(20, z))
    return 1 / (1 + math.exp(z))


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


# =============================================================================
# Passing System
# =============================================================================

class PassingSystem:
    """Manages ball flight and catch resolution."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.state = PassState.PRE_THROW

        # Current pass info
        self.ball: Optional[Ball] = None
        self.throw_start_time: float = 0.0
        self.target_receiver_id: Optional[str] = None
        self.throw_result: Optional[ThrowResult] = None

        # Defender tracking
        self.defenders_tracking_ball: set[str] = set()
        self.ball_in_air_ticks: int = 0

    def _select_throw_type(self, distance: float, has_defender_underneath: bool = False) -> ThrowType:
        """Select appropriate throw type based on distance and situation.

        Args:
            distance: Distance to target in yards
            has_defender_underneath: Is there a defender between QB and receiver

        Returns:
            Appropriate ThrowType
        """
        if distance <= BULLET_MAX_DISTANCE and not has_defender_underneath:
            return ThrowType.BULLET
        elif distance <= TOUCH_MAX_DISTANCE:
            return ThrowType.TOUCH
        else:
            return ThrowType.LOB

    def _calculate_intercept_point(
        self,
        thrower_pos: Vec2,
        receiver_pos: Vec2,
        receiver_velocity: Vec2,
        ball_speed: float,
    ) -> tuple[Vec2, float]:
        """Calculate where ball and receiver will meet.

        Uses the intercept equation to find the point where a ball traveling
        at ball_speed will meet a receiver traveling at receiver_velocity.

        This solves: |receiver_pos + t*receiver_vel - thrower_pos| = ball_speed * t

        Args:
            thrower_pos: QB position
            receiver_pos: Receiver current position
            receiver_velocity: Receiver velocity vector
            ball_speed: Ball velocity (yards/second)

        Returns:
            (intercept_point, flight_time)
        """
        # Vector from thrower to receiver
        to_receiver = receiver_pos - thrower_pos

        # Quadratic formula coefficients for intercept time
        # |P + t*V|^2 = (s*t)^2
        # where P = to_receiver, V = receiver_velocity, s = ball_speed
        #
        # Expanding: |P|^2 + 2*t*(P·V) + t^2*|V|^2 = s^2*t^2
        # Rearranging: (|V|^2 - s^2)*t^2 + 2*(P·V)*t + |P|^2 = 0

        v_squared = receiver_velocity.dot(receiver_velocity)
        s_squared = ball_speed * ball_speed
        p_dot_v = to_receiver.dot(receiver_velocity)
        p_squared = to_receiver.dot(to_receiver)

        a = v_squared - s_squared
        b = 2 * p_dot_v
        c = p_squared

        # Handle edge cases
        if abs(a) < 0.0001:
            # Receiver speed ≈ ball speed, degenerate case
            if abs(b) < 0.0001:
                # Can't intercept
                flight_time = math.sqrt(p_squared) / ball_speed
                return receiver_pos, flight_time
            flight_time = -c / b
            if flight_time < 0:
                flight_time = math.sqrt(p_squared) / ball_speed
                return receiver_pos, flight_time
        else:
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                # No real solution - throw directly at receiver
                flight_time = math.sqrt(p_squared) / ball_speed
                return receiver_pos, flight_time

            sqrt_disc = math.sqrt(discriminant)
            t1 = (-b + sqrt_disc) / (2 * a)
            t2 = (-b - sqrt_disc) / (2 * a)

            # Take the positive solution (future intercept)
            if t1 > 0 and t2 > 0:
                flight_time = min(t1, t2)
            elif t1 > 0:
                flight_time = t1
            elif t2 > 0:
                flight_time = t2
            else:
                # Both negative - throw directly
                flight_time = math.sqrt(p_squared) / ball_speed
                return receiver_pos, flight_time

        # Calculate intercept point
        intercept = receiver_pos + receiver_velocity * flight_time

        return intercept, flight_time

    def throw_ball(
        self,
        ball: Ball,
        thrower: Player,
        target_receiver: Player,
        clock: Clock,
        anticipated_target_pos: Optional[Vec2] = None,
        expected_receiver_velocity: Optional[Vec2] = None,
        throw_type_override: Optional[ThrowType] = None,
    ) -> ThrowResult:
        """Execute a throw to a receiver.

        Calculates the true intercept point where ball and receiver will meet,
        accounting for receiver movement. Selects appropriate throw type based
        on distance and applies realistic ball physics.

        Args:
            ball: The football
            thrower: Player throwing (usually QB)
            target_receiver: Intended receiver
            clock: Game clock
            anticipated_target_pos: Route-aware target position override.
                For settling routes (curl, hitch), this is the settle point.
                For continuing routes, this may be a lead point.
            expected_receiver_velocity: Override receiver velocity for lead calculation.
                Use when receiver's route is complete but they should continue running.
            throw_type_override: Force a specific throw type

        Returns:
            ThrowResult with throw details
        """
        self.ball = ball
        self.target_receiver_id = target_receiver.id
        self.throw_start_time = clock.current_time

        # Get receiver velocity (use expected if provided)
        receiver_velocity = expected_receiver_velocity if expected_receiver_velocity else target_receiver.velocity
        receiver_speed = receiver_velocity.length()

        # Initial distance estimate for throw type selection
        # Use anticipated target if provided, otherwise receiver's current position
        initial_target = anticipated_target_pos if anticipated_target_pos else target_receiver.pos
        initial_distance = thrower.pos.distance_to(initial_target)

        # Select throw type based on distance
        throw_type = throw_type_override or self._select_throw_type(initial_distance)

        # Get velocity range for this throw type and QB arm strength
        arm_strength = thrower.attributes.throw_power
        arm_factor = (arm_strength - 50) / 49  # 0 at 50, 1 at 99
        arm_factor = clamp(arm_factor, 0, 1)

        vel_min, vel_max = THROW_VELOCITY[throw_type]
        ball_speed = vel_min + arm_factor * (vel_max - vel_min)

        # Calculate target position
        # If anticipated_target_pos is provided, the QB brain has already calculated
        # the correct lead position accounting for route type (settling vs continuing).
        # Trust that calculation - don't override it.
        if anticipated_target_pos:
            # QB brain provided a specific target - use it directly
            target_pos = anticipated_target_pos
            flight_time = thrower.pos.distance_to(target_pos) / ball_speed
        elif receiver_speed < 0.5:
            # Receiver is stationary - throw directly at them
            target_pos = target_receiver.pos
            flight_time = thrower.pos.distance_to(target_pos) / ball_speed
        else:
            # No anticipated target and receiver is moving - calculate intercept
            target_pos, flight_time = self._calculate_intercept_point(
                thrower.pos, target_receiver.pos, receiver_velocity, ball_speed
            )

        # Calculate peak height based on throw type and distance
        height_min, height_max = THROW_ARC_HEIGHT[throw_type]
        distance = thrower.pos.distance_to(target_pos)
        # Scale height with distance (longer throws = higher arc)
        distance_factor = min(distance / 40.0, 1.0)  # Max at 40 yards
        peak_height = height_min + distance_factor * (height_max - height_min)

        # Apply accuracy variance
        accuracy = thrower.attributes.throw_accuracy
        accuracy_factor = (accuracy - 50) / 49
        max_variance = BASE_ACCURACY_VARIANCE * (1 - accuracy_factor * 0.8)
        max_variance = clamp(max_variance, MIN_ACCURACY_VARIANCE, BASE_ACCURACY_VARIANCE)

        # Random variance in throw
        variance_x = random.gauss(0, max_variance / 2)
        variance_y = random.gauss(0, max_variance / 2)
        actual_variance = math.sqrt(variance_x ** 2 + variance_y ** 2)

        actual_target = Vec2(
            target_pos.x + variance_x,
            target_pos.y + variance_y,
        )

        # Update ball state
        ball.state = BallState.IN_FLIGHT
        ball.flight_origin = thrower.pos
        ball.flight_target = actual_target
        ball.flight_start_time = clock.current_time
        ball.flight_duration = flight_time
        ball.intended_receiver_id = target_receiver.id
        ball.pos = thrower.pos
        ball.throw_type = throw_type
        ball.peak_height = peak_height

        self.state = PassState.IN_FLIGHT
        self.ball_in_air_ticks = 0
        self.defenders_tracking_ball.clear()

        result = ThrowResult(
            success=True,
            target_pos=target_pos,
            actual_target=actual_target,
            velocity=ball_speed,
            flight_time=flight_time,
            accuracy_variance=actual_variance,
        )
        self.throw_result = result

        # Emit event with throw type info
        throw_desc = {
            ThrowType.BULLET: "bullet pass",
            ThrowType.TOUCH: "touch pass",
            ThrowType.LOB: "lob",
        }[throw_type]
        self._emit_event(
            EventType.THROW,
            thrower.id,
            f"{thrower.name} {throw_desc} to {target_receiver.name} ({distance:.1f} yds, {flight_time:.2f}s)",
            clock,
        )

        return result

    def update(
        self,
        ball: Ball,
        receivers: List[Player],
        defenders: List[Player],
        clock: Clock,
        dt: float,
    ) -> Optional[CatchResolution]:
        """Update ball flight and check for resolution.

        Returns CatchResolution if the pass is resolved this tick.
        """
        if self.state != PassState.IN_FLIGHT:
            return None

        self.ball_in_air_ticks += 1

        # Update ball position
        ball.pos = ball.position_at_time(clock.current_time)

        # Check if ball has arrived
        if ball.has_arrived(clock.current_time):
            return self._resolve_catch(ball, receivers, defenders, clock)

        return None

    def _resolve_catch(
        self,
        ball: Ball,
        receivers: List[Player],
        defenders: List[Player],
        clock: Clock,
    ) -> CatchResolution:
        """Resolve the catch when ball arrives."""
        target_pos = ball.flight_target

        # Find target receiver
        target_receiver = None
        for r in receivers:
            if r.id == self.target_receiver_id:
                target_receiver = r
                break

        if not target_receiver:
            # Receiver not found - incomplete
            ball.state = BallState.DEAD
            self.state = PassState.RESOLVED
            ctx = CatchContext(
                receiver_dist_to_ball=float("inf"),
                defender_dist_to_ball=float("inf"),
                throw_accuracy=0.0,
                is_contested=False,
                receiver_catch_rating=0,
                defender_coverage_rating=0,
                separation=0.0,
            )
            return CatchResolution(
                result=CatchResult.INCOMPLETE,
                probability=1.0,
                catch_probability=0.0,
                int_probability=0.0,
                context=ctx,
                roll=0.0,
            )

        # Calculate distances
        receiver_dist = target_receiver.pos.distance_to(target_pos)

        # Find closest defender
        closest_defender = None
        defender_dist = float("inf")
        for d in defenders:
            dist = d.pos.distance_to(target_pos)
            if dist < defender_dist:
                defender_dist = dist
                closest_defender = d

        # Is it contested?
        is_contested = defender_dist <= CONTESTED_CATCH_RADIUS

        # Calculate throw accuracy (based on variance)
        accuracy_variance = self.throw_result.accuracy_variance if self.throw_result else 0
        throw_accuracy = 1.0 - clamp(accuracy_variance / BASE_ACCURACY_VARIANCE, 0, 1)

        # Build context
        ctx = CatchContext(
            receiver_dist_to_ball=receiver_dist,
            defender_dist_to_ball=defender_dist,
            throw_accuracy=throw_accuracy,
            is_contested=is_contested,
            receiver_catch_rating=target_receiver.attributes.catching,
            defender_coverage_rating=closest_defender.attributes.man_coverage if closest_defender else 50,
            separation=defender_dist - receiver_dist,
        )

        # Resolve catch
        resolution = self._calculate_catch(ctx)

        # Update ball and player state based on result
        if resolution.result == CatchResult.COMPLETE:
            ball.state = BallState.HELD
            ball.carrier_id = target_receiver.id
            ball.pos = target_receiver.pos
            target_receiver.has_ball = True

            self._emit_event(
                EventType.CATCH,
                target_receiver.id,
                f"{target_receiver.name} catches the ball ({receiver_dist:.1f}yd reach)",
                clock,
            )

        elif resolution.result == CatchResult.INTERCEPTION:
            ball.state = BallState.HELD
            ball.carrier_id = closest_defender.id if closest_defender else None
            ball.pos = closest_defender.pos if closest_defender else target_pos
            if closest_defender:
                closest_defender.has_ball = True

            defender_name = closest_defender.name if closest_defender else "Defender"
            self._emit_event(
                EventType.INTERCEPTION,
                closest_defender.id if closest_defender else None,
                f"INTERCEPTION by {defender_name}!",
                clock,
            )

        else:  # INCOMPLETE
            ball.state = BallState.DEAD
            ball.pos = target_pos

            self._emit_event(
                EventType.INCOMPLETE,
                target_receiver.id,
                f"Pass incomplete to {target_receiver.name}",
                clock,
            )

        self.state = PassState.RESOLVED
        return resolution

    def _calculate_catch(self, ctx: CatchContext) -> CatchResolution:
        """Calculate catch probabilities and resolve outcome."""
        # Reach probability
        reach_prob = logistic(
            ctx.receiver_dist_to_ball,
            center=REACH_FALLOFF_CENTER,
            rate=REACH_FALLOFF_RATE,
        )

        # Ball uncatchable
        if reach_prob < 0.1:
            return CatchResolution(
                result=CatchResult.INCOMPLETE,
                probability=1.0,
                catch_probability=0.0,
                int_probability=0.0,
                context=ctx,
                roll=0.0,
            )

        if ctx.is_contested:
            return self._resolve_contested(ctx, reach_prob)
        else:
            return self._resolve_uncontested(ctx, reach_prob)

    def _resolve_contested(self, ctx: CatchContext, reach_prob: float) -> CatchResolution:
        """Resolve contested catch."""
        catch_skill = ctx.receiver_catch_rating / 100
        cover_skill = ctx.defender_coverage_rating / 100

        # Continuous rating modifier for catch vs coverage matchup
        rating_mod = get_matchup_modifier(
            ctx.receiver_catch_rating,
            ctx.defender_coverage_rating,
        )

        # Contest factor (includes rating modifier)
        contest_factor = (
            CONTEST_BASE
            + ctx.separation * CONTEST_SEPARATION_WEIGHT
            + (catch_skill - cover_skill) * CONTEST_SKILL_WEIGHT
            + rating_mod  # Continuous rating bonus/penalty
        )
        contest_factor = clamp(contest_factor, 0.1, 0.9)

        # Interception chance
        if ctx.separation < 0:  # Defender has position
            int_chance = INT_BASE_CHANCE * (1 + (cover_skill - 0.7) * 1.2)
            int_chance += abs(ctx.separation) * 0.1
            int_chance = clamp(int_chance, INT_MIN_CHANCE, INT_MAX_CHANCE)
        else:
            int_chance = INT_MIN_CHANCE

        # Final probabilities
        catch_prob = reach_prob * contest_factor * (1 - int_chance)
        int_prob = reach_prob * (1 - contest_factor) * int_chance

        # Roll
        roll = random.random()

        if roll < catch_prob:
            result = CatchResult.COMPLETE
            probability = catch_prob
        elif roll < catch_prob + (1 - catch_prob - int_prob):
            result = CatchResult.INCOMPLETE
            probability = 1 - catch_prob - int_prob
        else:
            result = CatchResult.INTERCEPTION
            probability = int_prob

        return CatchResolution(
            result=result,
            probability=probability,
            catch_probability=catch_prob,
            int_probability=int_prob,
            context=ctx,
            roll=roll,
        )

    def _resolve_uncontested(self, ctx: CatchContext, reach_prob: float) -> CatchResolution:
        """Resolve uncontested catch."""
        catch_skill = ctx.receiver_catch_rating / 100
        base_catch = UNCONTESTED_BASE_CATCH + catch_skill * UNCONTESTED_SKILL_BONUS

        # Accuracy bonus
        accuracy_mod = (ctx.throw_accuracy - 0.5) * 0.06
        base_catch += accuracy_mod

        # Depth penalty - deeper passes are harder to complete
        # Calculate throw distance from velocity and flight time
        throw_depth = 0.0
        if self.throw_result:
            throw_depth = self.throw_result.velocity * self.throw_result.flight_time
        depth_penalty = (throw_depth / 10.0) * DEPTH_CATCH_PENALTY_PER_10YDS
        base_catch -= depth_penalty

        catch_prob = clamp(reach_prob * base_catch, 0.15, 0.92)

        # Small interception chance even on uncontested (bad reads, tipped balls)
        # Increases with depth
        int_prob = 0.01 + (throw_depth / 40.0) * 0.03  # 1-4% based on depth
        int_prob = clamp(int_prob, 0.01, 0.05)

        roll = random.random()

        if roll < catch_prob:
            result = CatchResult.COMPLETE
            probability = catch_prob
        elif roll < catch_prob + int_prob:
            result = CatchResult.INTERCEPTION
            probability = int_prob
        else:
            result = CatchResult.INCOMPLETE
            probability = 1 - catch_prob - int_prob

        return CatchResolution(
            result=result,
            probability=probability,
            catch_probability=catch_prob,
            int_probability=int_prob,
            context=ctx,
            roll=roll,
        )

    def get_defender_ball_tracking(
        self,
        defender: Player,
        ball: Ball,
        clock: Clock,
    ) -> Tuple[Optional[Vec2], str]:
        """Get target position for defender tracking the ball.

        Returns (target_position, reasoning) or (None, reasoning) if not tracking.
        """
        if self.state != PassState.IN_FLIGHT:
            return None, "Ball not in flight"

        # Reaction delay
        if self.ball_in_air_ticks < BALL_TRACK_REACTION_TICKS:
            return None, f"Reacting to throw ({self.ball_in_air_ticks}/{BALL_TRACK_REACTION_TICKS} ticks)"

        # Track to ball landing spot
        target = ball.flight_target
        if target is None:
            return None, "No ball target"

        self.defenders_tracking_ball.add(defender.id)

        return target, f"Tracking ball to ({target.x:.1f}, {target.y:.1f})"

    def should_defender_track_ball(self, defender: Player, ball: Ball) -> bool:
        """Check if defender should abandon coverage to track ball."""
        if self.state != PassState.IN_FLIGHT:
            return False

        if self.ball_in_air_ticks < BALL_TRACK_REACTION_TICKS:
            return False

        # Distance to ball target
        if ball.flight_target is None:
            return False

        dist_to_target = defender.pos.distance_to(ball.flight_target)

        # Track if within reasonable range (15 yards)
        return dist_to_target < 15.0

    def reset(self):
        """Reset for new play."""
        self.state = PassState.PRE_THROW
        self.ball = None
        self.throw_start_time = 0.0
        self.target_receiver_id = None
        self.throw_result = None
        self.defenders_tracking_ball.clear()
        self.ball_in_air_ticks = 0

    def _emit_event(
        self,
        event_type: EventType,
        player_id: Optional[str],
        description: str,
        clock: Clock,
    ):
        """Emit a passing event."""
        self.event_bus.emit_simple(
            event_type=event_type,
            tick=clock.tick_count,
            time=clock.current_time,
            player_id=player_id,
            description=description,
        )

    def evaluate_receivers(
        self,
        receivers: List[Player],
        defenders: List[Player],
        route_assignments: Optional[Dict[str, Any]] = None,
    ) -> List[ReceiverWindow]:
        """Evaluate all receivers and return their throw windows.

        Args:
            receivers: List of receiver players
            defenders: List of defender players
            route_assignments: Optional dict mapping player_id to RouteAssignment
                              (for route phase info)

        Returns list sorted by read_order (progression order).
        """
        windows = []

        for receiver in receivers:
            # Find nearest defender to this receiver
            nearest_defender = None
            min_dist = float("inf")

            for defender in defenders:
                dist = receiver.pos.distance_to(defender.pos)
                if dist < min_dist:
                    min_dist = dist
                    nearest_defender = defender

            separation = min_dist

            # Score is based on separation (used for final decision)
            score = separation

            # Bonus for receivers moving (in their route)
            if receiver.velocity.length() > 3.0:
                score += 0.5

            # Get route phase info if available
            route_phase = ""
            at_or_past_break = False
            if route_assignments and receiver.id in route_assignments:
                assignment = route_assignments[receiver.id]
                route_phase = assignment.phase.value if hasattr(assignment.phase, 'value') else str(assignment.phase)
                # Consider at break if in BREAK, POST_BREAK, or COMPLETE phase
                at_or_past_break = route_phase in ("break", "post_break", "complete")

            windows.append(ReceiverWindow(
                receiver=receiver,
                separation=separation,
                nearest_defender=nearest_defender,
                score=score,
                route_phase=route_phase,
                at_or_past_break=at_or_past_break,
            ))

        # Sort by read_order (1st read first, then 2nd, etc.)
        windows.sort(key=lambda w: w.receiver.read_order)
        return windows

    def should_throw(
        self,
        receivers: List[Player],
        defenders: List[Player],
        clock: Clock,
        route_assignments: Optional[Dict[str, Any]] = None,
    ) -> Optional[Player]:
        """Decide if QB should throw and to whom using read progression.

        The QB follows his reads in order based on route timing:
        1. Check first read - if they've hit their break AND are open, throw it
        2. If first read covered or not at break, check next read
        3. Continue through progression
        4. If all reads covered and out of time, throw to best available

        Args:
            receivers: List of receiver players
            defenders: List of defender players
            clock: Game clock
            route_assignments: Optional dict mapping player_id to RouteAssignment

        Returns the target receiver if should throw, None otherwise.
        """
        # Don't throw too early
        if clock.current_time < MIN_THROW_TIME:
            return None

        # Already threw or resolved
        if self.state != PassState.PRE_THROW:
            return None

        windows = self.evaluate_receivers(receivers, defenders, route_assignments)
        if not windows:
            return None

        current_time = clock.current_time

        # Go through read progression in order
        for window in windows:
            # Check if receiver has hit their route break (timing based on actual route)
            # If we don't have route info, use a fallback based on time
            if not window.at_or_past_break:
                # Route hasn't developed yet - skip this read for now
                # But allow it if we're running out of time
                if current_time < MAX_HOLD_TIME - 1.0:
                    continue

            # Check if this receiver is open
            if window.separation >= OPEN_THRESHOLD:
                # Wide open - throw it!
                return window.receiver

            # Check if contested but throwable
            if window.separation >= CONTESTED_THRESHOLD:
                # Contested but can make the throw
                return window.receiver

            # This read is covered - continue to next read
            # (implicit continue to next iteration)

        # All reads covered or not developed - check if we're running out of time
        if current_time >= MAX_HOLD_TIME - 0.5:
            # Pressure coming - throw to best available who's at their break
            available = [w for w in windows if w.at_or_past_break]
            if available:
                best = max(available, key=lambda w: w.separation)
                if best.separation >= COVERED_THRESHOLD:
                    return best.receiver

        # Forced throw - out of time, throw to anyone
        if current_time >= MAX_HOLD_TIME:
            best = max(windows, key=lambda w: w.separation)
            return best.receiver

        return None
