"""Offensive Line Brain - Decision-making for OL.

INTERCEPT-PATH PHILOSOPHY:
OL don't chase DL. They position BETWEEN DL and the ball/QB.
Engagement happens as a SIDE EFFECT when DL runs into the OL
who is in their path. OL success = DL doesn't reach target.

The OL brain controls tackles, guards, and centers in:
- Pass protection: Position between rusher and QB
- Run blocking: Create lanes, seal defenders from ball
- Stunt pickup: React to changing threats
- Communication: MIKE calls, slide direction

Key insight: We don't "find and fight" - we intercept paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import OLContext
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from ..core.trace import get_trace_system, TraceCategory


# =============================================================================
# Trace Helper
# =============================================================================

def _trace(world: WorldState, msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace for this OL."""
    trace = get_trace_system()
    trace.trace(world.me.id, world.me.name, category, msg)


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

def _is_dl_in_pursuit(opp: PlayerView, world: WorldState) -> bool:
    """Check if a DL is in pursuit mode (chasing ballcarrier past LOS).

    OL should NOT chase DL that are in pursuit - instead hold position or lead block.
    """
    # DL is past LOS and moving further downfield
    if opp.pos.y > world.los_y + 2.0 and opp.velocity.y > 1.0:
        return True

    # DL is running horizontally across formation (chasing ball)
    if abs(opp.velocity.x) > 3.0 and abs(opp.velocity.y) > 1.0:
        return True

    return False


# =============================================================================
# Intercept-Path Functions
# =============================================================================

def _get_protect_target(world: WorldState) -> Vec2:
    """Get the position we're protecting (QB or ballcarrier).

    Returns:
        Position of the player we need to keep DL away from.
    """
    # Find QB
    for tm in world.teammates:
        if tm.position == Position.QB:
            return tm.pos

    # Fallback to pocket area
    return Vec2(0, world.los_y - 5)


def _calculate_intercept_position(
    my_pos: Vec2,
    threat_pos: Vec2,
    threat_vel: Vec2,
    protect_pos: Vec2,
    world: WorldState
) -> Vec2:
    """Calculate where OL should position to intercept DL's path to target.

    The OL doesn't chase the DL - they position BETWEEN DL and the target.
    Engagement happens when DL runs into OL.

    Args:
        my_pos: Our current position
        threat_pos: DL position
        threat_vel: DL velocity
        protect_pos: Position we're protecting (QB/ball)
        world: World state for LOS reference

    Returns:
        Position to move to that intercepts DL's path
    """
    # Calculate DL's likely target path (toward protect_pos)
    dl_to_target = protect_pos - threat_pos
    if dl_to_target.length() < 0.1:
        return my_pos  # DL is on target, hold

    dl_direction = dl_to_target.normalized()

    # Position on the line between DL and target
    # Closer to DL = more aggressive, closer to target = more conservative
    # Standard pass pro: meet them ~2 yards in front of protect pos

    # Calculate point on DL's path that we can reach
    dist_dl_to_target = dl_to_target.length()

    # We want to be ~60% of the way from DL to target (meeting point)
    intercept_ratio = 0.4  # Closer to DL = more aggressive

    intercept_point = threat_pos + dl_direction * (dist_dl_to_target * intercept_ratio)

    # Don't go past the LOS (on pass plays) or too far downfield (run plays)
    if not world.is_run_play:
        # Pass pro: stay behind LOS
        clamped_y = min(intercept_point.y, world.los_y - 1.0)
        intercept_point = Vec2(intercept_point.x, clamped_y)
    else:
        # Run blocking: can push past LOS
        clamped_y = min(intercept_point.y, world.los_y + 3.0)
        intercept_point = Vec2(intercept_point.x, clamped_y)

    return intercept_point


def _find_threat_in_zone(world: WorldState) -> Optional[PlayerView]:
    """Find the DL threat in our zone that's heading toward our protect target.

    Unlike _find_rusher which just finds closest DL, this identifies
    DL that are actively threatening our protection responsibility.
    """
    my_pos = world.me.pos
    my_position = world.me.position
    protect_pos = _get_protect_target(world)

    # Define our zone of responsibility
    zone_ranges = {
        Position.LT: (-6.0, -3.0),
        Position.LG: (-3.0, -0.75),
        Position.C: (-1.5, 1.5),
        Position.RG: (0.75, 3.0),
        Position.RT: (3.0, 6.0),
    }

    zone_min, zone_max = zone_ranges.get(my_position, (-2, 2))

    # Find DL in our zone that's heading toward protect target
    best_threat = None
    best_threat_score = float('inf')

    for opp in world.opponents:
        if opp.position not in (Position.DE, Position.DT, Position.NT):
            continue

        # Skip DL in pursuit mode
        if _is_dl_in_pursuit(opp, world):
            continue

        # Is this DL in or threatening our zone?
        in_zone = zone_min - 1.5 <= opp.pos.x <= zone_max + 1.5

        if not in_zone:
            continue

        # Calculate threat score (lower = more threatening)
        # Based on: distance to protect target, closing speed, angle

        dist_to_target = opp.pos.distance_to(protect_pos)

        # Check if DL is moving toward protect target
        to_target = (protect_pos - opp.pos).normalized()
        closing_speed = opp.velocity.dot(to_target)

        # More threatening if: closer to target, moving toward target
        threat_score = dist_to_target - (closing_speed * 2)

        if threat_score < best_threat_score:
            best_threat_score = threat_score
            best_threat = opp

    return best_threat


def _find_rusher_in_gap(world: WorldState) -> Optional[PlayerView]:
    """Find the defender in OUR gap - don't chase DL outside our zone.

    Each OL is responsible for a gap based on their position.
    We only block DL that are threatening OUR gap, not random DL.
    """
    my_pos = world.me.pos
    my_position = world.me.position

    # Define gap responsibility (x-range we're responsible for)
    # Based on 1.5 yard OL spacing
    gap_ranges = {
        Position.LT: (-4.5, -2.25),  # Outside LT to B gap
        Position.LG: (-2.25, -0.75), # B gap to A gap
        Position.C: (-0.75, 0.75),   # A gap (both sides)
        Position.RG: (0.75, 2.25),   # A gap to B gap
        Position.RT: (2.25, 4.5),    # B gap to outside RT
    }

    gap_min, gap_max = gap_ranges.get(my_position, (-2, 2))

    # Find DL in our gap
    best_target = None
    best_priority = float('inf')

    for opp in world.opponents:
        if opp.position not in (Position.DE, Position.DT, Position.NT):
            continue

        # Skip DL in pursuit mode - don't chase them
        if _is_dl_in_pursuit(opp, world):
            continue

        # Is this DL in our gap?
        if gap_min <= opp.pos.x <= gap_max:
            # Priority: closer to LOS and closer to us
            y_from_los = abs(opp.pos.y - world.los_y)
            x_from_me = abs(opp.pos.x - my_pos.x)
            priority = y_from_los + x_from_me * 0.5

            if priority < best_priority:
                best_priority = priority
                best_target = opp

    return best_target


def _find_rusher(world: WorldState) -> Optional[PlayerView]:
    """Find the defender rushing us - wrapper for backward compatibility."""
    return _find_rusher_in_gap(world)


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
    # Explicit run play from WorldState
    if world.is_run_play:
        return False

    # Check if we got a pass protection assignment
    if "pass" in world.assignment.lower() or "protect" in world.assignment.lower():
        return True

    # Check if we got a run assignment
    if "run:" in world.assignment.lower():
        return False

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
    """Calculate pass set depth based on rusher.

    NFL OL typically set up only 1-2 yards behind LOS. They don't retreat
    all the way back to the QB - they create a pocket by holding their ground.
    """
    base_depth = 1.5  # 1.5 yards behind LOS - realistic pass set

    if rusher:
        # Slightly deeper vs speed rusher (need cushion)
        if hasattr(rusher, 'speed') and rusher.speed > 6.0:
            base_depth = 2.0

    # Tackles can set slightly deeper to protect the edge
    if world.me.position in (Position.LT, Position.RT):
        base_depth += 0.5

    return base_depth


def _get_zone_block_target(world: WorldState) -> Vec2:
    """Get target for zone blocking."""
    my_pos = world.me.pos

    # Zone step playside (simplified: assume right)
    return Vec2(my_pos.x + 1, world.los_y + 2)


def _find_second_level_target(world: WorldState, ball_target: Optional[Vec2] = None) -> Optional[PlayerView]:
    """Find LB to block at second level.

    Prioritizes LBs that are:
    1. Coming downhill (moving toward LOS)
    2. Threatening the ball path
    3. Closest to our position

    Args:
        world: World state
        ball_target: Where the ball is heading (for threat calculation)
    """
    my_pos = world.me.pos

    # Default ball target if not provided
    if ball_target is None:
        playside_dir = 1 if getattr(world, 'run_play_side', 'right') == 'right' else -1
        ball_target = Vec2(playside_dir * 3, world.los_y + 5)

    candidates = []
    for opp in world.opponents:
        if opp.position not in (Position.MLB, Position.ILB, Position.OLB):
            continue

        dist = opp.pos.distance_to(my_pos)
        if dist > 10:  # Too far
            continue

        # LB must be at or past LOS (coming downhill) or close to it
        if opp.pos.y < world.los_y - 2:
            continue

        # Calculate threat score - lower = more threatening
        # LBs moving toward ball path are more threatening
        dist_to_ball = opp.pos.distance_to(ball_target)
        to_ball = (ball_target - opp.pos)
        if to_ball.length() > 0.1:
            to_ball = to_ball.normalized()
            closing_speed = opp.velocity.dot(to_ball)
        else:
            closing_speed = 0

        # LBs coming downhill (negative y velocity = toward LOS) are threats
        downhill_speed = -opp.velocity.y if opp.velocity.y < 0 else 0

        # Score: prioritize close LBs coming downhill toward ball
        threat_score = dist_to_ball - (closing_speed * 2) - (downhill_speed * 3)

        candidates.append((opp, threat_score, dist))

    if not candidates:
        return None

    # Sort by threat score (most threatening first), then by distance
    candidates.sort(key=lambda x: (x[1], x[2]))
    return candidates[0][0]


def _find_any_downhill_threat(world: WorldState) -> Optional[PlayerView]:
    """Find ANY defender coming downhill toward the ballcarrier.

    Used when OL is unengaged and should pick up the most dangerous threat.
    Includes LBs, safeties, and even DBs filling against the run.
    """
    my_pos = world.me.pos
    playside_dir = 1 if getattr(world, 'run_play_side', 'right') == 'right' else -1
    ball_target = Vec2(playside_dir * 3, world.los_y + 5)

    candidates = []
    for opp in world.opponents:
        # Skip DL - they're handled by other logic
        if opp.position in (Position.DE, Position.DT, Position.NT):
            continue

        dist = opp.pos.distance_to(my_pos)
        if dist > 8:  # Too far to pick up
            continue

        # Must be coming downhill (toward backfield)
        if opp.velocity.y > -0.5:  # Not moving downhill
            continue

        # Must be in front of us (between us and ball path)
        if opp.pos.y < my_pos.y - 2:
            continue

        # Calculate threat
        dist_to_ball = opp.pos.distance_to(ball_target)
        downhill_speed = abs(opp.velocity.y)

        # Score by threat level
        threat_score = dist_to_ball - (downhill_speed * 2)

        candidates.append((opp, threat_score, dist))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[1], x[2]))
    return candidates[0][0]


# =============================================================================
# Main Brain Function
# =============================================================================

def ol_brain(world: OLContext) -> BrainDecision:
    """Offensive line brain - for tackles, guards, and centers.

    Features:
    - MIKE identification (Center makes protection call)
    - Combo blocks (two OL work DL, one climbs to LB)
    - Stunt pickup (detect twists, switch assignments)

    Args:
        world: OLContext with blocking assignments

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
    just_made_call = False
    if _should_center_make_call(world) and _protection_call is None:
        _protection_call = _identify_mike(world)
        just_made_call = True

    # Build protection call string to return to orchestrator
    protection_call_str = None
    if just_made_call and _protection_call and _protection_call.slide_direction != "none":
        protection_call_str = f"slide_{_protection_call.slide_direction}"

    # Find our assignment (use protection call if available)
    rusher = _find_rusher(world)
    if rusher:
        state.assigned_defender_id = rusher.id
        state.original_assignment_id = rusher.id

    # =========================================================================
    # Pass Protection - INTERCEPT PATH APPROACH
    # =========================================================================
    # Key insight: Don't chase DL. Position BETWEEN DL and QB.
    # Engagement happens when DL runs into us.
    if _is_pass_play(world):
        protect_pos = _get_protect_target(world)
        threat = _find_threat_in_zone(world)

        # Pass set phase (first 0.5s) - establish position
        if world.time_since_snap < 0.5:
            state.phase = OLPhase.PASS_SET

            # Calculate set depth
            set_depth = _get_kick_slide_depth(world, threat)
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
                protection_call=protection_call_str,
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

                # Find the new threat and intercept their path
                for opp in world.opponents:
                    if opp.id == new_assignment:
                        intercept_pos = _calculate_intercept_position(
                            world.me.pos, opp.pos, opp.velocity, protect_pos, world
                        )
                        return BrainDecision(
                            move_target=intercept_pos,
                            move_type="run",
                            action="pickup",
                            target_id=new_assignment,
                            intent="stunt_pickup",
                            reasoning=f"Stunt pickup! Intercepting crasher ({stunt})",
                        )

        # =====================================================================
        # Main Pass Protection Logic - Intercept DL path to QB
        # =====================================================================
        if threat:
            state.phase = OLPhase.ENGAGED
            state.assigned_defender_id = threat.id

            dist_to_threat = world.me.pos.distance_to(threat.pos)

            # Calculate intercept position - where we need to be to block DL's path
            intercept_pos = _calculate_intercept_position(
                world.me.pos, threat.pos, threat.velocity, protect_pos, world
            )

            # If we're close to threat, we're engaged
            if dist_to_threat < 1.5:
                state.is_engaged = True

                # Engaged - maintain position between threat and QB
                # Don't chase threat - stay in their path
                rush_move = _detect_rush_move(threat)
                counter = _get_counter_for_move(rush_move)

                # Calculate position to maintain - between threat and QB
                to_qb = (protect_pos - threat.pos).normalized()
                maintain_pos = threat.pos + to_qb * 1.2  # Stay 1.2yd in front of DL

                return BrainDecision(
                    move_target=maintain_pos,
                    move_type="run",
                    action=counter.value,
                    target_id=threat.id,
                    intent="block",
                    reasoning=f"Engaged - {counter.value}, maintaining position",
                )

            # Not engaged yet - move to intercept position
            # Don't run TO the DL, run to WHERE we need to be
            return BrainDecision(
                move_target=intercept_pos,
                move_type="run",
                action="kick_slide",
                target_id=threat.id,
                intent="intercept",
                reasoning=f"Intercepting DL path ({dist_to_threat:.1f}yd away)",
            )

        # No direct threat - look for blitzing LB (use MIKE call)
        if _protection_call and _protection_call.mike_id:
            mike = None
            for opp in world.opponents:
                if opp.id == _protection_call.mike_id:
                    mike = opp
                    break

            if mike and mike.pos.y < world.los_y + 2:
                # MIKE is blitzing - intercept their path
                intercept_pos = _calculate_intercept_position(
                    world.me.pos, mike.pos, mike.velocity, protect_pos, world
                )
                return BrainDecision(
                    move_target=intercept_pos,
                    move_type="run",
                    action="pickup",
                    target_id=mike.id,
                    intent="blitz_pickup",
                    reasoning="MIKE blitzing - intercepting path",
                )

        # No threats - hold position in our zone (don't retreat too far)
        set_depth = _get_kick_slide_depth(world, None)
        hold_pos = Vec2(world.me.pos.x, world.los_y - set_depth)
        return BrainDecision(
            move_target=hold_pos,
            intent="hold",
            reasoning="No threat - holding zone",
        )

    # =========================================================================
    # Run Blocking - Use assignments from run concept
    # =========================================================================
    state.phase = OLPhase.RUN_BLOCK

    # Get assignment from WorldState
    assignment = world.run_blocking_assignment
    play_side = world.run_play_side

    # Determine playside direction
    playside_dir = 1 if play_side == "right" else -1

    # Get our gap responsibility
    gap_ranges = {
        Position.LT: (-4.5, -2.25),
        Position.LG: (-2.25, -0.75),
        Position.C: (-0.75, 0.75),
        Position.RG: (0.75, 2.25),
        Position.RT: (2.25, 4.5),
    }
    my_gap_min, my_gap_max = gap_ranges.get(world.me.position, (-2, 2))
    my_gap_center = (my_gap_min + my_gap_max) / 2

    # =========================================================================
    # First: Fire off the ball to LOS (first 0.2s)
    # All OL should step forward at snap, not chase DL
    # =========================================================================
    if world.time_since_snap < 0.2:
        # Fire forward to our gap at LOS
        fire_target = Vec2(my_gap_center, world.los_y)
        return BrainDecision(
            move_target=fire_target,
            move_type="run",
            action="fire_out",
            intent="run_block",
            reasoning="Firing off the ball",
        )

    # =========================================================================
    # Pull assignments (PULL_LEAD, PULL_WRAP)
    # =========================================================================
    if assignment in ("pull_lead", "pull_wrap"):
        state.phase = OLPhase.PULLING
        state.is_pulling = True

        # Pull to playside - aim for hole area
        pull_x = playside_dir * 4  # 4 yards playside
        pull_y = world.los_y + 3   # 3 yards past LOS
        pull_target = Vec2(pull_x, pull_y)

        # Find a defender to kick out or lead on
        kick_target = None
        for opp in world.opponents:
            if opp.position in (Position.DE, Position.OLB):
                if abs(opp.pos.x - pull_x) < 3:
                    kick_target = opp
                    break

        if kick_target and world.me.pos.distance_to(kick_target.pos) < 3:
            return BrainDecision(
                move_target=kick_target.pos,
                move_type="sprint",
                action="kick_out" if assignment == "pull_lead" else "wrap",
                target_id=kick_target.id,
                intent="pull_block",
                reasoning=f"Pulling to kick out {kick_target.position.value}",
            )

        return BrainDecision(
            move_target=pull_target,
            move_type="sprint",
            action="pull",
            intent="pulling",
            reasoning=f"Pulling {play_side} to hole",
        )

    # =========================================================================
    # Combo block assignment - INTERCEPT PATH APPROACH
    # =========================================================================
    # Combo: Two OL work together to seal DL from ball path, then one climbs
    if assignment == "combo":
        # Ball path target for run plays
        ball_target = Vec2(playside_dir * 3, world.los_y + 5)
        if hasattr(world, 'run_aiming_point') and world.run_aiming_point:
            ball_target = world.run_aiming_point

        # Find combo partner
        partner_pos = world.combo_partner_position
        partner = None
        if partner_pos:
            for tm in world.teammates:
                if tm.position and tm.position.value.upper() == partner_pos:
                    partner = tm
                    break

        # Find DL in our combined zone that could get to ball
        dl_target = None
        if partner:
            my_gap_min_x = my_gap_min
            my_gap_max_x = my_gap_max
            partner_position = partner.position

            partner_gap_ranges = {
                Position.LT: (-4.5, -2.25),
                Position.LG: (-2.25, -0.75),
                Position.C: (-0.75, 0.75),
                Position.RG: (0.75, 2.25),
                Position.RT: (2.25, 4.5),
            }
            partner_gap = partner_gap_ranges.get(partner_position, (-2, 2))

            combined_min = min(my_gap_min_x, partner_gap[0]) - 0.5
            combined_max = max(my_gap_max_x, partner_gap[1]) + 0.5

            midpoint = (world.me.pos + partner.pos) * 0.5
            candidates = []
            for opp in world.opponents:
                if opp.position in (Position.DE, Position.DT, Position.NT):
                    if _is_dl_in_pursuit(opp, world):
                        continue
                    if not (combined_min <= opp.pos.x <= combined_max):
                        continue
                    if abs(opp.pos.y - world.los_y) > 3.0:
                        continue

                    # Score by threat to ball path
                    dist_to_ball = opp.pos.distance_to(ball_target)
                    to_ball = (ball_target - opp.pos).normalized()
                    closing = opp.velocity.dot(to_ball)
                    threat_score = dist_to_ball - (closing * 2)

                    candidates.append((opp, threat_score))

            if candidates:
                # Most threatening to ball path first
                candidates.sort(key=lambda x: x[1])
                dl_target = candidates[0][0]
                state.combo_target_id = dl_target.id

        if dl_target:
            # Check if we should climb to second level
            if _should_climb_from_combo(world, state):
                lb = _find_second_level_target(world)
                if lb:
                    state.phase = OLPhase.SECOND_LEVEL
                    # Intercept LB's path to ball
                    intercept_pos = _calculate_intercept_position(
                        world.me.pos, lb.pos, lb.velocity, ball_target, world
                    )
                    return BrainDecision(
                        move_target=intercept_pos,
                        move_type="sprint",
                        action="climb",
                        target_id=lb.id,
                        intent="combo_climb",
                        reasoning="Climbing - intercepting LB path to ball!",
                    )

            # Combo: Position to seal DL from ball path
            # Don't just drive them - position between them and ball
            dist_to_dl = world.me.pos.distance_to(dl_target.pos)

            if dist_to_dl < 1.5:
                # Engaged - seal playside shoulder
                seal_pos = Vec2(
                    dl_target.pos.x + playside_dir * 0.5,
                    dl_target.pos.y + 0.3
                )
                return BrainDecision(
                    move_target=seal_pos,
                    move_type="run",
                    action="double",
                    target_id=dl_target.id,
                    intent="combo_block",
                    reasoning=f"Combo: sealing DL from ball path with {partner_pos or 'partner'}",
                )
            else:
                # Move to intercept DL's path to ball
                intercept_pos = _calculate_intercept_position(
                    world.me.pos, dl_target.pos, dl_target.velocity, ball_target, world
                )
                return BrainDecision(
                    move_target=intercept_pos,
                    move_type="run",
                    action="double",
                    target_id=dl_target.id,
                    intent="combo_block",
                    reasoning=f"Combo: intercepting DL path with {partner_pos or 'partner'}",
                )

        # No valid combo target - hold gap
        hold_pos = Vec2(my_gap_center, world.los_y + 0.5)
        return BrainDecision(
            move_target=hold_pos,
            move_type="run",
            action="hold",
            intent="combo_block",
            reasoning="No combo target - holding gap",
        )

    # =========================================================================
    # Zone step assignments (ZONE_STEP, REACH) - INTERCEPT PATH APPROACH
    # =========================================================================
    # Zone blocking: Position to seal DL from getting to the ball.
    # Don't chase DL - position between them and the ball path.
    if assignment in ("zone_step", "reach"):
        my_pos = world.me.pos

        # The "protect target" for run plays is the RB/ball path
        ball_target = Vec2(playside_dir * 3, world.los_y + 5)  # Hole area
        if hasattr(world, 'run_aiming_point') and world.run_aiming_point:
            ball_target = world.run_aiming_point

        # Find defender in OUR gap that could get to the ball
        zone_target_opp = None
        for opp in world.opponents:
            if opp.position in (Position.DE, Position.DT, Position.NT):
                # Skip DL in pursuit mode - don't chase them
                if _is_dl_in_pursuit(opp, world):
                    continue
                # Only engage DL in our gap responsibility
                if my_gap_min <= opp.pos.x <= my_gap_max:
                    zone_target_opp = opp
                    break

        if zone_target_opp:
            dist_to_dl = my_pos.distance_to(zone_target_opp.pos)

            if dist_to_dl < 1.5:
                # Engaged - seal DL from ball path
                # Position on playside shoulder to seal
                seal_pos = Vec2(
                    zone_target_opp.pos.x + playside_dir * 0.5,  # Get playside shoulder
                    zone_target_opp.pos.y + 0.3
                )
                return BrainDecision(
                    move_target=seal_pos,
                    move_type="run",
                    action="sustain",
                    target_id=zone_target_opp.id,
                    intent="zone_block",
                    reasoning=f"Sealing {zone_target_opp.position.value} from ball path",
                )
            else:
                # Not engaged - move to intercept position between DL and ball path
                intercept_pos = _calculate_intercept_position(
                    my_pos, zone_target_opp.pos, zone_target_opp.velocity,
                    ball_target, world
                )
                return BrainDecision(
                    move_target=intercept_pos,
                    move_type="run",
                    action=assignment,
                    target_id=zone_target_opp.id,
                    intent="zone_block",
                    reasoning=f"Intercepting {zone_target_opp.position.value}'s path to ball",
                )

        # No DL in our gap - check for LB to pick up
        lb = _find_second_level_target(world)
        if lb and my_gap_min - 1 <= lb.pos.x <= my_gap_max + 2:
            # LB threatening our area - intercept their path
            intercept_pos = _calculate_intercept_position(
                my_pos, lb.pos, lb.velocity, ball_target, world
            )
            return BrainDecision(
                move_target=intercept_pos,
                move_type="run",
                action="climb",
                target_id=lb.id,
                intent="second_level",
                reasoning="Intercepting LB path to ball",
            )

        # No threats - hold position at LOS in our gap
        hold_pos = Vec2(my_gap_center, world.los_y + 0.5)
        return BrainDecision(
            move_target=hold_pos,
            move_type="run",
            action="zone_step",
            intent="zone_block",
            reasoning="Holding gap - no threat to ball path",
        )

    # =========================================================================
    # Down block assignment
    # =========================================================================
    if assignment == "down":
        my_pos = world.me.pos

        # Block down - inside shoulder of defender
        down_dir = -playside_dir  # Opposite of play direction
        target_x = my_pos.x + down_dir * 1

        # Find defender to down block
        down_target = None
        for opp in world.opponents:
            if opp.position in (Position.DE, Position.DT, Position.NT):
                if abs(opp.pos.x - target_x) < 2:
                    down_target = opp
                    break

        if down_target:
            return BrainDecision(
                move_target=down_target.pos,
                move_type="run",
                action="down_block",
                target_id=down_target.id,
                intent="gap_block",
                reasoning=f"Down block on {down_target.position.value}",
            )

    # =========================================================================
    # Cutoff assignment (backside)
    # =========================================================================
    if assignment == "cutoff":
        my_pos = world.me.pos

        # Find DL in or near our gap to cutoff
        # Cutoff blocks the backside - seal DL from pursuing
        cutoff_target = None
        for opp in world.opponents:
            if opp.position in (Position.DE, Position.DT, Position.NT):
                # Skip DL in pursuit mode - don't chase them
                if _is_dl_in_pursuit(opp, world):
                    continue
                # Only block DL in or adjacent to our gap
                expanded_min = my_gap_min - 1.0  # Slightly expand for backside
                expanded_max = my_gap_max + 1.0
                if expanded_min <= opp.pos.x <= expanded_max:
                    cutoff_target = opp
                    break

        if cutoff_target:
            dist_to_dl = my_pos.distance_to(cutoff_target.pos)

            if dist_to_dl < 1.5:
                # Engaged - sustain and seal
                seal_pos = Vec2(
                    cutoff_target.pos.x + playside_dir * 0.5,  # Get to playside shoulder
                    cutoff_target.pos.y
                )
                return BrainDecision(
                    move_target=seal_pos,
                    move_type="run",
                    action="cutoff",
                    target_id=cutoff_target.id,
                    intent="cutoff_block",
                    reasoning=f"Sealing {cutoff_target.position.value}",
                )
            else:
                # Move to engage
                return BrainDecision(
                    move_target=cutoff_target.pos,
                    move_type="run",
                    action="cutoff",
                    target_id=cutoff_target.id,
                    intent="cutoff_block",
                    reasoning=f"Cutoff on {cutoff_target.position.value}",
                )

        # No DL to cutoff - hold position at LOS in our gap
        hold_pos = Vec2(my_gap_center, world.los_y + 0.5)
        return BrainDecision(
            move_target=hold_pos,
            move_type="run",
            action="cutoff",
            intent="cutoff_block",
            reasoning="Holding backside gap",
        )

    # =========================================================================
    # Pass set assignment (for draw plays - fake pass protection)
    # =========================================================================
    if assignment == "pass_set":
        # Show pass protection initially, then transition to run block
        if world.time_since_snap < 0.8:
            # Pass set phase - drop back like pass pro
            set_depth = 2.5
            set_pos = Vec2(world.me.pos.x, world.los_y - set_depth)

            return BrainDecision(
                move_target=set_pos,
                move_type="backpedal",
                intent="pass_set",
                reasoning="Draw - showing pass set",
            )
        else:
            # Transition to run block - find nearest DL
            if rusher:
                return BrainDecision(
                    move_target=rusher.pos,
                    move_type="run",
                    action="drive",
                    target_id=rusher.id,
                    intent="drive_block",
                    reasoning="Draw - transitioning to run block",
                )

    # =========================================================================
    # Base block assignment (man-on-man)
    # =========================================================================
    if assignment == "base":
        my_pos = world.me.pos

        # Find DL in our gap
        base_target = None
        for opp in world.opponents:
            if opp.position in (Position.DE, Position.DT, Position.NT):
                # Skip DL in pursuit mode - don't chase them
                if _is_dl_in_pursuit(opp, world):
                    continue
                if my_gap_min <= opp.pos.x <= my_gap_max:
                    base_target = opp
                    break

        if base_target:
            dist_to_dl = my_pos.distance_to(base_target.pos)
            if dist_to_dl < 1.5:
                # Engaged - sustain
                return BrainDecision(
                    move_target=Vec2(base_target.pos.x, base_target.pos.y + 0.2),
                    move_type="run",
                    action="sustain",
                    target_id=base_target.id,
                    intent="base_block",
                    reasoning=f"Sustaining on {base_target.position.value}",
                )
            else:
                return BrainDecision(
                    move_target=base_target.pos,
                    move_type="run",
                    action="drive",
                    target_id=base_target.id,
                    intent="base_block",
                    reasoning=f"Base block on {base_target.position.value}",
                )

        # No DL in our gap - hold position
        hold_pos = Vec2(my_gap_center, world.los_y + 0.5)
        return BrainDecision(
            move_target=hold_pos,
            move_type="run",
            action="hold",
            intent="base_block",
            reasoning="Holding gap, no DL",
        )

    # =========================================================================
    # Default / Fallback - Find someone to block
    # =========================================================================
    # Ball path target
    ball_target = Vec2(playside_dir * 3, world.los_y + 5)
    if hasattr(world, 'run_aiming_point') and world.run_aiming_point:
        ball_target = world.run_aiming_point

    # 1. First look for DL in our gap
    gap_dl = _find_rusher_in_gap(world)
    if gap_dl:
        dist_to_dl = world.me.pos.distance_to(gap_dl.pos)
        if dist_to_dl < 1.5:
            # Engaged - sustain
            return BrainDecision(
                move_target=Vec2(gap_dl.pos.x, gap_dl.pos.y + 0.2),
                move_type="run",
                action="sustain",
                target_id=gap_dl.id,
                intent="block",
                reasoning=f"Blocking {gap_dl.position.value}",
            )
        else:
            return BrainDecision(
                move_target=gap_dl.pos,
                move_type="run",
                action="engage",
                target_id=gap_dl.id,
                intent="block",
                reasoning=f"Engaging {gap_dl.position.value}",
            )

    # 2. No DL in gap - look for LB coming downhill
    lb_target = _find_second_level_target(world, ball_target)
    if lb_target:
        dist_to_lb = world.me.pos.distance_to(lb_target.pos)
        # Intercept LB's path to the ball
        intercept_pos = _calculate_intercept_position(
            world.me.pos, lb_target.pos, lb_target.velocity, ball_target, world
        )
        if dist_to_lb < 2.0:
            return BrainDecision(
                move_target=lb_target.pos,
                move_type="run",
                action="climb",
                target_id=lb_target.id,
                intent="second_level",
                reasoning=f"Picking up {lb_target.position.value} at second level",
            )
        else:
            return BrainDecision(
                move_target=intercept_pos,
                move_type="sprint",
                action="climb",
                target_id=lb_target.id,
                intent="second_level",
                reasoning=f"Climbing to intercept {lb_target.position.value}",
            )

    # 3. No LB - look for ANY downhill threat (safety, DB filling)
    downhill_threat = _find_any_downhill_threat(world)
    if downhill_threat:
        intercept_pos = _calculate_intercept_position(
            world.me.pos, downhill_threat.pos, downhill_threat.velocity, ball_target, world
        )
        return BrainDecision(
            move_target=intercept_pos,
            move_type="sprint",
            action="lead",
            target_id=downhill_threat.id,
            intent="lead_block",
            reasoning=f"Lead blocking on {downhill_threat.position.value} coming downhill",
        )

    # 4. Nobody to block - get to the second level and look for work
    # Move toward the hole area in case a defender shows up
    climb_target = Vec2(my_gap_center + playside_dir * 1.5, world.los_y + 3)
    return BrainDecision(
        move_target=climb_target,
        move_type="run",
        action="climb",
        intent="second_level",
        reasoning="Climbing to second level - looking for work",
    )
