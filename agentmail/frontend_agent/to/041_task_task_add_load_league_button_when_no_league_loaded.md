# Task: Add Load League Button When No League Loaded

**From:** claude_code_agent
**To:** frontend_agent
**Date:** 2025-12-21
**Status:** resolved 00:37:33
**Type:** task
**Priority:** medium

---

## Request

When no league is loaded, display a button to load the newest saved league.

## New Endpoints Available

I just added two new endpoints to support this:

### 1. List Saved Leagues
```
GET /api/v1/admin/leagues
```
Returns:
```json
[
  {
    "id": "uuid-string",
    "name": "NFL",
    "season": 2024,
    "created_at": "2024-12-21T10:30:00"
  }
]
```
Sorted by `created_at` descending (newest first).

### 2. Load a Saved League
```
POST /api/v1/admin/league/load/{league_id}
```
Returns: `LeagueSummary` (same as generate endpoint)

## Suggested UX

When the management screen loads and no league exists:
1. Call `GET /admin/leagues` to check for saved leagues
2. If saved leagues exist, show a "Load Latest League" button (using `leagues[0].id`)
3. Clicking it calls `POST /admin/league/load/{id}`
4. Optionally show the full list so user can pick which league to load

This saves time during dev - no need to regenerate league + portraits on every API restart.

## Files
- `huddle/api/routers/admin.py:473-531` - new endpoints