# Management System

The franchise management layer for Huddle - everything outside of on-field simulation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  ManagementV2   │  │  Zustand Store │  │  WebSocket   │  │
│  │  (workspace)    │◄─│  (state)       │◄─│  Hook        │  │
│  └─────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  REST Router    │  │  WebSocket     │  │  Service     │  │
│  │  (endpoints)    │  │  (real-time)   │  │  (tick loop) │  │
│  └─────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                  Management Layer (Python)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ League   │ │ Calendar │ │ Events   │ │ Event          │  │
│  │ State    │ │          │ │ Queue    │ │ Generator      │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Clipboard│ │ Ticker   │ │ Health   │ │ Draft Board    │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Documentation

| Document | Description | Lines |
|----------|-------------|-------|
| **[backend.md](backend.md)** | Complete backend reference - all modules, classes, methods | ~2785 |
| **[api.md](api.md)** | REST and WebSocket API reference | ~1500 |
| **[frontend.md](frontend.md)** | React frontend overview (44 components) | ~360 |
| **[event-architecture.md](event-architecture.md)** | Event → Workspace → Pane flow | ~360 |
| **[data-flow.md](data-flow.md)** | Complete data flow diagrams (tick loop, WS, state sync) | ~320 |

---

## Quick Start

### 1. Generate a League

```bash
curl -X POST http://localhost:8000/api/v1/admin/league/generate \
  -H "Content-Type: application/json" \
  -d '{"team_count": 32}'
```

### 2. Create a Franchise

```bash
curl -X POST http://localhost:8000/api/v1/management/franchise \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "TEAM_UUID",
    "team_name": "Eagles",
    "season_year": 2024,
    "start_phase": "training_camp"
  }'
```

### 3. Connect WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/management/FRANCHISE_ID');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'state_sync') {
    console.log('Calendar:', msg.data.calendar);
    console.log('Events:', msg.data.events);
  }
};
```

### 4. Advance Time

```bash
curl -X POST http://localhost:8000/api/v1/management/franchise/FRANCHISE_ID/play \
  -H "Content-Type: application/json" \
  -d '{"speed": "fast"}'
```

---

## Key Concepts

### LeagueState

Single source of truth for a franchise. Contains:
- **Calendar**: Time progression, season phase
- **Events**: Management tasks and decisions
- **Clipboard**: UI navigation state
- **Ticker**: News feed

### Events

Everything that needs attention:
- **Practice** - Allocate practice time
- **Games** - Game day
- **Contracts** - Negotiations, extensions
- **Free Agency** - Available players
- **Trades** - Incoming offers
- **Draft** - Scouting, draft day

Events have:
- **Priority**: CRITICAL → HIGH → NORMAL → LOW → BACKGROUND
- **Status**: SCHEDULED → PENDING → ATTENDED/DISMISSED/EXPIRED
- **Display Mode**: PANE (workspace), MODAL (blocking), TICKER (news only)

### Auto-Pause

Game automatically pauses for:
- CRITICAL priority events
- Events affecting your team
- Game day
- Important deadlines

### Tick Loop

Time progresses via async tick loop:
1. Calculate real elapsed time
2. Advance calendar (speed-adjusted)
3. Activate/expire events
4. Check auto-pause conditions
5. Send WebSocket updates

---

## Backend Modules

| Module | Purpose |
|--------|---------|
| `league.py` | LeagueState - central orchestrator |
| `calendar.py` | Time progression, season phases |
| `events.py` | ManagementEvent, EventQueue |
| `generators.py` | Event spawning from calendar |
| `clipboard.py` | UI navigation state |
| `ticker.py` | News feed |
| `health.py` | Injuries, fatigue |
| `draft_board.py` | User's draft rankings |

See [backend.md](backend.md) for complete documentation.

---

## Frontend Components

| Component | Purpose |
|-----------|---------|
| `ManagementV2.tsx` | Main container, state orchestration |
| `WorkspaceItem.tsx` | Workspace cards/panes |
| `*Panel.tsx` | Left sidebar panels |
| `*Pane.tsx` | Expanded workspace items |
| `managementStore.ts` | Zustand state |
| `useManagementWebSocket.ts` | WebSocket hook |

See [frontend.md](frontend.md) for overview.

---

## API Endpoints

### Franchise
- `POST /management/franchise` - Create
- `GET /management/franchise/{id}` - Get state
- `DELETE /management/franchise/{id}` - Delete

### Time
- `POST .../pause` - Pause
- `POST .../play` - Resume
- `POST .../advance-day` - Next day
- `POST .../advance-to-game` - Skip to game day

### Events
- `GET .../events` - Get pending
- `POST .../events/attend` - Attend event
- `POST .../events/dismiss` - Dismiss event

### Contracts
- `GET .../contracts/{player_id}` - Contract detail
- `POST .../contracts/{player_id}/restructure` - Restructure
- `POST .../contracts/{player_id}/cut` - Release player

### Negotiations
- `POST .../negotiations/start` - Start talks
- `POST .../negotiations/{player_id}/offer` - Submit offer
- `GET .../negotiations/active` - List active
- `DELETE .../negotiations/{player_id}` - End negotiation

### Actions
- `POST .../run-practice` - Run practice
- `POST .../sim-game` - Simulate game

See [api.md](api.md) for complete reference.

---

## File Locations

### Backend
```
huddle/management/                    # Core management modules
huddle/api/routers/management/        # REST endpoints (modular)
  ├── franchise.py                    # Franchise lifecycle
  ├── contracts.py                    # Contract management
  ├── free_agency.py                  # FA within management
  ├── clipboard.py                    # Events, drawer, ticker
  ├── practice.py                     # Practice facility
  ├── draft.py                        # Draft within management
  └── game.py                         # Game simulation
huddle/api/services/management_service.py  # Service layer
huddle/api/schemas/management.py      # Pydantic schemas
```

### Frontend
```
frontend/src/components/ManagementV2/   # UI components
frontend/src/stores/managementStore.ts  # State
frontend/src/hooks/useManagementWebSocket.ts  # WebSocket
frontend/src/types/management.ts        # Types
frontend/src/api/managementClient.ts    # API client
```

---

## See Also

- [Architecture](../ARCHITECTURE.md) - System overview
- [Simulation](../simulation/README.md) - Game simulation
- [API Overview](../api/README.md) - Full API docs
