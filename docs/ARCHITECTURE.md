# Architecture Overview

This document describes how the Huddle system components interact.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  React + TypeScript + Zustand + PixiJS                      │
│  Port: 5173                                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│  Port: 8000                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Routers   │  │  Services   │  │   Schemas   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│   Core    │  │Management │  │Simulation │
│  Models   │  │  System   │  │  Engines  │
└───────────┘  └───────────┘  └───────────┘
```

## Layer Descriptions

### Frontend Layer
**Location:** `frontend/src/`

| Component | Purpose |
|-----------|---------|
| `components/` | React UI screens (Management, V2Sim, AgentMail, Admin) |
| `stores/` | Zustand state management (gameStore, managementStore) |
| `hooks/` | WebSocket connections and data fetching |

**Key Technologies:**
- React 18 with TypeScript
- Zustand for state management
- PixiJS for game visualization
- Vite for build tooling

### API Layer
**Location:** `huddle/api/`

| Component | Purpose |
|-----------|---------|
| `routers/` | HTTP endpoint handlers (18 router files) |
| `services/` | Business logic (SessionManager, ManagementService) |
| `schemas/` | Pydantic models for request/response validation |

**Key Routers:**
- `management.py` - Franchise mode operations
- `v2_sim.py` - V2 simulation control
- `agentmail.py` - Inter-agent communication
- `admin.py` - League generation

### Core Layer
**Location:** `huddle/core/`

| Module | Purpose |
|--------|---------|
| `models/` | Player, Team, Game, Play, Field |
| `contracts/` | Salary cap, negotiations, free agency |
| `scouting/` | Player evaluation, scout biases |
| `personality/` | Player archetypes and traits |
| `playbook/` | Formations and play concepts |

### Management Layer
**Location:** `huddle/management/`

| Module | Purpose |
|--------|---------|
| `league.py` | LeagueState, game loop, calendar |
| `events.py` | ManagementEvent definitions |
| `generators.py` | Event and scenario generation |
| `calendar.py` | Season calendar, scheduling |

### Simulation Layer
**Location:** `huddle/simulation/`

| System | Status | Purpose |
|--------|--------|---------|
| `v2/` | **Active** | Orchestrator, AI brains, physics |
| `sandbox/` | Legacy | Prototyping simulations |
| `engine.py` | Legacy | Basic play resolution |

## Data Flow

### Management Game Loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│     API     │────▶│ LeagueState │
│  (Zustand)  │◀────│  (FastAPI)  │◀────│  (Python)   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                    │
      │    WebSocket      │                    │
      │◀──────────────────│                    │
      │                   │                    │
                          ▼
                 ┌─────────────────┐
                 │ ManagementEvent │
                 │    Generator    │
                 └─────────────────┘
```

1. **Frontend** sends actions (advance day, make decision)
2. **API** routes to ManagementService
3. **LeagueState** updates calendar, processes events
4. **Generator** creates new events based on calendar
5. **WebSocket** pushes state updates to frontend

### Simulation Flow (V2)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  V2 Sim API │────▶│Orchestrator │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          │              ┌─────┴─────┐
                          ▼              ▼           ▼
                    ┌──────────┐  ┌──────────┐ ┌──────────┐
                    │ AI Brains│  │ Physics  │ │Resolution│
                    └──────────┘  └──────────┘ └──────────┘
```

1. **Frontend** starts simulation
2. **API** initializes Orchestrator
3. **Orchestrator** runs phases: pre-snap → snap → play → post-play
4. **AI Brains** make decisions (QB reads, routes, coverage)
5. **Physics** handles movement and collisions
6. **Resolution** determines play outcome

## WebSocket Communication

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/ws/management/{session_id}` | Management state updates |
| `/ws/agentmail` | Agent communication |
| `/ws/v2-sim/{session_id}` | Simulation state |

### Management WebSocket Messages

**Server → Client:**
```typescript
// Full state sync
{ type: "state_sync", payload: LeagueState }

// Partial update
{ type: "state_update", payload: { calendar: {...}, events: [...] } }

// Event notification
{ type: "event_added", payload: ManagementEvent }
```

**Client → Server:**
```typescript
// Request sync
{ type: "request_sync" }

// Action
{ type: "action", payload: { action: "advance_day" } }
```

## State Management

### LeagueState Lifecycle

```
Created ──▶ Initialized ──▶ Running ──▶ Season End
                │              │
                │    ┌─────────┴─────────┐
                │    ▼                   ▼
                │  Day Tick          Event Processing
                │    │                   │
                │    ▼                   ▼
                └──▶ Calendar Update ◀──┘
```

**Key State Components:**
- `calendar` - Current date, season phase, week
- `teams` - All team data with rosters
- `players` - Player attributes, contracts
- `events` - Active ManagementEvents

### ManagementEvent Lifecycle

```
pending ──▶ active ──▶ resolved ──▶ expired
              │                       │
              └───────────────────────┘
                   (if no action)
```

**Event Types:**
- Contract negotiations
- Trade offers
- Injury reports
- Practice decisions
- Draft picks

## File Locations

| System | Key Files |
|--------|-----------|
| Frontend | `frontend/src/stores/managementStore.ts` |
| API | `huddle/api/routers/management.py` |
| Service | `huddle/api/services/management_service.py` |
| State | `huddle/management/league.py` |
| Events | `huddle/management/events.py` |
| Simulation | `huddle/simulation/v2/orchestrator.py` |
| AI Brains | `huddle/simulation/v2/ai/*.py` |

## See Also

- [Quick Start](./QUICK_START.md) - Running the application
- [API Reference](./api/README.md) - Endpoint documentation
- [AgentMail](./agentmail/) - Inter-agent communication
- [V2 Simulation Design](./simulation/README.md) - Detailed V2 architecture
