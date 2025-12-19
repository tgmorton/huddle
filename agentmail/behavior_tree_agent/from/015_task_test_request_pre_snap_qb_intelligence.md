# Test Request: Pre-Snap QB Intelligence

**From:** behavior_tree_agent
**To:** qa_agent
**Date:** 2025-12-18 16:15:05
**Type:** task
**Priority:** medium

---

## Summary

Just implemented pre-snap QB intelligence. Adding to your test queue.

---

## Features to Test

### 1. Coverage Shell Identification
**Location:** `qb_brain.py` → `_identify_coverage_shell()`

**Test scenarios:**
- 2 deep safeties, wide split (> 20 yards) → Cover 2
- 2 deep safeties, tight split → Cover 4
- 1 deep safety, centered → Cover 1
- 1 deep safety, shaded to one side → Cover 3
- 0 deep safeties → Cover 0

### 2. Blitz Detection
**Location:** `qb_brain.py` → `_detect_blitz_look()`

**Test scenarios:**
- No walked-up defenders → BlitzLook.NONE
- 1 LB within 3 yards of LOS → BlitzLook.LIGHT
- 2+ defenders walked up, deep safety present → BlitzLook.HEAVY
- 2+ defenders walked up, NO deep safety → BlitzLook.ZERO
- Safety creep (safety < 8 yards deep) should trigger as potential blitzer

### 3. Hot Route Logic
**Location:** `qb_brain.py` → `_get_hot_route_for_blitz()`

**Test scenarios:**
- HEAVY/ZERO blitz → First WR should get "slant" hot route
- LIGHT blitz → RB should get "checkdown" hot route
- NONE blitz → No hot routes

### 4. Protection Calls
**Location:** `qb_brain.py` → `_get_protection_call()`

**Test scenarios:**
- Blitzers average position x > 0 → "slide_right"
- Blitzers average position x < 0 → "slide_left"
- No blitz → None

---

## Expected BrainDecision

When `world.phase == PlayPhase.PRE_SNAP`:

```python
BrainDecision(
    intent="pre_snap_read",
    hot_routes={"player_id": "slant"},  # Or None
    protection_call="slide_left",         # Or None
    reasoning="Coverage: cover_2, Blitz look: heavy, ..."
)
```

---

**- Behavior Tree Agent**