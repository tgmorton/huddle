# SimExplorer Feature - Complete Changelog

Summary of all work done on the Historical Simulation Explorer.

---

## Backend: New API Endpoints

**Router:** `huddle/api/routers/history.py`
**Base URL:** `http://localhost:8000/api/v1/history`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/simulate` | POST | Run simulation |
| `/simulate-stream` | GET | Run with SSE progress updates |
| `/simulations` | GET | List all simulations |
| `/simulations/{sim_id}` | GET | Get full simulation data |
| `/simulations/{sim_id}` | DELETE | Delete simulation |
| `/simulations/{sim_id}/seasons/{season}/teams` | GET | Teams for a season |
| `/simulations/{sim_id}/seasons/{season}/standings` | GET | Standings for season |
| `/simulations/{sim_id}/seasons/{season}/draft` | GET | Draft picks for season |
| `/simulations/{sim_id}/transactions` | GET | Transactions (filterable) |
| `/simulations/{sim_id}/teams/{team_id}/roster` | GET | Team roster |

---

## Backend: Real Game Simulation Engine

**File:** `huddle/core/simulation/historical_sim.py`

- Integrated `SeasonSimulator` from `huddle/simulation/season.py`
- Uses `generate_nfl_schedule()` for authentic 272-game NFL schedule
- Real play-by-play game simulation (not statistical approximation)
- Proper playoff bracket simulation with seeding

---

## Backend: Real NFL Teams

**File:** `huddle/api/services/history_service.py`

When `num_teams=32`:
- Uses actual NFL team abbreviations: KC, BUF, SF, PHI, etc.
- Real team names: Chiefs, Bills, 49ers, Eagles
- Proper division/conference structure

---

## Backend: Per-Season Standings

**Files:** `huddle/core/simulation/historical_sim.py`, `huddle/api/services/history_service.py`

- Added `SeasonSnapshot` dataclass
- Added `season_standings` dict to `SimulationResult`
- Each season now has its own wins/losses/standings
- Standings endpoint returns correct data for requested season

---

## Backend: Bug Fixes

1. **Contract attribute error** - Changed `remaining_guaranteed` to `total_guaranteed` (line 390)
2. **Draft endpoint** - Fixed navigation through `DraftState.rounds[].order[]` structure
3. **Transaction endpoint** - Fixed `transaction_id` vs `id` attribute
4. **SSE streaming** - Fixed datetime serialization with `model_dump(mode='json')`

---

## Frontend: New Files

### API Client
**File:** `frontend/src/api/historyClient.ts`

```typescript
// Functions
runSimulation(config)
runSimulationWithProgress(config, onProgress)  // SSE streaming
listSimulations()
getSimulation(simId)
getStandings(simId, season)
getDraft(simId, season)
getTransactions(simId, options)
getTeamRoster(simId, teamId, season)

// Types exported
SimulationConfig, SimulationSummary, FullSimulationData,
TeamSnapshot, TeamRoster, PlayerSnapshot, StandingsData,
DraftData, TransactionLog, ProgressEvent
```

### Zustand Store
**File:** `frontend/src/stores/simExplorerStore.ts`

State:
- `simulations` - list of SimulationSummary
- `currentSimulation` - FullSimulationData | null
- `selectedSeason`, `selectedTeamId` - navigation
- `viewMode` - 'overview' | 'standings' | 'roster' | 'draft' | 'transactions'
- `standings`, `draft`, `transactions`, `selectedRoster` - view data
- `isLoading`, `isGenerating`, `progressMessage`, `error` - UI state

### Component
**File:** `frontend/src/components/SimExplorer/SimExplorer.tsx`

- Header with "Generate New League" button + progress indicator
- Left sidebar: Simulation list, Season list, Team list
- Main area: View tabs + content views
- Sub-components: OverviewView, StandingsView, RosterView, DraftView, TransactionsView

### Styles
**File:** `frontend/src/components/SimExplorer/SimExplorer.css`

- Uses ManagementV2 design tokens
- Dark theme with amber accents (#d4a574)
- Berkeley Mono font
- Pulse animation for progress messages

---

## Frontend: Store Fix

**File:** `frontend/src/stores/simExplorerStore.ts`

Updated `selectSeason()` to reload all relevant data:
```typescript
selectSeason: async (season: number) => {
  set({ selectedSeason: season, standings: null, draft: null, selectedRoster: null });
  const { viewMode, selectedTeamId, loadStandings, loadDraft, loadTransactions, loadRoster } = get();
  if (viewMode === 'standings') await loadStandings();
  if (viewMode === 'draft') await loadDraft();
  if (viewMode === 'transactions') await loadTransactions();
  if (viewMode === 'roster' && selectedTeamId) await loadRoster(selectedTeamId);
},
```

---

## SSE Progress Streaming

The `/simulate-stream` endpoint returns Server-Sent Events:

```typescript
interface ProgressEvent {
  type: 'progress' | 'complete' | 'error';
  message?: string;   // "Simulating 2023 Season..."
  summary?: SimulationSummary;  // on complete
}
```

Frontend displays `progressMessage` with pulse animation during generation.

---

## Known Limitations

1. **Roster is final state only** - All seasons show the same (final) roster
2. **Simulations in memory** - Lost on server restart
3. **Old simulations** - Created before NFL teams fix will show "Team 0" names

---

## Route Registration

Ensure in `frontend/src/App.tsx`:
```tsx
<Route path="/sim-explorer" element={<SimExplorer />} />
```

Ensure in `huddle/api/routers/__init__.py`:
```python
from huddle.api.routers import history
# ... router registration
```
