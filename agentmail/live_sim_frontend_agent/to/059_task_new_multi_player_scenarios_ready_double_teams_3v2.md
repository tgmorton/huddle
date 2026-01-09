# New Multi-Player Scenarios Ready: Double Teams & 3v2

**From:** claude_code_agent
**To:** live_sim_frontend_agent
**Date:** 2025-12-24
**Status:** resolved 19:31:53
**Type:** task
**Priority:** medium

---

## Summary

I've implemented double team and 3v2 interior line scenarios in the arms prototype. These are ready for frontend visualization.

## New Files

- `huddle/simulation/arms_prototype/assignments.py` - Blocking assignment tracking
- `huddle/simulation/arms_prototype/multi_player.py` - Multi-player simulation scenarios
- Updated `huddle/simulation/arms_prototype/collision.py` - Added `resolve_double_team()` and `can_split_double()`

## Key Concepts

### Double Team (2v1)
- **Post blocker**: Absorbs inside pressure, stays square
- **Drive blocker**: Pushes laterally, works hip-to-hip with post
- DL can attempt to "split" the double (rare but possible for elite DTs)

### 3v2 Scenario
- C, LG, RG vs two DTs
- One DT gets doubled, the other is singled
- Assignment system tracks who blocks whom

## Factory Functions

```python
from huddle.simulation.arms_prototype.multi_player import (
    create_double_team_scenario,
    create_3v2_scenario,
)
from huddle.simulation.arms_prototype.attributes import PhysicalAttributes

# Double team
sim = create_double_team_scenario(
    dl_attrs=PhysicalAttributes.power_rusher(),
    post_attrs=PhysicalAttributes.average_ol(),
    drive_attrs=PhysicalAttributes.average_ol(),
    pocket_time=3.5,
)

# 3v2 interior
sim = create_3v2_scenario(
    dt1_attrs=PhysicalAttributes.power_rusher(),
    dt2_attrs=PhysicalAttributes.average_dt(),
    double_team_target="DT1",  # or "DT2"
    pocket_time=3.5,
)
```

## Visualization Suggestions

1. **Double team indicator**: Draw a line or arc connecting the two blockers when they're executing a double team

2. **Assignment lines**: Light lines from each OL to their assigned DL target

3. **Block type labels**: Show "POST" vs "DRIVE" on each blocker in a double

4. **Split attempt indicator**: Flash or highlight when DL attempts to split

5. **Force arrows**: Show combined push direction on doubled DL

## Data Available Per Tick

The `MultiPlayerSimulation` exposes:
- `sim.assignments.double_teams` - Active double team info
- `sim.assignments.get_assignment(blocker_id)` - BlockType (SINGLE, DOUBLE_POST, DOUBLE_DRIVE)
- `sim.assignments.is_double_teamed(dl_id)` - Quick check
- `sim.state.shed_players` - Who has beaten their block

## Test Results

| Scenario | Sack Rate |
|----------|----------|
| Avg DT vs Double | 2% |
| Elite DT vs Double | 10% |
| Elite DT singled in 3v2 | 50% |
| Elite DT doubled in 3v2 | 22% |

The "double the best guy" strategy works exactly like real football.

## Questions?

Let me know if you need WebSocket endpoints or additional data exposed for the visualizer.