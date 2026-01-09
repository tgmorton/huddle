# Test Request: QB Read Progression

**From:** live_sim_agent
**To:** qa_agent
**Date:** 2025-12-18
**Status:** resolved 20:46:07
**Type:** task
**Priority:** medium
**Thread:** qb_read_order_bug

---

# Test Request: QB Read Progression

**From:** live_sim_agent
**To:** qa_agent
**Date:** 2025-12-18
**Status:** resolved
**Type:** task
**Thread:** qb_read_order_bug

---

## What Was Fixed

We fixed the QB read_order bug where all receivers had hardcoded `read_order=1`. Now:

1. `PlayerView` in orchestrator has `read_order: int = 0` field
2. `RouteAssignment` in route_runner has `read_order: int = 1` field
3. Data flows from play config → route assignments → WorldState → QB brain

## What to Test

1. **Run a play with multiple receivers** (e.g., 3 WR set)
2. **Verify QB brain sees different read_order values** for each receiver
3. **Verify QB progresses through reads in order** (1st read → 2nd read → 3rd read)
4. **Different play configs should produce different progressions**

## How to Test

Option A: Run V2 sim via WebSocket and check QB decision logs
Option B: Write a unit test that:
- Creates a play with defined read order
- Builds WorldState
- Verifies `teammate.read_order` values are correct
- Calls qb_brain and checks it respects the order

## Expected Behavior

- First read receiver should have `read_order=1`
- Second read should have `read_order=2`
- QB should check receivers in that order before scrambling

## Files Changed

- `huddle/simulation/v2/orchestrator.py` - PlayerView.read_order field + wiring
- `huddle/simulation/v2/systems/route_runner.py` - RouteAssignment.read_order field

---

**- Live Sim Agent**

---
**Status Update (2025-12-18):** All 7/7 tests pass: Concepts (3), Sort (1), Progression (2), Pressure (1)