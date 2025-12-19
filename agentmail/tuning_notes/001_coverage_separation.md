# Coverage System Tuning Notes

**From:** Live Simulation Agent
**Date:** 2025-12-17
**Priority:** Low (not blocking, tune later)
**File:** `huddle/simulation/v2/systems/coverage.py`

---

## Issue

Man coverage is tracking too tightly. Receivers aren't creating realistic separation on timing routes.

## Test Results

Ran scenarios via `python -m huddle.simulation.v2.testing.run_scenarios`:

| Route | Initial Cushion | Separation at Break | Min Separation | Expected |
|-------|-----------------|---------------------|----------------|----------|
| Slant | 7.2 yd | 0.6 yd | 0.2 yd | 1.5-2.5 yd at break |
| Curl | 7.2 yd | 0.5 yd | 0.1 yd | 2-3 yd window |
| Go | 7.2 yd | N/A | 0.6 yd | ~correct (DB faster) |

## Root Cause Analysis

The `CoverageSystem._update_man_coverage()` uses predictive tracking that's too aggressive:

1. **Lookahead is generous** - DB projects where WR will be 6-12 ticks ahead
2. **Reaction delay may be too short** - `BASE_REACTION_DELAY = 5` ticks (0.25s)
3. **No cushion maintenance phase** - DB immediately closes rather than backpedaling to maintain depth during stem

## Tuning Knobs (for later)

```python
# In coverage.py
BASE_LOOKAHEAD_TICKS = 6      # Maybe reduce to 4?
MAX_LOOKAHEAD_TICKS = 12      # Maybe reduce to 8?
BASE_REACTION_DELAY = 5       # Maybe increase to 7-8?
FLIP_HIPS_SPEED_PENALTY = 0.45  # Maybe reduce to 0.35?
```

## Potential Fixes (not implemented yet)

1. **Add backpedal/cushion phase** - DB maintains depth during WR stem, doesn't close until break
2. **Reduce lookahead for close coverage** - When within 3 yards, react more than predict
3. **Route-specific reaction delays** - Slants should catch DBs more than curls
4. **Release phase impact** - WR should gain 0.5-1 yard at LOS vs off coverage

## Why This Can Wait

- Coverage system is **functional** - it works mechanically
- This is **realism tuning**, not architecture
- Need full plays running first to see how it feels in context
- Numbers might look different when QB is making actual throw decisions

## Action

Revisit after orchestrator is complete and we're running full passing plays. Tune based on watching actual play outcomes, not isolated route tests.

---

**Status:** Documented, deferred
