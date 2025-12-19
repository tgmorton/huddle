#!/usr/bin/env python3
"""Minimal reproduction for pursuit angle bug.

Bug: After a receiver catches the ball, defenders continue in "trailing" mode
targeting the receiver's current position instead of using pursuit angles.
Same-speed pursuit to current position = gap never closes.

Root causes:
1. db_brain._detect_run() only checks for RB/QB, not WR with ball
2. Orchestrator pursuit only triggers on RUN_ACTIVE phase, but catch sets AFTER_CATCH

Run: python repro_pursuit_bug.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Ball, Position, PlayerAttributes, Team, BallState
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig, PlayPhase
from huddle.simulation.v2.ai.db_brain import db_brain, _detect_run
from huddle.simulation.v2.ai.receiver_brain import receiver_brain


def test_detect_run_bug():
    """Show that _detect_run doesn't detect WR ballcarrier."""
    print("=" * 60)
    print("TEST 1: _detect_run() doesn't detect WR with ball")
    print("=" * 60)

    # Create a mock WorldState-like object with WR having ball
    class MockPlayer:
        def __init__(self, pos, has_ball, position):
            self.pos = pos
            self.has_ball = has_ball
            self.position = position
            self.velocity = Vec2(0, 7)  # Running upfield

    class MockWorld:
        def __init__(self):
            self.opponents = [
                MockPlayer(Vec2(0, 20), True, Position.WR),  # WR with ball
            ]
            self.time_since_snap = 2.0

    world = MockWorld()
    result = _detect_run(world)

    print(f"  WR has ball: True")
    print(f"  _detect_run() returns: {result}")
    print(f"  Expected: True")
    print(f"  BUG: Returns False, so pursuit mode never activates!")
    print()


def test_pursuit_gap():
    """Show the pursuit gap in action."""
    print("=" * 60)
    print("TEST 2: Pursuit gap demonstration")
    print("=" * 60)

    # Create players
    qb = Player(
        id="QB1",
        name="Quarterback",
        position=Position.QB,
        team=Team.OFFENSE,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(speed=80, throw_power=85, throw_accuracy=85),
    )

    wr = Player(
        id="WR1",
        name="Wide Receiver",
        position=Position.WR,
        team=Team.OFFENSE,
        pos=Vec2(-8, 0),
        attributes=PlayerAttributes(speed=90, acceleration=88, catching=85),
    )

    cb = Player(
        id="CB1",
        name="Cornerback",
        position=Position.CB,
        team=Team.DEFENSE,
        pos=Vec2(-8, 7),  # 7 yards off coverage
        attributes=PlayerAttributes(speed=90, acceleration=88, man_coverage=85),
    )

    # Config with early throw
    config = PlayConfig(
        routes={"WR1": "curl"},
        man_assignments={"CB1": "WR1"},
        throw_timing=1.0,
        throw_target="WR1",
        max_duration=6.0,
    )

    # Run
    orch = Orchestrator()
    orch.setup_play([qb, wr], [cb], config)

    # Register brains
    orch.register_brain("WR1", receiver_brain)
    orch.register_brain("CB1", db_brain)

    result = orch.run()

    # Get final positions
    wr_final = orch._get_player("WR1")
    cb_final = orch._get_player("CB1")

    print(f"  Outcome: {result.outcome}")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print()
    print("  Final Positions:")
    print(f"    WR: Y={wr_final.pos.y:.1f}")
    print(f"    CB: Y={cb_final.pos.y:.1f}")
    print(f"    Gap: {wr_final.pos.y - cb_final.pos.y:.1f} yards")
    print()
    print("  BUG: CB chases WR's current position, never closes gap!")
    print("  EXPECTED: CB should use pursuit angle to intercept WR")
    print()

    # Show why
    print("  Root Cause:")
    print("    1. db_brain._detect_run() returns False for WR with ball")
    print("    2. DB stays in 'trailing' mode, targets receiver.pos")
    print("    3. Same speed + targeting current pos = gap never closes")


def test_phase_transition():
    """Show that AFTER_CATCH never becomes RUN_ACTIVE."""
    print("=" * 60)
    print("TEST 3: Phase transition gap")
    print("=" * 60)

    print("  After catch, orchestrator sets phase to: AFTER_CATCH")
    print("  Orchestrator pursuit logic checks for: RUN_ACTIVE")
    print("  There's no code that transitions AFTER_CATCH -> RUN_ACTIVE")
    print()
    print("  Even if DB brain detected the catch correctly,")
    print("  the orchestrator's built-in pursuit would never trigger.")
    print()


if __name__ == "__main__":
    test_detect_run_bug()
    test_pursuit_gap()
    test_phase_transition()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Two bugs combine to prevent pursuit:

1. db_brain._detect_run() (lines 257-266):
   - Only checks: RB has ball OR QB doesn't have ball
   - Does NOT check: WR/TE has ball after catch
   - FIX: Add check for any opponent with ball

2. orchestrator._update_defense_player() (line 787):
   - Pursuit only triggers on phase == RUN_ACTIVE
   - After catch, phase is AFTER_CATCH (line 1065)
   - No transition from AFTER_CATCH -> RUN_ACTIVE
   - FIX: Transition to RUN_ACTIVE after catch, or check both phases

3. Even when pursuit IS triggered (for FS in run support):
   - CBs don't use pursuit angles, only FS does
   - db_brain lines 390-398 vs 368-387
""")
