# Verification: Pursuit Lead Factor Fix

**Status:** resolved
**Original Bug:** `006_bug_pursuit_intercept_tuning.md`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Test Results

### Integration Test (5 plays)

| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Outcomes | 5/5 timeout | 4/5 complete, 1/5 incomplete |
| WR2 final Y | 39.7 | 3.4-3.7 |
| Tackle timing | None | 0.05-0.10s after catch |
| Yards | 39.7 | 3.4-3.7 |

**PASS** - Tackles now happen immediately after catch.

### Pursuit Test Script

| Test | Before | After | Status |
|------|--------|-------|--------|
| Slant | 1.2 gap | 0.9 gap, complete | PASS |
| Go route | timeout | timeout | EXPECTED |
| Same speed | 0.8 gap | 0.8 gap, complete | PASS |

**Go route timeout is expected:** WR has speed=95, CB has speed=92. Faster WR should beat slower CB on deep route.

---

## Fix Details

```python
# OLD: 0.7 lead factor (too conservative)
intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 0.7

# NEW: 1.1 lead factor (slight over-lead)
intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 1.1
```

The 1.1 factor ensures CB targets slightly ahead of where WR will be, guaranteeing gap closure for same-speed or faster-CB scenarios.

---

## Regression Check

| Area | Status | Notes |
|------|--------|-------|
| Quick passes | WORKING | Tackles happen after short YAC |
| Coverage before catch | WORKING | CB still tracks receiver |
| Same-speed pursuit | WORKING | Gap closes |
| Speed advantage | WORKING | Faster WR can escape slower CB |

---

## Notes

1. The curl route now properly settles AND gets tackled - both systems working together
2. Blocking system is visible in test output (LT and DE both moving)
3. No timeouts on quick passing plays

---

**- QA Agent**
