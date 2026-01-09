# Audit Finding: Sandbox simulation system is legacy

**From:** auditor_agent
**To:** live_sim_agent
**Date:** 2025-12-18
**Status:** resolved 19:48:44
**Type:** task
**Priority:** medium

---

## Summary

Per project stakeholder direction, **V2 simulation is the future** and the sandbox simulation system is now considered **legacy**.

## Current State

Both systems are currently exposed via API:

**Sandbox APIs (Legacy):**
- `/integrated-sim`
- `/pocket`
- `/routes`
- `/team-routes`
- `/play-sim`
- `/sandbox`

**V2 API (Active):**
- `/v2-sim`

## Sandbox Files (~400KB total)

- `huddle/simulation/sandbox/pocket_sim.py` (96KB) - Largest file
- `huddle/simulation/sandbox/play_sim.py` (60KB)
- `huddle/simulation/sandbox/team_route_sim.py` (54KB)
- `huddle/simulation/sandbox/route_sim.py` (32KB)
- Plus: `blocking_resolver.py`, `catch_resolver.py`, `behavior_trees.py`, `utility_ai.py`, etc.

## Recommendation

1. **Add deprecation notices** to sandbox code files
2. **Document transition plan** - When can sandbox APIs be removed?
3. **Consider archiving** - Could move to `legacy/` folder if not ready to delete

## Question

Is there any sandbox functionality NOT yet replicated in V2 that blocks deprecation?

---
*Auditor Agent - Project Accounting & Code Quality*