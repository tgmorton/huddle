# Bug Fixes Ready for Verification

**From:** Live Sim Agent
**Date:** 2025-12-18
**Status:** resolved
**Priority:** HIGH

---

## Fixed Bugs

### 1. Vision Filter (Bug 009) - BLOCKING

**File:** `ballcarrier_brain.py:202`

**Fix:**
```python
# OLD: Filtered out close threats behind ballcarrier
if angle > vision_params.angle / 2:
    continue

# NEW: Allow very close threats regardless of angle
if angle > vision_params.angle / 2 and distance > 2.0:
    continue
```

**Why:** Threats < 2 yards now always perceived (instinctive awareness).

---

### 2. DB Backpedal Direction (Bug 011) - MAJOR

**File:** `db_brain.py:445`

**Fix:**
```python
# OLD: Went behind receiver (wrong!)
cushion_target = receiver.pos - Vec2(0, state.cushion)

# NEW: Stay AHEAD of receiver (higher Y)
cushion_target = receiver.pos + Vec2(0, state.cushion)
```

**Why:** DB now maintains cushion in front of receiver, not behind.

---

### 3. DL Contain Direction (Bug 010) - MAJOR

**File:** `dl_brain.py:292-317`

**Fix 1 - Higher threshold for contain:**
```python
# OLD: Any lateral movement triggered contain
if qb.velocity.x != 0 and abs(qb.velocity.x) > abs(qb.velocity.y):

# NEW: Only significant scrambles
qb_scrambling = (
    abs(qb.velocity.x) > 3.0 and  # Significant lateral speed
    abs(qb.velocity.x) > abs(qb.velocity.y) * 2  # Mostly lateral
)
```

**Fix 2 - Correct contain position:**
```python
# OLD: Ran further outside (away from QB)
contain_pos = Vec2(
    world.me.pos.x + (3 if world.me.pos.x > 0 else -3),
    qb.pos.y
)

# NEW: Position between DE and QB
side = 1 if qb.pos.x > world.me.pos.x else -1
contain_pos = Vec2(
    qb.pos.x + side * 2,  # Stay 2 yards outside QB
    qb.pos.y
)
```

**Why:** After shedding, DE now rushes QB (unblocked path) instead of entering contain mode on minor pocket movement.

---

## Please Verify

1. **Vision filter:** Run evasion test - ballcarrier should now detect threats behind them
2. **DB backpedal:** CBs should maintain position ahead of WRs during first second
3. **DL contain:** After block shed, DE should rush QB directly (not run sideways)

---

**- Live Sim Agent**
