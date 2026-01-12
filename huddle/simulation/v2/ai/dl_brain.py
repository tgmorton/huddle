"""Defensive Line Brain - Decision-making for DTs, DEs, and NTs.

TARGET-BASED PHILOSOPHY:
DL target is ALWAYS the ball (QB on pass, gap/RB on run).
Movement is always toward target. Engagement with OL happens
as a SIDE EFFECT when OL positions in our path - we don't
"fight blockers", we push THROUGH them toward our target.

The DL brain handles:
- Pass rush: Get to QB (OL are obstacles, not targets)
- Run defense: Get to ball/gap (shed blocks to make tackle)
- Pursuit: Chase ballcarrier

Phases: SNAP → GET_TO_TARGET → PURSUIT → TACKLE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import DLContext
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from ..core.trace import get_trace_system, TraceCategory
from ..core.variance import pursuit_angle_accuracy


# =============================================================================
# Trace Helper
# =============================================================================

def _trace(world: WorldState, msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace for this DL."""
    trace = get_trace_system()
    trace.trace(world.me.id, world.me.name, category, msg)


# =============================================================================
# DL Enums
# =============================================================================

class RushMove(str, Enum):
    """Pass rush moves."""
    BULL_RUSH = "bull_rush"
    SWIM = "swim"
    SPIN = "spin"
    RIP = "rip"
    SPEED_RUSH = "speed_rush"
    LONG_ARM = "long_arm"
    CLUB_SWIM = "club_swim"


class DLPhase(str, Enum):
    """Current phase of DL action."""
    PRE_SNAP = "pre_snap"
    ENGAGE = "engage"
    PASS_RUSH = "pass_rush"
    RUN_FIT = "run_fit"
    STUNT = "stunt"
    PURSUIT = "pursuit"
    CONTAIN = "contain"


class GapTechnique(str, Enum):
    """Gap technique."""
    ONE_GAP = "one_gap"   # Penetrate assigned gap
    TWO_GAP = "two_gap"   # Control blocker, play both gaps


class StuntRole(str, Enum):
    """Role in a stunt."""
    PENETRATOR = "penetrator"  # Crash and occupy
    LOOPER = "looper"          # Loop behind


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class DLState:
    """Tracked state for DL decision-making."""
    phase: DLPhase = DLPhase.PRE_SNAP
    # Target-based tracking (NOT blocker-based)
    target_pos: Optional[Vec2] = None  # Current target position (QB, gap, ballcarrier)
    target_type: str = "unknown"  # "qb", "gap", "ballcarrier"
    # Rush move tracking
    current_move: Optional[RushMove] = None
    move_start_time: float = 0.0
    move_progress: float = 0.0  # Progress toward target (0-1)
    # Gap responsibility
    gap_technique: GapTechnique = GapTechnique.ONE_GAP
    assigned_gap: str = "B_gap"
    stunt_role: Optional[StuntRole] = None


_dl_states: dict[str, DLState] = {}


def _get_state(player_id: str) -> DLState:
    if player_id not in _dl_states:
        _dl_states[player_id] = DLState()
    return _dl_states[player_id]


def _reset_state(player_id: str) -> None:
    _dl_states[player_id] = DLState()


# =============================================================================
# Target Calculation Functions
# =============================================================================

def _find_qb(world: WorldState) -> Optional[PlayerView]:
    """Find the QB."""
    for opp in world.opponents:
        if opp.position == Position.QB:
            return opp
    return None


def _find_ballcarrier(world: WorldState) -> Optional[PlayerView]:
    """Find the ballcarrier."""
    for opp in world.opponents:
        if opp.has_ball:
            return opp
    return None


def _calculate_target(world: WorldState, state: DLState) -> tuple[Vec2, str]:
    """Calculate DL's target position - ALWAYS the ball, not blockers.

    Returns:
        (target_position, target_type) where target_type is "qb", "gap", or "ballcarrier"
    """
    ballcarrier = _find_ballcarrier(world)
    qb = _find_qb(world)

    # If ballcarrier exists and is past LOS, target them directly
    if ballcarrier and ballcarrier.pos.y > world.los_y:
        return ballcarrier.pos, "ballcarrier"

    # Pass play: target is QB
    if _is_pass_play(world):
        if qb:
            return qb.pos, "qb"
        # No QB found, target pocket area
        return Vec2(0, world.los_y - 5), "qb"

    # Run play: target is our assigned gap area, then ballcarrier
    gap_x = _get_gap_x_position(state.assigned_gap)

    # If we can see the ballcarrier and they're heading to/through our area
    if ballcarrier:
        bc_in_our_area = abs(ballcarrier.pos.x - gap_x) < 4.0
        if bc_in_our_area:
            return ballcarrier.pos, "ballcarrier"

    # Target our gap at/past LOS
    return Vec2(gap_x, world.los_y + 1), "gap"


def _get_gap_x_position(gap: str) -> float:
    """Get the X position for a gap assignment."""
    gap_positions = {
        "A_gap": 1.0,   # Between center and guard
        "B_gap": 3.0,   # Between guard and tackle
        "C_gap": 5.5,   # Between tackle and TE
        "D_gap": 8.0,   # Outside contain
    }
    # Return absolute value - DL alignment determines sign
    return gap_positions.get(gap, 3.0)


def _is_blocked(world: WorldState) -> tuple[bool, Optional[PlayerView]]:
    """Check if we're currently engaged with a blocker (OL in our path).

    This is a DETECTION function, not a targeting function.
    We detect blockers to know we need to push through them,
    not to target them.

    Returns False if we have shed immunity (just broke free from block),
    allowing us to sprint past the blocker.
    """
    # If we just shed a block, we're free even if OL is close
    if world.has_shed_immunity:
        return False, None

    my_pos = world.me.pos

    for opp in world.opponents:
        if opp.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            dist = opp.pos.distance_to(my_pos)
            if dist < 1.5:  # Very close = engaged
                return True, opp

    return False, None


def _is_pass_play(world: WorldState) -> bool:
    """Determine if this is a pass play based on OL behavior and QB movement.

    Key reads:
    - OL stepping backward/setting = pass
    - OL stepping forward/firing out = run
    - QB dropping = pass
    - world.is_run_play flag (if available)
    """
    # Check explicit run play flag first
    if hasattr(world, 'is_run_play') and world.is_run_play:
        return False

    qb = _find_qb(world)
    if qb and qb.has_ball:
        # QB dropping back = pass
        if qb.velocity.y < -1:
            return True
        if world.time_since_snap > 0.5 and qb.pos.y < world.los_y - 3:
            return True

    # Read OL movement - are they firing out (run) or setting (pass)?
    ol_firing_out = False
    ol_pass_setting = False
    for opp in world.opponents:
        if opp.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            # OL moving forward = run blocking
            if opp.velocity.y > 1.0:
                ol_firing_out = True
            # OL moving backward/lateral = pass setting
            elif opp.velocity.y < -0.5:
                ol_pass_setting = True

    if ol_firing_out and not ol_pass_setting:
        return False  # Run play
    if ol_pass_setting:
        return True  # Pass play

    # Default to pass after initial reads
    return world.time_since_snap > 0.3


def _get_gap_assignment(world: WorldState) -> str:
    """Get DL gap assignment based on position and alignment.

    Gap naming: A (center-guard), B (guard-tackle), C (tackle-TE), D (outside TE)
    """
    my_pos = world.me.pos
    my_position = world.me.position

    # DT/NT typically have A or B gap
    if my_position in (Position.DT, Position.NT):
        if abs(my_pos.x) < 2:
            return "A_gap"
        else:
            return "B_gap"

    # DE typically has C gap or D gap (contain)
    if my_position == Position.DE:
        if abs(my_pos.x) < 6:
            return "C_gap"
        else:
            return "D_gap"  # Wide 9, contain responsibility

    return "B_gap"  # Default


def _read_run_direction(world: WorldState) -> str:
    """Read OL blocking scheme to determine run direction.

    Returns: "left", "right", or "unknown"
    """
    # Check explicit run side if available
    if hasattr(world, 'run_play_side') and world.run_play_side:
        return world.run_play_side

    # Read guard/tackle movement
    left_flow = 0
    right_flow = 0

    for opp in world.opponents:
        if opp.position in (Position.LG, Position.LT):
            if opp.velocity.x > 0.5:
                right_flow += 1
            elif opp.velocity.x < -0.5:
                left_flow += 1
        elif opp.position in (Position.RG, Position.RT):
            if opp.velocity.x > 0.5:
                right_flow += 1
            elif opp.velocity.x < -0.5:
                left_flow += 1

    if right_flow > left_flow:
        return "right"
    elif left_flow > right_flow:
        return "left"
    return "unknown"


def _is_ball_in_air(world: WorldState) -> bool:
    """Check if ball is currently in flight (pass thrown, not yet caught)."""
    return hasattr(world.ball, 'is_in_flight') and world.ball.is_in_flight


def _select_rush_move(
    world: WorldState,
    is_blocked: bool,
    state: DLState
) -> RushMove:
    """Select the best pass rush move based on our attributes and situation.

    The move is about HOW we push toward our target, not about fighting a blocker.
    """
    attrs = world.me.attributes

    if not is_blocked:
        return RushMove.SPEED_RUSH  # Free path to target

    # Attribute-based selection for pushing through OL
    finesse = attrs.pass_rush
    agility = attrs.agility

    # Strong player: power through
    if attrs.strength >= 85:
        return RushMove.BULL_RUSH

    # Fast edge player: go around
    if world.me.position == Position.DE and attrs.speed >= 85:
        return RushMove.SPEED_RUSH

    # High finesse: quick hands
    if finesse >= 85:
        return RushMove.SWIM

    # If we've been stuck, try counter move
    if state.move_progress < 0.2 and world.current_time - state.move_start_time > 0.8:
        if agility >= 80:
            return RushMove.SPIN
        return RushMove.RIP

    # Default based on attributes
    if finesse >= 75:
        return RushMove.RIP

    return RushMove.CLUB_SWIM


def _get_counter_move(current_move: RushMove) -> RushMove:
    """Get counter move when current move stalls."""
    counters = {
        RushMove.BULL_RUSH: RushMove.SWIM,
        RushMove.SWIM: RushMove.SPIN,
        RushMove.RIP: RushMove.SPIN,
        RushMove.SPEED_RUSH: RushMove.SPIN,
        RushMove.LONG_ARM: RushMove.SPIN,
    }
    return counters.get(current_move, RushMove.CLUB_SWIM)


def _is_being_doubled(world: WorldState, blocker: Optional[PlayerView]) -> bool:
    """Check if being double-teamed."""
    if not blocker:
        return False

    my_pos = world.me.pos
    count = 0

    for opp in world.opponents:
        if opp.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            if opp.pos.distance_to(my_pos) < 2.0:
                count += 1

    return count >= 2


def _calculate_pursuit_angle(
    world: WorldState, my_pos: Vec2, bc_pos: Vec2, bc_vel: Vec2, my_speed: float
) -> Vec2:
    """Calculate pursuit angle to intercept ballcarrier.

    Applies pursuit_angle_accuracy variance - lower awareness/tackle
    DL take worse angles (overpursue), creating cutback opportunities.
    """
    if bc_vel.length() < 0.5:
        return bc_pos

    # Calculate optimal intercept point
    optimal_intercept = bc_pos
    for t in [0.5, 1.0, 1.5]:
        predicted = bc_pos + bc_vel * t
        my_dist = my_pos.distance_to(predicted)
        my_time = my_dist / my_speed if my_speed > 0 else 10.0

        if my_time <= t + 0.2:
            optimal_intercept = predicted
            break
    else:
        optimal_intercept = bc_pos + bc_vel * 0.5

    # Apply pursuit accuracy variance
    # Lower awareness/tackle = worse angles (overpursue toward current pos)
    awareness = getattr(world.me.attributes, 'awareness', 75)
    tackle = getattr(world.me.attributes, 'tackle', 75)
    fatigue = getattr(world.me, 'fatigue', 0.0)

    accuracy = pursuit_angle_accuracy(awareness, tackle, fatigue)

    if accuracy < 1.0:
        # Lerp toward ballcarrier current position (overpursuit)
        return optimal_intercept.lerp(bc_pos, 1.0 - accuracy)

    return optimal_intercept


# =============================================================================
# Main Brain Function
# =============================================================================

def dl_brain(world: DLContext) -> BrainDecision:
    """Defensive line brain - for DTs, DEs, and NTs.

    TARGET-BASED APPROACH:
    1. Calculate target (QB for pass, gap/RB for run)
    2. Move toward target
    3. If blocked, push THROUGH toward target (don't fight blocker)
    4. Engagement is a side effect, not the goal

    Args:
        world: DLContext with pass rush and run defense info

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Reset at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

        # Set gap technique and assignment based on position
        if world.me.position == Position.NT:
            state.gap_technique = GapTechnique.TWO_GAP
        else:
            state.gap_technique = GapTechnique.ONE_GAP

        state.assigned_gap = _get_gap_assignment(world)

    # Adjust gap position based on our side of the field
    my_side = 1 if world.me.pos.x > 0 else -1

    # =========================================================================
    # STEP 1: Calculate our target (ALWAYS the ball, never the blocker)
    # =========================================================================
    target_pos, target_type = _calculate_target(world, state)

    # Adjust target X for our side of the field
    if target_type == "gap":
        target_pos = Vec2(my_side * abs(target_pos.x), target_pos.y)

    state.target_pos = target_pos
    state.target_type = target_type

    # =========================================================================
    # STEP 2: Check if we're blocked (OL in our path)
    # =========================================================================
    blocked, blocker = _is_blocked(world)

    # Calculate distance to target
    dist_to_target = world.me.pos.distance_to(target_pos)

    # Track progress toward target
    if state.move_start_time > 0:
        initial_dist = 10.0  # Assume starting ~10 yards from target
        state.move_progress = max(0, (initial_dist - dist_to_target) / initial_dist)

    # =========================================================================
    # Ball In Air - Continue toward QB area, don't track ball
    # =========================================================================
    if _is_ball_in_air(world):
        qb = _find_qb(world)
        if qb:
            return BrainDecision(
                move_target=qb.pos,
                move_type="run",
                intent="post_throw",
                reasoning="Ball in air - continuing toward QB",
            )
        return BrainDecision(
            intent="hold",
            reasoning="Ball in air - holding position",
        )

    # =========================================================================
    # Pursuit Mode - Ball past LOS and we're not blocked
    # =========================================================================
    ballcarrier = _find_ballcarrier(world)
    if ballcarrier and ballcarrier.pos.y > world.los_y and not blocked:
        state.phase = DLPhase.PURSUIT

        my_speed = 4.5 + (world.me.attributes.speed - 75) * 0.1
        intercept = _calculate_pursuit_angle(
            world, world.me.pos, ballcarrier.pos, ballcarrier.velocity, my_speed
        )

        dist = world.me.pos.distance_to(ballcarrier.pos)

        if dist < 2.0:
            return BrainDecision(
                move_target=ballcarrier.pos,
                move_type="sprint",
                action="tackle",
                target_id=ballcarrier.id,
                intent="tackle",
                reasoning="Tackling ballcarrier",
            )

        return BrainDecision(
            move_target=intercept,
            move_type="sprint",
            intent="pursuit",
            reasoning=f"Pursuing ballcarrier, {dist:.1f}yd away",
        )

    # =========================================================================
    # QB Scramble Contain (DE only)
    # =========================================================================
    qb = _find_qb(world)
    qb_scrambling = (
        qb and qb.has_ball and
        abs(qb.velocity.x) > 3.0 and
        abs(qb.velocity.x) > abs(qb.velocity.y) * 2
    )
    if qb_scrambling and world.me.position == Position.DE:
        state.phase = DLPhase.CONTAIN
        side = 1 if qb.pos.x > world.me.pos.x else -1
        contain_pos = Vec2(qb.pos.x + side * 2, qb.pos.y)

        return BrainDecision(
            move_target=contain_pos,
            move_type="sprint",
            action="contain",
            intent="contain",
            reasoning="Setting edge, containing QB scramble",
        )

    # =========================================================================
    # Double Team Detection - Anchor and occupy
    # =========================================================================
    if _is_being_doubled(world, blocker):
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 0.5),  # Push toward target direction
            move_type="run",
            action="anchor",
            intent="vs_double",
            reasoning="Being doubled - anchoring, occupying two blockers",
        )

    # =========================================================================
    # MAIN LOGIC: Move toward target, push through if blocked
    # =========================================================================

    # Select rush move based on situation
    if not state.current_move or (world.current_time - state.move_start_time > 1.0):
        state.current_move = _select_rush_move(world, blocked, state)
        state.move_start_time = world.current_time

    # -------------------------------------------------------------------------
    # NOT BLOCKED: Free path to target - sprint toward it
    # -------------------------------------------------------------------------
    if not blocked:
        state.phase = DLPhase.PASS_RUSH if target_type == "qb" else DLPhase.RUN_FIT

        # Adjust path for speed rush (wider angle for DE)
        adjusted_target = target_pos
        if state.current_move == RushMove.SPEED_RUSH and world.me.position == Position.DE:
            adjusted_target = target_pos + Vec2(my_side * 1.5, 0)

        if dist_to_target < 2.0 and target_type in ("qb", "ballcarrier"):
            return BrainDecision(
                move_target=target_pos,
                move_type="sprint",
                action="tackle" if target_type == "ballcarrier" else "sack",
                target_id=ballcarrier.id if ballcarrier else (qb.id if qb else None),
                intent="tackle",
                reasoning=f"Free run at {target_type}!",
            )

        return BrainDecision(
            move_target=adjusted_target,
            move_type="sprint",
            action=state.current_move.value if state.current_move else "rush",
            intent="free_rush" if target_type == "qb" else "penetrate",
            reasoning=f"Unblocked - attacking {target_type} ({dist_to_target:.1f}yd)",
        )

    # -------------------------------------------------------------------------
    # BLOCKED: Push THROUGH the blocker toward our target
    # -------------------------------------------------------------------------
    state.phase = DLPhase.PASS_RUSH if target_type == "qb" else DLPhase.RUN_FIT

    # Calculate direction TO our target (not to blocker)
    to_target = (target_pos - world.me.pos).normalized()

    # Our movement goal is toward the target, through the blocker
    # The blocking system will handle the collision physics
    push_through_pos = world.me.pos + to_target * 2.0

    # Check if we're being driven backward (losing the rep)
    being_driven_back = world.me.velocity.y < -0.5

    if being_driven_back:
        # Anchor - we're losing ground but still pushing toward target
        return BrainDecision(
            move_target=push_through_pos,
            move_type="run",
            action="anchor",
            intent="hold_gap" if target_type == "gap" else "pass_rush",
            reasoning=f"Anchoring - pushing through toward {target_type}",
        )

    # Two-gap technique: Control space, read ball
    if state.gap_technique == GapTechnique.TWO_GAP:
        # Stay at LOS, control blocker, but still face target
        hold_pos = Vec2(world.me.pos.x, world.los_y + 0.3)
        if ballcarrier and world.me.pos.distance_to(ballcarrier.pos) < 3.0:
            # Ball close - shed and attack
            return BrainDecision(
                move_target=ballcarrier.pos,
                move_type="sprint",
                action="shed_tackle",
                target_id=ballcarrier.id,
                intent="tackle",
                reasoning="Two-gap: ball close - shedding to tackle",
            )
        return BrainDecision(
            move_target=hold_pos,
            move_type="run",
            action="two_gap",
            intent="two_gap",
            reasoning=f"Two-gap: controlling space, reading toward {target_type}",
        )

    # One-gap / pass rush: Push through toward target
    # If target is close and visible, accelerate through
    if dist_to_target < 4.0:
        return BrainDecision(
            move_target=target_pos,
            move_type="sprint",
            action=state.current_move.value if state.current_move else "rush",
            intent="pass_rush" if target_type == "qb" else "penetrate",
            reasoning=f"Pushing through to {target_type} ({dist_to_target:.1f}yd)",
        )

    # Standard push toward target through blocker
    return BrainDecision(
        move_target=push_through_pos,
        move_type="run",
        action=state.current_move.value if state.current_move else "rush",
        intent="pass_rush" if target_type == "qb" else "penetrate",
        reasoning=f"Blocked - {state.current_move.value if state.current_move else 'pushing'} toward {target_type}",
    )
