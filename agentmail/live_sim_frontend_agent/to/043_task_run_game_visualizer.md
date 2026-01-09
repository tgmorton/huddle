# Task: Run Game Visualizer

**From:** live_sim_agent (claude_code)
**To:** live_sim_frontend_agent
**Date:** 2025-12-19
**Status:** resolved
**Type:** task
**Priority:** high

---

## Request

User wants eyes on the run game while we're building it. Need a visualizer for run plays.

## What's New in Backend

I've added run game support:

1. **Run Play Concepts** - Inside zone, outside zone, power, counter, dive, draw, toss
2. **Handoff Mechanics** - `HANDOFF` event emitted when QB hands off to RB
3. **Run Blocking Assignments** - OL get specific assignments (zone_step, pull_lead, combo, cutoff, etc.)
4. **RB Path** - Each concept has waypoints for the RB to follow

## Data Available in Tick Payload

For run plays (`is_run_play: true` in config):

```python
# Events
EventType.HANDOFF  # When QB hands off to RB

# Play phase
phase: "run_active"  # After handoff

# Player assignments visible in their brain decisions:
# OL: "run:zone_step", "run:pull_lead", "run:combo", etc.
# RB: "run:ball_carrier"
```

## Suggested Visualizer Features

1. **Gap Indicators** - Show A/B/C gaps on field (like the numbers A, B, C between OL positions)
2. **Blocking Assignments** - Small labels or colors on OL showing their assignment (pull, zone, down, cutoff)
3. **Designed Hole** - Highlight the aiming point gap that the play is designed to hit
4. **RB Path** - Draw the designed path waypoints the RB should follow
5. **Pulling Linemen** - Trail or animation showing OL pulling across formation

## Priority

High - user wants to see this while we're iterating on run game mechanics.

