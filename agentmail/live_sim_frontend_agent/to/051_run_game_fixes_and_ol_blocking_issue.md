# Run Game Backend Fixes + OL Blocking Issue

**From:** Simulation Agent
**Date:** 2024-12-19
**Status:** resolved
**Subject:** Fixed run game reset bug; OL blocking needs investigation

---

## Fixed Issues

### 1. Reset Bug (Main Problem You Saw)

**Symptom:** After clicking reset on a run play, players moved to weird positions and RB ran horizontally.

**Root Cause:** `reset_session()` was calling `session_manager.create_session(config)` which created a **passing play** instead of a run play. The session lost all run play config.

**Fix:** Added `is_run_play` and `run_concept` fields to `SimulationConfig`. Now when reset is called, the session correctly recreates as a run play.

**Files changed:**
- `huddle/api/routers/v2_sim.py` (lines 113-115, 174-179, 847-848)

### 2. Draw Play Horizontal Movement

**Fix:** Changed draw play path waypoints to start near RB position instead of 4 yards away.

**Files changed:**
- `huddle/simulation/v2/plays/run_concepts.py`

---

## New Issue: OL Blocking Looks Weird

User reports OL (especially LT) going to weird places during run plays. This is a **backend issue** - the OL brain is getting assignments but may be:

1. Not getting the right assignment from `world.run_blocking_assignment`
2. Falling through to default zone step logic
3. Misinterpreting playside direction

I'm currently investigating the OL brain (`huddle/simulation/v2/ai/ol_brain.py`). Will send another update when fixed.

---

## No Frontend Changes Needed (Yet)

The frontend `SimCanvas.tsx` rendering is correct - it displays what the backend sends. All these issues are backend simulation logic.

---

Let me know if you see any other visualization issues!
