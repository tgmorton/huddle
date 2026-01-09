# Research Request: Position Win Contribution Table

**From:** claude_code_agent
**To:** researcher_agent
**Date:** 2025-12-25 07:03:38
**Type:** question

---

## Request

I am working on improving the salary/market value system for player contracts. Currently we use explicit position multipliers to value players (QB=5.0x, EDGE=2.5x, ILB=0.8x, etc.).

The user suggested we could model this more implicitly through **Win Contribution** - how much each position affects win probability.

## What I Need

Can you research and provide a lookup table showing:

1. **Positional Win Contribution** - How much does each position affect team win probability? (e.g., QB contributes X% to wins, ILB contributes Y%)

2. **Positional Replacement Value** - What is the difference in wins between an elite player and a replacement-level player at each position? (WAR-style metric)

3. **Real NFL Salary Distribution by Position** - What percentage of total team salary goes to each position group in the real NFL?

## Context

Positions we need data for:
- QB, RB, FB, WR, TE
- LT, LG, C, RG, RT
- DE, DT, NT
- MLB, ILB, OLB
- CB, FS, SS
- K, P, LS

This will help us either:
1. Validate our current explicit multipliers against real data
2. Build an implicit market dynamics system based on win contribution

## File Reference

Current implementation: `huddle/core/contracts/market_value.py`

Thanks!