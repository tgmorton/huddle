# Bug Report: Pursuit Intercept Formula Too Conservative

**Severity:** MAJOR
**Status:** resolved
**Component:** db_brain pursuit intercept calculation
**Found In:** `huddle/simulation/v2/ai/db_brain.py:376-381`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

After the waypoint fix, routes now run properly and receivers get significant YAC. The pursuit formula's 0.7 lead factor is too conservative for same-speed pursuit, resulting in a consistent 3.0 yard gap that never closes.

## Expected Behavior

With same-speed players (WR2: 88, CB2: 88), pursuit angles should close the gap and result in a tackle.

## Actual Behavior

```
WR2: (-8.44, 39.67) [HAS BALL]
CB2: (-8.44, 36.65)   <-- 3.0 yards behind
```

All 5 plays ended in timeout. Gap is constant at ~3.0 yards.

## Reproduction Steps

1. Run: `python test_passing_integration.py multi`
2. Observe: All plays timeout, CB2 consistently 3.0 yards behind WR2

## Analysis

### The Formula

```python
time_to_reach = dist / 8.0  # Assume ~8 yd/s closing speed
intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 0.7
```

### The Problem

The **0.7 factor** means CB only targets 70% of where WR will be.

Example with dist=3, WR velocity=8 yd/s:
- time_to_reach = 3/8 = 0.375s
- intercept = WR.pos + 8 * 0.375 * 0.7 = WR.pos + 2.1 yards ahead

In 0.375s:
- WR moves: 8 * 0.375 = 3.0 yards
- CB targets: 2.1 yards ahead of original position
- Gap: 3.0 - 2.1 = 0.9 yards (gap GROWS slightly on each iteration)

### Why 0.7 Isn't Enough

For same-speed pursuit to close, lead factor should be >= 1.0:
- At 1.0: CB targets exactly where WR will be
- At 0.7: CB is always short by 30% of WR's travel distance

### Velocity Check

From test results:
- WR travels ~35 yards in 4.3s = 8.1 yd/s
- CB travels ~27 yards in 4.3s = 6.3 yd/s

CB is effectively running slower because pursuit angle keeps targeting behind the actual intercept point.

## Suggested Fix

Increase lead factor from 0.7 to 1.0 or 1.1:

```python
# Target where ballcarrier will be (lead pass style)
intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 1.0

# Or slightly over-lead to ensure closing
intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 1.1
```

Alternatively, adjust `time_to_reach` calculation to be more aggressive for close distances.

## Test Verification

My pursuit tests now show:
- Slant: 1.2 yard gap (was 0.0 before waypoint fix)
- Go: 3.0 yard gap, timeout
- Same speed: 0.8 yard gap

The fixes are working partially but the lead factor needs tuning.

---

**- QA Agent**
