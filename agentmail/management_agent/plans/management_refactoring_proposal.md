# Management System Refactoring Proposal

**Author:** management_agent  
**Date:** 2024-12-27  
**Status:** Draft

## Executive Summary

The management system has grown organically and now has several monolithic files that should be split for maintainability. The largest offender is `huddle/api/routers/management.py` at **2460 lines**, containing 50+ endpoints across 8+ different domains.

## Current State Analysis

### File Sizes (Lines of Code)

| File | Lines | Status |
|------|-------|--------|
| `huddle/api/routers/management.py` | 2460 | **Critical - needs split** |
| `huddle/management/events.py` | 1153 | Moderate - well-structured |
| `huddle/api/schemas/management.py` | 1049 | **Needs split** |
| `huddle/management/league.py` | 1039 | Review needed |
| `huddle/management/health.py` | 992 | Well-organized |
| `huddle/api/services/management_service.py` | 976 | Acceptable |

### Router Domain Analysis

The `management.py` router contains endpoints for these distinct domains:

1. **Franchise Core** (lines 118-238) - Create, get, delete franchise
2. **Time Controls** (lines 240-286) - Pause, play, speed
3. **Events** (lines 288-324) - Get, attend, dismiss events
4. **Clipboard/Navigation** (lines 326-366) - Tab selection, navigation
5. **Financials** (lines 369-535) - Cap, contracts, restructure, cut
6. **Free Agency** (lines 663-703) - FA listing
7. **Draft Prospects** (lines 706-963) - Prospects, scouting data
8. **Drawer** (lines 974-1037) - Desk drawer items
9. **Draft Board** (lines 1039-1128) - User's draft rankings
10. **Time Advancement** (lines 1131-1274) - Day/game advancement
11. **Week Journal** (lines 1277-1329) - Journal entries
12. **Practice** (lines 1332-1573) - Practice execution, mastery, development
13. **Game Simulation** (lines 1576-1694) - Sim games
14. **Negotiation** (lines 1697-1905) - Contract negotiations
15. **Auctions** (lines 1908-2460) - FA auction system

---

## Refactoring Proposal

### Phase 1: Split Router into Sub-Routers

Create domain-specific routers in `huddle/api/routers/management/`:

```
huddle/api/routers/management/
    __init__.py           # Aggregates all sub-routers
    franchise.py          # Franchise CRUD, time controls
    contracts.py          # Financials, restructure, cut, extend
    free_agency.py        # FA list, negotiations, auctions
    draft.py              # Prospects, scouting, draft board
    practice.py           # Practice, playbook mastery, development
    game.py               # Game simulation, results
    clipboard.py          # Events, drawer, journal, clipboard
```

**Example: `free_agency.py`**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/free-agency", tags=["free-agency"])

# Move these endpoints here:
# - GET /free-agents
# - POST /negotiations/start
# - POST /negotiations/{player_id}/offer
# - GET /negotiations/active
# - DELETE /negotiations/{player_id}
# - POST /auction/start
# - POST /auction/{player_id}/bid
# - POST /auction/{player_id}/advance
# - POST /auction/{player_id}/finalize
# - GET /auctions/active
# - DELETE /auction/{player_id}
```

**Aggregation in `__init__.py`:**
```python
from fastapi import APIRouter
from . import franchise, contracts, free_agency, draft, practice, game, clipboard

router = APIRouter(prefix="/management", tags=["management"])
router.include_router(franchise.router)
router.include_router(contracts.router)
router.include_router(free_agency.router)
router.include_router(draft.router)
router.include_router(practice.router)
router.include_router(game.router)
router.include_router(clipboard.router)
```

### Phase 2: Split Schemas

Create domain-specific schema files in `huddle/api/schemas/management/`:

```
huddle/api/schemas/management/
    __init__.py           # Re-exports all schemas
    enums.py              # All enum schemas (lines 11-119)
    core.py               # Calendar, League, Franchise responses
    events.py             # Event schemas
    contracts.py          # Contract, financial schemas
    free_agency.py        # FA, negotiation, auction schemas
    draft.py              # Prospect, scouting, draft board schemas
    practice.py           # Practice, mastery, development schemas
    game.py               # Game simulation schemas
    websocket.py          # WebSocket message types
```

### Phase 3: Extract In-Memory State

Currently, negotiation and auction state is stored in module-level dicts:

```python
# Lines 1703-1710
_active_negotiations: dict[str, dict[str, "NegotiationState"]] = {}

# Lines 1967-1974
_active_auctions: Dict[str, Dict[str, AuctionState]] = {}
```

**Proposal:** Move these into `ManagementService` as instance attributes:

```python
class ManagementService:
    def __init__(self, state: LeagueState, league: "League") -> None:
        # ... existing init ...
        
        # Move from module-level to instance
        self._active_negotiations: dict[str, NegotiationState] = {}
        self._active_auctions: dict[str, AuctionState] = {}
```

This improves:
- Testability (no global state to reset)
- Session isolation (multiple franchises don't share state)
- Memory management (state cleaned up with session)

### Phase 4: Extract Helper Classes

The `AuctionTeamBid` and `AuctionState` dataclasses (lines 1918-1965) should move to a dedicated module:

```
huddle/management/auction.py   # AuctionState, AuctionTeamBid, helper functions
huddle/management/negotiation.py  # NegotiationState (if not already separate)
```

---

## Identified Improvements

### 1. Missing Functionality

| Feature | Status | Notes |
|---------|--------|-------|
| Trade system | Missing | No trade offer handling beyond events |
| Injury integration | Partial | Health.py exists but not wired to practice |
| Staff/coaching | Missing | No endpoints for staff management |
| Standings updates | Missing | Game results don't update standings |
| Contract signing | Partial | Negotiation doesn't add player to roster |
| Cap validation | Missing | No cap check before signing |

### 2. Code Quality Issues

**Duplicate Code:**
- Position percentile calculation (lines 706-746) duplicated in single/batch endpoints
- Should extract to `_calculate_prospect_scouting_data(player, percentiles)` helper

**Type Safety:**
- Several `Optional[...]` returns without proper None checks
- `player.position.value` used without checking if position exists

**Random Seeding:**
- Single-prospect endpoint (line 910) uses global `random`, not player-seeded RNG
- Should use `player_rng = random.Random(hash(str(player.id)))` like batch endpoint

### 3. Performance Concerns

**Draft Prospects Endpoint:**
- Recalculates position percentiles on every request
- Should cache percentiles per draft class (they don't change)

**Free Agents Endpoint:**
- Recalculates market value for every FA on every request
- Should cache or compute lazily

### 4. API Consistency

**Inconsistent Response Patterns:**
- Some endpoints return `{"success": True, ...}`
- Others return `{"message": "...", ...}`
- Should standardize on consistent response envelope

**Missing Pagination:**
- `/free-agents` returns all FAs (could be 200+)
- `/draft-prospects` returns entire draft class
- Should add `?limit=50&offset=0` pagination

---

## Implementation Priority

### High Priority (Do First)
1. Split `management.py` router into sub-routers
2. Move auction/negotiation state into ManagementService
3. Fix random seeding in single-prospect endpoint

### Medium Priority
1. Split schemas into domain files
2. Add cap validation to contract signing
3. Complete negotiation → signing flow

### Low Priority
1. Add pagination to list endpoints
2. Cache percentile calculations
3. Standardize response envelopes

---

## Migration Strategy

### Step 1: Create Directory Structure
```bash
mkdir -p huddle/api/routers/management
mkdir -p huddle/api/schemas/management
```

### Step 2: Extract One Router at a Time
Start with the most isolated domain (e.g., `drawer.py` or `draft.py`), verify tests pass, then continue.

### Step 3: Update Imports Incrementally
Keep backward compatibility by re-exporting from original locations during migration.

### Step 4: Clean Up
Remove deprecated re-exports once all consumers updated.

---

## Testing Considerations

- Each sub-router should have its own test file
- Move router-specific fixtures to appropriate test files
- Ensure no cross-domain test dependencies

---

## Questions for Discussion

1. Should auctions be a completely separate module from negotiations, or unified under "transactions"?
2. Should we add an explicit `TransactionService` to handle all roster-modifying operations?
3. Is the current event system sufficient, or do we need event handlers for async processing?

---

## Appendix: Endpoint Mapping

| Current Endpoint | New Router | New Path |
|-----------------|------------|----------|
| `POST /franchise` | `franchise.py` | `POST /franchise` |
| `GET /franchise/{id}` | `franchise.py` | `GET /franchise/{id}` |
| `DELETE /franchise/{id}` | `franchise.py` | `DELETE /franchise/{id}` |
| `POST /franchise/{id}/pause` | `franchise.py` | `POST /{id}/pause` |
| `POST /franchise/{id}/play` | `franchise.py` | `POST /{id}/play` |
| `POST /franchise/{id}/speed` | `franchise.py` | `POST /{id}/speed` |
| `GET /franchise/{id}/events` | `clipboard.py` | `GET /{id}/events` |
| `POST /franchise/{id}/events/attend` | `clipboard.py` | `POST /{id}/events/attend` |
| `POST /franchise/{id}/events/dismiss` | `clipboard.py` | `POST /{id}/events/dismiss` |
| `GET /franchise/{id}/financials` | `contracts.py` | `GET /{id}/financials` |
| `GET /franchise/{id}/contracts` | `contracts.py` | `GET /{id}/contracts` |
| `GET /franchise/{id}/contracts/{pid}` | `contracts.py` | `GET /{id}/contracts/{pid}` |
| `POST /franchise/{id}/contracts/{pid}/restructure` | `contracts.py` | `POST /{id}/contracts/{pid}/restructure` |
| `POST /franchise/{id}/contracts/{pid}/cut` | `contracts.py` | `POST /{id}/contracts/{pid}/cut` |
| `GET /franchise/{id}/free-agents` | `free_agency.py` | `GET /{id}/` |
| `POST /franchise/{id}/negotiations/start` | `free_agency.py` | `POST /{id}/negotiations/start` |
| `POST /franchise/{id}/negotiations/{pid}/offer` | `free_agency.py` | `POST /{id}/negotiations/{pid}/offer` |
| `GET /franchise/{id}/negotiations/active` | `free_agency.py` | `GET /{id}/negotiations/active` |
| `DELETE /franchise/{id}/negotiations/{pid}` | `free_agency.py` | `DELETE /{id}/negotiations/{pid}` |
| `POST /franchise/{id}/free-agency/auction/start` | `free_agency.py` | `POST /{id}/auctions/start` |
| `POST /franchise/{id}/free-agency/auction/{pid}/bid` | `free_agency.py` | `POST /{id}/auctions/{pid}/bid` |
| `POST /franchise/{id}/free-agency/auction/{pid}/advance` | `free_agency.py` | `POST /{id}/auctions/{pid}/advance` |
| `POST /franchise/{id}/free-agency/auction/{pid}/finalize` | `free_agency.py` | `POST /{id}/auctions/{pid}/finalize` |
| `GET /franchise/{id}/free-agency/auctions/active` | `free_agency.py` | `GET /{id}/auctions/active` |
| `DELETE /franchise/{id}/free-agency/auction/{pid}` | `free_agency.py` | `DELETE /{id}/auctions/{pid}` |
| `GET /franchise/{id}/draft-prospects` | `draft.py` | `GET /{id}/prospects` |
| `GET /franchise/{id}/draft-prospects/{pid}` | `draft.py` | `GET /{id}/prospects/{pid}` |
| `GET /franchise/{id}/draft-board` | `draft.py` | `GET /{id}/board` |
| `POST /franchise/{id}/draft-board` | `draft.py` | `POST /{id}/board` |
| `DELETE /franchise/{id}/draft-board/{pid}` | `draft.py` | `DELETE /{id}/board/{pid}` |
| `PATCH /franchise/{id}/draft-board/{pid}` | `draft.py` | `PATCH /{id}/board/{pid}` |
| `POST /franchise/{id}/draft-board/{pid}/reorder` | `draft.py` | `POST /{id}/board/{pid}/reorder` |
| `GET /franchise/{id}/draft-board/{pid}/status` | `draft.py` | `GET /{id}/board/{pid}/status` |
| `GET /franchise/{id}/drawer` | `clipboard.py` | `GET /{id}/drawer` |
| `POST /franchise/{id}/drawer` | `clipboard.py` | `POST /{id}/drawer` |
| `DELETE /franchise/{id}/drawer/{iid}` | `clipboard.py` | `DELETE /{id}/drawer/{iid}` |
| `PATCH /franchise/{id}/drawer/{iid}` | `clipboard.py` | `PATCH /{id}/drawer/{iid}` |
| `POST /franchise/{id}/advance-day` | `franchise.py` | `POST /{id}/advance-day` |
| `POST /franchise/{id}/advance-to-game` | `franchise.py` | `POST /{id}/advance-to-game` |
| `GET /franchise/{id}/week-journal` | `clipboard.py` | `GET /{id}/journal` |
| `POST /franchise/{id}/week-journal` | `clipboard.py` | `POST /{id}/journal` |
| `POST /franchise/{id}/run-practice` | `practice.py` | `POST /{id}/run` |
| `GET /franchise/{id}/playbook-mastery` | `practice.py` | `GET /{id}/mastery` |
| `GET /franchise/{id}/development` | `practice.py` | `GET /{id}/development` |
| `GET /franchise/{id}/weekly-development` | `practice.py` | `GET /{id}/weekly` |
| `POST /franchise/{id}/sim-game` | `game.py` | `POST /{id}/sim` |
