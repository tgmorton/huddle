"""Play simulation with QB read progression and ball physics.

Extends team route simulation with:
- QB with auto-read progression
- Ball trajectory with simple physics
- Stochastic variance throughout (routes, DB reactions, QB accuracy)
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Use shared Vec2 directly
from .shared import Vec2

from .route_sim import (
    RouteWaypoint,
    RouteType,
    RoutePhase,
    Animation,
    ReceiverAttributes,
    DBAttributes,
)

from .team_route_sim import (
    Formation,
    CoverageScheme,
    RouteConcept,
    ReceiverPosition,
    DefenderPosition,
    ZoneType,
    TeamReceiver,
    TeamDefender,
    MatchupResult,
    ZONE_BOUNDARIES,
    ZONE_CENTERS,
    ZONE_RADIUS,
    get_receiver_alignments,
    get_coverage_assignments,
    get_defender_start_positions,
    get_routes_for_concept,
    create_offset_route,
    WR_BASE_SPEED,
    DB_BASE_SPEED,
    DB_REACTION_PENALTY,
    OPEN_SEPARATION,
    CONTESTED_SEPARATION,
    BASE_LOOKAHEAD_TICKS,
    MAX_LOOKAHEAD_TICKS,
)

# New AI modules
from .utility_ai import UtilityEvaluator, ThrowDecision
from .catch_resolver import CatchResolver, CatchResult, build_catch_context
from .pressure import PressureClock, get_pressure_throw_variance_multiplier


# =============================================================================
# Constants
# =============================================================================

MAX_TICKS = 60  # Slightly longer for throw to arrive

# QB Read Progression
BASE_READ_TICKS = 8         # Base ticks per read before moving to next
MIN_READ_TICKS = 4          # Minimum time on a read

# Read evaluation time (ticks needed to evaluate a receiver)
# Low decision_making = more ticks needed, high = faster evaluation
MAX_EVAL_TICKS = 4          # Poor QB (decision_making=50) needs 4 ticks to evaluate
MIN_EVAL_TICKS = 1          # Elite QB (decision_making=99) needs 1 tick to evaluate

# Progressive open thresholds - early reads require more separation
WIDE_OPEN_THRESHOLD = 4.0   # First read - must be clearly open
OPEN_THRESHOLD = 3.0        # Second read - open
CONTESTED_THRESHOLD = 2.0   # Third+ reads - willing to throw to tighter windows

MIN_DROP_BACK_TICKS = 6  # QB won't throw before this tick (let routes develop)

# Ball Physics
BASE_BALL_VELOCITY = 0.9  # Yards per tick (about 45 mph)
MAX_BALL_VELOCITY = 1.05  # Elite arm strength (less variance = less floaty)
CATCH_RADIUS = 1.3        # Yards from target where catch is possible (tighter = harder catches)
CONTESTED_RANGE = 0.6     # Defender within this distance of receiver = contested catch

# Ball Tracking (players react to ball in air)
DB_BALL_TRACKING_RADIUS = 12.0  # DBs within this range track the ball
DB_BALL_REACTION_DELAY = 3      # Ticks before DB reacts to ball in air (turning to find it)
DB_BALL_TRACKING_SPEED_PENALTY = 0.6  # DBs slower when tracking ball (not facing it initially)

# Variance
ROUTE_TIMING_VARIANCE = 0.5    # ±0.5 ticks variance on waypoint timing
ROUTE_POSITION_VARIANCE = 0.3  # Position variance at breaks based on skill
REACTION_DELAY_VARIANCE = 1.0  # DB reaction delay variance
VELOCITY_READ_VARIANCE = 0.05  # DB velocity read noise


# =============================================================================
# QB Animation States
# =============================================================================

class QBAnimation(str, Enum):
    """QB-specific animations."""
    STANCE = "stance"
    READING = "reading"
    THROWING = "throwing"
    FOLLOW_THROUGH = "follow_through"


class PlayResult(str, Enum):
    """Outcome of the play."""
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"


# =============================================================================
# QB Dataclass
# =============================================================================

@dataclass
class QBAttributes:
    """QB attributes affecting read and throw."""
    arm_strength: int = 85      # Ball velocity
    accuracy: int = 85          # Throw placement variance
    decision_making: int = 80   # How fast reads progress
    pocket_awareness: int = 75  # Pressure response and escape timing
    mobility: int = 75          # Scramble speed and elusiveness (1-99)

    def to_dict(self) -> dict:
        return {
            "arm_strength": self.arm_strength,
            "accuracy": self.accuracy,
            "decision_making": self.decision_making,
            "pocket_awareness": self.pocket_awareness,
            "mobility": self.mobility,
        }


@dataclass
class TeamQB:
    """Quarterback in play simulation."""
    id: str
    position: Vec2  # Typically (0, -7) for shotgun

    attributes: QBAttributes = field(default_factory=QBAttributes)

    # Read state
    read_order: list[str] = field(default_factory=list)  # Receiver IDs in order
    current_read_idx: int = 0
    ticks_on_read: int = 0
    current_read_duration: int = BASE_READ_TICKS  # How long to spend on this read

    # Throw state
    target_receiver_id: Optional[str] = None
    throw_tick: Optional[int] = None  # When throw was released
    has_thrown: bool = False

    # Visual
    animation: QBAnimation = QBAnimation.STANCE
    facing: Vec2 = field(default_factory=lambda: Vec2(0, 1))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "attributes": self.attributes.to_dict(),
            "read_order": self.read_order,
            "current_read_idx": self.current_read_idx,
            "ticks_on_read": self.ticks_on_read,
            "target_receiver_id": self.target_receiver_id,
            "throw_tick": self.throw_tick,
            "has_thrown": self.has_thrown,
            "animation": self.animation.value,
            "facing": self.facing.to_dict(),
        }


# =============================================================================
# Ball Dataclass
# =============================================================================

@dataclass
class Ball:
    """Football in flight."""
    position: Vec2 = field(default_factory=lambda: Vec2(0, -7))
    start_position: Vec2 = field(default_factory=lambda: Vec2(0, -7))
    target_position: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    velocity: float = BASE_BALL_VELOCITY  # Yards per tick

    # State
    is_thrown: bool = False
    is_caught: bool = False
    is_incomplete: bool = False
    throw_tick: int = 0
    arrival_tick: int = 0

    # Outcome
    target_receiver_id: Optional[str] = None
    intercepted_by_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "start_position": self.start_position.to_dict(),
            "target_position": self.target_position.to_dict(),
            "velocity": round(self.velocity, 3),
            "is_thrown": self.is_thrown,
            "is_caught": self.is_caught,
            "is_incomplete": self.is_incomplete,
            "throw_tick": self.throw_tick,
            "arrival_tick": self.arrival_tick,
            "target_receiver_id": self.target_receiver_id,
            "intercepted_by_id": self.intercepted_by_id,
        }


# =============================================================================
# Play Sim State
# =============================================================================

@dataclass
class PlaySimState:
    """Complete state of play simulation."""
    receivers: list[TeamReceiver]
    defenders: list[TeamDefender]
    qb: TeamQB
    ball: Ball
    formation: Formation
    coverage: CoverageScheme
    concept: RouteConcept

    # Tracking
    matchups: dict[str, MatchupResult] = field(default_factory=dict)
    tick: int = 0
    is_complete: bool = False
    play_result: PlayResult = PlayResult.IN_PROGRESS

    # Variance settings
    variance_enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "receivers": [r.to_dict() for r in self.receivers],
            "defenders": [d.to_dict() for d in self.defenders],
            "qb": self.qb.to_dict(),
            "ball": self.ball.to_dict(),
            "formation": self.formation.value,
            "coverage": self.coverage.value,
            "concept": self.concept.value,
            "matchups": {k: v.to_dict() for k, v in self.matchups.items()},
            "tick": self.tick,
            "is_complete": self.is_complete,
            "play_result": self.play_result.value,
        }


# =============================================================================
# Read Order by Concept
# =============================================================================

def get_read_order(concept: RouteConcept, formation: Formation) -> list[ReceiverPosition]:
    """Return receiver positions in read order based on concept."""
    if concept == RouteConcept.FOUR_VERTS:
        # Read outside-in for verts
        if formation in (Formation.TRIPS_RIGHT, Formation.SPREAD):
            return [ReceiverPosition.Z, ReceiverPosition.SLOT_R, ReceiverPosition.SLOT_L, ReceiverPosition.X]
        else:
            return [ReceiverPosition.X, ReceiverPosition.SLOT_L, ReceiverPosition.SLOT_R, ReceiverPosition.Z]

    elif concept == RouteConcept.SMASH:
        # Read corner first, then hitch
        return [ReceiverPosition.Z, ReceiverPosition.SLOT_R, ReceiverPosition.X, ReceiverPosition.SLOT_L]

    elif concept == RouteConcept.MESH:
        # Read crossing routes
        return [ReceiverPosition.SLOT_R, ReceiverPosition.SLOT_L, ReceiverPosition.X, ReceiverPosition.Z]

    elif concept == RouteConcept.FLOOD:
        # Read high-low
        return [ReceiverPosition.Z, ReceiverPosition.SLOT_R, ReceiverPosition.TE, ReceiverPosition.X]

    elif concept == RouteConcept.LEVELS:
        # Read short to deep
        return [ReceiverPosition.SLOT_R, ReceiverPosition.SLOT_L, ReceiverPosition.X, ReceiverPosition.Z]

    elif concept == RouteConcept.SLANTS:
        # Quick game - read inside-out
        return [ReceiverPosition.SLOT_R, ReceiverPosition.SLOT_L, ReceiverPosition.X, ReceiverPosition.Z]

    elif concept == RouteConcept.CURLS:
        # Curl-flat read
        return [ReceiverPosition.X, ReceiverPosition.Z, ReceiverPosition.SLOT_L, ReceiverPosition.SLOT_R]

    else:  # CUSTOM
        return [ReceiverPosition.X, ReceiverPosition.SLOT_L, ReceiverPosition.SLOT_R, ReceiverPosition.Z]


# =============================================================================
# Play Simulator
# =============================================================================

class PlaySimulator:
    """Simulates full passing play with QB reads and ball flight."""

    def __init__(
        self,
        formation: Formation = Formation.SPREAD,
        coverage: CoverageScheme = CoverageScheme.COVER_3,
        concept: RouteConcept = RouteConcept.FOUR_VERTS,
        variance_enabled: bool = True,
        qb_attributes: Optional[QBAttributes] = None,
        wr_attributes: Optional[dict[ReceiverPosition, ReceiverAttributes]] = None,
        db_attributes: Optional[dict[DefenderPosition, DBAttributes]] = None,
    ):
        self.formation = formation
        self.coverage = coverage
        self.concept = concept
        self.variance_enabled = variance_enabled
        self.qb_attributes = qb_attributes or QBAttributes()
        self.wr_attributes = wr_attributes or {}
        self.db_attributes = db_attributes or {}
        self.state: Optional[PlaySimState] = None

        # Track max separation per receiver
        self._max_separations: dict[str, float] = {}

        # AI components
        self._utility_evaluator = UtilityEvaluator(variance_enabled=variance_enabled)
        self._catch_resolver = CatchResolver(variance_enabled=variance_enabled)
        self._pressure_clock = PressureClock()

        # External pressure integration (from integrated_sim)
        self._external_pressure: Optional[float] = None
        self._external_pressure_enabled: bool = False

    def setup(self) -> None:
        """Initialize simulation."""
        # Create receivers based on formation
        alignments = get_receiver_alignments(self.formation)
        routes = get_routes_for_concept(self.concept, self.formation)

        receivers = []
        receiver_by_pos: dict[ReceiverPosition, TeamReceiver] = {}

        for pos, start_pos in alignments.items():
            route_type = routes.get(pos, RouteType.GO)
            route = create_offset_route(route_type, start_pos.x)

            attrs = self.wr_attributes.get(pos, ReceiverAttributes())

            rcvr = TeamReceiver(
                id=str(uuid.uuid4()),
                position=Vec2(start_pos.x, start_pos.y),
                alignment=pos,
                route=route,
                route_type=route_type,
                attributes=attrs,
            )
            receivers.append(rcvr)
            receiver_by_pos[pos] = rcvr

        # Create defenders based on coverage
        assignments = get_coverage_assignments(self.coverage, receivers)
        positions = get_defender_start_positions(self.coverage, receivers)

        defenders = []
        for def_pos, start_pos in positions.items():
            man_target, zone_type = assignments.get(def_pos, (None, None))

            attrs = self.db_attributes.get(def_pos, DBAttributes())

            zone_center = None
            zone_radius = 10.0
            if zone_type:
                zone_center = ZONE_CENTERS.get(zone_type)
                zone_radius = ZONE_RADIUS.get(zone_type, 10.0)

            defender = TeamDefender(
                id=str(uuid.uuid4()),
                position=Vec2(start_pos.x, start_pos.y),
                alignment=def_pos,
                attributes=attrs,
                man_assignment=man_target,
                zone_assignment=zone_type,
                zone_center=zone_center,
                zone_radius=zone_radius,
                is_in_man=man_target is not None,
            )
            defenders.append(defender)

        # Create QB
        qb = TeamQB(
            id=str(uuid.uuid4()),
            position=Vec2(0, -7),  # Shotgun depth
            attributes=self.qb_attributes,
        )

        # Set up read order
        read_positions = get_read_order(self.concept, self.formation)
        qb.read_order = [
            receiver_by_pos[pos].id
            for pos in read_positions
            if pos in receiver_by_pos
        ]

        # Initialize read duration with variance
        qb.current_read_duration = self._get_read_duration()

        # Create ball
        ball = Ball(
            position=Vec2(qb.position.x, qb.position.y),
            start_position=Vec2(qb.position.x, qb.position.y),
        )

        # Initialize matchups tracking
        matchups = {}
        for rcvr in receivers:
            matchups[rcvr.id] = MatchupResult(
                receiver_id=rcvr.id,
                defender_id="",
                separation=0.0,
                max_separation=0.0,
                result="in_progress",
            )
            self._max_separations[rcvr.id] = 0.0

        self.state = PlaySimState(
            receivers=receivers,
            defenders=defenders,
            qb=qb,
            ball=ball,
            formation=self.formation,
            coverage=self.coverage,
            concept=self.concept,
            matchups=matchups,
            variance_enabled=self.variance_enabled,
        )

    def reset(self) -> None:
        """Reset simulation."""
        self._max_separations = {}
        self._pressure_clock.reset()
        self._external_pressure = None
        self._external_pressure_enabled = False
        self.setup()

    # =========================================================================
    # External Pressure Hooks (for integrated_sim)
    # =========================================================================

    def set_external_pressure(
        self,
        total: float,
        eta_ticks: float = float('inf'),
        left: float = 0.0,
        right: float = 0.0,
        front: float = 0.0,
        panic: bool = False,
    ) -> None:
        """Set pressure from external source (e.g., pocket_sim).

        When external pressure is enabled, the internal pressure clock is bypassed
        and this value is used directly for QB decision-making and throw variance.

        Args:
            total: Overall pressure level 0.0-1.0
            eta_ticks: Estimated ticks until rusher reaches QB
            left: Pressure from left side 0.0-1.0
            right: Pressure from right side 0.0-1.0
            front: Pressure from front 0.0-1.0
            panic: Whether QB is in imminent danger
        """
        self._external_pressure = max(0.0, min(1.0, total))
        self._external_pressure_enabled = True
        # Use pressure clock's external pressure method
        self._pressure_clock.set_external_pressure(
            total=total,
            eta_ticks=eta_ticks,
            left=left,
            right=right,
            front=front,
            panic=panic,
        )

    def disable_external_pressure(self) -> None:
        """Disable external pressure and return to internal pressure clock."""
        self._external_pressure = None
        self._external_pressure_enabled = False
        self._pressure_clock.disable_external_pressure()

    def get_pressure(self) -> float:
        """Get current pressure level (external or internal)."""
        return self._pressure_clock.total_pressure

    def is_panic_mode(self) -> bool:
        """Check if QB is in panic mode (imminent sack)."""
        return self._pressure_clock.panic_mode

    def panic_throw(self, target_id: Optional[str] = None) -> bool:
        """Force immediate throw under heavy pressure (panic mode).

        When called, QB immediately throws to the specified target or the
        current read. This bypasses normal evaluation time and decision-making.

        Args:
            target_id: Receiver ID to throw to. If None, throws to current read.

        Returns:
            True if throw was executed, False if no valid target.
        """
        if not self.state or self.state.qb.has_thrown:
            return False

        qb = self.state.qb

        # Determine target
        if target_id is None:
            # Throw to current read or last receiver in progression
            if qb.current_read_idx < len(qb.read_order):
                target_id = qb.read_order[qb.current_read_idx]
            elif qb.read_order:
                target_id = qb.read_order[-1]
            else:
                return False

        # Verify target exists
        target_exists = any(r.id == target_id for r in self.state.receivers)
        if not target_exists:
            return False

        # Execute panic throw (with extra accuracy penalty applied in _execute_throw)
        self._execute_throw(target_id)
        return True

    def skip_read(self) -> bool:
        """Skip current read and move to next in progression.

        Used when pressure forces QB to abandon current read.

        Returns:
            True if read was skipped, False if no more reads.
        """
        if not self.state:
            return False

        qb = self.state.qb
        if qb.current_read_idx < len(qb.read_order) - 1:
            qb.current_read_idx += 1
            qb.ticks_on_read = 0
            qb.current_read_duration = self._get_read_duration()
            return True
        return False

    def _get_read_duration(self) -> int:
        """Calculate how long QB spends on current read."""
        decision_factor = self.qb_attributes.decision_making / 100
        base = BASE_READ_TICKS - (decision_factor * 3)  # 5-8 ticks

        if self.variance_enabled:
            variance = random.gauss(0, 1.0)  # ±1 tick variance
            return max(MIN_READ_TICKS, int(base + variance))
        return max(MIN_READ_TICKS, int(base))

    def tick(self) -> PlaySimState:
        """Advance simulation by one tick."""
        if not self.state or self.state.is_complete:
            return self.state

        self.state.tick += 1

        # Update pressure clock
        self._pressure_clock.update(self.state.tick)

        # Process each receiver (with variance)
        for rcvr in self.state.receivers:
            self._process_receiver(rcvr)

        # Process each defender (with variance)
        for defender in self.state.defenders:
            self._process_defender(defender)

        # Process QB reads (using utility AI)
        self._process_qb()

        # Process ball if thrown
        if self.state.ball.is_thrown and not self.state.ball.is_caught and not self.state.ball.is_incomplete:
            self._process_ball()

        # Update separations and matchups
        self._update_matchups()

        # Check completion
        self._check_completion()

        return self.state

    def _process_receiver(self, rcvr: TeamReceiver) -> None:
        """Move receiver along route with optional variance."""
        # If ball is thrown to this receiver, track toward the ball target
        ball = self.state.ball
        if ball.is_thrown and not ball.is_caught and not ball.is_incomplete:
            if ball.target_receiver_id == rcvr.id:
                self._move_toward_ball(rcvr, ball.target_position)
                return

        # Phase transitions
        if self.state.tick == 1:
            rcvr.route_phase = RoutePhase.RELEASE

        if rcvr.route_phase == RoutePhase.RELEASE:
            if self.state.tick >= 2:
                rcvr.route_phase = RoutePhase.STEM
                rcvr.animation = Animation.ROUTE_STEM
            return

        if rcvr.current_waypoint_idx >= len(rcvr.route):
            rcvr.route_phase = RoutePhase.COMPLETE
            return

        waypoint = rcvr.route[rcvr.current_waypoint_idx]

        # Apply timing variance
        effective_arrival = waypoint.arrival_tick
        if self.variance_enabled:
            timing_variance = random.gauss(0, ROUTE_TIMING_VARIANCE)
            effective_arrival += timing_variance

        # Check for break
        if waypoint.is_break and rcvr.route_phase != RoutePhase.BREAK:
            if self.state.tick >= effective_arrival - 2:
                rcvr.route_phase = RoutePhase.BREAK
                rcvr.animation = Animation.ROUTE_BREAK

        # Calculate target with position variance at breaks
        target = waypoint.position
        if self.variance_enabled and waypoint.is_break:
            route_skill = rcvr.attributes.route_running / 100
            position_variance = ROUTE_POSITION_VARIANCE * (1 - route_skill)
            target = Vec2(
                target.x + random.gauss(0, position_variance),
                target.y + random.gauss(0, position_variance),
            )

        # Calculate movement
        desired_direction = (target - rcvr.position).normalized()

        # Speed with acceleration and COD
        max_speed = WR_BASE_SPEED * (rcvr.attributes.speed / 85) ** 2
        accel_rate = 0.08 * (rcvr.attributes.acceleration / 85) ** 1.5

        # COD penalty
        if rcvr.current_speed > 0.1:
            current_dir = rcvr.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                route_skill = (rcvr.attributes.route_running / 85) ** 1.5
                base_loss = angle / math.pi
                cod_loss = min(0.4, base_loss * (1.0 - route_skill * 0.4))
                rcvr.current_speed *= (1.0 - cod_loss)

        # Accelerate
        if rcvr.current_speed < max_speed:
            rcvr.current_speed = min(max_speed, rcvr.current_speed + accel_rate)

        # Break speed cap
        if rcvr.route_phase == RoutePhase.BREAK:
            break_cap = max_speed * 0.7 * (rcvr.attributes.route_running / 85)
            rcvr.current_speed = min(rcvr.current_speed, break_cap)

        # Update position
        rcvr.velocity = desired_direction * rcvr.current_speed
        rcvr.position = rcvr.position + rcvr.velocity
        rcvr.facing = desired_direction

        # Check waypoint reached
        if rcvr.position.distance_to(waypoint.position) < 0.5:
            rcvr.current_waypoint_idx += 1
            if rcvr.route_phase == RoutePhase.BREAK:
                rcvr.route_phase = RoutePhase.POST_BREAK
                rcvr.animation = Animation.ROUTE_RUN

    def _move_toward_ball(self, player: TeamReceiver | TeamDefender, target: Vec2) -> None:
        """Move a player toward the ball's target position."""
        direction = (target - player.position).normalized()
        distance = player.position.distance_to(target)

        # Determine max speed based on player type
        # Defenders are slower when tracking ball (turning to find it)
        if isinstance(player, TeamReceiver):
            max_speed = WR_BASE_SPEED * (player.attributes.speed / 85) ** 2
        else:
            max_speed = DB_BASE_SPEED * (player.attributes.speed / 85) ** 2 * DB_BALL_TRACKING_SPEED_PENALTY

        # Accelerate toward target
        accel_rate = 0.08
        if player.current_speed < max_speed:
            player.current_speed = min(max_speed, player.current_speed + accel_rate)

        # Slow down when close to target
        if distance < 2.0:
            player.current_speed = min(player.current_speed, distance * 0.5)

        # Update position
        player.velocity = direction * player.current_speed
        player.position = player.position + player.velocity
        player.facing = direction

    def _should_defender_track_ball(self, defender: TeamDefender) -> bool:
        """Check if defender should abandon coverage and track the ball.

        Multiple defenders can rally to the ball:
        1. Primary coverage (man assignment or near zone): fastest reaction
        2. Help defenders (safeties, nearby DBs): can break on ball with slight delay
        3. All defenders within range can rally to make plays on the ball
        """
        ball = self.state.ball
        if not ball.is_thrown or ball.is_caught or ball.is_incomplete:
            return False

        ticks_in_air = self.state.tick - ball.throw_tick
        dist_to_ball = defender.position.distance_to(ball.target_position)

        # Primary defender (covering target) reacts fastest
        is_primary = False
        if defender.is_in_man:
            is_primary = defender.man_assignment == ball.target_receiver_id
        else:
            # Zone defender is primary if ball target is in their zone
            is_primary = dist_to_ball < DB_BALL_TRACKING_RADIUS * 0.6

        # Primary defenders react after standard delay
        if is_primary and ticks_in_air >= DB_BALL_REACTION_DELAY:
            return True

        # Help defenders (safeties, nearby zone) can rally with +1 tick delay
        # Safeties have deep zone assignments typically
        is_safety = defender.zone_assignment in {
            ZoneType.DEEP_THIRD_L, ZoneType.DEEP_THIRD_M, ZoneType.DEEP_THIRD_R,
            ZoneType.DEEP_HALF_L, ZoneType.DEEP_HALF_R,
            ZoneType.DEEP_QUARTER_1, ZoneType.DEEP_QUARTER_2,
            ZoneType.DEEP_QUARTER_3, ZoneType.DEEP_QUARTER_4
        } if defender.zone_assignment else False

        # Help defenders rally if within extended range
        help_radius = DB_BALL_TRACKING_RADIUS * 1.5  # Safeties can break from further away
        if is_safety and dist_to_ball < help_radius:
            if ticks_in_air >= DB_BALL_REACTION_DELAY + 1:
                return True

        # Any defender within tracking radius can rally after longer delay
        if dist_to_ball < DB_BALL_TRACKING_RADIUS:
            if ticks_in_air >= DB_BALL_REACTION_DELAY + 2:
                return True

        return False

    def _process_defender(self, defender: TeamDefender) -> None:
        """Move defender based on coverage assignment with variance."""
        # If ball is in the air and defender is nearby, track the ball
        if self._should_defender_track_ball(defender):
            self._move_toward_ball(defender, self.state.ball.target_position)
            return

        if defender.is_in_man and defender.man_assignment:
            self._process_man_defender(defender)
        elif defender.zone_assignment:
            self._process_zone_defender(defender)

    def _process_man_defender(self, defender: TeamDefender) -> None:
        """DB follows assigned receiver with predictive tracking and variance."""
        # Find target receiver
        target_rcvr = None
        for rcvr in self.state.receivers:
            if rcvr.id == defender.man_assignment:
                target_rcvr = rcvr
                break

        if not target_rcvr:
            return

        # Calculate lookahead based on play recognition
        play_rec_factor = defender.attributes.play_recognition / 100
        distance_to_wr = defender.position.distance_to(target_rcvr.position)

        base_lookahead = BASE_LOOKAHEAD_TICKS + (play_rec_factor * 4)
        if distance_to_wr < 1.5:
            base_lookahead *= 0.5
        elif distance_to_wr < 3:
            base_lookahead *= 0.7
        lookahead_ticks = max(3, min(MAX_LOOKAHEAD_TICKS, base_lookahead))

        # Handle break phase with variance in reaction delay
        just_started_flip = False

        if target_rcvr.route_phase == RoutePhase.BREAK:
            if not defender.has_reacted_to_break and defender.reaction_delay == 0:
                # Break just started! Set reaction delay with variance
                base_delay = 5
                delay_reduction = play_rec_factor * 2

                if self.variance_enabled:
                    delay_variance = random.gauss(0, REACTION_DELAY_VARIANCE * (1 - play_rec_factor))
                    defender.reaction_delay = max(3, int(base_delay - delay_reduction + delay_variance))
                else:
                    defender.reaction_delay = max(3, int(base_delay - delay_reduction))

                # Freeze pre-break velocity
                if defender.pre_break_velocity is None:
                    defender.pre_break_velocity = Vec2(
                        defender.last_read_velocity.x,
                        defender.last_read_velocity.y
                    )
                defender.read_confidence = 1.0

            if not defender.has_reacted_to_break:
                defender.reaction_delay -= 1
                if defender.pre_break_velocity:
                    defender.last_read_velocity = defender.pre_break_velocity

                if defender.reaction_delay <= 0:
                    defender.has_reacted_to_break = True
                    defender.animation = Animation.FLIP_HIPS
                    just_started_flip = True
                    defender.last_read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)
                    defender.pre_break_velocity = None
                    defender.read_confidence = 0.5

        elif target_rcvr.route_phase == RoutePhase.POST_BREAK:
            if defender.has_reacted_to_break:
                defender.read_confidence = min(1.0, defender.read_confidence + 0.1)
                defender.last_read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)
                defender.pre_break_velocity = None
        else:
            # Normal tracking with velocity read variance
            if target_rcvr.velocity.length() > 0.05:
                read_velocity = Vec2(target_rcvr.velocity.x, target_rcvr.velocity.y)

                if self.variance_enabled:
                    # Add noise to DB's velocity read
                    velocity_noise = VELOCITY_READ_VARIANCE * (1 - play_rec_factor)
                    read_velocity.x += random.gauss(0, velocity_noise)
                    read_velocity.y += random.gauss(0, velocity_noise)

                defender.last_read_velocity = read_velocity
            defender.read_confidence = 1.0
            defender.pre_break_velocity = None

        # Project anticipated position
        projected_pos = target_rcvr.position + defender.last_read_velocity * lookahead_ticks

        if defender.pre_break_velocity is not None:
            projection_weight = 1.0
        else:
            projection_weight = defender.read_confidence
            if distance_to_wr < 2:
                projection_weight *= 0.6

        anticipated = Vec2(
            target_rcvr.position.x * (1 - projection_weight) + projected_pos.x * projection_weight,
            target_rcvr.position.y * (1 - projection_weight) + projected_pos.y * projection_weight,
        )
        defender.anticipated_position = anticipated

        target = anticipated
        desired_direction = (target - defender.position).normalized()

        # Speed calculation
        speed_factor = (defender.attributes.speed / 85) ** 2
        coverage_factor = (defender.attributes.man_coverage / 85) ** 1.5
        max_speed = DB_BASE_SPEED * speed_factor * coverage_factor
        accel_rate = 0.07 * (defender.attributes.acceleration / 85) ** 1.5

        if just_started_flip:
            flip_penalty = 0.4 + (defender.attributes.man_coverage / 100) * 0.2
            defender.current_speed *= flip_penalty

        # COD
        if defender.current_speed > 0.1 and defender.animation != Animation.FLIP_HIPS:
            current_dir = defender.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                skill_factor = (defender.attributes.man_coverage / 85) ** 1.5
                base_loss = angle / math.pi
                cod_loss = min(0.4, base_loss * (1.0 - skill_factor * 0.35))
                defender.current_speed *= (1.0 - cod_loss)

        if defender.current_speed < max_speed:
            defender.current_speed = min(max_speed, defender.current_speed + accel_rate)

        if defender.animation == Animation.FLIP_HIPS:
            defender.current_speed = min(defender.current_speed, max_speed * 0.6)

        if target_rcvr.route_phase in (RoutePhase.BREAK, RoutePhase.POST_BREAK) and not defender.has_reacted_to_break:
            defender.current_speed = min(defender.current_speed, max_speed * DB_REACTION_PENALTY)

        defender.velocity = desired_direction * defender.current_speed
        defender.position = defender.position + defender.velocity
        defender.facing = desired_direction

        is_trailing = defender.position.y < target_rcvr.position.y
        if defender.animation == Animation.FLIP_HIPS:
            if defender.has_reacted_to_break and defender.reaction_delay <= -2:
                defender.animation = Animation.TRAIL if is_trailing else Animation.CLOSING
            defender.reaction_delay -= 1
        elif defender.animation not in (Animation.PRESS_JAM, Animation.PRESS_BEAT):
            defender.animation = Animation.TRAIL if is_trailing else Animation.CLOSING

    def _process_zone_defender(self, defender: TeamDefender) -> None:
        """Zone coverage with predictive tracking."""
        if not defender.zone_assignment:
            return

        zone = ZONE_BOUNDARIES.get(defender.zone_assignment)
        if not zone:
            return

        target_rcvr, threat_level = self._find_zone_threat(defender, zone)
        target = self._get_zone_target_position(defender, zone, target_rcvr, threat_level)

        desired_direction = (target - defender.position).normalized()

        speed_factor = (defender.attributes.speed / 85) ** 2
        zone_factor = (defender.attributes.zone_coverage / 85) ** 1.5

        if defender.has_triggered and target_rcvr:
            max_speed = DB_BASE_SPEED * speed_factor * zone_factor
        elif defender.is_backpedaling and zone.is_deep:
            max_speed = DB_BASE_SPEED * speed_factor * 0.6
        else:
            max_speed = DB_BASE_SPEED * speed_factor * zone_factor * 0.75

        accel_rate = 0.07 * (defender.attributes.acceleration / 85) ** 1.5

        if defender.current_speed > 0.1:
            current_dir = defender.velocity.normalized()
            dot = current_dir.dot(desired_direction)
            dot = max(-1.0, min(1.0, dot))
            angle = math.acos(dot)

            if angle > 0.5:
                skill_factor = (defender.attributes.zone_coverage / 85) ** 1.5
                base_loss = angle / math.pi
                cod_mult = 0.2 if defender.has_triggered else 0.35
                cod_loss = min(0.4, base_loss * (1.0 - skill_factor * cod_mult))
                defender.current_speed *= (1.0 - cod_loss)

        if defender.current_speed < max_speed:
            defender.current_speed = min(max_speed, defender.current_speed + accel_rate)

        if not defender.has_triggered and defender.position.distance_to(zone.anchor) < 2:
            defender.current_speed *= 0.5

        defender.velocity = desired_direction * defender.current_speed
        defender.position = defender.position + defender.velocity
        defender.facing = desired_direction

        if defender.has_triggered:
            defender.animation = Animation.CLOSING
        elif defender.is_backpedaling:
            defender.animation = Animation.BACKPEDAL
        else:
            defender.animation = Animation.ZONE_READ

    def _find_zone_threat(
        self, defender: TeamDefender, zone
    ) -> tuple[Optional[TeamReceiver], str]:
        """Find the most dangerous receiver threatening this zone."""
        best_rcvr = None
        best_threat = 'none'
        best_score = -float('inf')

        for rcvr in self.state.receivers:
            in_zone = zone.contains(rcvr.position)

            approaching = False
            dist_to_zone = zone.distance_to_boundary(rcvr.position)
            if dist_to_zone < 10:
                if rcvr.velocity.y > 0.1:
                    if rcvr.position.y < zone.max_y:
                        approaching = True
                if abs(rcvr.velocity.x) > 0.1:
                    if (rcvr.velocity.x > 0 and rcvr.position.x < zone.max_x) or \
                       (rcvr.velocity.x < 0 and rcvr.position.x > zone.min_x):
                        approaching = True

            if not in_zone and not approaching:
                continue

            score = 0

            if in_zone:
                score += 100
                dist_to_center = rcvr.position.distance_to(zone.anchor)
                score += max(0, 10 - dist_to_center)
            elif approaching:
                score += 50
                score += max(0, 10 - dist_to_zone) * 3

            if zone.is_deep and rcvr.velocity.y > 0.2:
                score += 20

            if defender.zone_target_id == rcvr.id:
                score += 25

            if zone.is_deep:
                x_proximity = abs(rcvr.position.x - defender.position.x)
                score += max(0, 30 - x_proximity * 2)

                zone_center_x = (zone.min_x + zone.max_x) / 2
                if (defender.position.x > zone_center_x and rcvr.position.x < zone_center_x) or \
                   (defender.position.x < zone_center_x and rcvr.position.x > zone_center_x):
                    score -= 40

            if score > best_score:
                best_score = score
                best_rcvr = rcvr
                best_threat = 'in_zone' if in_zone else 'approaching'

        return best_rcvr, best_threat

    def _get_zone_target_position(
        self,
        defender: TeamDefender,
        zone,
        target_rcvr: Optional[TeamReceiver],
        threat_level: str,
    ) -> Vec2:
        """Determine where the zone defender should move."""
        if target_rcvr and threat_level == 'in_zone':
            defender.has_triggered = True
            defender.zone_target_id = target_rcvr.id
            defender.is_backpedaling = False

            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5)

            anticipated = target_rcvr.position + target_rcvr.velocity * lookahead
            defender.anticipated_position = anticipated

            if zone.is_deep and target_rcvr.velocity.y > 0.25:
                target_x = anticipated.x
                target_y = max(defender.position.y, anticipated.y)
                return Vec2(target_x, target_y)

            return anticipated

        elif target_rcvr and threat_level == 'approaching':
            defender.zone_target_id = target_rcvr.id
            defender.is_backpedaling = False

            play_rec_factor = defender.attributes.play_recognition / 100
            lookahead = BASE_LOOKAHEAD_TICKS * (0.5 + play_rec_factor * 0.5)
            anticipated = target_rcvr.position + target_rcvr.velocity * lookahead
            defender.anticipated_position = anticipated

            if zone.is_deep and target_rcvr.velocity.y > 0.25:
                target_x = anticipated.x
                target_y = max(defender.position.y, anticipated.y)
                return Vec2(
                    max(zone.min_x, min(zone.max_x, target_x)),
                    target_y
                )

            intercept_x = max(zone.min_x, min(zone.max_x, anticipated.x))
            intercept_y = max(zone.min_y, min(zone.max_y, anticipated.y))

            return Vec2(intercept_x, intercept_y)

        else:
            defender.zone_target_id = None
            defender.has_triggered = False
            defender.anticipated_position = None

            if zone.is_deep:
                if defender.position.y < zone.anchor.y - 2:
                    defender.is_backpedaling = True
                else:
                    defender.is_backpedaling = False

                return zone.anchor

            return zone.anchor

    def _process_qb(self) -> None:
        """Process QB read progression and throw decision using utility AI."""
        qb = self.state.qb

        if qb.has_thrown:
            qb.animation = QBAnimation.FOLLOW_THROUGH
            return

        qb.animation = QBAnimation.READING

        # Gate 1: Don't start reading until MIN_DROP_BACK_TICKS (let routes develop)
        if self.state.tick < MIN_DROP_BACK_TICKS:
            return

        # Out of reads - throw to last option or checkdown
        if qb.current_read_idx >= len(qb.read_order):
            if qb.read_order:
                self._execute_throw(qb.read_order[-1])
            return

        current_target_id = qb.read_order[qb.current_read_idx]
        qb.ticks_on_read += 1

        # Find target receiver
        target_rcvr = None
        for rcvr in self.state.receivers:
            if rcvr.id == current_target_id:
                target_rcvr = rcvr
                break

        if not target_rcvr:
            qb.current_read_idx += 1
            qb.ticks_on_read = 0
            qb.current_read_duration = self._get_read_duration()
            return

        # Update QB facing toward target
        qb.facing = (target_rcvr.position - qb.position).normalized()

        # Get pressure (external or internal)
        pressure = self.get_pressure()

        # Pressure-aware read skipping
        # Under heavy pressure, QB may abandon current read early
        if self.variance_enabled and pressure > 0.5:
            skip_chance = self._calculate_read_skip_chance(pressure)
            if random.random() < skip_chance:
                # Skip to next read under pressure
                if qb.current_read_idx < len(qb.read_order) - 1:
                    qb.current_read_idx += 1
                    qb.ticks_on_read = 0
                    qb.current_read_duration = self._get_read_duration()
                    return

        # Gate 2: Must spend minimum evaluation time on current read before throwing
        eval_ticks_needed = self._get_evaluation_ticks()
        if qb.ticks_on_read < eval_ticks_needed:
            # Still evaluating current read - can't throw yet
            return

        # Use utility AI to make throw decision
        # Only evaluate receivers up to and including current read index
        available_receivers = [
            rcvr for rcvr in self.state.receivers
            if rcvr.id in qb.read_order[:qb.current_read_idx + 1]
        ]

        decision = self._utility_evaluator.make_decision(
            qb=qb,
            receivers=available_receivers,
            matchups=self.state.matchups,
            tick=self.state.tick,
            pressure=pressure,
        )

        if decision.should_throw and decision.target_id:
            self._execute_throw(decision.target_id)
            return

        # Move to next read?
        if qb.ticks_on_read >= qb.current_read_duration:
            qb.current_read_idx += 1
            qb.ticks_on_read = 0
            qb.current_read_duration = self._get_read_duration()

    def _calculate_read_skip_chance(self, pressure: float) -> float:
        """Calculate probability of skipping current read due to pressure.

        Args:
            pressure: Current pressure level (0.0 to 1.0)

        Returns:
            Skip probability per tick (0.0 to 1.0)
        """
        # No skipping below moderate pressure
        if pressure < 0.5:
            return 0.0

        # Base skip chances by pressure level
        # HEAVY (0.5-0.75): 5% per tick
        # CRITICAL (0.75-1.0): 15% per tick
        if pressure < 0.75:
            base_chance = 0.05
        else:
            base_chance = 0.15

        # Pocket awareness reduces skip chance
        awareness_factor = self.state.qb.attributes.pocket_awareness / 100
        adjusted_chance = base_chance * (1.0 - awareness_factor * 0.5)

        return max(0.0, min(0.25, adjusted_chance))

    def _get_evaluation_ticks(self) -> int:
        """Calculate ticks needed for QB to evaluate a receiver.

        Based on decision_making attribute:
        - Poor QB (50) needs ~5 ticks (stares down receiver)
        - Elite QB (99) needs ~1 tick (scans quickly)
        """
        decision_making = self.state.qb.attributes.decision_making
        # Linear interpolation between MAX_EVAL_TICKS and MIN_EVAL_TICKS
        # decision_making 50 -> MAX_EVAL_TICKS, decision_making 99 -> MIN_EVAL_TICKS
        factor = (decision_making - 50) / 49  # 0.0 at 50, 1.0 at 99
        factor = max(0.0, min(1.0, factor))
        eval_ticks = MAX_EVAL_TICKS - (factor * (MAX_EVAL_TICKS - MIN_EVAL_TICKS))
        return int(eval_ticks)

    def _should_throw(
        self,
        target_rcvr: TeamReceiver,
        separation: float,
        read_idx: int,
        ticks_on_read: int,
    ) -> bool:
        """Decide if QB should throw based on separation, route phase, and read progression.

        QB only throws if:
        1. Minimum dropback time has elapsed (routes need to develop)
        2. QB has evaluated the receiver (time based on decision_making)
        3. Receiver is in a "ready" route phase (BREAK or POST_BREAK for early reads)
        4. Separation exceeds threshold (lower threshold for later reads)
        """
        # Don't throw before routes have developed
        if self.state.tick < MIN_DROP_BACK_TICKS:
            return False

        # QB must evaluate receiver before throwing (attribute-based)
        eval_ticks_needed = self._get_evaluation_ticks()
        if ticks_on_read < eval_ticks_needed:
            return False

        # Don't throw to receivers still in release
        if target_rcvr.route_phase in (RoutePhase.PRE_SNAP, RoutePhase.RELEASE):
            return False

        # For first read, prefer receivers who have completed their break
        # (route timing - throw when receiver is "ready")
        if read_idx == 0 and target_rcvr.route_phase == RoutePhase.STEM:
            # Only throw to stem phase if VERY wide open
            if separation < WIDE_OPEN_THRESHOLD + 2.0:
                return False

        decision_factor = self.state.qb.attributes.decision_making / 100

        # Progressive threshold - earlier reads require more separation
        if read_idx == 0:
            base_threshold = WIDE_OPEN_THRESHOLD
        elif read_idx == 1:
            base_threshold = OPEN_THRESHOLD
        else:
            base_threshold = CONTESTED_THRESHOLD

        # Better decision-making = willing to throw to tighter windows
        threshold = base_threshold - (decision_factor * 1.0)

        if self.variance_enabled:
            variance = random.gauss(0, 0.5)
            return separation + variance > threshold

        return separation > threshold

    def _predict_receiver_position(
        self,
        receiver: TeamReceiver,
        qb_position: Vec2,
        ball_velocity: float,
    ) -> Vec2:
        """Predict where receiver will be when ball arrives.

        Uses route-aware prediction:
        - For settling routes (HITCH, CURL, COMEBACK), throw to the settle point
        - For continuing routes, use velocity extrapolation with lead cap
        """
        # Routes where receiver stops/settles at a point
        SETTLING_ROUTES = {RouteType.HITCH, RouteType.CURL, RouteType.COMEBACK}

        # For settling routes, use route waypoints to predict position
        if receiver.route_type in SETTLING_ROUTES and receiver.route:
            # Calculate initial estimated ball travel time
            distance = qb_position.distance_to(receiver.position)
            travel_ticks = max(1, int(distance / ball_velocity))
            arrival_tick = self.state.tick + travel_ticks

            # Movement timing is approximately 2x the waypoint timing
            # (receiver moves slower than waypoints suggest)
            TIMING_FACTOR = 2.0

            # Find the waypoint that matches when ball would arrive
            # Walk through waypoints to find position at arrival tick
            final_waypoint = receiver.route[-1]
            settle_position = final_waypoint.position
            settle_time = final_waypoint.arrival_tick * TIMING_FACTOR

            # If ball arrives after settle, throw to settle point
            if arrival_tick >= settle_time:
                return settle_position

            # Find which segment of the route receiver will be on at arrival
            prev_wp_time = 0
            # Start position: receiver begins at y=0 (line of scrimmage) at their route's X
            prev_wp_pos = Vec2(receiver.route[0].position.x, 0)

            for wp in receiver.route:
                wp_time = wp.arrival_tick * TIMING_FACTOR
                if arrival_tick <= wp_time:
                    # Ball arrives during this segment
                    # Interpolate between previous waypoint and this one
                    segment_duration = wp_time - prev_wp_time
                    if segment_duration > 0:
                        t = (arrival_tick - prev_wp_time) / segment_duration
                        t = min(1.0, max(0.0, t))
                        target_pos = Vec2(
                            prev_wp_pos.x + (wp.position.x - prev_wp_pos.x) * t,
                            prev_wp_pos.y + (wp.position.y - prev_wp_pos.y) * t,
                        )
                        return target_pos
                    else:
                        return wp.position
                prev_wp_time = wp_time
                prev_wp_pos = wp.position

            # Fallback to settle position
            return settle_position

        # For continuing routes, use velocity extrapolation
        target_pos = receiver.position
        for _ in range(3):
            distance = qb_position.distance_to(target_pos)
            travel_ticks = max(1, int(distance / ball_velocity))
            target_pos = receiver.position + receiver.velocity * travel_ticks

        # Cap maximum lead distance to prevent overthrows
        MAX_LEAD_DISTANCE = 15.0
        lead_vector = target_pos - receiver.position
        lead_distance = lead_vector.length()

        if lead_distance > MAX_LEAD_DISTANCE:
            scale = MAX_LEAD_DISTANCE / lead_distance
            target_pos = receiver.position + lead_vector * scale

        return target_pos

    def _execute_throw(self, receiver_id: str) -> None:
        """Execute throw to target receiver."""
        qb = self.state.qb
        ball = self.state.ball

        # Find receiver
        target_rcvr = None
        for rcvr in self.state.receivers:
            if rcvr.id == receiver_id:
                target_rcvr = rcvr
                break

        if not target_rcvr:
            return

        qb.animation = QBAnimation.THROWING
        qb.has_thrown = True
        qb.target_receiver_id = receiver_id
        qb.throw_tick = self.state.tick

        # Calculate ball velocity from arm strength (clamped to new constants)
        arm_factor = qb.attributes.arm_strength / 100
        velocity_range = MAX_BALL_VELOCITY - BASE_BALL_VELOCITY  # 0.15 range
        ball.velocity = BASE_BALL_VELOCITY + (arm_factor * velocity_range)
        ball.velocity = min(ball.velocity, MAX_BALL_VELOCITY)  # Clamp to max

        # Calculate target position based on route waypoints (not instant velocity)
        # This handles routes that break/turn correctly
        target_pos = self._predict_receiver_position(target_rcvr, qb.position, ball.velocity)

        # Apply accuracy variance (affected by pressure)
        if self.variance_enabled:
            accuracy_factor = qb.attributes.accuracy / 100
            base_variance = 1.5 * (1 - accuracy_factor)  # 0-1.5 yards variance

            # Pressure increases variance (uses imported helper)
            pressure_multiplier = get_pressure_throw_variance_multiplier(self._pressure_clock)
            variance_sigma = base_variance * pressure_multiplier

            # Get directional bias from pressure (throws miss away from pressure)
            x_bias, y_bias = self._pressure_clock.get_pressure_direction_bias()
            bias_strength = self._pressure_clock.total_pressure * 1.5  # Scale bias by pressure

            target_pos = Vec2(
                target_pos.x + random.gauss(x_bias * bias_strength, variance_sigma),
                target_pos.y + random.gauss(y_bias * bias_strength, variance_sigma),
            )

        # Set ball state
        ball.is_thrown = True
        ball.start_position = Vec2(qb.position.x, qb.position.y)
        ball.position = Vec2(qb.position.x, qb.position.y)
        ball.target_position = target_pos
        ball.throw_tick = self.state.tick
        ball.target_receiver_id = receiver_id

        # Calculate final arrival tick
        distance = qb.position.distance_to(target_pos)
        travel_ticks = max(1, int(distance / ball.velocity))
        ball.arrival_tick = self.state.tick + travel_ticks

    def _process_ball(self) -> None:
        """Move ball toward target and resolve catch."""
        ball = self.state.ball

        # Check if ball has arrived
        if self.state.tick >= ball.arrival_tick:
            self._resolve_catch()
            return

        # Linear interpolation to target
        total_ticks = ball.arrival_tick - ball.throw_tick
        elapsed = self.state.tick - ball.throw_tick
        t = min(1.0, elapsed / total_ticks) if total_ticks > 0 else 1.0

        ball.position = ball.start_position.lerp(ball.target_position, t)

    def _resolve_catch(self) -> None:
        """Determine catch outcome when ball arrives using probabilistic resolver."""
        ball = self.state.ball

        # Find target receiver
        target_rcvr = None
        for rcvr in self.state.receivers:
            if rcvr.id == ball.target_receiver_id:
                target_rcvr = rcvr
                break

        if not target_rcvr:
            ball.is_incomplete = True
            self.state.play_result = PlayResult.INCOMPLETE
            return

        # Find closest defender to catch point
        closest_defender = None
        closest_dist = float('inf')
        for defender in self.state.defenders:
            dist = defender.position.distance_to(ball.target_position)
            if dist < closest_dist:
                closest_dist = dist
                closest_defender = defender

        # Build catch context for probabilistic resolver
        rcvr_dist = target_rcvr.position.distance_to(ball.target_position)
        air_time = self.state.tick - ball.throw_tick

        # Get coverage rating from closest defender
        defender_coverage = 85  # Default
        if closest_defender:
            if closest_defender.is_in_man:
                defender_coverage = closest_defender.attributes.man_coverage
            else:
                defender_coverage = closest_defender.attributes.zone_coverage

        catch_context = build_catch_context(
            receiver_position=(target_rcvr.position.x, target_rcvr.position.y),
            defender_position=(closest_defender.position.x, closest_defender.position.y) if closest_defender else (100, 100),
            ball_target=(ball.target_position.x, ball.target_position.y),
            receiver_speed=target_rcvr.current_speed,
            defender_speed=closest_defender.current_speed if closest_defender else 0,
            receiver_catch_rating=getattr(target_rcvr.attributes, 'catching', 85),
            defender_coverage_rating=defender_coverage,
            throw_accuracy=self.state.qb.attributes.accuracy / 100,
            ball_velocity=ball.velocity,
            air_time=air_time,
        )

        # Resolve catch using probabilistic resolver
        resolution = self._catch_resolver.resolve(catch_context)

        # Apply result
        if resolution.result == CatchResult.COMPLETE:
            ball.is_caught = True
            ball.position = target_rcvr.position
            self.state.play_result = PlayResult.COMPLETE
        elif resolution.result == CatchResult.INTERCEPTION:
            ball.is_incomplete = True
            ball.intercepted_by_id = closest_defender.id if closest_defender else None
            self.state.play_result = PlayResult.INTERCEPTION
        else:  # INCOMPLETE
            ball.is_incomplete = True
            self.state.play_result = PlayResult.INCOMPLETE

    def _update_matchups(self) -> None:
        """Update separation tracking for each receiver."""
        for rcvr in self.state.receivers:
            closest_defender = None
            min_dist = float('inf')

            for defender in self.state.defenders:
                dist = rcvr.position.distance_to(defender.position)
                if dist < min_dist:
                    min_dist = dist
                    closest_defender = defender

            if closest_defender and rcvr.id in self.state.matchups:
                matchup = self.state.matchups[rcvr.id]
                matchup.defender_id = closest_defender.id
                matchup.separation = min_dist

                if min_dist > self._max_separations.get(rcvr.id, 0):
                    self._max_separations[rcvr.id] = min_dist
                matchup.max_separation = self._max_separations.get(rcvr.id, 0)

    def _check_completion(self) -> None:
        """Check if simulation is complete."""
        # Complete if ball caught or incomplete
        if self.state.ball.is_caught or self.state.ball.is_incomplete:
            self.state.is_complete = True
            self._determine_results()
            return

        # Complete if all routes done and no throw
        all_routes_complete = all(
            rcvr.route_phase == RoutePhase.COMPLETE or rcvr.current_waypoint_idx >= len(rcvr.route)
            for rcvr in self.state.receivers
        )

        if all_routes_complete and not self.state.qb.has_thrown:
            # QB held ball too long - sack/incomplete
            self.state.play_result = PlayResult.INCOMPLETE
            self.state.is_complete = True
            self._determine_results()
            return

        if self.state.tick >= MAX_TICKS:
            # If ball is in flight but hasn't arrived, mark as incomplete
            if self.state.ball.is_thrown and not self.state.ball.is_caught and not self.state.ball.is_incomplete:
                self.state.ball.is_incomplete = True
                self.state.play_result = PlayResult.INCOMPLETE
            self.state.is_complete = True
            self._determine_results()

    def _determine_results(self) -> None:
        """Determine final results for each matchup."""
        for rcvr_id, matchup in self.state.matchups.items():
            max_sep = matchup.max_separation
            final_sep = matchup.separation

            if final_sep < CONTESTED_SEPARATION:
                if max_sep >= OPEN_SEPARATION:
                    matchup.result = "contested"
                else:
                    matchup.result = "covered"
            elif final_sep < OPEN_SEPARATION:
                matchup.result = "contested"
            else:
                matchup.result = "open"

    def run_full(self) -> list[dict]:
        """Run complete simulation."""
        if not self.state:
            self.setup()

        states = [self.state.to_dict()]

        while not self.state.is_complete and self.state.tick < MAX_TICKS:
            self.tick()
            states.append(self.state.to_dict())

        return states
