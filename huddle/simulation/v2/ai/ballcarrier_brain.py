"""Ballcarrier Brain - Universal brain for any player with the ball.

YARDS-FIRST PHILOSOPHY:
The primary goal is GAINING YARDS toward the endzone. Defenders are
obstacles between us and our target - we go around, through, or away
from them. Every decision is "what gets me more yards" not "how do I
beat this defender".

The ballcarrier brain controls:
- Running backs after handoff
- Wide receivers after catch
- Quarterbacks scrambling
- Defenders after interception/fumble recovery

Key insight: We don't "beat defenders" - we ADVANCE THE BALL.
Moves and evasions are tools to gain MORE YARDS, not to win 1v1s.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from ..orchestrator import WorldState, BrainDecision, PlayerView, PlayPhase
from ..core.contexts import BallcarrierContextBase
from ..core.vec2 import Vec2
from ..core.entities import Position, Team
from ..core.trace import get_trace_system, TraceCategory
from .shared.perception import calculate_effective_vision, angle_between as shared_angle_between


# =============================================================================
# Trace Helper
# =============================================================================

def _trace(world: WorldState, msg: str, category: TraceCategory = TraceCategory.DECISION):
    """Add a trace for this ballcarrier."""
    trace = get_trace_system()
    trace.trace(world.me.id, world.me.name, category, msg)


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
    # Yards-first tracking
    target_endzone_y: float = 100.0  # Where we're trying to get to
    current_lane: Optional[Vec2] = None  # Current lane we're running through
    # Commitment tracking to prevent oscillation
    committed_direction: Optional[Vec2] = None  # Direction we're committed to
    commitment_time: float = 0.0  # When we committed

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


# =============================================================================
# Yards-First Target Calculation
# =============================================================================

def _calculate_yards_target(world: WorldState, state: BallcarrierState) -> Vec2:
    """Calculate our primary target - always the endzone direction.

    The ballcarrier's target is ALWAYS about gaining yards toward the endzone.
    Everything else (holes, moves, cuts) is about how to GET THERE.

    Returns:
        Target position toward the endzone
    """
    my_pos = world.me.pos

    # Determine goal direction based on team
    if world.me.team == Team.DEFENSE:
        # Defense on return runs toward negative Y
        endzone_y = world.los_y - 100  # Opponent's endzone
        y_dir = -1
    else:
        # Offense runs toward positive Y
        endzone_y = world.los_y + 100
        y_dir = 1

    state.target_endzone_y = endzone_y

    # Target is 10 yards ahead in endzone direction (intermediate goal)
    return Vec2(my_pos.x, my_pos.y + y_dir * 10)


def _find_best_path_to_target(
    world: WorldState,
    target: Vec2,
    obstacles: List["Threat"],
) -> tuple[Vec2, float, str]:
    """Find the best path toward our yards target, treating defenders as obstacles.

    This is NOT about "which defender to beat" - it's about "what path gains
    the most yards toward the endzone".

    Returns:
        (path_direction, clearance, reasoning)
    """
    my_pos = world.me.pos

    # Direction to our yards target
    to_target = (target - my_pos).normalized()
    y_dir = 1 if to_target.y > 0 else -1

    # Field boundaries
    field_half_width = 26.65

    # Sample paths toward target - all prioritize forward progress
    paths = [
        (Vec2(0, y_dir), "straight"),                      # Straight to endzone
        (Vec2(0.25, y_dir).normalized(), "slight_right"),  # Slight angle right
        (Vec2(-0.25, y_dir).normalized(), "slight_left"),  # Slight angle left
        (Vec2(0.5, y_dir).normalized(), "angle_right"),    # Moderate right
        (Vec2(-0.5, y_dir).normalized(), "angle_left"),    # Moderate left
        (Vec2(0.75, y_dir * 0.5).normalized(), "bounce_right"),  # Bounce outside right
        (Vec2(-0.75, y_dir * 0.5).normalized(), "bounce_left"),  # Bounce outside left
    ]

    best_path = None
    best_score = -float('inf')
    best_reasoning = "north_south"

    for direction, name in paths:
        # Check 5 yards ahead on this path
        check_pos = my_pos + direction * 5

        # Skip if out of bounds
        if abs(check_pos.x) > field_half_width - 2:
            continue

        # Calculate clearance from obstacles (defenders)
        min_clearance = float('inf')
        for obstacle in obstacles:
            dist = obstacle.player.pos.distance_to(check_pos)
            # Also consider path intersection - is defender in the way?
            path_dist = _point_to_line_distance(obstacle.player.pos, my_pos, check_pos)
            effective_dist = min(dist, path_dist + 1)  # +1 for some tolerance
            min_clearance = min(min_clearance, effective_dist)

        # Score the path: prioritize forward progress + clearance
        # Forward component (how much Y progress)
        forward_progress = direction.y * y_dir  # 1.0 for straight, less for angled

        # Clearance component (how open is the path)
        clearance_score = min(1.0, min_clearance / 5.0)

        # Sideline penalty
        sideline_dist = min(check_pos.x + field_half_width, field_half_width - check_pos.x)
        sideline_factor = min(1.0, sideline_dist / 8.0)

        # Total score: 50% forward progress, 40% clearance, 10% sideline
        score = forward_progress * 0.5 + clearance_score * 0.4 + sideline_factor * 0.1

        if score > best_score:
            best_score = score
            best_path = direction
            best_reasoning = name

    if best_path is None:
        best_path = Vec2(0, y_dir)
        best_reasoning = "north_south"

    # Calculate actual clearance for the chosen path
    check_pos = my_pos + best_path * 5
    clearance = float('inf')
    for obstacle in obstacles:
        dist = obstacle.player.pos.distance_to(check_pos)
        clearance = min(clearance, dist)

    return best_path, clearance, best_reasoning


def _point_to_line_distance(point: Vec2, line_start: Vec2, line_end: Vec2) -> float:
    """Calculate perpendicular distance from point to line segment."""
    line_vec = line_end - line_start
    line_len = line_vec.length()
    if line_len < 0.01:
        return point.distance_to(line_start)

    # Project point onto line
    t = max(0, min(1, (point - line_start).dot(line_vec) / (line_len * line_len)))
    projection = line_start + line_vec * t
    return point.distance_to(projection)


@dataclass
class Hole:
    """A potential running lane toward the endzone."""
    position: Vec2
    width: float
    quality: float  # 0-1 score - how good is this path for gaining yards
    direction: Vec2
    threats_beyond: int


def _find_holes(world: WorldState, threats: List[Threat]) -> List[Hole]:
    """Find running lanes/holes.

    Team-aware: Offense runs toward positive Y, Defense (INT/fumble return)
    runs toward negative Y.

    Sideline-aware: Penalizes holes near sidelines to avoid running out of bounds.

    Run-concept-aware: Prioritizes the designed hole direction if available.
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

    # Determine designed hole bias from run concept
    # Gap names: a_right, b_right, c_right, a_left, b_left, c_left
    # Use safe attribute access since ballcarrier could be any position (WR, RB, QB, etc.)
    designed_x_bias = 0.0
    run_aiming_point = getattr(world, "run_aiming_point", None)
    run_play_side = getattr(world, "run_play_side", None)
    if world.is_run_play and run_aiming_point:
        if "right" in run_aiming_point:
            designed_x_bias = 1.0  # Prefer right side
        elif "left" in run_aiming_point:
            designed_x_bias = -1.0  # Prefer left side
    elif world.is_run_play and run_play_side:
        if run_play_side == "right":
            designed_x_bias = 1.0
        elif run_play_side == "left":
            designed_x_bias = -1.0

    # Sample directions (flipped based on team)
    # Keep directions mostly north-south to avoid running sideways
    directions = [
        Vec2(0, y_dir),                          # Straight ahead
        Vec2(0.3, y_dir).normalized(),           # Slight right
        Vec2(-0.3, y_dir).normalized(),          # Slight left
        Vec2(0.6, y_dir).normalized(),           # Moderate right
        Vec2(-0.6, y_dir).normalized(),          # Moderate left
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

            # Designed hole bonus - boost quality for holes in the designed direction
            if designed_x_bias != 0.0:
                # Calculate alignment with designed direction
                # dir.x ranges from -1 to 1, designed_x_bias is -1 or 1
                alignment = dir.x * designed_x_bias  # Positive if same direction
                # Give up to 50% bonus for perfect alignment with designed hole
                design_bonus = max(0, alignment * 0.5)
                quality *= (1.0 + design_bonus)

            # Sideline penalty - penalize holes near boundaries
            distance_to_sideline = min(
                check_pos.x + field_half_width,   # Distance to left sideline
                field_half_width - check_pos.x    # Distance to right sideline
            )
            if distance_to_sideline < 8:
                # Heavy penalty near sideline - risk of running out of bounds
                # More aggressive: 0.0 at sideline, ramps up to 1.0 at 8 yards
                sideline_penalty = (distance_to_sideline / 8.0) ** 2  # Quadratic for stronger penalty
                quality *= sideline_penalty

            # Skip holes that would take us out of bounds
            if distance_to_sideline < 1:
                continue

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
    obstacle: Threat,
    state: BallcarrierState,
    best_path: Vec2,
) -> Optional[Tuple[MoveType, str]]:
    """Select a move to gain MORE YARDS - not to "beat" the defender.

    YARDS-FIRST: The question is not "how do I beat this guy" but
    "which move lets me advance the ball further".

    Returns:
        (move_type, reasoning) or None if no move needed
    """
    attrs = world.me.attributes
    current_time = world.current_time
    my_pos = world.me.pos

    # Cooldowns
    move_cooldown = 0.5
    if state.last_move_time > 0 and current_time - state.last_move_time < move_cooldown:
        return None

    # Is the obstacle actually in our path to the endzone?
    path_blocked = _point_to_line_distance(
        obstacle.player.pos, my_pos, my_pos + best_path * 5
    ) < 2.0

    if not path_blocked:
        # Obstacle not in our path - no move needed, just keep going
        return None

    # Speed burst - can we just outrun them to gain more yards?
    speed_diff = attrs.speed - 75
    if speed_diff >= 3 and obstacle.distance > 2.0:
        return MoveType.SPEED_BURST, f"Open space ahead - bursting for extra yards"

    # Juke/cut - can we angle around them to keep advancing?
    if attrs.agility >= 70 and obstacle.distance < 3.0:
        # Determine which direction gains more yards
        left_clear = True
        right_clear = True
        for opp in world.opponents:
            if opp.pos.x < my_pos.x and opp.pos.distance_to(my_pos) < 4:
                left_clear = False
            if opp.pos.x > my_pos.x and opp.pos.distance_to(my_pos) < 4:
                right_clear = False

        if left_clear or right_clear:
            direction = "left" if left_clear else "right"
            return MoveType.JUKE, f"Obstacle at {obstacle.distance:.1f}yd - cutting {direction} for yards"

    # Spin - can we spin past to continue forward?
    if attrs.agility >= 80 and obstacle.distance < 2.0:
        if obstacle.approach_angle > 0.7:  # Obstacle coming straight
            return MoveType.SPIN, "Spinning past obstacle to continue forward"

    # Stiff arm - can we fend off while maintaining forward progress?
    if attrs.strength >= 75 and obstacle.distance < 2.0:
        if obstacle.approach_angle < 0.5:  # Coming from angle
            return MoveType.STIFF_ARM, "Extending arm to maintain forward progress"

    # Truck - plow through to gain yards (contact as last resort)
    if attrs.strength >= 80 and obstacle.distance < 1.5:
        return MoveType.TRUCK, "Lowering shoulder for extra yards through contact"

    # Dead leg - subtle move to maintain yards
    if attrs.agility >= 70 and obstacle.distance < 3.0:
        return MoveType.DEAD_LEG, "Hesitation to slip past for more yards"

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

def ballcarrier_brain(world: BallcarrierContextBase) -> BrainDecision:
    """Ballcarrier brain - YARDS-FIRST approach.

    Every decision is about GAINING YARDS toward the endzone.
    Defenders are obstacles - we go around, through, or away from them.

    Args:
        world: Context for ballcarrier (any subclass of BallcarrierContextBase)

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

    # =========================================================================
    # STEP 1: Calculate our yards target (ALWAYS the endzone)
    # =========================================================================
    yards_target = _calculate_yards_target(world, state)
    y_dir = 1 if world.me.team != Team.DEFENSE else -1

    # =========================================================================
    # PATIENCE PHASE - Trust the blocking to create yards opportunities
    # =========================================================================
    vision = world.me.attributes.vision
    patience_time = 0.5 - (vision - 70) * 0.005
    patience_time = max(0.25, min(0.55, patience_time))

    time_since_handoff = world.time_since_snap
    in_backfield = world.me.pos.y < world.los_y

    if in_backfield and time_since_handoff < patience_time:
        # Trust blocking scheme - follow designed path toward yards
        designed_target = None
        if hasattr(world, 'run_aiming_point') and world.run_aiming_point:
            aiming = world.run_aiming_point
            gap_x = 0.0
            if "a" in aiming:
                gap_x = 1.0
            elif "b" in aiming:
                gap_x = 3.0
            elif "c" in aiming:
                gap_x = 5.0
            if "left" in aiming:
                gap_x = -gap_x
            designed_target = Vec2(gap_x, world.los_y + 2)
        elif hasattr(world, 'run_play_side') and world.run_play_side:
            gap_x = 3.0 if world.run_play_side == "right" else -3.0
            designed_target = Vec2(gap_x, world.los_y + 2)

        if designed_target:
            blocker = _find_blocker_to_follow(world)
            if blocker:
                follow_pos = blocker.pos + Vec2(0, -1.5)
                return BrainDecision(
                    move_target=follow_pos,
                    move_type="run",
                    intent="patience",
                    reasoning=f"Following blocker toward designed lane",
                )
            return BrainDecision(
                move_target=designed_target,
                move_type="run",
                intent="patience",
                reasoning=f"Pressing toward designed lane",
            )

    # =========================================================================
    # STEP 2: Identify obstacles (defenders) between us and yards
    # =========================================================================
    all_obstacles = _analyze_threats(world)
    perceived_obstacles = _filter_threats_by_vision(world, all_obstacles)

    # =========================================================================
    # STEP 3: Find best path to gain yards (treating defenders as obstacles)
    # =========================================================================
    best_path, clearance, path_type = _find_best_path_to_target(
        world, yards_target, perceived_obstacles
    )

    # Also find holes for compatibility with existing logic
    holes = _find_holes(world, perceived_obstacles)

    # Determine situation based on path clearance
    if clearance > 7:
        situation = Situation.OPEN_FIELD
    elif clearance < 2:
        situation = Situation.CONTACT
    elif clearance < 4:
        situation = Situation.CONGESTED
    else:
        situation = Situation.OPEN_FIELD

    # =========================================================================
    # Ball Security - Multiple obstacles converging limits yards potential
    # =========================================================================
    close_obstacles = [o for o in perceived_obstacles if o.distance < 2.5]
    if len(close_obstacles) >= 2:
        # Protect ball while still pressing forward
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, y_dir * 2),
            move_type="run",
            action="protect_ball",
            intent="ball_security",
            reasoning="Multiple obstacles converging - securing ball while gaining what I can",
        )

    # =========================================================================
    # Scoring Position - Maximum yards available
    # =========================================================================
    dist_to_endzone = abs(state.target_endzone_y - world.me.pos.y)

    if dist_to_endzone < 5:
        endzone_pos = Vec2(world.me.pos.x, state.target_endzone_y)
        if not perceived_obstacles or perceived_obstacles[0].distance > 3:
            return BrainDecision(
                move_target=endzone_pos,
                move_type="sprint",
                intent="score",
                reasoning="Clear path to endzone - maximum yards!",
            )
        return BrainDecision(
            move_target=endzone_pos,
            move_type="sprint",
            intent="score",
            action="dive" if dist_to_endzone < 2 else None,
            reasoning="Fighting for endzone yards!",
        )

    # =========================================================================
    # Obstacle in path - use move to GAIN MORE YARDS
    # =========================================================================
    if situation == Situation.CONTACT and perceived_obstacles:
        nearest_obstacle = perceived_obstacles[0]

        # Select move based on what gains MORE YARDS (not what beats defender)
        move_result = _select_move(world, nearest_obstacle, state, best_path)

        if move_result:
            move_type, reasoning = move_result
            state.last_move_time = world.current_time
            state.moves_used.append(move_type.value)

            # Calculate move target - always prioritizing forward progress
            if move_type == MoveType.JUKE:
                # Juke to the clearer side while maintaining forward progress
                obstacle_side = 1 if nearest_obstacle.player.pos.x > world.me.pos.x else -1
                juke_dir = Vec2(-obstacle_side * 0.7, y_dir * 0.7).normalized()
                move_target = world.me.pos + juke_dir * 3
            elif move_type == MoveType.SPIN:
                # Spin and continue forward
                move_target = world.me.pos + Vec2(0, y_dir * 3)
            else:
                # Continue toward yards target
                move_target = world.me.pos + best_path * 3

            return BrainDecision(
                move_target=move_target,
                move_type="sprint",
                action=move_type.value,
                intent="yards_move",
                reasoning=reasoning,
            )

        # No move - lower pad and fight for yards
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, y_dir * 2),
            move_type="run",
            intent="fight_forward",
            reasoning="Obstacle ahead - fighting forward for yards",
        )

    # =========================================================================
    # Open field - Sprint toward yards target
    # =========================================================================
    if situation == Situation.OPEN_FIELD:
        commitment_duration = 0.5

        # Initialize commitment toward yards
        if state.committed_direction is None:
            state.committed_direction = best_path
            state.commitment_time = world.current_time

        time_since_commit = world.current_time - state.commitment_time

        if time_since_commit < commitment_duration:
            # Stay committed to current path toward yards
            committed_target = world.me.pos + state.committed_direction * 7
            path_blocked = any(
                o.distance < 2.5 and o.player.pos.distance_to(committed_target) < 3
                for o in perceived_obstacles
            )

            if not path_blocked:
                return BrainDecision(
                    move_target=committed_target,
                    move_type="sprint",
                    intent="yards_sprint",
                    reasoning=f"Open field - sprinting for yards ({clearance:.1f}yd clearance)",
                )

        # Update path to best yards opportunity
        state.committed_direction = best_path
        state.commitment_time = world.current_time

        sprint_target = world.me.pos + best_path * 7
        return BrainDecision(
            move_target=sprint_target,
            move_type="sprint",
            intent="yards_sprint",
            reasoning=f"Taking best path toward endzone ({path_type})",
        )

    # =========================================================================
    # Congested - Work through traffic for yards
    # =========================================================================
    if situation == Situation.CONGESTED:
        commitment_duration = 0.5

        if state.committed_direction is None and world.is_run_play:
            run_aiming = getattr(world, "run_aiming_point", None)
            if run_aiming:
                design_x = 1.0 if "right" in run_aiming else -1.0 if "left" in run_aiming else 0.0
                state.committed_direction = Vec2(design_x * 0.4, y_dir * 0.9).normalized()
            else:
                state.committed_direction = best_path
            state.commitment_time = world.current_time

        time_since_commit = world.current_time - state.commitment_time

        if state.committed_direction and time_since_commit < commitment_duration:
            press_target = world.me.pos + state.committed_direction * 3
            return BrainDecision(
                move_target=press_target,
                move_type="run",
                intent="press_yards",
                reasoning=f"Pressing through traffic for yards",
            )

        # Check for cutback - more open path to yards
        _, _, _, can_see_cutback = _get_vision_params(vision)
        if can_see_cutback and holes:
            cutback_holes = [h for h in holes if h.direction.x * world.me.velocity.x < 0]
            if cutback_holes and cutback_holes[0].quality > 0.5:
                state.committed_direction = cutback_holes[0].direction
                state.commitment_time = world.current_time
                return BrainDecision(
                    move_target=cutback_holes[0].position,
                    move_type="sprint",
                    action="cut",
                    intent="cutback_yards",
                    reasoning="Cutback open - better path to yards!",
                )

        # Find best path through traffic
        if holes and holes[0].quality > 0.3:
            best_hole = holes[0]
            return BrainDecision(
                move_target=best_hole.position,
                move_type="run",
                intent="work_yards",
                reasoning=f"Working toward {best_hole.width:.1f}yd opening for yards",
            )

        # Churn forward for whatever yards available
        return BrainDecision(
            move_target=world.me.pos + Vec2(0, y_dir * 2),
            move_type="run",
            intent="churn_yards",
            reasoning="Churning forward for yards",
        )

    # =========================================================================
    # Follow blocker - They're creating yards opportunities
    # =========================================================================
    blocker = _find_blocker_to_follow(world)
    if blocker:
        follow_pos = blocker.pos + Vec2(0, -y_dir * 2)
        return BrainDecision(
            move_target=follow_pos,
            move_type="run",
            intent="follow_yards",
            reasoning="Following blocker to yards",
        )

    # Default: Press toward endzone
    return BrainDecision(
        move_target=world.me.pos + Vec2(0, y_dir * 5),
        move_type="sprint",
        intent="yards_forward",
        reasoning="Pressing forward for yards",
    )
