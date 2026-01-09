# Portrait Generation Integration Complete - Batch API + Auto-trigger

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-20
**Status:** resolved 00:37:49
**Type:** task
**Priority:** medium

---

# Portrait Generation Integration Complete

I've hooked portrait generation into the franchise creation flow. Here's what you need to know for frontend implementation.

## What's New

### 1. Automatic Portrait Generation
When `POST /api/v1/management/franchise` is called, portrait generation now triggers automatically in the background:
- User's team gets `priority: 100` (generated first, ~0.5s for 53 players)
- Other teams, free agents, draft prospects get `priority: 0`
- Full league (~1,700 portraits) takes ~17 seconds total

### 2. New Batch Endpoints

**Queue batch generation:**
```http
POST /api/v1/portraits/batch/generate
{
  "league_id": "uuid",
  "players": [
    {"player_id": "uuid", "position": "QB", "age": 28, "priority": 100}
  ]
}
```

**Check progress:**
```http
GET /api/v1/portraits/batch/status/{league_id}
```

Returns:
```json
{
  "league_id": "uuid",
  "total": 1696,
  "completed": 847,
  "failed": 0,
  "pending": 849,
  "status": "processing"
}
```

## Frontend Implementation Suggestions

### 1. Placeholder Strategy
The existing `GET /api/v1/portraits/{league_id}/{player_id}` already returns a placeholder if portrait isn't ready. Your current approach should work:
```tsx
<img
  src={`/api/v1/portraits/${leagueId}/${playerId}`}
  alt={player.name}
  onError={(e) => e.target.src = /placeholder.png}
/>
```

### 2. Optional: Progress Indicator
If you want to show "Generating portraits..." during franchise creation:
1. After franchise creation succeeds, poll `/api/v1/portraits/batch/status/{league_id}`
2. Show progress bar: `completed / total`
3. Stop polling when `status === "complete"`

### 3. Optional: "Polaroid Developing" Effect
Management suggested portraits could "develop" like Polaroids - start blurry/silhouette and fade in when ready. Could be a nice polish touch.

## Files Modified
- `huddle/api/routers/portraits.py` - Added batch endpoints
- `huddle/api/routers/management.py` - Auto-trigger on franchise creation
- `docs/PORTRAITS.md` - Updated documentation

## Testing
Create a franchise and check:
1. User's team portraits appear first
2. Other team portraits fill in over ~17 seconds
3. Placeholder shows for any not-yet-generated portraits

Let me know if you have questions!