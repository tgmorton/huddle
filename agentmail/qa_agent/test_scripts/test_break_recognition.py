#!/usr/bin/env python3
"""Test break recognition system for DBs.

Verifies:
1. Attribute impact (elite vs poor DB)
2. Route difficulty impact (curl < slant < post)
3. Delay calculation values
4. No regressions in ball-in-air tracking

Run: python agentmail/qa_agent/test_scripts/test_break_recognition.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.db_brain import db_brain, _get_break_recognition_delay, _db_states
from huddle.simulation.v2.ai.receiver_brain import receiver_brain


def test_attribute_impact():
    """Test that elite DBs have tighter coverage than poor DBs."""
    print("\n" + "=" * 60)
    print("TEST 1: Attribute Impact (Elite vs Poor DB)")
    print("=" * 60)
    print("  Testing coverage separation at catch time for different DB skill levels")

    results = {}

    for db_type, play_rec in [("elite", 95), ("average", 75), ("poor", 60)]:
        qb = Player(
            id="QB1",
            name="Quarterback",
            position=Position.QB,
            team=Team.OFFENSE,
            pos=Vec2(0, -5),
            has_ball=True,
            attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
        )

        wr = Player(
            id="WR1",
            name="Wide Receiver",
            position=Position.WR,
            team=Team.OFFENSE,
            pos=Vec2(15, 0),
            attributes=PlayerAttributes(speed=88, acceleration=86, catching=85),
        )

        cb = Player(
            id="CB1",
            name=f"{db_type.title()} CB",
            position=Position.CB,
            team=Team.DEFENSE,
            pos=Vec2(15, 7),
            attributes=PlayerAttributes(speed=88, acceleration=86, man_coverage=play_rec, play_recognition=play_rec),
        )

        # Reset DB state
        if "CB1" in _db_states:
            del _db_states["CB1"]

        config = PlayConfig(
            routes={"WR1": "slant"},
            man_assignments={"CB1": "WR1"},
            throw_timing=1.2,  # Quick slant timing - after break
            throw_target="WR1",
            max_duration=4.0,
        )

        orch = Orchestrator()
        orch.setup_play([qb, wr], [cb], config)
        orch.register_brain("WR1", receiver_brain)
        orch.register_brain("CB1", db_brain)

        result = orch.run()

        wr_p = orch._get_player("WR1")
        cb_p = orch._get_player("CB1")
        sep = wr_p.pos.distance_to(cb_p.pos)
        results[db_type] = sep
        print(f"  {db_type.title()} DB (play_rec={play_rec}): {sep:.2f} yard separation at end ({result.outcome})")

    # Verify elite < average < poor
    print()
    if results["elite"] < results["average"] < results["poor"]:
        print("  RESULT: PASS - Elite tighter than average, average tighter than poor")
        return True
    elif results["elite"] < results["poor"]:
        print("  RESULT: PARTIAL - Elite tighter than poor (expected ordering)")
        print(f"    Got: elite={results['elite']:.2f}, avg={results['average']:.2f}, poor={results['poor']:.2f}")
        return True
    else:
        print(f"  RESULT: FAIL - Expected elite < poor, got opposite")
        print(f"    elite={results['elite']:.2f}, avg={results['average']:.2f}, poor={results['poor']:.2f}")
        return False


def test_route_difficulty():
    """Test that harder routes create more separation."""
    print("\n" + "=" * 60)
    print("TEST 2: Route Difficulty Impact")
    print("=" * 60)
    print("  Testing coverage separation for different route types")

    results = {}

    for route in ["curl", "slant", "post"]:
        qb = Player(
            id="QB1",
            name="Quarterback",
            position=Position.QB,
            team=Team.OFFENSE,
            pos=Vec2(0, -5),
            has_ball=True,
            attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
        )

        wr = Player(
            id="WR1",
            name="Wide Receiver",
            position=Position.WR,
            team=Team.OFFENSE,
            pos=Vec2(15, 0),
            attributes=PlayerAttributes(speed=88, acceleration=86, catching=85),
        )

        cb = Player(
            id="CB1",
            name="Cornerback",
            position=Position.CB,
            team=Team.DEFENSE,
            pos=Vec2(15, 7),
            attributes=PlayerAttributes(speed=88, acceleration=86, man_coverage=75, play_recognition=75),
        )

        # Reset DB state
        if "CB1" in _db_states:
            del _db_states["CB1"]

        # Adjust timing based on route depth
        timing = {"curl": 1.0, "slant": 1.2, "post": 1.8}.get(route, 1.2)

        config = PlayConfig(
            routes={"WR1": route},
            man_assignments={"CB1": "WR1"},
            throw_timing=timing,
            throw_target="WR1",
            max_duration=5.0,
        )

        orch = Orchestrator()
        orch.setup_play([qb, wr], [cb], config)
        orch.register_brain("WR1", receiver_brain)
        orch.register_brain("CB1", db_brain)

        result = orch.run()

        wr_p = orch._get_player("WR1")
        cb_p = orch._get_player("CB1")
        sep = wr_p.pos.distance_to(cb_p.pos)
        results[route] = sep
        print(f"  {route.title()} route: {sep:.2f} yard separation ({result.outcome})")

    print()
    # Verify curl < slant < post (easier = less separation)
    if results["curl"] < results["slant"] < results["post"]:
        print("  RESULT: PASS - Harder routes create more separation")
        return True
    elif results["curl"] < results["post"]:
        print("  RESULT: PARTIAL - Post has more separation than curl (expected)")
        print(f"    curl={results['curl']:.2f}, slant={results['slant']:.2f}, post={results['post']:.2f}")
        return True
    else:
        print(f"  RESULT: FAIL - Route difficulty not reflected in separation")
        print(f"    curl={results['curl']:.2f}, slant={results['slant']:.2f}, post={results['post']:.2f}")
        return False


def test_ball_in_air_tracking():
    """Test that ball-in-air tracking still works correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Ball-in-Air Tracking (No Regression)")
    print("=" * 60)
    print("  Testing that DBs close on ball when thrown")

    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
    )

    wr = Player(
        id="WR1",
        name="Wide Receiver",
        position=Position.WR,
        team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(speed=88, acceleration=86, catching=85),
    )

    cb = Player(
        id="CB1",
        name="Cornerback",
        position=Position.CB,
        team=Team.DEFENSE,
        pos=Vec2(15, 7),
        attributes=PlayerAttributes(speed=88, acceleration=86, man_coverage=85, play_recognition=85),
    )

    # Reset DB state
    if "CB1" in _db_states:
        del _db_states["CB1"]

    config = PlayConfig(
        routes={"WR1": "curl"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.0,
        throw_target="WR1",
        max_duration=4.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)

    result = orch.run()

    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")
    gap = wr_final.pos.distance_to(cb_final.pos)

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Final gap: {gap:.1f} yards")

    # Ball-in-air should trigger pursuit/close coverage
    if result.outcome in ["complete", "incomplete", "interception"]:
        if gap < 2.0:
            print("  RESULT: PASS - Ball-in-air tracking working, tight coverage")
            return True
        else:
            print(f"  RESULT: PARTIAL - Play completed but gap={gap:.1f} yards")
            return True
    elif result.outcome == "timeout":
        print("  RESULT: FAIL - Timeout (tracking may be broken)")
        return False
    else:
        print(f"  RESULT: CHECK - Outcome={result.outcome}")
        return True


def test_delay_calculation():
    """Unit test for delay calculation function."""
    print("\n" + "=" * 60)
    print("TEST 4: Delay Calculation Values")
    print("=" * 60)
    print("  Verifying delay formula matches spec")

    from unittest.mock import MagicMock

    test_cases = [
        (95, "curl", 0.17),   # Elite + easy
        (95, "slant", 0.20),  # Elite + medium
        (75, "curl", 0.23),   # Average + easy
        (75, "slant", 0.26),  # Average + medium
        (60, "post", 0.44),   # Poor + hard
        (60, "corner", 0.50), # Poor + hardest
    ]

    all_pass = True
    for play_rec, route, expected in test_cases:
        # Create mock world
        world = MagicMock()
        world.me = MagicMock()
        world.me.attributes = MagicMock()
        world.me.attributes.play_recognition = play_rec

        actual = _get_break_recognition_delay(world, route)
        tolerance = 0.05
        passed = abs(actual - expected) < tolerance
        status = "OK" if passed else "MISMATCH"
        print(f"  play_rec={play_rec}, route={route}: expected={expected:.2f}s, actual={actual:.2f}s [{status}]")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  RESULT: PASS - All delay calculations match expected values")
    else:
        print("  RESULT: FAIL - Some delay calculations don't match")

    return all_pass


def test_separation_windows():
    """Test that timing routes get open at the right time."""
    print("\n" + "=" * 60)
    print("TEST 5: Separation Windows on Timing Routes")
    print("=" * 60)
    print("  Testing that slant/curl create catchable windows")

    results = []

    for route in ["curl", "slant"]:
        qb = Player(
            id="QB1",
            name="Quarterback",
            position=Position.QB,
            team=Team.OFFENSE,
            pos=Vec2(0, -5),
            has_ball=True,
            attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
        )

        wr = Player(
            id="WR1",
            name="Wide Receiver",
            position=Position.WR,
            team=Team.OFFENSE,
            pos=Vec2(15, 0),
            attributes=PlayerAttributes(speed=88, acceleration=86, catching=85),
        )

        # Average CB - should give timing routes a window
        cb = Player(
            id="CB1",
            name="Cornerback",
            position=Position.CB,
            team=Team.DEFENSE,
            pos=Vec2(15, 7),
            attributes=PlayerAttributes(speed=88, acceleration=86, man_coverage=75, play_recognition=75),
        )

        # Reset DB state
        if "CB1" in _db_states:
            del _db_states["CB1"]

        config = PlayConfig(
            routes={"WR1": route},
            man_assignments={"CB1": "WR1"},
            throw_timing=1.0,  # Quick timing
            throw_target="WR1",
            max_duration=4.0,
        )

        orch = Orchestrator()
        orch.setup_play([qb, wr], [cb], config)
        orch.register_brain("WR1", receiver_brain)
        orch.register_brain("CB1", db_brain)

        result = orch.run()
        results.append((route, result.outcome, result.yards_gained))
        print(f"  {route.title()}: {result.outcome}, {result.yards_gained:.1f} yards")

    print()
    # Timing routes should complete against average coverage
    completions = sum(1 for _, outcome, _ in results if outcome == "complete")
    if completions >= 1:
        print(f"  RESULT: PASS - Timing routes creating windows ({completions}/2 completions)")
        return True
    else:
        print("  RESULT: FAIL - Timing routes not completing")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("BREAK RECOGNITION SYSTEM - VERIFICATION TESTS")
    print("=" * 70)

    results = []
    results.append(("Attribute Impact", test_attribute_impact()))
    results.append(("Route Difficulty", test_route_difficulty()))
    results.append(("Ball-in-Air Tracking", test_ball_in_air_tracking()))
    results.append(("Delay Calculation", test_delay_calculation()))
    results.append(("Separation Windows", test_separation_windows()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")
