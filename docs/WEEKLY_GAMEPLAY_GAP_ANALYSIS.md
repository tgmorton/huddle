# Weekly Gameplay Gap Analysis

**Goal**: Identify what's needed to run a complete week of football management, from Tuesday through game day.

---

## Executive Summary

The backend management system is **remarkably complete** - calendar, events, practices, and game simulation are all implemented. The frontend has **both content viewing AND decision-making panes built** - but they're not yet connected.

**Critical Path to Playable Week:**
1. ~~Add time control UI~~ → **Day-by-day design** (Advance Day button only)
2. Wire event clicks → open correct workspace pane
3. Event blocking logic (must handle before advancing)
4. Test end-to-end flow: Tuesday → Sunday game

**Key Finding**: We're closer than expected. All workspace panes (Practice, Game, Scout, Contract, Deadline) are functional - we just need the routing/wiring to connect events to them.

**Design Change (Dec 2024)**: Abandoning real-time (play/pause/speed) in favor of manual day-by-day advancement. User clicks "Advance Day" to progress, must handle blocking events first.

---

## Backend Status: What's Built

### Fully Implemented (Ready to Use)

| System | Location | Notes |
|--------|----------|-------|
| Calendar & Time | `management/calendar.py` | Full NFL season, phases, speed controls |
| Event System | `management/events.py` | 13 categories, priorities, lifecycle, arcs |
| Event Generator | `management/generators.py` | Auto-spawns practices, games, FA, trades |
| League State | `management/league.py` | Main coordinator, tick loop, auto-pause |
| Practice System | `league.py:run_practice()` | Playbook/development/gameprep allocation |
| Game Simulation | `league.py:sim_game()` | Calls v2 sim, returns results |
| News Ticker | `management/ticker.py` | 14 categories, aging, clickable items |
| Clipboard/Tabs | `management/clipboard.py` | 15 tabs with navigation |

### API Endpoints (All Working)

```
Time Control:
  POST /franchise/{id}/pause
  POST /franchise/{id}/play
  POST /franchise/{id}/speed
  POST /franchise/{id}/advance-day
  POST /franchise/{id}/advance-to-game

Events:
  GET  /franchise/{id}/events
  POST /franchise/{id}/events/attend
  POST /franchise/{id}/events/dismiss

Actions:
  POST /franchise/{id}/run-practice
  POST /franchise/{id}/sim-game

Data:
  GET  /franchise/{id}/financials
  GET  /franchise/{id}/contracts
  GET  /franchise/{id}/free-agents
  GET  /franchise/{id}/draft-prospects
  GET  /franchise/{id}/playbook-mastery
  GET  /franchise/{id}/development
  GET  /franchise/{id}/weekly-development
  GET  /franchise/{id}/week-journal
```

---

## Frontend Status: What's Built

### Content Components (Viewing Data) - Mostly Complete

| Component | Status | Data Source |
|-----------|--------|-------------|
| RosterContent | **Complete** | `adminApi.getTeamRoster()` |
| ScheduleContent | **Complete** | Real schedule data |
| DepthChartContent | **Complete** | Real depth chart |
| StandingsContent | **Complete** | All divisions |
| ContractsContent | **Complete** | Full contract details |
| SalaryCapContent | **Complete** | 6-year projections |
| FreeAgentsContent | **Complete** | Filtered listing |
| DraftClassContent | **Complete** | Prospects with scouting |
| PlaybookContent | **Complete** | Play mastery tracking |
| DevelopmentContent | **Complete** | Attribute potentials |
| CoachesContent | **Stub** | Not implemented |

### Workspace Panes (Making Decisions) - Mostly Complete

| Pane | Status | Notes |
|------|--------|-------|
| PlayerPane | **Complete** | Uses shared PlayerView |
| ProspectPane | **Complete** | Full prospect details |
| GamePane | **Complete** | Sim game, shows results |
| DeadlinePane | **Complete** | Injury decisions |
| ContractPane | **Complete** | Trade/contract decisions (demo mode) |
| ScoutPane | **Complete** | Opponent intel review |
| PracticePane | **Complete** | Sliders, intensity, API call, results |
| MeetingPane | **Needs Review** | Not fully examined |
| NewsPane | **Stub** | Minimal implementation |

### Panels (Tab Containers)

| Panel | Status | Notes |
|-------|--------|-------|
| WeekPanel | **Complete** | Journal, day timeline, advance buttons |
| FinancesPanel | **Complete** | SalaryCap + Contracts tabs |
| PersonnelPanel | **Partial** | Coaches tab is stub |
| TransactionsPanel | **Partial** | Trades/Waivers tabs are stubs |
| DraftPanel | **Partial** | Board/Scouts tabs are stubs |
| ReferencePanel | **Complete** | Panel router |

---

## Gap Analysis: What's Missing for Weekly Play

### Priority 1: Critical Path (Must Have)

#### 1.1 Practice Allocation UI
- **Backend**: `run_practice()` accepts `playbook_pct`, `development_pct`, `game_prep_pct`
- **Frontend**: **COMPLETE** - PracticePane has sliders, intensity, API call, results display
- **Work**: None - just needs to be wired to PRACTICE events

#### 1.2 Time Control in Main UI
- **Backend**: Pause/play/speed endpoints exist
- **Frontend Gap**: No visible time control buttons in ManagementV2
- **Work**: Add play/pause button and speed selector to header or WeekPanel

#### 1.3 Event Modal System
- **Backend**: Events have `display_mode: MODAL | PANE | TICKER`
- **Frontend Gap**: ManagementEventModal exists but may not handle all event types
- **Work**: Ensure modal renders for MODAL-type events, routes correctly

#### 1.4 Auto-Pause Handling
- **Backend**: Auto-pauses for critical events and game days
- **Frontend Gap**: Store has `showAutoPauseModal` but UI implementation unclear
- **Work**: Wire up auto-pause modal to show when backend triggers pause

### Priority 2: Week Flow (Should Have)

#### 2.1 Event Attend/Dismiss Flow
- **Backend**: `attend_event()` and `dismiss_event()` endpoints
- **Frontend**: Events tab shows list, but clicking needs to open correct pane
- **Work**: Wire event click → open workspace pane with event context

#### 2.2 Week Journal Display
- **Backend**: `get_week_journal()` returns day-by-day entries
- **Frontend**: WeekPanel displays journal but needs validation
- **Work**: Verify journal entries populate correctly after actions

#### 2.3 Ticker Feed Display
- **Backend**: Ticker items generated, have priorities/categories
- **Frontend**: TickerFeed exists in store but display unclear
- **Work**: Add scrolling ticker to UI (header or footer)

### Priority 3: Polish (Nice to Have)

#### 3.1 Trades/Waivers UI
- **Backend**: Trade events generated, trade offer factory exists
- **Frontend**: TransactionsPanel has stub tabs
- **Work**: Build trade offer review UI, waiver wire browser

#### 3.2 Scout Management
- **Backend**: Scouting events exist
- **Frontend**: DraftPanel "Scouts" tab is stub
- **Work**: Build scout assignment UI

#### 3.3 Coaching Staff
- **Backend**: Staff events category exists
- **Frontend**: CoachesContent is stub
- **Work**: Build coaches listing and management

---

## Recommended Implementation Order

### Phase 1: Minimum Viable Week (Est. 3-4 tasks)

```
1. Day-by-day UI (simplified from real-time)
   - Current date/week display in header
   - "Advance Day" button (calls advanceDay endpoint)
   - "Advance to Game" button (skip to Sunday)
   - NO play/pause/speed controls

2. Wire event clicks to workspace panes
   - PRACTICE events → PracticePane (already built!)
   - GAME events → GamePane (already built!)
   - CONTRACT events → ContractPane (already built!)
   - SCOUTING events → ScoutPane (already built!)
   - This is mostly routing logic in ManagementV2.tsx

3. Event blocking logic
   - Define which events block day advancement
   - Show "must handle X events" if trying to advance with blockers
   - Allow skip/dismiss for non-critical events

4. Test full loop
   - Create franchise
   - Click Advance Day → practices generate
   - Click practice event → pane opens
   - Set allocation, run practice
   - Advance to game day
   - Sim game
   - View results in journal
```

**Key Insight**: All workspace panes are built - we just need to connect events to them.

### Phase 2: Enhanced Decision-Making

```
6. Trade offer review pane
7. Free agent negotiation pane
8. Contract extension pane
9. Injury decision pane (already exists, verify)
10. Ticker feed display
```

### Phase 3: Scouting & Draft

```
11. Scout assignment UI
12. Draft board UI
13. Combine/Pro Day event handling
```

---

## Data Flow: Complete Week Example

```
TUESDAY (Day 1)
├── Calendar: current_date = "2024-09-03", week = 1
├── Auto-Generated Events:
│   ├── PRACTICE (9:00 AM) - requires allocation decision
│   └── SCOUTING (2:00 PM) - opponent intel available
├── User Actions:
│   ├── Open Practice event → PracticePane
│   ├── Set allocation (50% playbook, 30% dev, 20% prep)
│   ├── Submit → run_practice() → journal entry created
│   └── Open Scout event → ScoutPane → review intel

WEDNESDAY-SATURDAY (Days 2-5)
├── Similar practice events each day
├── Possible events:
│   ├── TRADE offer from other team
│   ├── CONTRACT extension eligible
│   ├── INJURY report
│   └── TICKER items (league news)

SUNDAY (Day 7 - Game Day)
├── Auto-Pause triggers (game day)
├── GAME event becomes active
├── User clicks "Sim Game" → sim_game()
├── Results displayed in GamePane
├── Journal updated with outcome
├── Week 2 begins...
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `ManagementV2.tsx` | Add time controls header, wire event→pane routing |
| `ManagementEventModal.tsx` | Verify modal displays for MODAL-type events |
| `WorkshopPanel.tsx` | Make event clicks open correct pane |
| `managementStore.ts` | Already has auto-pause state (ready) |
| `ManagementV2.css` | Styles for time controls header |

**Already Complete (No Changes Needed):**
- `PracticePane.tsx` - Full allocation UI with API integration
- `GamePane.tsx` - Game sim with results display
- `ContractPane.tsx` - Decision UI with journal integration
- `ScoutPane.tsx` - Intel review pane
- `DeadlinePane.tsx` - Injury decisions
- `managementClient.ts` - All API methods exist

---

## API Client Status

**`managementClient.ts` is COMPLETE** - All required methods exist:

```typescript
// Time control ✅
pause(franchiseId)
play(franchiseId, speed?)
setSpeed(franchiseId, speed)
advanceDay(franchiseId) → DayAdvanceResponse
advanceToGame(franchiseId)

// Actions ✅
runPractice(franchiseId, { event_id, playbook, development, game_prep })
simGame(franchiseId, eventId) → GameResult

// Events ✅
getEvents(franchiseId)
attendEvent(franchiseId, eventId)
dismissEvent(franchiseId, eventId)

// Journal ✅
getWeekJournal(franchiseId)
addJournalEntry(franchiseId, entry)

// Development ✅
getPlaybookMastery(franchiseId)
getDevelopment(franchiseId)
getWeeklyDevelopment(franchiseId)

// Draft ✅
getDraftProspects(franchiseId)
getProspect(franchiseId, prospectId)
```

**No new API methods needed** - the frontend just needs to wire existing methods to UI.

---

## Testing Checklist

```
[ ] Create new franchise
[ ] See initial events in Events tab
[ ] Click practice event → PracticePane opens
[ ] Set allocation and submit → journal updates
[ ] Advance day → new events generate
[ ] See ticker items appear
[ ] Auto-pause triggers on game day
[ ] Sim game → results display
[ ] Journal shows week summary
[ ] Advance to week 2 → calendar updates
```

---

## Conclusion

**Both backend AND frontend are further along than expected.**

Backend is **production-ready**:
- Full calendar with NFL season phases
- Event system with 13 categories and auto-generation
- Practice execution with playbook/development/gameprep
- Game simulation integration
- News ticker and journal systems

Frontend workspace panes are **built and functional**:
- PracticePane: Allocation sliders, intensity, API call, results
- GamePane: Sim button, score display, stats
- ScoutPane: Opponent intel review
- ContractPane: Decision UI with journal
- DeadlinePane: Injury decisions

**What's missing is the wiring:**
1. Day advancement UI (Advance Day / Advance to Game buttons)
2. Event click → pane routing
3. Event blocking logic (what must be handled before advancing)

**Estimated effort**: 1-2 days of focused wiring work to get a playable week loop.

**Note**: Day-by-day design is simpler than real-time - no WebSocket tick loop, no speed controls, just button clicks to advance.
