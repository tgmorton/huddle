# Documentation Agent Brief

**Status:** resolved

## Your Mission

Create comprehensive documentation of the existing codebase so future agents can quickly understand what's built, where it lives, and how systems connect. This saves significant ramp-up time.

## Context

This is "Huddle" - a state-of-the-art football management game inspired heavily by **NFL Head Coach 09**. The codebase has substantial infrastructure already built, but it's not well-documented. Future agents waste time rediscovering what exists.

## Key Reference Documents

Read these first to understand the vision:
- `docs/DESIGN_PHILOSOPHY.md` - Seven pillars guiding the game design
- `NFLHEADCOACH09DETAILS.md` - Detailed breakdown of the HC09 systems we're drawing from

## What Needs Documenting

### 1. Core Data Models (`huddle/core/`)

Document each model with:
- Purpose and responsibilities
- Key fields/properties
- How it connects to other models
- Example usage

**Files to document:**
- `core/models/player.py` - Player with attributes, contracts, physical info
- `core/models/team.py` - Team, Roster, DepthChart
- `core/models/tendencies.py` - AI behavior DNA (DraftStrategy, TradeAggression, NegotiationTone, etc.)
- `core/models/team_identity.py` - TeamFinancials
- `core/attributes/base.py` and `registry.py` - Attribute system

### 2. Contract System (`huddle/core/contracts/`)

This is a complete HC09-style negotiation system:
- `negotiation.py` - Full negotiation loop with offers, counters, walk-away
- `market_value.py` - Position multipliers, age curves, salary calculation
- `free_agency.py` - FA market mechanics
- `extensions.py` - Contract extensions
- `ai_decisions.py` - AI contract decision logic

### 3. Scouting System (`huddle/core/scouting/`)

HC09-style fog of war scouting:
- `stages.py` - 5 scouting stages (UNKNOWN→COMPLETE), attribute reveal by stage
- `staff.py` - Scout specialties, skill levels, ScoutingDepartment
- `projections.py` - Player projections with accuracy
- `report.py` - Scouting reports with letter grades, scheme fit

### 4. Philosophy/Evaluation (`huddle/core/philosophy/`)

Team-specific player evaluation:
- `positions.py` - Position philosophies (QBPhilosophy, RBPhilosophy, etc.)
- `evaluation.py` - Calculate OVR based on team's philosophy weights

### 5. League Structure (`huddle/core/league/`)

- `nfl_data.py` - All 32 NFL teams, divisions, conferences
- `league.py` - League-level operations

### 6. Management Layer (`huddle/management/`)

The game loop infrastructure:
- `league.py` - LeagueState (central controller), tick loop, auto-pause
- `calendar.py` - LeagueCalendar, season phases, time speeds, NFL week structure
- `events.py` - ManagementEvent, EventQueue, event lifecycle
- `generators.py` - EventGenerator (spawns practice, game, FA, trade events)

### 7. API Layer (`huddle/api/`)

FastAPI backend:
- `routers/management.py` - Management endpoints
- `routers/management_websocket.py` - Real-time updates
- `services/management_service.py` - Business logic

### 8. Frontend (`frontend/src/`)

React/TypeScript:
- `components/Management/` - Management UI panels
- `hooks/useManagementWebSocket.ts` - WebSocket connection
- `stores/managementStore.ts` - State management

## Output Format

Create `docs/CODEBASE_REFERENCE.md` with:

```markdown
# Huddle Codebase Reference

## Architecture Overview
[High-level diagram or description of how layers connect]

## Core Models
### Player
- Location: `huddle/core/models/player.py`
- Purpose: ...
- Key Properties: ...
- Relationships: ...

### Team
...

## Systems
### Contract Negotiation
- Entry Point: `start_negotiation()` in `core/contracts/negotiation.py`
- Flow: ...
- Key Functions: ...

### Scouting
...

## Data Flow
[How data moves from models → services → API → frontend]

## What's Implemented vs Placeholder
[List of fully working systems vs stubs that need implementation]
```

## Important Notes

1. **Be thorough but scannable** - Future agents need to find things fast
2. **Include file paths** - Always reference exact locations
3. **Note TODOs and placeholders** - Flag `_apply_practice_effects()` and similar stubs
4. **Cross-reference HC09** - Note which HC09 systems each component implements
5. **Document the gaps** - What's NOT built yet is as important as what is

## What's Known to be Missing

From analysis, these HC09 features are NOT yet implemented:
- Personality archetypes (17 types that drive all interactions)
- Coach skill trees (Basic + 44 Special skills)
- Staff control mechanic (cede authority for talent)
- Wear & tear injury system (body-part HP)
- Play knowledge/decay (Unlearned→Learned→Mastered)
- Approval rating (5-faction reputation)
- Practice effects (stub exists, no real impact)

Document these gaps clearly so future agents know where to focus.

## Coordination

When complete, update this file to note what was documented. Other agents reading `agentmail/` should know documentation exists.

---

## Status: COMPLETE (December 2024)

Documentation has been created at `docs/CODEBASE_REFERENCE.md`. This includes:

- **Architecture Overview** with visual diagram
- **Core Models**: Player, Team, Tendencies, Attributes
- **Contract System**: Negotiation, Market Value, Free Agency, Extensions
- **Scouting System**: 5-stage fog of war, Scout Staff, Projections, Reports
- **Philosophy/Evaluation**: Position philosophies, philosophy-weighted OVR
- **League Structure**: NFL teams, standings, schedule, FA pool
- **Management Layer**: LeagueState, Calendar, Events, Generators
- **API Layer**: REST endpoints, WebSocket, ManagementService
- **Frontend**: Zustand store, WebSocket hook, UI components
- **Implemented vs Placeholder**: Clear status of what works vs TODO
- **HC09 Feature Mapping**: What's implemented from HC09 vs what's missing

**Key gaps identified**:
- `_apply_practice_effects()` is a stub
- Personality archetypes (17 types) NOT implemented
- Coach skill trees NOT implemented
- Wear & tear injury system NOT implemented
- Play knowledge/decay NOT implemented
- Approval rating NOT implemented
