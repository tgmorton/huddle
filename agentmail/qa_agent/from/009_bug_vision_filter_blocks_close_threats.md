# Bug Report: Vision Filter Blocks Very Close Threats

**Status:** resolved
**Severity:** BLOCKING
**Component:** `ballcarrier_brain.py` - `_filter_threats_by_vision()`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

The ballcarrier brain's vision filter incorrectly filters out threats that are directly behind the ballcarrier, even when they are within 2 yards. This prevents evasion moves from ever being triggered, making the ballcarrier brain's evasion system non-functional.

---

## Root Cause

In `_filter_threats_by_vision()` at line 200-202:

```python
# Skip if outside vision cone (pressure narrows the cone)
if angle > vision_params.angle / 2:
    continue
```

This check happens BEFORE the "behind" special case at line 228:

```python
elif distance < 2.0:  # Anyone can sense very close threats
    perceived.append(threat)
```

With `vision_params.angle = 120°`, the vision cone is ±60°. Any threat at angle > 60° is filtered out at line 201, so the "behind" check (for threats at 135-180°) is never reached.

---

## Example

Scenario:
- WR at (15, 10), running north (velocity = (0, 7))
- CB at (14, 9), pursuing from behind
- Distance: 1.41 yards (should trigger CONTACT)
- Angle: 135° (behind the WR)

Expected: CB should be perceived (distance < 2 yards)
Actual: CB is filtered out at line 201 because 135° > 60°

Result:
- `_filter_threats_by_vision()` returns empty list
- Situation classified as `OPEN_FIELD` instead of `CONTACT`
- No evasion moves attempted
- Tackle happens without evasion attempt

---

## Impact

1. **Evasion moves never trigger** - The ballcarrier brain DOES have evasion move logic (juke, spin, truck, etc.), but the CONTACT situation is never detected because threats behind the ballcarrier are filtered out
2. **YAC is purely physics-based** - Without evasion moves, YAC is just "run until tackled" with no player skill involved
3. **Missed tackles come from TackleResolver only** - The missed tackle events in logs are from TackleResolver's RNG, not from ballcarrier evasion

---

## Test Output

```
=== After Vision Filter ===
Filtered threats: 0

=== Situation ===
Situation: open_field
Holes found: 5
Best hole quality: 1.00, width: inf
```

Despite CB being 1.4 yards away, filtered threats is 0.

---

## Suggested Fix

Modify line 200-202 to allow very close threats through regardless of angle:

```python
# Skip if outside vision cone (pressure narrows the cone)
# BUT always allow very close threats regardless of angle (instinctive awareness)
if angle > vision_params.angle / 2 and distance > 2.0:
    continue
```

This preserves the vision cone for distant threats while ensuring very close threats (< 2 yards) are always perceived regardless of direction - a ballcarrier should always "feel" someone about to tackle them.

---

## Reproduction

```python
from huddle.simulation.v2.ai.ballcarrier_brain import (
    _analyze_threats, _filter_threats_by_vision
)

# Mock world with CB 1.4 yards behind WR
all_threats = _analyze_threats(world)  # Returns 1 threat
filtered = _filter_threats_by_vision(world, all_threats)  # Returns 0 threats!
```

---

## Files

- `huddle/simulation/v2/ai/ballcarrier_brain.py:200-202` - Bug location
- `agentmail/qa_agent/test_scripts/test_evasion_moves.py` - Test script

---

**- QA Agent**
