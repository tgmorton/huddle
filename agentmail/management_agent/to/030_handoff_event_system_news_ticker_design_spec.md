# Event System & News Ticker Design Spec

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-20 23:43:41
**Type:** handoff

---

# Event System & News Ticker Design

Documenting the full vision for how events and news work in ManagementV2.

## Day-Based Progression

- No real-time simulation - user clicks **Next Day** to advance
- Each day advance triggers event generation and news refresh
- Events are day-bounded (scheduled for specific week/day)

## Event Display Modes

Events have a `display_mode` field:

| Mode | Behavior |
|------|----------|
| `PANE` | Opens as workspace item (default) - user can interact, dismiss, or defer |
| `MODAL` | Blocking overlay - requires immediate attention (e.g., critical deadline, game result) |
| `TICKER` | Info only - appears in news ticker, no workspace item |

## Event Flow

1. User clicks **Next Day**
2. Backend advances calendar, generates events for new day
3. Events sync to frontend store via WebSocket
4. Frontend sorts events by display_mode:
   - MODAL events → show first modal, queue others
   - PANE events → add to workspace as items
   - TICKER events → populate news ticker
5. User handles events (attend, dismiss, defer)
6. Completed events removed from workspace

## Event Arcs

Events can be part of arcs (multi-step storylines):

- `arc_id` - groups related events
- `triggers` - conditions that spawn follow-up events
- Example: Contract negotiation arc (initial offer → counter → accept/reject → announcement)

## News Ticker

### Current State
- Scrolling ticker in top bar (center column)
- Pauses on hover, clickable pause button
- Clicking news item adds it to workspace

### Design Vision
- **Dynamic news of the day** - refreshes each day advance
- Generated from real game events:
  - Player transactions (trades, drops, signings of significance)
  - Game results (big wins/losses)
  - Record updates after games
  - League announcements
- Only significant events make the ticker (not every minor move)

### Future: News Quickview
- Timeline view of all news
- Filterable by category (transactions, games, league)
- Accessible from ticker or dedicated panel

## Frontend Implementation Status

✅ Completed:
- `eventToWorkspace.ts` - converts ManagementEvent to WorkspaceItem
- `ManagementEventModal` - modal overlay for MODAL events
- Store sync effect - wires pending events to workspace
- `display_mode` field on ManagementEvent type
- Top bar redesign with ticker in center
- Ticker pause functionality
- Next Day button

⏳ Pending:
- Wire ticker to real news from store (currently DEMO_NEWS)
- News quickview panel
- Event arc UI (showing arc progress)

## Backend Requirements

- News generation system (triggered by game events)
- News endpoint or WebSocket field for daily news
- Event arc management (tracking arc state, spawning follow-ups)

Let me know if you need any clarification on the frontend implementation or have questions about the design.