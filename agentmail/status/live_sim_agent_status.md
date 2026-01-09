# Live Simulation Agent - Status

**Last Updated:** 2025-12-27
**Agent Role:** Core simulation systems, orchestrator, physics, resolution systems

---

## Current Session (2025-12-27)

### Context Restored

Reviewed inbox (86 messages) and status files. Key pending work from researcher_agent:

| Message | Topic | Priority | Status |
|---------|-------|----------|--------|
| 063 | Simulation Calibration Targets (completion, INT, YAC, run yards) | HIGH | Review complete |
| 064 | OL/DL Blocking Win Rates (pass pro, run blocking) | HIGH | Review complete |
| 065 | Deep OL/DL Data (box count, gaps, QB hit impact) | HIGH | Review complete |
| 066 | Rating Impact Model (quartile performance by rating) | HIGH | Review complete |
| 067 | Calibration Systems Implemented (health.py, calibration.py) | INFO | Acknowledged |
| 068 | QB Intangibles Behavioral Proposal | MEDIUM | Pending implementation |
| 069 | Arms Prototype Physics Feedback | MEDIUM | Pending review |

### Blocking System Status

The blocking system (`resolution/blocking.py`) is already well-calibrated:

- **Momentum-based leverage system** - smooth, realistic battles
- **NFL-calibrated win rates** - OL wins 90%+ pass pro, 70-85% run blocking
- **Play-level blocking quality** - 18% great, 17% poor, 65% average
- **Position-specific adjustments** - DT vs Edge differences
- **Quick beat mechanic** - 2-4% chance per tick for pass rush breakthrough

### What's Working Well

1. **Throw lead mechanics** - Fixed 2025-12-26, scripted throws now lead receivers
2. **Pre-snap reads** - QB evaluates defense, applies hot routes
3. **Break recognition** - DB cognitive delay based on play_rec + route difficulty
4. **All brain refactors** - Objective-first philosophy across all 7 position brains

---

## Research Calibration Summary

### Pass Game Targets (msg 063)

| Condition | Target Rate |
|-----------|-------------|
| Clean pocket | 67.2% |
| Under pressure | 41.1% (0.61x modifier) |
| Deep ball penalty | -7% per 10 yards |

### Run Game Targets (msg 063)

| Metric | NFL Target |
|--------|------------|
| Median | 3.0 yds |
| Mean | 4.3 yds |
| Stuff rate | 18.3% |
| Explosive (10+) | 10.8% |

### Rating Impact (msg 066)

| Position | Elite-Bad Spread |
|----------|-----------------|
| QB Comp% | 8.0% (63.5% - 55.5%) |
| RB YPC | 2.2 yds (5.7 - 3.5) |
| DL Pressure% | 8.3% (33.2% - 24.9%) |

### Box Count Effects (msg 065)

| Box Count | Stuff Rate | Explosive |
|-----------|------------|-----------|
| 5 | 10.0% | 19.1% |
| 7 (baseline) | 17.9% | 10.8% |
| 9 | 29.3% | 4.7% |

---

## Next Up

1. **Rating Impact Integration** - Wire quartile-based modifiers into passing/running resolution
2. **QB Intangibles** - Implement poise, anticipation, decision-making as behavioral modifiers
3. **Arms Prototype Review** - Evaluate condition-based moves vs probability-based

---

## V2 Simulation Structure

```
huddle/simulation/v2/
├── orchestrator.py         # Main loop, WorldState, phases
├── ai/                     # Player brains (QB, DB, LB, DL, OL, etc.)
├── resolution/             # Blocking, tackle, move resolution
├── systems/                # Route runner, coverage, passing
├── plays/                  # Routes, run concepts, schemes
├── core/                   # Vec2, entities, events, variance
├── physics/                # Movement, spatial, body
└── testing/                # Scenario runner, integration tests
```

---

## Coordination

| Agent | Status |
|-------|--------|
| behavior_tree_agent | All 7 brain refactors complete, objective-first |
| researcher_agent | Rich calibration data delivered, ready for integration |
| qa_agent | 64+ tests passing, evasion timing blocked |
| management_agent | Calibration systems (health.py) implemented |

---

## Files I Own

- `huddle/simulation/v2/orchestrator.py`
- `huddle/simulation/v2/resolution/*.py`
- `huddle/simulation/v2/systems/*.py`
- `huddle/simulation/v2/core/*.py`
- `huddle/simulation/v2/physics/*.py`
