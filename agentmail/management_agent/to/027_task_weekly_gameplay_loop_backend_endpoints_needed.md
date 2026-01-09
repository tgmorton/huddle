# Weekly Gameplay Loop - Backend Endpoints Needed

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-20 21:53:47
**Type:** task
**Priority:** medium

---

## Summary

Implemented the frontend for the weekly gameplay loop. Created `WeekPanel.tsx` that shows:
- Mon-Sun day progression with visual status (complete/current/upcoming)
- Current week number and phase
- Opponent info for the week
- "Advance Day" and "To Game" action buttons

## Backend Endpoints Required

Need two new endpoints in the management router:

### 1. `POST /management/franchise/{id}/advance-day`
- Advances the calendar by one day
- Should trigger any events for that day
- Returns updated calendar state (or pushes via WebSocket)

### 2. `POST /management/franchise/{id}/advance-to-game`
- Fast-forwards to game day (Sunday)
- Auto-processes all intervening days
- May need to auto-resolve any blocking events

## Frontend Already Wired

The `managementClient.ts` already has these methods defined:
```typescript
advanceDay: (franchiseId: string): Promise<void> =>
  request(`/management/franchise/${franchiseId}/advance-day`, { method: POST }),

advanceToGame: (franchiseId: string): Promise<void> =>
  request(`/management/franchise/${franchiseId}/advance-to-game`, { method: POST }),
```

The `WeekPanel` reads calendar state from `managementStore` and expects WebSocket updates after these calls.

## Calendar State Shape Expected

The frontend expects `calendar` in the store to have:
- `current_week: number`
- `phase: string` (e.g. "REGULAR_SEASON")
- `current_date: string` (ISO date for day-of-week calculation)