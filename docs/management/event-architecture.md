# Event → Workspace → Pane Architecture

This document explains how management events flow from the backend through the frontend UI to display the correct interactive pane.

---

## Overview

```
Backend Event → Store → Workspace Item → Pane Component
     ↓              ↓           ↓              ↓
ManagementEvent → events.pending → WorkspaceItem → PracticePane, GamePane, etc.
```

The system has three main layers:
1. **Events** - Backend data representing things that need attention
2. **Workspace Items** - UI representation of events as cards/panes
3. **Panes** - Interactive components for handling specific event types

---

## Layer 1: Management Events (Backend → Store)

### Source
Events come from the backend via:
- WebSocket messages (`event_added`, `state_sync`)
- REST API calls (`advanceDay`, `getEvents`)

### Storage
Events are stored in the Zustand management store:

```typescript
// stores/managementStore.ts
interface ManagementStore {
  events: EventQueue | null;
  // ...
}

interface EventQueue {
  pending: ManagementEvent[];   // Active events needing attention
  upcoming: ManagementEvent[];  // Scheduled future events
  urgent_count: number;
  total_count: number;
}
```

### Event Structure

```typescript
// types/management.ts
interface ManagementEvent {
  id: string;
  event_type: string;
  category: EventCategory;      // PRACTICE, GAME, CONTRACT, SCOUTING, etc.
  priority: EventPriority;      // CRITICAL, HIGH, NORMAL, LOW
  title: string;
  description: string;
  display_mode: DisplayMode;    // PANE, MODAL, or TICKER
  status: EventStatus;
  payload: Record<string, unknown>;
  // ...
}
```

**Key Fields:**
- `category` - Determines which pane type to use
- `display_mode` - Where the event should appear:
  - `PANE` → Workspace grid (interactive card/pane)
  - `MODAL` → Blocking modal overlay
  - `TICKER` → News ticker only (no interaction)

---

## Layer 2: Event → Workspace Item Conversion

### Conversion Utility

```typescript
// components/ManagementV2/utils/eventToWorkspace.ts

const CATEGORY_TO_ITEM_TYPE: Record<string, ItemType> = {
  PRACTICE: 'practice',
  GAME: 'game',
  MEETING: 'meeting',
  DEADLINE: 'deadline',
  CONTRACT: 'decision',
  TRADE: 'decision',
  FREE_AGENCY: 'decision',
  SCOUTING: 'scout',
  DRAFT: 'scout',
  // ...
};

function eventToWorkspaceItem(event: ManagementEvent): WorkspaceItem | null {
  // Skip ticker-only events
  if (event.display_mode === 'TICKER') return null;

  // Skip already-handled events
  if (['ATTENDED', 'EXPIRED', 'DISMISSED'].includes(event.status)) return null;

  // Map category to item type
  const itemType = CATEGORY_TO_ITEM_TYPE[event.category] || 'deadline';

  return {
    id: `event-${event.id}`,
    type: itemType,           // Used by WorkspaceItem to pick pane
    title: event.title,
    eventId: event.id,        // Original event ID for API calls
    eventPayload: event.payload,  // Data passed to pane
    // ...
  };
}
```

### Workspace Item Types

```typescript
// components/ManagementV2/types.ts
type ItemType =
  | 'practice'   // → PracticePane
  | 'game'       // → GamePane
  | 'meeting'    // → MeetingPane
  | 'deadline'   // → DeadlinePane
  | 'decision'   // → ContractPane
  | 'scout'      // → ScoutPane
  | 'player'     // → PlayerPane (reference, not event)
  | 'prospect'   // → ProspectPane (reference, not event)
  | 'news';      // → NewsPane (reference, not event)
```

---

## Layer 3: Workspace Item → Pane Routing

### The Router

```typescript
// components/ManagementV2/workspace/WorkspaceItem.tsx

// When item is open, render the appropriate pane
<div className="workspace-item__pane-content">
  {item.type === 'practice' && (
    <PracticePane
      eventId={item.eventId}
      onComplete={onRemove}
    />
  )}
  {item.type === 'decision' && (
    <ContractPane
      eventId={item.eventId || item.id}
      onComplete={onRemove}
    />
  )}
  {item.type === 'scout' && (
    <ScoutPane
      eventPayload={item.eventPayload}
      onComplete={onRemove}
    />
  )}
  {item.type === 'game' && (
    <GamePane
      eventId={item.eventId}
      eventPayload={item.eventPayload}
      onComplete={onRemove}
    />
  )}
  // ... etc
</div>
```

### Pane Props Pattern

All event panes receive:
- `eventId` - For API calls (run practice, sim game, etc.)
- `eventPayload` - Event-specific data from backend
- `onComplete` - Callback when done (removes item from workspace)

---

## User Interaction Flow

### Click Event in WorkshopPanel → Open in Workspace

```
┌─────────────────────┐
│  WorkshopPanel      │
│  Events Tab         │
│  ┌───────────────┐  │
│  │ Practice Event├──┼──── onClick ────┐
│  └───────────────┘  │                 │
└─────────────────────┘                 │
                                        ▼
                            ┌───────────────────────┐
                            │ handleEventClick()    │
                            │ in ManagementV2.tsx   │
                            └───────────┬───────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
         ┌─────────────────┐                    ┌─────────────────┐
         │ Event exists in │                    │ Event not in    │
         │ workspace?      │                    │ workspace       │
         └────────┬────────┘                    └────────┬────────┘
                  │                                      │
                  ▼                                      ▼
         Move to front & open              Convert to WorkspaceItem
                  │                        Add to workspace (open)
                  │                                      │
                  └──────────────┬───────────────────────┘
                                 │
                                 ▼
                    ┌───────────────────────┐
                    │ WorkspaceItem renders │
                    │ with isOpen: true     │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Correct Pane renders  │
                    │ (PracticePane, etc.)  │
                    └───────────────────────┘
```

### handleEventClick Implementation

```typescript
// components/ManagementV2/ManagementV2.tsx

const handleEventClick = useCallback((event: ManagementEvent) => {
  // Convert to workspace item
  const workspaceItem = eventToWorkspaceItem(event);
  if (!workspaceItem) return;

  // Check if already on workspace
  const existingIndex = workspaceItems.findIndex(
    item => item.eventId === event.id
  );

  if (existingIndex >= 0) {
    // Move to front and open
    setWorkspaceItems(items => {
      const updated = [...items];
      const existing = updated[existingIndex];
      updated.splice(existingIndex, 1);
      return [{ ...existing, isOpen: true }, ...updated];
    });
  } else {
    // Add new and open
    setWorkspaceItems(items => [
      { ...workspaceItem, isOpen: true },
      ...items
    ]);
  }
}, [workspaceItems]);
```

---

## Category → ItemType → Pane Mapping

| Event Category | ItemType | Pane Component | Purpose |
|----------------|----------|----------------|---------|
| PRACTICE | `practice` | PracticePane | Allocate practice time |
| GAME | `game` | GamePane | Sim game, view results |
| MEETING | `meeting` | MeetingPane | Staff/player meetings |
| DEADLINE | `deadline` | DeadlinePane | Time-sensitive decisions |
| CONTRACT | `decision` | ContractPane | Contract negotiations |
| TRADE | `decision` | ContractPane | Trade offers |
| FREE_AGENCY | `decision` | ContractPane | FA signings |
| SCOUTING | `scout` | ScoutPane | Scout reports |
| DRAFT | `scout` | ScoutPane | Draft-related scouting |
| ROSTER | `decision` | ContractPane | Roster moves |
| INJURY | `deadline` | DeadlinePane | Injury decisions |

---

## File Locations

```
frontend/src/
├── stores/
│   └── managementStore.ts       # Event storage (events.pending)
│
├── types/
│   └── management.ts            # ManagementEvent, EventCategory, etc.
│
├── components/ManagementV2/
│   ├── ManagementV2.tsx         # Main component, handleEventClick
│   ├── types.ts                 # WorkspaceItem, ItemType
│   │
│   ├── utils/
│   │   └── eventToWorkspace.ts  # Event → WorkspaceItem conversion
│   │
│   ├── workspace/
│   │   ├── WorkspaceItem.tsx    # ItemType → Pane routing
│   │   └── panes/
│   │       ├── PracticePane.tsx
│   │       ├── GamePane.tsx
│   │       ├── ContractPane.tsx
│   │       ├── ScoutPane.tsx
│   │       ├── DeadlinePane.tsx
│   │       ├── MeetingPane.tsx
│   │       └── ...
│   │
│   └── components/
│       └── WorkshopPanel.tsx    # Debug panel with event list
```

---

## Adding a New Event Type

To add support for a new event category:

1. **Backend**: Create event with new category in `huddle/management/events.py`

2. **Frontend Type**: Add category to `EventCategory` in `types/management.ts`:
   ```typescript
   export type EventCategory =
     | 'PRACTICE' | 'GAME' | ... | 'NEW_CATEGORY';
   ```

3. **Map to ItemType**: Update `CATEGORY_TO_ITEM_TYPE` in `eventToWorkspace.ts`:
   ```typescript
   const CATEGORY_TO_ITEM_TYPE = {
     // ...existing...
     NEW_CATEGORY: 'newtype',  // or reuse existing like 'decision'
   };
   ```

4. **Create Pane** (if new ItemType): Create `NewTypePane.tsx` in `workspace/panes/`

5. **Wire Routing**: Add to WorkspaceItem.tsx:
   ```typescript
   {item.type === 'newtype' && (
     <NewTypePane eventId={item.eventId} onComplete={onRemove} />
   )}
   ```

6. **Export**: Add to `workspace/panes/index.ts`

---

## Key Concepts

### Event Lifecycle
```
SCHEDULED → PENDING → IN_PROGRESS → ATTENDED/DISMISSED/EXPIRED
```

### Workspace Item Lifecycle
```
Event arrives → Converted to WorkspaceItem → Added to workspace (closed)
                                                      ↓
User clicks → Item opens → Pane renders → User takes action → onComplete called
                                                      ↓
                                            Item removed from workspace
```

### Display Mode Routing
- `PANE` → Goes to workspace grid, user can open/close
- `MODAL` → Blocking overlay, must handle before continuing
- `TICKER` → News feed only, no interactive handling
