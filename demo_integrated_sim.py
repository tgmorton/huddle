#!/usr/bin/env python3
"""Demo script for integrated passing play simulation.

This demonstrates the integrated simulator that combines:
- Pocket simulation (O-line vs D-line blocking, pressure)
- Play simulation (routes, coverage, QB decision-making)

The two simulations run in lockstep with bidirectional data flow:
- Pocket sim generates pressure state
- Play sim uses pressure to affect QB decisions and accuracy
- QB throw decision terminates pocket sim
"""

import sys
sys.path.insert(0, '.')

from huddle.simulation.sandbox.integrated_sim import (
    IntegratedSimulator,
    create_integrated_sim,
)
from huddle.simulation.sandbox.play_sim import QBAttributes
from huddle.simulation.sandbox.team_route_sim import (
    Formation,
    CoverageScheme,
    RouteConcept,
)
from huddle.simulation.sandbox.pocket_sim import DefensiveFront
from huddle.simulation.sandbox.shared import FieldContext, HashPosition


def print_header(text: str) -> None:
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def run_demo_game():
    """Run a demo with multiple plays showing different scenarios."""

    print_header("INTEGRATED PASSING PLAY SIMULATOR DEMO")
    print("""
This demo shows the integrated simulation combining:
- Pocket collapse (O-line vs D-line blocking)
- Route running and coverage
- QB read progression and throw decisions
- Pressure affecting accuracy and decision-making
""")

    # Scenario 1: Clean pocket, four verts vs Cover 3
    print_header("Scenario 1: Clean Pocket - 4 Verts vs Cover 3")

    sim = create_integrated_sim(
        formation="spread",
        coverage="cover_3",
        concept="four_verts",
        defensive_front="4_man",
        field_yard_line=25,
        hash_position="middle",
    )

    context = sim.setup()
    print(f"Field position: Own {context.field_context.yard_line}, {context.field_context.hash_position.value} hash")
    print()

    states = sim.run_full(max_ticks=50)
    final = sim.context

    print(f"Play Result: {final.result.upper()}")
    print(f"Total ticks: {final.tick}")
    if final.throw_tick:
        print(f"Throw released at tick: {final.throw_tick}")
    if final.yards_gained is not None:
        print(f"Yards gained: {final.yards_gained:.1f}")

    # Show pressure timeline
    print("\nPressure Timeline:")
    key_ticks = [5, 10, 15, 20, final.tick] if final.tick > 20 else list(range(1, final.tick + 1, 3))
    for i, state in enumerate(states):
        tick = i + 1
        if tick in key_ticks or tick == len(states):
            pressure = state.get('pressure_state', {})
            print(f"  Tick {tick:2d}: pressure={pressure.get('total', 0):.2f} level={pressure.get('level', 'clean')}")

    # Scenario 2: Trips right, Mesh vs Cover 1
    print_header("Scenario 2: Trips Right - Mesh vs Cover 1")

    sim = IntegratedSimulator(
        formation=Formation.TRIPS_RIGHT,
        coverage=CoverageScheme.COVER_1,
        concept=RouteConcept.MESH,
        defensive_front=DefensiveFront.FOUR_MAN,
        qb_attributes=QBAttributes(
            arm_strength=92,
            accuracy=88,
            decision_making=90,
            pocket_awareness=85,
        ),
        field_context=FieldContext.from_yard_line(35, HashPosition.RIGHT),
    )

    context = sim.setup()
    print(f"QB: Elite (arm=92, acc=88, dec=90, aware=85)")
    print(f"Field: Own {context.field_context.yard_line}, {context.field_context.hash_position.value} hash")
    print()

    states = sim.run_full(max_ticks=50)
    final = sim.context

    print(f"Play Result: {final.result.upper()}")
    print(f"Total ticks: {final.tick}")
    if final.throw_tick:
        print(f"Throw released at tick: {final.throw_tick}")
    if final.yards_gained is not None:
        print(f"Yards gained: {final.yards_gained:.1f}")

    # Scenario 3: Red zone, Slants vs Cover 0 (blitz)
    print_header("Scenario 3: Red Zone - Slants vs Cover 0 Blitz")

    sim = IntegratedSimulator(
        formation=Formation.SPREAD,
        coverage=CoverageScheme.COVER_0,
        concept=RouteConcept.SLANTS,
        defensive_front=DefensiveFront.FIVE_MAN,  # Extra rusher
        qb_attributes=QBAttributes(
            arm_strength=85,
            accuracy=80,
            decision_making=75,
            pocket_awareness=70,
        ),
        field_context=FieldContext.from_yard_line(90, HashPosition.MIDDLE),  # Red zone
    )

    context = sim.setup()
    print(f"QB: Average (arm=85, acc=80, dec=75, aware=70)")
    print(f"Field: Opponent {100 - context.field_context.yard_line} (RED ZONE)")
    print(f"Defense: 5-man rush with Cover 0 (all man, no safety)")
    print()

    states = sim.run_full(max_ticks=60)
    final = sim.context

    print(f"Play Result: {final.result.upper()}")
    print(f"Total ticks: {final.tick}")
    if final.throw_tick:
        print(f"Throw released at tick: {final.throw_tick}")
    if final.yards_gained is not None:
        print(f"Yards gained: {final.yards_gained:.1f}")

    # Show final pressure
    if states:
        last_pressure = states[-1].get('pressure_state', {})
        print(f"\nFinal pressure state:")
        print(f"  Total: {last_pressure.get('total', 0):.2f}")
        print(f"  Level: {last_pressure.get('level', 'clean')}")
        print(f"  Panic: {last_pressure.get('panic', False)}")

    print_header("DEMO COMPLETE")
    print("""
The integrated simulator successfully combines:
- Pocket simulation with engagement model
- Play simulation with routes and coverage
- External pressure flow affecting QB decisions
- Field position adjustments (hash marks, boundary)

Key integration points:
1. Pocket sim produces PocketPressureState each tick
2. Pressure feeds into play sim via set_external_pressure()
3. Under panic (eta < 3 ticks), panic_throw() forces immediate release
4. Throw completion terminates pocket sim
5. Sack from pocket sim terminates play
""")


def run_single_play():
    """Run a single play with detailed output."""
    print_header("SINGLE PLAY - DETAILED OUTPUT")

    sim = create_integrated_sim(
        formation="spread",
        coverage="cover_3",
        concept="smash",
        defensive_front="4_man",
    )

    context = sim.setup()
    print(f"Formation: Spread | Coverage: Cover 3 | Concept: Smash")
    print(f"Receivers: {len(sim._play_sim.state.receivers)}")
    print(f"Defenders: {len(sim._play_sim.state.defenders)}")
    print(f"Rushers: {len(sim._pocket_sim.state.rushers)}")
    print(f"Blockers: {len(sim._pocket_sim.state.blockers)}")
    print()

    print("Tick-by-tick simulation:")
    print("-" * 60)

    for tick_num in range(45):
        context = sim.tick()

        pressure = context.pressure_state
        play = sim._play_sim.state

        # Show every 3rd tick or key events
        show = (tick_num % 3 == 0) or context.is_complete or (pressure.panic)

        if show:
            qb_read = play.qb.current_read_idx + 1
            thrown = "THROWN" if play.qb.has_thrown else f"reading #{qb_read}"

            print(f"T{context.tick:2d}: pressure={pressure.total:.2f} ({pressure.level.value}) | QB: {thrown}")

            if pressure.panic:
                print("      ** PANIC MODE - QB under heavy pressure! **")

        if context.is_complete:
            print()
            print(f">>> PLAY COMPLETE: {context.result.upper()} <<<")
            break

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Integrated simulation demo")
    parser.add_argument("--single", action="store_true", help="Run single play with details")
    args = parser.parse_args()

    if args.single:
        run_single_play()
    else:
        run_demo_game()
