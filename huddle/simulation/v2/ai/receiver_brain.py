"""Receiver Brain - Decision-making for WRs and TEs.

SEPARATION-FIRST PHILOSOPHY:
The goal is to GET OPEN (create separation) and GAIN YARDS. The DB is
an obstacle between us and being open - we're not trying to "beat" them,
we're trying to create space for the QB to complete a pass.

- Routes create separation through spacing and timing
- Release/breaks create open windows, not 1v1 victories
- After catch = ballcarrier philosophy (yards toward endzone)
- Contested catches happen when separation failed, not as a goal

Phases: RELEASE → STEM → BREAK → POST_BREAK → CATCH → (Ballcarrier Brain)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from typing import Union
from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import WRContext, RBContext
from ..core.vec2 import Vec2
from ..core.entities import Position, Team, BallState
from ..core.trace import get_trace_system, TraceCategory


# =============================================================================
# Trace Helper
# =============================================================================

def _trace(world: WorldState, msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace for this receiver."""
    trace = get_trace_system()
    trace.trace(world.me.id, world.me.name, category, msg)


# =============================================================================
# Receiver State Enums
# =============================================================================

class RoutePhase(str, Enum):
    """Current phase of route execution.

    SEPARATION-FIRST: Each phase is about creating/maintaining separation.
    """
    PRE_SNAP = "pre_snap"
    RELEASE = "release"      # Create initial separation from LOS
    STEM = "stem"           # Create vertical separation, sell route
    BREAK = "break"         # Create lateral separation with cut
    POST_BREAK = "post_break"  # Maximize separation, find open space
    SCRAMBLE = "scramble"    # Find open space for scramble completion
    BALL_TRACKING = "ball_tracking"  # Secure the completion
    BLOCKING = "blocking"    # Create separation for ballcarrier


class CatchType(str, Enum):
    """Type of catch to attempt."""
    HANDS = "hands"         # Clean catch, hands only
    BODY = "body"           # Secure against body
    HIGH_POINT = "high_point"  # Jump and catch at highest point
    BACK_SHOULDER = "back_shoulder"  # Turn back to ball
    DIG_OUT = "dig_out"     # Low ball, dig out


class ReleaseType(str, Enum):
    """Release technique vs press coverage."""
    SWIM = "swim"           # Arm over defender - best vs inside leverage
    RIP = "rip"             # Arm under defender - best vs outside leverage
    SPEED = "speed"         # Outrun jam - best vs slower DB
    HESITATION = "hesitation"  # Fake inside, go outside - best vs aggressive press
    FREE = "free"           # No press, clean release


class HotRouteType(str, Enum):
    """Hot route conversion types."""
    SLANT = "slant"
    QUICK_OUT = "quick_out"
    SHALLOW_CROSS = "shallow_cross"
    SIGHT_ADJUST = "sight_adjust"


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class ReceiverState:
    """Tracked state for receiver decision-making."""
    route_phase: RoutePhase = RoutePhase.PRE_SNAP
    separation: float = 0.0
    covering_defender_id: Optional[str] = None
    is_target: bool = False
    scramble_mode: bool = False
    break_direction: Optional[Vec2] = None
    on_schedule: bool = True
    last_ball_check_time: float = 0.0
    # Release state
    release_type: ReleaseType = ReleaseType.FREE
    release_complete: bool = False
    # Hot route state
    is_hot: bool = False
    hot_route_type: Optional[HotRouteType] = None
    original_route: str = ""


# Module-level state tracking
_receiver_states: dict[str, ReceiverState] = {}


def _get_state(player_id: str) -> ReceiverState:
    """Get or create state for a receiver."""
    if player_id not in _receiver_states:
        _receiver_states[player_id] = ReceiverState()
    return _receiver_states[player_id]


def _reset_state(player_id: str) -> None:
    """Reset state for a new play."""
    _receiver_states[player_id] = ReceiverState()


# =============================================================================
# Helper Functions
# =============================================================================

def _find_covering_defender(world: WorldState) -> Optional[PlayerView]:
    """Find the nearest defender (obstacle to separation).

    SEPARATION-FIRST: We're not looking for "who to beat" - we're
    identifying what's between us and being open for a completion.
    """
    my_pos = world.me.pos
    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        # DBs and LBs can be in coverage
        if opp.position not in (Position.CB, Position.FS, Position.SS, Position.MLB, Position.OLB, Position.ILB):
            continue

        dist = opp.pos.distance_to(my_pos)
        if dist < closest_dist:
            closest_dist = dist
            closest = opp

    return closest


def _calculate_separation(world: WorldState, defender: Optional[PlayerView]) -> float:
    """Calculate our separation (how open we are for a completion)."""
    if not defender:
        return 10.0  # Wide open

    raw_sep = world.me.pos.distance_to(defender.pos)

    # Adjust for defender position relative to QB
    qb_pos = None
    for tm in world.teammates:
        if tm.position == Position.QB:
            qb_pos = tm.pos
            break

    if qb_pos and defender:
        receiver_to_qb = (qb_pos - world.me.pos).normalized()
        def_to_receiver = (world.me.pos - defender.pos).normalized()

        # Defender trailing = bonus
        if receiver_to_qb.dot(def_to_receiver) > 0.5:
            raw_sep += 1.0
        # Defender undercutting = penalty
        elif receiver_to_qb.dot(def_to_receiver) < -0.3:
            raw_sep -= 0.5

    # Closing speed penalty
    if defender and defender.velocity.length() > 0:
        to_me = (world.me.pos - defender.pos).normalized()
        closing = defender.velocity.dot(to_me)
        if closing > 0:
            raw_sep -= closing * 0.3

    return max(0, raw_sep)


def _is_qb_scrambling(world: WorldState) -> bool:
    """Check if QB is scrambling.

    Scramble = QB moving laterally or forward with speed.
    Dropback = QB moving backward, NOT a scramble.
    """
    for tm in world.teammates:
        if tm.position == Position.QB:
            if not tm.has_ball:
                continue

            vel = tm.velocity
            speed = vel.length()

            # Must be moving with some speed
            if speed < 2.0:
                return False

            # Check direction: scramble = lateral or forward movement
            # Dropback = moving in -Y direction (backward)
            # Scramble = significant X component or positive Y
            if speed > 0.1:
                # Normalize to check direction
                lateral_component = abs(vel.x) / speed
                forward_component = vel.y / speed  # Positive = upfield

                # Scramble if mostly lateral (> 50% of velocity in X)
                # or moving forward/upfield
                if lateral_component > 0.5 or forward_component > 0.3:
                    return True

            return False
    return False


def _find_open_space(world: WorldState) -> Vec2:
    """Find open space for scramble drill.

    SCRAMBLE DRILL RULES (NFL-style):
    1. Get into QB's field of vision (same direction they're rolling)
    2. Find soft spots in the defense (windows between defenders)
    3. Stay past LOS but find open grass
    4. Make yourself an easy target by stopping in clear space
    """
    my_pos = world.me.pos

    # Find QB to understand their roll direction
    qb = None
    for teammate in world.teammates:
        # QB will have a position of QB
        if hasattr(teammate, 'position') and str(teammate.position).upper() in ('QB', 'POSITION.QB'):
            qb = teammate
            break

    # Determine QB's roll direction from their velocity
    qb_rolling_right = False
    qb_rolling_left = False
    if qb and hasattr(qb, 'velocity') and qb.velocity:
        if qb.velocity.x > 1.0:
            qb_rolling_right = True
        elif qb.velocity.x < -1.0:
            qb_rolling_left = True

    # Build candidate positions based on QB's roll direction
    candidates = []

    # If QB rolling right, move to right side of field
    if qb_rolling_right:
        candidates.append(my_pos + Vec2(6, 3))   # Upfield and right (into vision)
        candidates.append(my_pos + Vec2(4, 0))   # Right
        candidates.append(my_pos + Vec2(5, 5))   # Deep right
    # If QB rolling left, move to left side
    elif qb_rolling_left:
        candidates.append(my_pos + Vec2(-6, 3))  # Upfield and left (into vision)
        candidates.append(my_pos + Vec2(-4, 0))  # Left
        candidates.append(my_pos + Vec2(-5, 5))  # Deep left
    else:
        # QB in pocket or scrambling forward - find any open grass
        candidates.append(my_pos + Vec2(5, 3))   # Right diagonal
        candidates.append(my_pos + Vec2(-5, 3))  # Left diagonal
        candidates.append(my_pos + Vec2(0, 6))   # Straight upfield
        candidates.append(my_pos + Vec2(4, -2))  # Back and right (comeback)
        candidates.append(my_pos + Vec2(-4, -2)) # Back and left (comeback)

    # Evaluate candidates by defender clearance AND visibility to QB
    best_pos = my_pos
    best_score = 0.0

    for pos in candidates:
        # Calculate clearance from nearest defender
        min_defender_dist = float('inf')
        for opp in world.opponents:
            dist = opp.pos.distance_to(pos)
            if dist < min_defender_dist:
                min_defender_dist = dist

        # Calculate visibility to QB (penalize positions behind QB)
        qb_visibility = 1.0
        if qb:
            # Position should be roughly in QB's field of view
            to_pos = pos - qb.pos
            # Behind QB is bad
            if to_pos.y < -2:  # Behind LOS
                qb_visibility = 0.3
            # Far to opposite side of roll is also harder to see
            if qb_rolling_right and to_pos.x < -5:
                qb_visibility *= 0.5
            elif qb_rolling_left and to_pos.x > 5:
                qb_visibility *= 0.5

        # Score = defender clearance * visibility
        score = min_defender_dist * qb_visibility

        if score > best_score:
            best_score = score
            best_pos = pos

    return best_pos


def _get_ball_adjustment(world: WorldState) -> tuple[CatchType, Vec2, Vec2, bool]:
    """Determine how to adjust to the ball, catch type, and whether to run through.

    JUDGEMENT CALL: Receiver decides if they can run through the ball or must adjust.
    - Good throw (on path): Run through, catch in stride, maintain momentum
    - Bad throw (off path): Adjust to ball, may need to slow/stop
    - Better WRs can handle tighter adjustments

    Returns:
        (catch_type, catch_point, continue_direction, can_run_through)
        - catch_point: where the ball will arrive
        - continue_direction: direction to keep running after catch
        - can_run_through: True if catch can be made in stride
    """
    ball = world.ball
    my_pos = world.me.pos
    my_vel = world.me.velocity
    attrs = world.me.attributes

    # Default continue direction
    if my_vel.length() > 0.5:
        my_dir = my_vel.normalized()
    else:
        my_dir = Vec2(0, 1)  # Default upfield

    if not ball.flight_target:
        return CatchType.HANDS, my_pos, my_dir, False

    target = ball.flight_target
    to_ball = target - my_pos

    # === JUDGE: Can we run through this ball? ===
    # A good throw is "on path" - where we're naturally going
    # Calculate how far off our current path the ball is

    if my_vel.length() > 1.0:
        # Project where we'll be in ~0.3s if we keep running
        projected_pos = my_pos + my_vel * 0.3

        # How far is ball target from our projected path?
        path_error = target.distance_to(projected_pos)

        # How far is ball target from current position?
        direct_dist = to_ball.length()

        # Calculate "on path" threshold based on receiver attributes
        # Better route runners and catchers can handle more deviation
        catching = attrs.catching
        route_running = attrs.route_running
        adjustment_skill = (catching + route_running) / 2.0

        # Base threshold: 1.5 yards
        # Good receivers (85+): can handle up to 2.5 yards
        # Elite receivers (95+): can handle up to 3.0 yards
        base_threshold = 1.5
        skill_bonus = (adjustment_skill - 70) / 100.0 * 1.5  # 0 to 1.5 yards
        on_path_threshold = base_threshold + max(0, skill_bonus)

        # Is ball close enough to our path to run through?
        can_run_through = path_error < on_path_threshold

        # Continue direction:
        # - If running through: keep our current direction
        # - If adjusting: direction is toward ball, then upfield
        if can_run_through:
            continue_dir = my_dir
        else:
            # Blend: start toward ball, but curve upfield
            to_ball_dir = to_ball.normalized() if to_ball.length() > 0.1 else Vec2(0, 1)
            upfield = Vec2(0, 1)
            continue_dir = (to_ball_dir + upfield).normalized()

    else:
        # Not moving much - can't "run through", must adjust
        can_run_through = False
        continue_dir = to_ball.normalized() if to_ball.length() > 0.1 else Vec2(0, 1)

    # Determine catch type based on ball location
    catch_type = CatchType.HANDS

    return catch_type, target, continue_dir, can_run_through


def _find_nearest_defender_to_block(world: WorldState) -> Optional[PlayerView]:
    """Find nearest defender to block (for run support or after catch elsewhere)."""
    my_pos = world.me.pos
    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        dist = opp.pos.distance_to(my_pos)
        if dist < closest_dist:
            closest_dist = dist
            closest = opp

    return closest if closest_dist < 10.0 else None


def _get_route_target(world: WorldState) -> Optional[Vec2]:
    """Get the next target position for route running.

    Uses route_target from WorldState if available (provided by route_runner),
    otherwise falls back to running upfield.

    Note: Uses getattr() for compatibility with RBContext which may not have route_target.
    """
    # Use route target from orchestrator/route_runner if available
    # Safe access since RBContext doesn't have route_target attribute
    route_target = getattr(world, 'route_target', None)
    if route_target is not None:
        return route_target

    # Fallback: run 10 yards upfield from current position
    return world.me.pos + Vec2(0, 10)


# =============================================================================
# Release Technique System
# =============================================================================

def _select_release_type(
    world: WorldState,
    defender: Optional[PlayerView],
    route_direction: str,
) -> ReleaseType:
    """Select release technique to create separation from press.

    SEPARATION-FIRST: The goal is to create separation from LOS,
    not to "beat" the DB. Each technique creates space differently.

    Swim: Create separation by going over/around
    Rip: Create separation by going under/through
    Speed: Create separation with burst
    Hesitation: Create separation with misdirection
    """
    if not defender or defender.distance > 2.0:
        return ReleaseType.FREE

    attrs = world.me.attributes
    my_pos = world.me.pos
    def_pos = defender.pos

    # Determine defender leverage
    x_diff = def_pos.x - my_pos.x
    is_inside_leverage = x_diff < -0.5 if my_pos.x < 0 else x_diff > 0.5

    # Speed advantage check
    my_speed = attrs.speed
    # Estimate defender speed (without direct attribute access)
    def_current_speed = defender.speed
    speed_advantage = my_speed > 80 and def_current_speed < 5.0

    if speed_advantage:
        return ReleaseType.SPEED

    # Route running affects technique selection
    route_running = attrs.route_running

    # Based on leverage and route direction
    if is_inside_leverage:
        # Defender has inside - swim over them
        if route_running >= 80:
            return ReleaseType.SWIM
        return ReleaseType.SPEED
    else:
        # Defender has outside - rip under
        if route_running >= 80:
            return ReleaseType.RIP
        return ReleaseType.HESITATION

    return ReleaseType.SPEED


def _get_release_target(
    world: WorldState,
    release_type: ReleaseType,
    defender: Optional[PlayerView],
) -> Vec2:
    """Get the movement target for release technique."""
    my_pos = world.me.pos

    if release_type == ReleaseType.FREE or not defender:
        # Free release - just go vertical
        return my_pos + Vec2(0, 5)

    def_pos = defender.pos

    if release_type == ReleaseType.SWIM:
        # Swim over - go opposite of defender, then vertical
        swim_dir = -1 if def_pos.x > my_pos.x else 1
        return my_pos + Vec2(swim_dir * 2, 3)

    elif release_type == ReleaseType.RIP:
        # Rip under - attack inside shoulder, then clear
        rip_dir = 1 if def_pos.x > my_pos.x else -1
        return my_pos + Vec2(rip_dir * 1.5, 3)

    elif release_type == ReleaseType.SPEED:
        # Speed release - run past their outside
        speed_dir = 1 if def_pos.x < my_pos.x else -1
        return my_pos + Vec2(speed_dir * 1, 4)

    elif release_type == ReleaseType.HESITATION:
        # Hesitation - fake inside, go outside
        fake_dir = 1 if def_pos.x < my_pos.x else -1
        return my_pos + Vec2(-fake_dir * 0.5, 4)

    return my_pos + Vec2(0, 5)


# =============================================================================
# Hot Route System
# =============================================================================

def _detect_blitz(world: WorldState) -> tuple[bool, str]:
    """Detect if defense is blitzing and from which side.

    Returns:
        (is_blitz, blitz_side) where side is 'left', 'right', or 'center'
    """
    my_pos = world.me.pos
    blitz_threats = []

    for opp in world.opponents:
        # LBs and DBs can blitz
        if opp.position in (Position.MLB, Position.OLB, Position.ILB, Position.SS, Position.CB):
            # Check if rushing toward LOS
            if opp.velocity.y < -2.0 or opp.pos.y < world.los_y - 1:
                blitz_threats.append(opp)

    if not blitz_threats:
        return False, ""

    # Determine side
    avg_x = sum(t.pos.x for t in blitz_threats) / len(blitz_threats)
    if avg_x < -3:
        return True, "left"
    elif avg_x > 3:
        return True, "right"
    return True, "center"


def _should_convert_to_hot(
    world: WorldState,
    is_blitz: bool,
    blitz_side: str,
) -> bool:
    """Determine if we should convert to hot route."""
    if not is_blitz:
        return False

    my_pos = world.me.pos

    # Convert if blitz is from our side
    if blitz_side == "left" and my_pos.x < 0:
        return True
    if blitz_side == "right" and my_pos.x > 0:
        return True

    # Always convert on center blitz if inside receiver
    if blitz_side == "center" and abs(my_pos.x) < 10:
        return True

    return False


def _convert_to_hot_route(original_route: str) -> HotRouteType:
    """Convert current route to appropriate hot route.

    From design doc:
        Go → Slant
        Out → Quick out
        Dig → Shallow cross
        Any → Sight adjust
    """
    route_lower = original_route.lower()

    if "go" in route_lower or "fly" in route_lower or "streak" in route_lower:
        return HotRouteType.SLANT
    elif "out" in route_lower:
        return HotRouteType.QUICK_OUT
    elif "dig" in route_lower or "in" in route_lower:
        return HotRouteType.SHALLOW_CROSS
    else:
        return HotRouteType.SIGHT_ADJUST


def _get_hot_route_target(world: WorldState, hot_type: HotRouteType) -> Vec2:
    """Get target position for hot route.

    Hot routes need to get open within 1.0s, expect throw within 1.5s.
    """
    my_pos = world.me.pos
    los = world.los_y

    if hot_type == HotRouteType.SLANT:
        # Quick slant at 5-7 yards
        slant_dir = 1 if my_pos.x < 0 else -1  # Slant toward middle
        return Vec2(my_pos.x + slant_dir * 5, los + 6)

    elif hot_type == HotRouteType.QUICK_OUT:
        # Quick out at 3-5 yards
        out_dir = -1 if my_pos.x < 0 else 1  # Out toward sideline
        return Vec2(my_pos.x + out_dir * 5, los + 4)

    elif hot_type == HotRouteType.SHALLOW_CROSS:
        # Shallow cross at 3-4 yards
        cross_dir = 1 if my_pos.x < 0 else -1
        return Vec2(cross_dir * 5, los + 4)

    else:  # SIGHT_ADJUST
        # Find open space
        return _find_open_space(world)


# =============================================================================
# Main Brain Function
# =============================================================================

def receiver_brain(world: Union[WRContext, RBContext]) -> BrainDecision:
    """Receiver brain - called every tick for WRs, TEs, and RBs running routes.

    Args:
        world: Context from receiver's perspective (WRContext or RBContext)

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Reset state at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)
        state.route_phase = RoutePhase.RELEASE

    # =========================================================================
    # If we have the ball, this brain shouldn't be active
    # (Orchestrator should use ballcarrier brain)
    # =========================================================================
    if world.me.has_ball:
        # Shouldn't happen, but handle gracefully
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 10),
            move_type="sprint",
            intent="turn_upfield",
            reasoning="Have ball, turning upfield (should use ballcarrier brain)",
        )

    # =========================================================================
    # Run Play - RB follows run path to mesh point before handoff
    # =========================================================================
    if world.is_run_play and world.me.position in (Position.RB, Position.FB):
        # RB/FB follows run path waypoints before handoff
        if world.run_path and len(world.run_path) > 0:
            # Find current waypoint (mesh point is first waypoint)
            mesh_point = world.run_path[0]
            dist_to_mesh = world.me.pos.distance_to(mesh_point)

            if dist_to_mesh > 0.5:
                # Move to mesh point for handoff
                return BrainDecision(
                    move_target=mesh_point,
                    move_type="jog",  # Controlled speed to mesh point
                    intent="run_path",
                    reasoning=f"Moving to mesh point ({dist_to_mesh:.1f}yd away)",
                )
            else:
                # At mesh point, hold for handoff
                return BrainDecision(
                    intent="hold",
                    reasoning="At mesh point, waiting for handoff",
                )
        else:
            # No run path, just hold position
            return BrainDecision(
                intent="hold",
                reasoning="Run play but no path - holding for handoff",
            )

    # =========================================================================
    # Ball in air - Track and catch (in stride if possible)
    # =========================================================================
    if world.ball.is_in_flight:
        if world.ball.intended_receiver_id == world.me.id:
            state.route_phase = RoutePhase.BALL_TRACKING
            state.is_target = True

            catch_type, catch_point, continue_dir, can_run_through = _get_ball_adjustment(world)

            # Calculate distance to catch point
            dist_to_catch = world.me.pos.distance_to(catch_point)

            # === GOOD THROW: Run through the ball ===
            if can_run_through:
                _trace(world, f"Ball on path - catching in stride", TraceCategory.PERCEPTION)

                if dist_to_catch < 0.5:
                    # At catch point - keep running!
                    yac_target = catch_point + continue_dir * 5.0
                    return BrainDecision(
                        move_target=yac_target,
                        move_type="sprint",
                        intent="catch_and_run",
                        reasoning=f"Catch in stride, YAC mode",
                    )
                elif dist_to_catch < 3.0:
                    # Close - target past catch point
                    yac_target = catch_point + continue_dir * 3.0
                    return BrainDecision(
                        move_target=yac_target,
                        move_type="sprint",
                        intent="track_ball",
                        reasoning=f"Ball arriving in stride ({dist_to_catch:.1f}yd)",
                    )
                else:
                    # Further out - run through catch point
                    return BrainDecision(
                        move_target=catch_point + continue_dir * 2.0,
                        move_type="sprint",
                        intent="track_ball",
                        reasoning=f"Running through catch ({dist_to_catch:.1f}yd)",
                    )

            # === BAD THROW: Must adjust to ball ===
            else:
                _trace(world, f"Ball off path - adjusting ({dist_to_catch:.1f}yd)", TraceCategory.PERCEPTION)

                if dist_to_catch < 0.5:
                    # At catch point - try to continue but may be slow
                    yac_target = catch_point + continue_dir * 3.0
                    return BrainDecision(
                        move_target=yac_target,
                        move_type="run",  # Not sprint - had to adjust
                        intent="catch_and_run",
                        reasoning=f"Adjusted catch, recovering momentum",
                    )
                elif dist_to_catch < 2.0:
                    # Close - brake slightly to secure catch
                    return BrainDecision(
                        move_target=catch_point,
                        move_type="run",  # Controlled speed
                        intent="track_ball",
                        reasoning=f"Adjusting to ball ({dist_to_catch:.1f}yd off path)",
                    )
                else:
                    # Further out - sprint to ball location
                    return BrainDecision(
                        move_target=catch_point,
                        move_type="sprint",
                        intent="track_ball",
                        reasoning=f"Chasing ball ({dist_to_catch:.1f}yd away)",
                    )
        else:
            # Ball thrown elsewhere - block for RAC
            defender = _find_nearest_defender_to_block(world)
            if defender:
                return BrainDecision(
                    move_target=defender.pos,
                    intent="block_for_rac",
                    target_id=defender.id,
                    reasoning=f"Ball elsewhere, blocking for RAC",
                )
            return BrainDecision(
                intent="watch",
                reasoning="Ball in air to teammate",
            )

    # =========================================================================
    # Check for QB scramble - find open space for completion
    # =========================================================================
    if _is_qb_scrambling(world):
        state.route_phase = RoutePhase.SCRAMBLE
        state.scramble_mode = True

        open_space = _find_open_space(world)

        return BrainDecision(
            move_target=open_space,
            move_type="run",
            intent="scramble_drill",
            reasoning="Finding open space for scramble completion",
        )

    # =========================================================================
    # Route Running
    # =========================================================================

    # Find covering defender
    defender = _find_covering_defender(world)
    state.covering_defender_id = defender.id if defender else None
    state.separation = _calculate_separation(world, defender)

    # =========================================================================
    # Hot Route Check (early in play)
    # =========================================================================
    if world.time_since_snap < 0.3 and not state.is_hot:
        is_blitz, blitz_side = _detect_blitz(world)
        if _should_convert_to_hot(world, is_blitz, blitz_side):
            state.is_hot = True
            state.original_route = world.assignment
            state.hot_route_type = _convert_to_hot_route(world.assignment)

    # If running hot route, use hot route logic
    if state.is_hot and state.hot_route_type:
        hot_target = _get_hot_route_target(world, state.hot_route_type)
        sep_status = "OPEN" if state.separation > 2.5 else "WINDOW" if state.separation > 1.5 else "TIGHT"

        return BrainDecision(
            move_target=hot_target,
            move_type="sprint",
            intent="hot_route",
            reasoning=f"HOT! {state.hot_route_type.value} ({sep_status})",
        )

    # Determine route phase based on time
    time = world.time_since_snap

    if time < 0.5:
        state.route_phase = RoutePhase.RELEASE
    elif time < 1.2:
        state.route_phase = RoutePhase.STEM
    elif time < 1.5:
        state.route_phase = RoutePhase.BREAK
    else:
        state.route_phase = RoutePhase.POST_BREAK

    # Get route target (simplified - real implementation uses route waypoints)
    route_target = _get_route_target(world)
    if not route_target:
        route_target = world.me.pos + Vec2(0, 5)

    # Phase-specific behavior - each phase creates/maintains separation
    if state.route_phase == RoutePhase.RELEASE:
        # Release phase - create initial separation from LOS
        if defender and defender.distance < 2.0:
            # Press - use technique to create separation
            state.release_type = _select_release_type(world, defender, world.assignment)
            release_target = _get_release_target(world, state.release_type, defender)

            return BrainDecision(
                move_target=release_target,
                move_type="sprint",
                action=state.release_type.value,
                intent="release",
                reasoning=f"Creating separation with {state.release_type.value}",
            )

        state.release_type = ReleaseType.FREE
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="release",
            reasoning="Clean release - building separation",
        )

    elif state.route_phase == RoutePhase.STEM:
        # Stem - create vertical separation
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="stem",
            reasoning=f"Creating vertical separation ({state.separation:.1f}yd)",
        )

    elif state.route_phase == RoutePhase.BREAK:
        # Break - create lateral separation with cut
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="break",
            reasoning=f"Creating separation with break ({state.separation:.1f}yd)",
        )

    else:  # POST_BREAK
        # Post-break - maximize separation for completion
        sep_status = "OPEN" if state.separation > 2.5 else "WINDOW" if state.separation > 1.5 else "TIGHT"

        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="post_break",
            reasoning=f"{sep_status} for completion ({state.separation:.1f}yd separation)",
        )
