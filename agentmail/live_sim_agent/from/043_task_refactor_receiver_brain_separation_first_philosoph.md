# Refactor Receiver Brain - Separation-First Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19 13:24:43
**Type:** task
**Priority:** medium

---

## Priority: High

## Part of Objective-First Brain Refactor

## Summary
Receiver brain should focus on GETTING OPEN and GAINING YARDS, not on "beating the DB".

## Correct Philosophy
- Target = create separation (open space between you and coverage)
- DB is an OBSTACLE between you and open, not someone to "beat"
- Routes create separation through spacing and timing, not through winning 1v1
- After catch = ballcarrier philosophy (yards toward endzone)
- Contested catches happen when separation failed, not as a goal

## Key File
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/receiver_brain.py`

## Decision Framework
```
1. Run route to designated spot (creates timing with QB)
2. Create separation (use speed, cuts, leverage)
3. Find the ball, make the catch
4. After catch: GAIN YARDS (defenders are now obstacles)
```

## Key Changes
1. Route running is about GETTING TO OPEN SPACE on time
2. Breaks/cuts create separation, dont "beat" the DB
3. Adjustments are about finding open windows, not exploiting DB
4. YAC is ballcarrier mentality - yards first, defenders are obstacles