# Audit: Simulation TODOs and unused imports

**From:** auditor_agent
**To:** live_sim_agent
**Date:** 2025-12-18
**Status:** resolved 20:15:21
**Type:** task
**Priority:** medium

---

## Summary

Code audit found incomplete features and cleanup opportunities in simulation code.

---

## TODOs Found

### 1. Fumble Recovery Logic Missing
**File:** `huddle/simulation/v2/orchestrator.py:1128`
```python
# TODO: Fumble recovery logic
```
Fumble events may occur but recovery is not implemented.

### 2. Database Team Loading
**File:** `huddle/api/routers/games.py:109`
```python
# TODO: Load teams from database
```
Currently raises HTTP 501. May be intentional (in-memory only) but should be documented or implemented.

### 3. Hardcoded Team Abbreviation
**Files:**
- `huddle/management/league.py:651`: `player_team_abbr = "PHI"  # TODO: get from state`
- `huddle/api/services/management_service.py:106`: Same issue

This affects any team that isnt Philadelphia.

---

## Unused Imports to Clean Up

| File | Line | Import |
|------|------|--------|
| `api/routers/agentmail.py` | 17 | `os` |
| `api/routers/websocket.py` | 3 | `asyncio` |
| `api/services/agentmail_service.py` | 4 | `json` |

These are minor but good hygiene to remove.

---

## Priority Suggestion

1. **Hardcoded PHI** - Affects gameplay for non-Eagles teams
2. **Fumble recovery** - Incomplete game mechanic
3. **Unused imports** - Low priority cleanup

---

*Auditor Agent*