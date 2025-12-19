"""Export simulation frames to JSON for visualization."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from .core.vec2 import Vec2
from .core.entities import Player, Team
from .core.clock import Clock
from .core.events import EventBus, Event
from .physics.movement import MovementProfile, MovementResult
from .physics.body import BodyModel
from .plays.routes import RouteType, ROUTE_LIBRARY, RoutePhase
from .systems.route_runner import RouteRunner, RouteAssignment


@dataclass
class PlayerFrame:
    """Single frame of player state."""
    id: str
    name: str
    team: str
    position: str
    x: float
    y: float
    vx: float
    vy: float
    speed: float
    facing_x: float
    facing_y: float

    # Route info (if applicable)
    route_name: Optional[str] = None
    route_phase: Optional[str] = None
    current_waypoint: int = 0
    total_waypoints: int = 0
    target_x: Optional[float] = None
    target_y: Optional[float] = None

    # Physics debug
    at_max_speed: bool = False
    cut_occurred: bool = False
    cut_angle: float = 0.0

    # Decision reasoning
    reasoning: str = ""


@dataclass
class WaypointData:
    """Waypoint visualization data."""
    x: float
    y: float
    is_break: bool
    phase: str
    look_for_ball: bool


@dataclass
class EventFrame:
    """Event that occurred during this frame."""
    time: float
    type: str
    player_id: Optional[str]
    description: str


@dataclass
class SimulationFrame:
    """Complete frame of simulation state."""
    tick: int
    time: float
    players: List[PlayerFrame]
    events: List[EventFrame]


@dataclass
class SimulationExport:
    """Complete simulation export."""
    metadata: Dict[str, Any]
    waypoints: Dict[str, List[WaypointData]]  # player_id -> waypoints
    frames: List[SimulationFrame]

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)

    def save(self, path: str) -> None:
        """Save to file."""
        with open(path, 'w') as f:
            f.write(self.to_json())


class SimulationRecorder:
    """Records simulation frames for export."""

    def __init__(self):
        self.frames: List[SimulationFrame] = []
        self.waypoints: Dict[str, List[WaypointData]] = {}
        self.pending_events: List[EventFrame] = []

    def record_waypoints(self, player_id: str, assignment: RouteAssignment):
        """Record waypoints for a player's route."""
        waypoint_data = []
        for i, wp in enumerate(assignment._field_waypoints):
            wp_def = assignment.route.waypoints[i]
            waypoint_data.append(WaypointData(
                x=wp.x,
                y=wp.y,
                is_break=wp_def.is_break,
                phase=wp_def.phase.value,
                look_for_ball=wp_def.look_for_ball,
            ))
        self.waypoints[player_id] = waypoint_data

    def record_event(self, event: Event):
        """Record an event."""
        self.pending_events.append(EventFrame(
            time=event.time,
            type=event.type.value,
            player_id=event.player_id,
            description=event.description,
        ))

    def record_frame(
        self,
        tick: int,
        time: float,
        players: List[tuple[Player, MovementProfile, Optional[RouteAssignment], MovementResult, str]],
    ):
        """Record a simulation frame.

        Args:
            tick: Current tick number
            time: Current time in seconds
            players: List of (player, profile, assignment, result, reasoning) tuples
        """
        player_frames = []

        for player, profile, assignment, result, reasoning in players:
            frame = PlayerFrame(
                id=player.id,
                name=player.name,
                team=player.team.value,
                position=player.position.value,
                x=player.pos.x,
                y=player.pos.y,
                vx=player.velocity.x,
                vy=player.velocity.y,
                speed=player.velocity.length(),
                facing_x=player.facing.x,
                facing_y=player.facing.y,
                reasoning=reasoning,
            )

            # Add physics debug info
            if result:
                frame.at_max_speed = result.at_max_speed
                frame.cut_occurred = result.cut_occurred
                frame.cut_angle = result.cut_angle

            # Add route info
            if assignment:
                frame.route_name = assignment.route.name
                frame.route_phase = assignment.phase.value
                frame.current_waypoint = assignment.current_waypoint_idx
                frame.total_waypoints = len(assignment.route.waypoints)
                if assignment.current_target:
                    frame.target_x = assignment.current_target.x
                    frame.target_y = assignment.current_target.y

            player_frames.append(frame)

        # Create frame with pending events
        sim_frame = SimulationFrame(
            tick=tick,
            time=time,
            players=player_frames,
            events=self.pending_events.copy(),
        )

        self.frames.append(sim_frame)
        self.pending_events.clear()

    def export(self, metadata: Optional[Dict[str, Any]] = None) -> SimulationExport:
        """Create export object."""
        return SimulationExport(
            metadata=metadata or {},
            waypoints=self.waypoints,
            frames=self.frames,
        )


def run_and_export(
    routes: List[tuple[str, RouteType, float, bool]],
    max_time: float = 5.0,
    output_path: Optional[str] = None,
) -> SimulationExport:
    """Run a simulation and export frames.

    Args:
        routes: List of (name, route_type, alignment_x, is_left_side)
        max_time: Maximum simulation time
        output_path: Optional path to save JSON

    Returns:
        SimulationExport object
    """
    from .core.entities import Player, Team, Position, PlayerAttributes

    # Setup
    clock = Clock(tick_rate=0.05)
    event_bus = EventBus()
    recorder = SimulationRecorder()
    route_runner = RouteRunner(event_bus)

    # Subscribe to events
    event_bus.subscribe_all(recorder.record_event)

    # Create players
    players_data = []  # (player, profile, assignment)

    for name, route_type, alignment_x, is_left_side in routes:
        if is_left_side:
            alignment_x = -abs(alignment_x)

        alignment = Vec2(alignment_x, 0)
        attrs = PlayerAttributes(speed=90, acceleration=88, agility=88)

        player = Player(
            id=name.lower().replace(" ", "_"),
            name=name,
            team=Team.OFFENSE,
            position=Position.WR,
            pos=alignment,
            attributes=attrs,
        )

        profile = MovementProfile.from_attributes(
            attrs.speed, attrs.acceleration, attrs.agility
        )

        route = ROUTE_LIBRARY[route_type]
        assignment = route_runner.assign_route(player, route, alignment, is_left_side)

        # Record waypoints
        recorder.record_waypoints(player.id, assignment)

        players_data.append((player, profile, assignment))

    # Start play
    route_runner.start_all_routes(clock)

    # Record initial frame
    frame_data = []
    for player, profile, assignment in players_data:
        frame_data.append((player, profile, assignment, None, "Pre-snap"))
    recorder.record_frame(clock.tick_count, clock.current_time, frame_data)

    # Simulation loop
    all_complete = False
    while clock.current_time < max_time and not all_complete:
        clock.tick()

        frame_data = []
        all_complete = True

        for player, profile, assignment in players_data:
            result, reasoning = route_runner.update(player, profile, clock.tick_rate, clock)

            player.pos = result.new_pos
            player.velocity = result.new_vel

            frame_data.append((player, profile, assignment, result, reasoning))

            if not assignment.is_complete:
                all_complete = False

        recorder.record_frame(clock.tick_count, clock.current_time, frame_data)

    # Create export
    export = recorder.export(metadata={
        "total_time": clock.current_time,
        "total_ticks": clock.tick_count,
        "tick_rate": clock.tick_rate,
        "routes": [
            {"name": name, "type": rt.value, "x": x, "left": left}
            for name, rt, x, left in routes
        ],
    })

    if output_path:
        export.save(output_path)
        print(f"Exported {len(export.frames)} frames to {output_path}")

    return export


# Convenience function for quick exports
def export_route_demo(output_path: str = "route_sim.json"):
    """Export a demo simulation."""
    routes = [
        ("Tyreek Hill", RouteType.SLANT, 20.0, False),
        ("Davante Adams", RouteType.CURL, 18.0, True),
        ("Travis Kelce", RouteType.SEAM, 5.0, False),
    ]
    return run_and_export(routes, max_time=4.0, output_path=output_path)


if __name__ == "__main__":
    export_route_demo("frontend/public/route_sim.json")
