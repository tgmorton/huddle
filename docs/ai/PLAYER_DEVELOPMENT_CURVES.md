# Player Development Curves

This document describes the player development system used for modeling player potential (growth) and regression (decline) based on age.

## Overview

Player careers follow predictable arcs by position:

```
Performance
    ▲
    │            ┌─── Peak Age
    │         ┌──┴──┐
    │      ┌──┘     └──┐
    │   ┌──┘           └──┐
    │ ┌─┘ Growth    Decline └─┐
    │─┘                       └─
    └──────────────────────────────► Age
      21    25    Peak    35    40
```

- **Growth Phase**: Performance increases as players gain experience and reach physical maturity
- **Peak/Prime**: Optimal performance window, varies by position
- **Decline Phase**: Performance decreases due to aging, injury accumulation, speed loss

## Position Curves

### Peak Ages

| Position | Peak Age | Prime Years | Notes |
|----------|----------|-------------|-------|
| **Offense** |
| QB | 29 | 27-33 | Long prime, experience compensates |
| RB | 26 | 24-28 | Earliest peak, contact wear |
| WR | 27 | 25-30 | Speed-dependent |
| TE | 28 | 26-31 | Dual-role extends prime |
| OL | 28 | 26-32 | Technique-heavy, long careers |
| **Defense** |
| CB | 27 | 25-29 | Most speed-dependent |
| S | 28 | 26-30 | Less speed-critical than CB |
| LB | 27 | 25-30 | Physical but technique matters |
| EDGE | 27 | 25-30 | Explosiveness key |
| DL | 28 | 26-31 | Power-based, slower decline |

### Growth Rates (% of peak per year)

| Position | Growth Rate | Development Speed |
|----------|-------------|-------------------|
| RB | 15% | Fast - physical maturity |
| CB | 12% | Fast - athleticism |
| LB | 12% | Fast - physical position |
| WR | 12% | Medium - route technique |
| TE | 10% | Medium - dual skills |
| S | 10% | Medium |
| EDGE | 10% | Medium - technique + power |
| QB | 8% | Slow - mental game |
| OL | 8% | Slow - technique heavy |
| DL | 8% | Slow - technique heavy |

### Decline Rates (% of peak per year)

| Position | Decline Rate | Decline Speed | Key Factor |
|----------|--------------|---------------|------------|
| RB | 12% | Fastest | Contact, speed loss |
| CB | 10% | Fast | Speed critical |
| EDGE | 8% | Medium-Fast | Explosiveness |
| LB | 7% | Medium | Physical demands |
| WR | 6% | Medium | Speed matters |
| S | 6% | Medium | Less speed-critical |
| TE | 5% | Slow-Medium | Power-based |
| DL | 5% | Slow | Power > speed |
| QB | 4% | Slowest | Experience compensates |
| OL | 4% | Slowest | Technique-based |

## Decline Schedules

Performance remaining as % of peak, by years past peak age:

| Years | RB | CB | EDGE | LB | WR | S | TE | DL | QB | OL |
|-------|----|----|------|----|----|---|----|----|----|----|
| 1 | 88 | 90 | 92 | 93 | 94 | 94 | 95 | 95 | 96 | 96 |
| 2 | 77 | 81 | 85 | 86 | 88 | 88 | 90 | 90 | 92 | 92 |
| 3 | 68 | 73 | 78 | 80 | 83 | 83 | 86 | 86 | 88 | 88 |
| 4 | 60 | 66 | 72 | 75 | 78 | 78 | 81 | 81 | 85 | 85 |
| 5 | 53 | 59 | 66 | 70 | 73 | 73 | 77 | 77 | 82 | 82 |
| 6 | 46 | 53 | 61 | 65 | 69 | 69 | 74 | 74 | 78 | 78 |

**Example**: A 30-year-old RB (4 years past peak of 26) performs at ~60% of their peak level.

## Usage in Game Systems

### Player Potential (Young Players)

For players under peak age, project their ceiling:

```python
from huddle.core.ai.development_curves import project_performance, get_potential_tier

# 23-year-old WR with 72 rating
current_age = 23
current_rating = 72
position = 'WR'

# Project to peak (age 27)
projected_peak = project_performance(position, current_age, current_rating, target_age=27)
# Result: ~86 rating at peak

# Get potential tier
tier = get_potential_tier(position, current_age, current_rating)
# Result: 'star' or 'starter' depending on league average
```

### Player Regression (Aging Players)

For players past peak age, apply decline:

```python
from huddle.core.ai.development_curves import get_regression_factor, is_in_prime

# 31-year-old RB (5 years past peak)
age = 31
position = 'RB'

# Check if still in prime
in_prime = is_in_prime(position, age)  # False (prime is 24-28)

# Get regression factor
factor = get_regression_factor(position, age)  # ~0.53 (53% of peak)

# Apply to rating
current_rating = 85
adjusted_rating = current_rating * factor  # ~45 effective rating
```

### Contract Decisions

Combine with salary allocation for value assessment:

```python
from huddle.core.ai.development_curves import get_years_past_peak, get_decline_rate
from huddle.core.ai.allocation_tables import get_market_value

position = 'RB'
age = 28
current_rating = 85

# Years of production left
years_past_peak = get_years_past_peak(position, age)  # 2 years

# Expected decline
decline_rate = get_decline_rate(position)  # 12% per year

# Market value
market = get_market_value(position, 'starter')  # ~0.75% of cap

# Decision: Don't pay market rate for declining RB
```

## API Reference

### Core Functions

```python
get_peak_age(position: str) -> int
get_prime_years(position: str) -> Tuple[int, int]
get_growth_rate(position: str) -> float
get_decline_rate(position: str) -> float
```

### Projection Functions

```python
project_performance(
    position: str,
    current_age: int,
    current_rating: float,
    target_age: int
) -> float

get_potential_tier(
    position: str,
    age: int,
    current_rating: float,
    league_avg_rating: float = 70.0
) -> str  # 'elite', 'star', 'starter', 'backup', 'depth'

get_regression_factor(position: str, age: int) -> float
```

### Utility Functions

```python
get_years_to_peak(position: str, current_age: int) -> int
get_years_past_peak(position: str, current_age: int) -> int
is_in_prime(position: str, age: int) -> bool
```

## Data Sources & Methodology

### Data
- `seasonal_stats.parquet` - Fantasy points for offense (2019-2024)
- `defensive_value.parquet` - DV metric for defense (2019-2024)
- `contracts.parquet` - Player birth dates and draft years

### Methodology
1. Join performance data with player ages
2. Group by position and age bucket
3. Compute performance percentiles at each age
4. Identify peak age (highest mean performance)
5. Fit growth curves (pre-peak) and decline curves (post-peak)

### Corrections Applied
Raw data showed survivorship bias (old players still active are the good ones), causing:
- Peaks appearing too late
- Decline rates appearing too low

We corrected using established literature:
- Mulholland & Jensen (2019, 2020) - age effects in FA performance
- Industry consensus on position aging curves
- Physical demands by position (speed vs. power vs. technique)

## Integration Points

| System | Usage |
|--------|-------|
| Player Generation | Set initial potential based on age + attributes |
| Season Progression | Apply age-based development/regression each year |
| Contract AI | Assess future value for extension decisions |
| Draft AI | Value young players' growth potential |
| Trade AI | Discount aging players, premium on young talent |
| Free Agency AI | Avoid overpaying for declining veterans |

## File Locations

| File | Description |
|------|-------------|
| `huddle/core/ai/development_curves.py` | Python module for game integration |
| `research/exports/player_development_curves.json` | Raw analysis output |
| `research/scripts/player_development_curves.py` | Analysis pipeline |
