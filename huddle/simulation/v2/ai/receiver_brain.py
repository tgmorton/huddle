"""Receiver Brain - Decision-making for WRs and TEs.

The receiver brain controls route running, catch execution, and blocking.
After the catch, control transfers to the Ballcarrier Brain.

Phases: RELEASE → STEM → BREAK → POST_BREAK → CATCH → (Ballcarrier Brain)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team, BallState


# =============================================================================
# Receiver State Enums
# =============================================================================

class RoutePhase(str, Enum):
    """Current phase of route execution."""
    PRE_SNAP = "pre_snap"
    RELEASE = "release"      # First 0.5s - winning vs press
    STEM = "stem"           # Selling vertical, setting up break
    BREAK = "break"         # Executing the break
    POST_BREAK = "post_break"  # After break - find window or accelerate
    SCRAMBLE = "scramble"    # QB scrambling, find space
    BALL_TRACKING = "ball_tracking"  # Ball in air to me
    BLOCKING = "blocking"    # Run play blocking


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
    """Find the defender covering this receiver."""
    my_pos = world.me.pos
    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        # Look for DBs and LBs in coverage
        if opp.position not in (Position.CB, Position.FS, Position.SS, Position.MLB, Position.OLB, Position.ILB):
            continue

        dist = opp.pos.distance_to(my_pos)
        if dist < closest_dist:
            closest_dist = dist
            closest = opp

    return closest


def _calculate_separation(world: WorldState, defender: Optional[PlayerView]) -> float:
    """Calculate effective separation from defender."""
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
    """Find open space for scramble drill."""
    my_pos = world.me.pos

    # Try to find space away from defenders
    best_pos = my_pos
    best_clearance = 0.0

    # Check several candidate positions
    candidates = [
        my_pos + Vec2(5, 0),   # Right
        my_pos + Vec2(-5, 0),  # Left
        my_pos + Vec2(0, 5),   # Upfield
        my_pos + Vec2(3, 3),   # Diagonal
        my_pos + Vec2(-3, 3),
    ]

    for pos in candidates:
        min_dist = float('inf')
        for opp in world.opponents:
            dist = opp.pos.distance_to(pos)
            if dist < min_dist:
                min_dist = dist

        if min_dist > best_clearance:
            best_clearance = min_dist
            best_pos = pos

    return best_pos


def _get_ball_adjustment(world: WorldState) -> tuple[CatchType, Vec2]:
    """Determine how to adjust to the ball and catch type."""
    ball = world.ball
    my_pos = world.me.pos

    if not ball.flight_target:
        return CatchType.HANDS, my_pos

    target = ball.flight_target
    to_ball = target - my_pos

    # Determine catch type based on ball location
    # For now, simplified version
    if to_ball.length() < 1.0:
        # Ball coming right to us
        return CatchType.HANDS, target

    # Ball requires adjustment
    return CatchType.HANDS, target


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
    """
    # Use route target from orchestrator/route_runner if available
    if world.route_target is not None:
        return world.route_target

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
    """Select the best release technique vs press coverage.

    From design doc:
        Swim: Arm over defender - best vs inside leverage
        Rip: Arm under defender - best vs outside leverage
        Speed: Outrun jam - best vs slower DB
        Hesitation: Fake inside, go outside - best vs aggressive press
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

def receiver_brain(world: WorldState) -> BrainDecision:
    """Receiver brain - called every tick for WRs and TEs.

    Args:
        world: Complete world state from receiver's perspective

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
    # Ball in air - Track and catch
    # =========================================================================
    if world.ball.is_in_flight:
        if world.ball.intended_receiver_id == world.me.id:
            state.route_phase = RoutePhase.BALL_TRACKING
            state.is_target = True

            catch_type, target_pos = _get_ball_adjustment(world)

            # Move to catch point
            dist_to_ball = world.me.pos.distance_to(target_pos)

            if dist_to_ball < 0.5:
                # Ready to catch
                return BrainDecision(
                    intent="catch",
                    reasoning=f"Ball arriving, {catch_type.value} catch",
                )

            return BrainDecision(
                move_target=target_pos,
                move_type="sprint",
                intent="track_ball",
                reasoning=f"Tracking ball, {dist_to_ball:.1f}yd to catch point",
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
    # Check for QB scramble - enter scramble drill
    # =========================================================================
    if _is_qb_scrambling(world):
        state.route_phase = RoutePhase.SCRAMBLE
        state.scramble_mode = True

        open_space = _find_open_space(world)

        return BrainDecision(
            move_target=open_space,
            move_type="run",
            intent="scramble_drill",
            reasoning="QB scrambling, finding open space",
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

    # Phase-specific behavior
    if state.route_phase == RoutePhase.RELEASE:
        # Release phase - get off LOS
        if defender and defender.distance < 2.0:
            # Press coverage - select release technique
            state.release_type = _select_release_type(world, defender, world.assignment)
            release_target = _get_release_target(world, state.release_type, defender)

            return BrainDecision(
                move_target=release_target,
                move_type="sprint",
                action=state.release_type.value,
                intent="release",
                reasoning=f"{state.release_type.value.upper()} release vs press",
            )

        state.release_type = ReleaseType.FREE
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="release",
            reasoning="Free release, getting into route",
        )

    elif state.route_phase == RoutePhase.STEM:
        # Stem - sell vertical, set up defender
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="stem",
            reasoning=f"Selling vertical, sep: {state.separation:.1f}yd",
        )

    elif state.route_phase == RoutePhase.BREAK:
        # Break - execute the break
        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="break",
            reasoning=f"Executing break, sep: {state.separation:.1f}yd",
        )

    else:  # POST_BREAK
        # Post-break - find window or continue route
        sep_status = "OPEN" if state.separation > 2.5 else "WINDOW" if state.separation > 1.5 else "TIGHT"

        return BrainDecision(
            move_target=route_target,
            move_type="sprint",
            intent="post_break",
            reasoning=f"Post-break, {sep_status} ({state.separation:.1f}yd sep)",
        )
