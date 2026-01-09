# Game Manager Layer - Implementation Plan

## Overview

Build the **Game Manager** layer that bridges Management (League, Teams, Rosters) with V2 Simulation (Orchestrator) to enable complete football games.

**Goal:** Transform v2 from a "play sandbox" into a "game engine" that produces meaningful outcomes for the career sim.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MANAGEMENT LAYER                          │
│  League → Teams → Rosters → Depth Charts → Playbooks        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GAME MANAGER (NEW)                        │
│  GameManager → DriveManager → CoordinatorAI → RosterBridge  │
│  SpecialTeamsResolver → PlayAdapter → ResultHandler          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    V2 SIMULATION                             │
│  Orchestrator.setup_play() → run() → PlayResult             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
huddle/game/                    # NEW DIRECTORY
├── __init__.py
├── manager.py                  # GameManager - main orchestrator
├── state.py                    # GameState, GameClock, DownState, etc.
├── drive.py                    # DriveManager - drive loop
├── coordinator.py              # CoordinatorAI - play calling
├── roster_bridge.py            # Depth chart → simulation players
├── play_adapter.py             # Playbook plays → V2 PlayConfig
├── special_teams.py            # Kickoff, punt, FG, PAT (statistical)
├── result_handler.py           # Results → stats, injuries, approval
└── integration.py              # Connect back to management layer
```

---

## Design Decisions

1. **Priority:** Coach mode first - user calls plays, game pauses for decisions
2. **Special teams:** Hybrid - V2 physics for 2-point conversions, statistical for kicks
3. **Penalties:** Deferred - not in MVP, add as separate system later

---

## Implementation Phases

### Phase 1: Core Game Loop (MVP)

**Goal:** Run a complete game from kickoff to final whistle.

#### 1.1 State Classes (`state.py`)
- [ ] `GameState` - teams, phase, clock, score, possession, down_state
- [ ] `GameClock` - quarter, time_remaining, play_clock
- [ ] `ScoreState` - home/away totals, by-quarter breakdown
- [ ] `PossessionState` - team_with_ball, timeouts, receiving_second_half
- [ ] `DownState` - down, yards_to_go, line_of_scrimmage
- [ ] `PlayType` enum - NORMAL, KICKOFF, PUNT, FG_ATTEMPT, PAT, TWO_PT

**Note:** Reuse existing models from `huddle/core/models/game.py` where possible.

#### 1.2 Roster Bridge (`roster_bridge.py`)
- [ ] `get_offensive_11()` - Map depth chart slots to v2 Player objects
- [ ] `get_defensive_11()` - Map defense depth chart to v2 Players
- [ ] `convert_player()` - core.models.Player → v2.core.entities.Player
- [ ] Position mapping (management Position enum → v2 Position enum)
- [ ] Attribute mapping (PlayerAttributes → v2 PlayerAttributes)

#### 1.3 Play Adapter (`play_adapter.py`)
- [ ] `build_pass_config()` - Playbook pass play → PlayConfig with routes
- [ ] `build_run_config()` - Playbook run play → PlayConfig with run_concept
- [ ] Map play codes to V2 CONCEPT_LIBRARY concepts
- [ ] Determine dropback type from play timing

#### 1.4 Special Teams (`special_teams.py`)
- [ ] `resolve_kickoff()` → starting field position (statistical)
- [ ] `resolve_punt()` → field position change (statistical)
- [ ] `resolve_field_goal()` → made/missed (probability by distance + kicker rating)
- [ ] `resolve_pat()` → made/missed (94% base + kicker rating)
- [ ] `resolve_two_point()` → **V2 simulation** (full play execution from 2-yard line)

#### 1.5 Drive Manager (`drive.py`)
- [ ] `run_drive()` - Execute plays until scoring/turnover/punt
- [ ] `update_down_distance()` - After each play
- [ ] `check_drive_end()` - TD, turnover, punt, FG, turnover on downs
- [ ] `check_first_down()` - Reset downs on first down

#### 1.6 Game Manager (`manager.py`)
- [ ] `run_game()` - Complete game orchestration
- [ ] `_coin_toss()` - Determine receiving team
- [ ] `_handle_kickoff()` - Invoke special teams, set possession
- [ ] `_run_play()` - Invoke V2 orchestrator
- [ ] `_handle_scoring()` - PAT/2PT decision, update score
- [ ] `_check_quarter_end()` - Quarter transitions
- [ ] `_handle_halftime()` - Switch possession
- [ ] `_compile_result()` → GameResult

---

### Phase 1b: Coach Mode Interface (Priority)

**Goal:** User calls plays, game pauses for decisions.

- [ ] `get_situation()` - Return current game state for UI
- [ ] `get_play_options()` - Available plays filtered by playbook + situation
- [ ] `await_play_call()` - Pause game, wait for user selection
- [ ] `run_play(play_code)` - Execute user's chosen play
- [ ] `get_timeout_option()` - When user can call timeout
- [ ] `call_timeout()` - Stop clock

**UI Integration:**
- Game Manager exposes state for frontend to render
- Frontend sends play selection back
- Game advances one play at a time
- Between plays: user sees situation + play menu

---

### Phase 2: Play Calling AI

**Goal:** Intelligent situational play selection (for opponent + auto-sim).

#### 2.1 Coordinator AI (`coordinator.py`)
- [ ] `PlayCallContext` - down, distance, yard_line, time, score
- [ ] `call_offensive_play()` - Select from playbook by situation
- [ ] `call_defensive_play()` - Select coverage/scheme
- [ ] `fourth_down_decision()` - punt vs FG vs go for it
- [ ] `two_point_decision()` - PAT vs 2PT
- [ ] Run/pass balance based on TeamTendencies
- [ ] Situational adjustments (red zone, 2-minute, etc.)

---

### Phase 3: Result Integration

**Goal:** Feed game results back to management layer.

#### 3.1 Result Handler (`result_handler.py`)
- [ ] `process_play_result()` - Update game state from V2 PlayResult
- [ ] `record_stats()` - Passing, rushing, receiving, defense stats
- [ ] `check_injury()` - Roll for injuries based on play intensity
- [ ] `update_approval()` - Player morale from performance

#### 3.2 Management Integration (`integration.py`)
- [ ] `integrate_game_result()` - Post-game processing
- [ ] Update standings via `league.update_standings_from_game()`
- [ ] Record GameLog via `league.add_game_log()`
- [ ] Process injuries → player.injury_history
- [ ] Update player approval/morale
- [ ] Advance calendar to next event

---

## Key Files to Reference

| File | Purpose |
|------|---------|
| `huddle/simulation/v2/orchestrator.py` | V2 interface - setup_play(), run() |
| `huddle/core/models/game.py` | Existing GameState, GameClock, etc. |
| `huddle/simulation/engine.py` | Old engine patterns to learn from |
| `huddle/core/models/team.py` | Team, Roster, DepthChart |
| `huddle/core/models/player.py` | Player attributes |
| `huddle/simulation/v2/plays/concepts.py` | CONCEPT_LIBRARY |
| `huddle/simulation/v2/plays/run_concepts.py` | Run concept definitions |
| `huddle/core/playbook/play_codes.py` | PlayCode definitions |
| `huddle/management/league.py` | LeagueState integration point |

---

## Statistical Models (Special Teams)

```python
# Kickoff
TOUCHBACK_RATE = 0.65  # Modern NFL average
RETURN_AVG = 23        # When not touchback

# Field Goal by distance
FG_RATES = {
    (0, 30): 0.97,
    (30, 40): 0.89,
    (40, 50): 0.80,
    (50, 55): 0.65,
    (55, 60): 0.45,
}

# Extra point / 2-point
PAT_RATE = 0.94
TWO_PT_RATE = 0.48
```

---

## Success Criteria

A complete game produces:
- Final score (home and away)
- Quarter-by-quarter breakdown
- Drive summaries (plays, yards, result)
- Player stats (passing, rushing, receiving, defense)
- Injury events (if any)
- Integration with standings and season stats
