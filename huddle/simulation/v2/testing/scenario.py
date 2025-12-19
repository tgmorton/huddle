"""Scenario runner for behavioral testing.

Scenarios are pre-configured situations that can be run and analyzed.
They produce logs and stats for assessing simulation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from ..core.vec2 import Vec2
from ..core.entities import Player, Ball, BallState, Team, Position, PlayerAttributes
from ..core.field import Field
from ..core.clock import Clock
from ..core.events import EventBus, Event, EventType
from ..physics.movement import MovementProfile
from ..physics.body import BodyModel
from ..plays.routes import RouteDefinition, RouteType, get_route

from .logger import PlayLogger


class ScenarioType(str, Enum):
    """Types of test scenarios."""
    # Route running
    ROUTE_VS_AIR = "route_vs_air"           # Receiver runs route, no defender
    ROUTE_VS_MAN = "route_vs_man"           # Receiver vs man coverage
    ROUTE_VS_ZONE = "route_vs_zone"         # Receiver vs zone coverage

    # Passing
    SIMPLE_PASS = "simple_pass"             # QB throws to receiver
    CONTESTED_CATCH = "contested_catch"     # Throw into coverage

    # Coverage
    MAN_COVERAGE_TEST = "man_coverage"      # Test man coverage tracking
    ZONE_COVERAGE_TEST = "zone_coverage"    # Test zone drops and triggers

    # Run game (future)
    HOLE_HIT = "hole_hit"                   # RB hits a gap
    OPEN_FIELD = "open_field"               # Ballcarrier in space

    # Custom
    CUSTOM = "custom"


@dataclass
class ScenarioResult:
    """Result of running a scenario."""
    scenario_name: str
    scenario_type: ScenarioType
    success: bool
    duration: float
    tick_count: int

    # Key metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    # The full log
    logger: Optional[PlayLogger] = None

    # Events that occurred
    events: List[Event] = field(default_factory=list)

    # Notes/observations
    notes: List[str] = field(default_factory=list)

    def add_metric(self, name: str, value: Any) -> None:
        """Add a metric."""
        self.metrics[name] = value

    def add_note(self, note: str) -> None:
        """Add an observation."""
        self.notes.append(note)

    def format_report(self) -> str:
        """Format a human-readable report."""
        lines = [
            "=" * 60,
            f"SCENARIO: {self.scenario_name}",
            f"Type: {self.scenario_type.value}",
            f"Result: {'SUCCESS' if self.success else 'FAILURE'}",
            f"Duration: {self.duration:.2f}s ({self.tick_count} ticks)",
            "=" * 60,
        ]

        if self.metrics:
            lines.append("\nMETRICS:")
            for name, value in self.metrics.items():
                if isinstance(value, float):
                    lines.append(f"  {name}: {value:.3f}")
                else:
                    lines.append(f"  {name}: {value}")

        if self.notes:
            lines.append("\nNOTES:")
            for note in self.notes:
                lines.append(f"  - {note}")

        key_events = [e for e in self.events if e.type.value in
                     {"throw", "catch", "incomplete", "interception", "tackle",
                      "route_break", "route_complete"}]
        if key_events:
            lines.append("\nKEY EVENTS:")
            for e in key_events:
                lines.append(f"  [{e.time:.2f}s] {e.type.value}: {e.description}")

        return "\n".join(lines)


class Scenario:
    """A test scenario that can be run and analyzed."""

    def __init__(
        self,
        name: str,
        scenario_type: ScenarioType = ScenarioType.CUSTOM,
    ):
        self.name = name
        self.scenario_type = scenario_type

        # Components
        self.clock = Clock()
        self.event_bus = EventBus()
        self.field = Field()
        self.logger = PlayLogger()

        # Players
        self.offense: List[Player] = []
        self.defense: List[Player] = []
        self.ball = Ball()

        # Run configuration
        self.max_ticks = 200  # 10 seconds at 20 ticks/sec
        self.stop_conditions: List[Callable[[], bool]] = []

    # =========================================================================
    # Setup helpers
    # =========================================================================

    def add_receiver(
        self,
        id: str,
        pos: Vec2,
        name: str = "",
        speed: int = 88,
        accel: int = 86,
        agility: int = 85,
        route_running: int = 85,
        catching: int = 85,
    ) -> Player:
        """Add a receiver to the scenario."""
        player = Player(
            id=id,
            name=name or id,
            team=Team.OFFENSE,
            position=Position.WR,
            pos=pos,
            attributes=PlayerAttributes(
                speed=speed,
                acceleration=accel,
                agility=agility,
                route_running=route_running,
                catching=catching,
            ),
        )
        body = BodyModel.for_position(Position.WR)
        player.collision_radius = body.collision_radius
        player.tackle_reach = body.tackle_reach
        player.weight = body.weight

        self.offense.append(player)
        return player

    def add_qb(
        self,
        id: str = "QB1",
        pos: Vec2 = None,
        name: str = "QB",
        throw_power: int = 85,
        throw_accuracy: int = 85,
    ) -> Player:
        """Add a QB."""
        if pos is None:
            pos = Vec2(0, -5)  # Shotgun

        player = Player(
            id=id,
            name=name,
            team=Team.OFFENSE,
            position=Position.QB,
            pos=pos,
            has_ball=True,
            attributes=PlayerAttributes(
                throw_power=throw_power,
                throw_accuracy=throw_accuracy,
            ),
        )
        self.offense.append(player)

        # Ball starts with QB
        self.ball.state = BallState.HELD
        self.ball.carrier_id = id
        self.ball.pos = pos

        return player

    def add_db(
        self,
        id: str,
        pos: Vec2,
        name: str = "",
        speed: int = 90,
        accel: int = 88,
        agility: int = 88,
        man_coverage: int = 80,
        zone_coverage: int = 80,
        play_recognition: int = 78,
    ) -> Player:
        """Add a defensive back."""
        player = Player(
            id=id,
            name=name or id,
            team=Team.DEFENSE,
            position=Position.CB,
            pos=pos,
            attributes=PlayerAttributes(
                speed=speed,
                acceleration=accel,
                agility=agility,
                man_coverage=man_coverage,
                zone_coverage=zone_coverage,
                play_recognition=play_recognition,
            ),
        )
        body = BodyModel.for_position(Position.CB)
        player.collision_radius = body.collision_radius
        player.tackle_reach = body.tackle_reach
        player.weight = body.weight

        self.defense.append(player)
        return player

    def add_lb(
        self,
        id: str,
        pos: Vec2,
        name: str = "",
        speed: int = 82,
        play_recognition: int = 80,
        zone_coverage: int = 70,
    ) -> Player:
        """Add a linebacker."""
        player = Player(
            id=id,
            name=name or id,
            team=Team.DEFENSE,
            position=Position.MLB,
            pos=pos,
            attributes=PlayerAttributes(
                speed=speed,
                play_recognition=play_recognition,
                zone_coverage=zone_coverage,
            ),
        )
        self.defense.append(player)
        return player

    def add_stop_condition(self, condition: Callable[[], bool]) -> None:
        """Add a condition that stops the scenario when true."""
        self.stop_conditions.append(condition)

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID."""
        for p in self.offense + self.defense:
            if p.id == player_id:
                return p
        return None

    # =========================================================================
    # Pre-built scenarios
    # =========================================================================

    @classmethod
    def route_vs_air(
        cls,
        route_type: RouteType,
        receiver_speed: int = 88,
        alignment_x: float = 20.0,
    ) -> Scenario:
        """Create a scenario testing a route with no defender."""
        scenario = cls(
            name=f"Route vs Air: {route_type.value}",
            scenario_type=ScenarioType.ROUTE_VS_AIR,
        )

        # Add receiver
        alignment = Vec2(alignment_x, 0)
        scenario.add_receiver(
            id="WR1",
            pos=alignment,
            name="Receiver",
            speed=receiver_speed,
        )

        # No defender

        # Stop when route completes or 4 seconds
        scenario.max_ticks = 80

        return scenario

    @classmethod
    def route_vs_man(
        cls,
        route_type: RouteType,
        receiver_speed: int = 88,
        db_speed: int = 90,
        db_man_coverage: int = 80,
        cushion: float = 7.0,
    ) -> Scenario:
        """Create a scenario testing a route vs man coverage."""
        scenario = cls(
            name=f"Route vs Man: {route_type.value}",
            scenario_type=ScenarioType.ROUTE_VS_MAN,
        )

        alignment_x = 20.0
        alignment = Vec2(alignment_x, 0)

        # Add receiver
        scenario.add_receiver(
            id="WR1",
            pos=alignment,
            name="Receiver",
            speed=receiver_speed,
        )

        # Add DB in off coverage
        scenario.add_db(
            id="CB1",
            pos=Vec2(alignment_x - 2, cushion),  # Shaded inside, 7 yards off
            name="Corner",
            speed=db_speed,
            man_coverage=db_man_coverage,
        )

        scenario.max_ticks = 80

        return scenario

    @classmethod
    def simple_pass(
        cls,
        route_type: RouteType,
        throw_at_time: float = 1.5,
    ) -> Scenario:
        """Create a scenario with QB throwing to receiver."""
        scenario = cls(
            name=f"Simple Pass: {route_type.value}",
            scenario_type=ScenarioType.SIMPLE_PASS,
        )

        # Add QB
        scenario.add_qb(id="QB1", name="Quarterback")

        # Add receiver
        scenario.add_receiver(
            id="WR1",
            pos=Vec2(20, 0),
            name="Receiver",
        )

        scenario.max_ticks = 100

        return scenario

    @classmethod
    def contested_catch(
        cls,
        separation: float = 1.5,
        receiver_catching: int = 85,
        db_coverage: int = 80,
    ) -> Scenario:
        """Create a contested catch scenario."""
        scenario = cls(
            name=f"Contested Catch (sep={separation}yd)",
            scenario_type=ScenarioType.CONTESTED_CATCH,
        )

        # Receiver at catch point
        catch_point = Vec2(15, 12)
        scenario.add_receiver(
            id="WR1",
            pos=catch_point,
            name="Receiver",
            catching=receiver_catching,
        )

        # DB nearby
        scenario.add_db(
            id="CB1",
            pos=Vec2(catch_point.x - separation * 0.7, catch_point.y + separation * 0.7),
            name="Corner",
            man_coverage=db_coverage,
        )

        # QB ready to throw
        scenario.add_qb()

        scenario.max_ticks = 60

        return scenario

    # =========================================================================
    # Run infrastructure (basic - to be enhanced with orchestrator)
    # =========================================================================

    def should_stop(self) -> bool:
        """Check if any stop condition is met."""
        if self.clock.tick_count >= self.max_ticks:
            return True
        for condition in self.stop_conditions:
            if condition():
                return True
        return False

    def log_current_state(self) -> None:
        """Log current tick."""
        # Collect any new events
        recent_events = []  # Would come from event bus in real implementation

        self.logger.log_tick(
            self.clock,
            self.offense,
            self.defense,
            self.ball,
            events=recent_events,
        )

    def get_result(self, success: bool = True) -> ScenarioResult:
        """Package up the result."""
        return ScenarioResult(
            scenario_name=self.name,
            scenario_type=self.scenario_type,
            success=success,
            duration=self.clock.current_time,
            tick_count=self.clock.tick_count,
            logger=self.logger,
            events=list(self.event_bus.history),
        )


# =============================================================================
# Scenario Library
# =============================================================================

def all_route_scenarios() -> List[Scenario]:
    """Generate scenarios for all route types."""
    scenarios = []
    for route_type in [
        RouteType.SLANT, RouteType.HITCH, RouteType.CURL,
        RouteType.OUT, RouteType.IN, RouteType.POST,
        RouteType.GO, RouteType.CORNER, RouteType.DRAG,
    ]:
        scenarios.append(Scenario.route_vs_air(route_type))
        scenarios.append(Scenario.route_vs_man(route_type))
    return scenarios


def coverage_test_scenarios() -> List[Scenario]:
    """Generate scenarios for coverage testing."""
    scenarios = []

    # Different cushions
    for cushion in [5.0, 7.0, 10.0]:
        scenarios.append(
            Scenario.route_vs_man(RouteType.SLANT, cushion=cushion)
        )

    # Different DB speeds
    for db_speed in [85, 90, 95]:
        scenarios.append(
            Scenario.route_vs_man(RouteType.GO, db_speed=db_speed)
        )

    return scenarios
