# Live Simulation Agent - Status

**Last Updated:** 2025-12-18
**Agent Role:** Core simulation systems, orchestrator, physics, resolution systems

---

## V2 Simulation Status

### COMPLETE (Functional)

| Layer | Files | Notes |
|-------|-------|-------|
| Core | `core/vec2.py`, `entities.py`, `field.py`, `clock.py`, `events.py` | All solid |
| Physics | `physics/movement.py`, `spatial.py`, `body.py` | Movement solver, influence zones |
| Systems | `systems/route_runner.py` | Routes with waypoint advancement, hot routes |
| Systems | `systems/coverage.py` | Man + zone coverage |
| Systems | `systems/passing.py` | Ball flight, catch resolution |
| Plays | `plays/routes.py` | 13 route definitions |
| Resolution | `resolution/tackle.py` | Tackle outcomes, broken tackles |
| Resolution | `resolution/move.py` | Ballcarrier moves (juke, spin, etc.) |
| Resolution | `resolution/blocking.py` | OL/DL engagement, shed progress |
| Orchestrator | `orchestrator.py` | Main loop, WorldState, pre-snap phase |
| AI Brains | `ai/*.py` | QB, receiver, ballcarrier, DB, LB, OL, DL |
| Testing | `testing/`, `test_passing_integration.py` | Scenario runner, integration tests |

### TODAY'S WORK (2025-12-18)

| Task | Status | Notes |
|------|--------|-------|
| Pre-snap phase | ✅ DONE | QB reads defense, calls hot routes |
| Hot route system | ✅ DONE | `route_runner.change_route()` method |
| WebSocket wiring | ✅ DONE | DB recognition, pursuit, goal_direction |
| Vision filter bug | ✅ FIXED | Threats <2yd now always perceived (bug 009) |
| DB backpedal direction | ✅ FIXED | Now stays ahead of receiver (bug 011) |
| DL contain direction | ✅ FIXED | Correct contain position (bug 010) |
| Break recognition delay | ✅ DONE | Cognitive delay before DB tracks break |
| PlayHistory wiring | ✅ DONE | Orchestrator records plays, passes to WorldState |

### WEBSOCKET FIELDS (v2_sim.py)

| Field | Status | Notes |
|-------|--------|-------|
| `goal_direction` | ✅ | 1 for offense, -1 for defense |
| `has_recognized_break` | ✅ | DB recognition state |
| `recognition_timer` | ✅ | Progress toward recognition |
| `recognition_delay` | ✅ | Total delay required |
| `pursuit_target_x/y` | ✅ | Pursuit line endpoints |
| `is_ball_carrier` | ✅ | Flag for ballcarrier ID |
| OL/DL player types | ❌ | Not in v2_sim (needs orchestrator) |
| Blocking engagement | ❌ | Not in v2_sim (needs BlockResolver) |
| Ballcarrier moves | ❌ | Not in v2_sim (needs brain) |

---

## Key Systems

### Pre-Snap Phase (NEW)

Location: `orchestrator.py`

- `_do_pre_snap_reads()` called before snap
- QB brain evaluates defense, returns hot routes
- `_apply_hot_route()` calls `route_runner.change_route()`
- Emits HOT_ROUTE and PROTECTION_CALL events

### BlockResolver

Location: `resolution/blocking.py`

- Engagement detection (1.5 yard range)
- Action matchup (anchor vs bull_rush, etc.)
- Attribute-based resolution (block_power/finesse vs pass_rush)
- Shed progress tracking (DL accumulates when winning)
- Movement override (winner pushes loser)
- Emits BLOCK_SHED events

### Break Recognition System

Location: `ai/db_brain.py`

- **Cognitive delay**: DB doesn't instantly know when receiver breaks
- **Recognition timer**: Starts when break detected, must elapse before DB reacts
- **Delay calculation**: Base (0.12s) + play_recognition modifier + route difficulty
- **Attribute-driven**: High play_rec = faster recognition, low = slower
- **Route-dependent**: Corner (0.14s) harder to read than curl (0.05s)

Example delays:
- Elite DB (95 play_rec) vs curl: ~0.17s
- Average DB (75 play_rec) vs slant: ~0.26s
- Poor DB (60 play_rec) vs post: ~0.44s

---

## Integration Test

```bash
python test_passing_integration.py        # Single play
python test_passing_integration.py multi  # 5 plays
```

Players: QB, WR1, WR2, LT, DE, CB1, CB2, MLB

---

## Pending / Next Up

1. **Full orchestrator WebSocket** - For OL/DL and ballcarrier move visualization
2. **game_situation population** - For clock-aware decisions
3. **Inner Weather integration** - Receive pre-game state from management

---

## Coordination

- **Behavior Tree Agent**: Unblocked on pre-snap phase
- **Frontend Agent**: Notified of WebSocket field status
- **QA Agent**: All bug fixes verified
- **Researcher Agent**: Cognitive framing implemented

### Inbox/Outbox
- Check `agentmail/live_sim_agent/to/` for incoming messages
- Send to `agentmail/{agent}/to/` for outgoing
