# Refactor LB Brain - Playmaker-First Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19 13:24:43
**Type:** task
**Priority:** medium

---

## Priority: High

## Part of Objective-First Brain Refactor

## Summary
LB brain should focus on MAKING PLAYS (tackles, coverage, pressure), not on "reading keys" or "taking on blocks".

## Correct Philosophy
- Target = GET TO THE BALL and make the play
- Run defense: fill gap, TACKLE THE BALLCARRIER
- Pass defense: take away zone or cover man (same as DB philosophy)
- Blitz: GET TO QB (same as DL philosophy - OL are obstacles)
- Blockers are OBSTACLES between you and the ball, not targets

## Key File
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/lb_brain.py`

## Decision Framework
```
Run Defense:
1. Read run direction
2. Fill assigned gap / flow to ball
3. TACKLE THE BALLCARRIER (avoid/shed blocks to get there)

Pass Defense:
1. Drop to zone or match man
2. Read QB, break on ball
3. Prevent completion or tackle after catch

Blitz:
1. Target = QB
2. OL are obstacles (same as DL philosophy)
3. Get there and make the play
```

## Key Changes
1. Run fits are about GETTING TO BALL, blocks are obstacles
2. Coverage is prevention-focused (same as DB)
3. Blitz = DL philosophy (target QB, OL are obstacles)
4. Every decision is "how do I make this play" not "how do I beat this blocker"