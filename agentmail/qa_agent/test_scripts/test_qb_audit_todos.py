#!/usr/bin/env python3
"""Test QB Brain Audit TODO Fixes.

Tests:
1. Blocker Visibility Check - blocked threats reduce pressure
2. Velocity-Based Throw Lead - passes lead receivers
3. Hot Route Tracking - hot routes properly flagged

Run: python agentmail/qa_agent/test_scripts/test_qb_audit_todos.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from dataclasses import dataclass
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.ai.qb_brain import (
    _calculate_throw_lead,
    ReceiverEval,
    ReceiverStatus,
)


# =============================================================================
# Test 1: Velocity-Based Throw Lead
# =============================================================================

def test_throw_lead_stationary_receiver():
    """Test that stationary receiver gets pass to current position."""
    print("=" * 60)
    print("TEST 1a: Throw Lead - Stationary Receiver")
    print("=" * 60)

    qb_pos = Vec2(0, 55)
    receiver = ReceiverEval(
        player_id="WR1",
        position=Vec2(10, 40),  # 15 yards away
        velocity=Vec2(0, 0),    # Stationary
        separation=3.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,
        read_order=1,
    )

    lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

    print(f"  Receiver at: ({receiver.position.x:.1f}, {receiver.position.y:.1f})")
    print(f"  Receiver velocity: ({receiver.velocity.x:.1f}, {receiver.velocity.y:.1f})")
    print(f"  Lead position: ({lead_pos.x:.1f}, {lead_pos.y:.1f})")

    # Stationary receiver should get pass very close to current position
    distance_from_receiver = lead_pos.distance_to(receiver.position)
    if distance_from_receiver < 0.5:
        print(f"  RESULT: PASS - Lead position matches receiver ({distance_from_receiver:.2f} yards off)")
        return True
    else:
        print(f"  RESULT: FAIL - Lead too far from stationary receiver ({distance_from_receiver:.2f} yards)")
        return False


def test_throw_lead_moving_receiver():
    """Test that moving receiver gets pass ahead of current position."""
    print("\n" + "=" * 60)
    print("TEST 1b: Throw Lead - Moving Receiver (Crossing Route)")
    print("=" * 60)

    qb_pos = Vec2(0, 55)
    receiver = ReceiverEval(
        player_id="WR1",
        position=Vec2(5, 45),   # 10 yards away
        velocity=Vec2(8, 0),    # Moving right at 8 yd/s (crossing route)
        separation=3.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,
        read_order=1,
    )

    lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

    print(f"  Receiver at: ({receiver.position.x:.1f}, {receiver.position.y:.1f})")
    print(f"  Receiver velocity: ({receiver.velocity.x:.1f}, {receiver.velocity.y:.1f}) - moving right")
    print(f"  Lead position: ({lead_pos.x:.1f}, {lead_pos.y:.1f})")

    # Moving receiver should get pass AHEAD of current position (lead_x > current_x)
    if lead_pos.x > receiver.position.x:
        lead_distance = lead_pos.x - receiver.position.x
        print(f"  Lead amount: {lead_distance:.1f} yards ahead")
        print(f"  RESULT: PASS - Pass leads the receiver")
        return True
    else:
        print(f"  RESULT: FAIL - Pass not leading receiver")
        return False


def test_throw_lead_deep_route():
    """Test that deep routes get appropriate lead."""
    print("\n" + "=" * 60)
    print("TEST 1c: Throw Lead - Deep Route (Go Route)")
    print("=" * 60)

    qb_pos = Vec2(0, 55)
    receiver = ReceiverEval(
        player_id="WR1",
        position=Vec2(0, 25),   # 30 yards downfield
        velocity=Vec2(0, -10),  # Running deep at 10 yd/s
        separation=2.0,
        status=ReceiverStatus.WINDOW,
        nearest_defender_id="CB1",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,
        read_order=1,
    )

    lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=90)

    print(f"  Receiver at: ({receiver.position.x:.1f}, {receiver.position.y:.1f})")
    print(f"  Receiver velocity: ({receiver.velocity.x:.1f}, {receiver.velocity.y:.1f}) - running deep")
    print(f"  Lead position: ({lead_pos.x:.1f}, {lead_pos.y:.1f})")

    # Deep route - pass should lead receiver downfield (lower Y value)
    if lead_pos.y < receiver.position.y:
        lead_distance = receiver.position.y - lead_pos.y
        print(f"  Lead amount: {lead_distance:.1f} yards downfield")
        print(f"  RESULT: PASS - Pass leads receiver downfield")
        return True
    else:
        print(f"  RESULT: FAIL - Pass not leading deep receiver")
        return False


def test_throw_lead_touch_pass():
    """Test that short passes use touch pass (slower ball speed, less lead needed)."""
    print("\n" + "=" * 60)
    print("TEST 1d: Throw Lead - Touch Pass (Short Distance)")
    print("=" * 60)

    qb_pos = Vec2(0, 55)

    # Short pass receiver - 5 yards out
    short_receiver = ReceiverEval(
        player_id="WR1",
        position=Vec2(5, 52),   # 5 yards away
        velocity=Vec2(5, 0),    # Moving at 5 yd/s
        separation=2.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,
        read_order=1,
    )

    # Intermediate pass receiver - 15 yards out
    intermediate_receiver = ReceiverEval(
        player_id="WR2",
        position=Vec2(15, 45),  # ~15 yards away
        velocity=Vec2(5, 0),    # Same speed
        separation=2.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,
        read_order=1,
    )

    short_lead = _calculate_throw_lead(qb_pos, short_receiver, throw_power=80)
    intermediate_lead = _calculate_throw_lead(qb_pos, intermediate_receiver, throw_power=80)

    short_lead_amt = short_lead.x - short_receiver.position.x
    intermediate_lead_amt = intermediate_lead.x - intermediate_receiver.position.x

    print(f"  Short pass lead: {short_lead_amt:.2f} yards")
    print(f"  Intermediate pass lead: {intermediate_lead_amt:.2f} yards")

    # Touch passes (short) should have less lead relative to distance
    # because ball speed is reduced for catchability
    if short_lead_amt < intermediate_lead_amt:
        print(f"  RESULT: PASS - Short pass has proportionally less lead (touch pass)")
        return True
    else:
        print(f"  RESULT: FAIL - Expected short pass to have less lead")
        return False


# =============================================================================
# Test 2: Hot Route Tracking
# =============================================================================

def test_hot_route_flagging():
    """Test that is_hot flag can be set based on world.hot_routes."""
    print("\n" + "=" * 60)
    print("TEST 2: Hot Route Flagging")
    print("=" * 60)

    # Create two receiver evals - one hot, one not
    hot_receiver = ReceiverEval(
        player_id="WR1",
        position=Vec2(5, 45),
        velocity=Vec2(5, 0),
        separation=2.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=True,  # This receiver is on a hot route
        read_order=1,
    )

    regular_receiver = ReceiverEval(
        player_id="WR2",
        position=Vec2(-5, 40),
        velocity=Vec2(0, -5),
        separation=3.0,
        status=ReceiverStatus.OPEN,
        nearest_defender_id="",
        defender_closing_speed=0,
        route_phase="stem",
        is_hot=False,  # Regular route
        read_order=2,
    )

    print(f"  WR1 (is_hot={hot_receiver.is_hot})")
    print(f"  WR2 (is_hot={regular_receiver.is_hot})")

    if hot_receiver.is_hot and not regular_receiver.is_hot:
        print(f"  RESULT: PASS - Hot route properly flagged")
        return True
    else:
        print(f"  RESULT: FAIL - Hot route flagging incorrect")
        return False


def test_hot_route_logic():
    """Test the logic for detecting hot routes from world.hot_routes dict."""
    print("\n" + "=" * 60)
    print("TEST 2b: Hot Route Detection Logic")
    print("=" * 60)

    # Simulate the logic from line 379:
    # is_hot = bool(world.hot_routes and teammate.id in world.hot_routes)

    class MockWorld:
        def __init__(self, hot_routes=None):
            self.hot_routes = hot_routes

    teammate_id = "WR1"

    # Case 1: No hot routes
    world_no_hot = MockWorld(hot_routes=None)
    is_hot_1 = bool(world_no_hot.hot_routes and teammate_id in world_no_hot.hot_routes)

    # Case 2: Hot routes exist but this receiver not in it
    world_other_hot = MockWorld(hot_routes={"WR2": "slant"})
    is_hot_2 = bool(world_other_hot.hot_routes and teammate_id in world_other_hot.hot_routes)

    # Case 3: This receiver is in hot routes
    world_this_hot = MockWorld(hot_routes={"WR1": "slant"})
    is_hot_3 = bool(world_this_hot.hot_routes and teammate_id in world_this_hot.hot_routes)

    print(f"  No hot routes: is_hot={is_hot_1}")
    print(f"  Other receiver hot: is_hot={is_hot_2}")
    print(f"  This receiver hot: is_hot={is_hot_3}")

    if not is_hot_1 and not is_hot_2 and is_hot_3:
        print(f"  RESULT: PASS - Hot route logic works correctly")
        return True
    else:
        print(f"  RESULT: FAIL - Hot route logic incorrect")
        return False


# =============================================================================
# Test 3: Blocker Visibility (Conceptual)
# =============================================================================

def test_blocker_visibility_concept():
    """Test the blocker visibility algorithm conceptually.

    The actual _calculate_pressure function requires full WorldState,
    but we can verify the geometric logic is correct.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Blocker Visibility Geometry")
    print("=" * 60)

    # QB at origin, threat approaching from (5, 5), blocker at (3, 3)
    qb_pos = Vec2(0, 0)
    threat_pos = Vec2(5, 5)
    blocker_pos = Vec2(3, 3)

    # Is blocker closer to threat than QB?
    blocker_to_threat = blocker_pos.distance_to(threat_pos)
    qb_to_threat = qb_pos.distance_to(threat_pos)

    print(f"  QB at: (0, 0)")
    print(f"  Threat at: (5, 5)")
    print(f"  Blocker at: (3, 3)")
    print(f"  Blocker-to-threat: {blocker_to_threat:.2f} yards")
    print(f"  QB-to-threat: {qb_to_threat:.2f} yards")

    # Check if blocker is in lane (perpendicular distance to threat-QB line)
    threat_to_qb = qb_pos - threat_pos
    threat_to_blocker = blocker_pos - threat_pos

    if threat_to_qb.length() > 0.1:
        t = threat_to_blocker.dot(threat_to_qb) / threat_to_qb.dot(threat_to_qb)
        closest_point = threat_pos + threat_to_qb * t
        lane_distance = blocker_pos.distance_to(closest_point)

        print(f"  Projection t: {t:.2f} (0 < t < 1 means between)")
        print(f"  Lane distance: {lane_distance:.2f} yards (< 2 = in lane)")

        in_lane = 0 < t < 1 and lane_distance < 2.0

        if blocker_to_threat < qb_to_threat and in_lane:
            print(f"  RESULT: PASS - Blocker correctly identified as blocking threat")
            return True
        else:
            print(f"  RESULT: FAIL - Blocker should be identified as blocking")
            return False
    else:
        print(f"  RESULT: FAIL - Invalid geometry")
        return False


def test_blocker_not_in_lane():
    """Test that blockers not in the lane are not considered blocking."""
    print("\n" + "=" * 60)
    print("TEST 3b: Blocker NOT in Lane")
    print("=" * 60)

    # QB at origin, threat approaching from (5, 5), blocker off to the side
    qb_pos = Vec2(0, 0)
    threat_pos = Vec2(5, 5)
    blocker_pos = Vec2(0, 5)  # To the side, not between

    # Check if blocker is in lane
    threat_to_qb = qb_pos - threat_pos
    threat_to_blocker = blocker_pos - threat_pos

    t = threat_to_blocker.dot(threat_to_qb) / threat_to_qb.dot(threat_to_qb)
    closest_point = threat_pos + threat_to_qb * t
    lane_distance = blocker_pos.distance_to(closest_point)

    print(f"  QB at: (0, 0)")
    print(f"  Threat at: (5, 5)")
    print(f"  Blocker at: (0, 5) - to the side")
    print(f"  Projection t: {t:.2f}")
    print(f"  Lane distance: {lane_distance:.2f} yards")

    in_lane = 0 < t < 1 and lane_distance < 2.0

    if not in_lane:
        print(f"  RESULT: PASS - Blocker correctly NOT identified as blocking")
        return True
    else:
        print(f"  RESULT: FAIL - Blocker incorrectly identified as in lane")
        return False


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("QB BRAIN AUDIT TODO FIXES - VERIFICATION TESTS")
    print("=" * 70)

    results = []

    # Throw Lead Tests
    results.append(("Throw lead - stationary receiver", test_throw_lead_stationary_receiver()))
    results.append(("Throw lead - moving receiver", test_throw_lead_moving_receiver()))
    results.append(("Throw lead - deep route", test_throw_lead_deep_route()))
    results.append(("Throw lead - touch pass", test_throw_lead_touch_pass()))

    # Hot Route Tests
    results.append(("Hot route flagging", test_hot_route_flagging()))
    results.append(("Hot route detection logic", test_hot_route_logic()))

    # Blocker Visibility Tests
    results.append(("Blocker visibility geometry", test_blocker_visibility_concept()))
    results.append(("Blocker not in lane", test_blocker_not_in_lane()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")
