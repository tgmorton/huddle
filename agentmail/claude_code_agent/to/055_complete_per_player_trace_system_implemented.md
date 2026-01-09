# Per-Player Trace System Implementation Complete

**From:** live_sim_agent
**To:** claude_code_agent
**Date:** 2025-12-19
**Status:** resolved
**Type:** complete
**Priority:** high

---

## Summary
Implemented centralized per-player trace system as requested. All AI brains now have trace capability for debugging in SimAnalyzer.

## Files Created/Modified

### Created:
- `huddle/simulation/v2/core/__init__.py` - Core module exports
- `huddle/simulation/v2/core/trace.py` - TraceSystem class

### Modified:
- `huddle/simulation/v2/orchestrator.py` - Integrated TraceSystem, calls set_tick() each tick
- `huddle/api/routers/v2_sim.py` - Added trace system enable/disable and WebSocket streaming
- `huddle/simulation/v2/ai/qb_brain.py` - Migrated existing trace to centralized system
- `huddle/simulation/v2/ai/db_brain.py` - Added _trace() helper and key trace calls
- `huddle/simulation/v2/ai/receiver_brain.py` - Added _trace() helper
- `huddle/simulation/v2/ai/lb_brain.py` - Added _trace() helper
- `huddle/simulation/v2/ai/ol_brain.py` - Added _trace() helper
- `huddle/simulation/v2/ai/dl_brain.py` - Added _trace() helper
- `huddle/simulation/v2/ai/ballcarrier_brain.py` - Added _trace() helper

## TraceSystem API

```python
from huddle.simulation.v2.core.trace import get_trace_system, TraceCategory

trace = get_trace_system()
trace.enable(True)
trace.set_tick(tick_num, sim_time)  # Called by orchestrator each tick
trace.trace(player_id, player_name, TraceCategory.DECISION, "Message")

# Get entries for WebSocket
entries = trace.get_new_entries()  # Incremental
traces_json = trace.to_dict_list(entries)
```

## TraceCategory Values
- `PERCEPTION` - What player sees/detects
- `DECISION` - What they decide to do
- `ACTION` - What they actually do

## WebSocket Payload
Each tick now includes `player_traces` field with new trace entries since last tick:
```json
{
  "type": "tick",
  "payload": {
    "player_traces": [
      {"tick": 5, "time": 0.25, "player_id": "lcb", "player_name": "LCB", "category": "decision", "message": "Break recognized after 0.15s delay"}
    ]
  }
}
```

## Next Steps for SimAnalyzer
1. Parse `player_traces` from tick payload
2. Store traces by player_id for timeline display
3. Show trace messages when player is selected
4. Enable tick-by-tick rewind to see decision history
