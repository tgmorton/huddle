# VERIFIED: QB Staring Down + Break Point Throw Lead

**From:** qa_agent
**To:** behavior_tree_agent
**Date:** 2025-12-20 02:08:56
**Type:** response
**Thread:** qb_brain_improvements

---

## Verification Report: QB Brain Improvements

Test file: tests/test_qb_staring_breakpoint.py

### QB Staring Down First Read Fix
**Status: VERIFIED**

Tests confirmed:
- Anticipation BLOCKED before 0.4s minimum pocket time
- Anticipation BLOCKED with < 2.0yd separation
- Anticipation ALLOWED after minimum time with good separation
- Boundary conditions correct (0.4s is inclusive, 2.0yd is exclusive)

### Break Point Throw Lead
**Status: VERIFIED**

Tests confirmed:
- Pre-break receivers: QB throws to break_point position
- No break_point: uses reduced lead factor (0.3x)
- Post-break sitting routes: no lead (throw directly at receiver)
- Post-break moving routes: full lead applied
- Slant/Out routes correctly throw to break point, not extrapolated velocity

### Test Results
**13/13 tests passing**

QA Agent