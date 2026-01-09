# Draft Value System

This document describes the draft prospect generation system, providing data-driven models for realistic drafts with appropriate uncertainty and variance by position.

## Overview

The draft value system addresses key questions:
- **Pick Value**: How much is each draft pick worth?
- **Hit Rates**: What % of picks become starters/stars/busts?
- **Position Variance**: Which positions are boom/bust vs. safe?
- **Scouting Error**: How much does true talent differ from scouted grade?
- **Development Speed**: How quickly do players reach their potential?

## Key Findings

### 1. Pick Value Curve

Value drops steeply after the top 10 picks:

```
Pick Value (relative to #1 = 100):
Pick   1: 100    Pick  10: 64     Pick  50: 45
Pick   5:  80    Pick  32: 35     Pick 100: 34
```

### 2. Position Matters More in Later Rounds

| Round | Best Positions | Avoid |
|-------|----------------|-------|
| 1 | TE, DL, RB (50%+ star rate) | OL (20% bust rate) |
| 2 | EDGE, WR, DL | QB (17% bust) |
| 3 | LB, WR (30% star) | **QB (43% bust, 0% star)** |
| 4+ | RB, LB | QB, TE |

**Critical insight**: Never draft a QB after round 2. The data shows 0% star rate and 43% bust rate for round 3+ QBs.

### 3. Position Variance (Boom/Bust Potential)

| Variance | Positions | Characteristics |
|----------|-----------|-----------------|
| **High** (CV > 1.0) | QB, RB, TE, WR | More upside AND downside |
| **Medium** (CV 0.9-1.0) | DL, LB, EDGE, CB | Balanced risk/reward |
| **Low** (CV < 0.9) | S, OL | Safest picks, limited upside |

### 4. Scouting Accuracy

Some positions are much harder to scout than others:

| Difficulty | Positions | Error Std | Implications |
|------------|-----------|-----------|--------------|
| **Hard** | QB, WR, RB, TE | 1.0-1.2 | True talent varies wildly from grade |
| **Medium** | EDGE, S | 0.8 | Moderate uncertainty |
| **Easy** | DL, LB, CB | 0.6-0.8 | What you see is what you get |

### 5. Development Speed

| Speed | Positions | Peak Year | Early Contributor Rate |
|-------|-----------|-----------|----------------------|
| **Fast** | RB, WR | 3.3-3.4 | 30-35% contribute year 1-2 |
| **Normal** | QB, CB, TE, S, EDGE, LB | 3.6-4.0 | 20-25% early |
| **Slow** | OL, DL | 4.3-4.4 | 14-15% early |

## Usage Examples

### Evaluating a Draft Pick

```python
from huddle.core.ai.draft_value import (
    get_hit_rates,
    get_position_variance,
    should_draft_position,
)

# Is this a good pick?
position = 'QB'
round_num = 3

good_value, reason = should_draft_position(position, round_num)
print(f"Draft {position} in round {round_num}? {good_value}")
# Output: Draft QB in round 3? False
# Reason: High bust rate (43%)

# Compare positions
for pos in ['QB', 'LB', 'WR']:
    rates = get_hit_rates(pos, 3)
    print(f"{pos}: starter={rates['starter']:.0%}, star={rates['star']:.0%}")
# QB:  starter=43%, star=0%
# LB:  starter=70%, star=30%  <-- Best round 3 value
# WR:  starter=71%, star=29%
```

### Generating Prospects

```python
from huddle.core.ai.draft_value import generate_prospect_outcome

# Generate a 1st round QB prospect
prospect = generate_prospect_outcome(
    position='QB',
    pick=5,
    scouted_grade=85.0,
)

print(prospect)
# {
#     'scouted_grade': 85.0,      # What scouts see
#     'true_potential': 87.3,     # Hidden actual ceiling
#     'development_speed': 'normal',
#     'expected_outcome': 'starter',
#     'boom_probability': 0.16,    # 16% chance to exceed projections
#     'bust_probability': 0.05,    # 5% chance to bust badly
#     'pick_value': 80.0,
# }
```

### Generating a Draft Class

```python
from huddle.core.ai.draft_value import generate_draft_class

positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'CB', 'S', 'LB', 'EDGE', 'DL']
draft_class = generate_draft_class(positions, num_prospects=250, random_seed=42)

# Top prospects
for p in draft_class[:5]:
    print(f"{p['position']:4} Grade: {p['scouted_grade']:.1f} "
          f"True: {p['true_potential']:.1f} Outcome: {p['expected_outcome']}")
```

### Contract/Trade Decisions

```python
from huddle.core.ai.draft_value import get_pick_value

# What's fair trade value?
pick_32 = get_pick_value(32)  # 35.0
pick_50 = get_pick_value(50)  # 45.3
pick_64 = get_pick_value(64)  # 45.3

# Pick 32 + Pick 64 ≈ Pick 50 in value? No:
# 35.0 + 45.3 = 80.3 >> 45.3
# Two mid-round picks are worth more than one!
```

## API Reference

### Core Functions

```python
get_pick_value(pick: int) -> float
    """Get expected value for a draft pick (pick 1 = 100)."""

get_round(pick: int) -> int
    """Convert overall pick to round number."""

get_hit_rates(position: str, round_num: int) -> Dict[str, float]
    """Get hit rates {'starter', 'star', 'bust'} for position at round."""

get_position_variance(position: str) -> Dict
    """Get variance characteristics {'cv', 'tier', 'boom_mult', 'bust_mult'}."""

get_scouting_error(position: str) -> Dict
    """Get scouting error parameters {'mean', 'std', 'range'}."""

get_development_speed(position: str) -> Dict
    """Get development speed {'speed', 'mean_peak_year', 'early_rate'}."""
```

### Prospect Generation

```python
generate_prospect_outcome(
    position: str,
    pick: int,
    scouted_grade: float = 70.0,
    random_seed: Optional[int] = None
) -> Dict
    """Generate a realistic prospect with hidden talent and outcomes."""

get_draft_grade_range(pick: int) -> Tuple[float, float]
    """Get typical scouted grade range (min, max) for a draft pick."""

generate_draft_class(
    positions: List[str],
    num_prospects: int = 250,
    random_seed: Optional[int] = None
) -> List[Dict]
    """Generate a full draft class of prospects."""
```

### Decision Support

```python
should_draft_position(position: str, round_num: int) -> Tuple[bool, str]
    """Advise whether a position is good value at a given round."""
```

## Integration with Other Systems

### Development Curves

The draft system integrates with `development_curves.py`:

```python
from huddle.core.ai.development_curves import get_peak_age, project_performance
from huddle.core.ai.draft_value import generate_prospect_outcome

# Generate prospect
prospect = generate_prospect_outcome('QB', pick=10, scouted_grade=80)

# Project their development
rookie_age = 22
peak_age = get_peak_age('QB')  # 29

# Their true potential rating at peak
peak_rating = project_performance(
    position='QB',
    current_age=rookie_age,
    current_rating=prospect['true_potential'],
    target_age=peak_age
)
```

### Salary Allocation

Combine with `allocation_tables.py` for draft strategy:

```python
from huddle.core.ai.allocation_tables import get_rookie_premium
from huddle.core.ai.draft_value import get_hit_rates

# Should we draft OL or sign in FA?
ol_premium = get_rookie_premium('OL', 'offense')  # 5.0x value
ol_hit_r1 = get_hit_rates('OL', 1)  # 60% starter, 20% star, 20% bust

# OL: High rookie premium BUT risky in round 1 (20% bust)
# Strategy: Draft OL in round 2-3 where hit rates are better
```

## Data Sources

- **Contracts**: `research/data/cached/contracts.parquet` (21K drafted players)
- **Offensive Performance**: `seasonal_stats.parquet` (fantasy points)
- **Defensive Performance**: `defensive_value.parquet` (DV metric)
- **Analysis Period**: 2015-2021 drafts, 2019-2024 performance

## File Locations

| File | Description |
|------|-------------|
| `huddle/core/ai/draft_value.py` | Game integration module |
| `research/exports/draft_value_analysis.json` | Raw analysis output |
| `research/scripts/draft_value_analysis.py` | Analysis pipeline |

## Regenerating Analysis

```bash
# Run the analysis pipeline
python research/scripts/draft_value_analysis.py
```

## Key Takeaways for AI Decisions

1. **Don't draft QBs after round 2** - 0% star rate, 43% bust rate
2. **LB and WR are round 3 gems** - 30% star rate, low bust rate
3. **High variance positions (QB/RB/WR/TE)** - Worth the risk in round 1, dangerous later
4. **Low variance positions (S/OL)** - Safe picks but limited upside
5. **Scouting is unreliable for skill positions** - QB/WR/RB grades vary ±20% from true talent
6. **Development matters** - OL/DL take 4+ years to peak; RB/WR contribute early
