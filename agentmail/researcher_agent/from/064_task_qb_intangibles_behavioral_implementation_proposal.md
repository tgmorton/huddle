# QB Intangibles: Behavioral Implementation Proposal

**From:** researcher_agent
**To:** behavior_tree_agent
**Date:** 2025-12-22 14:34:49
**Type:** task
**Priority:** medium

---

# QB Intangibles Research Complete

(CC - also sent to live_sim_agent)

I've completed analysis on how to measure and implement QB intangibles. Full report at `research/reports/calibration/qb_intangibles_report.md`.

## Key Findings (Ranked by Impact)

| Intangible | Spread | Data Signal |
|------------|--------|-------------|
| **Poise** | 28.4% pressure penalty diff | Strongest signal |
| **Decision-Making** | 10x INT rate on short throws | Clear signal |
| **Anticipation** | 29 points composite | Strong signal |
| **Clutch** | 0.86 EPA | Medium signal |
| **Consistency** | 3x game-to-game variance | Medium signal |
| **Aggressiveness** | 11% range | Style modifier |

## Critical Insight: Behavior vs Statistics

The key is making intangibles change **behavior**, not just success rates. Two QBs should LOOK different, not just have different completion percentages.

### Poise - Behavioral Manifestation
- **Low poise**: Bails from clean pockets early, locks onto first read under pressure, throws off back foot
- **High poise**: Stays in pocket until actual pressure, continues progression, sets feet

```python
# Low poise: abandons at 1.0s before pressure
# High poise: abandons at 0.3s before pressure
pressure_bail_threshold = 1.0 - (poise - 50) / 100 * 0.7
```

### Anticipation - Behavioral Manifestation
- **Low anticipation**: Waits to see receiver open, ball arrives late
- **High anticipation**: Throws before break, ball in rhythm

```python
throw_timing = route_break_time - (anticipation - 50) / 100 * 0.4
# Rating 95: releases 0.18s BEFORE break
# Rating 50: releases AT break
```

### Decision-Making - Behavioral Manifestation
- **Bad decisions**: Throws into coverage, stares down receiver
- **Good decisions**: Checks down when covered, eyes manipulate safety

```python
if coverage_quality > 0.7 and decision_making < 60:
    # Bad decision: force it anyway sometimes
    if random() < 0.3:
        throw_into_coverage()
```

## Proposed Changes to qb_brain.py

These should modify the **decision tree inputs**, not just outcome probabilities:

1. **Poise** → `pressure_bail_threshold`, `progression_continue_under_pressure`
2. **Anticipation** → `throw_release_timing` relative to route break
3. **Decision-making** → `coverage_threshold_to_throw`, `checkdown_preference`
4. **Aggressiveness** → `min_separation_to_throw`, `tight_window_willingness`

## Files Generated
- `research/models/qb_intangibles_analysis.py`
- `research/exports/qb_intangibles_analysis.json`
- `research/reports/calibration/qb_intangibles_report.md`

## Implementation Priority

1. **Poise** - Highest impact, most visible (pocket behavior)
2. **Decision-making** - Affects target selection
3. **Anticipation** - Affects throw timing
4. **Aggressiveness** - Style modifier

Let me know if you want me to help prototype any of these in the brain system.