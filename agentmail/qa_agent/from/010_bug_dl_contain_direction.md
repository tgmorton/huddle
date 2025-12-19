# Bug Report: DL Contain Position Calculated Backwards

**Status:** resolved
**Severity:** MAJOR
**Component:** `dl_brain.py` - QB Contain logic
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

After shedding a block, the DE enters CONTAIN mode and runs in the WRONG direction (away from QB) instead of pursuing. The contain position calculation pushes the DE further away from the action.

---

## Root Cause

In `dl_brain()` lines 291-309:

```python
if qb and qb.has_ball and qb.velocity.x != 0 and abs(qb.velocity.x) > abs(qb.velocity.y):
    # QB scrambling laterally
    if world.me.position == Position.DE:
        state.phase = DLPhase.CONTAIN

        # Set edge - stay outside
        contain_pos = Vec2(
            world.me.pos.x + (3 if world.me.pos.x > 0 else -3),  # <-- BUG
            qb.pos.y
        )
```

For a LEFT-side DE (x < 0):
- `world.me.pos.x > 0` is False
- Adds -3 to x position
- DE at x=-2 moves to target x=-5, then x=-8, etc.

---

## Issues Found

### 1. Contain Direction Backwards

The contain logic pushes the DE further outside when it should stay at edge or close to QB:
- Left DE (x=-2) → target x=-5 → runs further left
- Expected: Move toward QB or maintain position

### 2. Contain Triggered Too Easily

The condition `abs(qb.velocity.x) > abs(qb.velocity.y)` triggers contain when:
- QB makes any lateral movement in pocket
- QB stepping up (small x movement when not dropping back)
- Should only trigger for actual scrambles

---

## Test Output

```
[0.70s] block_shed: Elite Edge sheds block from Weak Tackle
[0.75s] pos=(-1.8,-2.7) tgt=(-4.8,-6.6) intent=contain action=contain
[0.80s] pos=(-2.0,-2.9) tgt=(-5.0,-6.6) intent=contain action=contain
...
[1.50s] pos=(-5.8,-5.8) tgt=(-8.8,-6.9) intent=contain action=contain
```

After shedding at 0.70s, DE runs from x=-1.8 to x=-5.8 (further left, away from QB at x=0).

---

## Suggested Fixes

### Fix 1: Contain Direction

```python
# OLD: Runs away from QB
contain_pos = Vec2(
    world.me.pos.x + (3 if world.me.pos.x > 0 else -3),
    qb.pos.y
)

# NEW: Run toward QB to set edge between DE and QB
side = 1 if qb.pos.x > world.me.pos.x else -1
contain_pos = Vec2(
    qb.pos.x + side * 2,  # Stay 2 yards outside QB
    qb.pos.y
)
```

### Fix 2: Only Trigger Contain on True Scrambles

```python
# OLD: Any lateral movement triggers contain
if abs(qb.velocity.x) > abs(qb.velocity.y):

# NEW: Only trigger on significant scramble
if abs(qb.velocity.x) > 3.0 and abs(qb.velocity.x) > abs(qb.velocity.y) * 2:
```

### Fix 3: After Block Shed, Rush QB First

Add explicit post-shed behavior:
```python
# If just shed a block and QB has ball, rush QB
if not blocker and qb and qb.has_ball and qb.pos.y < world.los_y:
    return BrainDecision(
        move_target=qb.pos,
        move_type="sprint",
        action="rush",
        intent="free_rush",
        reasoning="Block shed! Rushing QB",
    )
```

---

## Impact

- DE never sacks QB even after winning the block
- Pocket stays clean despite bad pass protection
- Elite pass rushers become ineffective

---

**- QA Agent**
