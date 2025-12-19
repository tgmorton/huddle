#!/usr/bin/env python3
"""Test ballcarrier brain activation after catch.

Verifies that after a WR catches, they:
1. Switch to ballcarrier brain
2. Attempt evasion moves (juke, spin, etc.)
3. Sometimes break tackles
4. Have varied outcomes

Run: python agentmail/qa_agent/test_scripts/test_ballcarrier_brain.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from collections import Counter
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain


def run_yac_play(play_num: int, verbose: bool = False):
    """Run a single play designed for YAC opportunity."""

    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=90, throw_accuracy=90),
    )

    # Elusive receiver - good at breaking tackles
    wr = Player(
        id="WR1",
        name="Elusive Receiver",
        position=Position.WR,
        team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(
            speed=90,
            acceleration=88,
            catching=88,
            agility=92,  # High agility for moves
            elusiveness=88,  # Good at breaking tackles
            vision=85,  # Ball carrier vision
        ),
    )

    # CB in off coverage - will have to close distance
    cb = Player(
        id="CB1",
        name="Cornerback",
        position=Position.CB,
        team=Team.DEFENSE,
        pos=Vec2(13, 10),  # 10 yards off - more cushion
        attributes=PlayerAttributes(
            speed=86,  # Slower than WR
            acceleration=84,
            man_coverage=80,
            tackling=78,  # Not a great tackler
        ),
    )

    config = PlayConfig(
        routes={"WR1": "slant"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.5,  # Later throw - more route development
        throw_target="WR1",
        max_duration=10.0,  # Longer for YAC
    )

    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)

    # Register all brains including ballcarrier
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("ballcarrier", ballcarrier_brain)  # Key!

    result = orch.run(verbose=verbose)

    wr_final = orch._get_player("WR1")

    # Check phase and events
    if verbose:
        print(f"  Final phase: {orch.phase}")
        for e in result.events:
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    if verbose:
        print(f"\nPlay {play_num}:")
        print(f"  Outcome: {result.outcome}")
        print(f"  Duration: {result.duration:.2f}s")
        print(f"  Yards: {result.yards_gained:.1f}")
        print(f"  Events: {len(result.events)}")

        # Look for move-related events
        for e in result.events:
            desc = e.description.lower()
            if any(word in desc for word in ['juke', 'spin', 'truck', 'stiff', 'broken', 'move', 'evasion']):
                print(f"    [{e.time:.2f}s] {e.description}")

    return result


def main():
    print("=" * 60)
    print("TEST: Ballcarrier Brain Activation After Catch")
    print("=" * 60)

    num_plays = 10
    results = []

    print(f"\nRunning {num_plays} plays...\n")

    # Run first play with verbose for debugging
    result = run_yac_play(1, verbose=True)
    results.append(result)

    # Run rest quietly
    for i in range(1, num_plays):
        result = run_yac_play(i + 1, verbose=False)
        results.append(result)

    # Analyze outcomes
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    outcomes = Counter(r.outcome for r in results)
    print(f"\nOutcome distribution:")
    for outcome, count in outcomes.items():
        print(f"  {outcome}: {count}/{num_plays}")

    yards = [r.yards_gained for r in results]
    print(f"\nYards gained:")
    print(f"  Min: {min(yards):.1f}")
    print(f"  Max: {max(yards):.1f}")
    print(f"  Avg: {sum(yards)/len(yards):.1f}")

    durations = [r.duration for r in results]
    print(f"\nPlay duration:")
    print(f"  Min: {min(durations):.2f}s")
    print(f"  Max: {max(durations):.2f}s")
    print(f"  Avg: {sum(durations)/len(durations):.2f}s")

    # Check for move events
    move_keywords = ['juke', 'spin', 'truck', 'stiff', 'broken', 'evasion', 'move']
    plays_with_moves = 0
    for r in results:
        for e in r.events:
            if any(kw in e.description.lower() for kw in move_keywords):
                plays_with_moves += 1
                break

    print(f"\nMove attempts detected: {plays_with_moves}/{num_plays} plays")

    # Verdict
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

    issues = []

    if len(outcomes) == 1:
        issues.append("All plays have same outcome - no variance")

    if max(yards) - min(yards) < 2.0:
        issues.append("Yards gained too consistent - ballcarrier may not be running")

    if plays_with_moves == 0:
        issues.append("No move attempts detected - ballcarrier brain may not be active")

    if 'timeout' in outcomes:
        issues.append(f"{outcomes['timeout']} plays ended in timeout")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("PASS - Ballcarrier brain appears to be working:")
        print("  - Varied outcomes")
        print("  - Varied yards gained")
        print("  - Move attempts detected" if plays_with_moves > 0 else "  - (No moves needed)")


if __name__ == "__main__":
    main()
