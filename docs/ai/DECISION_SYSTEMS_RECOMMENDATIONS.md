# AI Decision Systems - Recommendations for Management

This report summarizes findings from four additional analyses and provides strategic recommendations for implementing AI decision systems in Huddle.

---

## Executive Summary

We analyzed NFL data to create frameworks for four key decision areas:

| Analysis | Data Source | Key Finding |
|----------|-------------|-------------|
| **Trade Value** | 1,627 actual trades (2002-2025) | Trading up in R1 costs original pick + 2 more |
| **Contract Timing** | Development curves + salary data | Extend 2-3 years BEFORE peak, not at peak |
| **FA Valuation** | Market rates + rookie premiums | Sign RBs and CBs in FA; draft QBs and OL |
| **Injury Risk** | 33,635 injury reports (2019-2024) | CB/WR/LB are highest injury risk |

---

## 1. Trade Value System

### Empirical Findings (from 1,627 actual NFL trades)

**Trade-Up Costs:**

| Target Round | Typical Cost |
|--------------|--------------|
| Round 1 | Original pick + 2 additional picks |
| Round 2-5 | Original pick + 1 additional pick |
| Round 6-7 | Even swap or conditional pick |

**Player Trade Returns:**

| Player Tier | Typical Return |
|-------------|----------------|
| Elite (Von Miller, Mack, CMC) | 2nd round pick |
| Good starter | 3rd-4th round pick |
| Average starter | 5th-6th round pick |
| Backup/role player | 6th-7th round or conditional |

### Recommendations for Implementation

1. **Use Jimmy Johnson chart as baseline** - Still accurate for pick-for-pick trades
2. **Future picks = 20-25% discount** - A 2026 1st is worth ~a current 2nd
3. **Player value factors**:
   - Years of control remaining (most important)
   - Contract surplus (cheap deals worth more)
   - Age relative to peak
   - Position (QB/EDGE > RB/LB)

### Decision API Suggestion

```
TradeEvaluator.evaluate(
    giving: [assets],
    receiving: [assets],
) → {fair: bool, value_difference: int, recommendation: str}
```

---

## 2. Contract Timing System

### Optimal Extension Windows

| Position | Optimal Age | Why |
|----------|-------------|-----|
| QB | 26-28 | Peak at 29, locks in 7 prime years |
| RB | 23-25 | Peak at 26, locks in 5 prime years |
| EDGE | 24-26 | Peak at 27, locks in 6 prime years |
| CB | 24-26 | Peak at 27, locks in 5 prime years |
| OL | 25-27 | Peak at 28, locks in 7 prime years |

**Key Insight**: Extend BEFORE peak to capture prime at pre-prime prices.

### Contract Length Guidelines

| Player Age vs Peak | Recommended Max Years |
|--------------------|----------------------|
| 3+ years before peak | 4-5 years |
| 1-2 years before peak | 3-4 years |
| At peak | 2-3 years |
| 1-2 years past peak | 1-2 years |
| 3+ years past peak | 1 year or don't extend |

### Extend vs. Replace Framework

| Position | Replace via... | When to Extend |
|----------|----------------|----------------|
| QB | Draft only | Almost always (very hard to replace) |
| EDGE | Draft preferred | Elite players only past 29 |
| OL | Draft preferred | Technique ages well, can extend older |
| WR | Draft or FA | Only elite, avoid 30+ |
| RB | FA preferred | Never past age 27 |
| CB | FA preferred | Never past age 29 |

### Decision API Suggestion

```
ContractAdvisor.should_extend(
    player: Player,
    proposed_years: int,
    proposed_apy: float,
) → {decision: str, rationale: str, max_years: int, max_apy: float}
```

---

## 3. Free Agency Valuation System

### Position Tiers (Draft vs FA Preference)

| Tier | Positions | Strategy |
|------|-----------|----------|
| **Sign in FA** | RB, CB | 0.39x and 0.58x rookie premium - vets are more efficient |
| **Either** | LB, TE | Moderate premium - either approach works |
| **Draft** | WR, S, DL | 2.0-2.3x premium - draft provides edge |
| **Always Draft** | QB, OL, EDGE | 3.2-9.6x premium - draft much better value |

### FA Target Evaluation Framework

**Value Score (0-100):**
- Base value from rating (40-100 → 0-60 points)
- Age factor (+10 if pre-prime, -5 to -30 if past prime)
- Position multiplier (RB = 1.5x, QB = 0.4x for FA purposes)
- Injury discount (clean = 1.0, major = 0.7)

**Cost Score (0-100):**
- Based on expected cap hit (0% = 0, 4% = 100)

**Classification:**
- Value/Cost > 1.5 = STRONG BUY
- 1.2-1.5 = BUY
- 0.9-1.2 = FAIR VALUE
- 0.7-0.9 = OVERPRICED
- < 0.7 = AVOID

### Recommendations for Implementation

1. **Spend heavily on**: Peak-age RBs, proven CBs age 26-28, LBs
2. **Spend moderately on**: WR2/WR3 types, rotational DL, TEs
3. **Spend sparingly on**: QBs (only backups), OL, EDGE

### Decision API Suggestion

```
FAEvaluator.score_target(
    player: Player,
) → {value_score: float, expected_cost: float, classification: str}
```

---

## 4. Injury Risk System

### Position Durability Rankings

| Durability | Positions | Implication |
|------------|-----------|-------------|
| **High** (70+) | QB, EDGE, DL, TE | Can commit to longer deals |
| **Medium** (40-70) | RB, S | Factor in injury risk to value |
| **Low** (<40) | LB, WR, CB, OL | Need depth, limit guarantees |

### Games Missed Per Season (League-Wide)

| Position | Avg Games Missed/Season | Risk Level |
|----------|-------------------------|------------|
| OL | 173 | High (but 5 starters/team) |
| CB | 152 | High |
| WR | 137 | High |
| LB | 134 | Medium-High |
| S | 88 | Medium |
| RB | 79 | Medium |
| QB | 32 | Low |

### Top Injury Types by Position

| Position | Primary Injuries |
|----------|------------------|
| QB | Knee, Ankle, Concussion |
| RB | Ankle, Knee, Hamstring |
| WR | Hamstring, Knee, Ankle |
| CB | Hamstring, Knee, Ankle |
| EDGE | Knee, Ankle, Shoulder |

### Recommendations for Implementation

1. **Contract implications**:
   - CB/WR/LB: Limit guaranteed money, include injury protections
   - QB/DL: More comfortable with guarantees

2. **Roster depth priorities**:
   - Budget 2-3 IR spots for CB/WR
   - Always have competent backup QB
   - OL depth critical (5 starters = more exposure)

3. **Player evaluation adjustments**:
   - Minor injury history: -5 to -10% value
   - Major injury history: -15 to -25% value
   - Age + injury combo: Additional discount

### Decision API Suggestion

```
InjuryRiskAssessor.evaluate(
    player: Player,
    injury_history: List[Injury],
) → {durability_score: float, risk_factors: List[str], value_adjustment: float}
```

---

## Integration Architecture

### Recommended Decision Flow

```
                    ┌─────────────────┐
                    │   Game State    │
                    │ (roster, cap,   │
                    │  needs, picks)  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Draft Decision │ │   FA Decision   │ │ Contract Decision│
│                 │ │                 │ │                  │
│ • Draft Value   │ │ • FA Valuation  │ │ • Contract Timing│
│ • Development   │ │ • Salary Alloc  │ │ • Development    │
│   Curves        │ │ • Injury Risk   │ │ • Trade Value    │
└────────┬────────┘ └────────┬────────┘ └────────┬─────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   AI Decision   │
                    │ (with rationale)│
                    └─────────────────┘
```

### Data Dependencies

| System | Required Inputs | Outputs |
|--------|-----------------|---------|
| Trade Value | Player rating, age, position, contract, picks involved | Fair value assessment |
| Contract Timing | Player rating, age, position | Extend/replace decision |
| FA Valuation | Player rating, age, position, injury history | Value score, bid amount |
| Injury Risk | Position, injury history | Durability score, value adjustment |

---

## Files Created

| File | Description |
|------|-------------|
| `research/scripts/trade_value_analysis.py` | Theoretical trade model |
| `research/scripts/trade_value_empirical.py` | Empirical trade analysis |
| `research/scripts/contract_timing_analysis.py` | Extension timing model |
| `research/scripts/fa_valuation_analysis.py` | FA target scoring |
| `research/scripts/injury_risk_analysis.py` | Injury risk model |
| `research/exports/trade_value_analysis.json` | Trade value data |
| `research/exports/trade_value_empirical.json` | Empirical trade data |
| `research/exports/contract_timing_analysis.json` | Contract timing data |
| `research/exports/fa_valuation_analysis.json` | FA valuation data |
| `research/exports/injury_risk_analysis.json` | Injury risk data |

---

## Next Steps

### Immediate (Use as-is)
- JSON exports can be loaded directly for AI decision logic
- Recommendations can inform game design documents

### Near-term (Wire into game)
- Create decision APIs that combine multiple systems
- Build AI GM personalities with different weights on each factor

### Future (Enhance with more data)
- Add scheme fit analysis (need play-by-play tagging)
- Add coaching impact (need coach history data)
- Add combine → success model (have combine data, need to analyze)

---

## Summary of Key Insights

| Category | Insight |
|----------|---------|
| Draft | Never draft QB after Round 2 (0% star rate) |
| Draft | OL rookies = 9.56x value (best draft position) |
| Trade | Trading up in R1 costs original + 2 picks |
| Contract | Extend 2-3 years BEFORE peak, not at peak |
| Contract | Never extend RBs past 27 (12%/year decline) |
| FA | Sign RBs and CBs in FA (0.39x, 0.58x rookie premium) |
| FA | Draft QBs, OL, EDGE (3.2-9.6x rookie premium) |
| Injury | CB/WR/LB highest risk - need depth and limit guarantees |
| Injury | QB lowest injury rate but highest impact when it happens |
