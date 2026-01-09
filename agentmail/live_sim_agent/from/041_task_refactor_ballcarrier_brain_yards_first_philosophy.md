# Refactor Ballcarrier Brain - Yards-First Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19 13:14:53
**Type:** task
**Priority:** medium

---

## Priority: High

## Related To
This follows the same philosophy as the DL/OL refactor task - objectives first, players as obstacles.

## Summary
Ballcarrier brain should be focused on GAINING YARDS, not "beating defenders". Defenders are obstacles between the ballcarrier and the endzone.

## Current (Wrong) Approach
- Find hole → run to hole
- See defender → try to juke/evade them
- Primary decisions are about "how to beat this guy"

## Correct Approach
- Primary goal: ADVANCE THE BALL (gain yards, reach endzone)
- Read field for best path forward (most open space, best blocking angles)
- Defenders are obstacles - go around, through, or away from them
- Blockers create lanes - run where defenders ARENT
- Every decision is "what gets me more yards" not "how do I beat this defender"

## Key File
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/ballcarrier_brain.py`

## Ballcarrier Brain Changes
1. Primary target = endzone direction (positive Y)
2. Field vision: scan for open lanes, not for defenders to beat
3. Cut decisions based on "where is open space" not "which defender to juke"
4. Speed vs power: which gets MORE YARDS, not which beats the defender
5. Follow blockers = run where they are creating space
6. Cutback reads = find where defense OVERFLOWED, not where a specific defender is

## Decision Framework
```
1. Where is open space? (lanes, cutback, bounce outside)
2. What is my speed/angle to that space?
3. Are there obstacles (defenders) in the way?
4. Can I go around them or do I need to go through?
5. Execute move that maximizes yards gained
```

## Expected Behavior
1. Ballcarrier always pressing toward endzone
2. Cuts and moves are to AVOID defenders, not to BEAT them
3. Follows blocking - runs to daylight created by OL
4. Cutback when backside is open, not when "I can beat this guy"
5. Contact happens when necessary, not as a goal

## Test Scenarios
- Use run play scenarios in BLOCKING_SCENARIOS (4.1, 4.2)
- RB should find and hit the designed hole
- RB should cutback if playside is clogged
- RB should not run directly at defenders