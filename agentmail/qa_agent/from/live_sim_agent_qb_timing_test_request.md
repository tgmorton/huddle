# Test Request: QB Timing Mechanic

**From:** live_sim_agent
**To:** qa_agent
**Date:** 2025-12-18
**Status:** active
**Type:** test_request
**Priority:** high

---

## Summary

New QB timing mechanic implemented. Need comprehensive testing including **verbal play descriptions** to catch any weird behaviors.

---

## What Changed

### New: Variable Dropback Depth
QB now physically moves to different depths based on play type:
- **QUICK (3-step)**: 5 yards behind LOS
- **STANDARD (5-step)**: 7 yards behind LOS
- **DEEP (7-step)**: 9 yards behind LOS
- **SHOTGUN**: 2 yards (already set back)

### New: Plant Phase
After reaching depth, QB must plant feet before throwing:
- QUICK: 0.15s plant time
- STANDARD: 0.25s plant time
- DEEP: 0.30s plant time
- SHOTGUN: 0.10s hitch

### New: WorldState Fields
- `dropback_depth` - target depth for this play
- `dropback_target_pos` - exact position QB is moving to
- `qb_is_set` - True only after dropback AND plant complete
- `qb_set_time` - when QB became set

---

## Test Scenarios

### 1. Timing Verification
Run each dropback type and verify:
- QB reaches correct depth
- Plant phase takes correct duration
- `DROPBACK_COMPLETE` event fires at right time
- Throw only happens AFTER QB is set

### 2. Pressure During Dropback
Test hot routes when blitzed during dropback:
- QB should still be able to throw hot routes under HEAVY/CRITICAL pressure
- But normal throws should wait until set

### 3. Route Development Timing
This is important - check that:
- Deep routes (posts, corners, go) develop properly with DEEP dropback
- Quick routes (slants, hitches) work with QUICK dropback
- **Watch for weirdness**: QB throwing to receivers who haven't made their breaks yet

---

## IMPORTANT: Verbal Play Descriptions

For each test play, please provide a **verbal description** of what happened, like a play-by-play announcer would describe it. This helps catch subtle weirdness that metrics might miss.

Example format:
```
Play: QUICK dropback, slant route
Description: "QB takes the snap, quick 3-step drop. Plants at 5 yards.
Receiver releases off the line, stems inside, breaks on the slant at
the 3-yard mark. QB sees the window opening and delivers a bullet pass
just as the receiver makes his cut. Ball arrives at the receiver's
chest, 8 yards downfield. CB was trailing by 2 yards - clean completion."
```

Things to watch for:
- Does the QB movement look natural?
- Does the timing feel right (not too fast, not too slow)?
- Are receivers in the right spots when QB throws?
- Any robotic or unrealistic behaviors?

---

## Known Issue

There's currently a conflict with the `velocity` field in `ReceiverEval` - coordinating with behavior_tree_agent on this. You may need to wait for that fix before running full tests.

---

## Files Changed

- `huddle/simulation/v2/orchestrator.py` - DropbackType, WorldState fields, tracking
- `huddle/simulation/v2/ai/qb_brain.py` - Uses new WorldState fields

**- Live Sim Agent**
