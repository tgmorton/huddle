# Management System - Frontend

Overview of the ManagementV2 React frontend.

**Location**: `frontend/src/components/ManagementV2/`

---

## Architecture

```
ManagementV2/
├── ManagementV2.tsx           # Main container (~1100 lines)
├── ManagementV2.css           # Styles
├── types.ts                   # TypeScript interfaces
├── constants.ts               # Config and navigation
├── data/demo.ts               # Demo data
├── components/                # Reusable UI components
├── panels/                    # Left sidebar panels
├── content/                   # Panel content views
├── workspace/                 # Workspace grid and panes
└── utils/                     # Helpers
```

### Data Flow

```
Backend WebSocket ──► Zustand Store ──► React Components
       │                    │                  │
       │                    ▼                  │
       │            managementStore.ts         │
       │                    │                  │
       ▼                    ▼                  ▼
  Real-time           State (calendar,    UI renders
  updates             events, ticker)     from state
```

---

## Key Files

### ManagementV2.tsx (Main Component)

Orchestrates the entire interface:

- **State**: `franchiseId`, `workspaceItems`, `leftPanel`, `modalEvent`
- **WebSocket**: Connects via `useManagementWebSocket` hook
- **Event Sync**: Converts backend events to workspace items
- **Day Advancement**: Handles blocking events

```tsx
// Key patterns
const { connect, runPractice, attendEvent } = useManagementWebSocket(options);

// Event → Workspace conversion
useEffect(() => {
  const items = eventsToWorkspaceItems(storeEvents.pending);
  setWorkspaceItems(prev => mergeWithPinned(prev, items));
}, [storeEvents]);
```

### managementStore.ts (Zustand Store)

```typescript
interface ManagementStore {
  franchiseId: string | null;
  state: LeagueState | null;
  calendar: CalendarState | null;
  events: EventQueue | null;
  ticker: TickerFeed | null;

  // Actions
  setFullState(state: LeagueState): void;
  updateCalendar(calendar: CalendarState): void;
  addEvent(event: ManagementEvent): void;
}
```

### useManagementWebSocket.ts

WebSocket connection hook:

```typescript
const {
  connect,
  disconnect,
  pause,
  play,
  setSpeed,
  attendEvent,
  dismissEvent,
  runPractice,
  simGame,
} = useManagementWebSocket({
  franchiseId,
  onStateSync: (state) => store.setFullState(state),
  onEventAdded: (event) => store.addEvent(event),
  onCalendarUpdate: (cal) => store.updateCalendar(cal),
});
```

---

## Workspace System

### WorkspaceItem Type

```typescript
interface WorkspaceItem {
  id: string;
  type: ItemType;  // 'practice' | 'game' | 'player' | etc.
  title: string;
  subtitle?: string;
  isOpen: boolean;
  eventId?: string;       // Links to ManagementEvent
  eventPayload?: Record<string, unknown>;
  status: 'active' | 'pinned' | 'archived';
}
```

### Pane Components

| Type | Component | Purpose |
|------|-----------|---------|
| `practice` | PracticePane | Allocate practice time |
| `game` | GamePane | Game day actions |
| `player` | PlayerPane | Player details |
| `prospect` | ProspectPane | Draft prospect view |
| `meeting` | MeetingPane | Meeting decisions |
| `deadline` | DeadlinePane | Time-sensitive actions |
| `scout` | ScoutPane | Scouting reports |
| `decision` | ContractPane | Contract negotiations |
| `news` | NewsPane | News articles |

### Masonry Grid

Uses CSS grid with height tracking:

```css
.workspace {
  display: grid;
  grid-template-columns: repeat(auto-fill, 80px);
  grid-auto-rows: 1px;  /* Fine-grained rows */
  grid-auto-flow: dense;
}

.workspace-item {
  /* Height-based row span */
  grid-row: span var(--item-height-rows);
}
```

---

## Reference Panels

Left sidebar with context-aware content:

| Panel | Components | Content |
|-------|------------|---------|
| `personnel` | PersonnelPanel | Roster, Depth Chart, Development |
| `draft` | DraftPanel | Prospects, Board, Scouting |
| `transactions` | TransactionsPanel | Free Agents, Trades |
| `finances` | FinancesPanel | Salary Cap, Contracts, Negotiations |
| `season` | SeasonPanel | Schedule, Standings, Playoffs |
| `team` | TeamPanel | Strategy, Staff |
| `week` | WeekPanel | Weekly loop, Journal |

---

## Key Patterns

### Event to Workspace Conversion

```typescript
// utils/eventToWorkspace.ts
function eventToWorkspaceItem(event: ManagementEvent): WorkspaceItem | null {
  if (event.display_mode === 'ticker') return null;
  if (event.status === 'attended') return null;

  return {
    id: `event-${event.id}`,
    type: categoryToItemType(event.category),
    title: event.title,
    eventId: event.id,
    eventPayload: event.payload,
    isOpen: false,
    status: 'active',
  };
}
```

### LocalStorage Persistence

```typescript
// Pinned items survive refresh
savePinnedItems(items);
const pinned = loadPinnedItems();

// Franchise ID for auto-rejoin
localStorage.setItem('huddle_franchise_id', id);
```

### Blocking Day Advancement

```typescript
const blockingEvents = events.filter(e =>
  e.category === 'GAME' ||
  (e.requires_attention && !e.can_dismiss)
);

if (blockingEvents.length > 0) {
  showBlockingPopup(blockingEvents);
  return;
}

await advanceDay();
```

---

## Components (`components/`)

Reusable UI building blocks:

| Component | Purpose |
|-----------|---------|
| **TimeControls.tsx** | Play/pause and speed controls (slow/normal/fast) |
| **StatBar.tsx** | Stat bar with gradient color interpolation |
| **PlayerPortrait.tsx** | Player portrait with customizable size and status |
| **InlinePlayerCard.tsx** | Compact player card for inline references |
| **PlayerView.tsx** | Unified player detail view (used in panes) |
| **DeskDrawer.tsx** | Archived items with timeline grouping |
| **EventModal.tsx** | Modal overlay for game events |
| **ManagementEventModal.tsx** | Blocking overlay for critical events |
| **QueuePanel.tsx** | Upcoming agenda items with queue cards |
| **AdminSidebar.tsx** | Dev controls for league/franchise management |
| **WorkshopPanel.tsx** | Debug panel with 5 tabs: Status, Events, Calendar, Actions, Log |
| **StatsTable.tsx** | Reusable stats table component |
| **SettingsPanel.tsx** | User settings and preferences panel |

---

## Panels (`panels/`)

Left sidebar panel containers with tabbed interfaces:

| Panel | Tabs |
|-------|------|
| **PersonnelPanel.tsx** | Roster, Depth Chart, Coaches, Development |
| **FinancesPanel.tsx** | Salary Cap (with 6-year projection), Contracts, Negotiations |
| **TransactionsPanel.tsx** | Free Agents, Trades, Waivers |
| **DraftPanel.tsx** | Draft Board, Prospect Scouts, Draft Class |
| **TeamPanel.tsx** | Strategy, Playbook, Chemistry, Front Office |
| **SeasonPanel.tsx** | Schedule, Standings, Playoffs |
| **ReferencePanel.tsx** | Reference documentation |
| **WeekPanel.tsx** | Weekly loop and journal |
| **LeagueStatsPanel.tsx** | League-wide stats and leaders |

---

## Content Views (`content/`)

Content modules plugged into panels:

### Personnel Content
| Component | Description |
|-----------|-------------|
| **RosterContent.tsx** | Roster with player list and detail views |
| **DepthChartContent.tsx** | Depth chart with offense/defense slots |
| **CoachesContent.tsx** | Coaching staff with grouped display |
| **DevelopmentContent.tsx** | Weekly development gains from practice |

### Financial Content
| Component | Description |
|-----------|-------------|
| **SalaryCapContent.tsx** | Salary cap with 6-year projection chart (Recharts) |
| **ContractsContent.tsx** | Team contracts with filtering and year-by-year breakdown |
| **FreeAgentsContent.tsx** | Free agents with tier badges and market values |
| **NegotiationsContent.tsx** | Active negotiations list with patience indicators and offer tracking |

### Playbook & Strategy
| Component | Description |
|-----------|-------------|
| **PlaybookContent.tsx** | Play mastery/knowledge tracking per player |

### League Data
| Component | Description |
|-----------|-------------|
| **ScheduleContent.tsx** | Season schedule (wired to API) |
| **StandingsContent.tsx** | Division standings (wired to API) |
| **PlayoffsContent.tsx** | Playoff picture/seeding and bracket visualization |
| **TeamStatsContent.tsx** | Team stats display and comparison |

### Draft Management
| Component | Description |
|-----------|-------------|
| **DraftClassContent.tsx** | Draft class prospects list |
| **DraftBoardContent.tsx** | User's custom draft board (rankings/tiering) |
| **ProspectDetailView.tsx** | Prospect detail view |

---

## Workspace Panes (`workspace/panes/`)

Focused decision-making panes for workspace items:

### Player/Prospect Details
| Pane | Purpose |
|------|---------|
| **PlayerPane.tsx** | Player detail pane wrapping PlayerView |
| **ProspectPane.tsx** | Prospect detail pane (matches PlayerPane design) |
| **ContractDetailPane.tsx** | Player contract detail with restructure/cut options |
| **PlayerStatsPane.tsx** | Player career and season statistics view |

### Event/Decision Panes
| Pane | Purpose |
|------|---------|
| **GamePane.tsx** | Game day with sim and results |
| **PracticePane.tsx** | Practice allocation (playbook/development/game prep sliders) |
| **DeadlinePane.tsx** | Injury/deadline pane with real player data |
| **ScoutPane.tsx** | Scout report showing opponent analysis |
| **MeetingPane.tsx** | Meeting/media event with completion results |
| **NewsPane.tsx** | News item display (reference type) |

### Negotiation
| Pane | Purpose |
|------|---------|
| **NegotiationPane.tsx** | Full contract negotiation UI with offers and tone selection |
| **ContractPane.tsx** | Decision pane for trades/contracts |
| **AuctionPane.tsx** | Competitive bidding UI for elite free agents with multi-round auctions |

---

## Summary

| Category | Count |
|----------|-------|
| Components | 14 |
| Panels | 9 |
| Content Views | 17 |
| Workspace Panes | 13 |
| **Total** | **53** |

---

## CSS Tokens

```css
/* Spacing */
--unit: 48px;
--unit-half: 24px;
--unit-quarter: 12px;

/* Colors */
--bg-base: #09090b;
--bg-surface: #0f0f12;
--accent: #f59e0b;  /* Amber */
--text-primary: #e4e4e7;

/* Typography */
--font-sans: Berkeley Mono;
--text-base: 14px;
```

---

## See Also

- [Backend Documentation](backend.md) - Full backend reference
- [API Reference](api.md) - REST and WebSocket endpoints
- [Event Architecture](event-architecture.md) - Event → Workspace flow
