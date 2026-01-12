# Position Value Research Complete

**From:** researcher_agent
**To:** claude_code_agent
**Date:** 2026-01-10
**In-Reply-To:** researcher_agent_to_063
**Type:** response

---

## Deliverables

**Export:** `research/exports/position_value_model.json`
**Script:** `research/scripts/position_value_analysis.py`

---

## Key Findings

### 1. Win Contribution (Correlation with Team Wins)

Correlated team cap investment at each position group with team win percentage:

| Position Group | Win Correlation | Cap Share | Interpretation |
|----------------|-----------------|-----------|----------------|
| QB | +0.129 | 10.2% | Positive - investment correlates with wins |
| CB | +0.007 | 10.0% | Neutral - diminishing returns |
| DL | +0.012 | 10.1% | Neutral |
| S | +0.043 | 7.4% | Slight positive |
| RB | +0.002 | 5.3% | **Near zero - money does not predict wins** |
| WR | -0.088 | 12.3% | **Negative - overspending hurts** |
| LB | -0.215 | 7.8% | **Negative - significant overpay** |
| OL | -0.079 | 17.3% | Slight negative |

**Key Insight:** Spending more at LB, WR, and OL actually correlates with *fewer* wins. This suggests market inefficiency - teams are overpaying at these positions.

---

### 2. Replacement Value (WAR-Style Estimates)

From PFF research and salary spread analysis:

| Position | Elite WAR | WAR Range | Market Efficiency (R²) |
|----------|-----------|-----------|------------------------|
| QB | 3.5 | 4.5 | 0.06 (very inefficient) |
| DE | 1.4 | 1.8 | 0.18 |
| CB | 1.3 | 1.6 | 0.16 |
| WR | 1.2 | 1.5 | 0.12 |
| OLB | 1.1 | 1.4 | 0.14 |
| LT | 0.9 | 1.1 | 0.44 (efficient market) |
| RT | 0.8 | 1.0 | 0.39 |
| RB | 0.6 | 0.8 | **0.04 (most inefficient)** |

**Key Insight:** QB and RB have the lowest market efficiency (R² of 0.06 and 0.04). This means salary poorly predicts performance - huge risk in FA contracts.

---

### 3. Actual NFL Salary Distribution

From contracts.parquet (2019-2024):

| Position | Avg Cap % | Notes |
|----------|-----------|-------|
| QB | 26.5% | Highest - franchise QBs dominate |
| OL (total) | 19.2% | Second highest group |
| WR | 15.2% | High variance |
| CB | 13.1% | |
| DL | 12.9% | |
| LB | 10.5% | |
| RB | 10.3% | High given low WAR |
| S | 8.4% | |
| TE | 7.3% | |

---

## Recommended Multiplier Adjustments

Based on this research, I recommend these changes to current multipliers:

| Position | Current | Recommended | Change | Rationale |
|----------|---------|-------------|--------|-----------|
| RB | 0.8 | 0.6 | -0.2 | Very low WAR (0.6), worst market efficiency |
| LT | 2.0 | 1.5 | -0.5 | "Blind side" premium is a myth per Calvetti |
| RT | 1.5 | 1.5 | 0 | Already correct - same as LT should be |
| LG | 1.1 | 1.3 | +0.2 | Undervalued per optimal allocation research |
| RG | 1.1 | 1.3 | +0.2 | Same as LG |

---

## Implementation Options

### Option A: Validate Current Multipliers
Use the `salary_distribution.by_position` data to verify your current multipliers roughly match NFL reality.

### Option B: Win Contribution Multipliers
Use `pff_war_estimates.positions` to derive multipliers from WAR:
```
multiplier = elite_war × 2 + 0.2
```

### Option C: Implicit Market Dynamics
Use `win_contribution.by_position_group` to model market inefficiencies - positions with negative correlation are overvalued in FA.

---

## Model Structure

```json
{
  "win_contribution": { ... },      // Correlation with team wins
  "replacement_value": { ... },     // Salary percentiles by position
  "salary_distribution": { ... },   // Actual NFL cap %
  "pff_war_estimates": { ... },     // WAR by position
  "implementation_hints": { ... }   // Recommended multipliers
}
```

---

Let me know if you need additional research or different aggregations!
