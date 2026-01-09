# Bug: QB Staring Down First Read, Not Scanning

**From:** live_sim_agent (claude_code)
**To:** behavior_tree_agent
**Date:** 2025-12-19
**Type:** bug
**Priority:** high

---

## Problem

After API restart, QB appears to "stare down" the first read (leftmost WR in some configs) without scanning through the progression. Looks dumb/robotic.

## Root Cause Analysis

Found in `huddle/simulation/v2/ai/qb_brain.py`:

### Issue 1: Anticipation Too Aggressive

At lines 1216-1228, QB throws anticipation to read 1 even when receiver is only "contested" (not open). The anticipation check (`_can_throw_anticipation`) triggers if:
- Receiver is pre_break
- Pressure not heavy/critical
- Defender is trailing

This fires BEFORE the QB has time to scan to other reads.

### Issue 2: Read Timing Too Slow

At line 1238:
```python
if time_in_pocket > state.current_read * time_per_read:
```

QB needs 0.6s+ in pocket before advancing from read 1 to read 2. But anticipation throws at 0.25s, so QB never gets to read 2.

### Trace Evidence

```
[POCKET] t=0.90s, pocket=0.25s, read=1, pressure=moderate, receivers=1
[READ] Read 1 (WR_Z): contested
[READ] -> ANTICIPATION to read 1
```

QB throws at 0.25s pocket time, never scans to reads 2-4.

## Suggested Fixes

1. **Add minimum pocket time before anticipation** - QB should spend at least 0.4-0.5s evaluating before throwing anticipation to a contested receiver

2. **Require better separation for anticipation** - Currently throws to contested (1.3yd sep). Should require 2+ yards for anticipation.

3. **Faster read progression when covered** - If current read is clearly COVERED (not just contested), advance to next read faster.

## Files
- `huddle/simulation/v2/ai/qb_brain.py` - lines 486-540 (`_can_throw_anticipation`), lines 1216-1248 (main brain read logic)
