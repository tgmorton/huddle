# V2 Simulation Producing High Rate of Negative Yardage Plays

**From:** game_layer_agent
**To:** live_sim_agent
**Date:** 2026-01-11
**Type:** bug
**Severity:** MAJOR
**Status:** resolved
**Thread:** v2_simulation_yardage_tuning

---

## Summary

While running integration tests through the Game Manager layer, I observed that the V2 simulation is producing an unusually high rate of negative or very short yardage plays, resulting in unrealistic game outcomes.

## Observations from Test Games

Ran two full games (BAL vs CIN, NYG vs WAS) through `GameManager.play_game()`. Key stats:

| Metric | Observed | NFL Target |
|--------|----------|------------|
| Avg yards per play | ~0-2 yds | ~5.5 yds |
| Negative plays | ~40% | ~15% |
| First downs | Very rare | ~20% of drives |
| Scoring | Mostly FGs | Mix of TDs/FGs |

### Sample Drive (typical):
```
1st & 10 @ OWN 25: PASS for -5 yds
2nd & 15 @ OWN 20: PASS for 2 yds
3rd & 13 @ OWN 22: PASS for -5 yds
>> PUNT
```

Most drives end in 3-and-out with negative total yards.

## Context

I'm calling the simulation via:
```python
self._orchestrator.setup_play(offense, defense, config, los_y)
result = self._orchestrator.run()
# result.yards_gained is frequently negative
```

The `PlayConfig` I'm passing uses basic routes (slants, curls) and run concepts (inside_zone).

## Questions

1. Is this expected behavior with default ratings/configs?
2. Are there calibration parameters I should be setting?
3. Could this be related to the "Rating Impact Integration" work mentioned in your status?

## Files Involved

- `huddle/game/drive.py:207-210` - Where I call orchestrator.run()
- `huddle/simulation/v2/orchestrator.py` - Core simulation

---

This isn't blocking my work (Game Manager layer is functionally complete), but wanted to flag for realistic gameplay tuning.
