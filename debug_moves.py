#!/usr/bin/env python3
"""Debug script to trace move resolution and tackle interactions."""

import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Ball, BallState, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.events import EventBus, EventType
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain


def setup_run_play():
    """Setup a simple run play scenario."""
    orchestrator = Orchestrator()

    # RB with the ball, 5 yards behind LOS
    rb = Player(
        id="RB1",
        name="Running Back",
        team=Team.OFFENSE,
        position=Position.RB,
        pos=Vec2(0, -5),
        velocity=Vec2(0, 0),
        has_ball=True,
        attributes=PlayerAttributes(
            speed=90,
            acceleration=88,
            agility=92,
            strength=75,
        ),
    )

    # A couple blockers
    lg = Player(
        id="LG",
        name="Left Guard",
        team=Team.OFFENSE,
        position=Position.LG,
        pos=Vec2(-3, 0),
        attributes=PlayerAttributes(speed=65, strength=85),
    )
    rg = Player(
        id="RG",
        name="Right Guard",
        team=Team.OFFENSE,
        position=Position.RG,
        pos=Vec2(3, 0),
        attributes=PlayerAttributes(speed=65, strength=85),
    )

    # Defenders
    mlb = Player(
        id="MLB",
        name="Middle LB",
        team=Team.DEFENSE,
        position=Position.MLB,
        pos=Vec2(0, 5),
        attributes=PlayerAttributes(
            speed=84,
            acceleration=82,
            tackling=85,
        ),
    )

    olb1 = Player(
        id="OLB1",
        name="Outside LB",
        team=Team.DEFENSE,
        position=Position.OLB,
        pos=Vec2(-5, 4),
        attributes=PlayerAttributes(
            speed=82,
            tackling=80,
        ),
    )

    olb2 = Player(
        id="OLB2",
        name="Outside LB 2",
        team=Team.DEFENSE,
        position=Position.OLB,
        pos=Vec2(5, 4),
        attributes=PlayerAttributes(
            speed=82,
            tackling=80,
        ),
    )

    # Setup orchestrator
    offense = [rb, lg, rg]
    defense = [mlb, olb1, olb2]

    config = PlayConfig()
    orchestrator.setup_play(offense, defense, config, los_y=0.0)

    # Manually set RB as ballcarrier (since we don't have a QB)
    orchestrator.ball.state = BallState.HELD
    orchestrator.ball.carrier_id = "RB1"
    orchestrator.ball.pos = rb.pos
    rb.has_ball = True

    # Register ballcarrier brain for the RB
    orchestrator.register_brain("RB1", ballcarrier_brain)

    return orchestrator


def run_with_debug():
    """Run the play with detailed debug output."""
    orchestrator = setup_run_play()

    print("="*60)
    print("MOVE RESOLUTION DEBUG TEST")
    print("="*60)
    print()

    # Hook into events to track them
    events_log = []
    original_emit = orchestrator.event_bus.emit_simple

    def tracking_emit(event_type, tick, time, **kwargs):
        events_log.append({
            'type': event_type.value if hasattr(event_type, 'value') else str(event_type),
            'tick': tick,
            'time': time,
            'data': kwargs
        })
        return original_emit(event_type, tick, time, **kwargs)

    orchestrator.event_bus.emit_simple = tracking_emit

    # Track move attempts and tackle immunity
    move_attempts = 0
    move_successes = 0

    # Snap the ball
    orchestrator._do_snap()

    # Force phase to RUN_ACTIVE since RB has ball
    from huddle.simulation.v2.orchestrator import PlayPhase
    orchestrator.phase = PlayPhase.RUN_ACTIVE

    for tick in range(50):  # Max 50 ticks
        if orchestrator._should_stop():
            break

        dt = orchestrator.clock.tick()
        orchestrator._update_tick(dt)

        # Debug output
        rb = orchestrator._get_player("RB1")
        if rb:
            # Check immunity status
            immunity_until = orchestrator._tackle_immunity.get("RB1", 0)
            has_immunity = orchestrator.clock.current_time < immunity_until

            # Find nearest defender
            nearest_dist = float('inf')
            nearest_def = None
            for d in orchestrator.defense:
                dist = rb.pos.distance_to(d.pos)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_def = d

            # Just print the state - DON'T call brain again (pollutes shared state)
            print(f"[Tick {tick:2d}] t={orchestrator.clock.current_time:.2f}s  RB: {rb.pos.rounded()}  "
                  f"def: {nearest_def.id if nearest_def else 'none'} @ {nearest_dist:.1f}yd")

            # Show any events this tick
            tick_events = [e for e in events_log if e['tick'] == tick + 1]  # +1 because tick count is 1-indexed
            for evt in tick_events:
                if evt['type'] in ('move_success', 'tackle', 'broken_tackle'):
                    print(f"         >>> EVENT: {evt['type']} - {evt['data'].get('description', '')}")

    print()
    print("="*60)
    print("RESULTS")
    print("="*60)

    # Count events
    move_events = [e for e in events_log if 'move' in e['type'].lower()]
    tackle_events = [e for e in events_log if e['type'] == 'tackle']

    print(f"Move events: {len(move_events)}")
    for e in move_events:
        print(f"  - {e['type']} at tick {e['tick']}, t={e['time']:.2f}s")

    print(f"Tackle events: {len(tackle_events)}")
    for e in tackle_events:
        print(f"  - {e['type']} at tick {e['tick']}, t={e['time']:.2f}s")

    rb = orchestrator._get_player("RB1")
    if rb:
        yards_gained = rb.pos.y - (-5)  # Started at y=-5
        print(f"\nYards gained: {yards_gained:.1f}")


if __name__ == "__main__":
    run_with_debug()
