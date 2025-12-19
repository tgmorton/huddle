#!/usr/bin/env python3
"""Test Pre-Snap QB Intelligence Features.

Tests:
1. Coverage Shell Identification
2. Blitz Detection
3. Hot Route Logic
4. Protection Calls

Run: python agentmail/qa_agent/test_scripts/test_presnap_qb_intelligence.py
"""
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from unittest.mock import MagicMock
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Position
from huddle.simulation.v2.ai.qb_brain import (
    _identify_coverage_shell,
    _detect_blitz_look,
    _get_hot_route_for_blitz,
    _get_protection_call,
    CoverageShell,
    BlitzLook,
)


class MockPlayer:
    """Mock player for testing."""
    def __init__(self, id: str, pos: Vec2, position: Position):
        self.id = id
        self.pos = pos
        self.position = position


def create_world(los_y: float, opponents: list, teammates: list = None, awareness: int = 85):
    """Create mock WorldState."""
    world = MagicMock()
    world.los_y = los_y
    world.opponents = opponents
    world.teammates = teammates or []
    world.me = MagicMock()
    world.me.attributes = MagicMock()
    world.me.attributes.awareness = awareness
    return world


# =============================================================================
# Test 1: Coverage Shell Identification
# =============================================================================

def test_cover_2_wide_split():
    """Two deep safeties with wide split -> Cover 2."""
    print("=" * 60)
    print("TEST 1a: Cover 2 (Two deep safeties, wide split)")
    print("=" * 60)

    # Two safeties, each 15 yards deep, split 25 yards apart
    opponents = [
        MockPlayer("FS1", Vec2(-12, 35), Position.FS),  # Left safety at y=35 (15 yards deep from LOS at 50)
        MockPlayer("SS1", Vec2(12, 35), Position.SS),   # Right safety at y=35
    ]
    world = create_world(los_y=50, opponents=opponents)

    result = _identify_coverage_shell(world)
    print(f"  Safeties: FS at (-12, 35), SS at (12, 35)")
    print(f"  Split: 24 yards")
    print(f"  Result: {result}")

    if result == CoverageShell.COVER_2:
        print("  RESULT: PASS - Correctly identified Cover 2")
        return True
    else:
        print(f"  RESULT: FAIL - Expected COVER_2, got {result}")
        return False


def test_cover_4_tight_split():
    """Two deep safeties with tight split -> Cover 4."""
    print("\n" + "=" * 60)
    print("TEST 1b: Cover 4 (Two deep safeties, tight split)")
    print("=" * 60)

    # Two safeties, 15 yards deep, only 10 yards apart
    opponents = [
        MockPlayer("FS1", Vec2(-5, 35), Position.FS),
        MockPlayer("SS1", Vec2(5, 35), Position.SS),
    ]
    world = create_world(los_y=50, opponents=opponents)

    result = _identify_coverage_shell(world)
    print(f"  Safeties: FS at (-5, 35), SS at (5, 35)")
    print(f"  Split: 10 yards")
    print(f"  Result: {result}")

    if result == CoverageShell.COVER_4:
        print("  RESULT: PASS - Correctly identified Cover 4")
        return True
    else:
        print(f"  RESULT: FAIL - Expected COVER_4, got {result}")
        return False


def test_cover_1_centered():
    """Single high safety, centered -> Cover 1."""
    print("\n" + "=" * 60)
    print("TEST 1c: Cover 1 (Single high safety, centered)")
    print("=" * 60)

    # Single safety, 15 yards deep, centered
    opponents = [
        MockPlayer("FS1", Vec2(0, 35), Position.FS),
    ]
    world = create_world(los_y=50, opponents=opponents)

    result = _identify_coverage_shell(world)
    print(f"  Safety: FS at (0, 35)")
    print(f"  Result: {result}")

    if result == CoverageShell.COVER_1:
        print("  RESULT: PASS - Correctly identified Cover 1")
        return True
    else:
        print(f"  RESULT: FAIL - Expected COVER_1, got {result}")
        return False


def test_cover_3_shaded():
    """Single high safety, shaded to one side -> Cover 3."""
    print("\n" + "=" * 60)
    print("TEST 1d: Cover 3 (Single high safety, shaded)")
    print("=" * 60)

    # Single safety, 15 yards deep, shaded to the right
    opponents = [
        MockPlayer("FS1", Vec2(10, 35), Position.FS),
    ]
    world = create_world(los_y=50, opponents=opponents)

    result = _identify_coverage_shell(world)
    print(f"  Safety: FS at (10, 35) - shaded right")
    print(f"  Result: {result}")

    if result == CoverageShell.COVER_3:
        print("  RESULT: PASS - Correctly identified Cover 3")
        return True
    else:
        print(f"  RESULT: FAIL - Expected COVER_3, got {result}")
        return False


def test_cover_0_no_deep():
    """No deep safeties -> Cover 0."""
    print("\n" + "=" * 60)
    print("TEST 1e: Cover 0 (No deep safeties)")
    print("=" * 60)

    # No deep safeties (all at or near LOS)
    opponents = [
        MockPlayer("FS1", Vec2(5, 47), Position.FS),  # Only 3 yards deep - not "deep"
        MockPlayer("SS1", Vec2(-5, 48), Position.SS),
    ]
    world = create_world(los_y=50, opponents=opponents)

    result = _identify_coverage_shell(world)
    print(f"  Safeties: FS at (5, 47), SS at (-5, 48) - both shallow")
    print(f"  Result: {result}")

    if result == CoverageShell.COVER_0:
        print("  RESULT: PASS - Correctly identified Cover 0")
        return True
    else:
        print(f"  RESULT: FAIL - Expected COVER_0, got {result}")
        return False


# =============================================================================
# Test 2: Blitz Detection
# =============================================================================

def test_blitz_none():
    """No walked-up defenders -> BlitzLook.NONE."""
    print("\n" + "=" * 60)
    print("TEST 2a: No Blitz (LBs at normal depth)")
    print("=" * 60)

    # LBs at 7 yards depth
    opponents = [
        MockPlayer("MLB1", Vec2(0, 43), Position.MLB),   # 7 yards deep
        MockPlayer("OLB1", Vec2(-10, 43), Position.OLB),
        MockPlayer("FS1", Vec2(0, 35), Position.FS),     # 15 yards deep
    ]
    world = create_world(los_y=50, opponents=opponents)

    blitz_look, blitzers = _detect_blitz_look(world)
    print(f"  MLB at (0, 43) - 7 yards deep")
    print(f"  OLB at (-10, 43) - 7 yards deep")
    print(f"  Result: {blitz_look}, blitzers: {blitzers}")

    if blitz_look == BlitzLook.NONE:
        print("  RESULT: PASS - Correctly detected no blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected NONE, got {blitz_look}")
        return False


def test_blitz_light():
    """One walked-up LB -> BlitzLook.LIGHT."""
    print("\n" + "=" * 60)
    print("TEST 2b: Light Blitz (1 LB walked up)")
    print("=" * 60)

    # One LB at 2 yards depth
    opponents = [
        MockPlayer("MLB1", Vec2(0, 48), Position.MLB),   # 2 yards deep - walked up
        MockPlayer("OLB1", Vec2(-10, 43), Position.OLB), # Normal depth
        MockPlayer("FS1", Vec2(0, 35), Position.FS),
    ]
    world = create_world(los_y=50, opponents=opponents)

    blitz_look, blitzers = _detect_blitz_look(world)
    print(f"  MLB at (0, 48) - 2 yards deep (walked up)")
    print(f"  Result: {blitz_look}, blitzers: {blitzers}")

    if blitz_look == BlitzLook.LIGHT and len(blitzers) == 1:
        print("  RESULT: PASS - Correctly detected light blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected LIGHT with 1 blitzer, got {blitz_look} with {len(blitzers)}")
        return False


def test_blitz_heavy():
    """Two walked-up defenders with deep safety -> BlitzLook.HEAVY."""
    print("\n" + "=" * 60)
    print("TEST 2c: Heavy Blitz (2+ walked up, deep safety present)")
    print("=" * 60)

    opponents = [
        MockPlayer("MLB1", Vec2(0, 48), Position.MLB),    # Walked up
        MockPlayer("OLB1", Vec2(-5, 48), Position.OLB),   # Walked up
        MockPlayer("FS1", Vec2(0, 35), Position.FS),      # Deep safety present
    ]
    world = create_world(los_y=50, opponents=opponents)

    blitz_look, blitzers = _detect_blitz_look(world)
    print(f"  MLB at (0, 48) - walked up")
    print(f"  OLB at (-5, 48) - walked up")
    print(f"  FS at (0, 35) - deep safety")
    print(f"  Result: {blitz_look}, blitzers: {blitzers}")

    if blitz_look == BlitzLook.HEAVY and len(blitzers) >= 2:
        print("  RESULT: PASS - Correctly detected heavy blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected HEAVY with 2+ blitzers, got {blitz_look} with {len(blitzers)}")
        return False


def test_blitz_zero():
    """Two walked-up defenders with NO deep safety -> BlitzLook.ZERO."""
    print("\n" + "=" * 60)
    print("TEST 2d: Zero Blitz (2+ walked up, NO deep safety)")
    print("=" * 60)

    opponents = [
        MockPlayer("MLB1", Vec2(0, 48), Position.MLB),    # Walked up
        MockPlayer("OLB1", Vec2(-5, 48), Position.OLB),   # Walked up
        MockPlayer("SS1", Vec2(5, 45), Position.SS),      # Safety crept up too (5 yards deep)
    ]
    world = create_world(los_y=50, opponents=opponents)

    blitz_look, blitzers = _detect_blitz_look(world)
    print(f"  MLB at (0, 48) - walked up")
    print(f"  OLB at (-5, 48) - walked up")
    print(f"  SS at (5, 45) - crept up (no deep safety)")
    print(f"  Result: {blitz_look}, blitzers: {blitzers}")

    if blitz_look == BlitzLook.ZERO:
        print("  RESULT: PASS - Correctly detected Cover 0 blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected ZERO, got {blitz_look}")
        return False


def test_safety_creep():
    """Safety within 8 yards should be flagged as potential blitzer."""
    print("\n" + "=" * 60)
    print("TEST 2e: Safety Creep Detection")
    print("=" * 60)

    opponents = [
        MockPlayer("MLB1", Vec2(0, 43), Position.MLB),    # Normal depth
        MockPlayer("SS1", Vec2(5, 45), Position.SS),      # Safety crept up (5 yards deep)
        MockPlayer("FS1", Vec2(0, 35), Position.FS),      # Deep safety still present
    ]
    world = create_world(los_y=50, opponents=opponents)

    blitz_look, blitzers = _detect_blitz_look(world)
    print(f"  SS at (5, 45) - 5 yards deep (crept up)")
    print(f"  Result: {blitz_look}, blitzers: {blitzers}")

    if "SS1" in blitzers:
        print("  RESULT: PASS - Correctly detected safety creep")
        return True
    else:
        print(f"  RESULT: FAIL - Expected SS1 in blitzers, got {blitzers}")
        return False


# =============================================================================
# Test 3: Hot Route Logic
# =============================================================================

def test_hot_route_heavy():
    """Heavy blitz -> First WR gets slant hot route."""
    print("\n" + "=" * 60)
    print("TEST 3a: Hot Route on Heavy Blitz")
    print("=" * 60)

    teammates = [
        MockPlayer("WR1", Vec2(-15, 50), Position.WR),
        MockPlayer("WR2", Vec2(15, 50), Position.WR),
        MockPlayer("RB1", Vec2(0, 55), Position.RB),
    ]
    world = create_world(los_y=50, opponents=[], teammates=teammates)

    hot_routes = _get_hot_route_for_blitz(world, BlitzLook.HEAVY, CoverageShell.COVER_0)
    print(f"  Blitz: HEAVY")
    print(f"  Hot routes: {hot_routes}")

    if hot_routes and any(r == "slant" for r in hot_routes.values()):
        print("  RESULT: PASS - WR correctly assigned slant hot route")
        return True
    else:
        print(f"  RESULT: FAIL - Expected slant hot route, got {hot_routes}")
        return False


def test_hot_route_zero():
    """Zero blitz -> First WR gets slant hot route."""
    print("\n" + "=" * 60)
    print("TEST 3b: Hot Route on Zero Blitz")
    print("=" * 60)

    teammates = [
        MockPlayer("WR1", Vec2(-15, 50), Position.WR),
        MockPlayer("RB1", Vec2(0, 55), Position.RB),
    ]
    world = create_world(los_y=50, opponents=[], teammates=teammates)

    hot_routes = _get_hot_route_for_blitz(world, BlitzLook.ZERO, CoverageShell.COVER_0)
    print(f"  Blitz: ZERO")
    print(f"  Hot routes: {hot_routes}")

    if hot_routes and "slant" in hot_routes.values():
        print("  RESULT: PASS - WR correctly assigned slant on zero blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected slant hot route, got {hot_routes}")
        return False


def test_hot_route_light():
    """Light blitz -> RB gets checkdown hot route."""
    print("\n" + "=" * 60)
    print("TEST 3c: Hot Route on Light Blitz")
    print("=" * 60)

    teammates = [
        MockPlayer("WR1", Vec2(-15, 50), Position.WR),
        MockPlayer("RB1", Vec2(0, 55), Position.RB),
    ]
    world = create_world(los_y=50, opponents=[], teammates=teammates)

    hot_routes = _get_hot_route_for_blitz(world, BlitzLook.LIGHT, CoverageShell.COVER_1)
    print(f"  Blitz: LIGHT")
    print(f"  Hot routes: {hot_routes}")

    if hot_routes and "checkdown" in hot_routes.values():
        print("  RESULT: PASS - RB correctly assigned checkdown on light blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected checkdown hot route for RB, got {hot_routes}")
        return False


def test_hot_route_none():
    """No blitz -> No hot routes."""
    print("\n" + "=" * 60)
    print("TEST 3d: No Hot Routes on No Blitz")
    print("=" * 60)

    teammates = [
        MockPlayer("WR1", Vec2(-15, 50), Position.WR),
        MockPlayer("RB1", Vec2(0, 55), Position.RB),
    ]
    world = create_world(los_y=50, opponents=[], teammates=teammates)

    hot_routes = _get_hot_route_for_blitz(world, BlitzLook.NONE, CoverageShell.COVER_2)
    print(f"  Blitz: NONE")
    print(f"  Hot routes: {hot_routes}")

    if hot_routes is None:
        print("  RESULT: PASS - No hot routes when no blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected None, got {hot_routes}")
        return False


# =============================================================================
# Test 4: Protection Calls
# =============================================================================

def test_protection_slide_right():
    """Blitzers on right side -> slide_right."""
    print("\n" + "=" * 60)
    print("TEST 4a: Protection Call - Slide Right")
    print("=" * 60)

    opponents = [
        MockPlayer("OLB1", Vec2(8, 48), Position.OLB),   # Walked up on right
    ]
    world = create_world(los_y=50, opponents=opponents)

    protection = _get_protection_call(world, BlitzLook.LIGHT, ["OLB1"])
    print(f"  Blitzer: OLB1 at (8, 48) - right side")
    print(f"  Protection call: {protection}")

    if protection == "slide_right":
        print("  RESULT: PASS - Correctly called slide_right")
        return True
    else:
        print(f"  RESULT: FAIL - Expected slide_right, got {protection}")
        return False


def test_protection_slide_left():
    """Blitzers on left side -> slide_left."""
    print("\n" + "=" * 60)
    print("TEST 4b: Protection Call - Slide Left")
    print("=" * 60)

    opponents = [
        MockPlayer("OLB1", Vec2(-8, 48), Position.OLB),   # Walked up on left
        MockPlayer("MLB1", Vec2(-3, 48), Position.MLB),   # Also left side
    ]
    world = create_world(los_y=50, opponents=opponents)

    protection = _get_protection_call(world, BlitzLook.HEAVY, ["OLB1", "MLB1"])
    print(f"  Blitzers: OLB1 at (-8), MLB1 at (-3) - left side")
    print(f"  Average blitz X: {(-8 + -3) / 2}")
    print(f"  Protection call: {protection}")

    if protection == "slide_left":
        print("  RESULT: PASS - Correctly called slide_left")
        return True
    else:
        print(f"  RESULT: FAIL - Expected slide_left, got {protection}")
        return False


def test_protection_none():
    """No blitz -> No protection call."""
    print("\n" + "=" * 60)
    print("TEST 4c: No Protection Call on No Blitz")
    print("=" * 60)

    world = create_world(los_y=50, opponents=[])

    protection = _get_protection_call(world, BlitzLook.NONE, [])
    print(f"  Blitz: NONE")
    print(f"  Protection call: {protection}")

    if protection is None:
        print("  RESULT: PASS - No protection call when no blitz")
        return True
    else:
        print(f"  RESULT: FAIL - Expected None, got {protection}")
        return False


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PRE-SNAP QB INTELLIGENCE - VERIFICATION TESTS")
    print("=" * 70)

    results = []

    # Coverage Shell Identification (5 tests)
    results.append(("Cover 2 (wide split)", test_cover_2_wide_split()))
    results.append(("Cover 4 (tight split)", test_cover_4_tight_split()))
    results.append(("Cover 1 (centered)", test_cover_1_centered()))
    results.append(("Cover 3 (shaded)", test_cover_3_shaded()))
    results.append(("Cover 0 (no deep)", test_cover_0_no_deep()))

    # Blitz Detection (5 tests)
    results.append(("Blitz None", test_blitz_none()))
    results.append(("Blitz Light", test_blitz_light()))
    results.append(("Blitz Heavy", test_blitz_heavy()))
    results.append(("Blitz Zero", test_blitz_zero()))
    results.append(("Safety Creep", test_safety_creep()))

    # Hot Route Logic (4 tests)
    results.append(("Hot Route Heavy", test_hot_route_heavy()))
    results.append(("Hot Route Zero", test_hot_route_zero()))
    results.append(("Hot Route Light", test_hot_route_light()))
    results.append(("Hot Route None", test_hot_route_none()))

    # Protection Calls (3 tests)
    results.append(("Protection Slide Right", test_protection_slide_right()))
    results.append(("Protection Slide Left", test_protection_slide_left()))
    results.append(("Protection None", test_protection_none()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n  Total: {passed_count}/{len(results)} tests passed")
