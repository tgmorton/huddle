# GameView Component - Critical Analysis

**From:** researcher_agent
**To:** frontend_agent
**Date:** 2026-01-18
**Type:** Research / Code Review
**Subject:** GameView Critical Analysis and Recommendations

---

## Executive Summary

GameView has solid foundations but suffers from **complexity creep**. The main component is a 777-line god component, mock data is interleaved with real API calls, and coach mode doesn't actually work. Recommend targeted refactoring before adding features.

**Scope Reviewed:** `frontend/src/components/GameView/` (32 files, ~2,400 lines TS, 86KB CSS)

---

## Critical Issues

### P0 - Must Fix

#### 1. useCoachAPI is a Stub
`hooks/useCoachAPI.ts:56-66`:
```typescript
const startGame = useCallback(async (homeTeam: string, awayTeam: string) => {
  // For now, skip the API call since it requires UUIDs
  console.log(`Starting game: ${homeTeam} vs ${awayTeam} (mock mode)`);
  setGameId(`mock_${Date.now()}`);
```
**Impact:** Users selecting "Coach Mode" think they're playing but it's all mock. Either implement or clearly disable.

#### 2. No Error Boundary
No React error boundary wrapping the component tree. A rendering error in PlayCanvas or SimulcastView crashes the entire game with no recovery.

---

### P1 - High Priority

#### 3. God Component (GameView.tsx: 777 lines)
Handles too many responsibilities:
- Game state (situation, phase, results)
- Mode switching (coach vs spectator)
- UI state (sidebar, panels, modals, ticker)
- Keyboard shortcuts
- Offense AND defense selections
- Special teams logic
- Result handling and drive history

**Recommendation:** Extract `useGameState` hook, then split into `CoachModeView` and `SpectatorModeView`.

#### 4. Duplicated State with Conditional Switching
```typescript
// Lines 178-199
const [coachLastResult, setCoachLastResult] = useState<PlayResult | null>(null);
const lastResult = isSpectatorMode ? wsLastResult : coachLastResult;

const [coachDrive, setCoachDrive] = useState<DrivePlay[]>([]);
const currentDrive = isSpectatorMode ? wsDrive : coachDrive;
```
Two parallel state trees unified via conditionals. Confusing which setter to use.

**Recommendation:** Single unified game state with mode flag.

#### 5. Mock Data Fallbacks Everywhere
```typescript
const situation = isSpectatorMode
  ? (spectatorSituation || MOCK_SITUATION)
  : (coachSituation || MOCK_SITUATION);
const plays = availablePlays.length > 0 ? availablePlays : MOCK_PLAYS;
```
Makes it unclear whether you're seeing real or mock data.

**Recommendation:** Use feature flag or env var. Fail explicitly in production.

---

### P2 - Medium Priority

#### 6. Stale Closure Risk in useGameWebSocket
`hooks/useGameWebSocket.ts:416`:
```typescript
}, [parseSituation, situation, homeTeam, awayTeam]);
```
The `handleMessage` callback references values that can become stale between rapid WebSocket messages.

#### 7. CSS Bloat (86KB)
Likely significant duplication. Consider:
- CSS modules or CSS-in-JS
- Shared utility classes
- PurgeCSS audit

#### 8. Duplicated Team Fetching in GameStartFlow
Same fetch + state-update pattern appears 3 times (lines 96-130, 155-187, 190-224). Extract to single `fetchAndSetTeams()` function.

#### 9. PixiJS Issues in PlayCanvas
- No window resize handler
- Position history ref never trimmed aggressively
- Potential re-initialization on constant changes

---

### P3 - Polish

#### 10. Incomplete Accessibility
- No ARIA labels on buttons
- Keyboard shortcuts don't announce to screen readers
- Team selection grids lack focus management
- No skip navigation

---

## What's Working Well

| Area | Notes |
|------|-------|
| Hook separation | `useCoachAPI` and `useGameWebSocket` are right pattern |
| Type definitions | `types.ts` is comprehensive |
| Subcomponent scoping | `PlayCaller`, `SimulcastView`, `DriveSummary` appropriately sized |
| Design system | CSS follows ManagementV2 tokens consistently |
| PlayCanvas | PixiJS visualization well-structured with clear coordinate transforms |

---

## Recommended Refactoring Order

1. **Add error boundary** around GameView (quick win)
2. **Fix or disable coach mode** - half-working is worse than missing
3. **Extract `useGameState` hook** from GameView.tsx
4. **Remove mock fallbacks** - explicit errors instead
5. **Split into CoachModeView / SpectatorModeView**
6. **Audit CSS** with PurgeCSS
7. **Add accessibility** (ARIA, focus management)

---

## Questions for You

1. Is coach mode intended to work soon, or should we disable it for now?
2. What's the plan for the WebSocket vs REST API split - will coach mode use WS too?
3. Any concerns about breaking the CSS into modules?

Happy to discuss any of these in detail or help prioritize based on what's coming next for GameView.

— researcher_agent
