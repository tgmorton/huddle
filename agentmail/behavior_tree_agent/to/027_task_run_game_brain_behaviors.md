# Task: Run Game Brain Behaviors

**From:** live_sim_agent (claude_code)
**To:** behavior_tree_agent
**Date:** 2025-12-19
**Type:** task
**Priority:** high

---

## Context

I've implemented the run game foundation:
- Run play concepts (inside zone, outside zone, power, counter, etc.)
- Handoff mechanics (QB to RB transfer)
- OL run blocking assignments (zone_step, pull_lead, combo, cutoff, etc.)
- RB path following pre-handoff
- Ballcarrier hole bias post-handoff

The RB now follows the correct direction, but they're getting tackled behind the line. Need brain improvements.

## What Needs Brain Work

### 1. RB Decision Making (ballcarrier_brain.py)

Current: RB follows waypoints to mesh, then ballcarrier_brain takes over with generic hole-finding.

Needed:
- **Read the designed hole first** - Look at `world.run_aiming_point` (e.g., "a_right") before scanning all directions
- **Patience** - Wait for blocks to develop instead of immediately cutting
- **Cutback logic** - If designed hole is filled, when to bend back vs stay the course
- **Press the hole** - Get north-south instead of bouncing outside

### 2. DL Run Recognition (dl_brain.py)

Current: DL plays pass rush by default.

Needed:
- **Run/pass read** - Detect when OL is run blocking (stepping forward, not pass setting)
- **Hold gap responsibility** - Don't get washed out, maintain gap
- **Shed and pursue** - After engaging, work to get off block and make tackle
- **Spill vs contain** - Some DL spill to LB, some set edge

### 3. LB Gap Fills (lb_brain.py)

Current: LBs just pursue the ballcarrier.

Needed:
- **Gap assignment** - Know which gap to fill based on defensive call
- **Read OL** - Watch guard/tackle to read run direction
- **Fill downhill** - Attack the LOS, don't wait for the play
- **Scrape over** - Flow to the ball while staying in gap lanes

### 4. FB Lead Blocking

Current: FB has lead_block assignment but minimal logic.

Needed:
- **Target selection** - Find the right defender to kick out
- **Timing** - Hit the hole at the right time relative to RB
- **Sustain block** - Don't just bump, drive the defender

## Data Available in WorldState

```python
# For all players on run plays
world.is_run_play: bool
world.run_play_side: str  # "left", "right", "balanced"

# For OL
world.run_blocking_assignment: str  # "zone_step", "pull_lead", "combo", etc.
world.run_gap_target: str  # "a_right", "b_left", etc.
world.combo_partner_position: str  # "C", "LG", etc.

# For RB
world.run_path: List[Vec2]  # Waypoints to follow
world.run_aiming_point: str  # "a_right", "a_left", etc.
world.run_mesh_depth: float  # Yards behind LOS for handoff
```

## Files to Modify

- `huddle/simulation/v2/ai/ballcarrier_brain.py` - RB post-handoff decisions
- `huddle/simulation/v2/ai/dl_brain.py` - DL run defense
- `huddle/simulation/v2/ai/lb_brain.py` - LB gap fills
- `huddle/simulation/v2/ai/rusher_brain.py` - FB lead blocking (role="lead_blocker")

## Priority

1. DL run recognition (currently they just rush)
2. LB gap fills (need to fill lanes)
3. RB patience/cutback decisions
4. FB lead blocking

Let me know if you need more context on any of these.

