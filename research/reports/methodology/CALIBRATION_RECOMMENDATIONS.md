# NFL Data Calibration Recommendations

**Prepared by:** researcher_agent
**Date:** December 2024
**For:** live_sim_agent, behavior_tree_agent, management_agent

---

## Executive Summary

This report compiles calibration targets derived from NFL data analysis to replace hardcoded simulation constants. All recommendations are based on 2019-2024 NFL data from nflfastR/nfl_data_py.

### Data Sources Analyzed:
- **Pass Game:** 121,640 pass plays (NGS + PBP)
- **Play Calling:** 208,784 offensive plays
- **Combine:** 3,133 athletes (2015-2024)
- **Contracts:** 30,280 contracts (2019-2024)
- **Draft:** 2,503 picks (2010-2019 with career outcomes)

---

## Part 1: Simulation Calibration (live_sim_agent)

### 1.1 Pass Game Targets

| Metric | NFL Target | Current Value | Notes |
|--------|------------|---------------|-------|
| Overall Completion % | 60.5% | Check | Based on 121k passes |
| Time to Throw | 2.79s avg | ~2.5s | May need adjustment |
| Avg Separation | 3.0 yards | Check | NGS data |
| Air Yards / YAC Split | 53% / 47% | Check | Balance matters |

#### Completion by Depth

```python
COMPLETION_BY_DEPTH = {
    'behind_los': 0.77,   # Screens, checkdowns
    '0_5': 0.74,          # Short passes
    '6_10': 0.63,         # Intermediate
    '11_15': 0.57,        # Mid-range
    '16_20': 0.52,        # Deep outs
    '21_30': 0.38,        # Deep
    '30+': 0.30,          # Bombs
}
```

#### Pressure Impact

```python
PRESSURE_MODIFIER = {
    'clean': 1.00,        # 67.2% base completion
    'hurried': 0.85,      # ~57% completion
    'hit': 0.61,          # 41.1% completion
}
```

#### QB Read Timing
- **10th percentile:** 2.46s (quick game)
- **Median:** 2.78s
- **90th percentile:** 3.14s (extended plays)
- **Recommendation:** Average 0.5-0.7s per read progression

### 1.2 Play Calling Tendencies

#### Base Pass Rates by Down

```python
PASS_RATE_BY_DOWN = {
    1: 0.55,   # 1st down - balanced
    2: 0.58,   # 2nd down - slight pass lean
    3: 0.70,   # 3rd down - varies by distance
    4: 0.70,   # 4th down (when going for it)
}
```

#### Key Situational Overrides

| Situation | Pass Rate | Notes |
|-----------|-----------|-------|
| 3rd & 1-2 | 25% | Short yardage runs |
| 3rd & 7+ | 85%+ | Obvious passing |
| Down 17+ | 72% | Comeback mode |
| Up 17+ Q4 | 39% | Run out clock |
| Red Zone | 48% | More balanced |

#### Score Differential Modifier

```python
SCORE_MODIFIER = {
    'down_17+': +0.15,    # Way behind
    'down_10-16': +0.10,
    'down_4-9': +0.05,
    'close_3': 0.00,      # Balanced
    'up_4-10': -0.05,
    'up_11-17': -0.10,
    'up_17+': -0.15,      # Way ahead
}
```

---

## Part 2: Player Generation (behavior_tree_agent)

### 2.1 Combine-Based Physical Profiles

Replace hardcoded position templates with these distributions:

#### Speed (40-yard dash) by Position

| Position | Mean | Std | 10th% | 90th% |
|----------|------|-----|-------|-------|
| CB | 4.49 | 0.09 | 4.37 | 4.61 |
| WR | 4.51 | 0.10 | 4.39 | 4.64 |
| S | 4.54 | 0.11 | 4.40 | 4.69 |
| RB | 4.57 | 0.12 | 4.42 | 4.71 |
| LB | 4.67 | 0.15 | 4.49 | 4.87 |
| EDGE | 4.74 | 0.16 | 4.55 | 4.94 |
| TE | 4.74 | 0.14 | 4.57 | 4.92 |
| QB | 4.79 | 0.16 | 4.58 | 4.98 |
| DL | 5.05 | 0.20 | 4.80 | 5.32 |
| OL | 5.22 | 0.18 | 4.99 | 5.45 |

#### Height/Weight by Position

| Position | Height (in) | Weight (lbs) |
|----------|-------------|--------------|
| OL | 76.9 ± 1.5 | 313 ± 12 |
| TE | 76.3 ± 1.5 | 250 ± 8 |
| EDGE | 75.4 ± 1.6 | 256 ± 17 |
| DL | 75.2 ± 1.4 | 300 ± 21 |
| QB | 74.6 ± 1.9 | 220 ± 11 |
| LB | 73.4 ± 1.5 | 236 ± 10 |
| WR | 72.8 ± 2.3 | 201 ± 15 |
| S | 72.1 ± 1.6 | 202 ± 10 |
| CB | 71.8 ± 1.7 | 192 ± 9 |
| RB | 70.4 ± 1.9 | 213 ± 14 |

### 2.2 Key Correlations

When generating players, apply these correlations:

| Attribute 1 | Attribute 2 | Correlation |
|-------------|-------------|-------------|
| 40-time | Weight | +0.86 (heavier = slower) |
| 40-time | Vertical | -0.73 (faster = higher jump) |
| 40-time | Broad Jump | -0.82 (faster = longer jump) |
| 3-cone | Shuttle | +0.87 (agility cluster) |
| Vertical | Broad Jump | +0.83 (explosion cluster) |
| Bench | Weight | +0.67 (heavier = stronger) |

**Recommendation:** Generate 40-time first, then derive correlated attributes.

---

## Part 3: Draft System (management_agent)

### 3.1 Success Rates by Round

| Round | Bust (<5 AV) | Starter+ | Star+ | Elite |
|-------|--------------|----------|-------|-------|
| 1 | 3% | 76% | 54% | 24% |
| 2 | 11% | 57% | 30% | 10% |
| 3 | 23% | 42% | 17% | 5% |
| 4 | 38% | 27% | 9% | 2% |
| 5 | 48% | 20% | 5% | 1% |
| 6 | 57% | 14% | 3% | 0% |
| 7 | 72% | 9% | 2% | 0% |

### 3.2 Prospect Tier Distribution

```python
TIER_BY_ROUND = {
    1: {'elite': 0.24, 'star': 0.30, 'starter': 0.22, 'role': 0.21, 'bust': 0.03},
    2: {'elite': 0.10, 'star': 0.20, 'starter': 0.27, 'role': 0.32, 'bust': 0.11},
    3: {'elite': 0.05, 'star': 0.12, 'starter': 0.25, 'role': 0.35, 'bust': 0.23},
    4: {'elite': 0.02, 'star': 0.07, 'starter': 0.18, 'role': 0.35, 'bust': 0.38},
    5: {'elite': 0.01, 'star': 0.04, 'starter': 0.15, 'role': 0.32, 'bust': 0.48},
    6: {'elite': 0.00, 'star': 0.03, 'starter': 0.11, 'role': 0.29, 'bust': 0.57},
    7: {'elite': 0.00, 'star': 0.02, 'starter': 0.07, 'role': 0.19, 'bust': 0.72},
}
```

### 3.3 Draft Class Composition

| Position | Picks/Year | % of Draft |
|----------|------------|------------|
| OL | 28 | 11.2% |
| WR | 26 | 10.5% |
| CB | 24 | 9.7% |
| EDGE | 22 | 8.8% |
| LB | 21 | 8.4% |
| DL | 18 | 7.2% |
| S | 14 | 5.6% |
| RB | 14 | 5.6% |
| TE | 10 | 4.0% |
| QB | 5 | 2.0% |

---

## Part 4: Contract System (management_agent)

### 4.1 Top-of-Market APY by Position

| Position | Top 5 Avg | Top 10 Avg | Starter | Depth |
|----------|-----------|------------|---------|-------|
| QB | $56.0M | $47.5M | $15.0M | $2.5M |
| EDGE | $26.5M | $23.0M | $10.0M | $2.0M |
| WR | $24.0M | $21.0M | $8.0M | $1.5M |
| CB | $20.5M | $17.5M | $7.5M | $1.5M |
| OL | $18.5M | $16.0M | $6.5M | $1.2M |
| DL | $17.0M | $14.5M | $6.0M | $1.2M |
| S | $14.5M | $12.5M | $5.5M | $1.0M |
| LB | $14.0M | $12.0M | $5.0M | $1.0M |
| TE | $12.0M | $10.5M | $4.5M | $0.9M |
| RB | $12.0M | $9.5M | $4.0M | $0.8M |

### 4.2 Age Depreciation Curves

| Position | Peak Age | Age 30 Value | Age 33 Value |
|----------|----------|--------------|--------------|
| QB | 28-32 | 100% | 95% |
| OL | 27-30 | 95% | 85% |
| WR | 26-28 | 90% | 70% |
| EDGE | 26-28 | 85% | 60% |
| CB | 25-27 | 80% | 55% |
| RB | 24-26 | 65% | 35% |

### 4.3 Guaranteed Money Patterns

| Tier | Guaranteed % |
|------|-------------|
| Elite (Top 5) | 55-70% |
| Top 10 | 45-55% |
| Starter | 35-45% |
| Depth | 20-35% |
| Minimum | <20% |

---

## Part 5: Implementation Priority

### High Priority (Simulation Feel)
1. Pass completion by depth model
2. QB read timing calibration
3. Pressure impact on accuracy
4. Play calling AI probabilities

### Medium Priority (Realism)
5. Combine-based physical profiles
6. Draft success rates by round
7. Contract market values

### Lower Priority (Polish)
8. Age depreciation curves
9. Guaranteed money patterns
10. Position correlations

---

## Appendix: Data Files

All raw data and figures are available in:
- `research/data/cached/` - Parquet files
- `research/data/figures/` - PNG visualizations
- `research/data/` - CSV exports

### Individual Reports
- `research/reports/pass_game_analysis.md`
- `research/reports/play_calling_analysis.md`
- `research/reports/combine_analysis.md`
- `research/reports/contract_analysis.md`
- `research/reports/draft_analysis.md`

---

*This report consolidates findings from multiple NFL data analyses. All statistics are derived from official NFL data sources via nfl_data_py.*
