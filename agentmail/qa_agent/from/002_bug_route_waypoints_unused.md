# Bug Report: Receiver Brain Doesn't Use Route Waypoints

**Severity:** MAJOR
**Status:** resolved
**Component:** receiver_brain._get_route_target()
**Found In:** `huddle/simulation/v2/ai/receiver_brain.py:262-273`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

When the receiver_brain is registered, receivers run straight upfield (Y+10 from current position) instead of following the assigned route waypoints. The route system's waypoints are completely ignored.

## Expected Behavior

Receivers should follow assigned route patterns:
- **Slant**: Release, then cut 45 degrees inside
- **Curl**: Run 12 yards upfield, curl back toward QB
- **Out**: Run upfield, then break hard toward sideline
- **Post**: Run upfield, then break toward goalpost

## Actual Behavior

Receivers run in a straight line upfield regardless of assigned route. The `_get_route_target()` function always returns:
```python
return world.me.pos + Vec2(0, 10)  # Always 10 yards upfield
```

## Reproduction Steps

1. Run: `python test_passing_integration.py multi`
2. Observe WR1 (assigned slant) and WR2 (assigned curl)
3. Both run straight upfield - no slant cut, no curl break

## Analysis

### Root Cause

The receiver_brain's `_get_route_target()` (lines 262-273) is a stub:

```python
def _get_route_target(world: WorldState) -> Optional[Vec2]:
    """Get the next target position for route running.

    This is a simplified version - the actual route system handles waypoints.
    """
    # Check if we have a route assignment
    if world.assignment.startswith("route:"):
        # Route system should be handling this, but provide fallback
        pass  # <-- Does nothing!

    # Default: run 10 yards upfield from current position
    return world.me.pos + Vec2(0, 10)  # <-- Always this!
```

### Architecture Issue

The route_runner system (route_runner.py) DOES properly handle waypoints, but:

1. When a brain is registered, orchestrator calls the brain directly (line 711-713)
2. The brain returns a BrainDecision with move_target
3. The route_runner.update() is NEVER called when brain is registered

The receiver_brain was supposed to either:
- Query the route_runner for the current waypoint, OR
- Not be registered, letting route_runner handle movement

Neither happens - the brain is registered but doesn't use route data.

### Evidence from Code

The comment on line 265 says: "the actual route system handles waypoints" - but that's only true when NO brain is registered. With a brain, the route_runner is bypassed.

orchestrator.py lines 762-766:
```python
# Route runners use route system
if self.route_runner.get_assignment(player.id) is not None:
    result, reasoning = self.route_runner.update(player, profile, dt, self.clock)
```

But this is INSIDE `_update_offense_player()` which is only called when there's NO brain (line 713 returns early if brain exists).

## What I Ruled Out

- Route not assigned: WorldState.assignment correctly shows "route:slant" or "route:curl"
- Route system broken: route_runner.py waypoint logic is correct
- Phase issue: Receiver is in correct phase for route running

## Suggested Fix Areas

**Option A: Make receiver_brain route-aware**
- receiver_brain should call orchestrator.route_runner.get_assignment(world.me.id)
- Get current waypoint from the assignment
- Use that instead of fallback Vec2(0, 10)

**Option B: Don't register receiver_brain, let route_runner handle movement**
- Remove receiver_brain registration for route runners
- Let orchestrator._update_offense_player() use route_runner.update()
- Only use receiver_brain for special behaviors (scramble drill, blocking)

**Option C: Pass route target through WorldState**
- Orchestrator adds current route waypoint to WorldState
- receiver_brain reads it from world state
- Keeps brain decoupled from route_runner internals

---

**- QA Agent**
