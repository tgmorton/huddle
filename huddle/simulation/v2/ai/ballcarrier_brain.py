"""Ballcarrier Brain - Universal brain for any player with the ball.

The ballcarrier brain controls:
- Running backs after handoff
- Wide receivers after catch
- Quarterbacks scrambling
- Defenders after interception/fumble recovery

Responsibilities: Find daylight, execute moves, maximize yards, protect ball
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from .shared.perception import calculate_effective_vision, angle_between as shared_angle_between


# =============================================================================
# Ballcarrier Enums
# =============================================================================

class Situation(str, Enum):
    """Current running situation."""
    OPEN_FIELD = "open_field"   # Space to run
    CONGESTED = "congested"     # In traffic
    CONTACT = "contact"         # Tackler imminent
    SCORING = "scoring"         # Near goal line


class MoveType(str, Enum):
    """Available evasion moves."""
    JUKE = "juke"         # Lateral direction change
    SPIN = "spin"         # 360 spin
    STIFF_ARM = "stiff_arm"
    TRUCK = "truck"       # Lower shoulder through
    HURDLE = "hurdle"     # Jump over low tackler
    SPEED_BURST = "speed_burst"
    DEAD_LEG = "dead_leg" # Subtle hesitation
    CUT = "cut"           # Sharp direction change


# =============================================================================
# Internal State
# =============================================================================

@dataclass
class BallcarrierState:
    """Tracked state for ballcarrier decision-making."""
    yards_gained: float = 0.0
    time_with_ball: float = 0.0
    last_cut_time: float = -1.0
    last_move_time: float = -1.0
    moves_used: List[str] = None
    in_contact: bool = False

    def __post_init__(self):
        if self.moves_used is None:
            self.moves_used = []


# Module-level state
_bc_states: dict[str, BallcarrierState] = {}


def _get_state(player_id: str) -> BallcarrierState:
    if player_id not in _bc_states:
        _bc_states[player_id] = BallcarrierState()
    return _bc_states[player_id]


def _reset_state(player_id: str) -> None:
    _bc_states[player_id] = BallcarrierState()


# =============================================================================
# Vision System - Core perception filtering
# =============================================================================

def _calculate_threat_pressure(world: WorldState) -> float:
    """Calculate pressure level from threat count and proximity.

    More threats and closer threats = higher pressure = narrower vision.
    Implements Easterbrook Hypothesis for ballcarriers.

    Returns:
        Float from 0.0 (open field) to 1.0 (swarmed)
    """
    my_pos = world.me.pos
    pressure_score = 0.0

    for opp in world.opponents:
        distance = opp.pos.distance_to(my_pos)

        if distance > 15.0:
            continue

        # Closer threats contribute more to pressure
        if distance < 3.0:
            pressure_score += 0.4  # Imminent threat
        elif distance < 6.0:
            pressure_score += 0.2  # Close threat
        elif distance < 10.0:
            pressure_score += 0.1  # Nearby
        else:
            pressure_score += 0.05

        # Closing speed increases pressure
        if opp.velocity.length() > 0:
            to_bc = (my_pos - opp.pos).normalized()
            closing = opp.velocity.dot(to_bc)
            if closing > 2.0:  # Coming fast
                pressure_score += 0.1

    # Cap at 1.0
    return min(1.0, pressure_score)


def _get_vision_params(vision: int) -> tuple[float, bool, bool, bool]:
    """Get vision parameters based on attribute.

    Returns:
        (perception_radius, can_see_backside, can_see_second_level, can_see_cutback)

    From design doc:
        90+: Full field, all defenders, pursuit angles
        80-89: 15 yards, 2nd level, predict pursuit
        70-79: 10 yards, immediate threats, primary hole
        60-69: 7 yards, 2-3 nearest defenders
        <60: 5 yards, tunnel vision, react only
    """
    if vision >= 90:
        return 30.0, True, True, True
    elif vision >= 80:
        return 15.0, True, True, True
    elif vision >= 70:
        return 10.0, False, True, False
    elif vision >= 60:
        return 7.0, False, False, False
    else:
        return 5.0, False, False, False


def _angle_between(v1: Vec2, v2: Vec2) -> float:
    """Calculate angle between two vectors in degrees."""
    import math
    if v1.length() < 0.01 or v2.length() < 0.01:
        return 0.0
    dot = v1.normalized().dot(v2.normalized())
    dot = max(-1.0, min(1.0, dot))  # Clamp for numerical stability
    return math.degrees(math.acos(dot))


def _filter_threats_by_vision(
    world: WorldState,
    threats: List["Threat"],
) -> List["Threat"]:
    """Filter threats based on ballcarrier's vision attribute AND pressure.

    Implements Easterbrook Hypothesis: Under pressure, peripheral perception
    degrades. Ballcarriers with more closing threats see less of the field.

    Low-vision backs miss:
    - Backside pursuit (can't see defender coming from behind)
    - Second-level defenders until too late
    - Cutback lanes (focused on primary hole)

    Under pressure, even high-vision backs experience:
    - Narrowed vision cone
    - Reduced perception radius
    - Degraded peripheral detection
    """
    vision = world.me.attributes.vision
    _, can_see_backside, can_see_second_level, _ = _get_vision_params(vision)

    # Calculate pressure and apply to vision
    pressure = _calculate_threat_pressure(world)
    vision_params = calculate_effective_vision(vision, pressure)

    my_pos = world.me.pos
    my_facing = world.me.velocity.normalized() if world.me.velocity.length() > 0.1 else Vec2(0, 1)

    perceived = []

    for threat in threats:
        to_threat = threat.player.pos - my_pos
        distance = to_threat.length()

        # Skip if beyond effective perception radius (pressure-modified)
        if distance > vision_params.radius:
            continue

        angle = _angle_between(my_facing, to_threat)

        # Skip if outside vision cone (pressure narrows the cone)
        # BUT always allow very close threats regardless of angle (instinctive awareness)
        if angle > vision_params.angle / 2 and distance > 2.0:
            continue

        # Forward cone (0-45 degrees) - always visible within radius
        if angle < 45:
            perceived.append(threat)
            continue

        # Peripheral vision - quality degrades with pressure
        # Use peripheral_quality as a distance modifier
        peripheral_range = vision_params.radius * vision_params.peripheral_quality

        if angle < 90:
            # 45-90 degrees - peripheral range
            if distance < peripheral_range * 0.8:
                perceived.append(threat)
            continue

        if angle < 135:
            # 90-135 degrees - side vision, further reduced
            if distance < peripheral_range * 0.5:
                perceived.append(threat)
            continue

        # Behind (135-180 degrees) - requires high vision AND low pressure
        if can_see_backside and pressure < 0.5 and distance < 5.0:
            perceived.append(threat)
        elif distance < 2.0:  # Anyone can sense very close threats
            perceived.append(threat)

    # Second-level filtering (defenders beyond LOS)
    if not can_see_second_level:
        # Can only see closest 3 defenders
        perceived = perceived[:3]

    return perceived


# =============================================================================
# Helper Functions
# =============================================================================

@dataclass
class Threat:
    """A defensive threat to the ballcarrier."""
    player: PlayerView
    distance: float
    eta: float  # Estimated time to contact
    approach_angle: float  # Angle of approach
    can_intercept: bool


def _analyze_threats(world: WorldState) -> List[Threat]:
    """Analyze all defensive threats."""
    threats = []
    my_pos = world.me.pos
    my_vel = world.me.velocity

    for opp in world.opponents:
        dist = opp.pos.distance_to(my_pos)

        # Skip far away defenders
        if dist > 20.0:
            continue

        # Calculate intercept
        opp_speed = max(opp.speed, 5.0)  # Minimum assumed speed
        eta = dist / opp_speed

        # Approach angle
        to_me = (my_pos - opp.pos).normalized()
        approach_angle = 0.0
        if opp.velocity.length() > 0.1:
            approach_angle = abs(to_me.dot(opp.velocity.normalized()))

        # Can they intercept?
        # Simple: if they're fast enough to reach our projected position
        can_intercept = True
        if my_vel.length() > 0:
            future_pos = my_pos + my_vel * eta
            intercept_dist = opp.pos.distance_to(future_pos)
            can_intercept = intercept_dist < dist + eta * opp_speed * 0.5

        threats.append(Threat(
            player=opp,
            distance=dist,
            eta=eta,
            approach_angle=approach_angle,
            can_intercept=can_intercept,
        ))

    # Sort by distance
    threats.sort(key=lambda t: t.distance)
    return threats


@dataclass
class Hole:
    """A potential running lane."""
    position: Vec2
    width: float
    quality: float  # 0-1 score
    direction: Vec2
    threats_beyond: int


def _find_holes(world: WorldState, threats: List[Threat]) -> List[Hole]:
    """Find running lanes/holes.

    Team-aware: Offense runs toward positive Y, Defense (INT/fumble return)
    runs toward negative Y.

    Sideline-aware: Penalizes holes near sidelines to avoid running out of bounds.
    """
    my_pos = world.me.pos
    holes = []

    # Determine goal direction based on team
    # Offense runs toward positive Y (opponent's end zone)
    # Defense on return runs toward negative Y (opponent's end zone from their perspective)
    if world.me.team == Team.DEFENSE:
        y_dir = -1  # Return direction
    else:
        y_dir = 1   # Offensive direction

    # Sample directions (flipped based on team)
    directions = [
        Vec2(0, y_dir),                          # Straight ahead
        Vec2(0.5, y_dir).normalized(),           # Slight right
        Vec2(-0.5, y_dir).normalized(),          # Slight left
        Vec2(1, 0.5 * y_dir).normalized(),       # Hard right
        Vec2(-1, 0.5 * y_dir).normalized(),      # Hard left
    ]

    # Field boundaries (field is 53.3 yards wide, centered at x=0)
    field_half_width = 26.65

    for dir in directions:
        # Check 5 yards ahead in this direction
        check_pos = my_pos + dir * 5

        # Find minimum clearance
        min_dist = float('inf')
        for threat in threats:
            dist = threat.player.pos.distance_to(check_pos)
            if dist < min_dist:
                min_dist = dist

        if min_dist > 1.5:  # Minimum hole width
            # Count threats beyond (relative to goal direction)
            if y_dir > 0:
                beyond = sum(1 for t in threats if t.player.pos.y > check_pos.y)
            else:
                beyond = sum(1 for t in threats if t.player.pos.y < check_pos.y)

            quality = min(1.0, min_dist / 5.0) * (1.0 - beyond * 0.2)

            # Sideline penalty - penalize holes near boundaries
            distance_to_sideline = min(
                check_pos.x + field_half_width,   # Distance to left sideline
                field_half_width - check_pos.x    # Distance to right sideline
            )
            if distance_to_sideline < 5:
                # Heavy penalty near sideline - risk of running out of bounds
                sideline_penalty = distance_to_sideline / 5.0  # 0.0 at sideline, 1.0 at 5 yards
                quality *= sideline_penalty

            holes.append(Hole(
                position=check_pos,
                width=min_dist,
                quality=quality,
                direction=dir,
                threats_beyond=beyond,
            ))

    holes.sort(key=lambda h: h.quality, reverse=True)
    return holes


def _select_move(
    world: WorldState,
    threat: Threat,
    state: BallcarrierState,
) -> Optional[Tuple[MoveType, str]]:
    """Select the best move for the situation.

    Returns:
        (move_type, reasoning) or None if no move appropriate
    """
    attrs = world.me.attributes
    current_time = world.current_time

    # Cooldowns
    move_cooldown = 0.5
    if state.last_move_time > 0 and current_time - state.last_move_time < move_cooldown:
        return None

    # Speed burst - if we have speed advantage
    speed_diff = attrs.speed - 75  # Assume average defender
    if speed_diff >= 3 and threat.distance > 2.0:
        return MoveType.SPEED_BURST, f"Speed advantage (+{speed_diff}), bursting past"

    # Hurdle - if defender is low
    if attrs.agility >= 85 and threat.distance < 2.0:
        # Would need info about defender's height/dive, simplified check
        pass

    # Stiff arm - if defender reaching from side
    if attrs.strength >= 75 and threat.distance < 2.0:
        if threat.approach_angle < 0.5:  # Not head-on
            return MoveType.STIFF_ARM, "Defender reaching, extending stiff arm"

    # Juke - if lateral space
    if attrs.agility >= 70 and threat.distance < 3.0:
        return MoveType.JUKE, f"Defender at {threat.distance:.1f}yd, juking"

    # Spin - if defender committed
    if attrs.agility >= 80 and threat.distance < 2.0:
        if threat.approach_angle > 0.7:  # Coming fast and straight
            return MoveType.SPIN, "Defender committed, spinning"

    # Truck - if smaller defender or no other option
    if attrs.strength >= 80 and threat.distance < 1.5:
        return MoveType.TRUCK, "Lowering shoulder through contact"

    # Dead leg - subtle move
    if attrs.agility >= 70 and threat.distance < 3.0:
        return MoveType.DEAD_LEG, "Subtle hesitation move"

    return None


def _find_blocker_to_follow(world: WorldState) -> Optional[PlayerView]:
    """Find a lead blocker to follow."""
    my_pos = world.me.pos

    for tm in world.teammates:
        # Look for blockers ahead
        if tm.pos.y > my_pos.y and tm.pos.y < my_pos.y + 5:
            dist = tm.pos.distance_to(my_pos)
            if dist < 4.0:
                return tm

    return None


def _get_situation(threats: List[Threat], holes: List[Hole]) -> Situation:
    """Determine current running situation."""
    if not threats or threats[0].distance > 7:
        return Situation.OPEN_FIELD

    if threats[0].distance < 2.0:
        return Situation.CONTACT

    if not holes or holes[0].quality < 0.3:
        return Situation.CONGESTED

    return Situation.OPEN_FIELD


# =============================================================================
# Main Brain Function
# =============================================================================

def ballcarrier_brain(world: WorldState) -> BrainDecision:
    """Ballcarrier brain - controls any player with the ball.

    Args:
        world: Complete world state

    Returns:
        BrainDecision with action and reasoning
    """
    state = _get_state(world.me.id)

    # Verify we have the ball
    if not world.me.has_ball:
        return BrainDecision.hold("Don't have ball (shouldn't be in ballcarrier brain)")

    # Update state
    state.time_with_ball = world.time_since_snap
    state.yards_gained = world.me.pos.y - world.los_y

    # Analyze situation - filter by vision
    all_threats = _analyze_threats(world)
    perceived_threats = _filter_threats_by_vision(world, all_threats)

    # Find holes using only perceived threats
    holes = _find_holes(world, perceived_threats)

    # Can we see cutback lanes? (vision-dependent)
    vision = world.me.attributes.vision
    _, _, _, can_see_cutback = _get_vision_params(vision)
    if not can_see_cutback:
        # Low vision backs focus on primary hole, filter cutback options
        holes = [h for h in holes if h.direction.x * world.me.velocity.x >= 0] or holes

    situation = _get_situation(perceived_threats, holes)

    # =========================================================================
    # Ball Security Check - Protect ball in high-risk situations
    # =========================================================================
    multiple_close_tacklers = len([t for t in perceived_threats if t.distance < 2.5]) >= 2
    if multiple_close_tacklers:
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 2),
            move_type="run",
            action="protect_ball",
            intent="ball_security",
            reasoning="Multiple tacklers converging, protecting ball",
        )

    # =========================================================================
    # Scoring Position (within 5 yards of goal)
    # =========================================================================
    goal_line_y = world.los_y + 100  # Use relative to LOS, not hardcoded
    dist_to_goal = goal_line_y - world.me.pos.y

    if dist_to_goal < 5:
        # Near goal line
        if not perceived_threats or perceived_threats[0].distance > 3:
            # Clear path
            return BrainDecision(
                move_target=Vec2(world.me.pos.x, goal_line_y),
                move_type="sprint",
                intent="score",
                reasoning="Clear path to end zone, sprinting!",
            )

        # Fight for it
        return BrainDecision(
            move_target=Vec2(world.me.pos.x, goal_line_y),
            move_type="sprint",
            intent="score",
            action="dive" if dist_to_goal < 2 else None,
            reasoning="Fighting for the goal line",
        )

    # =========================================================================
    # Contact Imminent
    # =========================================================================
    if situation == Situation.CONTACT and perceived_threats:
        nearest_threat = perceived_threats[0]

        # Try to make a move
        move_result = _select_move(world, nearest_threat, state)

        if move_result:
            move_type, reasoning = move_result
            state.last_move_time = world.current_time
            state.moves_used.append(move_type.value)

            # Calculate move direction
            if move_type == MoveType.JUKE:
                # Juke opposite of defender approach
                threat_dir = (world.me.pos - nearest_threat.player.pos).normalized()
                juke_dir = Vec2(-threat_dir.y, threat_dir.x)  # Perpendicular
                move_target = world.me.pos + juke_dir * 2
            elif move_type == MoveType.SPIN:
                # Spin away from defender
                move_target = world.me.pos + Vec2(0, 2)  # Continue upfield after spin
            else:
                move_target = world.me.pos + Vec2(0, 3)

            return BrainDecision(
                move_target=move_target,
                move_type="sprint",
                action=move_type.value,
                target_id=nearest_threat.player.id,
                intent="evasion",
                reasoning=reasoning,
            )

        # No move available - brace for contact
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 2),
            move_type="run",
            intent="lower_pad",
            reasoning="Contact imminent, lowering pad level",
        )

    # =========================================================================
    # Open Field Running
    # =========================================================================
    if situation == Situation.OPEN_FIELD:
        # Find best lane
        if holes:
            best_hole = holes[0]
            return BrainDecision(
                move_target=best_hole.position,
                move_type="sprint",
                intent="open_field",
                reasoning=f"Open field! Taking lane with {best_hole.width:.1f}yd clearance",
            )

        # Just run north
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 10),
            move_type="sprint",
            intent="north_south",
            reasoning="Open field, running north",
        )

    # =========================================================================
    # Congested Running
    # =========================================================================
    if situation == Situation.CONGESTED:
        # Try to find or create a hole
        if holes and holes[0].quality > 0.4:
            best_hole = holes[0]

            # Is the hole closing?
            closing = False
            for threat in perceived_threats:
                if threat.player.pos.distance_to(best_hole.position) < 3:
                    closing = True
                    break

            if closing:
                return BrainDecision(
                    move_target=best_hole.position,
                    move_type="sprint",
                    intent="hit_hole",
                    reasoning=f"Hole closing, hitting it NOW",
                )

            return BrainDecision(
                move_target=best_hole.position,
                move_type="run",
                intent="find_hole",
                reasoning=f"Traffic ahead, working toward {best_hole.width:.1f}yd hole",
            )

        # Check for cutback
        cutback_holes = [h for h in holes if h.direction.x * world.me.velocity.x < 0]
        if cutback_holes and cutback_holes[0].quality > 0.5:
            return BrainDecision(
                move_target=cutback_holes[0].position,
                move_type="sprint",
                action="cut",
                intent="cutback",
                reasoning="Cutback lane open!",
            )

        # No lanes - go north-south and churn
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, 2),
            move_type="run",
            intent="churn",
            reasoning="No lanes, churning for yards",
        )

    # =========================================================================
    # Follow Blocker
    # =========================================================================
    blocker = _find_blocker_to_follow(world)
    if blocker:
        # Position behind blocker
        follow_pos = blocker.pos - Vec2(0, 2)

        return BrainDecision(
            move_target=follow_pos,
            move_type="run",
            intent="follow_block",
            reasoning=f"Following blocker {blocker.id}",
        )

    # Default: run upfield
    return BrainDecision(
        move_target=world.me.pos + Vec2(0, 5),
        move_type="sprint",
        intent="north_south",
        reasoning="Running north-south",
    )
