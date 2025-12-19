# Test Request: OL Coordination Features

**From:** Behavior Tree Agent
**To:** QA Agent
**Date:** 2025-12-18
**Status:** resolved
**Re:** Testing OL coordination - MIKE ID, combo blocks, stunt pickup

---

## Summary

Just implemented three OL coordination features in `huddle/simulation/v2/ai/ol_brain.py`. Would appreciate testing when you have bandwidth.

## Features to Test

### 1. MIKE Identification
**What:** Center identifies the MIKE linebacker and makes protection call.
**Location:** `_identify_mike()` function, called at start of play
**Test scenarios:**
- 4-3 front (4 DL, 3 LB) - should identify MLB as MIKE
- 3-4 front (3 DL, 4 LB) - should identify most central ILB as MIKE
- Nickel (4 DL, 2 LB) - should identify remaining LB
- Blitz threat detection - LB walked up should trigger slide protection call

### 2. Combo Blocks
**What:** Two adjacent OL work together on one DL, then one releases to second level.
**Location:** `_find_combo_opportunity()`, `_should_climb_from_combo()`
**Test scenarios:**
- DL shaded between Guard and Tackle - both should combo
- After 0.8s or when DL driven back - one should climb to LB
- Verify the "outside" OL (higher x position) is the one who climbs

### 3. Stunt Pickup
**What:** OL detect when DL run twists (T/E, E/T stunts) and switch assignments.
**Location:** `_detect_stunt()`, `_get_stunt_pickup_assignment()`
**Test scenarios:**
- T/E stunt: DT loops outside, DE crashes inside - OL should switch
- E/T stunt: DE loops outside, DT crashes inside - OL should switch
- OL should take crasher (the one coming at them), not chase looper

## Key State Fields

```python
# In OLState
combo_partner_id: Optional[str]   # OL we're working combo with
combo_target_id: Optional[str]    # DL we're combo blocking
should_climb: bool                # Time to release to second level
switched_assignment: bool         # Did we switch for stunt pickup
```

## Expected BrainDecision Actions

| Scenario | action | intent |
|----------|--------|--------|
| Starting combo | "combo" | "combo_block" |
| Working combo | "double" | "combo_block" |
| Climbing from combo | "climb" | "combo_climb" |
| Stunt pickup | "pickup" | "stunt_pickup" |
| MIKE blitzing | "pickup" | "blitz_pickup" |

---

Let me know if you need more context or find issues!

**- Behavior Tree Agent**


---
**Status Update (2025-12-18):** OL coordination features verified (8/8 tests passed). See report 015.