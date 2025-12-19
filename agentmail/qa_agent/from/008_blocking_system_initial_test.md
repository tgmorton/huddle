# BlockResolver Initial Test Report

**Status:** open (with observations)
**Component:** `resolution/blocking.py`, `ol_brain`, `dl_brain`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Test Results

### Test 1: Engagement
- **Result:** PASS
- LT and DE closed from 2 yards to 1.7 yards
- Players moving toward each other as expected

### Test 2: Block Shed (Weak OL vs Elite DE)
- **Result:** PARTIAL
- Block sheds at 0.40s and 0.95s (events emitted correctly!)
- Elite Edge sheds Weak Tackle's block twice
- **Issue:** After shed, DE went to X=-32.7 instead of pursuing QB
- Expected: DE should rush QB after shedding

### Test 3: Long Developing Play
- **Result:** PASS
- Block shed at 2.50s (after 2.5 seconds of blocking)
- Play completed at 4.55s with pass

---

## What's Working

1. **Engagement** - OL and DL close distance when brains registered
2. **Block shed progress** - Accumulates when DL winning
3. **Block shed events** - `block_shed` event emits correctly
4. **Attribute resolution** - Weak OL (60/55) loses to Elite DE (95)

---

## Observations

### Post-Shed Behavior

After shedding, the DE position was unexpected:
```
QB: (5.8, -8.1)
DE: (-32.7, -7.8)  <-- Way left, not toward QB
```

The DE should pursue the QB after winning the block, but went in the opposite direction. This may be:
1. DL brain doesn't have "pursue QB after shed" logic
2. Movement override from block resolver pushing DE wrong way
3. Some other issue with post-shed state

### Quick Pass vs Block Shed

- Test 1: Quick pass (1.5s throw), no shed - correct, ball out too fast
- Test 3: Late throw (3.0s), shed at 2.50s - correct, pressure develops

---

## Integration Test Confirmation

From `test_passing_integration.py multi`:
```
LT: (-1.27, -0.49)  started at (-3, -2) - moved toward engagement
DE1: (-1.06, 1.43)  started at (-3, 1) - moved toward engagement
```

Both players engaged in the pocket area as expected.

---

## Recommendation

Check DL brain behavior after block shed:
- Should transition to "rush QB" mode
- Should target QB position, not continue in previous direction

---

**Files Created:**
- `agentmail/qa_agent/test_scripts/test_blocking_system.py`

**- QA Agent**
