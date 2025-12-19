#!/usr/bin/env python3
"""Integration test for passing plays with multiple brains."""

import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Ball, BallState, Team, Position, PlayerAttributes
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig, PlayPhase
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.lb_brain import lb_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain


def create_passing_play():
    """Create a passing play with QB, WR, CB, and LB."""
    orchestrator = Orchestrator()

    # Offense
    qb = Player(
        id="QB1",
        name="Quarterback",
        team=Team.OFFENSE,
        position=Position.QB,
        pos=Vec2(0, -5),  # Shotgun
        has_ball=True,
        attributes=PlayerAttributes(
            speed=78,
            acceleration=80,
            throw_power=88,
            throw_accuracy=85,
            awareness=82,
        ),
    )

    wr1 = Player(
        id="WR1",
        name="Wide Receiver",
        team=Team.OFFENSE,
        position=Position.WR,
        pos=Vec2(15, 0),  # Right side
        attributes=PlayerAttributes(
            speed=92,
            acceleration=90,
            agility=88,
            route_running=85,
            catching=86,
        ),
    )

    wr2 = Player(
        id="WR2",
        name="Slot Receiver",
        team=Team.OFFENSE,
        position=Position.WR,
        pos=Vec2(-8, 0),  # Left slot
        attributes=PlayerAttributes(
            speed=88,
            acceleration=86,
            agility=90,
            route_running=82,
            catching=84,
        ),
    )

    # Offensive line
    lt = Player(
        id="LT",
        name="Left Tackle",
        team=Team.OFFENSE,
        position=Position.LT,
        pos=Vec2(-3, -2),  # Left side of QB
        attributes=PlayerAttributes(
            speed=68,
            acceleration=72,
            strength=85,
            block_power=82,
            block_finesse=80,
            awareness=78,
        ),
    )

    # Defense
    de = Player(
        id="DE1",
        name="Defensive End",
        team=Team.DEFENSE,
        position=Position.DE,
        pos=Vec2(-3, 1),  # Lined up over LT
        attributes=PlayerAttributes(
            speed=82,
            acceleration=84,
            strength=82,
            pass_rush=85,
            agility=80,
            tackling=78,
        ),
    )

    cb1 = Player(
        id="CB1",
        name="Cornerback",
        team=Team.DEFENSE,
        position=Position.CB,
        pos=Vec2(13, 7),  # Off coverage on WR1
        attributes=PlayerAttributes(
            speed=91,
            acceleration=88,
            agility=88,
            man_coverage=82,
            zone_coverage=78,
            play_recognition=75,
        ),
    )

    cb2 = Player(
        id="CB2",
        name="Nickel Corner",
        team=Team.DEFENSE,
        position=Position.CB,
        pos=Vec2(-6, 5),  # Covering slot
        attributes=PlayerAttributes(
            speed=88,
            acceleration=86,
            man_coverage=78,
            zone_coverage=80,
        ),
    )

    mlb = Player(
        id="MLB",
        name="Middle Linebacker",
        team=Team.DEFENSE,
        position=Position.MLB,
        pos=Vec2(0, 5),
        attributes=PlayerAttributes(
            speed=82,
            acceleration=80,
            tackling=85,
            play_recognition=80,
            zone_coverage=72,
        ),
    )

    offense = [qb, wr1, wr2, lt]
    defense = [de, cb1, cb2, mlb]

    # Configure play with routes
    config = PlayConfig(
        routes={
            "WR1": "slant",
            "WR2": "curl",
        },
        man_assignments={
            "CB1": "WR1",
            "CB2": "WR2",
        },
        max_duration=6.0,
    )

    orchestrator.setup_play(offense, defense, config, los_y=0.0)

    # Register brains
    orchestrator.register_brain("QB1", qb_brain)
    orchestrator.register_brain("WR1", receiver_brain)
    orchestrator.register_brain("WR2", receiver_brain)
    orchestrator.register_brain("LT", ol_brain)
    orchestrator.register_brain("DE1", dl_brain)
    orchestrator.register_brain("CB1", db_brain)
    orchestrator.register_brain("CB2", db_brain)
    orchestrator.register_brain("MLB", lb_brain)
    orchestrator.register_brain("ballcarrier", ballcarrier_brain)

    return orchestrator


def run_test():
    """Run the passing play and report results."""
    print("=" * 70)
    print("PASSING PLAY INTEGRATION TEST")
    print("=" * 70)
    print()

    orchestrator = create_passing_play()

    print("Setup:")
    print("  QB in shotgun at (0, -5)")
    print("  WR1 running slant from (15, 0)")
    print("  WR2 running curl from (-8, 0)")
    print("  LT pass blocking at (-3, -2)")
    print("  DE rushing from (-3, 1)")
    print("  CB1 in man on WR1, CB2 on WR2")
    print("  MLB reading run/pass")
    print()

    # Run the play
    result = orchestrator.run(verbose=False)

    print("-" * 70)
    print("PLAY RESULT")
    print("-" * 70)
    print(f"  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")

    if result.yards_gained is not None:
        print(f"  Yards: {result.yards_gained:.1f}")

    print()
    print("Key Events:")
    for event in result.events:
        if event.type.value in ('snap', 'throw', 'catch', 'incomplete', 'interception',
                                 'tackle', 'out_of_bounds', 'touchdown', 'sack',
                                 'route_break', 'move_success', 'block_shed'):
            print(f"  [{event.time:.2f}s] {event.type.value}: {event.description}")

    print()
    print("Final Positions:")
    for p in orchestrator.offense + orchestrator.defense:
        status = ""
        if p.has_ball:
            status = " [HAS BALL]"
        elif p.is_down:
            status = " [DOWN]"
        print(f"  {p.id}: {p.pos.rounded()}{status}")

    return result


def run_multiple(n=5):
    """Run multiple plays to see variation."""
    print("=" * 70)
    print(f"RUNNING {n} PLAYS")
    print("=" * 70)

    outcomes = {}
    total_yards = 0
    completions = 0

    for i in range(n):
        print(f"\n--- Play {i+1} ---")
        result = run_test()

        outcome = result.outcome
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

        if result.yards_gained is not None:
            total_yards += result.yards_gained
        if outcome in ('catch', 'tackle', 'touchdown'):
            completions += 1

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Outcomes: {outcomes}")
    print(f"Completions: {completions}/{n} ({100*completions/n:.0f}%)")
    if completions > 0:
        print(f"Avg yards on completions: {total_yards/completions:.1f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        run_multiple(5)
    else:
        run_test()
