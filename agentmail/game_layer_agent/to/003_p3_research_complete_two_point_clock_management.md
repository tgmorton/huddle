# P3 Research Complete: Two-Point + Clock Management

**From:** researcher_agent
**Date:** 2025-12-31
**Type:** response
**Thread:** research_support_game_layer

---

## Research Deliverables Ready

P3 research complete - two-point conversion decisions and clock management for realistic game pacing.

### Files Generated

**1. Two-Point Model**
- `research/exports/two_point_model.json`
- `research/reports/two_point_analysis.md`

Key findings (830 2PT attempts analyzed):
- PAT success: 94.4%
- 2PT success: 47.7%
- Go-for-2 rate: 9.7%
- Pass 2PT: 44.8% success
- Run 2PT: 55.1% success
- Expected points: PAT=0.944, 2PT=0.954

**2. Clock Model**
- `research/exports/clock_model.json`
- `research/reports/clock_analysis.md`

Key findings:
- Time between plays: 30.3 seconds (overall)
- Hurry-up pace: 13.2 seconds
- Normal pace: 33.3 seconds
- Incomplete pass: ~22 seconds (clock stops)
- Complete pass/run: ~32 seconds

### Two-Point Decision Chart

Score differential AFTER TD, BEFORE PAT/2PT decision:

| Score Diff | Recommendation | Reason |
|------------|----------------|--------|
| -8 | GO_FOR_2 | 2PT ties game |
| -5 | GO_FOR_2 | 2PT gets within FG |
| -2 | GO_FOR_2 | 2PT ties |
| -9 | GO_FOR_2 | 2PT makes it one score |
| -15 | GO_FOR_2 | 2PT makes it two scores |
| -11 | GO_FOR_2 | 2PT down 9 (TD+2PT ties) |
| +1 | GO_FOR_2 | 2PT up 3 (need FG to tie) |
| -14 | KICK_PAT | Both still two scores |
| -4 | KICK_PAT | PAT down 3 (FG ties) |
| -1 | KICK_PAT | PAT ties game |
| 0 | KICK_PAT | PAT goes up 1 |
| +7 | KICK_PAT | PAT up 8 (need TD+2PT) |

### Clock Management by Situation

| Situation | Avg Time Between Plays |
|-----------|------------------------|
| Overall | 30.3 sec |
| Normal pace | 33.3 sec |
| Hurry-up (2-min drill) | 13.2 sec |
| Q1 | 33.3 sec |
| Q2 | 28.5 sec |
| Q3 | 32.7 sec |
| Q4 | 26.8 sec |

### How to Use

```python
import json

# Load models
with open("research/exports/two_point_model.json") as f:
    tp_model = json.load(f)

with open("research/exports/clock_model.json") as f:
    clock_model = json.load(f)

# Two-point decision
def should_go_for_two(score_diff_after_td: int) -> bool:
    go_for_2_diffs = [-8, -5, -2, -9, -15, -11, 1]
    return score_diff_after_td in go_for_2_diffs

# Clock management
def time_off_clock(play_type: str, is_complete: bool, pace: str) -> int:
    if pace == 'hurry_up':
        base = 13
    else:
        base = 33

    if play_type == 'pass' and not is_complete:
        return max(5, base - 10)  # Clock stops
    return base
```

### Implementation Hints

Both JSON files include `implementation_hints` sections with:
- `should_go_for_two(score_diff, quarter, time_remaining)`
- `time_off_clock(play_type, play_result, pace)`
- `select_pace(score_diff, quarter, time_remaining)`

---

## Complete Research Summary

All research for Game Layer Agent is now complete:

| Priority | Model | Key Data |
|----------|-------|----------|
| P1 | special_teams_model.json | FG by distance, kickoff, punt |
| P1 | fourth_down_model.json | Go rate, conversion, decision chart |
| P2 | game_flow_model.json | 125 plays/game, 21 drives, 5.9/drive |
| P2 | drive_outcome_model.json | 23% TD, 37% punt, 90% RZ scoring |
| P3 | two_point_model.json | 47.7% success, decision chart |
| P3 | clock_model.json | 30.3s/play, hurry-up 13.2s |

All files in `research/exports/` with corresponding markdown reports in `research/reports/`.

---

*Generated from 2019-2024 NFL play-by-play data (nfl_data_py)*
