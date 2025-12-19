"""Defensive Line Brain - Decision-making for DTs, DEs, and NTs.

The DL brain handles:
- Pass rush execution and moves
- Run defense (one-gap vs two-gap)
- Stunt execution
- Pursuit

Phases: SNAP → ENGAGE → RUSH/RUN_FIT → PURSUIT → TACKLE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team


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
    blocker_id: Optional[str] = None
    current_move: Optional[RushMove] = None
    move_start_time: float = 0.0
    move_stalled: bool = False
    gap_technique: GapTechnique = GapTechnique.ONE_GAP
    stunt_role: Optional[StuntRole] = None
    rep_status: str = "neutral"  # winning, neutral, losing


_dl_states: dict[str, DLState] = {}


def _get_state(player_id: str) -> DLState:
    if player_id not in _dl_states:
        _dl_states[player_id] = DLState()
    return _dl_states[player_id]


def _reset_state(player_id: str) -> None:
    _dl_states[player_id] = DLState()


# =============================================================================
# Helper Functions
# =============================================================================

def _find_blocker(world: WorldState) -> Optional[PlayerView]:
    """Find the OL blocking us."""
    my_pos = world.me.pos
    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        if opp.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            dist = opp.pos.distance_to(my_pos)
            if dist < closest_dist and dist < 3.0:
                closest_dist = dist
                closest = opp

    return closest


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


def _is_pass_play(world: WorldState) -> bool:
    """Determine if this is a pass play."""
    qb = _find_qb(world)
    if qb and qb.has_ball:
        # QB still has ball and dropping back
        if qb.velocity.y < -1:
            return True
        if world.time_since_snap > 0.5 and qb.pos.y < world.los_y - 3:
            return True
    return False


def _is_ball_in_air(world: WorldState) -> bool:
    """Check if ball is currently in flight (pass thrown, not yet caught)."""
    return hasattr(world.ball, 'is_in_flight') and world.ball.is_in_flight


def _select_rush_move(
    world: WorldState,
    blocker: Optional[PlayerView],
    state: DLState
) -> RushMove:
    """Select the best pass rush move."""
    attrs = world.me.attributes

    if not blocker:
        return RushMove.SPEED_RUSH  # Free rush

    # Attribute advantages
    strength_diff = attrs.strength - 75  # Assume average OL
    finesse = attrs.pass_rush
    speed_diff = attrs.speed - 75
    agility = attrs.agility

    # Bull rush if strong
    if strength_diff > 10:
        return RushMove.BULL_RUSH

    # Speed rush if fast and edge player
    if world.me.position == Position.DE and speed_diff > 5:
        return RushMove.SPEED_RUSH

    # Swim if high pass rush
    if finesse >= 85:
        return RushMove.SWIM

    # Spin if agile and move stalled
    if state.move_stalled and agility >= 80:
        return RushMove.SPIN

    # Rip as alternative
    if finesse >= 75:
        return RushMove.RIP

    # Default to club-swim combo
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


def _calculate_pursuit_angle(my_pos: Vec2, bc_pos: Vec2, bc_vel: Vec2, my_speed: float) -> Vec2:
    """Calculate pursuit angle to intercept ballcarrier."""
    if bc_vel.length() < 0.5:
        return bc_pos

    # Predict future position
    for t in [0.5, 1.0, 1.5]:
        predicted = bc_pos + bc_vel * t
        my_dist = my_pos.distance_to(predicted)
        my_time = my_dist / my_speed if my_speed > 0 else 10.0

        if my_time <= t + 0.2:
            return predicted

    return bc_pos + bc_vel * 0.5


# =============================================================================
# Main Brain Function
# =============================================================================

def dl_brain(world: WorldState) -> BrainDecision:
    """Defensive line brain - for DTs, DEs, and NTs.

    Args:
        world: Complete world state

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Reset at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

        # Set gap technique based on position
        if world.me.position == Position.NT:
            state.gap_technique = GapTechnique.TWO_GAP
        else:
            state.gap_technique = GapTechnique.ONE_GAP

    # Find key players
    blocker = _find_blocker(world)
    qb = _find_qb(world)
    ballcarrier = _find_ballcarrier(world)

    if blocker:
        state.blocker_id = blocker.id

    # =========================================================================
    # Ball In Air - D-line does NOT track the ball
    # =========================================================================
    # When ball is thrown but not caught, D-line should:
    # - Continue rushing toward where QB was (occupy blockers)
    # - NOT run downfield to track ball (they don't cover)
    # - Wait for catch before switching to pursuit
    if _is_ball_in_air(world):
        state.phase = DLPhase.PASS_RUSH  # Stay in pass rush mode

        # D-line doesn't track ball - continue toward QB position
        # or hold position if engaged with blocker
        if blocker and world.me.pos.distance_to(blocker.pos) < 2.0:
            # Stay engaged with blocker
            return BrainDecision(
                move_target=blocker.pos,
                move_type="run",
                action="engage",
                target_id=blocker.id,
                intent="engaged",
                reasoning="Ball in air - staying engaged with blocker",
            )

        # Not engaged - continue toward where QB was
        qb = _find_qb(world)
        if qb:
            return BrainDecision(
                move_target=qb.pos,
                move_type="run",
                intent="post_throw",
                reasoning="Ball in air - continuing toward QB",
            )

        # Default - hold position
        return BrainDecision(
            intent="hold",
            reasoning="Ball in air - holding position",
        )

    # =========================================================================
    # Pursuit Mode - Ball past LOS
    # =========================================================================
    if ballcarrier and ballcarrier.pos.y > world.los_y:
        state.phase = DLPhase.PURSUIT

        my_speed = 4.5 + (world.me.attributes.speed - 75) * 0.1
        intercept = _calculate_pursuit_angle(
            world.me.pos, ballcarrier.pos, ballcarrier.velocity, my_speed
        )

        dist = world.me.pos.distance_to(ballcarrier.pos)

        if dist < 2.0:
            return BrainDecision(
                move_target=ballcarrier.pos,
                move_type="sprint",
                action="tackle",
                target_id=ballcarrier.id,
                intent="tackle",
                reasoning=f"Tackling ballcarrier",
            )

        return BrainDecision(
            move_target=intercept,
            move_type="sprint",
            intent="pursuit",
            reasoning=f"Pursuing ballcarrier, {dist:.1f}yd away",
        )

    # =========================================================================
    # QB Contain (if QB scrambling significantly)
    # =========================================================================
    # Only trigger contain on actual scrambles, not minor pocket movement
    qb_scrambling = (
        qb and qb.has_ball and
        abs(qb.velocity.x) > 3.0 and  # Significant lateral speed
        abs(qb.velocity.x) > abs(qb.velocity.y) * 2  # Mostly lateral movement
    )
    if qb_scrambling:
        # QB scrambling laterally
        if world.me.position == Position.DE:
            state.phase = DLPhase.CONTAIN

            # Set edge - position between DE and QB to cut off escape
            # If QB is to our right, stay 2 yards to his left (and vice versa)
            side = 1 if qb.pos.x > world.me.pos.x else -1
            contain_pos = Vec2(
                qb.pos.x + side * 2,  # Stay 2 yards outside QB
                qb.pos.y
            )

            return BrainDecision(
                move_target=contain_pos,
                move_type="sprint",
                action="contain",
                intent="contain",
                reasoning="Setting edge, containing QB scramble",
            )

    # =========================================================================
    # Pass Rush
    # =========================================================================
    if _is_pass_play(world):
        state.phase = DLPhase.PASS_RUSH

        # Check for double team
        if _is_being_doubled(world, blocker):
            # Anchor and occupy both blockers
            return BrainDecision(
                move_target=world.me.pos + Vec2(0, 1),
                move_type="run",
                action="anchor",
                intent="vs_double",
                reasoning="Being doubled, anchoring and occupying",
            )

        # Unblocked - rush QB
        if not blocker:
            if qb:
                return BrainDecision(
                    move_target=qb.pos,
                    move_type="sprint",
                    action="rush",
                    intent="free_rush",
                    reasoning="Unblocked! Rushing QB",
                )

        # Select and execute rush move
        if not state.current_move or state.move_stalled:
            if state.move_stalled and state.current_move:
                state.current_move = _get_counter_move(state.current_move)
            else:
                state.current_move = _select_rush_move(world, blocker, state)
            state.move_start_time = world.current_time
            state.move_stalled = False

        # Check if move is stalling
        if world.current_time - state.move_start_time > 1.0:
            # Check if making progress toward QB
            if qb:
                dist_to_qb = world.me.pos.distance_to(qb.pos)
                if dist_to_qb > 5:  # Still far away
                    state.move_stalled = True

        # Execute current move
        if qb:
            rush_target = qb.pos

            # Adjust target based on move
            if state.current_move == RushMove.SPEED_RUSH:
                # Take wider angle
                side = 1 if world.me.pos.x > 0 else -1
                rush_target = qb.pos + Vec2(side * 2, 1)
            elif state.current_move == RushMove.BULL_RUSH:
                # Straight through
                rush_target = qb.pos

            return BrainDecision(
                move_target=rush_target,
                move_type="sprint",
                action=state.current_move.value,
                target_id=blocker.id if blocker else None,
                intent="pass_rush",
                reasoning=f"Executing {state.current_move.value}",
            )

    # =========================================================================
    # Run Defense
    # =========================================================================
    state.phase = DLPhase.RUN_FIT

    if state.gap_technique == GapTechnique.TWO_GAP:
        # Two-gap: Stack blocker, read ball
        if blocker:
            return BrainDecision(
                move_target=blocker.pos,
                move_type="run",
                action="two_gap",
                target_id=blocker.id,
                intent="two_gap",
                reasoning="Two-gap technique, controlling blocker",
            )
    else:
        # One-gap: Penetrate
        # Calculate gap position (simplified)
        my_x = world.me.pos.x
        gap_x = my_x + (1 if my_x < 0 else -1)  # Slant to gap
        gap_pos = Vec2(gap_x, world.los_y + 2)

        return BrainDecision(
            move_target=gap_pos,
            move_type="sprint",
            action="penetrate",
            intent="one_gap",
            reasoning="One-gap penetration",
        )

    # Default
    return BrainDecision(
        move_target=world.me.pos + Vec2(0, 2),
        move_type="run",
        intent="engage",
        reasoning="Engaging at LOS",
    )
