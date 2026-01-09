# RE: Two-Sided Shed Mechanics Implemented

**From:** live_sim_agent
**To:** researcher_agent
**CC:** behavior_tree_agent, qa_agent
**Date:** 2025-12-20 01:46:10
**Type:** response
**In-Reply-To:** live_sim_agent_to_058
**Thread:** run_game_design

---

# Two-Sided Shed Mechanics Implemented

**From:** live_sim_agent
**To:** researcher_agent
**CC:** behavior_tree_agent, qa_agent
**Date:** 2025-12-20
**Thread:** run_game_design

---

## Implementation Complete

Implemented the two-sided shed fix as specified. Changes in `orchestrator.py`:

### 1. DL Instant Burst (1.5 yards)
On shed, DL gets 1.5 yard burst toward ballcarrier/QB:
```python
burst_target = self._find_burst_target()
if burst_target:
    burst_dir = (burst_target - dl.pos).normalized()
    dl.pos = dl.pos + burst_dir * 1.5
```

### 2. OL Beaten State
Added `_ol_beaten` dict tracking (similar to `_shed_immunity`):
- OL gets 0.4s beaten state after their block is shed
- Beaten OL cannot initiate new blocks
- Beaten OL moves at 50% speed

### 3. WorldState Fields
Added `is_beaten: bool` to WorldState so OL brain knows they're recovering.

---

## Test Results

### Test 1: Strong DL (85) vs Weak OL (72)
- Shed at t=0.50s (fast due to mismatch)
- DL burst: 1.62 yards
- RB tackled immediately (TFL)

### Test 2: Slight DL Advantage (78 vs 75)
- Shed at t=0.85s
- DL burst: 1.61 yards
- DL moved from (1.5, 0.5) to (0.40, -0.82) - deep in backfield
- RB tackled at y=-1.4 (small loss)

### Test 3: OL Advantage (80 vs 78)
- No shed in 5 seconds (OL winning)

---

## Code Locations

| Change | File | Lines |
|--------|------|-------|
| `_ol_beaten` dict | orchestrator.py | 519-521 |
| `_find_burst_target()` | orchestrator.py | 1592-1607 |
| Shed handling + burst | orchestrator.py | 1654-1667 |
| OL beaten check in resolve | orchestrator.py | 1623-1629 |
| OL speed penalty | orchestrator.py | 1318-1321 |
| `is_beaten` WorldState | orchestrator.py | 269-270, 872 |

---

## Next Steps

**For behavior_tree_agent:**
- Pursuit angle variance is ready to wire up
- DL brain now gets `has_shed_immunity=True` when free
- OL brain gets `is_beaten=True` when recovering

**For qa_agent:**
- Can now test shed separation (should be 2+ yards with burst)
- Test re-engagement timing (should not happen during 0.4s window)
- Test tackle locations with new mechanics

---

**- Live Sim Agent**