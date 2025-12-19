#!/usr/bin/env python3
"""Test blocking system - OL vs DL engagements.

Tests:
1. Engagement happens when players are close
2. Block sheds occur with weak OL or long plays
3. Sacks result when DL sheds and reaches QB

Run: python agentmail/qa_agent/test_scripts/test_blocking_system.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain


def test_engagement():
    """Test that OL and DL engage when close."""
    print("=" * 60)
    print("TEST 1: Blocking Engagement")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=85, throw_accuracy=85),
    )

    lt = Player(
        id="LT", name="Left Tackle", position=Position.LT, team=Team.OFFENSE,
        pos=Vec2(-3, -2),
        attributes=PlayerAttributes(block_power=82, block_finesse=80, strength=85),
    )

    de = Player(
        id="DE1", name="Defensive End", position=Position.DE, team=Team.DEFENSE,
        pos=Vec2(-3, 0),  # Closer than default - only 2 yards away
        attributes=PlayerAttributes(pass_rush=85, speed=82, strength=80),
    )

    wr = Player(
        id="WR1", name="Receiver", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(speed=90, catching=85),
    )

    cb = Player(
        id="CB1", name="Cornerback", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(15, 7),
        attributes=PlayerAttributes(speed=88, man_coverage=85),
    )

    config = PlayConfig(
        routes={"WR1": "go"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.5,
        throw_target="WR1",
        max_duration=4.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, lt, wr], [de, cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("LT", ol_brain)
    orch.register_brain("DE1", dl_brain)

    result = orch.run()

    lt_final = orch._get_player("LT")
    de_final = orch._get_player("DE1")
    dist = lt_final.pos.distance_to(de_final.pos)

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print()
    print("  Final Positions:")
    print(f"    LT: ({lt_final.pos.x:.1f}, {lt_final.pos.y:.1f})")
    print(f"    DE: ({de_final.pos.x:.1f}, {de_final.pos.y:.1f})")
    print(f"    Distance: {dist:.1f} yards")
    print()

    # Check for block events
    block_events = [e for e in result.events if 'block' in e.description.lower() or 'shed' in e.description.lower()]
    if block_events:
        print("  Block Events:")
        for e in block_events:
            print(f"    [{e.time:.2f}s] {e.description}")
    else:
        print("  No block events (expected for quick pass)")

    if dist < 2.0:
        print("\n  RESULT: PASS - Players engaged (distance < 2 yards)")
    else:
        print(f"\n  RESULT: CHECK - Players {dist:.1f} yards apart")

    return result


def test_shed_with_weak_ol():
    """Test block shed with weaker OL."""
    print("\n" + "=" * 60)
    print("TEST 2: Block Shed (Weak OL)")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=85, throw_accuracy=85),
    )

    # Weak tackle
    lt = Player(
        id="LT", name="Weak Tackle", position=Position.LT, team=Team.OFFENSE,
        pos=Vec2(-3, -1),  # Closer to DE
        attributes=PlayerAttributes(block_power=60, block_finesse=55, strength=65),  # Weak!
    )

    # Strong pass rusher
    de = Player(
        id="DE1", name="Elite Edge", position=Position.DE, team=Team.DEFENSE,
        pos=Vec2(-3, 0),  # Close to LT
        attributes=PlayerAttributes(pass_rush=95, speed=88, strength=90, agility=85),  # Elite!
    )

    wr = Player(
        id="WR1", name="Receiver", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(speed=90, catching=85),
    )

    cb = Player(
        id="CB1", name="Cornerback", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(15, 10),  # Deep cushion
        attributes=PlayerAttributes(speed=88, man_coverage=85),
    )

    config = PlayConfig(
        routes={"WR1": "go"},
        man_assignments={"CB1": "WR1"},
        throw_timing=None,  # No scripted throw - let play develop
        max_duration=6.0,  # Longer play
    )

    orch = Orchestrator()
    orch.setup_play([qb, lt, wr], [de, cb], config)
    orch.register_brain("QB1", qb_brain)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("LT", ol_brain)
    orch.register_brain("DE1", dl_brain)

    result = orch.run()

    lt_final = orch._get_player("LT")
    de_final = orch._get_player("DE1")
    qb_final = orch._get_player("QB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print()
    print("  Final Positions:")
    print(f"    QB: ({qb_final.pos.x:.1f}, {qb_final.pos.y:.1f})")
    print(f"    LT: ({lt_final.pos.x:.1f}, {lt_final.pos.y:.1f})")
    print(f"    DE: ({de_final.pos.x:.1f}, {de_final.pos.y:.1f})")

    # Check for shed and sack events
    for e in result.events:
        desc = e.description.lower()
        if 'shed' in desc or 'sack' in desc or 'block' in desc:
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    if result.outcome == "sack":
        print("\n  RESULT: PASS - DE shed block and sacked QB!")
    elif 'block_shed' in [e.type.value for e in result.events]:
        print("\n  RESULT: PARTIAL - Block shed occurred but no sack")
    else:
        print("\n  RESULT: CHECK - No shed detected")

    return result


def test_long_developing_play():
    """Test blocking on a long developing play (deep route)."""
    print("\n" + "=" * 60)
    print("TEST 3: Long Developing Play")
    print("=" * 60)

    qb = Player(
        id="QB1", name="Quarterback", position=Position.QB, team=Team.OFFENSE,
        pos=Vec2(0, -5), has_ball=True,
        attributes=PlayerAttributes(speed=78, throw_power=90, throw_accuracy=85),
    )

    lt = Player(
        id="LT", name="Left Tackle", position=Position.LT, team=Team.OFFENSE,
        pos=Vec2(-3, -2),
        attributes=PlayerAttributes(block_power=80, block_finesse=78, strength=82),
    )

    de = Player(
        id="DE1", name="Defensive End", position=Position.DE, team=Team.DEFENSE,
        pos=Vec2(-3, 1),
        attributes=PlayerAttributes(pass_rush=82, speed=82, strength=78),
    )

    wr = Player(
        id="WR1", name="Receiver", position=Position.WR, team=Team.OFFENSE,
        pos=Vec2(15, 0),
        attributes=PlayerAttributes(speed=92, catching=85),
    )

    cb = Player(
        id="CB1", name="Cornerback", position=Position.CB, team=Team.DEFENSE,
        pos=Vec2(15, 7),
        attributes=PlayerAttributes(speed=90, man_coverage=85),
    )

    config = PlayConfig(
        routes={"WR1": "post"},  # Deep post route
        man_assignments={"CB1": "WR1"},
        throw_timing=3.0,  # Late throw - gives time for pressure
        throw_target="WR1",
        max_duration=6.0,
    )

    orch = Orchestrator()
    orch.setup_play([qb, lt, wr], [de, cb], config)
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)
    orch.register_brain("LT", ol_brain)
    orch.register_brain("DE1", dl_brain)

    result = orch.run()

    lt_final = orch._get_player("LT")
    de_final = orch._get_player("DE1")
    qb_final = orch._get_player("QB1")

    print(f"\n  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s")
    print()
    print("  Final Positions:")
    print(f"    QB: ({qb_final.pos.x:.1f}, {qb_final.pos.y:.1f})")
    print(f"    LT: ({lt_final.pos.x:.1f}, {lt_final.pos.y:.1f})")
    print(f"    DE: ({de_final.pos.x:.1f}, {de_final.pos.y:.1f})")

    # Check all block-related events
    for e in result.events:
        desc = e.description.lower()
        if any(word in desc for word in ['shed', 'sack', 'block', 'pressure', 'rush']):
            print(f"    [{e.time:.2f}s] {e.type.value}: {e.description}")

    return result


if __name__ == "__main__":
    print("Testing BlockResolver System")
    print()

    test_engagement()
    test_shed_with_weak_ol()
    test_long_developing_play()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
The blocking system should:
1. Engage OL and DL when within 1.5 yards
2. Resolve block vs rush action each tick
3. Accumulate shed progress when DL is winning
4. Trigger shed event when progress reaches 100%
5. Allow sacks when DE reaches QB after shedding
""")
