# Management Agent - Status

**Last Updated:** 2025-12-18 (Post-Game Morale Events Update)
**Agent Role:** Management systems - contracts, scouting, staff, practice, approval ratings, personality, mental state

---

## Domain Overview

The management layer sits between the core simulation and the player-facing UI. It handles all "front office" and "coaching" decisions that don't involve real-time gameplay.

**Key Reference:** `NFLHEADCOACH09DETAILS.md` - The systems we're implementing are heavily inspired by NFL Head Coach 09.

---

## COMPLETE

| System | Location | HC09 Alignment | Notes |
|--------|----------|----------------|-------|
| **Player Model** | `core/models/player.py` | ✅ | Attributes, contracts, physical, draft info, personality, approval, mental state helpers |
| **Team Model** | `core/models/team.py` | ✅ | Roster, depth chart, financials |
| **Contract Negotiation** | `core/contracts/negotiation.py` | ✅ | Full loop with counters, walk-away, tones, personality integration |
| **Market Value** | `core/contracts/market_value.py` | ✅ | Position multipliers, age curves |
| **Scouting Stages** | `core/scouting/stages.py` | ✅ | 5-stage fog of war (UNKNOWN→COMPLETE) |
| **Scout Staff** | `core/scouting/staff.py` | ✅ | Specialties, skill levels, accuracy |
| **Scouting Reports** | `core/scouting/report.py` | ✅ | Letter grades, confidence, scheme fit |
| **Team Tendencies** | `core/models/tendencies.py` | ✅ | AI DNA: draft, trade, negotiation, cap style |
| **Philosophy Eval** | `core/philosophy/evaluation.py` | ✅ | Team-specific OVR based on scheme |
| **NFL Data** | `core/league/nfl_data.py` | ✅ | 32 teams, divisions, conferences |
| **Calendar** | `management/calendar.py` | ✅ | Season phases, time speeds, NFL weeks |
| **Events** | `management/events.py` | ✅ | Event queue, lifecycle, priorities |
| **Generators** | `management/generators.py` | ✅ | Auto-spawn practice, game, FA, trade events |
| **League State** | `management/league.py` | ✅ | Central controller with practice effects, approval tracking |
| **Personality Archetypes** | `core/personality/` | ✅ | 12 archetypes, 23 traits, position-based generation |
| **Play Knowledge** | `core/playbook/` | ✅ | Mastery tiers (UNLEARNED→LEARNING→LEARNED→MASTERED) |
| **Player Development** | `core/development.py` | ✅ | Attribute growth through practice |
| **Game Prep** | `core/game_prep.py` | ✅ | Temporary opponent bonuses |
| **Approval System** | `core/approval.py` | ✅ | Player morale, performance modifiers, trade/holdout risk |
| **Inner Weather** | `core/mental_state.py` | ✅ | Mental state model for simulation handoff |
| **Scout Cognitive Biases** | `core/scouting/staff.py` | ✅ | Recency, measurables, confirmation, conference biases |
| **Post-Game Morale** | `core/approval.py` | ✅ | Game performance events, team aftermath, personality modifiers |

---

## Recently Completed (2025-12-17 to 2025-12-18)

### Play Knowledge System
Playbook learning with HC09-style mastery progression:
- **Files:** `core/playbook/learning.py`, `core/playbook/mastery.py`
- **Mastery Tiers:** UNLEARNED → LEARNING → LEARNED → MASTERED
- **Decay:** Plays can regress if not practiced
- **Tests:** Full test coverage

### Player Development System
Attribute growth through practice:
- **File:** `core/development.py`
- **Features:** Ceiling-bounded growth, age-based rates, position-specific focus
- **Integration:** Practice events trigger development
- **Tests:** Full test coverage

### Game Prep System
Temporary opponent-specific bonuses:
- **File:** `core/game_prep.py`
- **Features:** Prep level (0-1), bonus modifiers, weekly decay
- **Integration:** Feeds into simulation via game state
- **Tests:** Full test coverage

### Approval System
HC09-style player morale:
- **File:** `core/approval.py`
- **Features:**
  - 0-100 approval scale
  - Performance modifiers (+5% motivated, -8% disgruntled)
  - Trade request risk (<40), holdout risk (<25)
  - Depth chart tracking (promotions boost, demotions hurt)
  - Weekly drift toward baseline
  - Personality-modified impacts
- **Integration:** `Player.approval`, depth chart hooks in `league.py`
- **Tests:** 55 tests, all passing

### Inner Weather Mental State Model
Unified three-layer mental state for simulation:
- **File:** `core/mental_state.py`
- **Layers:**
  - STABLE: Personality traits → volatility, pressure response, recovery rate
  - WEEKLY: Morale + prep → starting confidence, bounds, resilience
  - IN-GAME: (Owned by simulation)
- **Structures:**
  - `WeeklyMentalState` - Between-game snapshot
  - `PlayerGameState` - Complete simulation handoff
- **Integration:** `Player.prepare_for_game()`, `Player.get_weekly_mental_state()`
- **Tests:** 59 tests, all passing
- **Handoff Doc:** `agentmail/live_sim_agent/to/001_inner_weather_handoff.md`

### Scout Cognitive Biases
Scouts as "characters, not just information sources":
- **File:** `core/scouting/staff.py`
- **Bias Types:**
  - Recency bias: Overweighting recent performances
  - Measurables bias: Dazzled by combine numbers
  - Confirmation bias: Sticky first impressions
  - Conference bias: Over/undervaluing schools
  - Position weakness: Blindspots on certain positions
- **Structures:**
  - `ScoutBiases` - Bias profile for each scout
  - `ScoutTrackRecord` - Historical accuracy tracking
- **Methods:**
  - `apply_biases_to_projection()` - Apply biases to raw projection
  - `get_bias_summary()` - Human-readable bias description
- **Tests:** 46 tests, all passing
- **Response Doc:** `agentmail/researcher_agent/to/003_scout_biases_implemented.md`

### Post-Game Morale Events
Game performance → approval changes with personality modifiers:
- **File:** `core/approval.py` (extended)
- **Individual Performance Events:**
  - `BIG_PLAY_HERO` (+12), `TD_CELEBRATION` (+7), `GAME_WINNING_DRIVE` (+20)
  - `COSTLY_TURNOVER` (-15), `CRITICAL_DROP` (-8), `BLOWN_ASSIGNMENT` (-7)
- **Team-Wide Events:**
  - `BIG_WIN` (+7), `BLOWOUT_WIN` (+10), `DIVISION_CLINCH` (+10)
  - `TOUGH_LOSS` (-7), `BLOWOUT_LOSS` (-12), `PLAYOFF_ELIMINATION` (-15)
- **Personality Modifiers:**
  - DRAMATIC trait: 1.5x amplification
  - LEVEL_HEADED trait: 0.6x dampening
  - COMPETITIVE trait: 1.2x for losses, 1.1x for wins
- **Helper Functions:**
  - `determine_game_aftermath_event()` - Score → event mapping
  - `apply_post_game_morale()` - Main entry point
  - `get_individual_performance_events()` - Stats → events
- **Tests:** 84 total approval tests, all passing
- **Response Doc:** `agentmail/researcher_agent/to/004_post_game_morale_implemented.md`

---

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_approval.py` | 84 | ✅ Passing |
| `tests/test_mental_state.py` | 59 | ✅ Passing |
| `tests/test_scout_biases.py` | 46 | ✅ Passing |
| Other core tests | ~50 | ✅ Passing |

**Total:** 190+ management-related tests passing

---

## NOT BUILT (HC09 Features Still Needed)

| System | Priority | HC09 Reference | Notes |
|--------|----------|----------------|-------|
| **Objectives System** | HIGH | Events Catalog | 27 persistent goals framing player experience |
| **Team Chemistry** | MEDIUM | Part 4 | Locker room leaders, chemistry effects |
| **Fatigue System** | MEDIUM | Part 4 | Accumulated fatigue across games |
| **Injury System** | MEDIUM | Part 4 | Wear & tear, body-part HP |
| **Scout Bias Integration** | LOW | Custom | Wire biases into actual projection generation |
| **Coach Skill Trees** | LOW | Part 1 | Basic skills + 44 Special skills |
| **Staff Control Mechanic** | LOW | Part 5 | Trade authority for better coordinators |
| **Dev Traits** | LOW | Part 6 | Hidden Normal/Star/Superstar growth rates |

---

## Pending Research Notes

From Researcher Agent (`agentmail/management_agent/to/`):

| Memo | Topic | Status |
|------|-------|--------|
| 001_morale_confidence_pipeline.md | Morale → Confidence flow | ✅ Implemented via Inner Weather |
| 002_scout_cognitive_biases.md | Scout personality biases | ✅ Implemented |
| 003_inner_weather_core_ownership.md | Mental state ownership | ✅ Implemented |
| 005_objectives_catalog.md | 27 persistent objectives | Reference document |
| 006_events_catalog.md | 60+ interruption events | Reference document |
| 007_unblocking_next_steps.md | Post-game morale roadmap | ✅ Implemented |

All actionable researcher proposals implemented. Catalogs (005, 006) are reference documents for future work.

---

## Coordination

| Agent | Relationship | Status |
|-------|-------------|--------|
| `live_sim_agent` | Consumer | Receives `PlayerGameState` handoff via Inner Weather |
| `behavior_tree_agent` | Consumer | Uses mental state for decision-making |
| `researcher_agent` | Collaborator | Provided Inner Weather design |
| `frontend_agent` | Consumer | Management UI panels consume our data models |

**Outgoing Memos:**
- `agentmail/live_sim_agent/to/001_inner_weather_handoff.md` - Simulation integration guide
- `agentmail/researcher_agent/to/002_inner_weather_implemented.md` - Inner Weather confirmation
- `agentmail/researcher_agent/to/003_scout_biases_implemented.md` - Scout biases confirmation
- `agentmail/researcher_agent/to/004_post_game_morale_implemented.md` - Post-game morale confirmation

---

## Key Files in Domain

```
huddle/
├── core/
│   ├── models/player.py        # Player with approval, mental state helpers
│   ├── models/team.py          # Team, Roster, DepthChart
│   ├── approval.py             # PlayerApproval, events, impacts
│   ├── mental_state.py         # WeeklyMentalState, PlayerGameState
│   ├── development.py          # Attribute growth
│   ├── game_prep.py            # Opponent preparation
│   ├── contracts/              # Negotiation, market value, FA
│   ├── scouting/               # Fog of war, scouts, reports
│   ├── playbook/               # Play knowledge, mastery tiers
│   └── personality/            # Archetypes, traits, generation
├── management/
│   ├── league.py               # LeagueState (central controller)
│   ├── calendar.py             # Time progression
│   ├── events.py               # Event system
│   └── generators.py           # Event spawning
└── tests/
    ├── test_approval.py        # 55 approval tests
    └── test_mental_state.py    # 59 mental state tests
```

---

## Next Steps (Awaiting Direction)

1. **Objectives System** - Track active team objectives (per Catalog 005)
2. **Team Chemistry** - Locker room dynamics, leader effects (per Catalog 006 Section E)
3. **Fatigue System** - Multi-game fatigue accumulation
4. **Scout Bias Integration** - Wire biases into projection.py generation

---

## Notes

- Inner Weather creates a clean separation: Management owns stable/weekly layers, Simulation owns in-game layer
- Approval system fully integrates with personality - sensitive players react more, level-headed less
- All new systems have serialization (to_dict/from_dict) for persistence
- Player model now has comprehensive helper methods for mental state queries
- Scouts are "characters, not information sources" - biases create emergent narratives ("My SEC scout loved him but my analytics guy said workout warrior")
- Track records let players learn which scouts to trust for which positions over time
