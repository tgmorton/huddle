# BUG: get_draft_prospect endpoint 500 error

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-19 13:23:56
**Type:** bug
**Severity:** MAJOR
**Status:** resolved

---

# Bug: get_draft_prospect endpoint crashes

## Error

```
AttributeError: 'LeagueState' object has no attribute 'league'
```

At `huddle/api/routers/management.py:449`:
```python
league = session.service.state.league
```

## Problem

`session.service.state` is a `LeagueState` object which does not have a `.league` attribute.

Looking at other working endpoints in the same file (lines 242-243):
```python
state = session.service.state
team = state.league.teams.get(state.player_team_abbr)
```

So `state.league` exists but you need to get `state` first, then access `.league`.

## Fix

Change line 449 from:
```python
league = session.service.state.league
```

To:
```python
state = session.service.state
league = state.league
```

Or check how other endpoints access the league - there may be a different pattern needed.

## Affected Endpoints

- `GET /management/franchise/{id}/draft-prospects/{player_id}` - crashes
- Possibly also `GET /management/franchise/{id}/draft-prospects` (line 351) and `GET /franchise/{id}/free-agents` (line 305) if they have the same issue

---

**- Frontend Agent**