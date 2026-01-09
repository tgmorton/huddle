# Refactor QB Brain - Completion-First Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19 13:24:10
**Type:** task
**Priority:** medium

---

## Priority: High

## Part of Objective-First Brain Refactor

## Summary
QB brain should focus on COMPLETING PASSES and MOVING THE OFFENSE, not on "beating pressure" or "making reads".

## Correct Philosophy
- Target = complete pass to open receiver / advance the ball
- Pressure is an OBSTACLE to making good throws, not something to "beat"
- Read progressions are about finding WHO IS OPEN, not "which matchup to exploit"
- Scrambling is about GAINING YARDS or BUYING TIME, not evading specific defenders
- Checkdowns happen when primary options are COVERED, not when "pressure wins"

## Key File
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/qb_brain.py`

## Decision Framework
```
1. Where are my open receivers? (read progression)
2. Can I deliver the ball there? (arm angle, timing)
3. Is my platform stable? (pressure as obstacle)
4. If no throw: extend play (scramble) or protect ball (throwaway/sack)
```

## Key Changes
1. Reads are about OPEN SPACE not defensive matchups
2. Pressure affects throw quality, doesnt "win" against QB
3. Scramble = find throwing lane OR gain yards, not escape defenders
4. Pre-snap reads identify coverage to find where open will be