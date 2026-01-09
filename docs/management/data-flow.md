# Management System Data Flow

Detailed visualization of how data flows through the Management System, from backend tick loop to frontend UI.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  ManagementV2    │◄───│  Zustand Store   │◄───│  useManagementWS     │   │
│  │  (components)    │    │  (state)         │    │  (WebSocket hook)    │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────────┘   │
│           ▲                       ▲                       ▲                  │
│           │                       │                       │                  │
│           │               REST responses          WebSocket messages         │
│           │                       │                       │                  │
└───────────┼───────────────────────┼───────────────────────┼──────────────────┘
            │                       │                       │
            │ User Actions          │                       │
            ▼                       ▼                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                               API LAYER (FastAPI)                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐    │
│  │  REST Router     │───▶│  Management      │───▶│  WebSocket Handler   │    │
│  │  (/management)   │    │  Service         │    │  (/ws/management)    │    │
│  └──────────────────┘    └──────────────────┘    └──────────────────────┘    │
│                                   │                       ▲                   │
│                                   │ Tick Loop             │ Broadcasts        │
│                                   ▼                       │                   │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           MANAGEMENT LAYER (Python)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ LeagueState  │  │ LeagueCalendar│ │ EventQueue   │  │ EventGenerator   │  │
│  │ (orchestrator)│ │ (time)       │  │ (events)     │  │ (spawns events)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Clipboard    │  │ TickerFeed   │  │ Health       │  │ DraftBoard       │  │
│  │ (UI state)   │  │ (news)       │  │ (injuries)   │  │ (rankings)       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Tick Loop Data Flow

The tick loop is the heartbeat of the management system, running at 20 ticks/second.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ManagementService._tick_loop()                   │
│                            (runs every 50ms)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    1. Calculate elapsed time
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           LeagueState.tick()                             │
└─────────────────────────────────────────────────────────────────────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ LeagueCalendar  │   │ EventQueue      │   │ Auto-Pause      │
│ .tick()         │   │ .update()       │   │ Check           │
│                 │   │                 │   │                 │
│ • Advance time  │   │ • Activate      │   │ • Critical?     │
│ • Speed adjust  │   │   scheduled     │   │ • Game day?     │
│ • Phase check   │   │ • Expire old    │   │ • Deadline?     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                     │                      │
         │                     │            If pause triggered
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Callback:       │   │ Callback:       │   │ Callback:       │
│ _on_tick        │   │ _on_event_      │   │ _on_pause       │
│                 │   │ needs_attention │   │                 │
│ • Update badges │   │ • Add to ticker │   │ • Stop time     │
│ • Cleanup       │   │ • Notify UI     │   │ • Notify WS     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ManagementService (async)                           │
│  • _send_calendar_update() ──▶ WebSocket ──▶ Frontend                    │
│  • _send_event_added()     ──▶ WebSocket ──▶ Frontend                    │
│  • _send_auto_paused()     ──▶ WebSocket ──▶ Frontend                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Time Progression Detail

```
Real Time (wall clock)
    │
    │  elapsed_seconds (0.05s per tick)
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LeagueCalendar.tick()                            │
│                                                                          │
│   game_minutes = elapsed_seconds × time_multiplier × 60                  │
│                                                                          │
│   Time Multipliers:                                                      │
│   ┌────────────┬─────────────────────────────────────────────────────┐  │
│   │ Speed      │ Multiplier │ Real → Game Time                       │  │
│   ├────────────┼────────────┼───────────────────────────────────────┤  │
│   │ PAUSED     │    0.0     │ Time stops                             │  │
│   │ SLOW       │    0.5     │ 1 min real = 30 min game               │  │
│   │ NORMAL     │    1.0     │ 1 min real = 1 hour game               │  │
│   │ FAST       │    2.0     │ 1 min real = 2 hours game              │  │
│   │ VERY_FAST  │   10.0     │ 1 min real = 10 hours game             │  │
│   │ LIGHTNING  │   30.0     │ 1 min real = 30 hours game (~1.25 days)│  │
│   └────────────┴────────────┴───────────────────────────────────────┘  │
│                                                                          │
│   current_date += timedelta(minutes=game_minutes)                        │
│                                                                          │
│   Returns: minutes_advanced (int)                                        │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    Phase Transition Check
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
  │ OFFSEASON   │  ───▶ │ FREE_AGENCY │  ───▶ │ DRAFT       │
  │ Feb-Mar     │       │ Mar 15+     │       │ Apr 25+     │
  └─────────────┘       └─────────────┘       └─────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
  │ TRAINING    │  ◀─── │ PRESEASON   │  ◀─── │ ROOKIE_CAMP │
  │ Jul 22+     │       │ Aug 1+      │       │ May 1+      │
  └─────────────┘       └─────────────┘       └─────────────┘
         │
         ▼
  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
  │ REGULAR     │  ───▶ │ PLAYOFFS    │  ───▶ │ SUPER_BOWL  │
  │ Week 1+     │       │ After week  │       │ After conf  │
  │             │       │ 18          │       │ champs      │
  └─────────────┘       └─────────────┘       └─────────────┘
```

---

## Event Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Event State Machine                              │
└─────────────────────────────────────────────────────────────────────────┘

                          Event Created
                               │
                               ▼
                        ┌─────────────┐
                        │ SCHEDULED   │
                        │             │
                        │ (future)    │
                        └─────────────┘
                               │
                   When: scheduled_for <= now
                               │
                               ▼
                        ┌─────────────┐
                        │  PENDING    │  ◀──── Most events start here
                        │             │
                        │ (active)    │
                        └─────────────┘
                          │         │
            User attends  │         │  User dismisses OR
            (if modal) ───┘         └── deadline passes
                          │         │
                          ▼         ▼
                   ┌─────────────┐  ┌─────────────┐
                   │  ATTENDED   │  │  DISMISSED  │
                   │             │  │  /EXPIRED   │
                   │ (complete)  │  │  (skipped)  │
                   └─────────────┘  └─────────────┘
```

### Event → UI Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Event Activation Triggers UI Flow                     │
└─────────────────────────────────────────────────────────────────────────┘

Backend: EventQueue.update() activates event
                     │
                     ▼
Backend: Callback _on_event_needs_attention fires
                     │
                     ├──▶ Add to TickerFeed (if HIGH+ priority)
                     │
                     ▼
Backend: _send_event_added() sends WS message
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  WebSocket Message: { type: "event_added", payload: {...} }              │
└──────────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
Frontend: useManagementWebSocket.handleMessage()
                     │
                     ▼
Frontend: managementStore.addEvent(event)
                     │
                     ├──▶ Updates store.events.pending[]
                     │
                     ▼
Frontend: ManagementV2.tsx re-renders
                     │
                     ├──▶ useEffect detects new pending events
                     │
                     ▼
Frontend: eventToWorkspace() converts event to workspace item
                     │
                     ├──▶ Event appears as WorkspaceItem (card)
                     │
                     └──▶ If CRITICAL: Shows ManagementEventModal
```

---

## WebSocket Message Types

### Backend → Frontend (Outbound)

```
┌────────────────────┬────────────────────────────────────────────────────┐
│ Message Type       │ Purpose                                            │
├────────────────────┼────────────────────────────────────────────────────┤
│ state_sync         │ Full state on initial connect                      │
│                    │ Payload: LeagueState (calendar, events, clipboard) │
├────────────────────┼────────────────────────────────────────────────────┤
│ calendar_update    │ Time advancement (throttled to 10/sec max)         │
│                    │ Payload: CalendarState + pending events            │
├────────────────────┼────────────────────────────────────────────────────┤
│ event_added        │ New event activated                                │
│                    │ Payload: ManagementEvent                           │
├────────────────────┼────────────────────────────────────────────────────┤
│ event_updated      │ Event status changed                               │
│                    │ Payload: EventQueue                                │
├────────────────────┼────────────────────────────────────────────────────┤
│ clipboard_update   │ Navigation state changed                           │
│                    │ Payload: ClipboardState                            │
├────────────────────┼────────────────────────────────────────────────────┤
│ ticker_item        │ News item added                                    │
│                    │ Payload: TickerItem                                │
├────────────────────┼────────────────────────────────────────────────────┤
│ auto_paused        │ Game auto-paused for attention                     │
│                    │ Payload: { reason, event_id }                      │
├────────────────────┼────────────────────────────────────────────────────┤
│ error              │ Error notification                                 │
│                    │ Payload: { error_message }                         │
└────────────────────┴────────────────────────────────────────────────────┘
```

### Frontend → Backend (Inbound)

```
┌────────────────────┬────────────────────────────────────────────────────┐
│ Message Type       │ Purpose                                            │
├────────────────────┼────────────────────────────────────────────────────┤
│ pause              │ Pause time progression                             │
├────────────────────┼────────────────────────────────────────────────────┤
│ play               │ Resume time (payload: { speed })                   │
├────────────────────┼────────────────────────────────────────────────────┤
│ set_speed          │ Change time speed (payload: { speed })             │
├────────────────────┼────────────────────────────────────────────────────┤
│ select_tab         │ Navigate clipboard (payload: { tab })              │
├────────────────────┼────────────────────────────────────────────────────┤
│ attend_event       │ Mark event attended (payload: { event_id })        │
├────────────────────┼────────────────────────────────────────────────────┤
│ dismiss_event      │ Dismiss event (payload: { event_id })              │
├────────────────────┼────────────────────────────────────────────────────┤
│ run_practice       │ Execute practice (payload: { event_id, allocation })│
├────────────────────┼────────────────────────────────────────────────────┤
│ play_game          │ Play game manually                                 │
├────────────────────┼────────────────────────────────────────────────────┤
│ sim_game           │ Simulate game                                      │
├────────────────────┼────────────────────────────────────────────────────┤
│ go_back            │ Navigate back                                      │
├────────────────────┼────────────────────────────────────────────────────┤
│ request_sync       │ Request full state resync                          │
└────────────────────┴────────────────────────────────────────────────────┘
```

---

## State Sync Pattern

The system uses a dual-channel approach for reliability:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     WebSocket + REST Dual-Channel                        │
└─────────────────────────────────────────────────────────────────────────┘

INITIAL LOAD:
┌─────────────┐  connect   ┌─────────────┐  state_sync  ┌─────────────┐
│  Frontend   │ ─────────▶ │  WebSocket  │ ────────────▶│  Store      │
│             │            │  Handler    │              │             │
└─────────────┘            └─────────────┘              └─────────────┘

CONTINUOUS UPDATES:
┌─────────────┐  tick()    ┌─────────────┐  WS message  ┌─────────────┐
│  Tick Loop  │ ─────────▶ │  Service    │ ────────────▶│  Store      │
│  (20/sec)   │            │  (throttle) │  (10/sec)    │             │
└─────────────┘            └─────────────┘              └─────────────┘

USER ACTIONS (when blocking needed):
┌─────────────┐  POST      ┌─────────────┐  Response    ┌─────────────┐
│  Frontend   │ ─────────▶ │  REST API   │ ────────────▶│  Store      │
│             │            │  (wait)     │              │ (update)    │
└─────────────┘            └─────────────┘              └─────────────┘
                                │
                                │ Also triggers WS broadcast
                                ▼
                    Other connected clients receive update
```

### Why Dual-Channel?

| Operation | Channel | Reason |
|-----------|---------|--------|
| Time ticks | WebSocket | High frequency, fire-and-forget |
| Event notifications | WebSocket | Real-time feedback |
| Advance day | REST | Must wait for events to generate |
| Run practice | REST | Returns development gains |
| Sim game | REST | Returns game result |
| Contract operations | REST | Must confirm success/failure |

---

## Zustand Store Structure

```typescript
interface ManagementStore {
  // === Connection State ===
  isConnected: boolean;        // WebSocket connected?
  isLoading: boolean;          // Initial load or action in progress
  error: string | null;        // Last error message

  // === Session State ===
  franchiseId: string | null;  // Current franchise UUID
  state: LeagueState | null;   // Full backend state mirror

  // === Derived State (denormalized for performance) ===
  calendar: CalendarState | null;    // state.calendar
  events: EventQueue | null;         // state.events
  clipboard: ClipboardState | null;  // state.clipboard
  ticker: TickerFeed | null;         // state.ticker

  // === UI-Only State ===
  showAutoPauseModal: boolean;   // Show pause overlay?
  autoPauseReason: string | null;
  autoPauseEventId: string | null;
  journalVersion: number;        // Incremented when journal updates
}
```

### State Update Flow

```
WebSocket Message Arrives
         │
         ▼
handleMessage() in hook
         │
         ▼
Store action called (e.g., updateCalendar)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  set({                                                               │
│    calendar: newCalendar,                                            │
│    state: { ...state, calendar: newCalendar }  // Keep in sync      │
│  })                                                                  │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
React components re-render (via Zustand selectors)
```

---

## Event → Workspace Conversion

Events become workspace items for display:

```typescript
function eventToWorkspace(event: ManagementEvent): WorkspaceItem {
  return {
    id: event.id,
    type: eventTypeToWorkspaceType(event.event_type),  // 'practice' | 'game' | etc.
    title: event.title,
    subtitle: event.description,
    priority: mapPriority(event.priority),
    status: mapStatus(event.status),
    timestamp: event.scheduled_for,
    deadline: event.deadline,
    // ... additional fields
  };
}
```

### Workspace Item Lifecycle

```
Event activated in backend
         │
         ▼
WS: event_added message
         │
         ▼
Store: addEvent(event)
         │
         ▼
ManagementV2.tsx: useEffect detects new event
         │
         ▼
eventToWorkspace(event) conversion
         │
         ▼
WorkspaceItem rendered in grid
         │
         ├──▶ User clicks card → WorkspaceItem expands to pane
         │
         ├──▶ User attends event → REST API → Event marked ATTENDED
         │
         └──▶ User dismisses → REST API → Event marked DISMISSED
```

---

## Complete Request Flow Example

### Advance Day Button Click

```
1. USER ACTION
   └─▶ Click "Advance Day" button in ManagementV2

2. FRONTEND
   └─▶ managementClient.advanceDay(franchiseId)
   └─▶ POST /api/v1/management/franchise/{id}/advance-day

3. API ROUTER
   └─▶ @router.post("/{franchise_id}/advance-day")
   └─▶ Gets ManagementService from registry
   └─▶ Calls service.advance_day()

4. MANAGEMENT SERVICE
   └─▶ state.pause()  // Stop tick loop
   └─▶ state.calendar.advance_day()  // Move to next day
   └─▶ _generator.generate_random_day_events()  // Generate new events
   └─▶ For each event: state.events.add(event)
   └─▶ Build response with new events

5. API RESPONSE
   └─▶ Returns AdvanceDayResponse:
       {
         new_date: "2024-09-10",
         phase: "REGULAR_SEASON",
         new_events: [...],
         is_game_day: false
       }

6. FRONTEND RECEIVES
   └─▶ managementStore.setEvents(response.new_events)
   └─▶ UI re-renders with new date and events

7. WEBSOCKET BROADCAST (parallel)
   └─▶ calendar_update sent to all connected clients
   └─▶ event_added sent for each new event
```

---

## See Also

- [backend.md](backend.md) - Complete backend module reference
- [api.md](api.md) - REST and WebSocket API reference
- [frontend.md](frontend.md) - React component overview
- [event-architecture.md](event-architecture.md) - Event → Workspace → Pane flow
