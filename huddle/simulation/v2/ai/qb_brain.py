"""QB Brain - Decision-making for quarterbacks.

The QB brain manages:
- Pre-snap reads (coverage shell, blitz detection)
- Hot route calls and protection adjustments
- Dropback execution
- Read progression through receivers
- Pressure response (pocket movement, scramble)
- Throw/scramble decision

Lifecycle: PRE_SNAP → SNAP → DROPBACK → POCKET → THROW/SCRAMBLE/SACK

Pre-snap intelligence:
- _identify_coverage_shell(): Identifies Cover 0/1/2/3/4 based on safety alignment
- _detect_blitz_look(): Detects walked-up LBs, safety creep
- _get_hot_route_for_blitz(): Converts routes to beat blitz
- _get_protection_call(): Slide protection toward blitz side
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from .shared.perception import calculate_effective_vision, angle_between, VisionParams


# =============================================================================
# QB State Enums
# =============================================================================

class PressureLevel(str, Enum):
    """How much pressure the QB is under."""
    CLEAN = "clean"       # No pressure, all the time
    LIGHT = "light"       # Minor presence, manageable
    MODERATE = "moderate" # Need to think about moving
    HEAVY = "heavy"       # Must make decision soon
    CRITICAL = "critical" # Immediate action required


class QBPhase(str, Enum):
    """Current phase of QB actions."""
    PRE_SNAP = "pre_snap"
    DROPBACK = "dropback"
    POCKET = "pocket"
    SCRAMBLE = "scramble"
    THROWING = "throwing"


class ReceiverStatus(str, Enum):
    """How open a receiver is."""
    OPEN = "open"           # > 2.5 yards separation
    WINDOW = "window"       # 1.5 - 2.5 yards
    CONTESTED = "contested" # 0.5 - 1.5 yards
    COVERED = "covered"     # < 0.5 yards


class CoverageShell(str, Enum):
    """Pre-snap coverage shell identification."""
    COVER_0 = "cover_0"     # No deep safety, man-free
    COVER_1 = "cover_1"     # Single high safety
    COVER_2 = "cover_2"     # Two high safeties
    COVER_3 = "cover_3"     # Single high, corners deep
    COVER_4 = "cover_4"     # Quarters, two high
    COVER_6 = "cover_6"     # Quarter-quarter-half
    UNKNOWN = "unknown"     # Can't identify


class BlitzLook(str, Enum):
    """Pre-snap blitz indicators."""
    NONE = "none"
    LIGHT = "light"         # 5-man rush likely
    HEAVY = "heavy"         # 6+ man rush likely
    ZERO = "zero"           # Cover 0 blitz (all-out)


# =============================================================================
# Internal State Tracking
# =============================================================================

@dataclass
class ReceiverEval:
    """Evaluation of a receiver's openness."""
    player_id: str
    position: Vec2
    separation: float
    status: ReceiverStatus
    nearest_defender_id: str
    defender_closing_speed: float
    route_phase: str
    is_hot: bool
    read_order: int
    # Anticipation throw fields
    defender_trailing: bool = False  # Is defender behind receiver?
    pre_break: bool = False  # Is receiver pre-break?
    anticipation_viable: bool = False  # Can throw anticipation?
    # Vision-based detection quality (1.0 = central, lower = peripheral)
    detection_quality: float = 1.0


@dataclass
class QBState:
    """Tracked state for QB decision-making."""
    dropback_complete: bool = False
    current_read: int = 1
    read_start_time: float = 0.0
    pressure_level: PressureLevel = PressureLevel.CLEAN
    time_in_pocket: float = 0.0
    scramble_committed: bool = False
    last_pump_fake_time: float = -5.0
    hot_route_triggered: bool = False
    escape_direction: Optional[Vec2] = None
    set_time: float = 0.0  # When dropback completed


# Module-level state tracking (per player)
_qb_states: dict[str, QBState] = {}


def _get_state(player_id: str) -> QBState:
    """Get or create state for a QB."""
    if player_id not in _qb_states:
        _qb_states[player_id] = QBState()
    return _qb_states[player_id]


def _reset_state(player_id: str) -> None:
    """Reset state for a new play."""
    _qb_states[player_id] = QBState()


# =============================================================================
# Helper Functions
# =============================================================================

def _pressure_to_float(pressure: PressureLevel) -> float:
    """Convert PressureLevel enum to float for vision calculations.

    Returns:
        Float from 0.0 (clean) to 1.0 (critical)
    """
    pressure_map = {
        PressureLevel.CLEAN: 0.0,
        PressureLevel.LIGHT: 0.25,
        PressureLevel.MODERATE: 0.5,
        PressureLevel.HEAVY: 0.75,
        PressureLevel.CRITICAL: 1.0,
    }
    return pressure_map.get(pressure, 0.0)


def _get_qb_facing(world: WorldState) -> Vec2:
    """Get the direction the QB is facing.

    QB in pocket should face downfield to read receivers, regardless of
    any residual backward velocity from dropback.
    """
    vel = world.me.velocity
    if vel and vel.length() > 0.5:
        # If moving forward or laterally, use velocity
        # If moving backward (dropback), face downfield instead
        if vel.y >= 0:  # Forward or lateral movement
            return vel.normalized()
    # In pocket or dropback - face downfield to read receivers
    return Vec2(0, 1)


def _calculate_pressure(world: WorldState) -> Tuple[PressureLevel, List[PlayerView]]:
    """Calculate pressure level from defender positions.

    Returns:
        (pressure_level, list of threatening defenders)
    """
    qb_pos = world.me.pos
    threats = []
    total_threat_score = 0.0

    for opp in world.opponents:
        distance = opp.pos.distance_to(qb_pos)

        # Only consider players within threat range
        if distance > 15.0:
            continue

        # Calculate time to arrival (ETA)
        closing_speed = opp.speed if opp.speed > 0 else 5.0
        eta = distance / closing_speed if closing_speed > 0 else 10.0

        # Threat score inversely proportional to ETA
        threat_score = 1.0 / (eta + 0.1)

        # Blind side bonus (left side for right-handed QB)
        if opp.pos.x < qb_pos.x:  # Coming from left
            threat_score *= 1.5

        # Clear lane bonus
        # TODO: Check if blocker is between threat and QB

        total_threat_score += threat_score

        if eta < 2.0:  # Imminent threat
            threats.append(opp)

    # Map total threat to pressure level
    if total_threat_score < 0.5:
        level = PressureLevel.CLEAN
    elif total_threat_score < 1.0:
        level = PressureLevel.LIGHT
    elif total_threat_score < 2.0:
        level = PressureLevel.MODERATE
    elif total_threat_score < 3.5:
        level = PressureLevel.HEAVY
    else:
        level = PressureLevel.CRITICAL

    # Awareness modifier for detection
    awareness = world.me.attributes.awareness
    if awareness >= 90:
        # Elite awareness - detect pressure early (already calculated)
        pass
    elif awareness < 70:
        # Low awareness - might miss pressure
        if level == PressureLevel.HEAVY:
            level = PressureLevel.MODERATE
        elif level == PressureLevel.MODERATE:
            level = PressureLevel.LIGHT

    return level, threats


def _evaluate_receivers(world: WorldState, pressure: PressureLevel = None) -> List[ReceiverEval]:
    """Evaluate all receivers and their openness.

    Implements Easterbrook Hypothesis: under pressure, QB sees less of the field.
    Peripheral receivers may be missed entirely or evaluated with lower accuracy.

    Args:
        world: Current world state
        pressure: Current pressure level (if None, will be calculated)
    """
    evaluations = []

    # Calculate effective vision under current pressure
    if pressure is None:
        pressure, _ = _calculate_pressure(world)

    pressure_float = _pressure_to_float(pressure)
    awareness = getattr(world.me.attributes, 'awareness', 80)
    vision_params = calculate_effective_vision(awareness, pressure_float)

    # Get QB facing direction for vision cone
    qb_facing = _get_qb_facing(world)
    qb_pos = world.me.pos

    for teammate in world.teammates:
        # Only evaluate receivers
        if teammate.position not in (Position.WR, Position.TE, Position.RB):
            continue

        # Check if receiver is within QB's effective vision
        to_receiver = teammate.pos - qb_pos
        distance = to_receiver.length()

        # Outside vision radius - QB can't see them under pressure
        if distance > vision_params.radius:
            continue

        # Calculate angle to receiver
        if distance > 0.1:
            angle = angle_between(qb_facing, to_receiver.normalized())
            # Outside vision angle - QB can't see them (tunnel vision)
            if angle > vision_params.angle / 2:
                continue

            # Determine if receiver is in peripheral vision (outside 45 degree central cone)
            is_peripheral = angle > 45.0
            detection_quality = vision_params.peripheral_quality if is_peripheral else 1.0
        else:
            detection_quality = 1.0

        # Find nearest defender
        nearest_def = None
        nearest_dist = float('inf')
        closing_speed = 0.0

        for opp in world.opponents:
            dist = teammate.pos.distance_to(opp.pos)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_def = opp

                # Calculate closing speed
                if opp.velocity.length() > 0:
                    to_receiver = (teammate.pos - opp.pos).normalized()
                    closing_speed = opp.velocity.dot(to_receiver)

        # Adjust separation based on defender position
        effective_sep = nearest_dist
        defender_trailing = False
        if nearest_def:
            # Defender behind receiver = bonus separation
            receiver_to_qb = (world.me.pos - teammate.pos).normalized()
            def_to_receiver = (teammate.pos - nearest_def.pos).normalized()
            if receiver_to_qb.dot(def_to_receiver) > 0.5:  # Defender trailing
                effective_sep += 1.0
                defender_trailing = True
            # Defender in front (undercutting) = penalty
            elif receiver_to_qb.dot(def_to_receiver) < -0.3:
                effective_sep -= 0.5

        # Closing speed penalty
        if closing_speed > 0:
            effective_sep -= closing_speed * 0.3

        # Determine status
        if effective_sep > 2.5:
            status = ReceiverStatus.OPEN
        elif effective_sep > 1.5:
            status = ReceiverStatus.WINDOW
        elif effective_sep > 0.5:
            status = ReceiverStatus.CONTESTED
        else:
            status = ReceiverStatus.COVERED

        # Determine route phase based on time since snap
        # Typical timing: release 0-0.5s, stem 0.5-1.2s, break 1.2-1.5s, post-break 1.5s+
        time = world.time_since_snap
        if time < 0.5:
            route_phase = "release"
            pre_break = True
        elif time < 1.2:
            route_phase = "stem"
            pre_break = True
        elif time < 1.5:
            route_phase = "break"
            pre_break = True
        else:
            route_phase = "post_break"
            pre_break = False

        evaluations.append(ReceiverEval(
            player_id=teammate.id,
            position=teammate.pos,
            separation=effective_sep,
            status=status,
            nearest_defender_id=nearest_def.id if nearest_def else "",
            defender_closing_speed=closing_speed,
            route_phase=route_phase,
            is_hot=False,  # TODO: Track hot routes
            read_order=getattr(teammate, 'read_order', 0) or 99,  # 0 means unassigned → low priority
            defender_trailing=defender_trailing,
            pre_break=pre_break,
            detection_quality=detection_quality,  # Lower for peripheral receivers
        ))

    # Sort by read order
    evaluations.sort(key=lambda e: e.read_order)
    return evaluations


def _can_throw_anticipation(
    accuracy: int,
    receiver: ReceiverEval,
    pressure: PressureLevel,
) -> Tuple[bool, str]:
    """Check if QB can throw anticipation pass.

    From design doc:
        90+ accuracy: Can throw 0.3s before break
        80-89 accuracy: Can throw 0.15s before break
        70-79 accuracy: Must wait for break
        <70 accuracy: Must wait until receiver is open

    Requirements for anticipation:
        1. Receiver is pre-break
        2. QB accuracy allows anticipation
        3. Defender is trailing (not undercutting)
        4. Clean pocket (not heavy/critical pressure)

    Returns:
        (can_anticipate, reasoning)
    """
    # Can only anticipate to pre-break receivers
    if not receiver.pre_break:
        return False, "receiver past break point"

    # Pressure check - no anticipation under heavy pressure
    if pressure in (PressureLevel.HEAVY, PressureLevel.CRITICAL):
        return False, "too much pressure for anticipation"

    # Defender must be trailing
    if not receiver.defender_trailing:
        return False, "defender not trailing"

    # Accuracy thresholds
    if accuracy >= 90:
        return True, f"elite accuracy ({accuracy}), 0.3s anticipation window"
    elif accuracy >= 80:
        # Can anticipate only late stem / during break
        if receiver.route_phase == "break" or (receiver.route_phase == "stem" and receiver.separation > 1.0):
            return True, f"good accuracy ({accuracy}), 0.15s anticipation window"
        return False, "accuracy allows limited anticipation, too early"
    else:
        return False, f"accuracy ({accuracy}) requires receiver to be open"


def _find_best_receiver(
    evaluations: List[ReceiverEval],
    current_read: int,
    pressure: PressureLevel,
    accuracy: int = 75,
) -> Tuple[Optional[ReceiverEval], bool, str]:
    """Find the best receiver to throw to.

    Args:
        evaluations: List of receiver evaluations
        current_read: Current read in progression
        pressure: Current pressure level
        accuracy: QB throw accuracy attribute

    Returns:
        (best_receiver, is_anticipation, reasoning)
    """
    if not evaluations:
        return None, False, "no receivers"

    # Under critical pressure, find anyone remotely open
    if pressure == PressureLevel.CRITICAL:
        for eval in evaluations:
            if eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
                return eval, False, "critical pressure quick throw"
        # Even contested is better than sack
        for eval in evaluations:
            if eval.status == ReceiverStatus.CONTESTED:
                return eval, False, "critical pressure forced throw"
        return None, False, "no target under pressure"

    # Normal progression - check current read first
    current_eval = None
    for eval in evaluations:
        if eval.read_order == current_read:
            current_eval = eval
            break

    if current_eval:
        # Check if currently open
        if current_eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            return current_eval, False, f"read {current_read} open"

        # Check for anticipation throw
        can_anticipate, anticipate_reason = _can_throw_anticipation(
            accuracy, current_eval, pressure
        )
        if can_anticipate:
            return current_eval, True, f"anticipation: {anticipate_reason}"

    # If current read is covered, check if anyone else is clearly open
    for eval in evaluations:
        if eval.status == ReceiverStatus.OPEN:
            return eval, False, "found open receiver off-script"

    # Check all receivers for anticipation opportunity
    for eval in evaluations:
        can_anticipate, anticipate_reason = _can_throw_anticipation(
            accuracy, eval, pressure
        )
        if can_anticipate and eval.separation > 1.0:
            return eval, True, f"anticipation: {anticipate_reason}"

    return None, False, "no open receivers"


def _find_escape_lane(world: WorldState) -> Optional[Vec2]:
    """Find an escape lane from pressure."""
    qb_pos = world.me.pos

    # Check both sides
    escape_options = [
        Vec2(qb_pos.x + 5, qb_pos.y - 2),  # Right
        Vec2(qb_pos.x - 5, qb_pos.y - 2),  # Left
        Vec2(qb_pos.x, qb_pos.y + 3),      # Step up
    ]

    best_option = None
    best_clearance = 0.0

    for escape_pos in escape_options:
        # Find nearest defender to this escape position
        min_dist = float('inf')
        for opp in world.opponents:
            dist = opp.pos.distance_to(escape_pos)
            if dist < min_dist:
                min_dist = dist

        if min_dist > best_clearance:
            best_clearance = min_dist
            best_option = escape_pos

    return best_option if best_clearance > 3.0 else None


def _get_dropback_target(world: WorldState) -> Vec2:
    """Get the target position for dropback."""
    # Standard 5-step drop is about 7 yards behind snap
    # Use LOS as reference, not current position (avoid infinite retreat)
    return Vec2(world.me.pos.x, world.los_y - 7)


def _should_throw_away(world: WorldState) -> bool:
    """Check if QB should throw the ball away."""
    # Must be outside tackle box (> 3 yards from center)
    if abs(world.me.pos.x) < 3:
        return False
    return True


def _get_throw_away_target(world: WorldState) -> Vec2:
    """Get a safe target for throwing the ball away."""
    # Throw toward sideline, past LOS
    side = 1 if world.me.pos.x > 0 else -1
    return Vec2(side * 25, world.los_y + 5)


# =============================================================================
# Pre-Snap Analysis
# =============================================================================

def _identify_coverage_shell(world: WorldState) -> CoverageShell:
    """Identify the defensive coverage shell pre-snap.

    Reads safety alignment to determine coverage family:
    - 2 high safeties (12+ yards deep) = Cover 2/4 family
    - 1 high safety (center field) = Cover 1/3 family
    - 0 high safeties = Cover 0 (blitz)

    QB awareness affects accuracy of read.
    """
    awareness = world.me.attributes.awareness
    los_y = world.los_y

    # Find safeties (players deep in secondary)
    deep_safeties = []
    for opp in world.opponents:
        if opp.position in (Position.FS, Position.SS):
            depth = los_y - opp.pos.y  # How far behind LOS
            if depth > 10:  # Deep safety
                deep_safeties.append(opp)

    # Count safeties and their alignment
    num_deep = len(deep_safeties)

    if num_deep == 0:
        # No deep safety = Cover 0 (blitz look)
        return CoverageShell.COVER_0

    elif num_deep == 1:
        # Single high safety
        safety = deep_safeties[0]
        # Check if centered or shaded
        if abs(safety.pos.x) < 5:
            # Centered = Cover 1 or Cover 3
            # Check corners for depth hint
            return CoverageShell.COVER_1  # Default to Cover 1
        else:
            # Shaded = likely Cover 3
            return CoverageShell.COVER_3

    elif num_deep >= 2:
        # Two high safeties
        # Check their split
        xs = [s.pos.x for s in deep_safeties]
        split = abs(xs[0] - xs[1]) if len(xs) >= 2 else 0

        if split > 20:
            # Wide split = Cover 2
            return CoverageShell.COVER_2
        else:
            # Tighter split = Cover 4 (quarters)
            return CoverageShell.COVER_4

    # Low awareness QBs may misread
    if awareness < 75:
        # Sometimes return wrong read
        import random
        if random.random() < 0.2:
            return CoverageShell.UNKNOWN

    return CoverageShell.UNKNOWN


def _detect_blitz_look(world: WorldState) -> Tuple[BlitzLook, List[str]]:
    """Detect pre-snap blitz indicators.

    Looks for:
    - Walked-up linebackers (LBs at or near LOS)
    - Safety creep toward LOS
    - Overloaded rush side (more rushers than blockers)

    Returns:
        (blitz_look, list of player IDs showing blitz)
    """
    los_y = world.los_y
    blitzers = []

    # Check for walked-up LBs
    for opp in world.opponents:
        if opp.position in (Position.MLB, Position.OLB, Position.ILB):
            depth = los_y - opp.pos.y
            if depth < 3:  # Within 3 yards of LOS = walked up
                blitzers.append(opp.id)

        # Check for safety creep
        elif opp.position in (Position.FS, Position.SS):
            depth = los_y - opp.pos.y
            if depth < 8:  # Safety unusually close
                blitzers.append(opp.id)

    # Determine blitz severity
    num_potential_blitzers = len(blitzers)

    if num_potential_blitzers == 0:
        return BlitzLook.NONE, []
    elif num_potential_blitzers == 1:
        return BlitzLook.LIGHT, blitzers
    elif num_potential_blitzers >= 2:
        # Check if Cover 0 (no deep safety)
        has_deep_safety = any(
            (opp.position in (Position.FS, Position.SS) and los_y - opp.pos.y > 10)
            for opp in world.opponents
        )
        if not has_deep_safety:
            return BlitzLook.ZERO, blitzers
        return BlitzLook.HEAVY, blitzers

    return BlitzLook.NONE, []


def _get_hot_route_for_blitz(
    world: WorldState,
    blitz_look: BlitzLook,
    coverage: CoverageShell,
) -> Optional[dict]:
    """Determine hot routes based on blitz and coverage.

    Hot routes convert longer-developing routes to quick throws
    to beat the blitz.

    Returns:
        Dict of {player_id: new_route_name} or None
    """
    if blitz_look == BlitzLook.NONE:
        return None

    hot_routes = {}

    # Find eligible receivers for hot routes
    for teammate in world.teammates:
        if teammate.position not in (Position.WR, Position.TE, Position.RB):
            continue

        # Inside receiver on blitz side gets hot route
        # For now, simplify: convert first WR to slant on heavy blitz
        if blitz_look in (BlitzLook.HEAVY, BlitzLook.ZERO):
            if teammate.position == Position.WR:
                # Hot to quick slant
                hot_routes[teammate.id] = "slant"
                break  # Only one hot route for now

        elif blitz_look == BlitzLook.LIGHT:
            # Light blitz - RB can check release for outlet
            if teammate.position == Position.RB:
                hot_routes[teammate.id] = "checkdown"
                break

    return hot_routes if hot_routes else None


def _get_protection_call(
    world: WorldState,
    blitz_look: BlitzLook,
    blitzers: List[str],
) -> Optional[str]:
    """Generate protection call for OL.

    Returns slide direction and MIKE identification.
    """
    if blitz_look == BlitzLook.NONE:
        return None

    # Find the blitz side
    blitz_xs = []
    for opp in world.opponents:
        if opp.id in blitzers:
            blitz_xs.append(opp.pos.x)

    if not blitz_xs:
        return None

    avg_blitz_x = sum(blitz_xs) / len(blitz_xs)

    # Slide protection toward blitz side
    if avg_blitz_x > 0:
        return "slide_right"
    else:
        return "slide_left"


# =============================================================================
# Time Thresholds
# =============================================================================

def _get_time_thresholds(awareness: int) -> dict:
    """Get timing thresholds based on awareness."""
    # Base thresholds
    thresholds = {
        "early_end": 1.5,      # End of early/patient phase
        "normal_end": 2.5,     # End of normal phase
        "late_end": 3.0,       # End of late phase
        "critical_end": 3.5,   # End of critical, must act
        "forced": 4.0,         # Force throw or scramble
    }

    # Modify based on awareness
    if awareness >= 90:
        modifier = 0.3
    elif awareness < 70:
        modifier = -0.2
    else:
        modifier = 0.0

    return {k: v + modifier for k, v in thresholds.items()}


# =============================================================================
# Main Brain Function
# =============================================================================

def qb_brain(world: WorldState) -> BrainDecision:
    """QB brain - called every tick while QB has the ball.

    Args:
        world: Complete world state from QB's perspective

    Returns:
        BrainDecision with action and reasoning
    """
    # =========================================================================
    # Pre-Snap Phase - Read defense, call hot routes
    # =========================================================================
    if world.phase == PlayPhase.PRE_SNAP:
        # Identify coverage shell
        coverage = _identify_coverage_shell(world)

        # Detect blitz indicators
        blitz_look, blitzers = _detect_blitz_look(world)

        # Determine hot routes if blitz detected
        hot_routes = _get_hot_route_for_blitz(world, blitz_look, coverage)

        # Get protection call for OL
        protection_call = _get_protection_call(world, blitz_look, blitzers)

        # Build reasoning
        reasoning_parts = [f"Coverage: {coverage.value}"]
        if blitz_look != BlitzLook.NONE:
            reasoning_parts.append(f"Blitz look: {blitz_look.value}")
        if hot_routes:
            reasoning_parts.append(f"Hot routes: {list(hot_routes.keys())}")
        if protection_call:
            reasoning_parts.append(f"Protection: {protection_call}")

        return BrainDecision(
            intent="pre_snap_read",
            hot_routes=hot_routes,
            protection_call=protection_call,
            reasoning=", ".join(reasoning_parts),
        )

    # =========================================================================
    # Post-Snap Logic
    # =========================================================================
    state = _get_state(world.me.id)

    # Reset state at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

    # If we don't have the ball, something is wrong
    if not world.me.has_ball:
        return BrainDecision.hold("No longer have ball")

    # Calculate pressure
    pressure, threats = _calculate_pressure(world)
    state.pressure_level = pressure

    # Evaluate receivers
    receivers = _evaluate_receivers(world)

    # Get timing thresholds
    thresholds = _get_time_thresholds(world.me.attributes.awareness)

    # Phase: Dropback
    if not state.dropback_complete:
        dropback_target = _get_dropback_target(world)
        distance_to_target = world.me.pos.distance_to(dropback_target)

        if distance_to_target < 0.5:
            # Dropback complete
            state.dropback_complete = True
            state.set_time = world.current_time
            return BrainDecision(
                intent="set",
                reasoning="Dropback complete, setting in pocket",
            )

        # Check for hot route on blitz
        if pressure in (PressureLevel.HEAVY, PressureLevel.CRITICAL):
            # Look for hot route
            for recv in receivers:
                if recv.is_hot and recv.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
                    return BrainDecision(
                        action="throw",
                        target_id=recv.player_id,
                        action_target=recv.position,
                        reasoning=f"Hot route triggered! {recv.player_id} has {recv.separation:.1f}yd sep",
                    )

        return BrainDecision(
            move_target=dropback_target,
            move_type="backpedal",
            intent="dropback",
            reasoning=f"Executing dropback, {distance_to_target:.1f}yd to set point",
        )

    # Phase: Pocket (post-dropback)
    time_in_pocket = world.current_time - state.set_time
    state.time_in_pocket = time_in_pocket

    # =========================================================================
    # Critical Pressure Response
    # =========================================================================
    accuracy = world.me.attributes.throw_accuracy

    if pressure == PressureLevel.CRITICAL:
        # Must make immediate decision
        best, is_anticipation, find_reason = _find_best_receiver(
            receivers, state.current_read, pressure, accuracy
        )

        if best and best.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=best.position,
                reasoning=f"Critical pressure! Quick release to {best.player_id} ({best.separation:.1f}yd sep)",
            )

        # Can we throw it away?
        if _should_throw_away(world):
            return BrainDecision(
                action="throw",
                action_target=_get_throw_away_target(world),
                intent="throw_away",
                reasoning="Critical pressure, throwing ball away",
            )

        # Forced throw to best available
        if best:
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=best.position,
                reasoning=f"Critical pressure! Forced throw to {best.player_id} ({best.status.value})",
            )

        # Scramble as last resort
        escape = _find_escape_lane(world)
        if escape:
            state.scramble_committed = True
            return BrainDecision(
                move_target=escape,
                move_type="sprint",
                intent="scramble",
                reasoning="Critical pressure, no receivers, scrambling!",
            )

        # Brace for sack
        return BrainDecision(
            intent="protect_ball",
            reasoning="Critical pressure, no escape, protecting ball",
        )

    # =========================================================================
    # Heavy Pressure Response
    # =========================================================================
    if pressure == PressureLevel.HEAVY:
        # Find escape lane
        escape = _find_escape_lane(world)

        if escape:
            # Move to escape while evaluating
            best, is_anticipation, find_reason = _find_best_receiver(
                receivers, state.current_read, pressure, accuracy
            )

            if best and best.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
                return BrainDecision(
                    action="throw",
                    target_id=best.player_id,
                    action_target=best.position,
                    reasoning=f"Heavy pressure, throwing on move to {best.player_id}",
                )

            return BrainDecision(
                move_target=escape,
                move_type="run",
                intent="escape",
                reasoning=f"Heavy pressure, sliding to escape lane",
            )

        # No escape - accelerate reads
        state.current_read = min(state.current_read + 1, 4)

    # =========================================================================
    # Moderate Pressure Response
    # =========================================================================
    if pressure == PressureLevel.MODERATE:
        escape = _find_escape_lane(world)
        if escape and time_in_pocket > thresholds["normal_end"]:
            # Buy time by sliding
            return BrainDecision(
                move_target=escape,
                move_type="run",
                intent="buy_time",
                reasoning="Moderate pressure, sliding to buy time",
            )

    # =========================================================================
    # Normal Read Progression (Clean/Light Pressure)
    # =========================================================================

    # Get current read receiver with anticipation check
    best, is_anticipation, find_reason = _find_best_receiver(
        receivers, state.current_read, pressure, accuracy
    )

    # Check if receiver is open or anticipation throw available
    if best:
        if is_anticipation:
            # Anticipation throw - throw to where receiver will be
            # Calculate throw lead position (receiver position + velocity projection)
            lead_time = 0.2 if accuracy >= 90 else 0.15  # Anticipation window
            lead_pos = best.position  # TODO: Add velocity-based lead
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=lead_pos,
                reasoning=f"ANTICIPATION to {best.player_id}! {find_reason} ({best.separation:.1f}yd sep)",
            )
        elif best.status == ReceiverStatus.OPEN:
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=best.position,
                reasoning=f"Read {state.current_read}: {best.player_id} OPEN ({best.separation:.1f}yd sep)",
            )
        elif best.status == ReceiverStatus.WINDOW:
            # Window throw - acceptable with good accuracy
            if accuracy >= 80:
                return BrainDecision(
                    action="throw",
                    target_id=best.player_id,
                    action_target=best.position,
                    reasoning=f"Read {state.current_read}: {best.player_id} in window ({best.separation:.1f}yd sep)",
                )

    # Move to next read if time allows
    time_per_read = 0.6  # About 0.6s per read
    if time_in_pocket > state.current_read * time_per_read:
        if state.current_read < 4:
            state.current_read += 1
            return BrainDecision(
                intent="scanning",
                reasoning=f"Read {state.current_read - 1} covered, moving to read {state.current_read}",
            )

    # Time expired - must decide
    if time_in_pocket > thresholds["forced"]:
        if best:
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=best.position,
                reasoning=f"Time expired, forcing throw to {best.player_id}",
            )

        # Scramble
        escape = _find_escape_lane(world)
        if escape:
            state.scramble_committed = True
            return BrainDecision(
                move_target=escape,
                move_type="sprint",
                intent="scramble",
                reasoning="Time expired, no receivers, committing to scramble",
            )

        # Throw away if possible
        if _should_throw_away(world):
            return BrainDecision(
                action="throw",
                action_target=_get_throw_away_target(world),
                intent="throw_away",
                reasoning="Time expired, throwing ball away",
            )

    # Default: continue scanning
    return BrainDecision(
        intent="scanning",
        reasoning=f"Read {state.current_read}: evaluating ({time_in_pocket:.1f}s in pocket)",
    )
