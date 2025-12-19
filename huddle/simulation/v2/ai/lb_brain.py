"""Linebacker Brain - Decision-making for MLBs, OLBs, and ILBs.

The LB brain is the most versatile defensive brain, handling:
- Run/pass diagnosis
- Gap fits vs run
- Zone and man coverage
- Blitz execution
- Pursuit

Phases: PRE_SNAP → READ → RUN_FIT/COVERAGE/BLITZ → PURSUIT → TACKLE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team


# =============================================================================
# LB Enums
# =============================================================================

class PlayDiagnosis(str, Enum):
    """Diagnosed play type."""
    UNKNOWN = "unknown"
    RUN = "run"
    PASS = "pass"
    SCREEN = "screen"
    DRAW = "draw"
    RPO = "rpo"


class LBPhase(str, Enum):
    """Current phase of LB actions."""
    PRE_SNAP = "pre_snap"
    READING = "reading"
    RUN_FIT = "run_fit"
    COVERAGE = "coverage"
    BLITZ = "blitz"
    PURSUIT = "pursuit"
    TACKLE = "tackle"


class GapResponsibility(str, Enum):
    """Gap assignment."""
    A_GAP = "a_gap"
    B_GAP = "b_gap"
    C_GAP = "c_gap"
    D_GAP = "d_gap"
    NONE = "none"


class CoverageType(str, Enum):
    """Type of coverage."""
    HOOK = "hook"
    CURL = "curl"
    FLAT = "flat"
    MAN = "man"
    ROBBER = "robber"
    BLITZ = "blitz"


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class LBState:
    """Tracked state for LB decision-making."""
    phase: LBPhase = LBPhase.PRE_SNAP
    diagnosis: PlayDiagnosis = PlayDiagnosis.UNKNOWN
    read_confidence: float = 0.0
    read_complete_time: float = 0.0
    gap_assignment: GapResponsibility = GapResponsibility.NONE
    coverage_assignment: CoverageType = CoverageType.HOOK
    man_assignment_id: Optional[str] = None
    blitz_gap: Optional[GapResponsibility] = None
    pursuit_angle: float = 0.0
    blocker_id: Optional[str] = None
    # Play action response
    play_action_bite_start: float = 0.0
    is_biting_on_fake: bool = False
    play_action_recovered: bool = False
    # Throw reaction (cognitive delay before LB tracks ball)
    throw_detected_at: Optional[float] = None
    has_reacted_to_throw: bool = False
    throw_reaction_delay: float = 0.0


_lb_states: dict[str, LBState] = {}


def _get_state(player_id: str) -> LBState:
    if player_id not in _lb_states:
        _lb_states[player_id] = LBState()
    return _lb_states[player_id]


def _reset_state(player_id: str) -> None:
    _lb_states[player_id] = LBState()


# =============================================================================
# Read Keys
# =============================================================================

@dataclass
class ReadKeys:
    """Keys for run/pass diagnosis."""
    ol_high: bool = False     # OL in pass set (high hats)
    ol_low: bool = False      # OL in run block (low hats)
    guard_pulling: bool = False
    te_blocking: bool = False
    te_releasing: bool = False
    rb_to_los: bool = False   # RB heading to line
    rb_in_protection: bool = False
    qb_dropping: bool = False


def _read_keys(world: WorldState) -> ReadKeys:
    """Read offensive keys."""
    keys = ReadKeys()

    for opp in world.opponents:
        # Read OL
        if opp.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            # High hats = pass (backpedaling)
            if opp.velocity.y < -1:
                keys.ol_high = True
            # Low hats = run (forward)
            elif opp.velocity.y > 0.5:
                keys.ol_low = True
            # Guard pulling
            if opp.position in (Position.LG, Position.RG):
                if abs(opp.velocity.x) > 2:
                    keys.guard_pulling = True

        # Read TE
        if opp.position == Position.TE:
            # Releasing into route
            if opp.velocity.y > 2 and opp.pos.y > world.los_y + 2:
                keys.te_releasing = True
            # Blocking (staying near LOS)
            elif opp.pos.y < world.los_y + 2:
                keys.te_blocking = True

        # Read RB
        if opp.position == Position.RB:
            # Heading to LOS
            if opp.velocity.y > 1 and opp.pos.y < world.los_y:
                keys.rb_to_los = True
            # Setting up in protection
            elif abs(opp.velocity.y) < 1 and opp.pos.y < world.los_y - 3:
                keys.rb_in_protection = True

        # Read QB
        if opp.position == Position.QB:
            if opp.velocity.y < -1:
                keys.qb_dropping = True

    return keys


def _diagnose_play(world: WorldState, state: LBState) -> Tuple[PlayDiagnosis, float]:
    """Diagnose run vs pass.

    Returns:
        (diagnosis, confidence)
    """
    keys = _read_keys(world)
    play_rec = world.me.attributes.play_recognition

    # Calculate confidence score
    run_score = 0.0
    pass_score = 0.0

    if keys.ol_low:
        run_score += 0.3
    if keys.ol_high:
        pass_score += 0.3
    if keys.guard_pulling:
        run_score += 0.25
    if keys.te_blocking:
        run_score += 0.2
    if keys.te_releasing:
        pass_score += 0.2
    if keys.rb_to_los:
        run_score += 0.15
    if keys.rb_in_protection:
        pass_score += 0.15
    if keys.qb_dropping:
        pass_score += 0.2

    # Time to read (faster with higher play recognition)
    base_read_time = 0.4
    recognition_mod = (play_rec - 75) / 100 * 0.2
    read_time = base_read_time - recognition_mod  # 0.2s to 0.45s

    if world.time_since_snap < read_time:
        return PlayDiagnosis.UNKNOWN, 0.0

    # Apply recency bias to ambiguous reads
    # Implements cognitive science: Recent plays bias perception of ambiguous situations
    if world.play_history:
        tendency = world.play_history.get_tendency(last_n=5)
        score_diff = abs(run_score - pass_score)

        # Only bias ambiguous situations (scores within 0.3 of each other)
        if score_diff < 0.3:
            # Low play_recognition = more susceptible to bias
            # Elite LBs (85+) resist recency bias better
            bias_susceptibility = 1.0 - (play_rec - 60) / 40
            bias_susceptibility = max(0.0, min(1.0, bias_susceptibility))

            run_score += tendency['run_bias'] * bias_susceptibility
            pass_score += tendency['pass_bias'] * bias_susceptibility

    # Determine diagnosis
    total = run_score + pass_score
    if total < 0.3:
        return PlayDiagnosis.UNKNOWN, 0.0

    if run_score > pass_score + 0.2:
        return PlayDiagnosis.RUN, min(1.0, run_score)
    elif pass_score > run_score + 0.2:
        return PlayDiagnosis.PASS, min(1.0, pass_score)
    else:
        return PlayDiagnosis.UNKNOWN, max(run_score, pass_score) * 0.5


# =============================================================================
# Play Action Response
# =============================================================================

def _get_bite_duration(play_recognition: int) -> float:
    """How long LB bites on play action based on play recognition.

    Higher play recognition = quicker to diagnose fake and recover.

    Returns:
        Bite duration in seconds
    """
    if play_recognition >= 85:
        return 0.15  # Minimal bite, quick recovery
    elif play_recognition >= 75:
        return 0.4   # Moderate bite
    elif play_recognition >= 65:
        return 0.65  # Significant bite
    else:
        return 0.9   # Full bite, late recovery


def _detect_play_action(world: WorldState, keys: ReadKeys) -> bool:
    """Detect play action fake.

    Play action indicators:
    - RB moved toward LOS (run fake)
    - QB is dropping back (pass)
    - RB doesn't have the ball

    Returns:
        True if play action detected
    """
    if not keys.rb_to_los:
        return False
    if not keys.qb_dropping:
        return False

    # Check if RB has the ball
    for opp in world.opponents:
        if opp.position == Position.RB and opp.has_ball:
            return False  # Actually a run

    return True


def _rb_has_ball(world: WorldState) -> bool:
    """Check if RB has the ball."""
    for opp in world.opponents:
        if opp.position == Position.RB and opp.has_ball:
            return True
    return False


# =============================================================================
# Run Fit
# =============================================================================

def _find_ballcarrier(world: WorldState) -> Optional[PlayerView]:
    """Find the ballcarrier."""
    for opp in world.opponents:
        if opp.has_ball:
            return opp
    return None


def _get_gap_position(world: WorldState, gap: GapResponsibility) -> Vec2:
    """Get the position of a gap."""
    los = world.los_y

    # Simplified gap positions
    gap_positions = {
        GapResponsibility.A_GAP: Vec2(0.5, los),
        GapResponsibility.B_GAP: Vec2(2.5, los),
        GapResponsibility.C_GAP: Vec2(5.0, los),
        GapResponsibility.D_GAP: Vec2(7.5, los),
    }

    return gap_positions.get(gap, Vec2(0, los))


def _find_my_gap(world: WorldState) -> GapResponsibility:
    """Determine assigned gap based on position and alignment."""
    my_pos = world.me.pos
    position = world.me.position

    # Simplified assignment based on position
    if position == Position.MLB:
        return GapResponsibility.A_GAP
    elif position == Position.OLB:
        return GapResponsibility.C_GAP if my_pos.x > 0 else GapResponsibility.B_GAP
    elif position == Position.ILB:
        return GapResponsibility.B_GAP

    return GapResponsibility.B_GAP


def _calculate_pursuit_angle(my_pos: Vec2, bc_pos: Vec2, bc_vel: Vec2, my_speed: float) -> Vec2:
    """Calculate pursuit angle to intercept ballcarrier."""
    if bc_vel.length() < 0.5:
        return bc_pos

    # Predict where ballcarrier will be
    time_estimates = [0.5, 1.0, 1.5, 2.0]

    for t in time_estimates:
        predicted = bc_pos + bc_vel * t
        my_dist = my_pos.distance_to(predicted)
        my_time = my_dist / my_speed if my_speed > 0 else 10.0

        if my_time <= t + 0.2:  # Can intercept
            return predicted

    # Can't intercept - just chase
    return bc_pos + bc_vel * 0.5


# =============================================================================
# Coverage
# =============================================================================

def _get_zone_position(world: WorldState, zone: CoverageType) -> Vec2:
    """Get the position for zone coverage."""
    my_pos = world.me.pos
    los = world.los_y

    zone_depths = {
        CoverageType.HOOK: 12,
        CoverageType.CURL: 14,
        CoverageType.FLAT: 6,
        CoverageType.ROBBER: 10,
    }

    depth = zone_depths.get(zone, 10)
    x = my_pos.x * 0.5  # Shade toward middle

    return Vec2(x, los + depth)


def _find_receiver_in_zone(world: WorldState, zone_pos: Vec2) -> Optional[PlayerView]:
    """Find a receiver entering our zone."""
    zone_radius = 5.0

    for opp in world.opponents:
        if opp.position not in (Position.WR, Position.TE, Position.RB):
            continue

        if opp.pos.distance_to(zone_pos) < zone_radius:
            return opp

    return None


def _find_man_assignment(world: WorldState) -> Optional[PlayerView]:
    """Find our man assignment (usually TE or RB)."""
    my_pos = world.me.pos

    # LBs typically cover TE or RB
    for opp in world.opponents:
        if opp.position in (Position.TE, Position.RB):
            dist = opp.pos.distance_to(my_pos)
            if dist < 15:  # Close enough to be our man
                return opp

    return None


# =============================================================================
# Throw Reaction Delay (Cognitive delay before LB tracks ball)
# =============================================================================

def _calculate_lb_throw_reaction_delay(world: WorldState) -> float:
    """Calculate time before LB reacts to throw.

    LBs are often slower than DBs to react to throws because:
    - They're watching for run first
    - They're closer to the LOS and may be engaged
    - They have more responsibilities to process

    Returns delay in seconds.
    """
    # Base reaction time - LBs have slightly longer base than DBs
    base_delay = 0.25

    # Awareness affects reaction time
    awareness = getattr(world.me.attributes, 'awareness', 75)
    awareness_modifier = (90 - awareness) / 100 * 0.4
    awareness_modifier = max(0.0, awareness_modifier)

    # Play recognition helps LBs read the throw faster
    play_rec = getattr(world.me.attributes, 'play_recognition', 75)
    play_rec_modifier = (85 - play_rec) / 100 * 0.2
    play_rec_modifier = max(0.0, play_rec_modifier)

    # Can LB see the QB? Check facing direction
    qb = None
    for opp in world.opponents:
        if opp.position == Position.QB:
            qb = opp
            break

    facing_modifier = 0.0
    if qb:
        to_qb = (qb.pos - world.me.pos).normalized()
        facing = world.me.facing

        dot = facing.dot(to_qb) if facing.length() > 0 else 0

        if dot < 0:
            facing_modifier = 0.12  # Facing away
        elif dot < 0.5:
            facing_modifier = 0.06  # Partially turned

    return base_delay + awareness_modifier + play_rec_modifier + facing_modifier


def _can_lb_track_ball_yet(world: WorldState, state: 'LBState') -> bool:
    """Check if enough time has passed for LB to react to the throw."""
    if state.has_reacted_to_throw:
        return True

    if state.throw_detected_at is None:
        state.throw_detected_at = world.current_time
        state.throw_reaction_delay = _calculate_lb_throw_reaction_delay(world)
        return False

    elapsed = world.current_time - state.throw_detected_at
    if elapsed >= state.throw_reaction_delay:
        state.has_reacted_to_throw = True
        return True

    return False


# =============================================================================
# Blitz
# =============================================================================

def _get_blitz_path(world: WorldState, gap: GapResponsibility) -> Vec2:
    """Get blitz path through assigned gap."""
    gap_pos = _get_gap_position(world, gap)

    # Find QB
    qb_pos = Vec2(0, world.los_y - 7)
    for opp in world.opponents:
        if opp.position == Position.QB:
            qb_pos = opp.pos
            break

    # Path through gap toward QB
    return gap_pos.lerp(qb_pos, 0.5)


# =============================================================================
# Main Brain Function
# =============================================================================

def lb_brain(world: WorldState) -> BrainDecision:
    """Linebacker brain - called every tick for MLBs, OLBs, and ILBs.

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
        state.gap_assignment = _find_my_gap(world)
        state.coverage_assignment = CoverageType.HOOK  # Default

    # Check if ball carrier exists - pursuit mode
    ballcarrier = _find_ballcarrier(world)

    # =========================================================================
    # Pursuit Mode (ball past LOS or caught)
    # =========================================================================
    if ballcarrier and (ballcarrier.pos.y > world.los_y or world.phase == PlayPhase.AFTER_CATCH):
        state.phase = LBPhase.PURSUIT

        # Calculate pursuit angle
        my_speed = 5.0 + (world.me.attributes.speed - 75) * 0.1
        intercept = _calculate_pursuit_angle(
            world.me.pos, ballcarrier.pos, ballcarrier.velocity, my_speed
        )

        dist = world.me.pos.distance_to(ballcarrier.pos)

        if dist < 2.0:
            state.phase = LBPhase.TACKLE
            return BrainDecision(
                move_target=ballcarrier.pos,
                move_type="sprint",
                action="tackle",
                target_id=ballcarrier.id,
                intent="tackle",
                reasoning=f"Tackling ballcarrier at {dist:.1f}yd",
            )

        return BrainDecision(
            move_target=intercept,
            move_type="sprint",
            intent="pursuit",
            target_id=ballcarrier.id,
            reasoning=f"Pursuing at angle, {dist:.1f}yd from ballcarrier",
        )

    # =========================================================================
    # Blitz Execution (if assigned)
    # =========================================================================
    if state.blitz_gap:
        state.phase = LBPhase.BLITZ

        blitz_path = _get_blitz_path(world, state.blitz_gap)

        return BrainDecision(
            move_target=blitz_path,
            move_type="sprint",
            action="blitz",
            intent="blitz",
            reasoning=f"Blitzing through {state.blitz_gap.value}",
        )

    # =========================================================================
    # Read Phase
    # =========================================================================
    if state.diagnosis == PlayDiagnosis.UNKNOWN:
        state.phase = LBPhase.READING

        diagnosis, confidence = _diagnose_play(world, state)

        if confidence >= 0.5:
            state.diagnosis = diagnosis
            state.read_confidence = confidence
            state.read_complete_time = world.current_time

        return BrainDecision(
            intent="reading",
            reasoning=f"Reading keys... ({world.time_since_snap:.2f}s)",
        )

    # =========================================================================
    # Play Action Response
    # =========================================================================
    keys = _read_keys(world)
    play_rec = world.me.attributes.play_recognition

    # Detect play action and start biting
    if state.diagnosis == PlayDiagnosis.RUN and not state.play_action_recovered:
        if _detect_play_action(world, keys) and not state.is_biting_on_fake:
            # Start biting on the play action fake
            state.is_biting_on_fake = True
            state.play_action_bite_start = world.current_time

        if state.is_biting_on_fake:
            bite_duration = _get_bite_duration(play_rec)
            time_biting = world.current_time - state.play_action_bite_start

            if time_biting < bite_duration:
                # Still biting - commit toward gap as if it's a run
                gap_pos = _get_gap_position(world, state.gap_assignment)
                return BrainDecision(
                    move_target=gap_pos,
                    move_type="sprint",
                    intent="run_fit",
                    reasoning=f"Biting on play action ({time_biting:.2f}s / {bite_duration:.2f}s)",
                )
            else:
                # Recovered from fake - re-diagnose as pass
                state.is_biting_on_fake = False
                state.play_action_recovered = True
                state.diagnosis = PlayDiagnosis.PASS
                # Fall through to pass response

    # =========================================================================
    # Run Response
    # =========================================================================
    if state.diagnosis == PlayDiagnosis.RUN:
        state.phase = LBPhase.RUN_FIT

        gap_pos = _get_gap_position(world, state.gap_assignment)

        # Check for blocker
        for opp in world.opponents:
            if opp.position in (Position.LG, Position.RG, Position.C, Position.FB):
                if opp.pos.distance_to(gap_pos) < 3:
                    state.blocker_id = opp.id
                    break

        if state.blocker_id:
            # Take on blocker
            return BrainDecision(
                move_target=gap_pos,
                move_type="run",
                action="fit_gap",
                intent="run_fit",
                target_id=state.blocker_id,
                reasoning=f"Fitting {state.gap_assignment.value}, engaging blocker",
            )

        return BrainDecision(
            move_target=gap_pos,
            move_type="sprint",
            action="fit_gap",
            intent="run_fit",
            reasoning=f"Filling {state.gap_assignment.value}",
        )

    # =========================================================================
    # Pass Response (Zone or Man Coverage)
    # =========================================================================
    if state.diagnosis == PlayDiagnosis.PASS:
        state.phase = LBPhase.COVERAGE

        # Zone coverage
        if state.coverage_assignment != CoverageType.MAN:
            zone_pos = _get_zone_position(world, state.coverage_assignment)

            # Check for receiver in zone
            receiver = _find_receiver_in_zone(world, zone_pos)

            if receiver:
                return BrainDecision(
                    move_target=receiver.pos,
                    move_type="run",
                    intent="zone_cover",
                    target_id=receiver.id,
                    reasoning=f"Receiver in {state.coverage_assignment.value} zone",
                )

            # Ball thrown - break on it (with reaction delay)
            if world.ball.is_in_flight:
                if world.ball.flight_target:
                    target = world.ball.flight_target

                    # Check if LB has had time to react to the throw
                    if not _can_lb_track_ball_yet(world, state):
                        # Still processing throw - continue zone drop
                        delay_remaining = state.throw_reaction_delay - (
                            world.current_time - (state.throw_detected_at or world.current_time)
                        )
                        return BrainDecision(
                            move_target=zone_pos,
                            move_type="run",
                            intent="zone_drop",
                            reasoning=f"Reacting to throw ({delay_remaining:.2f}s)",
                        )

                    # Reacted - now check if ball is in our zone
                    if target.distance_to(zone_pos) < 8:
                        return BrainDecision(
                            move_target=target,
                            move_type="sprint",
                            action="break_on_ball",
                            intent="zone_break",
                            reasoning="Ball thrown to zone, breaking!",
                        )

            return BrainDecision(
                move_target=zone_pos,
                move_type="run",
                intent="zone_drop",
                reasoning=f"Dropping to {state.coverage_assignment.value} zone",
            )

        # Man coverage
        else:
            man = _find_man_assignment(world)

            if man:
                dist = world.me.pos.distance_to(man.pos)

                return BrainDecision(
                    move_target=man.pos,
                    move_type="run" if dist > 5 else "sprint",
                    intent="man_cover",
                    target_id=man.id,
                    reasoning=f"Man coverage on {man.position.value}, {dist:.1f}yd away",
                )

    # Default: hold position
    return BrainDecision(
        intent="hold",
        reasoning="Holding position",
    )
