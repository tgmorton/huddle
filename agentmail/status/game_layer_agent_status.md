# Game Layer Agent - Status

**Last Updated:** 2025-12-31
**Agent Role:** Game Manager layer - bridges Management with V2 Simulation

---

## Domain Overview

I own the **Game Manager layer** (`huddle/game/`) that transforms v2 simulation from a "play sandbox" into a "game engine" producing meaningful outcomes for the career sim.

**Core Responsibilities:**
- Game flow orchestration (quarters, drives, possessions, scoring)
- Coach mode interface (user calls plays)
- Roster-to-simulation bridge (depth chart → v2 players)
- Play adapter (playbook → V2 PlayConfig)
- Special teams resolution (kickoff, punt, FG, PAT)
- Result integration (stats, injuries, approval back to management)

---

## CURRENT STATUS: PHASE 2 COMPLETE

### Phase 1 MVP Implementation Complete

| Module | Status | Description |
|--------|--------|-------------|
| `__init__.py` | Done | Package exports all main classes |
| `roster_bridge.py` | Done | Depth chart → v2 Player conversion |
| `play_adapter.py` | Done | PlayCode → V2 PlayConfig mapping |
| `special_teams.py` | Done | Statistical kick resolution |
| `drive.py` | Done | Drive loop with down/distance tracking |
| `manager.py` | Done | Full game orchestration + coach mode |

### Phase 2 Implementation Complete

| Module | Status | Description |
|--------|--------|-------------|
| `result_handler.py` | Done | Extract stats from V2 PlayResult |
| `coordinator.py` | Done | AI play-calling for auto-play mode |
| `api/schemas/coach_mode.py` | Done | Pydantic schemas for API |
| `api/routers/coach_mode.py` | Done | REST endpoints for coach mode |
| `tests/test_game_integration.py` | Done | 14 tests, all passing |

---

## FILES CREATED

```
huddle/game/
├── __init__.py         # Package exports
├── roster_bridge.py    # RosterBridge, get_offensive_11, get_defensive_11
├── play_adapter.py     # PlayAdapter, build_play_config
├── special_teams.py    # SpecialTeamsResolver
├── drive.py            # DriveManager, DriveResult
├── manager.py          # GameManager, GameResult
├── result_handler.py   # ResultHandler, GameStatSheet, stat classes
└── coordinator.py      # OffensiveCoordinator, DefensiveCoordinator

huddle/api/schemas/
└── coach_mode.py       # Request/Response schemas for coach mode

huddle/api/routers/
└── coach_mode.py       # REST endpoints for coach mode

tests/
└── test_game_integration.py  # Integration tests (14 passing)
```

---

## COACH MODE API ENDPOINTS

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/coach/start` | POST | Start new game with home/away teams |
| `/api/v1/coach/{game_id}/situation` | GET | Get current game situation |
| `/api/v1/coach/{game_id}/plays` | GET | Get available plays for situation |
| `/api/v1/coach/{game_id}/play` | POST | Execute a called play |
| `/api/v1/coach/{game_id}/special` | POST | Execute special teams play |
| `/api/v1/coach/{game_id}/simulate-defense` | POST | AI handles defensive possession |

---

## KEY FEATURES IMPLEMENTED

### RosterBridge
- Converts `core.models.Player` → `v2.core.entities.Player`
- Maps all player attributes to v2 attributes
- Positions players at formation alignments
- Supports `get_offensive_11()` and `get_defensive_11()`

### PlayAdapter
- Maps 30+ offensive plays from PlayCode system
- Route assignments for all receiver slots
- Dropback type selection (quick/standard/deep)
- Run concept mapping (zone, power, counter, etc.)
- Coverage assignments for defensive plays

### SpecialTeamsResolver
- Kickoffs: touchback rate, return yards, onside kicks
- Punts: net yards, fair catch, blocked punts
- Field Goals: distance-based probability with kicker rating
- PAT: 94% base rate with modifiers
- All outcomes return field position updates

### DriveManager
- Executes plays until drive ends (TD, turnover, punt, etc.)
- Tracks down/distance, first downs
- Coach mode interface: `get_situation()`, `get_available_plays()`
- Play-by-play logging

### GameManager
- Full game orchestration
- Coin toss and opening kickoff
- Quarter/half transitions
- Scoring sequences (TD → PAT/2PT, FG)
- Coach mode: `execute_play()`, `get_situation()`
- Returns complete `GameResult` with all drives

### ResultHandler (NEW)
- Extracts passing stats (att/cmp/yds/td/int)
- Extracts rushing stats (att/yds/td)
- Extracts receiving stats (rec/yds/td)
- Extracts defensive stats (tackles/sacks/ints)
- Aggregates into player and team stat sheets

### AI Coordinator (NEW)
- `OffensiveCoordinator`: Situational play-calling
- `DefensiveCoordinator`: Coverage selection
- Down/distance tendencies (run vs pass)
- Red zone adjustments
- End-of-half/game clock management

---

## TEST RESULTS

```
tests/test_game_integration.py - 14 tests PASSED (92.93s)

Test Classes:
- TestRosterBridge: 2 tests
- TestCoordinator: 3 tests
- TestGameManager: 5 tests
- TestSpecialTeams: 4 tests
```

---

## BUGS FIXED DURING IMPLEMENTATION

1. **`GamePhase.PRE_GAME` → `GamePhase.PREGAME`** - Enum naming mismatch
2. **`time_remaining` → `time_remaining_seconds`** - GameClock field name
3. **Added `Clock.dt` property** - V2 orchestrator needed this alias

---

## NEXT UP (PHASE 3 - WHEN REQUESTED)

1. **Frontend Integration** - React components for coach mode UI
2. **WebSocket Support** - Real-time play-by-play streaming
3. **Play Filtering** - Filter plays by situation (short yardage, red zone)
4. **Game History** - Persist game results to database
5. **Penalties System** - Flag resolution during plays

---

## COORDINATION

| Agent | Interaction |
|-------|-------------|
| `live_sim_agent` | V2 Orchestrator interface, play execution |
| `management_agent` | League/Team/Roster data, result integration |
| `frontend_agent` | Coach mode UI, game visualization |
| `behavior_tree_agent` | AI brain behaviors during plays |

---

## DESIGN DECISIONS MADE

1. **Reused core.models.game** - GameState, GameClock, ScoreState already existed
2. **Statistical special teams** - Not simulating kicks with physics
3. **Coach mode first** - Full UI interface before auto-play AI
4. **Penalties deferred** - Not in MVP
5. **REST API first** - WebSocket can be added later for streaming
