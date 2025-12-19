"""Orchestrator - Main simulation loop for v2 engine.

The orchestrator coordinates all systems and manages play execution.
It provides WorldState to AI brains and handles phase transitions.

Play Lifecycle:
    1. Setup - Configure players, routes, coverages
    2. Pre-snap - Players at alignments (future: motion, audibles)
    3. Snap - Ball snapped, all systems start
    4. Development - Route running, coverage, pocket, blocking
    5. Resolution - Pass/run resolution, tackle attempts
    6. Post-play - Results compilation

Usage:
    orchestrator = Orchestrator()
    orchestrator.setup_play(offense, defense, play_config)
    result = orchestrator.run()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable, Tuple

from .core.vec2 import Vec2
from .core.entities import Player, Ball, BallState, Team, Position, PlayerAttributes
from .core.field import Field
from .core.clock import Clock
from .core.events import EventBus, Event, EventType
from .physics.movement import MovementProfile, MovementSolver, MovementResult
from .physics.body import BodyModel
from .systems.route_runner import RouteRunner, RouteAssignment
from .systems.coverage import CoverageSystem, CoverageType
from .systems.passing import PassingSystem, ThrowResult, CatchResolution
from .resolution.tackle import TackleResolver, TackleOutcome
from .resolution.move import MoveResolver, MoveOutcome
from .resolution.blocking import BlockResolver, BlockOutcome, BlockType, find_blocking_matchups
from .game_state import PlayHistory, GameSituation


# =============================================================================
# Play Phase
# =============================================================================

class PlayPhase(str, Enum):
    """Current phase of play execution."""
    SETUP = "setup"           # Configuring the play
    PRE_SNAP = "pre_snap"     # At alignments, ready to snap
    SNAP = "snap"             # Ball just snapped (single tick)
    DEVELOPMENT = "development"  # Routes running, pocket forming
    BALL_IN_AIR = "ball_in_air"  # Pass thrown, waiting for resolution
    AFTER_CATCH = "after_catch"  # Receiver caught ball, now running
    RUN_ACTIVE = "run_active"    # Ballcarrier has ball, running (handoff/scramble)
    RESOLUTION = "resolution"    # Play resolving (tackle, catch, etc.)
    POST_PLAY = "post_play"      # Play complete, compiling results


# =============================================================================
# WorldState - What AI brains see
# =============================================================================

@dataclass
class PlayerView:
    """Snapshot of a player visible to AI brains.

    This is what brains see - a view of another player, not full access
    to their internal state.
    """
    id: str
    team: Team
    position: Position
    pos: Vec2
    velocity: Vec2
    facing: Vec2
    has_ball: bool
    is_engaged: bool

    # Derived info
    speed: float = 0.0
    distance: float = 0.0  # Distance from self (filled in by WorldState)

    # Route info (for receivers)
    read_order: int = 0  # QB read progression (1 = first read, 2 = second, etc.)

    @classmethod
    def from_player(cls, player: Player, observer_pos: Optional[Vec2] = None) -> PlayerView:
        """Create view from a player."""
        view = cls(
            id=player.id,
            team=player.team,
            position=player.position,
            pos=player.pos,
            velocity=player.velocity,
            facing=player.facing,
            has_ball=player.has_ball,
            is_engaged=player.is_engaged,
            speed=player.velocity.length(),
        )
        if observer_pos:
            view.distance = player.pos.distance_to(observer_pos)
        return view


@dataclass
class BallView:
    """Ball state visible to AI brains."""
    state: BallState
    pos: Vec2
    carrier_id: Optional[str]
    is_in_flight: bool
    flight_target: Optional[Vec2] = None
    intended_receiver_id: Optional[str] = None
    time_to_arrival: Optional[float] = None

    @classmethod
    def from_ball(cls, ball: Ball, current_time: float) -> BallView:
        """Create view from ball state."""
        time_to_arrival = None
        if ball.is_in_flight:
            elapsed = current_time - ball.flight_start_time
            remaining = ball.flight_duration - elapsed
            time_to_arrival = max(0, remaining)

        return cls(
            state=ball.state,
            pos=ball.position_at_time(current_time),
            carrier_id=ball.carrier_id,
            is_in_flight=ball.is_in_flight,
            flight_target=ball.flight_target if ball.is_in_flight else None,
            intended_receiver_id=ball.intended_receiver_id if ball.is_in_flight else None,
            time_to_arrival=time_to_arrival,
        )


@dataclass
class WorldState:
    """Complete world state passed to AI brains each tick.

    This is the interface between simulation and AI. Brains receive
    this and return decisions. They don't have direct access to
    simulation internals.

    Attributes:
        me: The player this brain controls
        teammates: Other players on same team
        opponents: Players on opposing team
        ball: Ball state
        field: Field reference for geometry
        clock: Current time info
        phase: Current play phase

        # Context-specific data
        assignment: Current assignment (route, coverage target, etc.)
        threats: Nearby threats (defenders for ballcarrier, rushers for QB)
        opportunities: Windows, gaps, open receivers
    """
    # Core state
    me: Player
    teammates: List[PlayerView]
    opponents: List[PlayerView]
    ball: BallView
    field: Field

    # Time
    current_time: float
    tick: int
    dt: float  # Time delta for this tick

    # Play context
    phase: PlayPhase
    time_since_snap: float = 0.0

    # Assignment info (varies by position)
    assignment: str = ""
    target_id: Optional[str] = None  # Man coverage target, blocking assignment, etc.

    # Route info (for receivers)
    route_target: Optional[Vec2] = None  # Current waypoint target from route system
    route_phase: Optional[str] = None  # release, stem, break, post_break, complete
    at_route_break: bool = False  # Is receiver at the break point?
    route_settles: bool = False  # Does this route settle (curl/hitch) vs continue (slant/go)?

    # Spatial awareness
    threats: List[PlayerView] = field(default_factory=list)
    opportunities: Dict[str, Any] = field(default_factory=dict)

    # Situational
    down: int = 1
    distance: float = 10.0
    los_y: float = 0.0  # Line of scrimmage Y position

    # Game-level state (persists across plays)
    play_history: Optional[PlayHistory] = None
    game_situation: Optional[GameSituation] = None

    # Convenience methods
    def get_teammate(self, player_id: str) -> Optional[PlayerView]:
        """Get a specific teammate by ID."""
        for t in self.teammates:
            if t.id == player_id:
                return t
        return None

    def get_opponent(self, player_id: str) -> Optional[PlayerView]:
        """Get a specific opponent by ID."""
        for o in self.opponents:
            if o.id == player_id:
                return o
        return None

    def nearest_threat(self) -> Optional[PlayerView]:
        """Get the closest threat."""
        if not self.threats:
            return None
        return min(self.threats, key=lambda t: t.distance)

    def ball_carrier(self) -> Optional[PlayerView]:
        """Get the ball carrier if any."""
        if self.ball.carrier_id:
            if self.ball.carrier_id == self.me.id:
                return None  # That's me
            # Check teammates
            for t in self.teammates:
                if t.id == self.ball.carrier_id:
                    return t
            # Check opponents
            for o in self.opponents:
                if o.id == self.ball.carrier_id:
                    return o
        return None


# =============================================================================
# Brain Decision - What AI brains return
# =============================================================================

@dataclass
class BrainDecision:
    """Decision returned by an AI brain.

    Brains can request movement, specify intent, and add context
    for logging/debugging.

    Attributes:
        move_target: Where to move (position or direction)
        move_type: Type of movement (sprint, backpedal, strafe, etc.)
        intent: High-level intent (cover, pursue, block, route, etc.)
        action: Specific action to take (throw, catch, tackle, etc.)
        target_id: Target player for actions
        reasoning: Debug string explaining decision
    """
    # Movement
    move_target: Optional[Vec2] = None
    move_type: str = "run"  # run, sprint, backpedal, strafe, coast

    # Intent
    intent: str = ""  # cover, pursue, block, route, scramble, etc.

    # Actions (one-shot decisions)
    action: Optional[str] = None  # throw, handoff, attempt_catch, tackle, juke, spin
    action_target: Optional[Vec2] = None  # Target position for action
    target_id: Optional[str] = None  # Target player for action

    # Debug
    reasoning: str = ""

    # Pre-snap adjustments (QB only)
    hot_routes: Optional[Dict[str, str]] = None  # player_id -> new_route_name
    protection_call: Optional[str] = None  # MIKE identification, slide direction

    @classmethod
    def hold(cls, reasoning: str = "holding position") -> BrainDecision:
        """Create a decision to hold current position."""
        return cls(move_target=None, intent="hold", reasoning=reasoning)

    @classmethod
    def move_to(cls, target: Vec2, intent: str = "move", reasoning: str = "") -> BrainDecision:
        """Create a simple movement decision."""
        return cls(move_target=target, intent=intent, reasoning=reasoning)


# =============================================================================
# Play Configuration
# =============================================================================

@dataclass
class PlayConfig:
    """Configuration for setting up a play.

    This defines what routes to run, what coverage to use, etc.
    The orchestrator uses this to configure systems before snap.
    """
    # Routes (receiver_id -> route_type)
    routes: Dict[str, str] = field(default_factory=dict)

    # Coverage assignments (defender_id -> target_id or zone)
    man_assignments: Dict[str, str] = field(default_factory=dict)
    zone_assignments: Dict[str, str] = field(default_factory=dict)

    # Timing
    max_duration: float = 10.0  # Max play duration in seconds

    # QB settings
    throw_timing: Optional[float] = None  # When to throw (if scripted)
    throw_target: Optional[str] = None  # Who to throw to (if scripted)

    # Flags
    is_run_play: bool = False
    run_direction: str = ""  # e.g., "outside_left", "inside_right"


@dataclass
class PlayResult:
    """Result of a completed play.

    Contains outcome, statistics, and full event log.
    """
    # Outcome
    outcome: str  # complete, incomplete, interception, sack, run, fumble
    yards_gained: float = 0.0

    # Key events
    throw_time: Optional[float] = None
    catch_time: Optional[float] = None
    catch_position: Optional[Vec2] = None
    down_position: Optional[Vec2] = None

    # Stats
    duration: float = 0.0
    tick_count: int = 0
    air_yards: float = 0.0
    yac: float = 0.0  # Yards after catch

    # Participants
    passer_id: Optional[str] = None
    receiver_id: Optional[str] = None
    tackler_id: Optional[str] = None

    # Full log
    events: List[Event] = field(default_factory=list)

    def format_summary(self) -> str:
        """Format a one-line summary."""
        if self.outcome == "complete":
            return f"Complete to {self.receiver_id} for {self.yards_gained:.0f} yards ({self.air_yards:.0f} air + {self.yac:.0f} YAC)"
        elif self.outcome == "incomplete":
            return f"Incomplete intended for {self.receiver_id}"
        elif self.outcome == "interception":
            return f"Intercepted by {self.tackler_id}"
        elif self.outcome == "sack":
            return f"Sacked for {abs(self.yards_gained):.0f} yard loss"
        else:
            return f"{self.outcome}: {self.yards_gained:.0f} yards"


# =============================================================================
# Orchestrator
# =============================================================================

# Type alias for brain functions
BrainFunc = Callable[[WorldState], BrainDecision]


class Orchestrator:
    """Main simulation orchestrator.

    Coordinates all systems and runs the main tick loop.
    Provides WorldState to AI brains and processes their decisions.

    Usage:
        orch = Orchestrator()
        orch.setup_play(offense, defense, config)
        orch.register_brain("QB1", qb_brain_func)
        result = orch.run()
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        # Core components
        self.clock = Clock()
        self.event_bus = event_bus or EventBus()
        self.field = Field()

        # Players
        self.offense: List[Player] = []
        self.defense: List[Player] = []
        self.ball = Ball()

        # Systems
        self.route_runner = RouteRunner(self.event_bus)
        self.coverage_system = CoverageSystem(self.event_bus)
        self.passing_system = PassingSystem(self.event_bus)
        self.tackle_resolver = TackleResolver(self.event_bus)
        self.move_resolver = MoveResolver(self.event_bus)
        self.block_resolver = BlockResolver(self.event_bus)
        self.movement_solver = MovementSolver()

        # Game-level state (persists across plays)
        self.play_history = PlayHistory()
        self.game_situation: Optional[GameSituation] = None

        # Movement profiles cache
        self._profiles: Dict[str, MovementProfile] = {}

        # AI brains (player_id -> brain function)
        self._brains: Dict[str, BrainFunc] = {}

        # State
        self.phase = PlayPhase.SETUP
        self.snap_time: Optional[float] = None  # None = no snap yet, 0.0 = snapped at t=0
        self.los_y: float = 0.0  # Line of scrimmage

        # Configuration
        self.config: Optional[PlayConfig] = None
        self.max_ticks: int = 200

        # Tracking for results
        self._throw_time: Optional[float] = None
        self._throw_position: Optional[Vec2] = None
        self._result_outcome: Optional[str] = None
        self._down_position: Optional[Vec2] = None

        # Tackle immunity after successful moves (player_id -> immune_until_time)
        self._tackle_immunity: Dict[str, float] = {}

        # Subscribe to key events
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Subscribe to events we need to track."""
        self.event_bus.subscribe(EventType.THROW, self._on_throw)
        self.event_bus.subscribe(EventType.CATCH, self._on_catch)
        self.event_bus.subscribe(EventType.INCOMPLETE, self._on_incomplete)
        self.event_bus.subscribe(EventType.INTERCEPTION, self._on_interception)
        self.event_bus.subscribe(EventType.TACKLE, self._on_tackle)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_throw(self, event: Event) -> None:
        """Handle throw event."""
        self._throw_time = event.time
        self.phase = PlayPhase.BALL_IN_AIR

    def _on_catch(self, event: Event) -> None:
        """Handle catch event."""
        self._result_outcome = "complete"
        # Give some time for YAC before ending
        # In full implementation, would continue to RUN_ACTIVE

    def _on_incomplete(self, event: Event) -> None:
        """Handle incomplete pass."""
        self._result_outcome = "incomplete"
        self.phase = PlayPhase.POST_PLAY

    def _on_interception(self, event: Event) -> None:
        """Handle interception."""
        self._result_outcome = "interception"
        self.phase = PlayPhase.POST_PLAY

    def _on_tackle(self, event: Event) -> None:
        """Handle tackle."""
        self._down_position = event.data.get("position")
        self.phase = PlayPhase.POST_PLAY

    # =========================================================================
    # Setup
    # =========================================================================

    def setup_play(
        self,
        offense: List[Player],
        defense: List[Player],
        config: PlayConfig,
        los_y: float = 0.0,
    ) -> None:
        """Set up a play for execution.

        Args:
            offense: Offensive players at their alignments
            defense: Defensive players at their alignments
            config: Play configuration (routes, coverages, etc.)
            los_y: Line of scrimmage Y position
        """
        self.offense = offense
        self.defense = defense
        self.config = config
        self.los_y = los_y

        # Ensure team assignments are correct
        for p in offense:
            p.team = Team.OFFENSE
        for p in defense:
            p.team = Team.DEFENSE

        # Clear state from previous play
        self._profiles.clear()
        self.block_resolver.clear_engagements()

        # Build movement profiles
        for p in offense + defense:
            self._profiles[p.id] = MovementProfile.from_attributes(
                speed=p.attributes.speed,
                acceleration=p.attributes.acceleration,
                agility=p.attributes.agility,
            )

        # Find QB and give them the ball
        for p in offense:
            if p.position == Position.QB:
                p.has_ball = True
                self.ball.state = BallState.HELD
                self.ball.carrier_id = p.id
                self.ball.pos = p.pos
                break

        # Setup routes
        from .plays.routes import RouteType, get_route
        for receiver_id, route_name in config.routes.items():
            player = self._get_player(receiver_id)
            if player:
                route_type = RouteType(route_name.lower())
                route = get_route(route_type)
                # Determine side
                is_left = player.pos.x < 0
                self.route_runner.assign_route(player, route, player.pos, is_left)

        # Setup man coverage
        for defender_id, target_id in config.man_assignments.items():
            player = self._get_player(defender_id)
            if player:
                self.coverage_system.assign_man_coverage(player, target_id, player.pos)

        # Setup zone coverage
        from .systems.coverage import ZoneType
        for defender_id, zone_name in config.zone_assignments.items():
            player = self._get_player(defender_id)
            if player:
                zone_type = ZoneType(zone_name.lower())
                self.coverage_system.assign_zone_coverage(player, zone_type, player.pos)

        # Reset state
        self.clock = Clock()
        self.event_bus.clear_history()
        self.phase = PlayPhase.PRE_SNAP
        self.snap_time = None
        self._throw_time = None
        self._throw_position = None
        self._result_outcome = None
        self._down_position = None
        self.max_ticks = int(config.max_duration * 20)  # 20 ticks/sec

    def register_brain(self, player_id: str, brain_func: BrainFunc) -> None:
        """Register an AI brain for a player.

        Args:
            player_id: ID of the player
            brain_func: Function that takes WorldState, returns BrainDecision
        """
        self._brains[player_id] = brain_func

    def clear_brains(self) -> None:
        """Remove all registered brains."""
        self._brains.clear()

    # =========================================================================
    # WorldState Construction
    # =========================================================================

    def _build_world_state(self, player: Player, dt: float) -> WorldState:
        """Build WorldState for a specific player.

        Each player gets a personalized view of the world from their
        perspective.
        """
        my_pos = player.pos
        is_offense = player.team == Team.OFFENSE

        # Build teammate and opponent lists
        my_team = self.offense if is_offense else self.defense
        other_team = self.defense if is_offense else self.offense

        teammates = []
        for p in my_team:
            if p.id != player.id:
                view = PlayerView.from_player(p, my_pos)
                # Add read_order from route assignments (for QB to know read progression)
                route_assign = self.route_runner.get_assignment(p.id)
                if route_assign:
                    view.read_order = route_assign.read_order
                teammates.append(view)

        opponents = [
            PlayerView.from_player(p, my_pos)
            for p in other_team
        ]

        # Build threats (opponents within relevant range)
        threat_range = 15.0  # yards
        threats = [o for o in opponents if o.distance < threat_range]
        threats.sort(key=lambda t: t.distance)

        # Ball view
        ball_view = BallView.from_ball(self.ball, self.clock.current_time)

        # Assignment info
        assignment = player.assignment
        target_id = player.target_id

        # Route assignment if receiver
        route_assignment = self.route_runner.get_assignment(player.id)
        route_target = None
        route_phase = None
        at_route_break = False
        route_settles = False

        if route_assignment:
            # Check if player arrived at current waypoint and advance if so
            # This is needed when brain controls movement but route system tracks progress
            self.route_runner.check_waypoint_arrival(player)

            assignment = f"route:{route_assignment.route.name}"
            route_target = route_assignment.current_target
            route_phase = route_assignment.phase.value if route_assignment.phase else None
            at_route_break = route_assignment.is_at_break
            route_settles = route_assignment.route.settles

        # Coverage assignment if defender
        cov_assignment = self.coverage_system.get_assignment(player.id)
        if cov_assignment:
            if cov_assignment.coverage_type == CoverageType.MAN:
                assignment = f"man:{cov_assignment.man_target_id}"
                target_id = cov_assignment.man_target_id
            else:
                assignment = f"zone:{cov_assignment.zone_type.value}"

        return WorldState(
            me=player,
            teammates=teammates,
            opponents=opponents,
            ball=ball_view,
            field=self.field,
            current_time=self.clock.current_time,
            tick=self.clock.tick_count,
            dt=dt,
            phase=self.phase,
            time_since_snap=self.clock.current_time - self.snap_time if self.snap_time is not None else 0,
            assignment=assignment,
            target_id=target_id,
            threats=threats,
            los_y=self.los_y,
            # Route info
            route_target=route_target,
            route_phase=route_phase,
            at_route_break=at_route_break,
            route_settles=route_settles,
            # Game-level state
            play_history=self.play_history,
            game_situation=self.game_situation,
        )

    # =========================================================================
    # Main Loop
    # =========================================================================

    def run(self, verbose: bool = False) -> PlayResult:
        """Run the play to completion.

        Returns:
            PlayResult with outcome, stats, and event log
        """
        if self.phase != PlayPhase.PRE_SNAP:
            raise RuntimeError("Must call setup_play() before run()")

        # Emit play start
        self.event_bus.emit_simple(
            EventType.PLAY_START,
            self.clock.tick_count,
            self.clock.current_time,
            description="Play beginning",
        )

        # Pre-snap reads (QB reads defense, calls hot routes)
        self._do_pre_snap_reads()

        # Snap
        self._do_snap()

        # Main loop
        while not self._should_stop():
            dt = self.clock.tick()
            self._update_tick(dt, verbose)

        # Compile result
        return self._compile_result()

    def _do_pre_snap_reads(self) -> None:
        """Execute pre-snap reads and adjustments.

        Gives QB a chance to read the defense and make adjustments
        (hot routes, protection calls) before the snap.
        """
        # Find QB
        qb = None
        for p in self.offense:
            if p.position == Position.QB:
                qb = p
                break

        if not qb:
            return  # No QB, skip pre-snap reads

        # Check if QB has a brain registered
        qb_brain = self._get_brain_for_player(qb)
        if not qb_brain:
            return  # No QB brain, skip

        # Build pre-snap WorldState for QB
        # Use dt=0 since we're not moving yet
        world = self._build_world_state(qb, dt=0.0)

        # Call QB brain for pre-snap decision
        try:
            decision = qb_brain(world)
        except Exception as e:
            # Log error but don't crash
            self.event_bus.emit_simple(
                EventType.ERROR,
                self.clock.tick_count,
                self.clock.current_time,
                description=f"Pre-snap QB brain error: {e}",
            )
            return

        # Apply hot routes
        if decision.hot_routes:
            for player_id, new_route_name in decision.hot_routes.items():
                player = self._get_player(player_id)
                if player and player.team == Team.OFFENSE:
                    # Update route assignment
                    self._apply_hot_route(player, new_route_name)

                    self.event_bus.emit_simple(
                        EventType.HOT_ROUTE,
                        self.clock.tick_count,
                        self.clock.current_time,
                        player_id=player_id,
                        new_route=new_route_name,
                        description=f"Hot route: {player_id} → {new_route_name}",
                    )

        # Apply protection call (for OL coordination)
        if decision.protection_call:
            self._apply_protection_call(decision.protection_call)

    def _apply_hot_route(self, player: Player, new_route_name: str) -> None:
        """Apply a hot route change to a receiver."""
        from .plays.routes import RouteType

        try:
            new_route_type = RouteType[new_route_name.upper()]
        except KeyError:
            # Invalid route name, ignore
            return

        # Update route assignment
        # The route_runner will use this when routes start
        self.route_runner.change_route(player.id, new_route_type)

    def _apply_protection_call(self, call: str) -> None:
        """Apply a protection call for OL."""
        # Store protection call for OL brains to read
        # This will be available via WorldState or a shared state
        self._protection_call = call

    def _do_snap(self) -> None:
        """Execute the snap."""
        self.phase = PlayPhase.SNAP
        self.snap_time = self.clock.current_time

        self.event_bus.emit_simple(
            EventType.SNAP,
            self.clock.tick_count,
            self.clock.current_time,
            description="Ball snapped",
        )

        # Start all routes
        self.route_runner.start_all_routes(self.clock)

        # Start coverage
        self.coverage_system.start_coverage(self.clock)

        # Advance to development
        self.phase = PlayPhase.DEVELOPMENT

    def _update_tick(self, dt: float, verbose: bool = False) -> None:
        """Update one simulation tick."""

        # Update all players
        for player in self.offense + self.defense:
            self._update_player(player, dt)

        # Update ball position if in flight
        if self.ball.is_in_flight:
            self.ball.pos = self.ball.position_at_time(self.clock.current_time)

            # Check for arrival
            if self.ball.has_arrived(self.clock.current_time):
                self._resolve_pass()

        # Resolve OL/DL blocking engagements
        # Include BALL_IN_AIR - linemen don't instantly disengage when pass is thrown
        if self.phase in (PlayPhase.DEVELOPMENT, PlayPhase.RUN_ACTIVE, PlayPhase.BALL_IN_AIR):
            self._resolve_blocks(dt)

        # Check for tackle opportunities when there's a ballcarrier
        if self.ball.state == BallState.HELD and self.ball.carrier_id:
            self._check_tackles()

        # Handle scripted throw timing (for testing)
        if (self.config and self.config.throw_timing and
            self.phase == PlayPhase.DEVELOPMENT and
            self.snap_time is not None and
            self.clock.current_time - self.snap_time >= self.config.throw_timing):

            if self.config.throw_target:
                self._do_scripted_throw(self.config.throw_target)

        if verbose:
            self._print_tick_state()

    def _update_player(self, player: Player, dt: float) -> None:
        """Update a single player for one tick."""
        profile = self._profiles.get(player.id)
        if not profile:
            return

        # Get the appropriate brain for this player's current situation
        brain = self._get_brain_for_player(player)

        if brain:
            world_state = self._build_world_state(player, dt)
            decision = brain(world_state)
            self._apply_brain_decision(player, decision, profile, dt)
            return

        # Default system-driven behavior
        if player.team == Team.OFFENSE:
            self._update_offense_player(player, profile, dt)
        else:
            self._update_defense_player(player, profile, dt)

    def _get_brain_for_player(self, player: Player) -> Optional[BrainFunc]:
        """Get the appropriate brain for a player based on their situation.

        Supports both explicit player-specific brains and role-based auto-switching.
        """
        # Check for explicit player-specific brain first
        if player.id in self._brains:
            brain = self._brains[player.id]

            # Auto-switch ballcarrier brain when player has ball (unless it's a QB brain)
            # AFTER_CATCH = receiver with ball after catch (YAC situation)
            # RUN_ACTIVE = designed run or scramble
            ballcarrier_phases = (PlayPhase.RUN_ACTIVE, PlayPhase.AFTER_CATCH)
            if player.has_ball and self.phase in ballcarrier_phases:
                # Check if we have a ballcarrier brain registered
                if "ballcarrier" in self._brains:
                    return self._brains["ballcarrier"]
                # Otherwise use the player's brain (it should handle ballcarrying)

            return brain

        # Check for role-based brains
        ballcarrier_phases = (PlayPhase.RUN_ACTIVE, PlayPhase.AFTER_CATCH)
        if player.has_ball and self.phase in ballcarrier_phases:
            if "ballcarrier" in self._brains:
                return self._brains["ballcarrier"]

        # Position-based role brains
        role_key = f"role:{player.position.value}"
        if role_key in self._brains:
            return self._brains[role_key]

        return None

    def _update_offense_player(self, player: Player, profile: MovementProfile, dt: float) -> None:
        """Update offensive player using systems."""
        # QB holds position (for now - pocket system will handle this)
        if player.position == Position.QB:
            return

        # Ballcarrier runs upfield (simple behavior when no brain)
        # AFTER_CATCH = receiver with ball after catch (YAC situation)
        # RUN_ACTIVE = designed run or scramble
        ballcarrier_phases = (PlayPhase.RUN_ACTIVE, PlayPhase.AFTER_CATCH)
        if player.has_ball and self.phase in ballcarrier_phases:
            self._run_with_ball(player, profile, dt)
            return

        # Route runners use route system
        if self.route_runner.get_assignment(player.id) is not None:
            result, reasoning = self.route_runner.update(player, profile, dt, self.clock)
            self._apply_movement_result(player, result)
            player.set_decision("route", reasoning)

    def _run_with_ball(self, player: Player, profile: MovementProfile, dt: float) -> None:
        """Simple ballcarrier behavior - run upfield."""
        # Just run straight upfield for now
        # Real ballcarrier brain will be much smarter
        target = player.pos + Vec2(0, 10)  # 10 yards upfield

        result = self.movement_solver.solve(
            current_pos=player.pos,
            current_vel=player.velocity,
            target_pos=target,
            profile=profile,
            dt=dt,
        )
        self._apply_movement_result(player, result)
        player.set_decision("run", "Running upfield")

    def _update_defense_player(self, player: Player, profile: MovementProfile, dt: float) -> None:
        """Update defensive player using systems."""
        # When ball is caught or run play, switch to pursuit mode
        # AFTER_CATCH = receiver has ball after catching pass (YAC situation)
        # RUN_ACTIVE = designed run or scramble
        pursuit_phases = (PlayPhase.RUN_ACTIVE, PlayPhase.AFTER_CATCH)
        if self.phase in pursuit_phases and self.ball.carrier_id:
            self._pursue_ballcarrier(player, profile, dt)
            return

        # Coverage system handles DBs
        if self.coverage_system.get_assignment(player.id) is not None:
            result, reasoning = self.coverage_system.update(
                player, profile, self.offense, dt, self.clock
            )
            self._apply_movement_result(player, result)
            player.set_decision("coverage", reasoning)

    def _pursue_ballcarrier(self, player: Player, profile: MovementProfile, dt: float) -> None:
        """Simple pursuit - run toward ballcarrier with intercept angle."""
        ballcarrier = self._get_player(self.ball.carrier_id)
        if not ballcarrier:
            return

        # Calculate intercept point (lead the ballcarrier)
        bc_pos = ballcarrier.pos
        bc_vel = ballcarrier.velocity
        my_speed = profile.max_speed

        # Simple intercept: aim ahead of ballcarrier
        if bc_vel.length() > 0.5:
            # Time to reach current position
            dist = player.pos.distance_to(bc_pos)
            time_to_reach = dist / my_speed if my_speed > 0 else 1.0

            # Where will ballcarrier be?
            future_pos = bc_pos + bc_vel * time_to_reach * 0.7  # Don't overshoot
            target = future_pos
        else:
            target = bc_pos

        # Move toward target
        result = self.movement_solver.solve(
            current_pos=player.pos,
            current_vel=player.velocity,
            target_pos=target,
            profile=profile,
            dt=dt,
        )
        self._apply_movement_result(player, result)
        player.set_decision("pursuit", f"Pursuing {ballcarrier.name}")

    # Movement type speed modifiers
    MOVE_TYPE_SPEED = {
        "sprint": 1.0,
        "run": 0.85,
        "backpedal": 0.55,
        "strafe": 0.65,
        "coast": 0.5,
    }

    # Move actions that trigger the move resolver
    EVASION_MOVES = {"juke", "spin", "truck", "stiff_arm", "hurdle", "dead_leg", "cut", "speed_burst"}

    def _apply_brain_decision(
        self,
        player: Player,
        decision: BrainDecision,
        profile: MovementProfile,
        dt: float,
    ) -> None:
        """Apply an AI brain's decision to a player."""
        player.set_decision(decision.intent, decision.reasoning)

        # Store action for block resolution to use
        player._last_action = decision.action

        # Handle throw action
        if decision.action == "throw" and player.has_ball:
            if decision.target_id:
                self._do_throw(player, decision.target_id, decision.action_target)
            return

        # Handle evasion moves
        if decision.action in self.EVASION_MOVES and player.has_ball:
            self._resolve_move(player, decision, profile, dt)
            return

        # Handle movement with speed modifiers
        if decision.move_target:
            # Apply movement type speed modifier
            speed_mod = self.MOVE_TYPE_SPEED.get(decision.move_type, 0.85)
            modified_profile = MovementProfile(
                max_speed=profile.max_speed * speed_mod,
                acceleration=profile.acceleration * speed_mod,
                deceleration=profile.deceleration,
                cut_speed_retention=profile.cut_speed_retention,
                cut_angle_threshold=profile.cut_angle_threshold,
            )

            result = self.movement_solver.solve(
                current_pos=player.pos,
                current_vel=player.velocity,
                target_pos=decision.move_target,
                profile=modified_profile,
                dt=dt,
            )
            self._apply_movement_result(player, result)

    def _resolve_move(
        self,
        player: Player,
        decision: BrainDecision,
        profile: MovementProfile,
        dt: float,
    ) -> None:
        """Resolve an evasion move attempt.

        The brain has already decided to attempt this move - we just resolve the outcome.
        No second-guessing the brain's decision here.
        """
        # Find the target defender (from brain's decision or nearest)
        defender = None
        if decision.target_id:
            defender = self._get_player(decision.target_id)

        if not defender:
            # Find nearest defender
            nearest_dist = float('inf')
            for d in self.defense:
                dist = player.pos.distance_to(d.pos)
                if dist < nearest_dist:
                    nearest_dist = dist
                    defender = d

        if not defender:
            # No defenders at all - just move normally
            if decision.move_target:
                result = self.movement_solver.solve(
                    current_pos=player.pos,
                    current_vel=player.velocity,
                    target_pos=decision.move_target,
                    profile=profile,
                    dt=dt,
                )
                self._apply_movement_result(player, result)
            return

        # Create and resolve move attempt
        attempt = self.move_resolver.create_attempt(player, defender, decision.action)
        result = self.move_resolver.resolve(
            attempt, player, defender,
            tick=self.clock.tick_count,
            time=self.clock.current_time,
        )

        # Apply outcome
        if result.outcome == MoveOutcome.SUCCESS:
            # Grant tackle immunity for 0.3 seconds (6 ticks) after breaking tackle
            self._tackle_immunity[player.id] = self.clock.current_time + 0.3

            # Broke free! Apply direction change and speed
            if result.new_direction and decision.move_target:
                # Blend desired target with successful move direction
                target = player.pos + result.new_direction * 5
            elif decision.move_target:
                target = decision.move_target
            else:
                target = player.pos + Vec2(0, 5)

            modified_profile = MovementProfile(
                max_speed=profile.max_speed * result.speed_retained,
                acceleration=profile.acceleration,
                deceleration=profile.deceleration,
                cut_speed_retention=profile.cut_speed_retention,
                cut_angle_threshold=profile.cut_angle_threshold,
            )

            move_result = self.movement_solver.solve(
                current_pos=player.pos,
                current_vel=player.velocity,
                target_pos=target,
                profile=modified_profile,
                dt=dt,
            )
            self._apply_movement_result(player, move_result)

        elif result.outcome == MoveOutcome.PARTIAL:
            # Avoided tackle but slowed significantly
            player.velocity = player.velocity * result.speed_retained
            player.current_speed = player.velocity.length()

        elif result.outcome == MoveOutcome.FAILED:
            # Tackled - the tackle check will handle this
            player.velocity = Vec2.zero()
            player.current_speed = 0

        elif result.outcome == MoveOutcome.FUMBLE:
            # Fumble! Ball is loose
            player.has_ball = False
            self.ball.state = BallState.LOOSE
            self.ball.carrier_id = None
            self.ball.pos = result.fumble_pos or player.pos
            # TODO: Fumble recovery logic

    def _apply_movement_result(self, player: Player, result: MovementResult) -> None:
        """Apply a movement result to a player."""
        player.pos = result.new_pos
        player.velocity = result.new_vel
        player.current_speed = result.speed_after
        if result.new_vel.length() > 0.1:
            player.facing = result.new_vel.normalized()

    # =========================================================================
    # Throwing
    # =========================================================================

    def _do_throw(
        self,
        qb: Player,
        target_id: str,
        target_pos: Optional[Vec2] = None,
    ) -> None:
        """Execute a throw."""
        receiver = self._get_player(target_id)
        if not receiver:
            return

        # Execute throw using passing system
        throw_result = self.passing_system.throw_ball(
            ball=self.ball,
            thrower=qb,
            target_receiver=receiver,
            clock=self.clock,
            anticipated_target_pos=target_pos,
        )

        # Update QB state
        qb.has_ball = False

        self._throw_time = self.clock.current_time
        self._throw_position = qb.pos
        self.phase = PlayPhase.BALL_IN_AIR

    def _do_scripted_throw(self, target_id: str) -> None:
        """Execute a scripted throw for testing."""
        qb = None
        for p in self.offense:
            if p.position == Position.QB and p.has_ball:
                qb = p
                break

        if qb:
            self._do_throw(qb, target_id)
            # Clear the config so we don't throw again
            if self.config:
                self.config.throw_timing = None

    def _resolve_pass(self) -> None:
        """Resolve a pass that has arrived.

        Uses the passing system's update method which handles catch resolution.
        """
        # Let the passing system resolve the catch
        # It will update ball state and emit appropriate events
        resolution = self.passing_system.update(
            ball=self.ball,
            receivers=self.offense,
            defenders=self.defense,
            clock=self.clock,
            dt=0.05,  # Standard tick
        )

        if resolution is None:
            # Ball hasn't arrived yet (shouldn't happen if we check has_arrived first)
            return

        # Map CatchResult to our outcome strings
        from .systems.passing import CatchResult

        if resolution.result == CatchResult.COMPLETE:
            # Ball state already updated by passing system
            receiver = self._get_player(self.ball.carrier_id) if self.ball.carrier_id else None
            if receiver:
                receiver.has_ball = True
            self._result_outcome = "complete"
            # Transition to AFTER_CATCH for YAC
            self.phase = PlayPhase.AFTER_CATCH

        elif resolution.result == CatchResult.INTERCEPTION:
            # Ball state updated by passing system
            interceptor = self._get_player(self.ball.carrier_id) if self.ball.carrier_id else None
            if interceptor:
                interceptor.has_ball = True
            self._result_outcome = "interception"
            self.phase = PlayPhase.POST_PLAY

        else:  # INCOMPLETE
            self._result_outcome = "incomplete"
            self.phase = PlayPhase.POST_PLAY

    # =========================================================================
    # Block Resolution
    # =========================================================================

    def _resolve_blocks(self, dt: float) -> None:
        """Resolve all OL/DL blocking engagements."""
        # Find blocking matchups
        matchups = find_blocking_matchups(self.offense, self.defense)

        for ol, dl in matchups:
            # Skip if not in range
            if not self.block_resolver.is_engaged(ol, dl):
                continue

            # Get their actions from brain decisions (stored as last_intent)
            ol_action = getattr(ol, '_last_action', 'anchor')
            dl_action = getattr(dl, '_last_action', 'bull_rush')

            # Determine block type based on phase
            if self.phase == PlayPhase.RUN_ACTIVE:
                block_type = BlockType.RUN_BLOCK
            else:
                block_type = BlockType.PASS_PRO

            # Resolve the block
            result = self.block_resolver.resolve(
                ol, dl,
                ol_action, dl_action,
                block_type, dt,
                tick=self.clock.tick_count,
                time=self.clock.current_time,
            )

            # Apply movement from block resolution
            # This overrides their brain's requested movement
            ol.pos = result.ol_new_pos
            dl.pos = result.dl_new_pos

            # Track engagement state
            if result.outcome == BlockOutcome.DL_SHED:
                dl.is_engaged = False
                ol.is_engaged = False
            elif result.outcome != BlockOutcome.DISENGAGED:
                dl.is_engaged = True
                ol.is_engaged = True

    # =========================================================================
    # Tackle Resolution
    # =========================================================================

    def _check_tackles(self) -> None:
        """Check for tackle opportunities and resolve them."""
        # Find ballcarrier
        ballcarrier = self._get_player(self.ball.carrier_id) if self.ball.carrier_id else None
        if not ballcarrier:
            return

        # Check tackle immunity (from successful moves)
        immune_until = self._tackle_immunity.get(ballcarrier.id, 0)
        if self.clock.current_time < immune_until:
            return  # Still has immunity from breaking a tackle

        # Skip if QB still in pocket (hasn't scrambled)
        if ballcarrier.position == Position.QB and self.phase == PlayPhase.DEVELOPMENT:
            # QB is protected until they scramble or we add pocket collapse
            return

        # Determine which team is tackling
        if ballcarrier.team == Team.OFFENSE:
            tacklers = self.defense
        else:
            tacklers = self.offense

        # Find tackle attempts
        attempts = self.tackle_resolver.find_tackle_attempts(ballcarrier, tacklers)

        if not attempts:
            return

        # Only resolve if best attempt is in close range
        # Tackles can happen at 2 yards with a diving attempt
        if attempts[0].distance > 2.0:
            return

        # Resolve the tackle
        result = self.tackle_resolver.resolve(
            attempts,
            tick=self.clock.tick_count,
            time=self.clock.current_time,
        )

        # Handle outcome
        if result.outcome in (TackleOutcome.TACKLED, TackleOutcome.GANG_TACKLED):
            ballcarrier.is_down = True
            self._down_position = ballcarrier.pos
            self._result_outcome = "tackle"
            self.phase = PlayPhase.POST_PLAY

            # Update result tracking
            if self._throw_time:
                # This was a pass play that ended in tackle
                self._result_outcome = "complete"

        elif result.outcome == TackleOutcome.FUMBLE:
            # Handle fumble
            ballcarrier.has_ball = False
            self.ball.state = BallState.LOOSE

            if result.fumble_recovered_by:
                recoverer = self._get_player(result.fumble_recovered_by)
                if recoverer:
                    recoverer.has_ball = True
                    self.ball.state = BallState.HELD
                    self.ball.carrier_id = result.fumble_recovered_by

                    # If defense recovered, play ends
                    if recoverer.team != ballcarrier.team:
                        self._down_position = recoverer.pos
                        self._result_outcome = "fumble_lost"
                        self.phase = PlayPhase.POST_PLAY
                    else:
                        # Offense recovered, play continues
                        self._result_outcome = "fumble_recovered"

        elif result.outcome in (TackleOutcome.BROKEN, TackleOutcome.STUMBLE):
            # Broken tackle - ballcarrier continues but maybe slowed
            if result.outcome == TackleOutcome.STUMBLE:
                # Slow them down a bit
                ballcarrier.velocity = ballcarrier.velocity * 0.7

        # MISSED doesn't change anything

    # =========================================================================
    # End Conditions
    # =========================================================================

    def _should_stop(self) -> bool:
        """Check if simulation should stop."""
        # Explicit end
        if self.phase == PlayPhase.POST_PLAY:
            return True

        # Timeout
        if self.clock.tick_count >= self.max_ticks:
            self._result_outcome = "timeout"
            return True

        return False

    # =========================================================================
    # Results
    # =========================================================================

    def _compile_result(self) -> PlayResult:
        """Compile the play result."""
        result = PlayResult(
            outcome=self._result_outcome or "unknown",
            duration=self.clock.current_time,
            tick_count=self.clock.tick_count,
            events=list(self.event_bus.history),
        )

        # Calculate yards
        # Incomplete passes = 0 yards
        if self._result_outcome == "incomplete":
            result.yards_gained = 0.0
        elif self._down_position:
            result.down_position = self._down_position
            result.yards_gained = self._down_position.y - self.los_y
        elif self.ball.carrier_id:
            carrier = self._get_player(self.ball.carrier_id)
            if carrier:
                result.down_position = carrier.pos
                result.yards_gained = carrier.pos.y - self.los_y

        # Air yards and YAC
        if self._throw_position and self._result_outcome == "complete":
            receiver = self._get_player(self.ball.carrier_id) if self.ball.carrier_id else None
            if receiver and self.ball.flight_target:
                result.air_yards = self.ball.flight_target.y - self.los_y
                result.yac = result.yards_gained - result.air_yards

        # IDs
        result.receiver_id = self.ball.intended_receiver_id
        for p in self.offense:
            if p.position == Position.QB:
                result.passer_id = p.id
                break

        # Record play in history (for tendency tracking)
        self._record_play_history(result)

        return result

    def _record_play_history(self, result: PlayResult) -> None:
        """Record play result in history for tendency tracking."""
        # Determine play type
        if self._throw_time is not None:
            play_type = "pass"
        else:
            play_type = "run"

        # Determine success (positive yards or first down)
        yards = int(result.yards_gained) if result.yards_gained else 0
        success = yards > 0  # Simple for now - could add first down logic

        # Record
        self.play_history.record_play(play_type, success, yards)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID."""
        for p in self.offense + self.defense:
            if p.id == player_id:
                return p
        return None

    def _print_tick_state(self) -> None:
        """Print current state for debugging."""
        print(f"\n[Tick {self.clock.tick_count}] t={self.clock.current_time:.2f}s phase={self.phase.value}")
        print(f"  Ball: {self.ball}")
        for p in self.offense[:3]:  # First 3 offense
            print(f"  {p.format_brief()}")
        for p in self.defense[:2]:  # First 2 defense
            print(f"  {p.format_brief()}")


# =============================================================================
# Convenience Functions
# =============================================================================

def run_quick_scenario(
    receiver_speed: int = 88,
    db_speed: int = 90,
    route_name: str = "slant",
    throw_timing: float = 1.5,
    verbose: bool = False,
) -> PlayResult:
    """Run a quick test scenario.

    Sets up a simple 1-on-1 route vs man coverage with scripted throw.
    Useful for testing and debugging.
    """
    from .plays.routes import RouteType

    # Create players
    qb = Player(
        id="QB1",
        position=Position.QB,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(throw_power=85, throw_accuracy=85),
    )

    wr = Player(
        id="WR1",
        position=Position.WR,
        pos=Vec2(20, 0),
        attributes=PlayerAttributes(
            speed=receiver_speed,
            acceleration=86,
            agility=85,
            route_running=85,
            catching=85,
        ),
    )

    cb = Player(
        id="CB1",
        position=Position.CB,
        pos=Vec2(18, 7),  # Off coverage, shaded inside
        attributes=PlayerAttributes(
            speed=db_speed,
            acceleration=88,
            agility=88,
            man_coverage=80,
        ),
    )

    # Create config
    config = PlayConfig(
        routes={"WR1": route_name},
        man_assignments={"CB1": "WR1"},
        throw_timing=throw_timing,
        throw_target="WR1",
        max_duration=5.0,
    )

    # Run
    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    return orch.run(verbose=verbose)
