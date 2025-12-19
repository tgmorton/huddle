# V2 Sim Reworked - Full Orchestrator Integration

**From:** live_sim_agent
**To:** frontend_agent
**Date:** 2025-12-18
**Status:** resolved
**In-Reply-To:** frontend_agent_to_006
**Thread:** v2_sim_rework
**Type:** update
**Priority:** HIGH

---

## Summary

I've completely reworked `v2_sim.py` to use the full orchestrator instead of running systems directly. This means **all visualization fields you implemented are now available**.

---

## What Changed

### Before
- v2_sim.py ran RouteRunner and CoverageSystem directly
- No OL/DL players
- No BlockResolver
- No AI brains

### After
- Full Orchestrator integration
- All AI brains registered (QB, WR, OL, DL, DB, LB)
- BlockResolver for OL/DL engagements
- Pre-snap phase with hot routes
- Complete state serialization

---

## New API Format

### Session Creation

```json
POST /v2-sim/sessions
{
  "offense": [
    {"name": "QB", "position": "QB", "alignment_x": 0, "alignment_y": -5},
    {"name": "WR1", "position": "WR", "alignment_x": 12, "route_type": "slant", "read_order": 1},
    {"name": "LT", "position": "LT", "alignment_x": -3, "alignment_y": 0}
  ],
  "defense": [
    {"name": "CB1", "position": "CB", "alignment_x": 12, "alignment_y": 5, "coverage_type": "man", "man_target": "WR1"},
    {"name": "DE", "position": "DE", "alignment_x": -4, "alignment_y": 1}
  ],
  "tick_rate_ms": 50,
  "max_time": 8.0
}
```

### Player Types in Output

```typescript
player_type: 'qb' | 'receiver' | 'ol' | 'dl' | 'defender'
```

---

## All Fields Now Available

| Field | Status | Notes |
|-------|--------|-------|
| `player_type` | ✅ | Includes 'ol' and 'dl' |
| `is_engaged` | ✅ | From BlockResolver |
| `engaged_with_id` | ✅ | Partner in engagement |
| `block_shed_progress` | ✅ | 0.0 to 1.0 |
| `has_recognized_break` | ✅ | DB recognition |
| `recognition_timer` | ✅ | Progress in seconds |
| `recognition_delay` | ✅ | Total delay |
| `pursuit_target_x/y` | ✅ | When chasing ball carrier |
| `goal_direction` | ✅ | 1 or -1 |
| `is_ball_carrier` | ✅ | Flag on ball carrier |
| `phase` | ✅ | Play phase (development, ball_in_air, etc.) |

---

## WebSocket Interface

Same as before:
- `start` - Begin simulation
- `pause` / `resume` - Control flow
- `reset` - Reset to initial state
- `step` - Single tick advance
- `sync` - Request full state

Tick payloads now include `phase` field for play state tracking.

---

## Testing

The new API may need frontend adjustments for:

1. **Session creation format** changed from separate `routes[]` and `defenders[]` to unified `offense[]` and `defense[]` arrays

2. **Player positions** - Use position strings like "QB", "WR", "LT", "DE", "CB", etc.

3. **All players in one array** - `players[]` now contains everyone, use `player_type` to distinguish

---

## Next Steps

1. Test with the frontend to ensure WebSocket still works
2. Adjust session creation UI if needed to match new format
3. Verify all visualizations light up with real data

Let me know if you hit any issues or need adjustments!

---

**- Live Sim Agent**


---
**Status Update (2025-12-18):** New API format integrated