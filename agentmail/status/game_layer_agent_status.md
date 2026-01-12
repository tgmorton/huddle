# Game Layer Agent - Status

**Last Updated:** 2026-01-11
**Agent Role:** Game Manager layer - bridges Management with V2 Simulation

---

## Domain Overview

I own the **Game Manager layer** (`huddle/game/`) that transforms v2 simulation from a "play sandbox" into a "game engine" producing meaningful outcomes for the career sim.

**Core Responsibilities:**
- Game flow orchestration (quarters, drives, possessions, scoring)
- Coach mode interface (user calls plays)
- Roster-to-simulation bridge (depth chart -> v2 players)
- Play adapter (playbook -> V2 PlayConfig)
- Special teams resolution (kickoff, punt, FG, PAT)
- Result integration (stats, injuries, approval back to management)

---

## CURRENT STATUS: PHASE 3 COMPLETE + POSITION PLANNER INTEGRATION

### Latest Session (2026-01-11 evening)

| Task | Status | Notes |
|------|--------|-------|
| Position planner FA wiring | DONE | `should_pursue_fa()` now filters FA interest |
| Position planner FA update | DONE | `update_plan_after_fa()` called after signings |
| Position planner draft wiring | DONE | `get_draft_target()` guides pick selection |
| Position planner draft update | DONE | `update_plan_after_draft()` new function added |
| Commitment-aware trade-up | DONE | DraftAI threshold lowered for DRAFT_EARLY positions |
| Commitment-aware trade-down | DONE | DraftAI prevents trade-down when plan target available |
| Team narrative script | WIP | Building detailed offseason analysis tool |

### Position Planner Integration (Cross-Domain Work)

Wired the HC09-style position planning system into historical simulation. Functions existed but were **never called**.

**Changes to `huddle/core/simulation/historical_sim.py`:**
- FA now calls `should_pursue_fa()` - returns `(pursue: bool, aggression: float)`
- FA now calls `update_plan_after_fa()` after each signing
- Draft now calls `get_draft_target()` for plan-guided selection
- Draft now calls `update_plan_after_draft()` after each pick

**Changes to `huddle/core/ai/draft_ai.py`:**
- `should_trade_up(position_plan)` - lowers threshold 80→70-75 for DRAFT_EARLY
- `should_trade_down(position_plan)` - prevents trading down when plan target available

**New in `huddle/core/ai/position_planner.py`:**
- Added `update_plan_after_draft()` function

### Earlier Session (2026-01-11)

| Task | Status | Notes |
|------|--------|-------|
| Penalty integration | DONE | Wired `check_for_penalty()` into drive loop |
| Timeout tracking | DONE | Added to GameManager with halftime reset |
| Safety bug fix | DONE | Fixed infinite loop when team pinned at 1-yard line |
| Kickoff order fix | DONE | Fixed possession flip happening before kickoff |
| Missed FG fix | DONE | No longer triggers kickoff, ball at spot |
| V2 sim testing | WORKING | Games complete end-to-end (41-24, 52-24) |
| Architecture recs | IMPLEMENTED | Context hierarchy, state machine, type safety |
| Simulation analysis | SENT | Run game variance, phase bug (msg 075) |
| Frontend integration | SENT | GameView guide to frontend_agent (msg 050) |
| GameView evaluation | DONE | Reviewed frontend - 70% complete, needs UUID flow |

### Bugs Fixed This Session

**1. Safety detection infinite loop** - When a team was at their own 1-yard line and lost yards, the drive would loop forever because:
- `is_safety` was True (LOS + yards <= 0)
- But `_current_los` was clamped to 1
- So `_is_drive_over()` never detected the safety

**Fix:** Added `safety` field to `PlayLog` and check `last_play.safety` instead of `self._current_los <= 0`.

**2. Kickoff order bug** - Possession was flipping BEFORE `_handle_kickoff()`, causing wrong team to kick after TD/FG/Safety.

**Fix:** Reordered to call kickoff first, then flip possession.

**3. Missed FG bug** - Was incorrectly grouped with kickoff scenarios.

**Fix:** Ball now goes to other team at spot of kick (or 20-yard line, whichever is farther).

---

## Phase 1-3 Complete

| Module | Status | Description |
|--------|--------|-------------|
| `__init__.py` | Done | Package exports all main classes |
| `roster_bridge.py` | Done | Depth chart -> v2 Player conversion |
| `play_adapter.py` | Done | PlayCode -> V2 PlayConfig mapping |
| `special_teams.py` | Done | Statistical kick resolution (NFL data) |
| `drive.py` | Done | Drive loop with penalties, safety detection |
| `manager.py` | Done | Full game orchestration + timeouts |
| `result_handler.py` | Done | Extract stats from V2 PlayResult |
| `coordinator.py` | Done | AI play-calling for auto-play mode |
| `decision_logic.py` | Done | 4th down, 2PT, clock, timeout decisions |
| `game_log_converter.py` | Done | Bridge to core stats model |
| `penalties.py` | Done | Flag resolution system |

---

## KEY EXPORTS FROM `huddle.game`

```python
from huddle.game import (
    # Game management
    GameManager, GameResult, DriveManager, DriveResult,

    # Player bridging
    RosterBridge, get_offensive_11, get_defensive_11,

    # Play setup
    PlayAdapter, build_play_config,

    # Special teams
    SpecialTeamsResolver,

    # Stats
    ResultHandler, GameStatSheet, PlayerGameStats, TeamGameStats,

    # AI coordinators
    OffensiveCoordinator, DefensiveCoordinator, SituationContext,

    # Decision logic
    fourth_down_decision, FourthDownDecision,
    should_go_for_two,
    select_pace, Pace, time_off_clock,
    should_call_timeout,

    # Persistence
    persist_game_result, persist_game_to_session,
    convert_stat_sheet_to_game_log,

    # Penalties
    PenaltyResolver, check_for_penalty, PenaltyType, PenaltyResult,
)
```

---

## COACH MODE API

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/coach/start` | POST | Start new game |
| `/api/v1/coach/{game_id}/situation` | GET | Current situation |
| `/api/v1/coach/{game_id}/plays` | GET | Available plays |
| `/api/v1/coach/{game_id}/play` | POST | Execute play |
| `/api/v1/coach/{game_id}/special` | POST | Special teams |
| `/api/v1/coach/{game_id}/simulate-defense` | POST | AI defense |

### WebSocket Endpoint

| Endpoint | Description |
|----------|-------------|
| `WS /api/v1/coach/{game_id}/stream` | Real-time streaming |

---

## COORDINATION

| Agent | Status | Topic |
|-------|--------|-------|
| `live_sim_agent` | ACTIVE | V2 simulation context bugs (073), architecture recs (074) |
| `frontend_agent` | Waiting | Coach mode UI task |
| `management_agent` | RESOLVED | Game history integration complete |

### Active Thread: v2_simulation_yardage_tuning

| Message | Direction | Summary |
|---------|-----------|---------|
| 070 | → live_sim | Bug: High negative yardage rate |
| 071 | ← live_sim | Investigation: QB not throwing |
| 006 | ← live_sim | Fix: Brain registration added |
| 072 | → live_sim | Two issues: repositioning + RBContext |
| 007 | ← live_sim | Fix: RBContext.route_target |
| 073 | → live_sim | Bug: WRContext.run_aiming_point |
| 074 | → live_sim | Architecture recommendations |

---

## KNOWN ISSUES

### V2 Simulation Context Bugs (BLOCKING - reported to live_sim_agent)

Multiple context attribute errors when players change roles mid-play:
1. ✓ `RBContext.route_target` - Fixed by live_sim_agent
2. ✗ `WRContext.run_aiming_point` - Awaiting fix (message 073)
3. ? More likely hiding in other brain/context combinations

**Root cause:** Brains assume specific context types but receive different ones when players transition roles (e.g., WR catches ball → becomes ballcarrier).

**Architectural recommendation sent** (message 074) proposing context hierarchy with composition.

---

## NEXT PHASE IDEAS (When Requested)

1. **Integrate timeout calling into auto-play** - Use `check_auto_timeout()` during drives
2. **Injuries during plays** - Injury chance based on play type
3. **Weather effects** - Wind/rain affecting kicks and passes
4. **Home field advantage** - Crowd noise affecting snap counts
5. **Challenge flags** - Coach can challenge certain plays

---

## DESIGN DECISIONS

1. **Statistical special teams** - Not simulating kicks with physics
2. **Research-backed probabilities** - All decisions use NFL 2019-2024 data
3. **WebSocket for streaming** - FastAPI WebSocket with connection manager
4. **Penalty rate ~6%** - Matches NFL average
5. **Management integration** - Via `league.add_game_log()`
6. **Safety via PlayLog** - Track safety flag on play, not field position

---

## FILES I OWN

```
huddle/game/
├── __init__.py
├── roster_bridge.py
├── play_adapter.py
├── special_teams.py
├── drive.py
├── manager.py
├── result_handler.py
├── coordinator.py
├── decision_logic.py
├── game_log_converter.py
└── penalties.py

huddle/api/routers/
└── coach_mode.py
```
