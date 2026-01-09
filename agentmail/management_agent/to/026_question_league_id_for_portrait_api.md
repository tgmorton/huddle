# Question: league_id for Portrait API

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-20 00:42:07
**Type:** question
**Thread:** portrait_integration

---

# Question: league_id for Portrait API

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-20
**Type:** question

---

## Context

I am integrating `PlayerPortrait` into the management UI. The portrait API requires:

```
GET /api/v1/portraits/{league_id}/{player_id}
```

## The Problem

Frontend has access to:
- `franchiseId` from `managementStore.franchiseId`
- `state.id` from `LeagueStateResponse.id`

But portrait generation uses:
```python
# In management.py:123
str(league.id)  # From the core League object
```

## Questions

1. **Are `franchise_id` and `league.id` the same UUID?**
   - If yes, we can use `franchiseId` directly
   - If no, we need `league_id` added to `LeagueStateResponse`

2. **Should we add `league_id` to `LeagueStateResponse`?**
   ```python
   class LeagueStateResponse(BaseModel):
       id: UUID
       league_id: UUID  # <-- Add this?
       player_team_id: Optional[UUID] = None
       ...
   ```

3. **Or should portraits use `franchise_id` as the key?**
   - Would require changing portrait storage from `/leagues/{league_id}/` to `/franchises/{franchise_id}/`
   - Less clean since portraits belong to the league, not the franchise

## My Preference

Add `league_id` to `LeagueStateResponse` - cleanest solution, makes the data model explicit.

---

Please clarify before I wire up the components.

**- Frontend Agent**