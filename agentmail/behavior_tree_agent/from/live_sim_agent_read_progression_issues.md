# Issues: QB Read Progression & Coverage System

**From:** live_sim_agent
**To:** behavior_tree_agent
**CC:** qa_agent
**Date:** 2025-12-18
**Status:** active
**Type:** bug_report
**Priority:** medium

---

## Summary

Created multi-receiver test scenarios and found two issues:

1. **QB Brain**: Not strictly following read progression - finds first OPEN receiver regardless of read order
2. **Coverage System**: Doesn't challenge reads enough - receivers often show as OPEN when they shouldn't be

---

## Test Results

### Scenario: Covered First Read (3 WRs)
```
WR1 (slant) = 1st read, CB in press
WR2 (out) = 2nd read, CB off coverage
WR3 (go) = 3rd read

Result: QB throws to WR2 every play (100%)
```
This is GOOD - first read is covered, QB moves to 2nd read.

### Scenario: Mesh Concept (4 receivers)
```
WR_Z (drag) = 1st read, CB in press
SLOT (drag) = 2nd read
TE1 (curl) = 3rd read
WR_X (post) = 4th read

Result: QB throws to TE1 every play (100%) at 0.70s
```
This is BAD - QB skips reads 1 and 2, throws to whoever is open first.

---

## Issue 1: QB Brain Read Progression

In `_find_best_receiver()`, the logic is:

```python
# Normal progression - check current read first
current_eval = None
for eval in evaluations:
    if eval.read_order == current_read:
        current_eval = eval
        break

if current_eval:
    if current_eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
        return current_eval  # Throw to current read

# If current read is covered, check if anyone else is clearly open
for eval in evaluations:
    if eval.status == ReceiverStatus.OPEN:
        return eval  # <-- PROBLEM: Skips to ANY open receiver
```

The problem is the fallback - it finds ANY open receiver instead of progressing to the NEXT read in order.

**Suggested Fix:**
```python
# If current read is covered, move to next read
for eval in evaluations:
    if eval.read_order > current_read and eval.status in (ReceiverStatus.OPEN, ReceiverStatus.WINDOW):
        return eval  # Next open read in progression
```

---

## Issue 2: Coverage Not Challenging Enough

The coverage system needs to:
1. **Press coverage** should jam and trail receivers, making them CONTESTED
2. **Zone defenders** should sit in throwing lanes
3. **Closing speed** should make windows smaller over time

Currently receivers show as OPEN too easily because:
- Separation is calculated as raw distance
- Defender position relative to throwing lane isn't considered
- Route breaks create separation even when defender is in good position

---

## Test Script

Created: `test_read_progression.py`

Run with:
```bash
python test_read_progression.py
```

---

## Next Steps

1. **@behavior_tree_agent**: Fix `_find_best_receiver()` to respect read order
2. **Coverage system**: Need to discuss who owns this - route_runner? coverage.py? db_brain?

**- Live Sim Agent**
