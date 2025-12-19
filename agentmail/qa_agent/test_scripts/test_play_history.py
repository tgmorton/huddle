#!/usr/bin/env python3
"""Test PlayHistory recording feature.

Verifies:
1. Plays are recorded after completion
2. Tendency calculation works correctly
3. History is maintained across plays

Run: python agentmail/qa_agent/test_scripts/test_play_history.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.db_brain import db_brain, _db_states
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.game_state import PlayHistory


def test_play_history_unit():
    """Unit test PlayHistory class directly."""
    print("=" * 60)
    print("TEST 1: PlayHistory Unit Test")
    print("=" * 60)

    history = PlayHistory()

    # Record some plays
    history.record_play("pass", True, 8)
    history.record_play("run", True, 4)
    history.record_play("pass", False, -2)
    history.record_play("pass", True, 15)
    history.record_play("run", True, 6)

    print(f"  Recorded {len(history.recent_plays)} plays")

    tendency = history.get_tendency()
    print(f"  Tendency: {tendency}")

    # Verify counts
    if tendency['run_count'] == 2 and tendency['pass_count'] == 3:
        print("  RESULT: PASS - Correct run/pass counts")
        return True
    else:
        print(f"  RESULT: FAIL - Expected run=2, pass=3")
        return False


def test_play_history_integration():
    """Test that orchestrator records plays to history."""
    print("\n" + "=" * 60)
    print("TEST 2: PlayHistory Integration Test")
    print("=" * 60)

    # Run multiple plays and check history
    orch = Orchestrator()

    for i in range(5):
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

        config = PlayConfig(
            routes={"WR1": "curl"},
            man_assignments={"CB1": "WR1"},
            throw_timing=1.0,
            throw_target="WR1",
            max_duration=4.0,
        )

        orch.setup_play([qb, wr], [cb], config)
        orch.register_brain("WR1", receiver_brain)
        orch.register_brain("CB1", db_brain)

        result = orch.run()
        print(f"  Play {i+1}: {result.outcome}, {result.yards_gained:.1f} yards")

    # Check history
    print()
    print(f"  History length: {len(orch.play_history.recent_plays)}")

    if len(orch.play_history.recent_plays) == 5:
        print("  RESULT: PASS - All 5 plays recorded")

        # Check tendency
        tendency = orch.play_history.get_tendency()
        print(f"  Tendency: {tendency}")
        return True
    else:
        print(f"  RESULT: FAIL - Expected 5 plays, got {len(orch.play_history.recent_plays)}")
        return False


def test_tendency_calculation():
    """Test tendency calculation with different scenarios."""
    print("\n" + "=" * 60)
    print("TEST 3: Tendency Calculation")
    print("=" * 60)

    # Heavy run offense
    history = PlayHistory()
    history.record_play("run", True, 4)
    history.record_play("run", True, 5)
    history.record_play("run", False, -1)
    history.record_play("pass", True, 8)
    history.record_play("run", True, 3)

    tendency = history.get_tendency()
    print(f"  Run-heavy (4 run, 1 pass): run_bias={tendency['run_bias']:.2f}")

    if tendency['run_bias'] > 0:
        print("  RESULT: PASS - Positive run bias detected")
        return True
    else:
        print("  RESULT: FAIL - Expected positive run bias")
        return False


def test_history_limit():
    """Test that history respects max_history limit."""
    print("\n" + "=" * 60)
    print("TEST 4: History Limit (max 10)")
    print("=" * 60)

    history = PlayHistory()

    # Record 15 plays
    for i in range(15):
        history.record_play("pass", True, i)

    print(f"  Recorded 15 plays")
    print(f"  History length: {len(history.recent_plays)}")

    if len(history.recent_plays) == 10:
        # Check oldest play is yards=5 (first 5 were evicted)
        oldest = history.recent_plays[0]
        print(f"  Oldest play yards: {oldest.yards} (expected 5)")
        if oldest.yards == 5:
            print("  RESULT: PASS - History limited to 10, oldest evicted correctly")
            return True
    print("  RESULT: FAIL - History limit not working")
    return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PLAY HISTORY RECORDING - VERIFICATION TESTS")
    print("=" * 70)

    results = []
    results.append(("Unit Test", test_play_history_unit()))
    results.append(("Integration", test_play_history_integration()))
    results.append(("Tendency Calculation", test_tendency_calculation()))
    results.append(("History Limit", test_history_limit()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")
