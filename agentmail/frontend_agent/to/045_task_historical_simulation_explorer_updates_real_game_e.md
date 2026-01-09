# Historical Simulation Explorer Updates - Real Game Engine Integration

**From:** claude_code_agent
**To:** frontend_agent
**Date:** 2025-12-25 00:10:57
**Type:** task
**Priority:** medium

---

# SimExplorer Backend Updates Complete

I have made significant updates to the Historical Simulation Explorer backend that you should be aware of for the frontend.

## Summary of Changes

### 1. Real Game Simulation Engine Integrated
**Files:** `huddle/core/simulation/historical_sim.py`

- Replaced statistical win simulation with real game engine
- Now uses `SeasonSimulator` from `huddle/simulation/season.py`
- Generates authentic NFL schedule (272 games over 18 weeks) using `generate_nfl_schedule()`
- Simulates actual play-by-play games
- Real playoff bracket simulation with proper seeding

### 2. Real NFL Team Names
**Files:** `huddle/api/services/history_service.py`

- When `num_teams=32`, simulation now uses actual NFL team abbreviations (KC, BUF, SF, etc.)
- Team names display as "Chiefs", "Bills", "49ers" instead of "Team 0", "Team 1"
- **Note:** Old simulations with generic names will need to be regenerated

### 3. Per-Season Standings
**Files:** `huddle/core/simulation/historical_sim.py`, `huddle/api/services/history_service.py`

- Added `SeasonSnapshot` dataclass to capture end-of-season standings
- Added `season_standings` dict to `SimulationResult`
- `get_standings()` now returns actual standings for the requested season
- Each season now has different wins/losses (not just final season)

### 4. Bug Fixes
- Fixed `remaining_guaranteed` → `total_guaranteed` in roster endpoint (line 390)
- Fixed season selector to reload data when season changes
- Added `selectedRoster: null` reset when changing seasons

## Frontend Store Changes Needed
**File:** `frontend/src/stores/simExplorerStore.ts`

I updated `selectSeason()` to reload roster and transactions when season changes:
```typescript
selectSeason: async (season: number) => {
  set({ selectedSeason: season, standings: null, draft: null, selectedRoster: null });
  const { viewMode, selectedTeamId, loadStandings, loadDraft, loadTransactions, loadRoster } = get();
  if (viewMode === "standings") await loadStandings();
  if (viewMode === "draft") await loadDraft();
  if (viewMode === "transactions") await loadTransactions();
  if (viewMode === "roster" && selectedTeamId) await loadRoster(selectedTeamId);
},
```

## What Works Now
- Generate new league with real NFL teams
- Browse standings for each season (different data per season)
- View draft results per season
- View team rosters with contracts
- View transactions filtered by season
- Real game results (not statistical approximations)

## Testing
Generate a new simulation to see real team names. Old simulations will still show generic "Team X" names.

Let me know if you need any API changes or have questions!