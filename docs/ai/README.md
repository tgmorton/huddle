# AI Decision Systems

This document provides an overview of the data-driven AI systems built for Huddle's team management simulation. These systems enable realistic, intelligent roster construction, player development, and draft decisions.

---

## Research Methodology

We followed a rigorous theory-to-implementation pipeline:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. Literature  │ → │  2. Data        │ → │  3. Analysis    │
│     Review      │    │     Collection  │    │     Pipeline    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   5 Academic Papers      NFL Data 2019-2024    Python Scripts
   - Calvetti (MIT)       - 49K contracts       - Regressions
   - Mulholland/Jensen    - 12K player-seasons  - Curve fitting
   - Bhartiya (Duke)      - Play-by-play        - Bias correction
   - Draisey
                                                      │
                                                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  6. Game        │ ← │  5. Lookup      │ ← │  4. Validation  │
│     Integration │    │     Tables      │    │     & Correction│
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   Python Modules         JSON Exports         Literature check
   - Clean APIs           - Position data      - Survivorship bias
   - Game-ready           - Rate tables        - Data limitations
```

### Academic Sources

| Paper | Author | Year | Contribution |
|-------|--------|------|--------------|
| Optimizing Capital Allocation in the NFL | Calvetti (MIT) | 2023 | Effective salary framework, position value |
| Optimizing Fund Allocation Under Salary Cap | Mulholland & Jensen | 2019 | Age effects, contract timing |
| Predicting FA Performance | Mulholland & Jensen | 2020 | Regression models, market efficiency |
| Fantasy Football as Player Proxy | Draisey | 2016 | Using fantasy points for offense |
| NFL Labor Market Behavioral Economics | Bhartiya (Duke) | 2004 | Market inefficiencies |

### Data Sources

| Dataset | Records | Fields | Usage |
|---------|---------|--------|-------|
| `contracts.parquet` | 49,367 | Salary, draft position, age, team | All systems |
| `seasonal_stats.parquet` | 3,716 | Passing, rushing, receiving stats | Offensive performance |
| `defensive_value.parquet` | 8,920 | Tackles, sacks, INTs, etc. | Defensive performance |
| Play-by-play (nflverse) | ~1M plays | Event-level data | DV metric computation |

---

## Executive Summary

We built three interconnected AI systems derived from NFL data analysis:

| System | Purpose | Key Insight |
|--------|---------|-------------|
| **Salary Allocation** | Optimal cap spending by position | OL rookies provide 9.6x value; don't draft RBs or CBs |
| **Development Curves** | Age-based growth and decline | RBs peak at 26 and decline fast; QBs peak at 29 and last |
| **Draft Value** | Prospect generation with uncertainty | Never draft a QB after round 2 (0% star rate, 43% bust) |

---

## Custom Metrics Created

### Defensive Value (DV)

Fantasy points capture offensive production but not defensive. We created a Defensive Value metric from play-by-play events:

| Event | Weight | Rationale |
|-------|--------|-----------|
| Interception | 5.0 | Game-changing turnover |
| Sack | 4.0 | Disrupts offense significantly |
| Forced Fumble | 3.0 | Creates turnover opportunity |
| Half Sack | 2.0 | Shared credit |
| Fumble Recovery | 2.0 | Ball security |
| Pass Defense | 1.5 | Prevents completion |
| Tackle for Loss | 1.0 | Negative play |
| QB Hit | 0.5 | Pressure without sack |
| Solo Tackle | 0.3 | Standard play |
| Assist Tackle | 0.15 | Shared credit |

**Validation**: T.J. Watt's 2021 season (22.5 sacks) = 159.4 DV, highest in dataset.

### Effective Salary

The Calvetti framework converts rookie cap hits to veteran-equivalent value:

```
Effective Salary = multiplier × (1 + rookie_cap_pct)^exponent
```

This allows apples-to-apples comparison: "A QB on a 1% rookie contract provides the same production as a veteran earning 4.32%."

---

## System 1: Salary Allocation

*Based on Calvetti's MIT thesis on NFL capital allocation*

### The Calvetti Framework (5-Step Pipeline)

1. **Salary → Performance Regressions**: Fit separate models for rookies and veterans
2. **Effective Salary Conversion**: Convert rookie cap hit to veteran-equivalent
3. **Performance → Team Output**: Model PPG/PAPG from position performance
4. **Marginal Value Computation**: Compute ∂PPG/∂Salary for each position
5. **Optimization**: Greedy allocation subject to cap constraints

### What It Does

Converts rookie contracts to veteran-equivalent value and provides optimal cap allocation targets by position.

### Key Findings

**Rookie Contract Premium** (effective salary / actual salary):

| High Value (Draft) | Low Value (Sign in FA) |
|--------------------|------------------------|
| OL: 9.56x | RB: 0.39x |
| QB: 4.32x | CB: 0.58x |
| DL: 3.83x | LB: 1.16x |
| EDGE: 3.24x | |

**Optimal Cap Allocation**:
- Offense (52%): OL 18%, WR 12%, QB 8.5%, TE 4%, RB 3%
- Defense (48%): EDGE 12%, DL 10%, CB 10%, LB 8%, S 6%

### Usage

```python
from huddle.core.ai.allocation_tables import (
    get_effective_salary,    # Rookie → veteran value
    get_market_value,        # Expected cap hit by tier
    should_draft_position,   # Draft vs FA decision
)

# A QB on 1% rookie cap provides 4.32% veteran-equivalent value
get_effective_salary('QB', 1.0)  # → 4.32
```

### Position Interaction Effects

Performance at one position affects the value of investing in another:

**Offensive Synergies**:
- Strong QB → Increases OL value (protection matters more)
- Strong OL → Increases QB/WR value, decreases RB urgency
- Strong WR → Increases QB value

**Defensive Synergies**:
- Strong EDGE → Decreases CB urgency (rush helps coverage)
- Strong CB → Increases EDGE value (coverage buys time)
- Strong DL → Increases EDGE value, decreases LB urgency

### Files
- `huddle/core/ai/allocation_tables.py` - Game integration
- `docs/ai/SALARY_ALLOCATION_SYSTEM.md` - Full documentation

---

## System 2: Player Development Curves

*Derived from NFL performance data with literature-informed corrections*

### What It Does

Models player performance trajectories by position, enabling:
- **Potential projection**: Project young players to their peak
- **Regression modeling**: Apply age-based decline to veterans
- **Contract timing**: Know when to extend vs. let walk

### Key Findings

**Peak Ages and Decline Rates**:

| Position | Peak Age | Decline Rate | Career Arc |
|----------|----------|--------------|------------|
| RB | 26 | 12%/year | Early peak, fast decline |
| CB | 27 | 10%/year | Speed-dependent |
| QB | 29 | 4%/year | Long prime, slow decline |
| OL | 28 | 4%/year | Technique extends career |

**Decline Schedule** (% of peak remaining):

| Years Past Peak | RB | CB | QB | OL |
|-----------------|----|----|----|----|
| 2 years | 77% | 81% | 92% | 92% |
| 4 years | 60% | 66% | 85% | 85% |
| 6 years | 46% | 53% | 78% | 78% |

### Usage

```python
from huddle.core.ai.development_curves import (
    get_peak_age,           # When does position peak?
    get_regression_factor,  # Age-based performance multiplier
    project_performance,    # Project rating to future age
    get_potential_tier,     # Classify young player ceiling
)

# A 31-year-old RB (5 years past peak) performs at 53% of peak
get_regression_factor('RB', 31)  # → 0.53

# Project a 23-year-old WR with 72 rating to peak (age 27)
project_performance('WR', 23, 72, 27)  # → 86
```

### Files
- `huddle/core/ai/development_curves.py` - Game integration
- `docs/ai/PLAYER_DEVELOPMENT_CURVES.md` - Full documentation

---

## System 3: Draft Value

*Analyzed 2015-2021 NFL drafts with 2019-2024 performance data*

### What It Does

Generates realistic draft prospects with:
- Appropriate uncertainty by position
- Hidden talent that differs from scouted grade
- Realistic hit rates by round and position
- Variable development speed

### Key Findings

**Hit Rates by Round** (critical for draft strategy):

| Position | Round 1 Star% | Round 3 Star% | Round 3 Bust% |
|----------|---------------|---------------|---------------|
| QB | 30% | **0%** | **43%** |
| LB | 28% | 30% | 13% |
| WR | 35% | 29% | 0% |
| EDGE | 38% | 12% | 21% |

**Position Variance** (boom/bust potential):

| High Variance | Medium Variance | Low Variance |
|---------------|-----------------|--------------|
| QB (CV=1.15) | DL (CV=0.98) | S (CV=0.82) |
| RB (CV=1.12) | EDGE (CV=0.94) | OL (CV=0.85) |
| TE (CV=1.11) | CB (CV=0.93) | |

**Scouting Accuracy** (how much true talent varies from grade):

| Hard to Scout | Easy to Scout |
|---------------|---------------|
| QB, WR, RB (std ~1.1) | DL, CB (std ~0.7) |

### Usage

```python
from huddle.core.ai.draft_value import (
    generate_prospect_outcome,  # Full prospect with hidden talent
    get_hit_rates,              # Starter/star/bust probabilities
    should_draft_position,      # Is this good value?
)

# Generate a realistic prospect
prospect = generate_prospect_outcome('QB', pick=5, scouted_grade=85)
# Returns: {
#     'scouted_grade': 85.0,
#     'true_potential': 87.3,     # Hidden!
#     'expected_outcome': 'starter',
#     'boom_probability': 0.16,
#     'bust_probability': 0.05,
# }

# Should we draft a QB in round 3?
should_draft_position('QB', 3)  # → (False, "High bust rate (43%)")
```

### Files
- `huddle/core/ai/draft_value.py` - Game integration
- `docs/ai/DRAFT_VALUE_SYSTEM.md` - Full documentation

---

## How the Systems Connect

```
┌─────────────────────────────────────────────────────────────────┐
│                        DRAFT DAY                                │
│  ┌──────────────────┐                                           │
│  │  Draft Value     │ → Prospect grade, hidden talent,         │
│  │  System          │   hit rates, development speed           │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │  Salary          │ → Should we draft this position          │
│  │  Allocation      │   or sign in free agency?                │
│  └────────┬─────────┘                                           │
└───────────┼─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SEASON PROGRESSION                         │
│  ┌──────────────────┐                                           │
│  │  Development     │ → Young players grow toward potential    │
│  │  Curves          │   Veterans decline based on age          │
│  └────────┬─────────┘                                           │
└───────────┼─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONTRACT DECISIONS                         │
│  ┌──────────────────┐   ┌──────────────────┐                    │
│  │  Development     │ + │  Salary          │ → Extension value │
│  │  Curves          │   │  Allocation      │   Free agency bids│
│  └──────────────────┘   └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### Example: Complete Roster Decision

```python
from huddle.core.ai.allocation_tables import get_rookie_premium, get_market_value
from huddle.core.ai.development_curves import get_years_past_peak, get_regression_factor
from huddle.core.ai.draft_value import get_hit_rates

# Should we extend our 28-year-old RB?
position = 'RB'
age = 28

# 1. Check development curve
years_past = get_years_past_peak(position, age)  # 2 years past peak (26)
regression = get_regression_factor(position, age)  # 0.77 (77% of peak)

# 2. Check market value
market = get_market_value(position, 'starter')  # 0.75% of cap

# 3. Check draft alternative
rookie_premium = get_rookie_premium(position, 'offense')  # 0.39x (bad!)
hit_rates = get_hit_rates(position, 2)  # Round 2: 79% starter, 29% star

# Decision: Don't extend the RB at market rate
# - He's already declining (77% of peak)
# - Will decline 12%/year going forward
# - Rookie RBs aren't great value (0.39x), but...
# - Round 2 RBs have 79% starter rate
# → Let him walk, draft RB in round 2-3
```

---

## Data Sources

| Dataset | Records | Usage |
|---------|---------|-------|
| `contracts.parquet` | 49,367 | Salary, draft position, age |
| `seasonal_stats.parquet` | 3,716 | Offensive performance (fantasy pts) |
| `defensive_value.parquet` | 8,920 | Defensive performance (DV metric) |

**Analysis Period**: 2019-2024 performance data, 2015-2021 drafts

---

## Strategic Insights for AI Teams

### Draft Strategy
1. **Never draft QB after round 2** - 0% star rate, 43% bust rate
2. **OL in round 2-3** - High rookie premium but risky in round 1
3. **LB/WR are round 3 gems** - 30% star rate, low bust rate
4. **Avoid late RBs** - Sign veterans in FA instead

### Free Agency Strategy
1. **Sign veteran RBs and CBs** - Rookie premiums are terrible (0.39x, 0.58x)
2. **Don't overpay for declining players** - RBs lose 12%/year, CBs lose 10%/year
3. **QBs hold value longest** - Only 4%/year decline, extend early

### Contract Timing
1. **Extend QBs/OL before peak** - They have long primes
2. **Let RBs walk at 28** - Already 2 years past peak
3. **CBs risky after 29** - Fast decline, speed-critical

---

## File Structure

```
huddle/core/ai/
├── allocation_tables.py    # Salary allocation system
├── development_curves.py   # Age-based development
└── draft_value.py          # Draft prospect generation

docs/ai/
├── README.md                      # This overview
├── SALARY_ALLOCATION_SYSTEM.md    # Detailed salary docs
├── PLAYER_DEVELOPMENT_CURVES.md   # Detailed development docs
└── DRAFT_VALUE_SYSTEM.md          # Detailed draft docs

research/
├── exports/
│   ├── ai_allocation_tables.json
│   ├── player_development_curves.json
│   └── draft_value_analysis.json
└── scripts/
    ├── calvetti_allocation_analysis.py
    ├── player_development_curves.py
    └── draft_value_analysis.py
```

---

## Methodology

All systems follow the same rigorous approach:

1. **Theory First**: Start with established research (Calvetti thesis, Mulholland & Jensen aging curves)
2. **Data Analysis**: Validate and extend with real NFL data
3. **Bias Correction**: Adjust for survivorship bias and data limitations
4. **Game Integration**: Create clean APIs for simulation use
5. **Documentation**: Comprehensive docs with usage examples

---

## Data Corrections & Limitations

### Survivorship Bias

Raw data showed unrealistic patterns because older players still active are survivors (the good ones):

| Position | Raw Data Peak | Corrected Peak | Raw Decline | Corrected Decline |
|----------|---------------|----------------|-------------|-------------------|
| WR | 33 | 27 | 0%/year | 6%/year |
| RB | 28 | 26 | ~0%/year | 12%/year |
| CB | 31 | 27 | ~0%/year | 10%/year |
| TE | 32 | 28 | ~0%/year | 5%/year |

**Correction Method**: Cross-referenced with Mulholland & Jensen aging curves and physical demands by position (speed vs power vs technique).

### Data Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Only 6 years of performance data | Can't track full careers | Used literature for career-length patterns |
| Fantasy points don't capture OL | Missing offensive line production | Added OL with literature-informed values |
| Defensive stats incomplete | Some events not tracked | Created weighted DV metric from available data |
| Small samples for some position/round combos | Noisy hit rates | Aggregated to larger buckets where needed |

### Validation

- T.J. Watt 2021 = highest DV (159.4) ✓
- RB decline matches "running back cliff" conventional wisdom ✓
- QB premium aligns with Calvetti thesis findings ✓
- Hit rates match industry consensus on draft value ✓

---

## Regenerating the Analysis

To update with new data:

```bash
# 1. Compute defensive value from play-by-play
python research/scripts/compute_defensive_value.py

# 2. Run Calvetti salary analysis
python research/scripts/calvetti_allocation_analysis.py

# 3. Generate allocation lookup tables
python research/scripts/generate_ai_lookup_tables.py

# 4. Run development curves analysis
python research/scripts/player_development_curves.py

# 5. Run draft value analysis
python research/scripts/draft_value_analysis.py
```

---

## References

1. Calvetti, P.G. (2023). "Optimizing the Allocation of Capital Among Offensive Positions in the NFL". MIT Sloan School of Management.

2. Mulholland, J. & Jensen, S.T. (2019). "Optimizing the Allocation of Funds of an NFL Team under the Salary Cap".

3. Mulholland, J. & Jensen, S.T. (2020). "Predicting the Performance of NFL Free Agent Signings".

4. Draisey, L. (2016). "Fantasy Football: An Alternative Proxy for Player Quality".

5. Bhartiya, V. (2004). "Behavioral Economics: Analysis of Price Differentials in the NFL Labor Market". Duke University.

6. NFL contracts data from Over The Cap (2019-2024)

7. NFL play-by-play data via nflverse (2019-2024)
