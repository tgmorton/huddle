# Verification Report: Bug Fixes 009, 010, 011

**Status:** resolved VERIFIED
**Date:** 2025-12-18
**From:** Qa Agent
**To:** Live Sim Agent

---

## Bug 009 - Vision Filter Blocks Close Threats

### Fix Applied
```python
# OLD
if angle > vision_params.angle / 2:
    continue

# NEW
if angle > vision_params.angle / 2 and distance > 2.0:
    continue
```

### Test Results
```
WR pos: (15.0, 10.0)
CB pos: (14.0, 9.0)
Distance: 1.41 yards

All threats: 1
Filtered threats: 1  <-- WAS 0 BEFORE FIX

PASS - Threat at 135° angle (behind) now perceived at 1.41 yards
CONTACT situation correctly detected!
```

### Status: **VERIFIED**
Threats within 2 yards are now perceived regardless of angle.

---

## Bug 010 - DL Contain Direction Backwards

### Fixes Applied
1. Higher threshold for contain mode (significant scramble required)
2. Correct contain position calculation

### Test Results
```
Block shed at 0.75s

DE decisions AFTER shed:
  [0.80s] pos=(-1.7,-3.0) dist_to_qb=4.2
  [1.25s] pos=(0.6,-5.0) dist_to_qb=3.2

PASS - DE closing on QB! (dist: 4.2 -> 3.2)
X movement: -1.7 -> 0.6 (moving RIGHT toward QB at x=0)
```

### Status: **VERIFIED**
DE now moves toward QB after shedding block. Direction is correct.

**Note:** Sacks don't occur because QB is protected during DEVELOPMENT phase (line 1185 in orchestrator). This is intentional - sack system needs pocket collapse feature.

---

## Bug 011 - DB Backpedal Direction Wrong

### Fix Applied
```python
# OLD
cushion_target = receiver.pos - Vec2(0, state.cushion)

# NEW
cushion_target = receiver.pos + Vec2(0, state.cushion)
```

### Test Results
```
Position Tracking (first 1 second):
  [0.05s] WR=(0.0y) CB=(0.5y) Gap=0.5
  [0.45s] WR=(1.3y) CB=(1.3y) Gap=0.3
  [0.85s] WR=(3.8y) CB=(2.9y) Gap=0.9

PASS - CB moving FORWARD (Y increased by 0.9)
Final gap: 0.7 yards  <-- WAS 7+ YARDS BEFORE FIX
```

### Status: **VERIFIED**
DB now maintains tight coverage (0.7 yard gap vs 7+ yards before).

---

## Summary

| Bug | Fix | Result |
|-----|-----|--------|
| 009 Vision Filter | Add distance > 2.0 check | **VERIFIED** |
| 010 DL Contain | Fix direction + threshold | **VERIFIED** |
| 011 DB Backpedal | Change - to + | **VERIFIED** |

---

## Remaining Items

1. **Evasion moves** - Brain detects threats but tackle happens at same tick as catch. May need tackle immunity at catch point to give ballcarrier a chance to evade.

2. **Sacks** - Not implemented. QB protected during DEVELOPMENT phase. Needs pocket collapse system.

3. **Contested catches** - Should now work with DB backpedal fix. Needs retest.

---

**- QA Agent**
