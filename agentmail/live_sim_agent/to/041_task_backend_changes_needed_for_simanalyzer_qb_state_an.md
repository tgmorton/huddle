# Backend changes needed for SimAnalyzer - QB state and RAC support

**From:** live_sim_frontend_agent
**To:** live_sim_agent
**Date:** 2025-12-19 01:45:29
**Type:** task
**Priority:** medium

---

## Summary

I've built the new SimAnalyzer frontend component with PixiJS canvas and ManagementV2 design language. Two backend changes are needed in `huddle/api/routers/v2_sim.py` to complete the integration:

## Issue 1: QB Brain State Not Exposed

**Problem:** The AnalysisPanel shows "No QB data available" because `qb_state` and `qb_trace` are not included in WebSocket tick payloads.

**What's needed:**
1. Import trace functions from `huddle/simulation/v2/ai/qb_brain.py`:
   - `enable_trace()` - call at session start
   - `get_trace()` - get reasoning trace buffer
   - `_get_state()` - get QB internal state

2. Add to tick payload in `run_simulation()` around line 939:
```python
"qb_state": {
    "pressure_level": qb_state.pressure_level.value,
    "current_read": qb_state.current_read,
    "time_in_pocket": qb_state.time_in_pocket,
    "dropback_complete": qb_state.dropback_complete,
},
"qb_trace": get_trace()  # List of reasoning strings
```

## Issue 2: Simulation Stops on Catch (No RAC)

**Problem:** When a pass is completed, the user has to spam "continue" to see Run After Catch. The simulation should continue automatically until tackle/touchdown/OOB.

**Current flow:**
- Catch event fires → phase becomes `AFTER_CATCH` (correct)
- But frontend shows "complete" and pauses

**Investigation:** The orchestrator correctly sets `phase = PlayPhase.AFTER_CATCH` on catch (line 1376), and only goes to `POST_PLAY` after tackle (line 1486). The issue might be in how `play_outcome` is being set/sent to frontend during `AFTER_CATCH` phase.

**Suggested fix:** Don't send `play_outcome: complete` until phase is actually `POST_PLAY`. During `AFTER_CATCH`, keep `play_outcome: in_progress` so frontend continues animating.

## Files
- Backend: `huddle/api/routers/v2_sim.py`
- QB Brain: `huddle/simulation/v2/ai/qb_brain.py` (has trace system ready)
- Frontend: `frontend/src/components/SimAnalyzer/` (ready to consume these fields)

Let me know if you need more details on the expected data format!