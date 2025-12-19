#!/usr/bin/env python3
"""Test ballcarrier evasion moves.

Creates scenarios where ballcarrier has time to attempt moves:
1. Deep route with cushion at catch
2. Catch in open field with pursuing defender
3. Multiple defenders converging

Run: python agentmail/qa_agent/test_scripts/test_evasion_moves.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain


def test_deep_catch_with_cushion():
    """WR catches deep with CB trailing - should have YAC opportunity."""
    print("=" * 60)
    print("TEST 1: Deep Catch with Cushion")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=95, throw_accuracy=88),
    )

    # Fast, elusive receiver
    wr = Player(
        id="WR1", name="Speedster", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(20, 0),
        attributes=PlayerAttributes(
            speed=95, acceleration=92, agility=90,
            elusiveness=88, catching=85, vision=82,
        ),
    )

    # Slower CB with big cushion
    cb = Player(
        id="CB1", name="Cornerback", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(18, 12),  # 12 yards off - deep cushion
        attributes=PlayerAttributes(speed=88, acceleration=85, tackling=82),
    )

    config = PlayConfig(
        routes={"WR1": "go"},
        man_assignments={"CB1": "WR1"},
        throw_timing=2.0,  # Throw at 2s
        throw_target="WR1",
        max_duration=8.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("ballcarrier", ballcarrier_brain)

    result = orch.run()

    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Yards: {result.yards_gained:.1f}")
    print()
    print("  Final Positions:")
    print(f"    WR: ({wr_final.pos.x:.1f}, {wr_final.pos.y:.1f})")
    print(f"    CB: ({cb_final.pos.x:.1f}, {cb_final.pos.y:.1f})")

    # Look for evasion/move events
    move_events = []
    for e in result.events:
        desc = e.description.lower()
        if any(word in desc for word in ['juke', 'spin', 'truck', 'evasion', 'cut', 'broken']):
            move_events.append(e)
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    if move_events:
        print(f"\n  RESULT: PASS - {len(move_events)} evasion moves detected!")
    else:
        print("\n  RESULT: CHECK - No evasion moves (may not be needed)")

    return result, move_events


def test_pursuit_from_behind():
    """WR catches and runs with CB in trailing pursuit."""
    print("\n" + "=" * 60)
    print("TEST 2: Pursuit from Behind")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=90, throw_accuracy=85),
    )

    wr = Player(
        id="WR1", name="Elusive Receiver", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(
            speed=90, acceleration=88, agility=92,  # Very agile
            elusiveness=90, catching=85, strength=75,
        ),
    )

    # CB starts behind the catch point
    cb = Player(
        id="CB1", name="Trailing Corner", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(17, 0),  # On wrong side of receiver
        attributes=PlayerAttributes(speed=91, acceleration=88, tackling=85),
    )

    config = PlayConfig(
        routes={"WR1": "slant"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.0,
        throw_target="WR1",
        max_duration=6.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("ballcarrier", ballcarrier_brain)

    result = orch.run()

    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Yards: {result.yards_gained:.1f}")

    move_events = []
    for e in result.events:
        desc = e.description.lower()
        if any(word in desc for word in ['juke', 'spin', 'truck', 'evasion', 'cut', 'broken']):
            move_events.append(e)
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    return result, move_events


def test_converging_defenders():
    """Multiple defenders closing - should trigger ball security or power move."""
    print("\n" + "=" * 60)
    print("TEST 3: Converging Defenders")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=85, throw_accuracy=85),
    )

    # Strong, powerful receiver
    wr = Player(
        id="WR1", name="Power Receiver", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(10, 0),
        attributes=PlayerAttributes(
            speed=85, acceleration=82, strength=90,  # Strong!
            agility=78, elusiveness=75, catching=85,
        ),
    )

    # Two defenders converging
    cb = Player(
        id="CB1", name="Corner", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(8, 8),  # Coming from front-left
        attributes=PlayerAttributes(speed=88, tackling=80),
    )

    ss = Player(
        id="SS1", name="Safety", position=Position.SS, team=Team.DEFENSE,
        pos=Vec2(12, 10),  # Coming from front-right
        attributes=PlayerAttributes(speed=86, tackling=85),
    )

    config = PlayConfig(
        routes={"WR1": "curl"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.5,
        throw_target="WR1",
        max_duration=5.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb, ss], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("SS1", db_brain)
    orch.register_brain("ballcarrier", ballcarrier_brain)

    result = orch.run()

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Yards: {result.yards_gained:.1f}")

    move_events = []
    for e in result.events:
        desc = e.description.lower()
        if any(word in desc for word in ['juke', 'spin', 'truck', 'evasion', 'cut', 'broken', 'protect']):
            move_events.append(e)
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    return result, move_events


if __name__ == "__main__":
    print("Testing Ballcarrier Evasion Moves")
    print()

    all_results = []
    all_moves = []

    r1, m1 = test_deep_catch_with_cushion()
    all_results.append(("Deep Catch", r1))
    all_moves.extend(m1)

    r2, m2 = test_pursuit_from_behind()
    all_results.append(("Trailing Pursuit", r2))
    all_moves.extend(m2)

    r3, m3 = test_converging_defenders()
    all_results.append(("Converging", r3))
    all_moves.extend(m3)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, r in all_results:
        print(f"  {name}: {r.outcome} ({r.duration:.2f}s, {r.yards_gained:.1f} yds)")

    print(f"\n  Total evasion events: {len(all_moves)}")

    if all_moves:
        print("\n  All evasion events:")
        for e in all_moves:
            print(f"    [{e.time:.2f}s] {e.description}")
    else:
        print("\n  No evasion moves detected across all tests.")
        print("  Possible causes:")
        print("    1. Tackle happens before ballcarrier brain gets a tick")
        print("    2. Defenders too close at catch point")
        print("    3. Evasion move events not being emitted")
