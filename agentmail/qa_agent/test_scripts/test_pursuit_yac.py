#!/usr/bin/env python3
"""Test pursuit angles on YAC (non-settling routes).

Verifies that after a WR catches on a slant/go route, defenders:
1. Switch to pursuit mode
2. Calculate intercept angles
3. Close the gap and make tackles

Run: python agentmail/qa_agent/test_scripts/test_pursuit_yac.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain


def test_pursuit_on_slant():
    """Test pursuit on a slant route (non-settling, should have YAC)."""
    print("=" * 60)
    print("TEST: Pursuit on Slant Route (Non-Settling)")
    print("=" * 60)

    # Create players - throw to slant (WR1), not curl
    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
    )

    # WR running slant from wide right
    wr = Player(
        id="WR1",
        name="Wide Receiver",
        position=Position.WR,
        team=Team.OFFENSE,
        pos=Vec2(20, 0),  # Wide right
        attributes=PlayerAttributes(speed=90, acceleration=88, catching=90),
    )

    # CB in off coverage
    cb = Player(
        id="CB1",
        name="Cornerback",
        position=Position.CB,
        team=Team.DEFENSE,
        pos=Vec2(18, 7),  # 7 yards off, shaded inside
        attributes=PlayerAttributes(speed=90, acceleration=88, man_coverage=85),
    )

    # Config - throw to WR1 on slant
    config = PlayConfig(
        routes={"WR1": "slant"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.2,  # Quick slant timing
        throw_target="WR1",
        max_duration=6.0,
    )

    # Run
    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)

    result = orch.run()

    # Get final positions
    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print(f"  Yards gained: {result.yards_gained:.1f}")
    print()
    print("  Final Positions:")
    print(f"    WR: ({wr_final.pos.x:.1f}, {wr_final.pos.y:.1f})")
    print(f"    CB: ({cb_final.pos.x:.1f}, {cb_final.pos.y:.1f})")

    gap = wr_final.pos.distance_to(cb_final.pos)
    print(f"    Gap: {gap:.1f} yards")
    print()

    # Analyze
    if result.outcome == "timeout":
        print("  RESULT: FAIL - Play ended in timeout (pursuit not closing)")
    elif result.outcome == "complete" and gap < 1.0:
        print("  RESULT: PASS - Tackle made, pursuit working!")
    elif result.outcome == "complete":
        print(f"  RESULT: PARTIAL - Catch complete but gap={gap:.1f} at end")
    else:
        print(f"  RESULT: {result.outcome}")

    return result


def test_pursuit_on_go():
    """Test pursuit on a go route (deep, non-settling)."""
    print("\n" + "=" * 60)
    print("TEST: Pursuit on Go Route (Deep)")
    print("=" * 60)

    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=95, throw_accuracy=85),
    )

    # Fast WR running go route
    wr = Player(
        id="WR1",
        name="Speed Receiver",
        position=Position.WR,
        team=Team.OFFENSE,
        pos=Vec2(20, 0),
        attributes=PlayerAttributes(speed=95, acceleration=90, catching=85),  # Fast
    )

    # CB slightly slower
    cb = Player(
        id="CB1",
        name="Cornerback",
        position=Position.CB,
        team=Team.DEFENSE,
        pos=Vec2(18, 7),
        attributes=PlayerAttributes(speed=92, acceleration=88, man_coverage=85),  # Slower
    )

    config = PlayConfig(
        routes={"WR1": "go"},
        man_assignments={"CB1": "WR1"},
        throw_timing=2.0,  # Deeper throw
        throw_target="WR1",
        max_duration=8.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)

    result = orch.run()

    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print(f"  Yards gained: {result.yards_gained:.1f}")
    print()
    print("  Final Positions:")
    print(f"    WR: ({wr_final.pos.x:.1f}, {wr_final.pos.y:.1f})")
    print(f"    CB: ({cb_final.pos.x:.1f}, {cb_final.pos.y:.1f})")

    gap = wr_final.pos.distance_to(cb_final.pos)
    print(f"    Gap: {gap:.1f} yards")
    print()

    # With faster WR, CB should use pursuit angle but may not catch
    if result.outcome == "timeout":
        print("  RESULT: FAIL - Timeout (pursuit not working)")
    elif result.outcome == "complete":
        if gap < 2.0:
            print("  RESULT: PASS - CB closing gap with pursuit angles")
        else:
            print(f"  RESULT: CHECK - Gap still {gap:.1f} yards (WR faster, expected)")
    else:
        print(f"  RESULT: {result.outcome}")

    return result


def test_same_speed_pursuit():
    """Test that same-speed pursuit DOES close the gap with angles."""
    print("\n" + "=" * 60)
    print("TEST: Same-Speed Pursuit (Should Close Gap)")
    print("=" * 60)

    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
    )

    # WR and CB same speed
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
        pos=Vec2(13, 7),  # 7 yards off
        attributes=PlayerAttributes(speed=88, acceleration=86, man_coverage=85),  # Same speed!
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

    result = orch.run()

    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print()
    print("  Final Positions:")
    print(f"    WR: ({wr_final.pos.x:.1f}, {wr_final.pos.y:.1f})")
    print(f"    CB: ({cb_final.pos.x:.1f}, {cb_final.pos.y:.1f})")

    gap = wr_final.pos.distance_to(cb_final.pos)
    print(f"    Gap: {gap:.1f} yards")
    print()

    # Same speed with pursuit angles should close gap
    if result.outcome == "timeout":
        print("  RESULT: FAIL - Same speed pursuit should close gap!")
        print("  This is the original bug - pursuit angles not working")
    elif result.outcome == "complete" and gap < 1.0:
        print("  RESULT: PASS - Same speed pursuit closed gap!")
    else:
        print(f"  RESULT: {result.outcome}, gap={gap:.1f}")

    return result


if __name__ == "__main__":
    results = []
    results.append(("Slant", test_pursuit_on_slant()))
    results.append(("Go", test_pursuit_on_go()))
    results.append(("Same Speed", test_same_speed_pursuit()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, r in results:
        print(f"  {name}: {r.outcome} ({r.duration:.2f}s, {r.yards_gained:.1f} yds)")
