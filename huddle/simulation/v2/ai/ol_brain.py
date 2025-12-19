"""Offensive Line Brain - Decision-making for OL.

The OL brain controls tackles, guards, and centers in:
- Pass protection
- Run blocking
- Stunt pickup
- Communication (conceptual)

Phases: PRE_SNAP → PASS_SET/RUN_BLOCK → ENGAGE → SUSTAIN
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team


# =============================================================================
# OL Enums
# =============================================================================

class ProtectionScheme(str, Enum):
    """Pass protection scheme."""
    MAN = "man"       # Assigned blocker
    ZONE = "zone"     # Zone responsibility
    SLIDE = "slide"   # Slide protection


class RunScheme(str, Enum):
    """Run blocking scheme."""
    ZONE = "zone"     # Zone blocking
    GAP = "gap"       # Gap/power blocking
    COUNTER = "counter"
    PULL = "pull"


class OLPhase(str, Enum):
    """Current phase of OL action."""
    PRE_SNAP = "pre_snap"
    PASS_SET = "pass_set"
    ENGAGED = "engaged"
    RUN_BLOCK = "run_block"
    PULLING = "pulling"
    SECOND_LEVEL = "second_level"


class BlockCounter(str, Enum):
    """Counter technique vs rush moves."""
    ANCHOR = "anchor"
    PUNCH = "punch"
    MIRROR = "mirror"
    REFIT = "refit"


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class OLState:
    """Tracked state for OL decision-making."""
    phase: OLPhase = OLPhase.PRE_SNAP
    scheme: ProtectionScheme = ProtectionScheme.MAN
    assigned_defender_id: Optional[str] = None
    is_engaged: bool = False
    rep_status: str = "neutral"  # winning, neutral, losing
    stunt_detected: bool = False
    run_scheme: Optional[RunScheme] = None
    is_pulling: bool = False
    # Combo block tracking
    combo_partner_id: Optional[str] = None  # OL we're working combo with
    combo_target_id: Optional[str] = None   # DL we're combo blocking
    should_climb: bool = False              # Time to release to second level
    # Stunt tracking
    original_assignment_id: Optional[str] = None  # Who we were assigned before stunt
    switched_assignment: bool = False             # Did we switch for stunt pickup


@dataclass
class ProtectionCall:
    """Shared protection call made by Center."""
    mike_id: Optional[str] = None      # Identified MIKE linebacker
    mike_position: Optional[Vec2] = None
    front_type: str = "unknown"        # "4-3", "3-4", "nickel", "bear", etc.
    blitz_threat: str = "none"         # "none", "left", "right", "a_gap", "overload"
    slide_direction: str = "none"      # "left", "right", or "none"


# Module-level state
_ol_states: dict[str, OLState] = {}
_protection_call: Optional[ProtectionCall] = None  # Shared by all OL


def _get_state(player_id: str) -> OLState:
    if player_id not in _ol_states:
        _ol_states[player_id] = OLState()
    return _ol_states[player_id]


def _reset_state(player_id: str) -> None:
    _ol_states[player_id] = OLState()


def _reset_protection_call() -> None:
    """Reset protection call at start of play."""
    global _protection_call
    _protection_call = None


def _get_protection_call() -> Optional[ProtectionCall]:
    """Get current protection call."""
    return _protection_call


# =============================================================================
# MIKE Identification System
# =============================================================================

def _identify_mike(world: WorldState) -> ProtectionCall:
    """Center identifies the MIKE linebacker and reads the defensive front.

    The MIKE is the key linebacker for protection assignments. Usually:
    - In 4-3: Middle linebacker
    - In 3-4: Strong side inside linebacker
    - In Nickel: Remaining linebacker

    Returns:
        ProtectionCall with MIKE id, front type, and slide direction
    """
    call = ProtectionCall()

    # Count DL and LBs to identify front
    dl_count = 0
    lbs = []

    for opp in world.opponents:
        if opp.position in (Position.DE, Position.DT, Position.NT):
            dl_count += 1
        elif opp.position in (Position.MLB, Position.ILB, Position.OLB):
            lbs.append(opp)

    # Identify front type
    if dl_count >= 4:
        call.front_type = "4-3" if len(lbs) >= 3 else "nickel"
    elif dl_count == 3:
        call.front_type = "3-4" if len(lbs) >= 4 else "3-3"
    else:
        call.front_type = "bear" if dl_count >= 5 else "unknown"

    # Find MIKE - typically the most central LB
    if lbs:
        # Sort by distance from center (x=0)
        lbs_sorted = sorted(lbs, key=lambda lb: abs(lb.pos.x))
        mike = lbs_sorted[0]  # Most central
        call.mike_id = mike.id
        call.mike_position = mike.pos

    # Detect blitz threat based on LB positioning
    for lb in lbs:
        if lb.pos.y < world.los_y + 3:  # LB walked up
            if lb.pos.x < -2:
                call.blitz_threat = "left"
            elif lb.pos.x > 2:
                call.blitz_threat = "right"
            else:
                call.blitz_threat = "a_gap"
            break

    # Set slide direction away from blitz threat
    if call.blitz_threat == "left":
        call.slide_direction = "right"
    elif call.blitz_threat == "right":
        call.slide_direction = "left"

    return call


def _should_center_make_call(world: WorldState) -> bool:
    """Check if this player is the Center and should make protection call."""
    return world.me.position == Position.C


# =============================================================================
# Combo Block System
# =============================================================================

def _find_combo_opportunity(world: WorldState) -> tuple[Optional[str], Optional[str]]:
    """Find if we should combo block with adjacent OL.

    Combo blocks happen when:
    - DL is shaded between two OL
    - Both OL can reach the DL
    - There's a LB to climb to after winning combo

    Returns:
        (partner_ol_id, target_dl_id) or (None, None)
    """
    my_pos = world.me.pos
    my_position = world.me.position

    # Define adjacent positions
    adjacent_positions = {
        Position.LT: [Position.LG],
        Position.LG: [Position.LT, Position.C],
        Position.C: [Position.LG, Position.RG],
        Position.RG: [Position.C, Position.RT],
        Position.RT: [Position.RG],
    }

    if my_position not in adjacent_positions:
        return None, None

    # Find adjacent OL teammates
    adjacent_ol = []
    for tm in world.teammates:
        if tm.position in adjacent_positions[my_position]:
            adjacent_ol.append(tm)

    if not adjacent_ol:
        return None, None

    # Find DL between me and adjacent OL
    for partner in adjacent_ol:
        midpoint = (my_pos + partner.pos) * 0.5

        for opp in world.opponents:
            if opp.position not in (Position.DE, Position.DT, Position.NT):
                continue

            # DL is between us (within 2 yards of midpoint)
            if opp.pos.distance_to(midpoint) < 2.0:
                # Check there's a LB to climb to
                for lb in world.opponents:
                    if lb.position in (Position.MLB, Position.ILB, Position.OLB):
                        if lb.pos.y > world.los_y + 2 and lb.pos.distance_to(midpoint) < 8:
                            return partner.id, opp.id

    return None, None


def _should_climb_from_combo(world: WorldState, state: OLState) -> bool:
    """Determine if we should release from combo to second level.

    Climb when:
    - Partner has control of DL (DL moving away from QB)
    - LB is filling toward hole
    - Combo has been engaged for sufficient time
    """
    if not state.combo_target_id or not state.combo_partner_id:
        return False

    # Find combo target DL
    dl = None
    for opp in world.opponents:
        if opp.id == state.combo_target_id:
            dl = opp
            break

    if not dl:
        return False

    # Check if DL is being driven back (positive y velocity = away from QB)
    if dl.velocity.y > 0.5:
        # Partner has control, time to climb
        return True

    # Check time engaged - after 0.8s, one should climb
    if world.time_since_snap > 0.8:
        # Higher numbered position climbs (RG climbs over LG, etc.)
        # Simplified: position with higher x value climbs
        partner = None
        for tm in world.teammates:
            if tm.id == state.combo_partner_id:
                partner = tm
                break

        if partner and world.me.pos.x > partner.pos.x:
            return True

    return False


# =============================================================================
# Stunt Detection and Pickup
# =============================================================================

def _detect_stunt(world: WorldState, state: OLState) -> Optional[str]:
    """Detect if DL are running a stunt (twist).

    Common stunts:
    - T/E: Tackle crashes inside, End loops behind
    - E/T: End crashes inside, Tackle loops outside
    - Twist: Two DL swap gaps

    Returns:
        "te_stunt", "et_stunt", "twist", or None
    """
    if not state.assigned_defender_id:
        return None

    # Find our assigned DL
    assigned_dl = None
    for opp in world.opponents:
        if opp.id == state.assigned_defender_id:
            assigned_dl = opp
            break

    if not assigned_dl:
        return None

    my_pos = world.me.pos

    # Stunt indicators:
    # 1. Our DL is moving laterally away from us
    # 2. Another DL is moving into our gap

    lateral_movement = abs(assigned_dl.velocity.x)
    moving_away = False

    if world.me.position in (Position.LT, Position.LG):
        # Left side - DL moving right (positive x) is looping
        moving_away = assigned_dl.velocity.x > 2.0
    elif world.me.position in (Position.RT, Position.RG):
        # Right side - DL moving left (negative x) is looping
        moving_away = assigned_dl.velocity.x < -2.0

    if moving_away and lateral_movement > 2.0:
        # Our guy is looping - check if someone is crashing our gap
        for opp in world.opponents:
            if opp.id == assigned_dl.id:
                continue
            if opp.position not in (Position.DE, Position.DT, Position.NT):
                continue

            # Is this DL crashing toward our gap?
            dist_to_me = opp.pos.distance_to(my_pos)
            if dist_to_me < 3.0:
                # Stunt detected
                if assigned_dl.position == Position.DT:
                    return "te_stunt"  # Tackle looping, End crashing
                else:
                    return "et_stunt"  # End looping, Tackle crashing

    return None


def _get_stunt_pickup_assignment(world: WorldState, state: OLState, stunt_type: str) -> Optional[str]:
    """Get new assignment for stunt pickup.

    When stunt detected, OL switch assignments:
    - Original blocker takes crasher
    - Adjacent blocker takes looper

    Returns:
        New defender ID to block
    """
    my_pos = world.me.pos

    # Find the crasher (DL coming into our gap)
    for opp in world.opponents:
        if opp.position not in (Position.DE, Position.DT, Position.NT):
            continue
        if opp.id == state.assigned_defender_id:
            continue

        dist = opp.pos.distance_to(my_pos)
        # Is crasher coming at us?
        if dist < 3.0:
            to_me = (my_pos - opp.pos).normalized()
            closing = opp.velocity.dot(to_me)
            if closing > 1.0:  # Moving toward us
                return opp.id

    return None


# =============================================================================
# Helper Functions
# =============================================================================

def _find_rusher(world: WorldState) -> Optional[PlayerView]:
    """Find the defender rushing us."""
    my_pos = world.me.pos
    closest = None
    closest_dist = float('inf')

    for tm in world.opponents:  # Defense (we're offense)
        if tm.position in (Position.DE, Position.DT, Position.NT, Position.OLB, Position.MLB):
            dist = tm.pos.distance_to(my_pos)
            if dist < closest_dist and dist < 5.0:
                closest_dist = dist
                closest = tm

    return closest


def _find_assigned_by_position(world: WorldState) -> Optional[PlayerView]:
    """Find defender based on our position."""
    my_pos = world.me.pos
    my_position = world.me.position

    # Simplified assignment based on alignment
    target_x_offset = 0
    if my_position == Position.LT:
        target_x_offset = 3
    elif my_position == Position.LG:
        target_x_offset = 1.5
    elif my_position == Position.C:
        target_x_offset = 0
    elif my_position == Position.RG:
        target_x_offset = -1.5
    elif my_position == Position.RT:
        target_x_offset = -3

    # Find defender near our assignment area
    target_pos = Vec2(my_pos.x + target_x_offset, world.los_y + 1)

    closest = None
    closest_dist = float('inf')

    for opp in world.opponents:
        if opp.position in (Position.DE, Position.DT, Position.NT, Position.OLB, Position.MLB, Position.ILB):
            dist = opp.pos.distance_to(target_pos)
            if dist < closest_dist and dist < 4.0:
                closest_dist = dist
                closest = opp

    return closest


def _is_pass_play(world: WorldState) -> bool:
    """Determine if this is a pass play (from our perspective)."""
    # Check if we got a pass protection assignment
    if "pass" in world.assignment.lower() or "protect" in world.assignment.lower():
        return True

    # Check QB action
    for opp in world.opponents:
        if opp.position == Position.QB:
            if opp.velocity.y < -1:  # Dropping back
                return True
            if opp.has_ball and world.time_since_snap > 0.3:
                return True

    return True  # Default to pass protection


def _detect_rush_move(rusher: Optional[PlayerView]) -> Optional[str]:
    """Detect what rush move the defender is using."""
    if not rusher:
        return None

    # Simplified detection
    if rusher.velocity.length() > 5:
        return "speed_rush"
    elif rusher.velocity.y > 2:
        return "bull_rush"

    return None


def _get_counter_for_move(move: Optional[str]) -> BlockCounter:
    """Get the appropriate counter for a rush move."""
    counters = {
        "bull_rush": BlockCounter.ANCHOR,
        "swim": BlockCounter.PUNCH,
        "spin": BlockCounter.REFIT,
        "speed_rush": BlockCounter.MIRROR,
        "rip": BlockCounter.REFIT,
    }
    return counters.get(move, BlockCounter.PUNCH)


def _get_kick_slide_depth(world: WorldState, rusher: Optional[PlayerView]) -> float:
    """Calculate pass set depth based on rusher."""
    base_depth = 3.0  # 3 yards behind LOS

    if rusher:
        # Deeper vs speed rusher (estimate from their current speed)
        if rusher.speed > 6.0:  # Fast rusher
            base_depth = 4.0

    return base_depth


def _get_zone_block_target(world: WorldState) -> Vec2:
    """Get target for zone blocking."""
    my_pos = world.me.pos

    # Zone step playside (simplified: assume right)
    return Vec2(my_pos.x + 1, world.los_y + 2)


def _find_second_level_target(world: WorldState) -> Optional[PlayerView]:
    """Find LB to block at second level."""
    my_pos = world.me.pos

    for opp in world.opponents:  # LBs are opponents (defense)
        if opp.position in (Position.MLB, Position.ILB, Position.OLB):
            dist = opp.pos.distance_to(my_pos)
            if dist < 8 and opp.pos.y > world.los_y:
                return opp

    return None


# =============================================================================
# Main Brain Function
# =============================================================================

def ol_brain(world: WorldState) -> BrainDecision:
    """Offensive line brain - for tackles, guards, and centers.

    Features:
    - MIKE identification (Center makes protection call)
    - Combo blocks (two OL work DL, one climbs to LB)
    - Stunt pickup (detect twists, switch assignments)

    Args:
        world: Complete world state

    Returns:
        BrainDecision with action and reasoning
    """
    global _protection_call

    state = _get_state(world.me.id)

    # Reset at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        _reset_protection_call()
        state = _get_state(world.me.id)

    # =========================================================================
    # MIKE Identification (Center makes call for all OL)
    # =========================================================================
    if _should_center_make_call(world) and _protection_call is None:
        _protection_call = _identify_mike(world)

    # Find our assignment (use protection call if available)
    rusher = _find_rusher(world)
    if rusher:
        state.assigned_defender_id = rusher.id
        state.original_assignment_id = rusher.id

    # =========================================================================
    # Pass Protection
    # =========================================================================
    if _is_pass_play(world):
        # Pass set phase (first 0.5s)
        if world.time_since_snap < 0.5:
            state.phase = OLPhase.PASS_SET

            # Calculate set depth
            set_depth = _get_kick_slide_depth(world, rusher)
            set_pos = Vec2(world.me.pos.x, world.los_y - set_depth)

            # Include MIKE call in reasoning if we're Center
            mike_info = ""
            if _protection_call and _should_center_make_call(world):
                mike_info = f" [MIKE: {_protection_call.front_type}, blitz: {_protection_call.blitz_threat}]"

            return BrainDecision(
                move_target=set_pos,
                move_type="backpedal",
                intent="pass_set",
                reasoning=f"Setting at {set_depth:.1f}yd depth{mike_info}",
            )

        # =====================================================================
        # Stunt Detection and Pickup
        # =====================================================================
        stunt = _detect_stunt(world, state)
        if stunt and not state.switched_assignment:
            new_assignment = _get_stunt_pickup_assignment(world, state, stunt)
            if new_assignment:
                state.stunt_detected = True
                state.switched_assignment = True
                state.assigned_defender_id = new_assignment

                # Find the new target
                for opp in world.opponents:
                    if opp.id == new_assignment:
                        return BrainDecision(
                            move_target=opp.pos,
                            move_type="run",
                            action="pickup",
                            target_id=new_assignment,
                            intent="stunt_pickup",
                            reasoning=f"Stunt pickup! Switching to crasher ({stunt})",
                        )

        # Engaged phase
        if rusher:
            state.phase = OLPhase.ENGAGED
            state.is_engaged = True

            dist = world.me.pos.distance_to(rusher.pos)

            # Kick slide to rusher
            if dist > 2.0:
                return BrainDecision(
                    move_target=rusher.pos + Vec2(0, -1),
                    move_type="run",
                    action="kick_slide",
                    target_id=rusher.id,
                    intent="close_distance",
                    reasoning=f"Kick sliding to rusher ({dist:.1f}yd)",
                )

            # Engaged - counter moves
            rush_move = _detect_rush_move(rusher)
            counter = _get_counter_for_move(rush_move)

            # Maintain position between rusher and QB
            qb_pos = Vec2(0, world.los_y - 7)  # Assume QB dropback
            for tm in world.teammates:
                if tm.position == Position.QB:
                    qb_pos = tm.pos
                    break

            # Position to protect QB
            protect_pos = rusher.pos + (qb_pos - rusher.pos).normalized() * 1.5

            return BrainDecision(
                move_target=protect_pos,
                move_type="run",
                action=counter.value,
                target_id=rusher.id,
                intent="block",
                reasoning=f"Blocking, {counter.value} vs {rush_move or 'rush'}",
            )

        # No rusher - look for blitzing LB (use MIKE call)
        if _protection_call and _protection_call.mike_id:
            mike = None
            for opp in world.opponents:
                if opp.id == _protection_call.mike_id:
                    mike = opp
                    break

            if mike and mike.pos.y < world.los_y + 2:
                # MIKE is blitzing
                return BrainDecision(
                    move_target=mike.pos,
                    move_type="run",
                    action="pickup",
                    target_id=mike.id,
                    intent="blitz_pickup",
                    reasoning="MIKE blitzing, picking up",
                )

        return BrainDecision(
            intent="look_for_work",
            reasoning="No immediate threat, looking for work",
        )

    # =========================================================================
    # Run Blocking
    # =========================================================================
    state.phase = OLPhase.RUN_BLOCK

    # Check if pulling
    if state.is_pulling:
        state.phase = OLPhase.PULLING

        # Pull to playside
        pull_target = Vec2(5, world.los_y + 3)  # Simplified

        return BrainDecision(
            move_target=pull_target,
            move_type="sprint",
            action="pull",
            intent="pulling",
            reasoning="Pulling to hole",
        )

    # =========================================================================
    # Combo Block Logic
    # =========================================================================

    # Check if we should climb from existing combo
    if state.combo_partner_id and state.combo_target_id:
        if _should_climb_from_combo(world, state):
            state.should_climb = True
            lb = _find_second_level_target(world)
            if lb:
                state.phase = OLPhase.SECOND_LEVEL
                # Clear combo state
                state.combo_partner_id = None
                state.combo_target_id = None

                return BrainDecision(
                    move_target=lb.pos,
                    move_type="sprint",
                    action="climb",
                    target_id=lb.id,
                    intent="combo_climb",
                    reasoning="Releasing from combo to second level!",
                )

    # Check for new combo opportunity
    if not state.combo_partner_id:
        partner_id, dl_id = _find_combo_opportunity(world)
        if partner_id and dl_id:
            state.combo_partner_id = partner_id
            state.combo_target_id = dl_id

            # Find the DL to combo
            for opp in world.opponents:
                if opp.id == dl_id:
                    return BrainDecision(
                        move_target=opp.pos,
                        move_type="run",
                        action="combo",
                        target_id=dl_id,
                        intent="combo_block",
                        reasoning=f"Combo blocking with partner to DL",
                    )

    # Active combo block (working with partner on DL)
    if state.combo_target_id:
        for opp in world.opponents:
            if opp.id == state.combo_target_id:
                # Double-team the DL
                return BrainDecision(
                    move_target=opp.pos,
                    move_type="run",
                    action="double",
                    target_id=opp.id,
                    intent="combo_block",
                    reasoning="Double-teaming in combo",
                )

    # Standard zone blocking
    if rusher and rusher.pos.distance_to(world.me.pos) < 3:
        # Engaged with DL - drive block
        drive_dir = (rusher.pos - world.me.pos).normalized()
        drive_target = rusher.pos + drive_dir * 2

        return BrainDecision(
            move_target=drive_target,
            move_type="run",
            action="drive",
            target_id=rusher.id,
            intent="drive_block",
            reasoning="Drive blocking defender",
        )

    # Uncovered - climb to second level
    lb = _find_second_level_target(world)
    if lb:
        state.phase = OLPhase.SECOND_LEVEL

        return BrainDecision(
            move_target=lb.pos,
            move_type="run",
            action="climb",
            target_id=lb.id,
            intent="second_level",
            reasoning="Climbing to block LB",
        )

    # Zone step
    zone_target = _get_zone_block_target(world)

    return BrainDecision(
        move_target=zone_target,
        move_type="run",
        action="zone_step",
        intent="zone_block",
        reasoning="Zone stepping playside",
    )
