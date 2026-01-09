# Run Game Backend Fixes Complete

**From:** Simulation Agent
**Date:** 2024-12-19
**Subject:** Fixed run game reset bug and horizontal movement issue

---

## Summary

Fixed two issues causing weird RB behavior in run plays, especially after clicking the reset button.

## Issue 1: Reset Bug (Main Problem)

**Symptom:** After clicking reset on a run play, players would move to weird positions and the RB would run horizontally.

**Root Cause:** When resetting a run play session, the backend was calling `session_manager.create_session(config)` which created a **passing play** instead of a run play. The session lost:
- `is_run_play=True` flag
- `run_concept` name
- `ballcarrier_brain` registration
- Proper run play `PlayConfig`

**Fix:**
1. Added `is_run_play` and `run_concept` fields to `SimulationConfig` model
2. These fields are now stored when creating run play sessions
3. `session_manager.create_session()` now checks for `is_run_play` and delegates to `_create_run_session()` when true

**Files changed:**
- `huddle/api/routers/v2_sim.py` (lines 113-115, 174-179, 847-848)

## Issue 2: Draw Play Horizontal Movement

**Symptom:** Draw play RB would run sideways instead of toward the hole.

**Root Cause:** Draw play path waypoints used absolute X coordinates `[(2, -5), ...]` but RB starts at `x=-2`. First waypoint required moving 4 yards RIGHT and only 2 yards forward = horizontal movement.

**Fix:** Changed draw play path to start near RB position:
- Old: `[Vec2(2, -5), Vec2(2, -4), Vec2(1, -2), Vec2(1, 3)]`
- New: `[Vec2(-1, -5), Vec2(0, -4), Vec2(1, -2), Vec2(1, 3)]`

**Files changed:**
- `huddle/simulation/v2/plays/run_concepts.py`

## Verification

All 10 run concepts tested with 0 horizontal ticks:
- inside_zone_right/left ✓
- outside_zone_right/left ✓
- power_right/left ✓
- counter_right ✓
- dive_right ✓
- draw ✓
- toss_right ✓

## No Frontend Changes Needed

The frontend rendering (`SimCanvas.tsx`) was correct - it just displays what the backend sends. Both issues were backend-only fixes.

---

Let me know if you see any other run game visualization issues!
