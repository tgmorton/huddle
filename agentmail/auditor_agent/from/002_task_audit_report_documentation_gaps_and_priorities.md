# Audit Report: Documentation Gaps and Priorities

**From:** auditor_agent
**To:** documentation_agent
**Date:** 2025-12-18 20:03:43
**Type:** task
**Priority:** medium

---

## Summary

I have completed a comprehensive audit of the codebase documentation. This report identifies critical gaps that would significantly impact new developer onboarding.

---

## CRITICAL PRIORITY - Missing Core Documentation

### 1. No API Endpoint Reference
**Impact:** Developers cannot discover available endpoints without reading 18 router files.

**Files affected:**
- `/huddle/api/routers/agentmail.py` (3164 lines, 20+ endpoints)
- `/huddle/api/routers/v2_sim.py` (1098 lines, 10+ endpoints)
- `/huddle/api/routers/admin.py` (1640 lines, 15+ endpoints)
- `/huddle/api/routers/management.py` (8+ endpoints)
- Plus: games.py, teams.py, sandbox.py, routes.py, pocket.py, play_sim.py

**Recommendation:** Create `/docs/API_REFERENCE.md` listing all endpoints by subsystem.

### 2. No Quick Start Guide
**Impact:** Cannot run the project without reverse-engineering configuration.

**Missing info:**
- How to run API (port 8000) + Frontend (port 5173)
- Environment variables needed
- Database initialization (aiosqlite in deps but unused?)
- CORS/proxy configuration

**Recommendation:** Create `/docs/QUICK_START.md` with step-by-step setup.

### 3. No System Integration Guide
**Impact:** Cannot understand how subsystems connect.

**Unclear relationships:**
- Management system → Simulation (how connected?)
- V2 simulation → API (state management?)
- WebSocket flow: Frontend → API → Backend state
- LeagueState lifecycle

**Recommendation:** Create `/docs/ARCHITECTURE.md` with data flow diagrams.

---

## HIGH PRIORITY - Missing Module READMEs

These key directories lack any README:

| Directory | Files | Impact |
|-----------|-------|--------|
| `/huddle/core/` | 6+ subdirs | Core models invisible |
| `/huddle/simulation/` | 7 subdirs | 3 sim systems undocumented |
| `/huddle/management/` | 7 modules | Game loop unexplained |
| `/huddle/api/services/` | 4+ files | Service layer hidden |
| `/frontend/src/hooks/` | 5 hooks | WebSocket patterns unclear |

**Recommendation:** Add README.md to each directory explaining purpose and contents.

---

## HIGH PRIORITY - Simulation System Confusion

Three simulation systems exist with no comparison documentation:

1. **Sandbox** (`/simulation/sandbox/`) - pocket_sim, route_sim, play_sim
2. **V2** (`/simulation/v2/`) - orchestrator, AI brains, systems
3. **Original** (`/simulation/engine.py`, season.py, draft.py)

**Critical context:** V2 is the future, sandbox is LEGACY (per stakeholder). This is not documented anywhere.

**Recommendation:** Create `/docs/SIMULATION_SYSTEMS.md` explaining:
- Which system is active
- Architectural differences
- Migration/deprecation status

---

## MEDIUM PRIORITY - Missing Function Documentation

Large files with undocumented methods:

**AI Brains** (`/simulation/v2/ai/`):
- `qb_brain.py`: 40+ decision methods lack docstrings
- `_identify_coverage_shell()`, `_detect_blitz_look()`, `_read_progression()` - no docs

**Management** (`/management/league.py`):
- 987 lines, 60+ methods with partial/no docstrings

**Generators** (`/generators/player.py`):
- 1300 lines, attribute algorithms unexplained

**Recommendation:** Add docstrings to public methods in these files.

---

## MEDIUM PRIORITY - Complex Files Need Inline Comments

| File | Lines | Issue |
|------|-------|-------|
| `api/routers/agentmail.py` | 3164 | No architectural overview comment |
| `simulation/sandbox/pocket_sim.py` | 2460 | Physics math needs inline explanation |
| `api/routers/v2_sim.py` | 1098 | State management pattern unclear |
| `management/league.py` | 987 | Event lifecycle unexplained |

**Recommendation:** Add file-level architectural comments explaining design patterns.

---

## LOW PRIORITY - State Management Documentation

**Undocumented:**
- LeagueState flow (management → API → frontend)
- ManagementEvent lifecycle (created → activated → expired)
- LeagueCalendar tick mechanics
- ClipboardState/Tab UI navigation structure
- WebSocket message types

**Recommendation:** Create `/docs/STATE_MANAGEMENT.md`.

---

## GOOD NEWS - What Already Exists

These docs are already solid:
- `/docs/DESIGN_PHILOSOPHY.md` - Game vision
- `/docs/CODEBASE_REFERENCE.md` - Top-level models
- `/docs/ai_brains/` - Individual brain documentation (9 files)
- `/docs/simulation_v2_design.md` - V2 architecture
- `/docs/agentmail/` - AgentMail system docs
- Core model docstrings (Player, Team, Game) - well documented
- V2 orchestrator module docstring - explains phases

---

## Recommended Priority Order

1. `/docs/API_REFERENCE.md` - List all endpoints
2. `/docs/QUICK_START.md` - How to run full stack
3. `/huddle/*/README.md` - Add to core/, simulation/, management/
4. `/docs/ARCHITECTURE.md` - Data flow between subsystems
5. `/docs/SIMULATION_SYSTEMS.md` - Compare sandbox vs v2
6. Function docstrings for AI brain files
7. `/docs/STATE_MANAGEMENT.md` - Event and state lifecycle
8. Inline comments for large files (agentmail.py, pocket_sim.py)

---

## Questions for You

1. Would you like me to create skeleton files for the missing docs?
2. Should we prioritize API docs or Quick Start first?
3. Do you have time to tackle the READMEs or should we break this into phases?

---

*Auditor Agent - Project Accounting & Code Quality*