#!/usr/bin/env python3
"""Test OL Coordination Features.

Tests:
1. MIKE Identification - Center identifies MIKE LB for different fronts
2. Combo Blocks - Two OL work together on DL, one climbs to LB
3. Stunt Pickup - OL detect and switch assignments on DL stunts

Run: python agentmail/qa_agent/test_scripts/test_ol_coordination.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from unittest.mock import MagicMock

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Position, PlayerAttributes, Team
from huddle.simulation.v2.ai.ol_brain import (
    _identify_mike,
    _find_combo_opportunity,
    _should_climb_from_combo,
    _detect_stunt,
    _get_stunt_pickup_assignment,
    _ol_states,
    OLState,
    _get_state,
    _reset_state,
)


class MockPlayerView:
    """Simple mock for PlayerView."""
    def __init__(self, id, pos, position, team, velocity=None):
        self.id = id
        self.pos = pos
        self.position = position
        self.team = team
        self.velocity = velocity or Vec2(0, 0)


def create_world_state(my_player, teammates, opponents, time_since_snap=0.0, los_y=0.0):
    """Helper to create mock WorldState for testing."""
    # Create mock world
    world = MagicMock()

    # Mock 'me' player
    world.me = MagicMock()
    world.me.id = my_player.id
    world.me.pos = my_player.pos
    world.me.position = my_player.position
    world.me.team = my_player.team

    # Convert teammates to mock PlayerViews
    world.teammates = []
    for tm in teammates:
        view = MockPlayerView(
            id=tm.id,
            pos=tm.pos,
            position=tm.position,
            team=tm.team,
            velocity=getattr(tm, 'velocity', Vec2(0, 0)),
        )
        world.teammates.append(view)

    # Convert opponents to mock PlayerViews
    world.opponents = []
    for opp in opponents:
        view = MockPlayerView(
            id=opp.id,
            pos=opp.pos,
            position=opp.position,
            team=opp.team,
            velocity=getattr(opp, 'velocity', Vec2(0, 0)),
        )
        world.opponents.append(view)

    world.time_since_snap = time_since_snap
    world.los_y = los_y

    return world


def test_mike_identification_4_3():
    """Test MIKE identification in 4-3 front."""
    print("=" * 60)
    print("TEST 1a: MIKE Identification - 4-3 Front")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    # Center
    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)

    # 4-3 Defense: 4 DL, 3 LBs
    opponents = [
        # DL
        Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-6, 1), attributes=attrs),
        Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-2, 1), attributes=attrs),
        Player(id="DT2", position=Position.DT, team=Team.DEFENSE, pos=Vec2(2, 1), attributes=attrs),
        Player(id="DE2", position=Position.DE, team=Team.DEFENSE, pos=Vec2(6, 1), attributes=attrs),
        # LBs
        Player(id="WLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(-4, 5), attributes=attrs),
        Player(id="MLB", position=Position.MLB, team=Team.DEFENSE, pos=Vec2(0, 5), attributes=attrs),  # Center LB
        Player(id="SLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(4, 5), attributes=attrs),
    ]

    world = create_world_state(center, [], opponents)
    call = _identify_mike(world)

    print(f"  Front type: {call.front_type}")
    print(f"  MIKE ID: {call.mike_id}")
    print(f"  Blitz threat: {call.blitz_threat}")

    if call.front_type == "4-3" and call.mike_id == "MLB":
        print("  RESULT: PASS - Correctly identified 4-3 front and MLB as MIKE")
        return True
    else:
        print(f"  RESULT: FAIL - Expected 4-3 front, MLB as MIKE")
        return False


def test_mike_identification_3_4():
    """Test MIKE identification in 3-4 front."""
    print("\n" + "=" * 60)
    print("TEST 1b: MIKE Identification - 3-4 Front")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)

    # 3-4 Defense: 3 DL, 4 LBs
    opponents = [
        # DL
        Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-4, 1), attributes=attrs),
        Player(id="NT", position=Position.NT, team=Team.DEFENSE, pos=Vec2(0, 1), attributes=attrs),
        Player(id="DE2", position=Position.DE, team=Team.DEFENSE, pos=Vec2(4, 1), attributes=attrs),
        # LBs
        Player(id="LOLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(-6, 5), attributes=attrs),
        Player(id="LILB", position=Position.ILB, team=Team.DEFENSE, pos=Vec2(-1.5, 5), attributes=attrs),  # Central
        Player(id="RILB", position=Position.ILB, team=Team.DEFENSE, pos=Vec2(1.5, 5), attributes=attrs),
        Player(id="ROLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(6, 5), attributes=attrs),
    ]

    world = create_world_state(center, [], opponents)
    call = _identify_mike(world)

    print(f"  Front type: {call.front_type}")
    print(f"  MIKE ID: {call.mike_id}")

    if call.front_type == "3-4" and call.mike_id in ["LILB", "RILB"]:
        print("  RESULT: PASS - Correctly identified 3-4 front and ILB as MIKE")
        return True
    else:
        print(f"  RESULT: FAIL - Expected 3-4 front, ILB as MIKE")
        return False


def test_mike_blitz_detection():
    """Test blitz threat detection when LB walks up."""
    print("\n" + "=" * 60)
    print("TEST 1c: MIKE - Blitz Threat Detection")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)

    # 4-3 with walked-up OLB (blitz threat)
    opponents = [
        Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-6, 1), attributes=attrs),
        Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-2, 1), attributes=attrs),
        Player(id="DT2", position=Position.DT, team=Team.DEFENSE, pos=Vec2(2, 1), attributes=attrs),
        Player(id="DE2", position=Position.DE, team=Team.DEFENSE, pos=Vec2(6, 1), attributes=attrs),
        Player(id="WLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(-4, 2), attributes=attrs),  # Walked up!
        Player(id="MLB", position=Position.MLB, team=Team.DEFENSE, pos=Vec2(0, 5), attributes=attrs),
        Player(id="SLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(4, 5), attributes=attrs),
    ]

    world = create_world_state(center, [], opponents, los_y=0)
    call = _identify_mike(world)

    print(f"  Blitz threat: {call.blitz_threat}")
    print(f"  Slide direction: {call.slide_direction}")

    if call.blitz_threat == "left" and call.slide_direction == "right":
        print("  RESULT: PASS - Detected left blitz, called right slide")
        return True
    else:
        print(f"  RESULT: FAIL - Expected left blitz, right slide")
        return False


def test_combo_block_opportunity():
    """Test combo block detection when DL shaded between OL."""
    print("\n" + "=" * 60)
    print("TEST 2a: Combo Block - Opportunity Detection")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    # Left Guard
    lg = Player(id="LG1", position=Position.LG, team=Team.OFFENSE,
                pos=Vec2(-3, 0), attributes=attrs)

    # Teammates
    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)
    lt = Player(id="LT1", position=Position.LT, team=Team.OFFENSE,
                pos=Vec2(-6, 0), attributes=attrs)

    # DT shaded between LG and C
    opponents = [
        Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-1.5, 1), attributes=attrs),
        Player(id="MLB", position=Position.MLB, team=Team.DEFENSE, pos=Vec2(0, 5), attributes=attrs),  # LB to climb to
    ]

    world = create_world_state(lg, [center, lt], opponents)
    partner_id, target_id = _find_combo_opportunity(world)

    print(f"  Combo partner: {partner_id}")
    print(f"  Combo target: {target_id}")

    if partner_id == "C1" and target_id == "DT1":
        print("  RESULT: PASS - Found combo opportunity (LG + C on DT)")
        return True
    else:
        print(f"  RESULT: FAIL - Expected C1/DT1, got {partner_id}/{target_id}")
        return False


def test_combo_climb_timing():
    """Test climb timing from combo block."""
    print("\n" + "=" * 60)
    print("TEST 2b: Combo Block - Climb Timing")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    # Right Guard (higher x position, should be the one to climb)
    rg = Player(id="RG1", position=Position.RG, team=Team.OFFENSE,
                pos=Vec2(3, 0), attributes=attrs)

    # Teammates
    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)

    # DT being driven back
    dt = Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(1.5, 2), attributes=attrs)
    dt.velocity = Vec2(0, 1.0)  # Moving away from QB

    world = create_world_state(rg, [center], [dt], time_since_snap=0.5)

    # Set up combo state
    state = OLState()
    state.combo_partner_id = "C1"
    state.combo_target_id = "DT1"

    should_climb = _should_climb_from_combo(world, state)

    print(f"  DL velocity.y: {dt.velocity.y} (positive = being driven back)")
    print(f"  Should climb: {should_climb}")

    if should_climb:
        print("  RESULT: PASS - RG should climb (DL being driven back)")
        return True
    else:
        print("  RESULT: FAIL - Expected climb trigger")
        return False


def test_stunt_detection():
    """Test detection of T/E stunt."""
    print("\n" + "=" * 60)
    print("TEST 3a: Stunt Detection - T/E Stunt")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    # Left Tackle
    lt = Player(id="LT1", position=Position.LT, team=Team.OFFENSE,
                pos=Vec2(-6, 0), attributes=attrs)

    # DT looping outside (positive x = moving right)
    dt = Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-4, 1), attributes=attrs)
    dt.velocity = Vec2(3.0, 0)  # Moving right (looping)

    # DE crashing inside toward LT
    de = Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-7, 1), attributes=attrs)
    de.velocity = Vec2(2.0, 1.0)  # Moving toward gap

    world = create_world_state(lt, [], [dt, de], time_since_snap=0.5)

    # Set up state - LT was blocking DT
    state = OLState()
    state.assigned_defender_id = "DT1"

    stunt = _detect_stunt(world, state)

    print(f"  DT velocity.x: {dt.velocity.x} (looping)")
    print(f"  DE position: ({de.pos.x:.1f}, {de.pos.y:.1f}) (crashing)")
    print(f"  Stunt detected: {stunt}")

    if stunt == "te_stunt":
        print("  RESULT: PASS - Detected T/E stunt")
        return True
    else:
        print(f"  RESULT: FAIL - Expected te_stunt, got {stunt}")
        return False


def test_stunt_pickup():
    """Test stunt pickup assignment."""
    print("\n" + "=" * 60)
    print("TEST 3b: Stunt Pickup - Assignment Switch")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    # Left Tackle
    lt = Player(id="LT1", position=Position.LT, team=Team.OFFENSE,
                pos=Vec2(-6, 0), attributes=attrs)

    # DT looping (our original guy)
    dt = Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-4, 1), attributes=attrs)
    dt.velocity = Vec2(3.0, 0)

    # DE crashing hard (the one we should pick up)
    # Move DE closer and give it velocity directly toward LT
    de = Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-7, 0.5), attributes=attrs)
    de.velocity = Vec2(3.0, -0.5)  # Moving fast toward LT (needs closing > 1.0)

    world = create_world_state(lt, [], [dt, de], time_since_snap=0.5)

    # Set up state - LT was blocking DT
    state = OLState()
    state.assigned_defender_id = "DT1"

    new_assignment = _get_stunt_pickup_assignment(world, state, "te_stunt")

    print(f"  Original assignment: DT1")
    print(f"  New assignment: {new_assignment}")

    if new_assignment == "DE1":
        print("  RESULT: PASS - Picked up the crasher (DE)")
        return True
    else:
        print(f"  RESULT: FAIL - Expected DE1, got {new_assignment}")
        return False


def test_nickel_mike():
    """Test MIKE identification in Nickel defense."""
    print("\n" + "=" * 60)
    print("TEST 1d: MIKE Identification - Nickel")
    print("=" * 60)

    attrs = PlayerAttributes(speed=80)

    center = Player(id="C1", position=Position.C, team=Team.OFFENSE,
                    pos=Vec2(0, 0), attributes=attrs)

    # Nickel: 4 DL, 2 LBs, extra DB (not counted here)
    opponents = [
        Player(id="DE1", position=Position.DE, team=Team.DEFENSE, pos=Vec2(-6, 1), attributes=attrs),
        Player(id="DT1", position=Position.DT, team=Team.DEFENSE, pos=Vec2(-2, 1), attributes=attrs),
        Player(id="DT2", position=Position.DT, team=Team.DEFENSE, pos=Vec2(2, 1), attributes=attrs),
        Player(id="DE2", position=Position.DE, team=Team.DEFENSE, pos=Vec2(6, 1), attributes=attrs),
        # Only 2 LBs
        Player(id="MLB", position=Position.MLB, team=Team.DEFENSE, pos=Vec2(-1, 5), attributes=attrs),
        Player(id="WLB", position=Position.OLB, team=Team.DEFENSE, pos=Vec2(3, 5), attributes=attrs),
    ]

    world = create_world_state(center, [], opponents)
    call = _identify_mike(world)

    print(f"  Front type: {call.front_type}")
    print(f"  MIKE ID: {call.mike_id}")

    if call.front_type == "nickel":
        print("  RESULT: PASS - Correctly identified Nickel front")
        return True
    else:
        print(f"  RESULT: FAIL - Expected nickel, got {call.front_type}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("OL COORDINATION FEATURES - VERIFICATION TESTS")
    print("=" * 70)

    results = []

    # MIKE Identification
    results.append(("MIKE - 4-3 Front", test_mike_identification_4_3()))
    results.append(("MIKE - 3-4 Front", test_mike_identification_3_4()))
    results.append(("MIKE - Blitz Detection", test_mike_blitz_detection()))
    results.append(("MIKE - Nickel", test_nickel_mike()))

    # Combo Blocks
    results.append(("Combo - Opportunity", test_combo_block_opportunity()))
    results.append(("Combo - Climb Timing", test_combo_climb_timing()))

    # Stunt Pickup
    results.append(("Stunt - Detection", test_stunt_detection()))
    results.append(("Stunt - Pickup", test_stunt_pickup()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")
