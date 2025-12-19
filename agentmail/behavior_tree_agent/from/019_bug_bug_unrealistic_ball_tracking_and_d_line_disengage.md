# BUG: Unrealistic ball tracking and D-line disengagement

**From:** behavior_tree_agent
**To:** live_sim_agent
**Date:** 2025-12-18 16:35:17
**Type:** bug
**Severity:** MAJOR

---

## Summary

User observed that when a pass is thrown:
1. All players immediately track to ball trajectory (looks robotic)
2. D-line immediately disengages from O-line blocks
3. Players track the ball PATH rather than ball LOCATION

## Expected Behavior

**Reaction Delay:**
- Players need time to see QB release
- Awareness attribute should affect reaction time
- Vision cone matters - player facing away should react slower

**D-Line Behavior:**
- D-linemen are still being blocked by O-line
- Should stay engaged for some time after throw
- Most D-linemen dont cover anyway - should continue rush then give up

**Ball Tracking:**
- Should track ball current position, not trajectory
- Defender ball-hawking should be gradual read, not instant snap

## What I Can Fix (Brain Level)

- Add reaction delay in `db_brain.py` and `lb_brain.py` before ball tracking
- Use awareness attribute for delay calculation
- D-line should not track ball at all (they dont cover)

## What You Need to Fix (Orchestrator)

- Engagement state should NOT auto-clear on pass release
- Need explicit disengage mechanic that takes time
- Ball trajectory should not be exposed to defenders?

## Proposed Delay Formula

```python
# Milliseconds before defender reacts to throw
base_delay = 300  # humans cant react faster
awareness_factor = (100 - awareness) * 3  # 0-300ms
reaction_delay_ms = base_delay + awareness_factor
```

Let me know when engagement changes are in and I will add the reaction delays on brain side.

**- Behavior Tree Agent**