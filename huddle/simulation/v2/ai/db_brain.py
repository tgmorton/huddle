"""Defensive Back Brain - Decision-making for CBs and Safeties.

PREVENTION-FIRST PHILOSOPHY:
The goal is to PREVENT COMPLETIONS and PREVENT YARDS. We don't "cover"
receivers - we take away throws. Position between receiver and where
the ball will be, not between receiver and QB.

- Coverage = prevent the catch by taking away the throw
- Ball reaction = make a play (breakup or INT)
- Run support = prevent yards (fill gap, make tackle)
- Receivers are threats to prevent, not players to beat

Coverage Types: PRESS → TRAIL or ZONE_DROP → BALL_REACTION → TACKLE
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import DBContext
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from ..core.trace import get_trace_system, TraceCategory
from ..core.variance import recognition_delay as apply_recognition_variance
from ..core.reads import (
    BrainType,
    get_awareness_accuracy,
    get_decision_making_accuracy,
)
from ..core.read_registry import get_read_registry


# =============================================================================
# Trace Helper
# =============================================================================

def _trace(world: WorldState, msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace for this DB."""
    trace = get_trace_system()
    trace.trace(world.me.id, world.me.name, category, msg)


# =============================================================================
# DB Enums
# =============================================================================

class CoverageTechnique(str, Enum):
    """Coverage technique being used."""
    PRESS = "press"
    OFF_MAN = "off_man"
    ZONE = "zone"


class DBPhase(str, Enum):
    """Current phase of DB coverage.

    PREVENTION-FIRST: Each phase is about taking away the throw.
    """
    PRE_SNAP = "pre_snap"
    JAM = "jam"               # Disrupt timing to prevent quick throw
    BACKPEDAL = "backpedal"   # Maintain leverage to prevent deep throw
    TRANSITION = "transition"
    TRAIL = "trail"           # Stay between receiver and where ball goes
    ZONE_DROP = "zone_drop"   # Take away zone, prevent completion
    BALL_TRACKING = "ball_tracking"  # Prevent catch or create turnover
    RUN_SUPPORT = "run_support"      # Prevent yards
    RALLY = "rally"           # Prevent more yards after catch


class BallReaction(str, Enum):
    """How to react to ball in air."""
    PLAY_BALL = "play_ball"     # Go for INT
    PLAY_RECEIVER = "play_receiver"  # PBU through hands
    RALLY = "rally"             # Can't affect, tackle


class ZoneType(str, Enum):
    """Zone assignment for zone coverage."""
    DEEP_THIRD = "deep_third"
    DEEP_HALF = "deep_half"
    FLAT = "flat"
    QUARTER = "quarter"


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class DBState:
    """Tracked state for DB decision-making."""
    phase: DBPhase = DBPhase.PRE_SNAP
    coverage_type: CoverageTechnique = CoverageTechnique.OFF_MAN
    receiver_id: Optional[str] = None
    zone_assignment: Optional[ZoneType] = None
    in_phase: bool = True  # In-phase with receiver
    separation: float = 0.0
    cushion: float = 7.0  # Starting cushion
    hip_direction: Optional[Vec2] = None
    jam_attempted: bool = False
    # Break recognition (cognitive delay before DB "sees" the route break)
    has_recognized_break: bool = False
    recognition_timer: float = 0.0
    break_recognition_delay: float = 0.0
    # Throw reaction (cognitive delay before DB "sees" the throw)
    throw_detected_at: Optional[float] = None
    has_reacted_to_throw: bool = False
    throw_reaction_delay: float = 0.0
    # Zone threat detection (cognitive delay before DB "sees" threat in zone)
    # "Psychic Zone" prevention - DB needs time to detect and react to threats
    zone_threat_id: Optional[str] = None
    zone_threat_detected_at: Optional[float] = None
    zone_threat_reaction_delay: float = 0.0
    has_reacted_to_zone_threat: bool = False


_db_states: dict[str, DBState] = {}


def _get_state(player_id: str) -> DBState:
    if player_id not in _db_states:
        _db_states[player_id] = DBState()
    return _db_states[player_id]


def _reset_state(player_id: str) -> None:
    _db_states[player_id] = DBState()


# =============================================================================
# Helper Functions
# =============================================================================

def _is_in_field_of_view(
    my_pos: Vec2,
    my_facing: Vec2,
    target_pos: Vec2,
    fov_degrees: float = 160.0,
) -> bool:
    """Check if a target is within the defender's field of view.

    "Psychic Zone" prevention: DBs cannot instantly detect threats behind them.
    They need to be facing roughly toward the threat to see it.

    Args:
        my_pos: Defender position
        my_facing: Defender facing direction (normalized)
        target_pos: Target to check
        fov_degrees: Field of view angle (default 160 degrees = 80 degrees each side)

    Returns:
        True if target is within field of view
    """
    to_target = target_pos - my_pos
    if to_target.length() < 0.1:
        return True  # Target is on top of us

    to_target_normalized = to_target.normalized()

    # Dot product gives cosine of angle between facing and to_target
    # 1.0 = directly in front, 0.0 = perpendicular, -1.0 = directly behind
    dot = my_facing.dot(to_target_normalized) if my_facing.length() > 0.1 else 0.0

    # Convert FOV to cosine threshold
    # cos(80 degrees) ≈ 0.17 for 160 degree FOV
    import math
    half_fov_radians = math.radians(fov_degrees / 2)
    cos_threshold = math.cos(half_fov_radians)

    return dot >= cos_threshold


def _calculate_zone_threat_delay(awareness: int, in_fov: bool) -> float:
    """Calculate reaction delay for detecting a zone threat.

    "Psychic Zone" prevention: DBs need time to process threats entering their zone.
    Delay is longer if threat is outside FOV (must turn head/body first).

    Args:
        awareness: DB's awareness attribute (0-99)
        in_fov: Is the threat in the defender's field of view?

    Returns:
        Reaction delay in seconds
    """
    # Base delay: 0.15s for elite (99 awareness) to 0.4s for low (50 awareness)
    # Elite DBs process zone threats faster
    awareness_factor = (99 - awareness) / 49  # 0.0 for elite, 1.0 for low
    base_delay = 0.15 + awareness_factor * 0.25

    # Out of FOV penalty: must turn to see the threat
    # Adds 0.2-0.4s depending on awareness
    if not in_fov:
        fov_penalty = 0.2 + awareness_factor * 0.2
        base_delay += fov_penalty

    return base_delay


def _find_assigned_receiver(world: WorldState) -> Optional[PlayerView]:
    """Find assigned receiver, with situational fallback.

    Hybrid coverage system:
    1. First check PlayConfig assignment (world.me.target_id)
    2. If no assignment or assigned receiver not found, fall back to nearest
    """
    my_pos = world.me.pos

    # First: Check PlayConfig assignment from coverage_system
    if world.me.target_id:
        for opp in world.opponents:
            if opp.id == world.me.target_id:
                return opp  # Follow assignment

    # Fallback: Assignment missing or receiver not found - use nearest WR/TE
    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        if opp.position in (Position.WR, Position.TE):
            dist = opp.pos.distance_to(my_pos)
            if dist < closest_dist:
                closest_dist = dist
                closest = opp

    return closest


def _calculate_coverage_separation(my_pos: Vec2, receiver: PlayerView) -> float:
    """Calculate separation from receiver."""
    return my_pos.distance_to(receiver.pos)


def _am_in_phase(world: WorldState, receiver: PlayerView) -> bool:
    """Check if we're in-phase with the receiver."""
    my_pos = world.me.pos
    my_vel = world.me.velocity

    dist = my_pos.distance_to(receiver.pos)

    # In phase if close and matching direction
    if dist < 2.0:
        if my_vel.length() > 0 and receiver.velocity.length() > 0:
            dot = my_vel.normalized().dot(receiver.velocity.normalized())
            if dot > 0.5:  # Moving same direction
                return True

    return dist < 1.5


# =============================================================================
# Break Recognition (Cognitive Delay)
# =============================================================================

# Route difficulty affects how quickly DB recognizes the break
ROUTE_RECOGNITION_DIFFICULTY = {
    'slant': 0.08,      # Quick break, hard to read
    'out': 0.10,        # Requires hip flip
    'in': 0.08,         # Quick break
    'curl': 0.05,       # Easier (receiver slowing)
    'hitch': 0.05,      # Easier (receiver stops)
    'comeback': 0.06,   # Receiver slowing then cutting
    'post': 0.12,       # Break happens at speed, deep
    'corner': 0.14,     # Double-move quality
    'go': 0.0,          # No break to recognize
    'seam': 0.04,       # Straight up, easy read
    'flat': 0.03,       # Short, easy
    'wheel': 0.10,      # Deceptive route
    'dig': 0.09,        # Deep in-cut
}


def _get_break_recognition_delay(world: WorldState, route_type: str) -> float:
    """Calculate time before DB recognizes route break.

    Based on:
    - DB's play_recognition attribute (higher = faster recognition)
    - Route difficulty (some breaks are harder to read)
    - Variance from human factors (attention, fatigue, pressure)

    Returns delay in seconds.
    """
    base_delay = 0.12  # Minimum reaction time

    # Play recognition affects how quickly they read the break
    # 75 = average, 95 = elite, 60 = poor
    play_rec = getattr(world.me.attributes, 'play_recognition', 75)
    awareness = getattr(world.me.attributes, 'awareness', play_rec)

    # Higher play_rec = less delay
    # Range: 95 play_rec -> 0.0 extra delay, 60 play_rec -> 0.28 extra delay
    recognition_modifier = (90 - play_rec) / 100 * 0.4
    recognition_modifier = max(0.0, recognition_modifier)  # Can't be negative

    # Route difficulty
    route_mod = ROUTE_RECOGNITION_DIFFICULTY.get(route_type.lower(), 0.06)

    # Calculate deterministic base
    deterministic_delay = base_delay + recognition_modifier + route_mod

    # Apply variance based on awareness (adds human unpredictability)
    # Higher awareness = tighter variance around the base delay
    return apply_recognition_variance(deterministic_delay, awareness)


def _detect_receiver_break(world: WorldState, receiver: PlayerView) -> bool:
    """Detect if receiver has started their route break.

    Uses route_phase from WorldState if available, otherwise
    detects break from velocity change.
    """
    # Check if WorldState has route info (receiver perspective)
    # We're the DB, so we need to detect break from observation

    # Method 1: Significant direction change
    if receiver.velocity.length() > 2.0:
        # Check if receiver is cutting (velocity not aligned with position change)
        # A break looks like: running one way, then sharply changing
        # We can't see their facing directly, but rapid direction changes indicate break
        pass

    # Method 2: Use route timing (after ~1 second, most breaks happen)
    # This is a simplification - ideally we'd track receiver velocity history
    if world.time_since_snap > 0.8:  # Most breaks happen 0.8-1.5s after snap
        return True

    return False


def _estimate_route_type_from_movement(receiver: PlayerView) -> str:
    """Estimate route type from receiver movement pattern."""
    if receiver.velocity.length() < 1.0:
        return "curl"  # Receiver stopped/slowing = curl/hitch

    vel = receiver.velocity.normalized()

    # Mostly vertical = go/seam
    if abs(vel.y) > 0.9:
        return "go"

    # Diagonal = post/corner/out/in
    if vel.x > 0.5:
        return "out" if vel.y < 0.5 else "corner"
    elif vel.x < -0.5:
        return "in" if vel.y < 0.5 else "post"

    return "slant"  # Default for angled routes


# =============================================================================
# Throw Reaction Delay (Cognitive delay before DB tracks ball)
# =============================================================================

def _calculate_throw_reaction_delay(world: WorldState) -> float:
    """Calculate time before DB reacts to throw.

    Factors:
    - Base human reaction time (~200-300ms minimum)
    - Awareness attribute (higher = faster reaction)
    - Can they see the QB? (facing direction matters)
    - Distance from QB (closer = sees faster)

    Returns delay in seconds.
    """
    # Base reaction time - humans can't react faster than ~150ms
    base_delay = 0.20

    # Awareness affects how quickly they pick up the throw
    # 75 = average, 95 = elite, 60 = poor
    awareness = getattr(world.me.attributes, 'awareness', 75)

    # Higher awareness = less delay
    # Range: 95 awareness -> 0.05 extra delay, 60 awareness -> 0.28 extra delay
    awareness_modifier = (90 - awareness) / 100 * 0.4
    awareness_modifier = max(0.0, awareness_modifier)

    # Can DB see the QB? Check facing direction
    qb = None
    for opp in world.opponents:
        if opp.position == Position.QB:
            qb = opp
            break

    facing_modifier = 0.0
    if qb:
        # Direction to QB
        to_qb = (qb.pos - world.me.pos).normalized()
        # DB's facing direction
        facing = world.me.facing

        # Dot product: 1 = facing QB, -1 = facing away
        dot = facing.dot(to_qb) if facing.length() > 0 else 0

        if dot < 0:
            # Facing away from QB - significant delay (must turn + see)
            facing_modifier = 0.15
        elif dot < 0.5:
            # Partially turned - moderate delay
            facing_modifier = 0.08

    # Distance modifier - farther from QB means harder to see release
    dist_modifier = 0.0
    if qb:
        dist_to_qb = world.me.pos.distance_to(qb.pos)
        if dist_to_qb > 20:
            dist_modifier = 0.05  # Very far, hard to see release
        elif dist_to_qb > 15:
            dist_modifier = 0.02

    return base_delay + awareness_modifier + facing_modifier + dist_modifier


def _can_track_ball_yet(world: WorldState, state: 'DBState') -> bool:
    """Check if enough time has passed to react to the throw.

    Returns True if DB can start tracking the ball.
    """
    if state.has_reacted_to_throw:
        return True

    # First time seeing ball in air - calculate delay
    if state.throw_detected_at is None:
        state.throw_detected_at = world.current_time
        state.throw_reaction_delay = _calculate_throw_reaction_delay(world)
        return False

    # Check if delay has passed
    elapsed = world.current_time - state.throw_detected_at
    if elapsed >= state.throw_reaction_delay:
        state.has_reacted_to_throw = True
        return True

    return False


# =============================================================================
# Read System Integration - Route Anticipation
# =============================================================================

def _get_receiver_release_direction(receiver: PlayerView, los_y: float) -> str:
    """Determine receiver's release direction from the line."""
    if receiver.pos.y < los_y + 3:  # Still near LOS
        if receiver.velocity.x > 1.0:
            return "outside" if receiver.pos.x > 0 else "inside"
        elif receiver.velocity.x < -1.0:
            return "inside" if receiver.pos.x > 0 else "outside"
        elif receiver.velocity.y > 2.0:
            return "vertical"
    return "unknown"


def _apply_route_anticipation_read(
    world: WorldState,
    state: 'DBState',
    receiver: PlayerView,
) -> Optional[tuple[str, str]]:
    """Apply read system for route anticipation.

    Uses DB's awareness and play_recognition to anticipate routes
    based on receiver release and formation cues.

    Returns:
        (adjustment, reasoning) if read applies, None otherwise
    """
    # Get DB attributes
    awareness = getattr(world.me.attributes, 'awareness', 70)
    play_rec = getattr(world.me.attributes, 'play_recognition', 70)

    # Check if DB meets minimum awareness for read system
    awareness_acc, awareness_time = get_awareness_accuracy(awareness)
    if awareness_acc == 0.0:
        return None  # Read system disabled for low awareness

    # Too early in play for reads to apply
    if world.time_since_snap < awareness_time:
        return None

    # Get reads for coverage situation
    registry = get_read_registry()
    coverage_type = "man" if state.coverage_type in (
        CoverageTechnique.PRESS, CoverageTechnique.OFF_MAN
    ) else "zone"

    # Determine concept based on coverage technique
    concept = "press" if state.coverage_type == CoverageTechnique.PRESS else "coverage"

    reads = registry.get_reads_for_concept(concept, coverage_type, BrainType.DB)
    if not reads:
        return None

    # Check receiver release direction
    release_dir = _get_receiver_release_direction(receiver, world.los_y)

    # Find matching read based on release
    for read in reads:
        if read.min_awareness > awareness:
            continue
        if read.min_decision_making > play_rec:
            continue

        # Match release-based reads
        for trigger in read.triggers:
            trigger_val = trigger.trigger_type.value

            if release_dir == "inside" and trigger_val == "inside_release":
                primary = read.get_primary_outcome()
                if primary:
                    _trace(world, f"[READ] {read.name}: {primary.reasoning}")
                    return (primary.adjustment or "wall_inside", primary.reasoning)

            elif release_dir == "outside" and trigger_val == "outside_release":
                primary = read.get_primary_outcome()
                if primary:
                    _trace(world, f"[READ] {read.name}: {primary.reasoning}")
                    return (primary.adjustment or "leverage_outside", primary.reasoning)

            elif release_dir == "vertical" and trigger_val == "vertical_stem":
                primary = read.get_primary_outcome()
                if primary:
                    _trace(world, f"[READ] {read.name}: {primary.reasoning}")
                    return (primary.adjustment or "trail_deep", primary.reasoning)

    return None


def _estimate_ball_placement(world: WorldState, ball_target: Vec2) -> str:
    """Estimate ball placement from trajectory.

    Returns:
        'high' - over receiver, harder for DB to intercept
        'low' - under-thrown, DB can undercut
        'back_shoulder' - behind receiver, DB can jump route
        'good' - well-placed, contested
    """
    ball = world.ball
    if not ball or not hasattr(ball, 'velocity') or not ball.velocity:
        return "good"

    # Check ball trajectory angle
    # High arc = high ball, flat = catchable
    vel_y = ball.velocity.y if hasattr(ball.velocity, 'y') else 0
    vel_z = getattr(ball.velocity, 'z', 0) if hasattr(ball, 'velocity') else 0

    # Simplified: use vertical component if available
    if vel_z > 5:
        return "high"
    elif vel_z < -2:
        return "low"

    # Check if ball is behind receiver (back shoulder)
    # Ball target vs receiver momentum
    return "good"


def _decide_ball_reaction(
    world: WorldState,
    receiver: Optional[PlayerView],
    ball_target: Vec2
) -> Tuple[BallReaction, str]:
    """Decide how to react to ball in air using ball-hawking matrix.

    Ball-Hawking Decision Matrix:
    | Separation        | Ball Placement | Action           |
    |-------------------|----------------|------------------|
    | > 2 yards ahead   | Any            | Play ball → INT  |
    | 1-2 yards ahead   | Good           | INT attempt      |
    | 1-2 yards ahead   | High           | PBU              |
    | Even              | Under/behind   | INT attempt      |
    | Even              | Over receiver  | PBU              |
    | Behind < 2 yards  | Any            | Play receiver    |
    | Behind > 2 yards  | Any            | Rally            |

    Returns:
        (reaction_type, reasoning)
    """
    my_pos = world.me.pos

    if not receiver:
        return BallReaction.RALLY, "No receiver to contest"

    my_dist = my_pos.distance_to(ball_target)
    recv_dist = receiver.pos.distance_to(ball_target)

    # Calculate separation (positive = DB ahead/closer, negative = DB behind)
    separation = recv_dist - my_dist

    # Estimate ball placement
    ball_placement = _estimate_ball_placement(world, ball_target)

    # Ball-hawking decision matrix
    if separation > 2.0:
        # DB significantly ahead - go for INT regardless of placement
        return BallReaction.PLAY_BALL, f"Inside position by {separation:.1f}yd, INT opportunity"

    elif separation > 1.0:
        # DB ahead by 1-2 yards - depends on ball placement
        if ball_placement == "high":
            return BallReaction.PLAY_RECEIVER, f"Ahead {separation:.1f}yd but high ball, playing through receiver"
        else:
            return BallReaction.PLAY_BALL, f"Ahead {separation:.1f}yd with catchable ball, INT attempt"

    elif separation > -1.0:
        # Even position - depends on ball placement
        if ball_placement in ("low", "back_shoulder"):
            return BallReaction.PLAY_BALL, f"Even position, {ball_placement} ball, INT attempt"
        else:
            return BallReaction.PLAY_RECEIVER, "Even position, well-thrown, contesting catch"

    elif separation > -2.0:
        # DB behind by < 2 yards - play through receiver for PBU
        return BallReaction.PLAY_RECEIVER, f"Behind {-separation:.1f}yd, playing through receiver"

    else:
        # DB behind by > 2 yards - rally to tackle after catch
        return BallReaction.RALLY, f"Out of position by {-separation:.1f}yd, rallying to tackle"


def _get_zone_position(world: WorldState, zone: ZoneType) -> Vec2:
    """Get target position for zone coverage."""
    los = world.los_y
    my_pos = world.me.pos

    if zone == ZoneType.DEEP_THIRD:
        # Cover deep third of field
        x = my_pos.x * 0.5  # Shade toward sideline
        return Vec2(x, los + 20)

    elif zone == ZoneType.DEEP_HALF:
        # Cover deep half
        x = 15 if my_pos.x > 0 else -15
        return Vec2(x, los + 18)

    elif zone == ZoneType.FLAT:
        # Cover flat
        x = 20 if my_pos.x > 0 else -20
        return Vec2(x, los + 6)

    elif zone == ZoneType.QUARTER:
        # Quarter zone
        x = my_pos.x * 0.7
        return Vec2(x, los + 12)

    return Vec2(my_pos.x, los + 15)


def _detect_run(world: WorldState) -> bool:
    """Detect if this is a run play or ballcarrier running after catch.

    Returns True when any opponent has the ball and is running, including:
    - RB with ball (designed run)
    - QB scramble (no ball = handoff happened)
    - WR/TE with ball after catch (YAC situation)
    """
    for opp in world.opponents:
        # Any ballcarrier triggers run support (including WR after catch)
        if opp.has_ball and opp.position != Position.QB:
            return True
        # QB scramble detection (ball handed off)
        if opp.position == Position.QB and not opp.has_ball and world.time_since_snap > 0.5:
            return True

    return False


def _find_ballcarrier(world: WorldState) -> Optional[PlayerView]:
    """Find the ballcarrier."""
    for opp in world.opponents:
        if opp.has_ball:
            return opp
    return None


# =============================================================================
# Main Brain Function
# =============================================================================

def db_brain(world: DBContext) -> BrainDecision:
    """Defensive back brain - for CBs and Safeties.

    Args:
        world: DBContext for coverage and ball reaction

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Reset at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

        # Set initial coverage based on position
        if world.me.position == Position.CB:
            state.coverage_type = CoverageTechnique.OFF_MAN
        else:  # Safety
            state.coverage_type = CoverageTechnique.ZONE
            state.zone_assignment = ZoneType.DEEP_HALF

    # Find our receiver
    receiver = _find_assigned_receiver(world)
    if receiver:
        state.receiver_id = receiver.id
        state.separation = _calculate_coverage_separation(world.me.pos, receiver)
        state.in_phase = _am_in_phase(world, receiver)
        _trace(world, f"Coverage: {state.coverage_type.value}, sep={state.separation:.1f}yd, {'in-phase' if state.in_phase else 'trailing'}", TraceCategory.PERCEPTION)

    # =========================================================================
    # Ball In Air - React (with cognitive delay)
    # =========================================================================
    if world.ball.is_in_flight and world.ball.flight_target:
        target = world.ball.flight_target

        # Check if DB has had time to react to the throw
        if not _can_track_ball_yet(world, state):
            # Still processing throw - continue covering receiver
            # This creates the realistic delay before DBs snap to ball
            delay_remaining = state.throw_reaction_delay - (
                world.current_time - (state.throw_detected_at or world.current_time)
            )

            if receiver:
                # Keep covering receiver during reaction delay
                return BrainDecision(
                    move_target=receiver.pos,
                    move_type="sprint",
                    intent="coverage",
                    target_id=receiver.id,
                    reasoning=f"Reacting to throw ({delay_remaining:.2f}s)",
                )
            else:
                # No receiver - hold position while processing
                return BrainDecision(
                    intent="hold",
                    reasoning=f"Processing throw ({delay_remaining:.2f}s)",
                )

        # DB has reacted - now track the ball
        state.phase = DBPhase.BALL_TRACKING
        my_dist = world.me.pos.distance_to(target)
        _trace(world, f"Ball tracking: {my_dist:.1f}yd to target", TraceCategory.PERCEPTION)

        # Is this coming to my receiver?
        if receiver and world.ball.intended_receiver_id == receiver.id:
            reaction, reasoning = _decide_ball_reaction(world, receiver, target)
            _trace(world, f"Ball reaction: {reaction.value} - {reasoning}")

            if reaction == BallReaction.PLAY_BALL:
                return BrainDecision(
                    move_target=target,
                    move_type="sprint",
                    action="intercept",
                    intent="play_ball",
                    reasoning=reasoning,
                )
            elif reaction == BallReaction.PLAY_RECEIVER:
                return BrainDecision(
                    move_target=receiver.pos,
                    move_type="sprint",
                    action="contest",
                    target_id=receiver.id,
                    intent="play_receiver",
                    reasoning=reasoning,
                )
            else:  # Rally
                return BrainDecision(
                    move_target=target,
                    move_type="sprint",
                    intent="rally",
                    reasoning=reasoning,
                )

        # Ball going elsewhere - rally
        return BrainDecision(
            move_target=target,
            move_type="sprint",
            intent="rally",
            reasoning="Ball thrown elsewhere, rallying",
        )

    # =========================================================================
    # Run Support - PREVENT YARDS
    # =========================================================================
    if _detect_run(world):
        state.phase = DBPhase.RUN_SUPPORT
        _trace(world, "Run detected - preventing yards", TraceCategory.PERCEPTION)

        ballcarrier = _find_ballcarrier(world)
        if ballcarrier:
            dist = world.me.pos.distance_to(ballcarrier.pos)

            # Calculate intercept point to PREVENT MORE YARDS
            # NGS Physics: Account for turn penalty if DB needs to redirect
            bc_speed = ballcarrier.velocity.length()
            if bc_speed > 0.1:
                # Base time to reach
                my_speed = 8.0  # Approximate DB sprint speed
                base_time = dist / my_speed

                # Add turn penalty if DB is moving wrong direction
                turn_penalty = 0.0
                my_vel = world.me.velocity
                if my_vel.length() > 2.0:
                    to_bc = (ballcarrier.pos - world.me.pos).normalized()
                    my_dir = my_vel.normalized()
                    dot = max(-1.0, min(1.0, my_dir.dot(to_bc)))
                    turn_angle = abs(math.acos(dot))
                    if turn_angle > 0.3:  # >17 degrees
                        speed_factor = my_vel.length() / 6.0
                        turn_penalty = (turn_angle / 3.14) * 0.5 * speed_factor

                time_to_reach = base_time + turn_penalty
                intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 1.1
            else:
                intercept = ballcarrier.pos

            # All DBs pursue to prevent yards
            if world.me.position in (Position.SS, Position.CB):
                if dist < 3:
                    # Tackle to prevent more yards
                    return BrainDecision(
                        move_target=ballcarrier.pos,
                        move_type="sprint",
                        action="tackle",
                        target_id=ballcarrier.id,
                        intent="tackle",
                        reasoning=f"Tackle to prevent yards ({dist:.1f}yd)",
                    )
                else:
                    # Intercept path to prevent more yards
                    return BrainDecision(
                        move_target=intercept,
                        move_type="sprint",
                        action="pursue",
                        target_id=ballcarrier.id,
                        intent="pursuit",
                        reasoning=f"Closing to prevent yards ({dist:.1f}yd)",
                    )

            # FS - deep pursuit to prevent big gain
            else:
                return BrainDecision(
                    move_target=intercept,
                    move_type="sprint",
                    intent="pursuit",
                    reasoning=f"Preventing big gain ({dist:.1f}yd)",
                )

    # =========================================================================
    # Man Coverage - TAKE AWAY THE THROW
    # =========================================================================
    if state.coverage_type in (CoverageTechnique.PRESS, CoverageTechnique.OFF_MAN):
        if not receiver:
            return BrainDecision(intent="scan", reasoning="No threat to prevent")

        # Press coverage - disrupt timing to prevent quick throw
        if state.coverage_type == CoverageTechnique.PRESS and world.time_since_snap < 0.5:
            state.phase = DBPhase.JAM

            if not state.jam_attempted:
                state.jam_attempted = True
                return BrainDecision(
                    move_target=receiver.pos,
                    move_type="run",
                    action="jam",
                    target_id=receiver.id,
                    intent="press",
                    reasoning="Disrupting release to prevent quick throw",
                )

        # Backpedal phase - maintain leverage to prevent deep throw
        if world.time_since_snap < 1.0:
            state.phase = DBPhase.BACKPEDAL

            # Stay between receiver and where deep throw would go
            cushion_target = receiver.pos + Vec2(0, state.cushion)

            return BrainDecision(
                move_target=cushion_target,
                move_type="backpedal",
                intent="backpedal",
                target_id=receiver.id,
                reasoning=f"Taking away deep throw (cushion: {state.cushion:.1f}yd)",
            )

        # Trail phase - stay between receiver and where ball would go
        state.phase = DBPhase.TRAIL

        # =================================================================
        # Read System - Route Anticipation (before break)
        # =================================================================
        # Elite DBs use reads to anticipate routes before the break happens
        # Check for sideline leverage advantage first
        boundary_leverage = "none"
        if hasattr(world, 'field') and world.field:
            boundary_leverage = world.field.get_leverage_advantage(receiver.pos.x)

        read_result = _apply_route_anticipation_read(world, state, receiver)
        if read_result:
            adjustment, read_reasoning = read_result
            # Apply adjustment based on read
            if adjustment == "wall_inside":
                # Position inside to take away slant/dig
                target = receiver.pos + Vec2(-1.5 if receiver.pos.x > 0 else 1.5, 0.5)
                return BrainDecision(
                    move_target=target,
                    move_type="sprint",
                    intent="anticipate_inside",
                    target_id=receiver.id,
                    reasoning=f"[READ] {read_reasoning}",
                )
            elif adjustment == "leverage_outside":
                # If near sideline, sideline provides outside leverage - play inside instead
                if boundary_leverage == "inside":
                    # Sideline covers outside - shade inside for potential slant/in
                    inside_offset = -1.0 if receiver.pos.x > 0 else 1.0
                    target = receiver.pos + Vec2(inside_offset, 0.5)
                    return BrainDecision(
                        move_target=target,
                        move_type="sprint",
                        intent="leverage_inside_boundary",
                        target_id=receiver.id,
                        reasoning=f"[READ] Boundary leverage - sideline covers outside",
                    )
                else:
                    # Maintain outside leverage for out/corner routes
                    target = receiver.pos + Vec2(1.5 if receiver.pos.x > 0 else -1.5, 0.5)
                    return BrainDecision(
                        move_target=target,
                        move_type="sprint",
                        intent="anticipate_outside",
                        target_id=receiver.id,
                        reasoning=f"[READ] {read_reasoning}",
                    )
            elif adjustment == "trail_deep":
                # Stay on top for vertical routes
                target = receiver.pos + Vec2(0, 2.0)
                return BrainDecision(
                    move_target=target,
                    move_type="sprint",
                    intent="anticipate_deep",
                    target_id=receiver.id,
                    reasoning=f"[READ] {read_reasoning}",
                )

        # =================================================================
        # Break Recognition System (fallback for non-elite DBs)
        # =================================================================
        receiver_breaking = _detect_receiver_break(world, receiver)

        if receiver_breaking and not state.has_recognized_break:
            if state.break_recognition_delay == 0.0:
                route_type = _estimate_route_type_from_movement(receiver)
                state.break_recognition_delay = _get_break_recognition_delay(world, route_type)

            state.recognition_timer += world.dt

            if state.recognition_timer >= state.break_recognition_delay:
                state.has_recognized_break = True
                _trace(world, f"Break recognized after {state.recognition_timer:.2f}s delay")

        # Position to PREVENT the completion
        # Check for sideline leverage advantage
        leverage = "none"
        if hasattr(world, 'field') and world.field:
            leverage = world.field.get_leverage_advantage(receiver.pos.x)

        if state.has_recognized_break:
            lookahead = 0.15
            predicted_pos = receiver.pos + receiver.velocity * lookahead

            if state.in_phase:
                if leverage == "inside":
                    # Use sideline as extra defender - play inside leverage
                    inside_offset = -1.5 if receiver.pos.x > 0 else 1.5
                    target = predicted_pos + Vec2(inside_offset, 0.5)
                    reasoning = f"Inside leverage, sideline covers outside ({state.separation:.1f}yd)"
                else:
                    target = predicted_pos + Vec2(0, 0.5)
                    reasoning = f"In position to prevent completion ({state.separation:.1f}yd)"
            else:
                target = predicted_pos
                reasoning = f"Closing to take away throw ({state.separation:.1f}yd)"
        else:
            if state.in_phase:
                if leverage == "inside":
                    # Play inside leverage early - sideline is our help
                    inside_offset = -1.5 if receiver.pos.x > 0 else 1.5
                    target = receiver.pos + Vec2(inside_offset, 1)
                    reasoning = f"Inside leverage, reading route ({state.separation:.1f}yd)"
                else:
                    target = receiver.pos + Vec2(0, 1)
                    reasoning = f"Reading to prevent completion ({state.separation:.1f}yd)"
            else:
                target = receiver.pos
                reasoning = f"Reacting to prevent completion ({state.recognition_timer:.2f}s)"

        return BrainDecision(
            move_target=target,
            move_type="sprint",
            intent="in_phase" if state.in_phase else "trailing",
            target_id=receiver.id,
            reasoning=reasoning,
        )

    # =========================================================================
    # Zone Coverage - TAKE AWAY THE ZONE
    # "Psychic Zone" prevention: Vision cone + reaction delay for threat detection
    # =========================================================================
    if state.coverage_type == CoverageTechnique.ZONE and state.zone_assignment:
        state.phase = DBPhase.ZONE_DROP

        zone_pos = _get_zone_position(world, state.zone_assignment)
        my_facing = world.me.facing
        awareness = getattr(world.me.attributes, 'awareness', 70)
        current_time = world.time_since_snap

        # Check for threat entering zone WITH vision cone check
        zone_threat = None
        threat_in_fov = False
        for opp in world.opponents:
            if opp.position in (Position.WR, Position.TE):
                if opp.pos.distance_to(zone_pos) < 8:
                    # Check if this threat is in our field of view
                    in_fov = _is_in_field_of_view(world.me.pos, my_facing, opp.pos)
                    zone_threat = opp
                    threat_in_fov = in_fov
                    break

        if zone_threat:
            # "Psychic Zone" prevention: Apply reaction delay based on awareness and FOV
            # DB must "see" and "process" the threat before reacting

            # Check if this is a new threat or the same one we've been tracking
            if state.zone_threat_id != zone_threat.id:
                # New threat detected - start reaction timer
                state.zone_threat_id = zone_threat.id
                state.zone_threat_detected_at = current_time
                state.zone_threat_reaction_delay = _calculate_zone_threat_delay(awareness, threat_in_fov)
                state.has_reacted_to_zone_threat = False

            # Calculate time since threat was detected
            time_since_detection = current_time - (state.zone_threat_detected_at or current_time)

            # Has reaction delay passed?
            if time_since_detection >= state.zone_threat_reaction_delay:
                state.has_reacted_to_zone_threat = True

            if state.has_reacted_to_zone_threat:
                # Reaction complete - break on the threat
                return BrainDecision(
                    move_target=zone_threat.pos,
                    move_type="run",
                    intent="zone_match",
                    target_id=zone_threat.id,
                    reasoning=f"Breaking on threat in {state.zone_assignment.value} (reacted after {time_since_detection:.2f}s)",
                )
            else:
                # Still processing - continue holding zone position
                # If threat is outside FOV, turn to face it
                if not threat_in_fov:
                    return BrainDecision(
                        move_target=zone_pos,
                        move_type="run",
                        intent="zone_drop",
                        facing_direction=(zone_threat.pos - world.me.pos).normalized(),
                        reasoning=f"Turning to see threat in {state.zone_assignment.value} ({time_since_detection:.2f}s/{state.zone_threat_reaction_delay:.2f}s)",
                    )
                else:
                    return BrainDecision(
                        move_target=zone_pos,
                        move_type="run",
                        intent="zone_drop",
                        reasoning=f"Processing threat in {state.zone_assignment.value} ({time_since_detection:.2f}s/{state.zone_threat_reaction_delay:.2f}s)",
                    )
        else:
            # No threat - clear tracking state
            state.zone_threat_id = None
            state.zone_threat_detected_at = None
            state.has_reacted_to_zone_threat = False

        # Position to take away the zone
        return BrainDecision(
            move_target=zone_pos,
            move_type="run",
            intent="zone_drop",
            reasoning=f"Taking away {state.zone_assignment.value}",
        )

    # Default
    return BrainDecision(
        intent="hold",
        reasoning="Holding position",
    )
