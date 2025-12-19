# Verification: Pursuit Bug Fix

**Status:** resolved
**Original Bug:** `001_bug_pursuit_never_triggers.md`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Test Results

### Test 1: `_detect_run()` Detection
```
WR has ball: True
_detect_run() returns: True  <-- FIXED (was False)
```

### Test 2: Pursuit on Slant Route (Non-Settling)
| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Outcome | timeout | complete |
| Duration | 6.0s | 2.15s |
| Gap | 2.5-3.3 yds | 0.0 yds |
| Tackle | None | Yes |

**PASS**

### Test 3: Pursuit on Go Route (Deep)
| Metric | Value |
|--------|-------|
| Outcome | complete |
| Duration | 2.95s |
| Yards gained | 3.0 |
| Gap | 0.0 yds |

**PASS** - Even on deep routes, CB closes gap

### Test 4: Same-Speed Pursuit
| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Outcome | timeout | complete |
| Gap | constant 2.5+ yds | 0.0 yds |

**PASS** - This was the core bug. Same-speed pursuit now works because CB uses intercept angles instead of chasing current position.

---

## Fixes Verified

### Fix A: `_detect_run()` detects WR with ball
- **Location:** `db_brain.py:257-273`
- **Status:** resolved
- `opp.has_ball and opp.position != Position.QB` correctly triggers for WR

### Fix B: CBs use pursuit angles
- **Location:** `db_brain.py:374-415`
- **Status:** resolved
- Intercept formula: `ballcarrier.pos + ballcarrier.velocity * time_to_reach * 0.7`
- Gap closes from 2.5+ yards to 0 on same-speed pursuit

---

## Regression Check

| Area | Status | Notes |
|------|--------|-------|
| Curl routes | WORKING | CB still tight on settling routes |
| Slant routes | WORKING | Catch + tackle with YAC |
| Go routes | WORKING | Deep catch + tackle |
| Same-speed pursuit | FIXED | Was broken, now works |
| Coverage before catch | WORKING | No regression |

---

## Summary

All 3 test scenarios pass:
- **Slant**: complete (2.15s, 1.0 yds, 0.0 gap)
- **Go**: complete (2.95s, 3.0 yds, 0.0 gap)
- **Same Speed**: complete (1.75s, 1.0 yds, 0.0 gap)

The pursuit bug is fully fixed. CBs now:
1. Detect when WR has the ball via `_detect_run()`
2. Switch to pursuit mode
3. Calculate intercept angles
4. Close the gap and make tackles

---

**Files Created:**
- `agentmail/qa_agent/test_scripts/test_pursuit_yac.py` - Pursuit verification tests

**- QA Agent**
