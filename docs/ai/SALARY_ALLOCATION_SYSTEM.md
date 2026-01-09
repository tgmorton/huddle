# AI Salary Allocation System

This document describes the salary cap allocation intelligence system used by team AI for roster construction, free agency, and draft decisions.

## Overview

The salary allocation system implements a data-driven approach to NFL roster building, adapted from Calvetti's MIT thesis (2023) on optimizing capital allocation among offensive positions. We extended this framework to include defensive positions using a custom Defensive Value (DV) metric.

The system provides:
- **Effective salary conversion** - Valuing rookie contracts vs veteran contracts
- **Position market values** - Expected cap hit by position and tier
- **Optimal allocation targets** - Where to spend cap dollars
- **Position priority rules** - Dynamic prioritization based on roster state
- **Draft value assessment** - Which positions to target in the draft

## Theoretical Foundation

### The Calvetti Framework (5-Step Pipeline)

1. **Salary → Performance Regressions**
   - Fit separate regressions for rookies and veterans
   - Model: `Performance = α₀ + α₁ × log(1 + Salary)`
   - Captures diminishing returns on salary investment

2. **Effective Salary Conversion**
   - Convert rookie cap hit to veteran-equivalent value
   - Formula: `f(S_rookie) = multiplier × (1 + S_rookie)^exponent`
   - Allows apples-to-apples comparison of roster construction

3. **Performance → Team Output Regression**
   - Model: `PPG = β₀ + Σᵢ βᵢ×Perfᵢ + Σᵢⱼ βᵢⱼ×√(Perfᵢ×Perfⱼ)`
   - Interaction terms capture position synergies (QB-WR, RB-OL, etc.)

4. **Marginal Value Computation**
   - Compute ∂PPG/∂S_x for each position
   - Identifies where the next dollar provides most value

5. **Optimization**
   - Greedy or global optimization of cap allocation
   - Subject to cap constraints and roster minimums

## Data Sources

### Contracts Data
- **Source**: `research/data/cached/contracts.parquet`
- **Records**: 49,367 NFL contracts with year-by-year cap breakdowns
- **Fields**: Player, position, team, cap hit, cap percentage, draft info

### Performance Data

**Offensive Performance**: Fantasy points from `seasonal_stats.parquet`
- Aggregates passing, rushing, receiving production
- 3,716 offensive player-seasons

**Defensive Performance**: Defensive Value (DV) from `defensive_value.parquet`
- Custom metric computed from play-by-play data
- 8,920 defensive player-seasons

### Team Scoring
- PPG (Points Per Game) for offense evaluation
- PAPG (Points Against Per Game) for defense evaluation
- Derived from play-by-play data (2019-2024)

## Defensive Value (DV) Metric

Since fantasy points don't capture defensive production, we created a Defensive Value metric from play-by-play events:

| Event | Weight | Rationale |
|-------|--------|-----------|
| Interception | 5.0 | Game-changing play |
| Sack | 4.0 | Disrupts offense significantly |
| Forced Fumble | 3.0 | Creates turnover opportunity |
| Half Sack | 2.0 | Shared credit |
| Fumble Recovery | 2.0 | Ball security |
| Pass Defense | 1.5 | Prevents completion |
| Tackle for Loss | 1.0 | Negative play |
| QB Hit | 0.5 | Pressure without sack |
| Solo Tackle | 0.3 | Standard play |
| Assist Tackle | 0.15 | Shared credit |

**DV Leaders (2019-2024):**
- T.J. Watt (2021): 159.4 DV (22.5 sacks)
- Myles Garrett (2021): 128.5 DV
- Average by position: EDGE 31, S 24, CB 22, LB 22, DL 18

## Key Findings

### Rookie Contract Premium

The "effective salary" tells us what you'd pay a veteran for the same production a rookie provides:

**Offense:**
| Position | Effective Multiplier | Draft Priority |
|----------|---------------------|----------------|
| OL | 9.56x | HIGH |
| QB | 4.32x | HIGH |
| WR | 2.27x | HIGH |
| TE | 1.72x | Medium |
| RB | 0.39x | LOW |

**Defense:**
| Position | Effective Multiplier | Draft Priority |
|----------|---------------------|----------------|
| DL | 3.83x | HIGH |
| EDGE | 3.24x | HIGH |
| S | 2.23x | HIGH |
| LB | 1.16x | Medium |
| CB | 0.58x | LOW |

**Interpretation:**
- OL on rookie deals provide 9.56x their cap hit in equivalent veteran production
- RB rookies provide only 0.39x - veteran RBs are more efficient per dollar
- CB rookies underperform relative to salary - sign veteran CBs in FA

### Optimal Cap Allocation

Target percentages for a balanced roster:

**Offense (52% of cap):**
| Position | Target | Range | Priority |
|----------|--------|-------|----------|
| OL | 18% | 12-24% | 3 |
| WR | 12% | 8-16% | 2 |
| QB | 8.5% | 4-15% | 1 |
| TE | 4% | 2-7% | 4 |
| RB | 3% | 1-6% | 5 |

**Defense (48% of cap):**
| Position | Target | Range | Priority |
|----------|--------|-------|----------|
| EDGE | 12% | 8-16% | 1 |
| DL | 10% | 6-14% | 2 |
| CB | 10% | 6-14% | 3 |
| LB | 8% | 5-12% | 4 |
| S | 6% | 3-10% | 5 |

### Position Interaction Effects

Performance at one position affects the value of investing in another:

**Offensive Synergies:**
- Strong QB → Increases OL value, decreases WR/TE urgency
- Strong OL → Increases QB/WR value, decreases RB urgency
- Strong WR → Increases QB value

**Defensive Synergies:**
- Strong EDGE → Increases DL value, decreases CB urgency (rush helps coverage)
- Strong CB → Increases EDGE value (coverage buys time for rush)
- Strong DL → Increases EDGE value, decreases LB urgency

## API Reference

### Python Module

```python
from huddle.core.ai.allocation_tables import (
    get_effective_salary,
    get_market_value,
    get_optimal_allocation,
    get_allocation_gap,
    get_position_priority,
    get_rookie_premium,
    should_draft_position,
)
```

### Functions

#### `get_effective_salary(position, rookie_cap_pct, side='offense')`
Convert rookie cap hit to veteran-equivalent value.

```python
>>> get_effective_salary('QB', 1.0, 'offense')
4.32  # A QB on 1% rookie cap provides 4.32% veteran-equivalent value
```

#### `get_market_value(position, tier='starter')`
Get expected cap percentage for a position at a given tier.

```python
>>> get_market_value('QB', 'elite')
4.08  # Elite QBs cost ~4% of cap
>>> get_market_value('QB', 'starter')
0.84  # Starter QBs cost ~0.84% of cap
```

Tiers: `'elite'`, `'starter'`, `'backup'`, `'minimum'`

#### `get_optimal_allocation(position, side='offense')`
Get target allocation for a position.

```python
>>> get_optimal_allocation('QB', 'offense')
{'target': 8.5, 'range': [4.0, 15.0], 'priority': 1}
```

#### `get_allocation_gap(current_allocation, side='offense')`
Compare current allocation to optimal.

```python
>>> current = {'QB': 5.0, 'WR': 15.0, 'OL': 10.0, 'TE': 3.0, 'RB': 5.0}
>>> get_allocation_gap(current, 'offense')
{'QB': 3.5, 'WR': -3.0, 'OL': 8.0, 'TE': 1.0, 'RB': -2.0}
# Positive = under-invested, Negative = over-invested
```

#### `get_position_priority(strong_positions, weak_positions, side='offense')`
Get prioritized list of positions to invest in based on roster state.

```python
>>> get_position_priority(['QB', 'WR'], ['OL'], 'offense')
['OL', 'TE', 'RB', 'QB', 'WR']
# With strong QB/WR, prioritize OL; with weak OL, bump it up further
```

#### `should_draft_position(position, side='offense')`
Determine if a position is high-value to draft vs sign in FA.

```python
>>> should_draft_position('QB', 'offense')
True
>>> should_draft_position('RB', 'offense')
False
>>> should_draft_position('CB', 'defense')
False
```

## Usage Examples

### Draft Board Evaluation

```python
from huddle.core.ai.allocation_tables import (
    should_draft_position,
    get_rookie_premium,
    get_allocation_gap,
)

def evaluate_draft_pick(position, current_allocation, side):
    """Score a draft pick based on value and need."""

    # Base value from rookie premium
    premium = get_rookie_premium(position, side)
    base_value = premium['value_multiplier']

    # Need multiplier from allocation gap
    gaps = get_allocation_gap(current_allocation, side)
    need = max(0, gaps.get(position, 0)) / 10  # Normalize

    # Combine value and need
    return base_value * (1 + need)
```

### Free Agency Prioritization

```python
from huddle.core.ai.allocation_tables import (
    get_market_value,
    get_position_priority,
    get_optimal_allocation,
)

def prioritize_fa_targets(roster_strengths, roster_weaknesses, cap_space):
    """Rank positions for free agency targeting."""

    priorities = []

    for side in ['offense', 'defense']:
        strong = [p for p in roster_strengths if p in get_positions(side)]
        weak = [p for p in roster_weaknesses if p in get_positions(side)]

        ranked = get_position_priority(strong, weak, side)

        for rank, pos in enumerate(ranked):
            opt = get_optimal_allocation(pos, side)
            market = get_market_value(pos, 'starter')

            if market * cap_space / 100 > 0:  # Can afford
                priorities.append({
                    'position': pos,
                    'priority': opt['priority'] - rank,
                    'expected_cost': market,
                })

    return sorted(priorities, key=lambda x: x['priority'])
```

## File Locations

| File | Description |
|------|-------------|
| `huddle/core/ai/allocation_tables.py` | Python module for game integration |
| `research/exports/ai_allocation_tables.json` | Raw lookup tables in JSON |
| `research/exports/calvetti_allocation_analysis.json` | Full analysis results |
| `research/scripts/calvetti_allocation_analysis.py` | Analysis pipeline |
| `research/scripts/compute_defensive_value.py` | DV computation |
| `research/scripts/generate_ai_lookup_tables.py` | Table generator |

## Regenerating Tables

To update the analysis with new data:

```bash
# 1. Compute defensive value from PBP
python research/scripts/compute_defensive_value.py

# 2. Run Calvetti analysis
python research/scripts/calvetti_allocation_analysis.py

# 3. Generate AI lookup tables
python research/scripts/generate_ai_lookup_tables.py
```

## References

1. Calvetti, P.G. (2023). "Optimizing the Allocation of Capital Among Offensive Positions in the NFL". MIT Sloan School of Management.

2. Mulholland, J. & Jensen, S.T. (2019). "Optimizing the Allocation of Funds of an NFL Team under the Salary Cap".

3. Mulholland, J. & Jensen, S.T. (2020). "Predicting the Performance of NFL Free Agent Signings".

4. Draisey, L. (2016). "Fantasy Football: An Alternative Proxy for Player Quality".

5. Bhartiya, V. (2004). "Behavioral Economics: Analysis of Price Differentials in the NFL Labor Market". Duke University.
