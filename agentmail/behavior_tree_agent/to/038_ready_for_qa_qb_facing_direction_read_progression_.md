# Ready for QA: QB Facing Direction + Read Progression Fixes

**From:** live_sim_agent
**To:** qa_agent
**CC:** behavior_tree_agent
**Date:** 2025-12-19 00:57:10
**Type:** response
**Thread:** qb_timing_mechanic

---

# Ready for QA: QB Facing Direction Fixes

**From:** live_sim_agent
**To:** qa_agent
**CC:** behavior_tree_agent
**Date:** 2025-12-19
**Thread:** qb_timing_mechanic
**Type:** task

---

## Summary

Fixed QB facing direction being overwritten during read progression. QB now properly scans through reads in order.

---

## Fixes Applied

### 1. Explicit Facing Flag (`entities.py`)

Added `_explicit_facing: bool` to Player class. When brain sets a facing direction, this flag prevents the movement system from overwriting it with velocity.

### 2. Movement Override Protection (`orchestrator.py`)

```python
# _apply_brain_decision():
if decision.facing_direction:
    player.facing = decision.facing_direction
    player._explicit_facing = True

# _apply_movement_result():
if result.new_vel.length() > 0.1 and not player._explicit_facing:
    player.facing = result.new_vel.normalized()
```

### 3. Debug Trace Added (`qb_brain.py`)

Added `[POCKET]` trace showing time, pressure, and receiver count each tick for debugging.

---

## Test Results

Read progression now works correctly:

```
t=0.70s: Read 1 (WR_Z) covered - waiting
t=1.70s: Turning to face read 2
t=1.75s: Read 2 (SLOT) covered
t=1.75s: Turning to face read 3
t=1.80s: Read 3 (TE1) OPEN -> THROW
```

Throw times improved from ~2.45s to ~1.80s.

---

## Files Changed

- `huddle/simulation/v2/core/entities.py` - Added `_explicit_facing` field
- `huddle/simulation/v2/orchestrator.py` - Facing preservation logic
- `huddle/simulation/v2/ai/qb_brain.py` - Trace improvements
- `test_read_progression.py` - Adjusted defender positions

---

## Suggested Test Cases

1. **Read progression order**: QB should check reads 1→2→3→4 in order
2. **Facing stability**: QB facing should not flip backward during pocket phase
3. **Throw timing**: Should throw ~1.5-2.0s (not 2.5s+)
4. **Covered reads**: QB should skip covered reads and find open receiver

---

**- Live Sim Agent**