# Request: Prospect Scouting Data for Draft UI

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-19 12:59:46
**Type:** task
**Priority:** medium

---

## Summary

Building a draft prospect view (ProspectPane) inspired by FOF9 with uncertainty-first design. Need backend support for scouting data.

## Required Fields for Prospects

### 1. Scouting Depth (per prospect)
- `scouted_percentage` (0-100) - how much we have invested in scouting them
- `interviewed` (boolean) - have we done an interview?
- `private_workout` (boolean) - have we done a private workout?

### 2. Scout Estimates vs True Values
- Currently `attributes` are the "true" values
- For prospects, we need scout *estimates* that could be wrong
- Suggestion: `scout_estimates: Record<string, number>` separate from hidden true values
- The error margin could be based on `scouted_percentage`

### 3. Combine/Measurables (factual, not opinions)
- `forty_yard_dash: number`
- `bench_press: number` (reps)
- `vertical_jump: number` (inches)
- `broad_jump: string` (e.g. "10 ft 2 in")

### 4. Projection
- `projected_round: number` or `projected_pick_range: string`

## Current State

I have created `ProspectPane.tsx` that mocks this data for now. Once you add the backend support, I can wire it up.

## Files
- `/frontend/src/components/ManagementV2/workspace/panes/ProspectPane.tsx` - the new component
- Uses `adminApi.getPlayer(playerId)` to fetch data

Let me know if you have questions or want to discuss the data model.