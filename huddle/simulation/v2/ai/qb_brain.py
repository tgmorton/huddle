"""QB Brain - Decision-making for quarterbacks.

COMPLETION-FIRST PHILOSOPHY:
The QB's goal is to COMPLETE PASSES and ADVANCE THE BALL. Everything else
is in service of that goal:
- Reads find WHO IS OPEN (not which matchup to exploit)
- Pressure affects throw quality (it's an obstacle, not something to "beat")
- Scrambling = extend play to find open receiver OR gain yards
- Checkdowns happen when primary options are covered

The QB brain manages:
- Pre-snap reads: Identify where open receivers will be
- Hot route calls: Quick throws when pressure threatens completion
- Dropback execution: Get to throwing platform
- Read progression: Find the open receiver to complete the pass
- Platform stability: Pressure affects throw quality (move to maintain)
- Throw/scramble: Complete the pass or gain yards

Lifecycle: PRE_SNAP → SNAP → DROPBACK → POCKET → THROW/SCRAMBLE/SACK
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import QBContext
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from ..core.trace import get_trace_system, TraceCategory
from .shared.perception import calculate_effective_vision, angle_between, VisionParams
from ..core.variance import (
    decision_hesitation,
    should_make_suboptimal_decision,
    target_selection_noise,
    execution_timing,
)


# =============================================================================
# QB State Enums
# =============================================================================

class PressureLevel(str, Enum):
    """Platform stability - how clean is our throwing platform.

    COMPLETION-FIRST: Pressure is an OBSTACLE to completing passes,
    not something to "beat". Higher pressure = harder to throw accurately.
    """
    CLEAN = "clean"       # Stable platform, can make any throw
    LIGHT = "light"       # Minor disruption, most throws available
    MODERATE = "moderate" # Platform unstable, may need to move for completion
    HEAVY = "heavy"       # Must complete quickly or move to maintain platform
    CRITICAL = "critical" # Platform lost - quick release or extend play


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
    velocity: Vec2  # Receiver's current velocity for throw lead calculation
    separation: float
    status: ReceiverStatus
    nearest_defender_id: str
    nearest_defender_pos: Optional[Vec2] = None  # For far-shoulder throw placement
    defender_closing_speed: float = 0.0
    route_phase: str = ""
    is_hot: bool = False
    read_order: int = 99
    # Anticipation throw fields
    defender_trailing: bool = False  # Is defender behind receiver?
    pre_break: bool = False  # Is receiver pre-break?
    anticipation_viable: bool = False  # Can throw anticipation?
    # Vision-based detection quality (1.0 = central, lower = peripheral)
    detection_quality: float = 1.0
    # Route info for throw targeting
    break_point: Optional[Vec2] = None  # Where receiver will cut
    route_direction: str = ""  # "inside", "outside", "vertical"
    route_settles: bool = False  # True for curl/hitch, False for slant/go
    settle_point: Optional[Vec2] = None  # Where settling routes stop


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
    # Variance-affected timing (set once per play)
    time_per_read: float = 0.0  # 0 = not yet calculated


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
# Debug Trace System (uses centralized TraceSystem)
# =============================================================================

# Module-level reference for backward compatibility
_trace_enabled: bool = False
_trace_buffer: list[str] = []
_current_qb_id: str = ""
_current_qb_name: str = ""


def enable_trace(enabled: bool = True):
    """Enable or disable debug tracing.

    DEPRECATED: Use get_trace_system().enable() instead.
    This function is kept for backward compatibility.

    Args:
        enabled: Whether to enable tracing (default True)
    """
    global _trace_enabled, _trace_buffer
    _trace_enabled = enabled
    if enabled:
        _trace_buffer = []  # Clear on enable
    # Also enable centralized trace system
    get_trace_system().enable(enabled)


def get_trace() -> list[str]:
    """Get a copy of the current trace buffer.

    DEPRECATED: Use get_trace_system().get_entries() instead.
    This function is kept for backward compatibility.

    Returns:
        List of trace messages in order
    """
    return _trace_buffer.copy()


def _set_trace_context(player_id: str, player_name: str):
    """Set the current QB context for tracing."""
    global _current_qb_id, _current_qb_name
    _current_qb_id = player_id
    _current_qb_name = player_name


def _trace(msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace message to both local buffer and centralized system.

    Args:
        msg: Message to add to trace
        category: Type of trace (perception, decision, action)
    """
    global _trace_buffer
    if _trace_enabled:
        _trace_buffer.append(msg)
    # Always send to centralized system (it checks if enabled internally)
    trace = get_trace_system()
    trace.trace(_current_qb_id, _current_qb_name, category, msg)


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


# =============================================================================
# QB Intangible Effects
# =============================================================================

def _calculate_poise_effects(poise: int) -> dict:
    """Calculate behavioral effects based on poise rating.

    BEHAVIORAL PHILOSOPHY: High poise QBs LOOK different, not just perform better.
    - Low poise: Bails from clean pockets early, locks onto first read
    - High poise: Stays in pocket until real pressure, continues progression

    From research (msg 068): 28.4% pressure penalty difference between high/low poise QBs.

    Args:
        poise: QB's poise rating (0-99)

    Returns:
        Dict with behavioral modifiers:
        - pressure_escalation: How much worse pressure feels (0.6-1.4)
        - progression_under_pressure: Can continue reads under heavy pressure (bool)
        - pocket_bail_threshold: PressureLevel at which QB starts escaping
        - read_lock_under_pressure: Locks onto current read under pressure (bool)
    """
    # Normalize poise to -0.5 to +0.5 range (50 = baseline)
    poise_factor = (poise - 50) / 100.0

    # How early QB perceives pressure as threatening
    # Low poise (30): pressure_escalation = 1.4 (MODERATE feels like HEAVY)
    # High poise (90): pressure_escalation = 0.6 (HEAVY feels like MODERATE)
    pressure_escalation = 1.0 - poise_factor * 0.8

    # Can QB continue through read progression under heavy pressure?
    # High poise (75+): Can still progress through reads
    # Low poise (<60): Locks onto current read, can't process further
    progression_under_pressure = poise >= 75
    read_lock_under_pressure = poise < 60

    # At what pressure level does QB start looking to escape?
    # High poise (85+): Only CRITICAL makes them bail
    # Normal (60-84): HEAVY makes them bail
    # Low poise (<60): MODERATE makes them bail
    if poise >= 85:
        pocket_bail_threshold = PressureLevel.CRITICAL
    elif poise >= 60:
        pocket_bail_threshold = PressureLevel.HEAVY
    else:
        pocket_bail_threshold = PressureLevel.MODERATE

    return {
        "pressure_escalation": pressure_escalation,
        "progression_under_pressure": progression_under_pressure,
        "pocket_bail_threshold": pocket_bail_threshold,
        "read_lock_under_pressure": read_lock_under_pressure,
    }


def _calculate_decision_making_effects(decision_making: int) -> dict:
    """Calculate behavioral effects based on decision-making rating.

    BEHAVIORAL PHILOSOPHY: Decision-making affects WHAT the QB throws, not HOW.
    - Low decision-making: Forces throws into coverage, doesn't check down
    - High decision-making: Takes what defense gives, knows when to live for another play

    From research (msg 068): 10x INT rate difference on short throws between good/bad decision-makers.

    Args:
        decision_making: QB's decision-making rating (0-99)

    Returns:
        Dict with behavioral modifiers:
        - coverage_threshold: Separation needed to consider "throwable" (lower = more aggressive)
        - force_throw_chance: Chance to force throw into coverage (higher = worse decisions)
        - checkdown_willingness: How readily QB takes checkdown (higher = smarter)
        - tight_window_willingness: Will attempt contested throws (higher = more willing)
    """
    # Normalize to -0.5 to +0.5 range (50 = baseline)
    dm_factor = (decision_making - 50) / 100.0

    # Coverage threshold - separation required to throw
    # Low DM (30): 1.0 yd separation = "throw it" (too aggressive)
    # High DM (90): 2.5 yd separation required (patient, smart)
    coverage_threshold = 1.5 - dm_factor * 1.0

    # Chance to force a bad throw into coverage
    # Low DM: 30% chance to throw into tight coverage anyway
    # High DM: 5% chance (occasional brain fart)
    if decision_making >= 85:
        force_throw_chance = 0.05
    elif decision_making >= 70:
        force_throw_chance = 0.10
    elif decision_making >= 55:
        force_throw_chance = 0.15
    else:
        force_throw_chance = 0.25 + (55 - decision_making) / 100.0  # Up to 0.30

    # Checkdown willingness - how readily QB takes the short safe option
    # High DM: Immediately takes checkdown when primary is covered
    # Low DM: Keeps looking for home run, misses easy completion
    checkdown_willingness = 0.5 + dm_factor * 0.5  # 0.25 to 0.75

    # Tight window willingness - will attempt contested catches
    # This is more of a style trait - aggressive vs conservative
    tight_window_willingness = 1.0 - dm_factor * 0.6  # Low DM = more willing to force

    return {
        "coverage_threshold": coverage_threshold,
        "force_throw_chance": force_throw_chance,
        "checkdown_willingness": checkdown_willingness,
        "tight_window_willingness": tight_window_willingness,
    }


def _get_effective_pressure(
    actual_pressure: PressureLevel,
    poise: int,
) -> PressureLevel:
    """Get the pressure level as perceived by the QB based on poise.

    Low poise QBs feel more pressure than actually exists.
    High poise QBs stay calm even when pressure is real.

    This is the key behavioral difference - it affects everything downstream:
    - When to look for escape routes
    - Whether to accelerate reads
    - When to throw it away vs staying patient
    """
    poise_effects = _calculate_poise_effects(poise)
    escalation = poise_effects["pressure_escalation"]

    # Map pressure to numeric value
    pressure_values = {
        PressureLevel.CLEAN: 0,
        PressureLevel.LIGHT: 1,
        PressureLevel.MODERATE: 2,
        PressureLevel.HEAVY: 3,
        PressureLevel.CRITICAL: 4,
    }
    value_to_pressure = {v: k for k, v in pressure_values.items()}

    actual_value = pressure_values[actual_pressure]
    perceived_value = int(actual_value * escalation)
    perceived_value = max(0, min(4, perceived_value))  # Clamp to valid range

    return value_to_pressure[perceived_value]


def _get_qb_facing(world: WorldState) -> Vec2:
    """Get the direction the QB is facing.

    Prioritizes explicit facing direction (from scanning) over velocity.
    This allows QB to look at receivers while moving in the pocket.
    """
    # If facing is explicitly set (not default 0,1), use it
    # This happens when QB is scanning through reads
    if world.me.facing:
        facing = world.me.facing
        # Check if facing is NOT the default (0, 1) direction
        # i.e., has been explicitly set to look at a receiver
        if abs(facing.x) > 0.1 or facing.y < 0.9:
            return facing.normalized()

    # Otherwise use velocity if moving forward/lateral
    vel = world.me.velocity
    if vel and vel.length() > 0.5:
        if vel.y >= 0:  # Forward or lateral movement
            return vel.normalized()

    # Fallback: face downfield
    return Vec2(0, 1)


def _get_read_target_facing(world: WorldState, read_order: int) -> Optional[Vec2]:
    """Get facing direction toward a specific read target.

    Looks at ALL teammates (not just visible ones) to find the read target.
    This allows QB to face toward receivers before they're in the vision cone.
    """
    for teammate in world.teammates:
        if teammate.read_order == read_order:
            to_target = teammate.pos - world.me.pos
            if to_target.length() > 0.1:
                return to_target.normalized()
    return None


def _calculate_pressure(world: WorldState) -> Tuple[PressureLevel, List[PlayerView]]:
    """Calculate platform stability based on defender proximity.

    COMPLETION-FIRST: This determines how clean our throwing platform is.
    Defenders are obstacles to making accurate throws - their proximity
    degrades our ability to complete passes.

    Returns:
        (platform_stability, list of nearby obstacles)
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

        # Blocker protection check - reduce threat if OL is between threat and QB
        threat_blocked = False
        for teammate in world.teammates:
            if teammate.position not in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
                continue
            # Check if blocker is between threat and QB
            # Blocker is "between" if:
            # 1. Closer to threat than QB is
            # 2. Roughly in the lane (within 2 yards of threat-QB line)
            blocker_to_threat = teammate.pos.distance_to(opp.pos)
            if blocker_to_threat < distance:  # Blocker is closer to threat than QB
                # Check if blocker is in the lane (perpendicular distance to threat-QB line)
                threat_to_qb = qb_pos - opp.pos
                threat_to_blocker = teammate.pos - opp.pos
                if threat_to_qb.length() > 0.1:
                    # Project blocker onto threat-QB line
                    t = threat_to_blocker.dot(threat_to_qb) / threat_to_qb.dot(threat_to_qb)
                    if 0 < t < 1:  # Blocker is between (not behind threat or past QB)
                        closest_point = opp.pos + threat_to_qb * t
                        lane_distance = teammate.pos.distance_to(closest_point)
                        if lane_distance < 2.0:  # Within 2 yards of direct path
                            threat_blocked = True
                            break

        if threat_blocked:
            threat_score *= 0.3  # Significantly reduce threat if blocked

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

    _trace(f"[VISION SETUP] t={world.time_since_snap:.2f}s, facing=({qb_facing.x:.2f}, {qb_facing.y:.2f})")

    # Get position labels for tracing (e.g., "WR", "TE1")
    position_counts = {}

    for teammate in world.teammates:
        # Only evaluate receivers
        if teammate.position not in (Position.WR, Position.TE, Position.RB):
            continue

        # Generate position label for tracing
        pos_name = teammate.position.name
        position_counts[pos_name] = position_counts.get(pos_name, 0) + 1
        label = f"{pos_name}{position_counts[pos_name]}" if position_counts[pos_name] > 1 else pos_name

        to_receiver = teammate.pos - qb_pos
        distance = to_receiver.length()
        read_order = getattr(teammate, 'read_order', 0) or 99

        # No vision cone filtering - QB can evaluate all receivers
        # Decision is based on projected separation at ball arrival
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

        # PROJECT SEPARATION TO BALL ARRIVAL TIME
        # This is the key insight: "open now" doesn't mean "open when ball arrives"
        qb_pos = world.me.pos
        throw_distance = qb_pos.distance_to(teammate.pos)

        # Estimate ball flight time (based on throw power ~60-80 fps)
        throw_power = getattr(world.me.attributes, 'throw_power', 80)
        ball_speed = 50 + (throw_power - 50) * 0.76  # 50-88 fps range
        # Shorter passes thrown softer
        if throw_distance < 10:
            ball_speed *= 0.75
        elif throw_distance < 20:
            ball_speed *= 0.9
        flight_time = throw_distance / ball_speed
        flight_time = min(flight_time, 0.8)  # Cap at 0.8s

        # Project receiver position at ball arrival
        receiver_at_arrival = Vec2(
            teammate.pos.x + teammate.velocity.x * flight_time,
            teammate.pos.y + teammate.velocity.y * flight_time
        )

        # Project defender position at ball arrival
        defender_trailing = False
        if nearest_def:
            defender_at_arrival = Vec2(
                nearest_def.pos.x + nearest_def.velocity.x * flight_time,
                nearest_def.pos.y + nearest_def.velocity.y * flight_time
            )

            # Separation AT BALL ARRIVAL (not current separation)
            projected_sep = receiver_at_arrival.distance_to(defender_at_arrival)

            # Check if defender is trailing (behind receiver relative to QB)
            receiver_to_qb = (qb_pos - teammate.pos).normalized()
            def_to_receiver = (teammate.pos - nearest_def.pos).normalized()
            if receiver_to_qb.dot(def_to_receiver) > 0.5:
                defender_trailing = True
                projected_sep += 0.5  # Trailing defender = slightly easier catch
            elif receiver_to_qb.dot(def_to_receiver) < -0.3:
                projected_sep -= 1.0  # Undercutting = much harder, potential INT
        else:
            projected_sep = 10.0  # No defender nearby

        effective_sep = projected_sep

        # Determine status based on PROJECTED separation at ball arrival
        # These thresholds represent NFL-quality openness:
        # - OPEN (>5yd): Easy throw, high completion probability
        # - WINDOW (>3yd): Makeable throw, requires accuracy
        # - CONTESTED (>1.5yd): Tight window, 50/50 ball
        # - COVERED (<1.5yd): Don't throw here
        if effective_sep > 5.0:
            status = ReceiverStatus.OPEN
        elif effective_sep > 3.0:
            status = ReceiverStatus.WINDOW
        elif effective_sep > 1.5:
            status = ReceiverStatus.CONTESTED
        else:
            status = ReceiverStatus.COVERED

        # Use ACTUAL route phase from route runner, not time-based estimates
        # This is critical for accurate throw lead calculation
        route_phase = getattr(teammate, 'route_phase', "") or "stem"
        pre_break = getattr(teammate, 'pre_break', True)

        # Check if receiver was assigned a hot route
        is_hot = bool(world.hot_routes and teammate.id in world.hot_routes)

        # Trace receiver evaluation
        hot_tag = " HOT" if is_hot else ""
        _trace(f"[EVAL] R{read_order} {label}: {status.value} (proj_sep={effective_sep:.1f}yd{hot_tag})")

        evaluations.append(ReceiverEval(
            player_id=teammate.id,
            position=teammate.pos,
            velocity=teammate.velocity,  # For throw lead calculation
            separation=effective_sep,
            status=status,
            nearest_defender_id=nearest_def.id if nearest_def else "",
            nearest_defender_pos=nearest_def.pos if nearest_def else None,  # For far-shoulder placement
            defender_closing_speed=closing_speed,
            route_phase=route_phase,
            is_hot=is_hot,
            read_order=getattr(teammate, 'read_order', 0) or 99,  # 0 means unassigned → low priority
            defender_trailing=defender_trailing,
            pre_break=pre_break,
            detection_quality=detection_quality,  # Lower for peripheral receivers
            break_point=getattr(teammate, 'break_point', None),  # Where receiver will cut
            route_direction=getattr(teammate, 'route_direction', ""),  # inside/outside/vertical
            route_settles=getattr(teammate, 'route_settles', False),  # curl/hitch settle
            settle_point=getattr(teammate, 'settle_point', None),  # Where settling routes stop
        ))

    # Sort by read order
    evaluations.sort(key=lambda e: e.read_order)
    return evaluations


def _can_throw_anticipation(
    accuracy: int,
    receiver: ReceiverEval,
    pressure: PressureLevel,
    time_in_pocket: float = 0.0,
    anticipation: int = 50,
) -> Tuple[bool, str]:
    """Check if QB can throw anticipation pass.

    ANTICIPATION ATTRIBUTE determines how early QB can throw before receiver breaks:
        - Rating 95: releases 0.18s BEFORE break (elite timing)
        - Rating 50: releases AT break (average)
        - Rating 30: must wait until receiver is visibly open

    The formula: throw_timing = route_break_time - (anticipation - 50) / 100 * 0.4

    Requirements for anticipation:
        1. Receiver is pre-break
        2. QB anticipation rating allows early throw
        3. Defender is trailing (not undercutting)
        4. Clean pocket (not heavy/critical pressure)
        5. Minimum time in pocket (0.4s) - QB needs time to evaluate
        6. Minimum separation (2.0 yards) - can't throw into tight coverage

    Returns:
        (can_anticipate, reasoning)
    """
    # Minimum time in pocket - QB needs time to scan before anticipation
    if time_in_pocket < 0.4:
        return False, f"too early ({time_in_pocket:.2f}s), need 0.4s minimum"

    # Minimum separation - can't anticipate into tight coverage
    if receiver.separation < 2.0:
        return False, f"separation too tight ({receiver.separation:.1f}yd < 2.0yd)"

    # Can only anticipate to pre-break receivers
    if not receiver.pre_break:
        return False, "receiver past break point"

    # Pressure check - no anticipation under heavy pressure
    if pressure in (PressureLevel.HEAVY, PressureLevel.CRITICAL):
        return False, "too much pressure for anticipation"

    # Defender must be trailing
    if not receiver.defender_trailing:
        return False, "defender not trailing"

    # ANTICIPATION THRESHOLDS (primary factor for timing)
    # High anticipation QBs can throw earlier in the route
    if anticipation >= 90:
        # Elite anticipation - can throw 0.3s before break on any route
        return True, f"elite anticipation ({anticipation}), 0.3s before break"
    elif anticipation >= 75:
        # Good anticipation - can throw 0.2s before break
        return True, f"good anticipation ({anticipation}), 0.2s before break"
    elif anticipation >= 60:
        # Average anticipation - can throw only late stem / during break
        if receiver.route_phase == "break" or (receiver.route_phase == "stem" and receiver.separation > 2.5):
            return True, f"average anticipation ({anticipation}), timing at break"
        return False, f"anticipation ({anticipation}) requires later throw timing"
    else:
        # Low anticipation - must wait until receiver is visibly open
        # Ball arrives late, defenders can close
        return False, f"low anticipation ({anticipation}), must see receiver open"


def _find_best_receiver(
    evaluations: List[ReceiverEval],
    current_read: int,
    pressure: PressureLevel,
    accuracy: int = 75,
    time_in_pocket: float = 0.0,
    anticipation: int = 50,
) -> Tuple[Optional[ReceiverEval], bool, str]:
    """Find the best receiver to throw to.

    Args:
        evaluations: List of receiver evaluations
        current_read: Current read in progression
        pressure: Current pressure level
        accuracy: QB throw accuracy attribute
        time_in_pocket: How long QB has been set in pocket
        anticipation: QB anticipation attribute (affects early throw timing)

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
        _trace(f"[READ] Read {current_read} ({current_eval.player_id}): {current_eval.status.value}")
        # Check if currently open
        if current_eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            _trace(f"[READ] -> THROW to read {current_read}")
            return current_eval, False, f"read {current_read} open"

        # Check for anticipation throw
        can_anticipate, anticipate_reason = _can_throw_anticipation(
            accuracy, current_eval, pressure, time_in_pocket, anticipation
        )
        if can_anticipate:
            _trace(f"[READ] -> ANTICIPATION to read {current_read}")
            return current_eval, True, f"anticipation: {anticipate_reason}"
        _trace(f"[READ] Read {current_read}: covered, checking next")
    else:
        _trace(f"[READ] Read {current_read}: NOT VISIBLE - skip")

    # If current read is covered, progress to next reads IN ORDER
    # Don't skip to any random open receiver - respect the progression
    for eval in evaluations:
        if eval.read_order > current_read:
            _trace(f"[READ] Read {eval.read_order} ({eval.player_id}): {eval.status.value}")
            if eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
                _trace(f"[READ] -> THROW to read {eval.read_order}")
                return eval, False, f"progressed to read {eval.read_order}"
            # Check anticipation on next reads too
            can_anticipate, anticipate_reason = _can_throw_anticipation(
                accuracy, eval, pressure, time_in_pocket, anticipation
            )
            if can_anticipate:
                return eval, True, f"anticipation on read {eval.read_order}: {anticipate_reason}"

    # All reads exhausted - check for any anticipation opportunity as last resort
    for eval in evaluations:
        can_anticipate, anticipate_reason = _can_throw_anticipation(
            accuracy, eval, pressure, time_in_pocket, anticipation
        )
        if can_anticipate and eval.separation > 2.0:  # Require good separation for last resort
            return eval, True, f"anticipation: {anticipate_reason}"

    return None, False, "no open receivers"


def _find_escape_lane(world: WorldState) -> Optional[Vec2]:
    """Find a lane to extend the play for a completion opportunity.

    COMPLETION-FIRST: We're not "escaping pressure" - we're moving
    to maintain a throwing platform or create a new completion window.
    The goal is still to complete a pass or gain yards.

    Uses pressure state to determine escape direction:
    - Escape away from closest threat
    - Use pocket geometry to find open lanes
    - Prioritize staying in throwing position
    """
    qb_pos = world.me.pos

    # Get pressure info if available
    pressure_state = getattr(world, 'pressure_state', None)

    # Determine where threats are coming from
    threat_from_left = False
    threat_from_right = False

    if pressure_state and pressure_state.threats:
        for threat in pressure_state.threats:
            if threat.is_blind_side:  # Blind side = left
                threat_from_left = True
            else:
                threat_from_right = True

    # Build escape options prioritized by threat direction
    extend_options = []

    # If pocket is collapsed on one side, escape to the other
    if threat_from_left and not threat_from_right:
        # Escape right - roll out to strong side
        extend_options.append(Vec2(qb_pos.x + 6, qb_pos.y - 1))
        extend_options.append(Vec2(qb_pos.x + 4, qb_pos.y + 2))  # Step up and right
    elif threat_from_right and not threat_from_left:
        # Escape left - roll out to weak side
        extend_options.append(Vec2(qb_pos.x - 6, qb_pos.y - 1))
        extend_options.append(Vec2(qb_pos.x - 4, qb_pos.y + 2))  # Step up and left
    else:
        # Pressure from both sides or no clear direction - step up in pocket
        extend_options.append(Vec2(qb_pos.x, qb_pos.y + 4))  # Step up - new throwing lane
        extend_options.append(Vec2(qb_pos.x + 5, qb_pos.y - 2))  # Roll right
        extend_options.append(Vec2(qb_pos.x - 5, qb_pos.y - 2))  # Roll left

    best_option = None
    best_clearance = 0.0

    for extend_pos in extend_options:
        # Find nearest obstacle to this position
        min_dist = float('inf')
        for opp in world.opponents:
            dist = opp.pos.distance_to(extend_pos)
            if dist < min_dist:
                min_dist = dist

        if min_dist > best_clearance:
            best_clearance = min_dist
            best_option = extend_pos

    # Lower threshold when pocket is collapsed - must escape
    min_clearance = 2.0 if (pressure_state and pressure_state.pocket_collapsed) else 3.0
    return best_option if best_clearance > min_clearance else None


def _get_dropback_target(world: WorldState) -> Vec2:
    """Get the target position for dropback.

    Uses the dropback_target_pos from WorldState which is calculated
    by the orchestrator based on the play's DropbackType.
    """
    # Use WorldState dropback target if available
    if world.dropback_target_pos:
        return world.dropback_target_pos
    # Fallback: standard 5-step drop (7 yards behind LOS)
    return Vec2(world.me.pos.x, world.los_y - world.dropback_depth)


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


def _calculate_throw_lead(
    qb_pos: Vec2,
    receiver: ReceiverEval,
    throw_power: int = 80,
) -> Vec2:
    """Calculate where to throw based on ROUTE STRUCTURE.

    ANTICIPATION WITH CAPITAL A:
    The QB TRUSTS the route. The receiver WILL be where the route says.
    We throw to where the ROUTE takes them, not extrapolating from velocity.

    Route types:
    1. SETTLING routes (curl, hitch, comeback) → throw to settle_point
    2. CONTINUING routes (slant, go, post, out, in) → throw to route endpoint with lead

    The QB knows:
    - What route the receiver is running
    - Where the route will take them (break_point, settle_point)
    - The timing of the route

    Args:
        qb_pos: QB position
        receiver: Receiver evaluation with route info
        throw_power: QB throw power attribute (affects ball speed)

    Returns:
        Target position based on route structure
    """
    # =======================================================================
    # SETTLING ROUTES: Curl, Hitch, Comeback - receiver STOPS at settle_point
    # Check this FIRST - these routes have a defined endpoint
    # =======================================================================
    if receiver.route_settles:
        settle_target = receiver.settle_point or receiver.break_point or receiver.position
        break_point = receiver.break_point

        # Calculate ball physics
        base_ball_speed = 50 + (throw_power - 50) * 0.76

        # Receiver speed (actual if moving, assumed if not)
        actual_speed = receiver.velocity.length()
        rcvr_speed = actual_speed if actual_speed > 2.0 else 6.5

        # =======================================================================
        # KEY INSIGHT: For curl/hitch routes, receiver goes PAST settle point
        # before curling back. pre_break means they're still on the stem!
        # =======================================================================
        if receiver.pre_break:
            # STILL ON STEM - throw to where they'll be on their current path
            # NOT to the settle point (they haven't even reached the break yet!)
            dist_to_receiver = qb_pos.distance_to(receiver.position)
            ball_speed = base_ball_speed * (0.8 if dist_to_receiver < 10 else 0.9)
            flight_time = dist_to_receiver / ball_speed
            flight_time = min(flight_time, 0.8)  # Cap at 0.8s

            # Use their actual velocity direction (running the stem)
            if receiver.velocity.length() > 0.1:
                stem_dir = receiver.velocity.normalized()
            else:
                # Fallback: toward break point (next waypoint for pre-break receiver)
                if break_point:
                    stem_dir = (break_point - receiver.position).normalized()
                else:
                    stem_dir = Vec2(0, 1)  # Default upfield

            lead_dist = rcvr_speed * flight_time
            target = receiver.position + stem_dir * lead_dist

            # If close to break point, cap there (let them make the break)
            if break_point:
                dist_to_break = receiver.position.distance_to(break_point)
                if lead_dist > dist_to_break:
                    # Would overshoot break - throw to break point area
                    target = break_point
        else:
            # POST-BREAK - receiver is curling back to settle point
            # Now we can throw to the settle point
            receiver_to_settle = settle_target.distance_to(receiver.position)

            if receiver_to_settle < 3.0:
                # Very close to settle - throw there
                target = settle_target
            else:
                # Calculate timing to settle point
                time_to_settle = receiver_to_settle / rcvr_speed if rcvr_speed > 0.1 else 0
                ball_dist_to_settle = qb_pos.distance_to(settle_target)
                ball_speed = base_ball_speed * (0.8 if ball_dist_to_settle < 10 else 0.9)
                ball_flight_time = ball_dist_to_settle / ball_speed

                if time_to_settle < ball_flight_time + 0.15:
                    # Receiver will reach settle point before ball - good!
                    target = settle_target
                else:
                    # Receiver is still far - throw to intercept point
                    dist_to_receiver = qb_pos.distance_to(receiver.position)
                    ball_speed_to_rcvr = base_ball_speed * (0.8 if dist_to_receiver < 10 else 0.9)
                    flight_time = dist_to_receiver / ball_speed_to_rcvr
                    flight_time = min(flight_time, 0.6)

                    # Use their actual velocity (curling toward settle)
                    if receiver.velocity.length() > 0.1:
                        curl_dir = receiver.velocity.normalized()
                    else:
                        curl_dir = (settle_target - receiver.position).normalized()

                    lead_dist = rcvr_speed * flight_time
                    target = receiver.position + curl_dir * lead_dist

                    # Don't overshoot the settle point
                    if target.distance_to(receiver.position) > receiver_to_settle:
                        target = settle_target

        # Far-shoulder adjustment for settling routes
        if receiver.nearest_defender_pos:
            away_from_def = target - receiver.nearest_defender_pos
            if away_from_def.length() > 0.1:
                def_dist = receiver.nearest_defender_pos.distance_to(target)
                if def_dist < 4.0:
                    # Small offset (0.5 yard) away from defender
                    offset = 0.5
                    target = target + away_from_def.normalized() * offset

        return target

    # =======================================================================
    # CONTINUING ROUTES: Slant, Go, Post, Out, In, Drag
    # Receiver maintains speed - throw where route takes them
    # =======================================================================

    # Calculate ball physics
    base_ball_speed = 50 + (throw_power - 50) * 0.76  # 50-88 fps range

    # =======================================================================
    # POST-BREAK: If receiver has already broken, use their ACTUAL movement
    # =======================================================================
    receiver_speed = receiver.velocity.length()

    if not receiver.pre_break and receiver.route_phase == "post_break":
        # Receiver has already broken - trust their current movement
        if receiver_speed < 1.0:
            # Barely moving post-break = settling route (hitch, curl)
            # Throw right at them
            target = receiver.position

            # Far-shoulder adjustment
            if receiver.nearest_defender_pos:
                away_from_def = target - receiver.nearest_defender_pos
                if away_from_def.length() > 0.1:
                    def_dist = receiver.nearest_defender_pos.distance_to(target)
                    if def_dist < 4.0:
                        offset = 0.5
                        target = target + away_from_def.normalized() * offset

            return target

        else:
            # Moving post-break - lead based on ACTUAL velocity
            dist_to_receiver = qb_pos.distance_to(receiver.position)
            if dist_to_receiver < 10:
                ball_speed = base_ball_speed * 0.8
            elif dist_to_receiver < 20:
                ball_speed = base_ball_speed * 0.9
            else:
                ball_speed = base_ball_speed

            flight_time = dist_to_receiver / ball_speed
            flight_time = min(flight_time, 0.8)

            # Lead based on actual velocity (they've already broken)
            lead_distance = receiver_speed * flight_time
            lead_dir = receiver.velocity.normalized()

            target = receiver.position + lead_dir * lead_distance

            # Far-shoulder adjustment
            if receiver.nearest_defender_pos:
                def_to_target = target - receiver.nearest_defender_pos
                if def_to_target.length() > 0.1:
                    def_dist = def_to_target.length()
                    if def_dist < 4.0:
                        offset = 1.0 - (def_dist / 4.0) * 0.5
                        target = target + def_to_target.normalized() * offset

            return target

    # =======================================================================
    # PRE-BREAK: Use route structure to anticipate where receiver will be
    # =======================================================================

    # Determine where the route takes the receiver
    # IMPORTANT: Only use break_point if receiver hasn't passed it yet!
    # If receiver is post-break, the break_point is BEHIND them.
    if receiver.break_point and receiver.pre_break:
        # Route has a defined break point
        break_point = receiver.break_point

        # How far is receiver from break point?
        receiver_to_break = break_point.distance_to(receiver.position)

        # Receiver speed (use actual if moving, otherwise assume 6.5)
        actual_speed = receiver.velocity.length()
        receiver_speed = actual_speed if actual_speed > 2.0 else 6.5

        # Time for receiver to reach break point
        time_to_break = receiver_to_break / receiver_speed if receiver_speed > 0.1 else 0

        # Determine post-break direction from route_direction
        if receiver.route_direction == "inside":
            # Slant, dig, post - continue inside after break
            if receiver.position.x > 0:
                post_break_dir = Vec2(-0.8, 0.4).normalized()
            else:
                post_break_dir = Vec2(0.8, 0.4).normalized()
        elif receiver.route_direction == "outside":
            # Out, corner - continue outside after break
            if receiver.position.x > 0:
                post_break_dir = Vec2(0.8, 0.2).normalized()
            else:
                post_break_dir = Vec2(-0.8, 0.2).normalized()
        else:
            # Vertical routes (go, seam) - continue upfield
            post_break_dir = Vec2(0, 1)

        # =======================================================================
        # ANTICIPATION: Trust the route - throw to where it takes them
        # =======================================================================
        # Calculate flight time to break point first
        break_dist = qb_pos.distance_to(break_point)
        if break_dist < 10:
            ball_speed = base_ball_speed * 0.8
        elif break_dist < 20:
            ball_speed = base_ball_speed * 0.9
        else:
            ball_speed = base_ball_speed

        flight_time_to_break = break_dist / ball_speed
        flight_time_to_break = min(flight_time_to_break, 1.0)

        # Will receiver pass through break before ball arrives there?
        if time_to_break < flight_time_to_break:
            # YES: Receiver reaches break first, then continues
            # Throw PAST the break point
            # Time receiver spends post-break before ball would reach break point
            post_break_time = flight_time_to_break - time_to_break

            # But we need to iterate - throw target is past break, so flight time changes
            target = break_point
            for _ in range(3):
                throw_dist = qb_pos.distance_to(target)
                if throw_dist < 10:
                    ball_speed = base_ball_speed * 0.8
                elif throw_dist < 20:
                    ball_speed = base_ball_speed * 0.9
                else:
                    ball_speed = base_ball_speed

                flight_time = throw_dist / ball_speed
                flight_time = min(flight_time, 1.0)

                # Receiver position when ball arrives
                if flight_time > time_to_break:
                    post_break_dist = receiver_speed * (flight_time - time_to_break)
                    target = break_point + post_break_dir * post_break_dist
                else:
                    target = break_point

            # Add YAC buffer past the catch point
            yac_buffer = 1.0
            target = target + post_break_dir * yac_buffer

        else:
            # NO: Ball arrives at break point before receiver gets there
            # This is an anticipation throw - throw to break point with YAC lead
            # Receiver will catch in stride as they arrive at break
            yac_buffer = 1.0
            target = break_point + post_break_dir * yac_buffer

    else:
        # No break point - use ACTUAL VELOCITY for continuing routes (like GO)
        # This is common for vertical routes that just keep running

        actual_speed = receiver.velocity.length()

        if actual_speed > 2.0:
            # Receiver is moving - use their actual velocity direction
            lead_dir = receiver.velocity.normalized()
            receiver_speed = actual_speed
        else:
            # Receiver barely moving - fall back to route_direction
            receiver_speed = 6.5  # Assume they'll get up to speed
            if receiver.route_direction == "inside":
                if receiver.position.x > 0:
                    lead_dir = Vec2(-0.7, 0.5).normalized()
                else:
                    lead_dir = Vec2(0.7, 0.5).normalized()
            elif receiver.route_direction == "outside":
                if receiver.position.x > 0:
                    lead_dir = Vec2(0.7, 0.3).normalized()
                else:
                    lead_dir = Vec2(-0.7, 0.3).normalized()
            else:
                # Default: use direction toward downfield from QB
                # In this coord system, downfield is +Y
                lead_dir = Vec2(0, 1)

        # Calculate lead based on distance and receiver speed
        dist_to_receiver = qb_pos.distance_to(receiver.position)
        if dist_to_receiver < 10:
            ball_speed = base_ball_speed * 0.8
        elif dist_to_receiver < 20:
            ball_speed = base_ball_speed * 0.9
        else:
            ball_speed = base_ball_speed

        flight_time = dist_to_receiver / ball_speed
        flight_time = min(flight_time, 1.0)  # Allow longer flight for deep routes

        lead_distance = receiver_speed * flight_time

        target = receiver.position + lead_dir * lead_distance

    # =======================================================================
    # FAR-SHOULDER ADJUSTMENT
    # Throw away from the defender so receiver can shield the ball
    # =======================================================================
    if receiver.nearest_defender_pos:
        def_to_target = target - receiver.nearest_defender_pos
        if def_to_target.length() > 0.1:
            def_dist = def_to_target.length()
            if def_dist < 4.0:
                # Offset 0.5-1.5 yards away from defender
                offset = 1.5 - (def_dist / 4.0)
                target = target + def_to_target.normalized() * offset

    return target


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

def qb_brain(world: QBContext) -> BrainDecision:
    """QB brain - called every tick while QB has the ball.

    Args:
        world: Complete world state from QB's perspective

    Returns:
        BrainDecision with action and reasoning
    """
    # Set trace context for this QB
    _set_trace_context(world.me.id, world.me.name)

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

    # On run plays, QB just holds position - handoff is handled by orchestrator timing
    if world.is_run_play:
        return BrainDecision(
            intent="handoff",
            reasoning="Run play - holding for handoff",
        )

    state = _get_state(world.me.id)

    # Reset state at start of play
    if world.tick == 0 or world.time_since_snap < 0.1:
        _reset_state(world.me.id)
        state = _get_state(world.me.id)

    # If we don't have the ball, something is wrong
    if not world.me.has_ball:
        return BrainDecision.hold("No longer have ball")

    # Calculate pressure
    actual_pressure, threats = _calculate_pressure(world)

    # Apply poise to determine how QB perceives pressure
    # Low poise: feels more pressure than exists (panics early)
    # High poise: stays calm under fire
    poise = world.me.attributes.get("poise", 60)  # Default to average poise
    perceived_pressure = _get_effective_pressure(actual_pressure, poise)
    poise_effects = _calculate_poise_effects(poise)

    # Use perceived pressure for decision-making (this is the key behavioral change)
    pressure = perceived_pressure
    state.pressure_level = pressure

    _trace(f"[POISE] poise={poise}, actual={actual_pressure.value}, perceived={pressure.value}")

    # Calculate decision-making effects
    # Low DM: forces throws into coverage, doesn't check down
    # High DM: takes what defense gives, knows when to live for another play
    decision_making = world.me.attributes.get("decision_making", 55)  # Default slightly above average
    dm_effects = _calculate_decision_making_effects(decision_making)

    # Get timing thresholds
    thresholds = _get_time_thresholds(world.me.attributes.awareness)

    # Phase: Dropback - use orchestrator's qb_is_set tracking
    # The orchestrator tracks when QB reaches depth AND completes the plant phase
    if not world.qb_is_set:
        dropback_target = _get_dropback_target(world)
        distance_to_target = world.me.pos.distance_to(dropback_target)

        # Check for hot route on blitz (can throw during dropback under pressure)
        # Only do quick scan, no full evaluation during dropback
        if pressure in (PressureLevel.HEAVY, PressureLevel.CRITICAL):
            # Quick hot route check without full vision/read evaluation
            for teammate in world.teammates:
                if teammate.position not in (Position.WR, Position.TE, Position.RB):
                    continue
                is_hot = bool(world.hot_routes and teammate.id in world.hot_routes)
                if is_hot:
                    # Quick separation check
                    nearest_dist = min(
                        (teammate.pos.distance_to(opp.pos) for opp in world.opponents),
                        default=10.0
                    )
                    if nearest_dist > 1.5:  # Open enough for hot route
                        return BrainDecision(
                            action="throw",
                            target_id=teammate.id,
                            action_target=teammate.pos,
                            reasoning=f"Hot route during dropback! {teammate.id} has {nearest_dist:.1f}yd sep",
                        )

        # Still in dropback phase - move toward target
        if distance_to_target > 0.5:
            return BrainDecision(
                move_target=dropback_target,
                move_type="dropback",  # Faster than backpedal - QB retreat, not DB coverage
                intent="dropback",
                reasoning=f"Executing dropback, {distance_to_target:.1f}yd to set point",
            )
        else:
            # Reached depth, but orchestrator says still planting
            # Start facing toward read 1 while planting so we're ready to scan
            facing = _get_read_target_facing(world, 1)
            return BrainDecision(
                intent="planting",
                facing_direction=facing,
                reasoning=f"At depth ({world.dropback_depth:.0f}yd), planting feet",
            )

    # First tick after becoming set - initialize read timing
    if not state.dropback_complete:
        state.dropback_complete = True
        state.set_time = world.qb_set_time
        # Set time_per_read with variance (base 0.6s, modified by awareness)
        awareness = world.me.attributes.awareness
        base_read_time = 0.6 - (awareness - 75) * 0.005  # 0.5-0.7s range
        state.time_per_read = execution_timing(base_read_time, awareness)
        # Face toward read 1 as we begin scanning
        facing = _get_read_target_facing(world, 1)
        return BrainDecision(
            intent="set",
            facing_direction=facing,
            reasoning=f"Set in pocket, beginning reads (time_per_read: {state.time_per_read:.2f}s)",
        )

    # Phase: Pocket (post-dropback)
    # NOW we evaluate receivers - not during dropback
    receivers = _evaluate_receivers(world, pressure)

    time_in_pocket = world.current_time - state.set_time
    state.time_in_pocket = time_in_pocket

    # === MINIMUM ROUTE DEVELOPMENT TIME ===
    # Routes need time to develop before throws are reasonable.
    # This creates the realistic 2.5-3s average time to throw.
    # Only critical/heavy pressure bypasses this (survival mode).
    # Balance: too long = QB holds into sacks, too short = quick throws
    MIN_ROUTE_DEVELOPMENT_TIME = 1.0  # seconds since snap
    routes_developing = world.time_since_snap < MIN_ROUTE_DEVELOPMENT_TIME

    _trace(f"[POCKET] t={world.current_time:.2f}s, pocket={time_in_pocket:.2f}s, read={state.current_read}, pressure={pressure.value}, receivers={len(receivers)}, routes_developing={routes_developing}")

    # =========================================================================
    # Critical Pressure Response
    # =========================================================================
    accuracy = world.me.attributes.throw_accuracy
    throw_power = getattr(world.me.attributes, 'throw_power', 80)
    anticipation_attr = world.me.attributes.get("anticipation", 50)  # QB anticipation attribute

    if pressure == PressureLevel.CRITICAL:
        # Platform lost - must complete quickly or move
        best, is_anticipation, find_reason = _find_best_receiver(
            receivers, state.current_read, pressure, accuracy, time_in_pocket, anticipation_attr
        )

        if best and best.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            lead_pos = _calculate_throw_lead(world.me.pos, best, throw_power)
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=lead_pos,
                reasoning=f"Quick completion to {best.player_id} ({best.separation:.1f}yd open)",
            )

        # Live to play another down
        if _should_throw_away(world):
            return BrainDecision(
                action="throw",
                action_target=_get_throw_away_target(world),
                intent="throw_away",
                reasoning="No completion available, throwing away to reset",
            )

        # Attempt completion to best available
        if best:
            lead_pos = _calculate_throw_lead(world.me.pos, best, throw_power)
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=lead_pos,
                reasoning=f"Attempting completion to {best.player_id} ({best.status.value})",
            )

        # Extend play to find completion or gain yards
        escape = _find_escape_lane(world)
        if escape:
            state.scramble_committed = True
            return BrainDecision(
                move_target=escape,
                move_type="sprint",
                intent="scramble",
                reasoning="Extending play - looking for completion or yards",
            )

        # Protect ball for next play
        return BrainDecision(
            intent="protect_ball",
            reasoning="No completion available, protecting ball",
        )

    # =========================================================================
    # Heavy Pressure Response - Platform degrading, complete quickly
    # =========================================================================
    if pressure == PressureLevel.HEAVY:
        # Platform unstable - complete to current read if open
        current_eval = next(
            (r for r in receivers if r.read_order == state.current_read), None
        )

        if current_eval and current_eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
            return BrainDecision(
                action="throw",
                target_id=current_eval.player_id,
                action_target=lead_pos,
                reasoning=f"Completing to read {state.current_read} ({current_eval.separation:.1f}yd open)",
            )

        # POISE EFFECT: Low poise QBs lock onto current read under pressure
        # They can't process going to the next read - tunnel vision
        if poise_effects["read_lock_under_pressure"]:
            # Low poise: staring down first read, force throw or bail
            _trace(f"[POISE] Low poise ({poise}) - locked onto R{state.current_read}")
            if current_eval:
                # Force throw even into coverage (bad decision)
                lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
                return BrainDecision(
                    action="throw",
                    target_id=current_eval.player_id,
                    action_target=lead_pos,
                    reasoning=f"Forced throw to R{state.current_read} (low poise, locked on)",
                )

        # Current read covered - high poise can still progress
        if poise_effects["progression_under_pressure"]:
            # High poise: can advance reads even under heavy pressure
            _trace(f"[POISE] High poise ({poise}) - continuing progression under pressure")
            state.current_read = min(state.current_read + 1, 4)
            # Don't immediately bail - let read progression continue
        else:
            # Average poise: move to maintain platform
            escape = _find_escape_lane(world)
            if escape:
                return BrainDecision(
                    move_target=escape,
                    move_type="run",
                    intent="extend_play",
                    reasoning=f"Moving to maintain platform, looking for completion",
                )

            # No movement available - accelerate reads
            state.current_read = min(state.current_read + 1, 4)

    # =========================================================================
    # Moderate Pressure Response - Platform starting to degrade
    # =========================================================================
    if pressure == PressureLevel.MODERATE:
        escape = _find_escape_lane(world)
        if escape and time_in_pocket > thresholds["normal_end"]:
            # Move to maintain clean throwing platform
            return BrainDecision(
                move_target=escape,
                move_type="run",
                intent="maintain_platform",
                reasoning="Moving to maintain throwing platform",
            )

    # =========================================================================
    # Route Development Check
    # =========================================================================
    # Routes need time to develop before throws are reasonable.
    # This prevents unrealistic quick-game throws on every play.
    # Only critical/heavy pressure bypasses this (survival mode).
    if routes_developing and pressure not in (PressureLevel.CRITICAL, PressureLevel.HEAVY):
        # Still waiting for routes to develop - scan but don't throw
        _trace(f"[POCKET] Routes still developing ({world.time_since_snap:.2f}s < {MIN_ROUTE_DEVELOPMENT_TIME}s)")
        return BrainDecision(
            intent="scanning",
            facing_direction=_get_read_target_facing(world, state.current_read),
            reasoning=f"Letting routes develop ({world.time_since_snap:.1f}s)",
        )

    # =========================================================================
    # Read Progression with Dwell Time
    # =========================================================================
    # QB goes through reads in order (mechanical reality of scanning)
    # At each read, evaluates: "If I throw NOW, will it be open when ball arrives?"
    # Dwells on each read for ~0.3-0.5s before moving on
    #
    # Dwell time varies by:
    # - Awareness (higher = faster processing)
    # - Pressure (more pressure = less time per read)
    # - How covered the receiver is (clearly covered = move on faster)

    DWELL_TIME_BASE = 0.4  # Base time per read in seconds
    DWELL_TIME_MIN = 0.15  # Minimum dwell even under pressure

    # Calculate time on current read
    time_per_read = state.time_per_read if state.time_per_read > 0 else DWELL_TIME_BASE
    time_on_current_read = time_in_pocket - ((state.current_read - 1) * time_per_read)

    # Adjust dwell time based on pressure
    if pressure == PressureLevel.HEAVY:
        effective_dwell = max(DWELL_TIME_MIN, time_per_read * 0.5)
    elif pressure == PressureLevel.MODERATE:
        effective_dwell = max(DWELL_TIME_MIN, time_per_read * 0.75)
    else:
        effective_dwell = time_per_read

    # Find current read
    current_eval = next(
        (r for r in receivers if r.read_order == state.current_read), None
    )

    if current_eval:
        sep = current_eval.separation
        status = current_eval.status
        _trace(f"[READ] R{state.current_read} ({current_eval.player_id}): {status.value} ({sep:.1f}yd) dwell={time_on_current_read:.2f}/{effective_dwell:.2f}s")

        # OPEN = throw immediately, no dwell needed
        if status == ReceiverStatus.OPEN:
            lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
            _trace(f"[READ] -> THROW to R{state.current_read} (OPEN)")
            return BrainDecision(
                action="throw",
                target_id=current_eval.player_id,
                action_target=lead_pos,
                reasoning=f"R{state.current_read} {current_eval.player_id} OPEN ({sep:.1f}yd)",
            )

        # WINDOW = throw after confirming (partial dwell)
        if status == ReceiverStatus.WINDOW:
            # Need to dwell at least half the time to confirm it's a good window
            if time_on_current_read >= effective_dwell * 0.5 and accuracy >= 75:
                lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
                _trace(f"[READ] -> THROW to R{state.current_read} (window confirmed)")
                return BrainDecision(
                    action="throw",
                    target_id=current_eval.player_id,
                    action_target=lead_pos,
                    reasoning=f"R{state.current_read} {current_eval.player_id} window ({sep:.1f}yd)",
                )
            # Still evaluating this window
            _trace(f"[READ] R{state.current_read}: evaluating window...")
            return BrainDecision(
                intent="scanning",
                facing_direction=_get_read_target_facing(world, state.current_read),
                reasoning=f"Evaluating R{state.current_read} window",
            )

        # CONTESTED = might open up, dwell full time before moving on
        if status == ReceiverStatus.CONTESTED:
            # DECISION-MAKING EFFECT: Low DM QBs may force throw into coverage
            # This is the key behavioral difference - they see "tight window" where
            # high DM QBs see "covered, check down"
            if random.random() < dm_effects["force_throw_chance"]:
                # Bad decision: force the throw anyway
                _trace(f"[DM] Low decision-making ({decision_making}) - forcing into contested!")
                lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
                return BrainDecision(
                    action="throw",
                    target_id=current_eval.player_id,
                    action_target=lead_pos,
                    reasoning=f"Forcing to R{state.current_read} (contested - bad decision)",
                )

            if time_on_current_read >= effective_dwell:
                # Dwell complete, move to next read
                if state.current_read < 4:
                    state.current_read += 1
                    _trace(f"[READ] R{state.current_read - 1} contested, advancing to R{state.current_read}")
                    return BrainDecision(
                        intent="scanning",
                        facing_direction=_get_read_target_facing(world, state.current_read),
                        reasoning=f"R{state.current_read - 1} contested, checking R{state.current_read}",
                    )
            # Still dwelling on contested read
            return BrainDecision(
                intent="scanning",
                facing_direction=_get_read_target_facing(world, state.current_read),
                reasoning=f"Dwelling on R{state.current_read} ({time_on_current_read:.2f}s)",
            )

        # COVERED = move on quickly (no point dwelling)
        if status == ReceiverStatus.COVERED:
            # DECISION-MAKING EFFECT: Really bad QBs might even throw into COVERED receivers
            # This creates interceptions and the dramatic "what was he thinking?!" moments
            if decision_making < 45 and random.random() < dm_effects["force_throw_chance"] * 0.5:
                _trace(f"[DM] Poor decision-making ({decision_making}) - throwing into coverage!")
                lead_pos = _calculate_throw_lead(world.me.pos, current_eval, throw_power)
                return BrainDecision(
                    action="throw",
                    target_id=current_eval.player_id,
                    action_target=lead_pos,
                    reasoning=f"Forcing to R{state.current_read} (covered - terrible decision)",
                )

            if state.current_read < 4:
                state.current_read += 1
                _trace(f"[READ] R{state.current_read - 1} COVERED, quick advance to R{state.current_read}")
                return BrainDecision(
                    intent="scanning",
                    facing_direction=_get_read_target_facing(world, state.current_read),
                    reasoning=f"R{state.current_read - 1} covered, moving to R{state.current_read}",
                )

    # Exhausted all reads or time expired - find best available option
    if state.current_read >= 4 or time_in_pocket > thresholds["forced"]:
        # Find the best receiver across all options
        best = max(receivers, key=lambda r: r.separation) if receivers else None

        if best and best.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
            lead_pos = _calculate_throw_lead(world.me.pos, best, throw_power)
            _trace(f"[READ] All reads checked, throwing to best: {best.player_id} ({best.separation:.1f}yd)")
            return BrainDecision(
                action="throw",
                target_id=best.player_id,
                action_target=lead_pos,
                reasoning=f"Best available: {best.player_id} ({best.separation:.1f}yd)",
            )

        # No good option - scramble or throw away
        escape = _find_escape_lane(world)
        if escape:
            state.scramble_committed = True
            _trace(f"[READ] No completion, scrambling")
            return BrainDecision(
                move_target=escape,
                move_type="sprint",
                intent="scramble",
                reasoning="No completion available - scrambling",
            )

        if _should_throw_away(world):
            return BrainDecision(
                action="throw",
                action_target=_get_throw_away_target(world),
                intent="throw_away",
                reasoning="No completion, throwing away",
            )

    # Default: continue scanning current read
    facing = _get_read_target_facing(world, state.current_read)
    return BrainDecision(
        intent="scanning",
        facing_direction=facing,
        reasoning=f"Scanning R{state.current_read} ({time_in_pocket:.1f}s)",
    )
