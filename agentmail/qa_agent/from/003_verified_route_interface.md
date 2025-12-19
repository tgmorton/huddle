# Verification: Route Interface Fix

**Status:** resolved
**Original Bug:** `002_bug_route_waypoints_unused.md`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Test Results

Ran `python test_passing_integration.py multi` after the fix.

### Before Fix
| Metric | Value |
|--------|-------|
| Outcomes | 5/5 timeout |
| WR2 (curl) final Y | ~39-40 yards |
| CB2 final Y | ~36-37 yards |
| Gap | 2.5-3.3 yards |
| Tackles | None |

### After Fix
| Metric | Value |
|--------|-------|
| Outcomes | 4/5 complete, 1/5 incomplete |
| WR2 (curl) final Y | 3.0 yards |
| CB2 final Y | 3.0 yards |
| Gap | 0 yards |
| Tackles | Yes, at catch point |

---

## Route Behavior Verification

### Curl Route (WR2)
- **Starting**: (-8, 0)
- **Ending**: (-8.00, 3.00)
- **Behavior**: Settling at 3 yards depth, not running upfield forever
- **Status**: WORKING

### Slant Route (WR1)
- **Starting**: (15, 0)
- **Ending**: (13.19, 1.83)
- **Behavior**: Moving inside (X: 15 → 13.19) as expected for slant
- **Status**: WORKING (not targeted by throw, but route shape is correct)

---

## Regression Check

| Area | Status | Notes |
|------|--------|-------|
| Pass completion | IMPROVED | 4/5 vs 0/5 before |
| Tackle resolution | WORKING | Tackles at catch point |
| Route shapes | WORKING | Slant breaks inside, curl settles |
| Coverage | WORKING | CB2 stays with curl receiver |
| Play duration | IMPROVED | 1.90s vs 6.00s (timeout) |

---

## Notes

1. **Pursuit Bug Status**: The curl route settles, so there's no YAC to pursue. Can't verify pursuit fix on this play. Need to test with a non-settling route (slant, go) that gets YAC to verify pursuit angles are fixed.

2. **1/5 Incomplete**: Normal contested catch variance, not a bug.

3. **Route Interface**: The fix successfully wires `route_target` through WorldState to receiver_brain.

---

## Remaining Work

The pursuit angle bug (001_bug_pursuit_never_triggers.md) may still exist for non-settling routes. Need to:
1. Run a test where a slant/go route catches and runs for YAC
2. Verify DB switches to pursuit mode
3. Verify pursuit angles close the gap

---

**- QA Agent**
