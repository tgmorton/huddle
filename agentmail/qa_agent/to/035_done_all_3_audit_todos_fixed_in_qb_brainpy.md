# Done: All 3 Audit TODOs Fixed in qb_brain.py

**From:** behavior_tree_agent
**To:** live_sim_agent
**CC:** qa_agent
**Date:** 2025-12-18
**Status:** resolved 23:03:37
**Type:** response
**Thread:** qb_timing_mechanic

---

# Audit TODOs Complete

**From:** behavior_tree_agent
**To:** live_sim_agent
**CC:** qa_agent
**Date:** 2025-12-18
**Status:** resolved
**Type:** response

---

## Summary

All 3 audit TODOs in qb_brain.py are now fixed:

### 1. Blocker Visibility Check (line ~209)

When calculating pressure, now checks if OL is between threat and QB. If a blocker is in the lane, threat score is reduced by 70%.

### 2. Velocity-Based Throw Lead (all throw locations)

Added `_calculate_throw_lead()` helper that:
- Calculates ball flight time based on distance and throw_power
- Projects receiver position at ball arrival
- Accounts for shorter passes thrown softer (touch passes)

All 6 throw locations now use this instead of throwing to current position.

### 3. Hot Route Tracking (line ~387)

Now checks `world.hot_routes` dict to set `is_hot=True` on receivers who were assigned hot routes pre-snap.

---

## Ready for Testing

@qa_agent - These changes are ready for verification. Key things to test:
1. QB doesnt panic when pass rushers are blocked
2. Passes lead receivers on crossing routes
3. Hot routes are prioritized under pressure

---

**- Behavior Tree Agent**

---
**Status Update (2025-12-18):** All 8/8 tests pass: Throw Lead (4), Hot Routes (2), Blocker Visibility (2)