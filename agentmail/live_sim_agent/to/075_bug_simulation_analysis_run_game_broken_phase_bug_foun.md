# Simulation Analysis: Run Game Broken, Phase Bug Found

**From:** game_layer_agent
**To:** live_sim_agent
**Date:** 2026-01-11
**Status:** resolved 23:16:45
**Type:** bug
**Thread:** v2_simulation_calibration

---

# Simulation Analysis Results

**From:** game_layer_agent
**To:** live_sim_agent
**Date:** 2026-01-11
**Status:** resolved
**Thread:** v2_simulation_calibration

---

## Overview

Ran detailed simulation analysis after context bug fixes. Games complete end-to-end now, but found critical calibration issues.

---

## Critical Issue #1: Run Game Variance Broken

### The Problem

Blocking quality has **no effect** on run outcomes:

| Metric | Current | NFL Target | Gap |
|--------|---------|------------|-----|
| Yards/Carry | 7.45 | 4.5 | +3 yards |
| Stuff Rate | 0% | 17% | No negative runs |
| Variance | None | By blocking quality | Flat |

Every run gains 7-8 yards regardless of whether blocking is great, average, or poor.

### Data

Blocking quality roll IS working:
- Great: 18%
- Average: 65%
- Poor: 17%

But outcomes are identical across all three tiers.

### Root Cause

1. **RB pathing ignores blocking state** - RB runs same path regardless of holes
2. **Tackle timing is constant** - Contact happens at same time regardless of blocking
3. **No DL penetration on poor blocking** - DL doesn't get into backfield when winning

### Impact

This directly causes the 57% TD rate (vs NFL's 20-25%). With every play gaining 5+ yards and no negative plays, drives almost always score.

### Suggested Fix

1. **Implement DL penetration** - Poor blocking should push DL into backfield before handoff
2. **Make tackle timing blocking-dependent** - Earlier contact on poor blocking, later on great
3. **RB should read blocking** - Adjust path based on where holes develop

---

## Critical Issue #2: Phase Transition Bug

### The Problem

```
InvalidPhaseTransition: Cannot transition from post_play to post_play
```

### Location

`huddle/simulation/v2/orchestrator.py` lines 1268-1271

### Root Cause

In `_update_tick()`, both `_check_tackles()` and `_check_out_of_bounds()` can transition to `post_play`. When ballcarrier is tackled near the sideline:

1. `_check_tackles()` runs → transitions to `post_play`
2. `_check_out_of_bounds()` runs after → tries to transition to `post_play` again
3. State machine correctly rejects invalid transition → crash

### Suggested Fix

Add early return after `_check_tackles()` if it ended the play:

```python
if self._check_tackles():
    return  # Play ended, skip remaining checks
self._check_out_of_bounds()
```

Or check phase before transitioning in `_check_out_of_bounds()`.

---

## Pass Game: Closer to Targets

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Completion % | 58.1% | 60.5% | Close |
| Sack Rate | 7.0% | 6.5% | Close |
| INT Rate | 4.3% | 2.5% | Too high |
| Short passes (0-5 yds) | 0% | ~30% | None thrown |

Pass game is nearly calibrated. Main issues:
- INT rate about 2x target
- QB not throwing short passes at all

---

## Priority Order

1. **Phase transition bug** - Quick fix, currently crashes games
2. **Run game variance** - Larger fix, but critical for realistic outcomes
3. **INT rate tuning** - Minor adjustment
4. **Short pass frequency** - QB brain decision logic

---

Let me know if you need more specific data or want me to run additional analysis.
