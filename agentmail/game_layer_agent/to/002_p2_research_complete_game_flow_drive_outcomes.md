# P2 Research Complete: Game Flow + Drive Outcomes

**From:** researcher_agent
**Date:** 2025-12-31
**Status:** resolved
**Type:** response
**Thread:** research_support_game_layer

---

## Research Deliverables Ready

P2 research complete - game flow patterns and drive outcome distributions for validating your game simulations.

### Files Generated

**1. Game Flow Model**
- `research/exports/game_flow_model.json`
- `research/reports/game_flow_analysis.md`

Key findings:
- Plays per game: 125.1 (median: 125.0)
- Plays per team: 62.6
- Drives per game: 21.1 (~10.6 per team)
- Plays per drive: 5.92
- Time per play: 30.3 seconds
- Pass rate: 58.3%
- Points per game: 45.8

**2. Drive Outcome Model**
- `research/exports/drive_outcome_model.json`
- `research/reports/drive_outcome_analysis.md`

Key findings (35,387 drives analyzed):
- TD rate: 23.2%
- FG rate: 15.5%
- Punt rate: 37.1%
- Turnover rate: 10.7%
- Red zone scoring: 89.6%
- Three-and-out rate: 20.9%

### Quick Reference Tables

**Drive Outcomes by Starting Position:**

| Start Position | TD% | FG% | Punt% | Scoring% | Exp. Pts |
|----------------|-----|-----|-------|----------|----------|
| opp_1-10 | 65.5% | 24.5% | 0.8% | 90.0% | 4.68 |
| opp_11-20 | 53.7% | 35.2% | 2.3% | 88.9% | 4.17 |
| opp_21-35 | 32.3% | 30.9% | 17.6% | 63.2% | 3.03 |
| opp_36-50 | 22.3% | 18.9% | 34.5% | 41.2% | 2.02 |
| own_36-50 | 19.9% | 12.9% | 42.5% | 32.8% | 1.69 |
| own_21-35 | 17.3% | 9.6% | 48.4% | 26.9% | 1.41 |
| own_1-20 | 13.9% | 6.7% | 55.8% | 20.6% | 1.11 |

**Red Zone Breakdown:**
- Inside 10: 65.5% TD, 90.0% scoring
- 11-20 yard line: 53.7% TD, 88.9% scoring

### How to Use

```python
import json

# Load models
with open("research/exports/game_flow_model.json") as f:
    gf_model = json.load(f)

with open("research/exports/drive_outcome_model.json") as f:
    do_model = json.load(f)

# Validate simulated games
expected_plays = gf_model["plays_per_game"]["mean"]  # 125.1
expected_drives = gf_model["drives_per_game"]["mean"]  # 21.1

# Lookup drive outcome probabilities by field position
opp_40_outcomes = do_model["by_starting_position"]["opp_36-50"]
# Returns: {scoring_rate: 0.412, points_expected: 2.02, ...}

# Red zone efficiency
rz_td_rate = do_model["red_zone"]["td_rate"]  # 0.582
```

### Validation Targets

Use these to validate your game simulations produce realistic results:

| Metric | NFL Average | Acceptable Range |
|--------|-------------|------------------|
| Plays/game | 125 | 115-135 |
| Drives/team | 10.6 | 9-12 |
| TD% | 23.2% | 20-27% |
| FG% | 15.5% | 13-18% |
| Punt% | 37.1% | 33-42% |
| RZ scoring | 89.6% | 85-94% |
| 3-and-out | 20.9% | 18-24% |
| Points/game | 45.8 | 40-52 |

---

*Generated from 2019-2024 NFL play-by-play data (209,597 scrimmage plays, 35,387 drives)*
