# Refactor DB Brain - Prevention-First Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19
**Status:** resolved 13:24:43
**Type:** task
**Priority:** medium

---

## Priority: High

## Part of Objective-First Brain Refactor

## Summary
DB brain should focus on PREVENTING COMPLETIONS and PREVENTING YARDS, not on "covering" or "beating" receivers.

## Correct Philosophy
- Target = prevent the catch / prevent yards after catch
- Stay between receiver and WHERE THE BALL WILL BE
- Not "stick with receiver" but "take away the throw"
- In run support: tackle ballcarrier, prevent yards
- Turnovers happen when youre in position to make a play on the ball

## Key File
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/db_brain.py`

## Decision Framework
```
In Coverage:
1. Where will the ball be thrown? (read QB eyes, route concept)
2. Position between receiver and that spot
3. When ball is thrown: MAKE A PLAY (breakup or INT)

In Run Support:
1. Where is the ball going?
2. Fill gap or pursue ballcarrier
3. Make the tackle (prevent yards)
```

## Key Changes
1. Coverage is about POSITIONING relative to ball, not receiver
2. Breaks on ball are about getting to the catch point
3. Run support = fill gaps, make tackles (same as LB)
4. Dont "cover" receiver, TAKE AWAY the throw