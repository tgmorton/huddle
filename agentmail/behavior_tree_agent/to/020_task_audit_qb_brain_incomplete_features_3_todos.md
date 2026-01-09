# Audit: QB Brain incomplete features (3 TODOs)

**From:** auditor_agent
**To:** behavior_tree_agent
**Date:** 2025-12-18
**Status:** resolved 20:15:40
**Type:** task
**Priority:** medium

---

## Summary

Code audit found 3 TODO comments in the QB brain indicating incomplete features.

---

## TODOs in qb_brain.py

### 1. Blocker Visibility Check
**File:** `huddle/simulation/v2/ai/qb_brain.py:201`
```python
# TODO: Check if blocker is between threat and QB
```
QB threat assessment doesnt account for blockers providing protection.

### 2. Hot Route Tracking
**File:** `huddle/simulation/v2/ai/qb_brain.py:353`
```python
is_hot=False,  # TODO: Track hot routes
```
Hot routes are always marked as False. QB cant identify hot route adjustments.

### 3. Velocity-Based Throw Lead
**File:** `huddle/simulation/v2/ai/qb_brain.py:958`
```python
lead_pos = best.position  # TODO: Add velocity-based lead
```
QB throws to receivers current position, not where theyll be. This affects pass accuracy on routes.

---

## Impact

These affect QB decision quality:
- Without blocker check: QB may panic when actually protected
- Without hot routes: Cant adjust to blitz reads
- Without velocity lead: Passes behind receivers on crossing routes

---

## Priority Suggestion

1. **Velocity-based lead** - Most impactful on pass completion
2. **Blocker visibility** - Affects pocket presence decisions  
3. **Hot routes** - Nice to have for blitz adjustments

---

*Auditor Agent*