# Huddle Codebase Reference

> **For Future Agents**: This document provides a comprehensive map of the Huddle codebase. Use it to quickly understand what's built, where it lives, and how systems connect. Refer to `docs/DESIGN_PHILOSOPHY.md` for design principles and `NFLHEADCOACH09DETAILS.md` for HC09 feature reference.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React/TypeScript)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ Management   │  │   Zustand    │  │  useManagementWebSocket  │   │
│  │   Screen     │←─│    Store     │←─│        Hook              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑ WebSocket + REST
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  management  │  │  management  │  │   ManagementService +    │   │
│  │   router     │  │   websocket  │  │   SessionManager         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                    Management Layer (Game Loop)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ LeagueState  │  │  Calendar    │  │  EventQueue + Generator  │   │
│  │ (controller) │  │  (time)      │  │  (events)                │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                       Core Domain Models                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Player  │ │   Team   │ │ League   │ │ Contract │ │ Scouting │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Models

### Player
- **Location**: `huddle/core/models/player.py`
- **Purpose**: Represents an NFL player with attributes, contracts, physical info, and career tracking
- **Key Properties**:
  - `id`, `first_name`, `last_name`, `position` - Identity
  - `age`, `height_inches`, `weight_lbs` - Physical
  - `overall`, `attributes` - Skill ratings (0-99 scale)
  - `contract_years`, `salary`, `signing_bonus` - Contract
  - `experience_years`, `years_on_team` - Career
  - `projected_round` - Draft projection
- **Relationships**: Belongs to Team via Roster
- **HC09 Feature**: Maps to HC09 player model with wear & tear attributes (TODO: body-part HP)

### Team
- **Location**: `huddle/core/models/team.py`
- **Purpose**: NFL franchise with roster, depth chart, and financials
- **Key Classes**:
  - `Team` - The franchise entity
  - `Roster` - Collection of players with position limits
  - `DepthChart` - Starter/backup assignments per position
- **Key Properties**:
  - `id`, `name`, `abbreviation`, `city` - Identity
  - `roster: Roster` - All players
  - `depth_chart: DepthChart` - Position assignments
  - `financials: TeamFinancials` - Salary cap, dead money
  - `tendencies: TeamTendencies` - AI behavior DNA
- **Methods**:
  - `can_afford(salary)` - Check cap space
  - `cap_room` - Available cap space
  - `recalculate_financials()` - Update totals

### Tendencies (AI DNA)
- **Location**: `huddle/core/models/tendencies.py`
- **Purpose**: Defines AI team behavior for trades, drafts, negotiations
- **Key Enums**:
  - `DraftStrategy`: BEST_AVAILABLE, FILL_NEEDS, TRADE_HEAVY
  - `TradeAggression`: CONSERVATIVE, MODERATE, AGGRESSIVE
  - `NegotiationTone`: HARDBALL, FAIR, GENEROUS
  - `RosterPriority`: WIN_NOW, BALANCED, REBUILD
- **Key Class**: `TeamTendencies` - Combines all tendencies per team
- **HC09 Feature**: Implements HC09's "Tendencies" system that makes each AI team feel unique

### Attributes System
- **Location**: `huddle/core/attributes/base.py`, `registry.py`
- **Purpose**: Flexible attribute definition system for players
- **Key Classes**:
  - `AttributeDefinition` - Defines an attribute (name, category, min/max)
  - `AttributeRegistry` - Central registry of all attributes
- **Design**: Allows position-specific attributes with different weights

---

## Contract System

### Negotiation Loop
- **Location**: `huddle/core/contracts/negotiation.py`
- **Entry Point**: `start_negotiation(player, team, initial_offer)`
- **Purpose**: HC09-style back-and-forth contract negotiation
- **Flow**:
  1. Team makes initial offer
  2. Player evaluates vs market value
  3. Player counters or accepts
  4. Negotiation continues until deal or walk-away
- **Key Classes**:
  - `NegotiationState` - Tracks current offers, rounds
  - `NegotiationResult` - Final outcome (ACCEPTED, REJECTED, WALKED_AWAY)
- **HC09 Feature**: Direct implementation of HC09's negotiation mini-game

### Market Value Calculation
- **Location**: `huddle/core/contracts/market_value.py`
- **Entry Point**: `calculate_market_value(player)`
- **Purpose**: Determine fair contract value based on position, age, skill
- **Key Functions**:
  - `get_position_multiplier(position)` - QB highest, special teams lowest
  - `get_age_curve(age)` - Peak at 26-28, decline after 30
  - `calculate_market_value(player)` - Returns `MarketValue` with salary, years, bonus
- **HC09 Feature**: Based on HC09's market value system

### Free Agency
- **Location**: `huddle/core/contracts/free_agency.py`
- **Purpose**: Free agent market mechanics
- **Key Classes**:
  - `FreeAgentMarket` - Pool of available players
  - `FreeAgentOffer` - Team's offer to FA
- **Key Functions**:
  - `evaluate_offer()` - Player evaluates team offer
  - `sign_player()` - Complete signing
- **HC09 Feature**: Maps to HC09's real-time FA auction

### Extensions
- **Location**: `huddle/core/contracts/extensions.py`
- **Purpose**: In-season contract extension logic
- **Key Functions**:
  - `can_extend(player)` - Check eligibility
  - `calculate_extension_value()` - Determine offer

### AI Contract Decisions
- **Location**: `huddle/core/contracts/ai_decisions.py`
- **Purpose**: AI logic for contract decisions
- **Key Functions**:
  - `evaluate_player_value()` - AI's assessment
  - `make_counter_offer()` - AI negotiation logic

---

## Scouting System

### Scouting Stages
- **Location**: `huddle/core/scouting/stages.py`
- **Purpose**: Progressive information reveal (fog of war)
- **Enum** `ScoutingStage`:
  1. `UNKNOWN` - Only name/position visible
  2. `BASIC` - Height, weight, college
  3. `EVALUATED` - General strengths/weaknesses
  4. `DETAILED` - Most attributes visible
  5. `COMPLETE` - Full attribute visibility
- **Key Function**: `get_visible_attributes(stage)` - Returns which attributes are revealed
- **HC09 Feature**: Direct implementation of HC09's 5-stage scouting system

### Scout Staff
- **Location**: `huddle/core/scouting/staff.py`
- **Purpose**: Scout personnel with specialties and skill levels
- **Key Classes**:
  - `Scout` - Individual scout (specialty, skill_level, accuracy)
  - `ScoutSpecialty` - COLLEGE, NATIONAL, AREA, PRO
  - `ScoutingDepartment` - Team's scouting staff
- **Key Methods**:
  - `assign_scout(player)` - Assign scout to evaluate player
  - `get_scouting_efficiency()` - How fast scouts work

### Projections
- **Location**: `huddle/core/scouting/projections.py`
- **Purpose**: Draft projections with accuracy variance
- **Key Classes**:
  - `PlayerProjection` - Projected round, pick, career arc
- **Key Features**:
  - Projections can be wrong (accuracy based on scout skill)
  - Career projection (STAR, STARTER, BACKUP, BUST)

### Scouting Reports
- **Location**: `huddle/core/scouting/report.py`
- **Purpose**: Generated reports with grades and analysis
- **Key Classes**:
  - `ScoutingReport` - Full report for a player
  - `AttributeGrade` - Letter grade (A+ to F) per attribute
- **Key Features**:
  - Scheme fit analysis
  - Comparison to existing roster
  - Red flags (character, injury history)
- **HC09 Feature**: Based on HC09's detailed scouting report system

---

## Philosophy/Evaluation System

### Position Philosophies
- **Location**: `huddle/core/philosophy/positions.py`
- **Purpose**: Team-specific attribute weights per position
- **Key Classes**:
  - `QBPhilosophy` - QB evaluation weights (arm strength vs accuracy vs mobility)
  - `RBPhilosophy` - RB weights (power vs speed vs receiving)
  - Similar for all positions
- **HC09 Feature**: Implements HC09's "What type of X do you want?" system

### Evaluation
- **Location**: `huddle/core/philosophy/evaluation.py`
- **Purpose**: Calculate player OVR based on team's philosophy
- **Key Function**: `evaluate_player(player, philosophy)` - Returns philosophy-weighted OVR
- **Design**: Same player can have different OVR for different teams based on scheme fit
- **HC09 Feature**: HC09's core "fit" system where player value varies by team

---

## League Structure

### NFL Data
- **Location**: `huddle/core/league/nfl_data.py`
- **Purpose**: Static NFL structure data
- **Key Data**:
  - `NFL_TEAMS` - All 32 teams with metadata
  - `Division`, `Conference` enums
  - `DIVISIONS_BY_CONFERENCE` - Structural relationships
- **Key Functions**:
  - `get_teams_in_division(division)`
  - `get_teams_in_conference(conference)`

### League Container
- **Location**: `huddle/core/league/league.py`
- **Purpose**: Top-level container - the "save file"
- **Key Classes**:
  - `League` - Contains all 32 teams, standings, schedule
  - `TeamStanding` - Win/loss record, tiebreakers
  - `ScheduledGame` - Individual game on schedule
- **Key Properties**:
  - `teams: dict[str, Team]` - All teams by abbreviation
  - `standings: dict[str, TeamStanding]` - Current standings
  - `schedule: list[ScheduledGame]` - Season schedule
  - `free_agents: list[Player]` - FA pool
  - `draft_class: list[Player]` - Upcoming draft class
- **Key Methods**:
  - `sign_free_agent()` - Complete FA signing
  - `release_player()` - Cut with dead money
  - `start_new_season()` - Age players, process contracts
  - `save(path)` / `load(path)` - JSON serialization

---

## Management Layer (Game Loop)

### LeagueState
- **Location**: `huddle/management/league.py`
- **Purpose**: Central controller for franchise mode - coordinates all systems
- **Key Properties**:
  - `calendar: LeagueCalendar` - Time progression
  - `events: EventQueue` - Management events
  - `clipboard: ClipboardState` - UI navigation state
  - `ticker: TickerFeed` - News ticker
- **Key Methods**:
  - `tick(elapsed_seconds)` - Main game loop tick
  - `pause()` / `play(speed)` - Time controls
  - `attend_event(event_id)` - Navigate to event
  - `run_practice(event_id, allocation)` - Execute practice
  - `sim_game(event_id, league)` - Simulate game
- **Auto-Pause**: Automatically pauses for critical events (games, elite FAs)

### LeagueCalendar
- **Location**: `huddle/management/calendar.py`
- **Purpose**: Time progression with NFL season phases
- **Enum** `SeasonPhase`:
  - OFFSEASON_EARLY, FREE_AGENCY_LEGAL_TAMPERING, FREE_AGENCY
  - PRE_DRAFT, DRAFT, POST_DRAFT
  - OTA, MINICAMP, TRAINING_CAMP, PRESEASON
  - REGULAR_SEASON, WILD_CARD, DIVISIONAL, CONFERENCE_CHAMPIONSHIP, SUPER_BOWL
- **Enum** `TimeSpeed`:
  - PAUSED, SLOW (2 min/sec), NORMAL (30 min/sec), FAST (4 hr/sec), VERY_FAST (12 hr/sec), INSTANT
- **Key Methods**:
  - `tick(real_elapsed_seconds)` - Advance game time
  - `advance_to(target_date)` - Skip to date
  - `on_phase(phase, callback)` - Register phase callbacks
  - `on_daily(callback)` - Register daily callbacks

### ManagementEvent & EventQueue
- **Location**: `huddle/management/events.py`
- **Purpose**: Events that require player attention
- **Enum** `EventCategory`:
  - FREE_AGENCY, TRADE, CONTRACT, ROSTER
  - PRACTICE, MEETING, GAME
  - SCOUTING, DRAFT, STAFF, DEADLINE, SYSTEM
- **Enum** `EventPriority`:
  - CRITICAL (auto-pause), HIGH, NORMAL, LOW, BACKGROUND
- **Enum** `EventStatus`:
  - SCHEDULED, PENDING, IN_PROGRESS, ATTENDED, EXPIRED, DISMISSED, AUTO_RESOLVED
- **Key Factory Functions**:
  - `create_free_agent_event()` - FA available
  - `create_practice_event()` - Team practice
  - `create_game_event()` - Game day
  - `create_trade_offer_event()` - Incoming trade
  - `create_negotiation_event()` - Contract negotiation
- **EventQueue Methods**:
  - `add(event)` / `remove(event_id)`
  - `update(current_time)` - Activate/expire events
  - `get_pending()` / `get_urgent()`

### EventGenerator
- **Location**: `huddle/management/generators.py`
- **Purpose**: Automatically spawn events based on calendar
- **Key Callbacks**:
  - `_on_new_day()` - Generate practices, check FAs, maybe trade offers
  - `_on_new_week()` - Generate game events, scouting events
  - `_on_free_agency_start()` - Generate FA events
  - `_on_draft_start()` - Generate draft event
- **Configuration**: `EventGeneratorConfig` controls practice days, FA intervals, etc.

---

## API Layer

### Management Router (REST)
- **Location**: `huddle/api/routers/management.py`
- **Base Path**: `/management`
- **Key Endpoints**:
  - `POST /franchise` - Create new franchise session
  - `GET /franchise/{id}` - Get full state
  - `POST /franchise/{id}/pause` - Pause time
  - `POST /franchise/{id}/play` - Resume time
  - `POST /franchise/{id}/speed` - Set speed
  - `GET /franchise/{id}/events` - Get pending events
  - `POST /franchise/{id}/events/attend` - Attend event
  - `GET /franchise/{id}/clipboard` - Get clipboard state
  - `GET /franchise/{id}/ticker` - Get news ticker

### Management WebSocket
- **Location**: `huddle/api/routers/management_websocket.py`
- **Endpoint**: `ws://localhost:8000/ws/management/{franchise_id}`
- **Purpose**: Real-time bidirectional updates
- **Server → Client Messages**:
  - `state_sync` - Full state on connect
  - `calendar_update` - Time progression
  - `event_added` - New event spawned
  - `event_updated` - Event status changed
  - `clipboard_update` - Navigation changed
  - `auto_paused` - Game auto-paused
- **Client → Server Messages**:
  - `pause`, `play`, `set_speed` - Time control
  - `select_tab`, `go_back` - Navigation
  - `attend_event`, `dismiss_event` - Event actions
  - `run_practice`, `sim_game`, `play_game` - Game actions

### ManagementService
- **Location**: `huddle/api/services/management_service.py`
- **Purpose**: Business logic layer between API and management state
- **Key Class**: `ManagementService`
  - Wraps `LeagueState`
  - Runs async tick loop
  - Sends WebSocket updates
- **Key Class**: `ManagementSessionManager`
  - Manages active franchise sessions
  - Handles WebSocket attachment/detachment

---

## Frontend

### State Management
- **Location**: `frontend/src/stores/managementStore.ts`
- **Technology**: Zustand
- **Key State**:
  - `franchiseId`, `state` - Session
  - `calendar`, `events`, `clipboard`, `ticker` - Derived
  - `showAutoPauseModal` - UI state
- **Key Actions**:
  - `setFullState(state)` - Set complete state
  - `updateCalendar(calendar)` - Update time display
  - `addEvent(event)` - Add new event
- **Selectors**: `selectIsPaused`, `selectPendingEvents`, `selectActiveTab`, etc.

### WebSocket Hook
- **Location**: `frontend/src/hooks/useManagementWebSocket.ts`
- **Purpose**: WebSocket connection with message handling
- **Returns**:
  - `connect()`, `disconnect()` - Connection control
  - `pause()`, `play(speed)`, `setSpeed(speed)` - Time control
  - `selectTab(tab)`, `goBack()` - Navigation
  - `attendEvent(id)`, `dismissEvent(id)` - Event actions
  - `runPractice(id, allocation)`, `simGame(id)` - Game actions

### UI Components
- **Location**: `frontend/src/components/Management/`
- **Key Components**:
  - `ManagementScreen.tsx` - Main container
  - `TopBar.tsx` - Time display, speed controls
  - `Clipboard.tsx` - Tab navigation, event list
  - `ActivePanel.tsx` - Current panel content
  - `PracticePanel.tsx` - Practice allocation UI
  - `GameDayPanel.tsx` - Game day UI
  - `Ticker.tsx` - News ticker
  - `AutoPauseModal.tsx` - Auto-pause notification
  - `RosterPanel.tsx`, `DepthChartPanel.tsx`, `SchedulePanel.tsx` - Additional panels

---

## What's Implemented vs Placeholder

### Fully Working
- [x] Core data models (Player, Team, League)
- [x] Contract negotiation loop with HC09-style back-and-forth
- [x] Market value calculation with position multipliers and age curves
- [x] Scouting stages (5-level fog of war)
- [x] Scout staff system with specialties
- [x] Philosophy-based player evaluation
- [x] All 32 NFL teams and schedule structure
- [x] Management game loop with real-time tick
- [x] Calendar with all season phases
- [x] Event system with auto-pause
- [x] Event generators (practice, game, FA, trade)
- [x] REST API + WebSocket for frontend
- [x] React frontend with real-time updates

### Stubs/Placeholders (TODO)
- [ ] `_apply_practice_effects()` in `management/league.py:374` - Does nothing, needs playbook/development/game-prep effects
- [ ] Personality archetypes (HC09 has 17 types that drive all interactions)
- [ ] Coach skill trees (HC09: Basic + 44 Special skills)
- [ ] Staff control mechanic (cede authority for talent)
- [ ] Wear & tear injury system (body-part HP from HC09)
- [ ] Play knowledge/decay (Unlearned → Learned → Mastered)
- [ ] Approval rating (5-faction reputation system)
- [ ] Full trade AI evaluation
- [ ] Draft AI with personality-driven picks
- [ ] Holdout logic
- [ ] In-game simulation (currently uses placeholder)

---

## Data Flow

### Creating a Franchise
```
1. Client: POST /management/franchise {team_id, season_year, start_phase}
2. Server: ManagementSessionManager.create_session()
   - Creates LeagueState.new_franchise()
   - Creates ManagementService with core League
   - Starts async tick loop
3. Client: Connects WebSocket to /ws/management/{franchise_id}
4. Server: Sends state_sync with full state
5. Client: Zustand store populated via handleMessage()
```

### Time Progression
```
1. ManagementService._tick_loop() runs every 50ms
2. LeagueState.tick(elapsed) advances calendar
3. EventQueue.update() activates/expires events
4. EventGenerator callbacks spawn new events
5. Server sends calendar_update via WebSocket
6. Client updates Zustand store, React re-renders
```

### Attending an Event
```
1. Client: send({type: 'attend_event', payload: {event_id}})
2. Server: ManagementService.attend_event(event_id)
3. LeagueState.attend_event() marks event IN_PROGRESS
4. Clipboard navigates to event
5. Server sends clipboard_update
6. Client renders appropriate panel (PracticePanel, GameDayPanel, etc.)
```

---

## Key File Locations Quick Reference

| System | Key Files |
|--------|-----------|
| Player | `huddle/core/models/player.py` |
| Team | `huddle/core/models/team.py` |
| Tendencies | `huddle/core/models/tendencies.py` |
| Contracts | `huddle/core/contracts/` (negotiation.py, market_value.py) |
| Scouting | `huddle/core/scouting/` (stages.py, staff.py, report.py) |
| Philosophy | `huddle/core/philosophy/` (positions.py, evaluation.py) |
| League | `huddle/core/league/league.py` |
| Game Loop | `huddle/management/league.py` |
| Calendar | `huddle/management/calendar.py` |
| Events | `huddle/management/events.py`, `generators.py` |
| API | `huddle/api/routers/management.py`, `management_websocket.py` |
| Service | `huddle/api/services/management_service.py` |
| Store | `frontend/src/stores/managementStore.ts` |
| Hook | `frontend/src/hooks/useManagementWebSocket.ts` |
| Components | `frontend/src/components/Management/` |

---

## HC09 Feature Mapping

| HC09 Feature | Huddle Status | Location |
|--------------|---------------|----------|
| 5-Stage Scouting | Implemented | `core/scouting/stages.py` |
| Contract Negotiation | Implemented | `core/contracts/negotiation.py` |
| Position Multipliers | Implemented | `core/contracts/market_value.py` |
| Age Curves | Implemented | `core/contracts/market_value.py` |
| Team Tendencies | Implemented | `core/models/tendencies.py` |
| Philosophy Evaluation | Implemented | `core/philosophy/` |
| Season Calendar | Implemented | `management/calendar.py` |
| Real-time FA | Partial | `management/events.py` (events exist, bidding logic TODO) |
| 17 Personality Types | NOT IMPLEMENTED | - |
| Coach Skill Trees | NOT IMPLEMENTED | - |
| Staff Control Mechanic | NOT IMPLEMENTED | - |
| Wear & Tear Injuries | NOT IMPLEMENTED | - |
| Play Knowledge/Decay | NOT IMPLEMENTED | - |
| Approval Rating | NOT IMPLEMENTED | - |
| Practice Effects | STUB | `management/league.py:374` |

---

*Last Updated: December 2024*
*Documentation Agent: Documentation complete. Update this file as new systems are added.*
