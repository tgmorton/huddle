#!/usr/bin/env python3
"""Demo script for v2 route simulation.

Runs receivers through routes with focused, readable output.
"""

import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.clock import Clock
from huddle.simulation.v2.core.events import EventBus, Event, EventType
from huddle.simulation.v2.core.field import Field
from huddle.simulation.v2.physics.movement import MovementProfile
from huddle.simulation.v2.plays.routes import RouteType, ROUTE_LIBRARY
from huddle.simulation.v2.systems.route_runner import RouteRunner


def create_receiver(
    name: str,
    position: Vec2,
    speed: int = 90,
    accel: int = 88,
    agility: int = 88,
) -> tuple[Player, MovementProfile]:
    """Create a receiver with attributes and movement profile."""
    attrs = PlayerAttributes(speed=speed, acceleration=accel, agility=agility)
    player = Player(
        id=name.lower().replace(" ", "_"),
        name=name,
        team=Team.OFFENSE,
        position=Position.WR,
        pos=position,
        attributes=attrs,
    )
    profile = MovementProfile.from_attributes(speed, accel, agility)
    return player, profile


def run_simulation(
    route_type: RouteType,
    receiver_name: str = "Demo WR",
    alignment_x: float = 20.0,
    is_left_side: bool = False,
    max_time: float = 5.0,
):
    """Run a route simulation with concise output."""
    # Setup
    field = Field(line_of_scrimmage=25, yards_to_goal=75)
    clock = Clock(tick_rate=0.05)
    event_bus = EventBus()
    events_log = []

    def capture_event(event: Event):
        events_log.append(f"T={event.time:.2f}s: {event.description}")
    event_bus.subscribe_all(capture_event)

    # Create receiver
    if is_left_side:
        alignment_x = -abs(alignment_x)
    alignment = Vec2(alignment_x, 0)
    receiver, profile = create_receiver(receiver_name, alignment)
    route = ROUTE_LIBRARY[route_type]

    # Setup and run
    runner = RouteRunner(event_bus)
    assignment = runner.assign_route(receiver, route, alignment, is_left_side)
    runner.start_route(receiver.id, clock)

    # Simulation loop
    positions = [receiver.pos]
    while clock.current_time < max_time and not assignment.is_complete:
        result, _ = runner.update(receiver, profile, clock.tick_rate, clock)
        receiver.pos = result.new_pos
        receiver.velocity = result.new_vel
        positions.append(receiver.pos)
        clock.tick()

    # Calculate stats
    total_distance = sum(
        positions[i].distance_to(positions[i+1])
        for i in range(len(positions)-1)
    )

    # Output
    side = "L" if is_left_side else "R"
    print(f"\n{route.name} ({route_type.value}) - {receiver_name} [{side}]")
    print(f"  Start: ({alignment.x:.0f}, 0) → End: ({receiver.pos.x:.1f}, {receiver.pos.y:.1f})")
    print(f"  Time: {clock.current_time:.2f}s | Distance: {total_distance:.1f}yd | Speed: {profile.max_speed:.1f}yd/s")
    print(f"  Waypoints: {' → '.join(f'({w.x:.0f},{w.y:.0f})' for w in assignment._field_waypoints)}")

    if events_log:
        print(f"  Events: {' | '.join(events_log)}")

    return receiver, assignment


def main():
    """Run demo with multiple routes."""
    print("=" * 60)
    print("ROUTE SIMULATION DEMO - v2 Engine")
    print("=" * 60)

    routes = [
        (RouteType.SLANT, "Tyreek Hill", 20.0, False),
        (RouteType.GO, "Ja'Marr Chase", 22.0, False),
        (RouteType.CURL, "Davante Adams", 18.0, True),
        (RouteType.POST, "Justin Jefferson", 20.0, False),
        (RouteType.OUT, "Cooper Kupp", 19.0, True),
        (RouteType.CORNER, "DeVonta Smith", 21.0, False),
        (RouteType.DRAG, "Amon-Ra St. Brown", 8.0, True),
    ]

    for route_type, name, x, left in routes:
        run_simulation(route_type, name, x, left)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
