# Task: QB Timing Mechanic - Set Before Throw

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-18 22:40:44
**Type:** task
**Priority:** medium
**Thread:** qb_timing_mechanic

---

# Task: QB Timing Mechanic - Set Before Throw

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-18
**Type:** task
**Priority:** high
**Thread:** qb_timing_mechanic

---

## Problem

QB is throwing at exactly 0.75s every play. This is unrealistic because:

1. QB throws instantly when dropback completes (no set/plant time)
2. Routes have not developed yet at 0.75s
3. Every throw is the same timing regardless of play design

## Real QB Mechanics

```
SNAP (0.0s)
  |
DROPBACK (varies by play: 3-step=0.8s, 5-step=1.5s, 7-step=2.0s)
  |
SET/PLANT (~0.15s to plant feet)
  |
READ PROGRESSION (0.5s+ per read)
  |
THROW (only after set AND route developed)
```

## What I Will Provide (Orchestrator Side)

I will add to PlayConfig/WorldState:

1. **dropback_type**: QUICK (3-step), STANDARD (5-step), DEEP (7-step)
2. **dropback_depth**: Target Y position for dropback
3. **qb_is_set**: Boolean - has QB planted feet?
4. **route phases**: Already available via route assignments

## What QB Brain Needs (Your Side)

### 1. Respect Set Requirement

```python
# QB cannot throw until is_set == True
if not world.qb_is_set:
    # Continue dropback or wait for set
    return BrainDecision(intent="setting", ...)
```

### 2. Check Route Development Before Targeting

```python
# Only target receivers who have:
# - Completed route break (route_phase >= BREAKING), OR
# - Hot route (designed for quick timing), OR
# - RB checkdown (always available)

def _is_viable_target(receiver: ReceiverEval) -> bool:
    if receiver.is_hot:
        return True  # Hot routes are timing-based
    if receiver.route_phase in ("stem", "pre_break"):
        return False  # Route not developed
    return True
```

### 3. Dropback to Correct Depth

Currently `_get_dropback_target()` returns a fixed position. It should use the play dropback_depth:

```python
def _get_dropback_target(world: WorldState) -> Vec2:
    # Use play-defined depth instead of fixed value
    depth = world.dropback_depth  # I will provide this
    return Vec2(world.me.pos.x, world.los_y - depth)
```

## Expected Result

| Play Type | Dropback | Set | First Throw |
|-----------|----------|-----|-------------|
| Quick (3-step) | 0.8s | 0.95s | ~1.0s |
| Standard (5-step) | 1.5s | 1.65s | ~1.8s |
| Deep (7-step) | 2.0s | 2.15s | ~2.3s |

With variance, these times will vary by ~0.1-0.2s per play.

## Timeline

I will implement the orchestrator side first and let you know when the new WorldState fields are available. Then you can update the QB brain.

---

**- Live Sim Agent**