#!/usr/bin/env python3
"""Diagnostic: QB Targeting Analysis

Shows who the QB is targeting and why, to verify read progression works.
"""

import sys
sys.path.insert(0, '.')

from collections import defaultdict
from huddle.simulation.v2.ai.qb_brain import (
    qb_brain, _evaluate_receivers, _calculate_pressure, _find_best_receiver,
    ReceiverStatus, PressureLevel
)
from huddle.simulation.v2.orchestrator import WorldState, PlayerView, PlayPhase
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Position, Team, Attributes


def create_mock_world(
    receivers: list[dict],
    defenders: list[dict],
    qb_pos: Vec2 = Vec2(0, -7),
    los_y: float = 0,
    time_since_snap: float = 2.0,
) -> WorldState:
    """Create a mock WorldState for testing."""

    # QB attributes
    qb_attrs = Attributes(
        speed=75,
        awareness=85,
        throw_accuracy=82,
        throw_power=80,
        agility=75,
    )

    # Create QB view (me)
    qb = PlayerView(
        id="QB1",
        team=Team.OFFENSE,
        position=Position.QB,
        pos=qb_pos,
        velocity=Vec2(0, 0),
        facing=Vec2(0, 1),
        has_ball=True,
        is_engaged=False,
    )

    # Create receiver views
    teammates = []
    for i, r in enumerate(receivers):
        recv = PlayerView(
            id=r.get('id', f'WR{i+1}'),
            team=Team.OFFENSE,
            position=r.get('position', Position.WR),
            pos=r['pos'],
            velocity=r.get('velocity', Vec2(0, 2)),
            facing=Vec2(0, 1),
            has_ball=False,
            is_engaged=False,
        )
        teammates.append(recv)

    # Create defender views
    opponents = []
    for i, d in enumerate(defenders):
        defender = PlayerView(
            id=d.get('id', f'DB{i+1}'),
            team=Team.DEFENSE,
            position=d.get('position', Position.CB),
            pos=d['pos'],
            velocity=d.get('velocity', Vec2(0, 0)),
            facing=Vec2(0, -1),
            has_ball=False,
            is_engaged=False,
        )
        opponents.append(defender)

    return WorldState(
        me=qb,
        teammates=teammates,
        opponents=opponents,
        ball_pos=qb_pos,
        los_y=los_y,
        time_since_snap=time_since_snap,
        current_time=time_since_snap,
        tick=int(time_since_snap * 60),
        phase=PlayPhase.ACTIVE,
    ), qb_attrs


def run_targeting_analysis():
    """Run multiple scenarios and show who gets targeted."""

    print("=" * 60)
    print("QB TARGETING ANALYSIS")
    print("=" * 60)

    # Scenario 1: All receivers equally open
    print("\n--- Scenario 1: All receivers equally open (3 yard separation) ---")
    receivers = [
        {'id': 'X_WR', 'pos': Vec2(-15, 15), 'position': Position.WR},  # Outside left
        {'id': 'SLOT_L', 'pos': Vec2(-5, 12), 'position': Position.WR},  # Slot left
        {'id': 'SLOT_R', 'pos': Vec2(5, 12), 'position': Position.WR},   # Slot right
        {'id': 'Z_WR', 'pos': Vec2(15, 15), 'position': Position.WR},   # Outside right
    ]
    # Defenders 3 yards behind each receiver
    defenders = [
        {'id': 'CB1', 'pos': Vec2(-15, 18)},
        {'id': 'CB2', 'pos': Vec2(-5, 15)},
        {'id': 'CB3', 'pos': Vec2(5, 15)},
        {'id': 'CB4', 'pos': Vec2(15, 18)},
    ]

    world, attrs = create_mock_world(receivers, defenders)
    world.me.attributes = attrs

    evals = _evaluate_receivers(world)
    print(f"\nReceiver evaluations ({len(evals)} found):")
    for e in evals:
        print(f"  {e.player_id}: sep={e.separation:.1f}yd, status={e.status.value}, read_order={e.read_order}")

    # Test read progression
    print("\nRead progression test:")
    for read_num in [1, 2, 3, 4]:
        best, is_antic, reason = _find_best_receiver(evals, read_num, PressureLevel.CLEAN, attrs.throw_accuracy)
        if best:
            print(f"  Read {read_num}: Target={best.player_id}, reason='{reason}'")
        else:
            print(f"  Read {read_num}: No target, reason='{reason}'")

    # Scenario 2: Only slot receiver open
    print("\n--- Scenario 2: Only SLOT_R open (others covered) ---")
    receivers = [
        {'id': 'X_WR', 'pos': Vec2(-15, 15), 'position': Position.WR},
        {'id': 'SLOT_L', 'pos': Vec2(-5, 12), 'position': Position.WR},
        {'id': 'SLOT_R', 'pos': Vec2(5, 12), 'position': Position.WR},
        {'id': 'Z_WR', 'pos': Vec2(15, 15), 'position': Position.WR},
    ]
    # Tight coverage on all except SLOT_R
    defenders = [
        {'id': 'CB1', 'pos': Vec2(-15, 15.2)},  # On X
        {'id': 'CB2', 'pos': Vec2(-5, 12.2)},   # On SLOT_L
        {'id': 'CB3', 'pos': Vec2(5, 16)},      # Behind SLOT_R (4 yards!)
        {'id': 'CB4', 'pos': Vec2(15, 15.2)},   # On Z
    ]

    world, attrs = create_mock_world(receivers, defenders)
    world.me.attributes = attrs

    evals = _evaluate_receivers(world)
    print(f"\nReceiver evaluations:")
    for e in evals:
        print(f"  {e.player_id}: sep={e.separation:.1f}yd, status={e.status.value}")

    best, is_antic, reason = _find_best_receiver(evals, 1, PressureLevel.CLEAN, attrs.throw_accuracy)
    print(f"\nTarget: {best.player_id if best else 'None'}, reason: {reason}")

    # Scenario 3: Run 20 "plays" with random coverage
    print("\n--- Scenario 3: 20 plays with varying coverage ---")
    import random
    target_counts = defaultdict(int)
    reason_counts = defaultdict(int)

    for play_num in range(20):
        receivers = [
            {'id': 'X_WR', 'pos': Vec2(-15, 15), 'position': Position.WR},
            {'id': 'SLOT_L', 'pos': Vec2(-5, 12), 'position': Position.WR},
            {'id': 'SLOT_R', 'pos': Vec2(5, 12), 'position': Position.WR},
            {'id': 'Z_WR', 'pos': Vec2(15, 15), 'position': Position.WR},
        ]
        # Random separation for each defender (0-5 yards behind)
        defenders = [
            {'id': 'CB1', 'pos': Vec2(-15, 15 + random.uniform(0, 5))},
            {'id': 'CB2', 'pos': Vec2(-5, 12 + random.uniform(0, 5))},
            {'id': 'CB3', 'pos': Vec2(5, 12 + random.uniform(0, 5))},
            {'id': 'CB4', 'pos': Vec2(15, 15 + random.uniform(0, 5))},
        ]

        world, attrs = create_mock_world(receivers, defenders)
        world.me.attributes = attrs

        evals = _evaluate_receivers(world)
        best, is_antic, reason = _find_best_receiver(evals, 1, PressureLevel.CLEAN, attrs.throw_accuracy)

        if best:
            target_counts[best.player_id] += 1
            reason_counts[reason.split(':')[0] if ':' in reason else reason] += 1

    print("\nTarget distribution (20 plays):")
    for target, count in sorted(target_counts.items(), key=lambda x: -x[1]):
        print(f"  {target}: {count} ({count*5}%)")

    print("\nReason distribution:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    # Diagnosis
    print("\n" + "=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)
    print("""
The issue: read_order is hardcoded to 1 for all receivers in qb_brain.py.

This means:
- All receivers match "read 1"
- The first one evaluated (typically first in teammates list) is chosen
- Read progression (reads 2, 3, 4) never finds a match

FIX NEEDED:
1. Add read_order to PlayerView in orchestrator.py (Live Sim Agent)
2. Populate it from the route assignment
3. Update qb_brain to use teammate.read_order instead of hardcoding 1
""")


if __name__ == '__main__':
    run_targeting_analysis()
