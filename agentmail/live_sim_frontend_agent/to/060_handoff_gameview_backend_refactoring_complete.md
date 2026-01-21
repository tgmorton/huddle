# Handoff: GameView Backend Refactoring Complete

**From:** frontend_agent
**To:** live_sim_frontend_agent
**Date:** 2026-01-19
**Type:** task
**Subject:** GameView Backend Work Complete - Frontend Wiring Needed

---

## Summary

I've completed the backend refactoring for coach mode. The API is ready - frontend needs to wire `useCoachAPI.ts` to the real endpoints.

---

## What Was Done

### 1. Refactored coach_mode.py (1850 -> ~1525 lines) [frontend_agent]

Made it a thin wrapper around `GameManager` instead of duplicating game logic:

- `execute_play()` endpoint now calls `manager.execute_play_by_code()`
- `execute_special()` endpoint calls `manager.execute_special_teams()`
- `/step` endpoint calls `manager.step_auto_play()`
- Auto-play loop uses `manager.handle_drive_end()` for possession changes

### 2. Added Public Methods to GameManager [frontend_agent]

New methods in `huddle/game/manager.py`:

```python
def execute_play_by_code(self, play_code: str, shotgun: bool = True) -> dict
def execute_special_teams(self, play_type: str, go_for_two: bool = False) -> dict
def step_auto_play(self) -> dict
def handle_drive_end(self, reason: str) -> dict
```

### 3. Fixed Field Position Bugs [frontend_agent]

- **Punt LOS**: After punt, field position now shows receiver's yard line (not punter's)
- **Direction flip**: `SimulcastView.tsx` now computes field direction based on possession AND quarter (flips at halftime)

### 4. Fixed Player Positioning Bug [live_sim_agent]

Games via coach mode API were showing constant sacks/safeties because `execute_play_by_code()` wasn't repositioning players to the actual LOS - they were stuck at `los_y=0` (the endzone).

**Fix:** Added `_reposition_players()` method to `manager.py`, called in both `execute_play_by_code()` and `execute_play_by_code_with_frames()`.

### 5. Fixed Coordinate System Mismatch [live_sim_agent]

Players weren't appearing in PlayCanvas visualization because the backend was sending absolute field coordinates (e.g., `y=20` for a player at the 20-yard line), but `PlayCanvas.tsx` expects LOS-relative coordinates (`y=0` at LOS, negative=backfield, positive=downfield).

**Fix:** Modified `coach_mode.py` to convert all coordinates to LOS-relative format:
- Player positions in `_player_to_frame_dict()`
- Route target coordinates
- Pursuit target coordinates
- Ball position in `_collect_frame()`

---

## What You Need to Do

### P0: Wire useCoachAPI.ts to Real Endpoints

The hook at `hooks/useCoachAPI.ts` is currently a stub:
```typescript
// Line 56-66: "For now, skip the API call since it requires UUIDs"
console.log(`Starting game: ${homeTeam} vs ${awayTeam} (mock mode)`);
setGameId(`mock_${Date.now()}`);
```

Endpoints to wire:

| Hook Method | Backend Endpoint | Notes |
|-------------|------------------|-------|
| `startGame()` | `POST /coach/start` | Returns `game_id`, creates GameManager |
| `callPlay()` | `POST /coach/{game_id}/play` | Body: `{play_code, shotgun}` |
| `callSpecialTeams()` | `POST /coach/{game_id}/special` | Body: `{play_type, go_for_two?}` |
| `getAvailablePlays()` | `GET /coach/{game_id}/plays` | Returns play options |

### P1: Extract useGameState Hook

GameView.tsx is 777 lines. Suggested extraction:
- `useGameState.ts` - unified state (situation, drives, results)
- Eliminates dual coach/spectator state trees

### P2: Remove Mock Fallbacks

Once wired, replace:
```typescript
const situation = coachSituation || MOCK_SITUATION;
```
with explicit errors in dev mode.

---

## Key Files

| File | What It Does |
|------|--------------|
| `huddle/api/routers/coach_mode.py` | REST API for coach mode |
| `huddle/game/manager.py` | GameManager (single source of truth) |
| `frontend/src/components/GameView/hooks/useCoachAPI.ts` | **Needs wiring** |
| `frontend/src/components/GameView/views/SimulcastView.tsx` | Field direction fix done |
| `frontend/src/components/GameView/components/DriveFieldView.tsx` | Field visualization |

---

## Testing Notes

Run a game via the API to verify:
```bash
# Start game
curl -X POST http://localhost:8000/coach/start \
  -H "Content-Type: application/json" \
  -d '{"home_team_id": "...", "away_team_id": "..."}'

# Execute play
curl -X POST http://localhost:8000/coach/{game_id}/play \
  -H "Content-Type: application/json" \
  -d '{"play_code": "PASS_SLANT", "shotgun": true}'
```

Backend tests all pass (33 tests).

---

## Questions I Didn't Resolve

1. **Team IDs**: The API expects UUIDs but frontend has team names. May need a team lookup endpoint or accept names in `/start`.
2. **Frame collection**: Currently enabled by default for viz. May want a flag to disable for performance.

---

Let me know if you have questions about any of this. I'm returning to management frontend work.

---
