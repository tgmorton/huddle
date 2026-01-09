# Task: Throw Lead Improvements for Breaking Routes

**From:** live_sim_agent (claude_code)
**To:** behavior_tree_agent
**Date:** 2025-12-19
**Type:** task
**Priority:** medium

---

## Problem

Slant/out/in/post routes have ~0% completion rate because throw lead calculation doesn't account for direction changes at the break point.

**Current behavior:**
- QB throws pre-break while receiver runs stem (straight ahead)
- Ball is led based on stem velocity
- Receiver breaks and cuts at 45°+
- Ball and receiver don't meet (2-4 yard miss)

## Suggested Fix

In `qb_brain.py` `_calculate_throw_lead()`:

For pre-break receivers, throw to the **break point** instead of leading with current velocity:

```python
# Get break point from route assignment if available
if receiver.pre_break:
    # TODO: Need to pass break_point into ReceiverEval
    # RouteAssignment.get_break_point() returns the field position
    if receiver.break_point:
        return receiver.break_point
    # Fallback to current position if no break point known
    return receiver.position
```

This requires:
1. Adding `break_point: Optional[Vec2]` to `ReceiverEval` dataclass
2. Populating it from `RouteAssignment.get_break_point()` in `_evaluate_receivers()`
3. Using it in `_calculate_throw_lead()` for pre-break throws

## Other Brain Improvements to Consider

1. **Route-aware throw timing** - Wait until receiver is closer to break
2. **Pressure response tuning** - Earlier throws, checkdowns under pressure
3. **Coverage shell utilization** - Use pre-snap reads to adjust progression
4. **Contested catch decisions** - When to throw tight windows vs move on

## Files
- `huddle/simulation/v2/ai/qb_brain.py` - throw lead calc, ReceiverEval
- `huddle/simulation/v2/systems/route_runner.py` - has `get_break_point()`
