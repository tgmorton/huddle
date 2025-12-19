# Bug Report: Route Waypoint Advancement Stops After First Waypoint

**Severity:** BLOCKING
**Status:** resolved
**Component:** Route runner / receiver brain waypoint advancement
**Found In:** Observed in `receiver_brain` + `route_runner` interaction
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

On a slant route, the receiver reaches the first waypoint (Y=1.0) at 0.35s and then STOPS. They never advance to waypoints 2, 3, or 4 of the route. The receiver stays frozen at Y=1.0 until catch at 2.25s.

This blocks the ballcarrier brain test because:
1. Receiver doesn't run the actual route
2. CB closes during the long wait
3. Tackle happens same tick as catch
4. No YAC opportunity for ballcarrier brain

## Expected Behavior

Slant route waypoints:
1. Vec2(0, 1) - Quick release
2. Vec2(0, 3) - Threaten vertical
3. Vec2(4, 5) - Break inside (the slant)
4. Vec2(12, 10) - Continue across

WR should progress through all waypoints, ending up around X=3, Y=10 (slant breaking inside from X=15 start).

## Actual Behavior

```
[Tick 7] t=0.35s - WR at (15.00, 1.00)  <-- Reaches waypoint 1
[Tick 8] t=0.40s - WR at (15.00, 1.00)  <-- STUCK
...
[Tick 44] t=2.20s - WR at (15.00, 1.00) <-- Still stuck!
[Tick 45] t=2.25s - Catch and tackle at same position
```

The WR never advances past the first waypoint. X stays at 15.0 (no slant break inside).

## Reproduction Steps

1. Run: `python agentmail/qa_agent/test_scripts/test_ballcarrier_brain.py`
2. Observe tick-by-tick: WR reaches Y=1.0 at tick 7 and stays there
3. WR never advances to Y=3, Y=5 (break), or Y=10 (post-break)

## Analysis

### Possible Causes

1. **route_target not updating after first waypoint**
   - WorldState.route_target may be stuck on waypoint 1
   - route_runner.get_assignment() may not be advancing current_waypoint_idx

2. **receiver_brain not requesting movement**
   - _get_route_target() may be returning cached/stale value
   - Brain may be in wrong phase (not checking route_target after release)

3. **Arrival threshold issue**
   - Receiver arrives at Y=1.0 but isn't triggering waypoint advancement
   - route_runner.update() may not be called when brain is active

### Key Observation

The curl route worked (WR settled at Y=3.0 after going through waypoints). The slant route is stopping at Y=1.0 (first waypoint only).

Difference:
- Curl break is at ~Y=10, settle at Y=12
- Slant first waypoint is at Y=1 (very shallow)

Maybe the slant's first waypoint (Y=1) is close enough to start (Y=0) that it triggers immediately and doesn't advance?

## Secondary Issue: Same-Tick Tackle

Even if route worked, tackle happens at 2.25s (same tick as catch). This gives ballcarrier brain zero ticks to run. Should there be at least 1-2 ticks after catch before tackle is possible?

---

## Files Created

- `agentmail/qa_agent/test_scripts/test_ballcarrier_brain.py` - Test that exposed this bug

**- QA Agent**
