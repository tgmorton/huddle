# Bug Report: DB Backpedal Goes Wrong Direction

**Status:** resolved
**Severity:** MAJOR
**Component:** `db_brain.py` - Backpedal phase cushion calculation
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

During the backpedal phase (first 1.0 seconds), the DB calculates the cushion target incorrectly, causing them to run BEHIND the receiver instead of staying in front. This results in 7+ yard separation by the time a pass arrives, making contested catches impossible.

---

## Root Cause

In `db_brain()` line 445:

```python
# Maintain cushion while reading
cushion_target = receiver.pos - Vec2(0, state.cushion)
```

This calculates: `target = receiver_pos - (0, 7)` = position 7 yards BEHIND receiver.

For a receiver at (10, 0), target becomes (10, -7.0). The DB runs backwards (negative Y) while the WR runs forwards (positive Y), opening a huge gap.

---

## Test Output

```
[0.05s] WR=(10.0,0.0) CB=(10.0,0.5) Gap=0.5
[0.55s] WR=(9.7,1.8) CB=(10.0,-0.6) Gap=2.5   <-- CB going negative Y!
[1.05s] WR=(10.0,5.2) CB=(10.0,-2.0) Gap=7.2  <-- Gap exploded
```

Despite starting 0.5 yards away, gap reaches 7+ yards in 1 second.

---

## Impact

1. **Contested catches never happen** - DB always too far away at catch time
2. **Interceptions impossible** - Defender can't have position advantage
3. **Deep passes unrealistic** - WR always open regardless of coverage skill

---

## Suggested Fix

```python
# OLD: Wrong direction
cushion_target = receiver.pos - Vec2(0, state.cushion)

# NEW: Stay in front of receiver (higher Y = further downfield)
cushion_target = receiver.pos + Vec2(0, state.cushion)
```

Or for more nuanced coverage:

```python
# Mirror laterally, maintain cushion vertically
cushion_target = Vec2(receiver.pos.x, receiver.pos.y + state.cushion)
```

---

## Notes

This explains why passes consistently complete even with elite CBs vs below-average WRs. The coverage mechanics are sound, but the DB never gets close enough to contest.

---

**- QA Agent**
