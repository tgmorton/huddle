# NFL Salary Cap Allocation: Research Synthesis

## Executive Summary

This report synthesizes findings from five academic papers examining NFL salary cap allocation, player valuation, and team-building strategy. The research spans 2004-2023 and employs various methodological approaches including linear regression, optimization models, recursive partitioning trees, and behavioral economics frameworks.

The collective findings challenge several conventional NFL wisdoms while providing quantitative frameworks for optimal resource allocation. Key themes emerge around the premium value of rookie contracts, the systematic overvaluation of certain positions and player characteristics, and the inherent difficulty of predicting future player performance.

---

## 1. The Fundamental Constraint: Salary Cap Economics

### 1.1 The Allocation Problem

Every NFL team faces a constrained optimization problem: maximize team performance subject to a hard salary cap. Unlike MLB or the NBA (with its luxury tax), the NFL's strict cap creates a true zero-sum resource allocation challenge. Every dollar spent on one position is a dollar unavailable elsewhere.

The cap has grown substantially over time ($120.4M in 2011 to $208.2M in 2022), making cross-season salary comparisons require normalization to percentage of cap rather than absolute dollars (Calvetti, 2023).

### 1.2 Cap Hit vs. Cash

A player's "cap hit" differs from their cash compensation. Signing bonuses are prorated across contract years, allowing teams to manipulate timing of cap charges. All research reviewed uses cap hit as the relevant measure since it represents the true constraint on team building (Mulholland & Jensen, 2019; Calvetti, 2023).

---

## 2. Measuring Player Value

### 2.1 Approximate Value (AV)

Pro Football Reference's Approximate Value emerges as the most commonly used cross-position performance metric. AV attempts to assign a single number to each player-season, calculated from a combination of:
- Team statistics (points per possession)
- Individual statistics (games played, games started)
- Achievement markers (Pro Bowl selection)
- Position-specific production metrics

While acknowledged as "very approximate," AV's key advantage is comparability across positions and seasons (Mulholland & Jensen, 2019; Calvetti, 2023).

**Limitations:** AV has an autocorrelation of only 0.65 between consecutive seasons, indicating substantial year-to-year variance even when predicting a player's own future performance (Calvetti, 2023).

### 2.2 Fantasy Points Per Game

Draisey (2016) introduces fantasy football points as an alternative unified metric. Despite its origins in recreational gaming, fantasy PPG proves remarkably predictive:
- Explains 46% of veteran salary variance as a single variable
- Each additional fantasy PPG correlates with ~11% higher cap value
- Provides intuitive cross-position comparison

### 2.3 Win Contribution

Mulholland & Jensen (2019) develop a "win contribution" metric by regressing team wins on AV by position, then using the resulting coefficients to convert individual AV into estimated wins added. This approach yielded an R² of 0.77 for the AV-to-wins regression.

### 2.4 NFL Career Score

For skill positions, Mulholland & Jensen (2020) propose:

```
NFL Career Score = Receiving Yards + (19.3 × Receiving Touchdowns)
```

The 19.3 multiplier derives from expected points analysis: a touchdown from the 1-yard line is worth 20.3 yards of field position, minus the 1 yard already gained.

---

## 3. The Rookie Contract Premium

### 3.1 Quantifying the Advantage

The single most consistent finding across all papers is the premium value provided by players on rookie contracts. Calvetti (2023) formalizes this through "effective salary" - the veteran contract equivalent of a rookie's cap hit based on expected performance:

**Key Finding:** Rookies provide approximately 2x value relative to their salary compared to veterans at the same position.

This manifests in the data:
- Average veteran cap hit: 3.74% of cap, Average AV: 1.91
- Average rookie cap hit: 3.09% of cap, Average AV: 0.63
- But rookies with *equivalent AV* to veterans are paid roughly half as much

### 3.2 The Effective Salary Framework

Calvetti develops separate regressions for rookie and veteran contracts:

```
AV_rookie = α₀ʳ + α₁ʳ × log(1 + Salary_rookie)
AV_veteran = α₀ᵛ + α₁ᵛ × log(1 + Salary_veteran)
```

Setting these equal and solving for veteran salary yields the "effective salary" - what the market would pay a veteran for the same expected production.

**Application:** For a given draft pick with known salary, teams can calculate which position provides the highest effective salary, maximizing the rookie contract arbitrage.

### 3.3 Implications for Team Building

The rookie premium explains several observed phenomena:

1. **Draft pick value:** Teams correctly value draft picks highly, though Cade & Thaler's research suggests early picks are still overvalued relative to their production.

2. **The Seahawks model:** Seattle's 2013-2014 dominance (Super Bowl championship) came with Russell Wilson, Richard Sherman, Bobby Wagner, and numerous contributors all on rookie deals. They had only two players with cap hits over $8M.

3. **Contract timing:** Smart teams extend valuable players *before* free agency rather than letting the market set prices (Bhartiya, 2004).

### 3.4 Uncompensated Wins

Mulholland & Jensen (2019) define "uncompensated win contribution" as actual wins minus expected wins based on salary. Teams with high uncompensated wins systematically outperform:

**Top 5 Teams in Uncompensated Wins (2011-2015):**
| Rank | Team | Avg Uncompensated Wins |
|------|------|------------------------|
| 1 | NE | +4.0 |
| 2 | DEN | +3.9 |
| 3 | SEA | +3.0 |
| 4 | GB | +2.6 |
| 5 | BAL | +2.0 |

**Correlation between uncompensated wins and actual wins: 0.9**

This extraordinary correlation suggests that the ability to find undervalued talent (primarily through the draft) is the primary determinant of sustained team success.

---

## 4. Optimal Position Allocation

### 4.1 The Mulholland-Jensen Allocation Model

Using linear programming constrained by the salary cap, Mulholland & Jensen (2019) derive optimal allocation percentages:

| Position | Optimal Cap % | Typical Starters |
|----------|---------------|------------------|
| Outside Linebacker | 15.2% | 2 |
| Defensive End | 13.7% | 2 |
| Guard | 10.6% | 2 |
| Defensive Tackle | 10.2% | 1-2 |
| Inside Linebacker | 10.0% | 1-2 |
| Quarterback | 8.6% | 1 |
| Cornerback | 7.1% | 2 |
| Wide Receiver | 5.6% | 2 |
| Free Safety | 4.4% | 1 |
| Strong Safety | 3.2% | 1 |
| Right Tackle | 2.5% | 1 |
| Fullback | 2.1% | 0-1 |
| Center | 1.9% | 1 |
| Left Tackle | 1.2% | 1 |
| Kicker | 0.9% | 1 |
| Running Back | 0.8% | 1-2 |
| Tight End | 0.7% | 1-2 |

### 4.2 Surprising Findings

**Left Tackles Are Overvalued**

Despite the "blind side" premium and enormous real-world salaries for LTs, the model suggests minimal allocation (1.2%). The explanation: many highly-paid LTs underperform their contracts, reducing the expected marginal win contribution from additional LT spending.

**Running Backs Are Replaceable**

The 0.8% optimal allocation for RBs aligns with the league-wide trend of devaluing the position. The model suggests running back production is more fungible and less predictive of wins than commonly believed.

**Interior Defense Commands Premium**

Defensive tackles and defensive ends together warrant nearly 24% of cap - the largest positional grouping. Pass rush and run stuffing from the interior appears systematically undervalued by the market.

**Guards Over Tackles**

The model allocates more to guards (10.6%) than to both tackles combined (3.7%), contradicting the traditional tackle premium.

### 4.3 The Calvetti Interaction Model

Calvetti (2023) extends this analysis by incorporating position interactions:

```
PPG = β₀ + Σᵢ βᵢ×AVᵢ + Σᵢⱼ βᵢⱼ×√(AVᵢ×AVⱼ)
```

The cross-terms capture synergies: a great wide receiver contributes more with a great quarterback than with a mediocre one. This addresses a limitation of prior work that assumed each position's contribution was independent.

**Key Insight:** The optimal allocation depends on your existing roster. Adding a star WR has different value for a team with an elite QB versus one without.

### 4.4 Position-Specific Salary-to-Performance Relationships

Calvetti's regressions reveal varying strength of salary-performance relationships by position:

| Position | R² (Effective Salary → AV) |
|----------|---------------------------|
| Left Tackle | 0.44 |
| Right Tackle | 0.39 |
| Guard | 0.19 |
| Center | 0.18 |
| Wide Receiver | 0.13 |
| Kicker | 0.12 |
| Tight End | 0.09 |
| Quarterback | 0.06 |
| Running Back | 0.04 |

**Interpretation:** Offensive line positions show the strongest salary-performance correlation, suggesting the market is most efficient at pricing linemen. Running back and quarterback show weak correlations - high variance in outcomes relative to salary suggests either market inefficiency or high inherent unpredictability.

---

## 5. Predicting Future Performance

### 5.1 The Limits of Prediction

Bhartiya (2004) provides the most sobering assessment of performance prediction:

- **Ex-ante R²:** 0.25 (using variables known before signing)
- **Ex-post R²:** 0.11 (using actual future performance)

This counterintuitive result (predictions are worse after observing outcomes) suggests teams are systematically overconfident in their ability to forecast player futures.

### 5.2 What Predicts Free Agent Performance

Mulholland & Jensen (2020) identify the most predictive variables for WR/TE free agents:

**Most Predictive:**
1. Age (negative coefficient in all models)
2. NFL career score per year to date
3. Conference (Big Ten positive, BCS often negative for free agents)
4. Weight/BMI (smaller receivers outperform)

**Key Finding:** Age is NOT included in salary prediction models but IS included in performance prediction models. This means **teams systematically overpay older players** relative to their expected future production.

### 5.3 The Free Agency Selection Bias

Players reaching free agency are a biased sample:
- Elite players get extended before free agency
- Franchise tags retain top performers
- Free agents are disproportionately: (a) players teams chose not to retain, or (b) players who outperformed low expectations

This explains counterintuitive findings like non-BCS players and smaller receivers performing better in free agency - they're more likely to be the "diamonds in the rough" who exceeded initial expectations on cheap rookie deals.

### 5.4 Cognitive Biases in Player Evaluation

Bhartiya (2004) documents specific biases:

**Recency Effect:** Recent performance is overweighted relative to career averages for statistical measures.

**Label Effect:** Categorical achievements (Pro Bowl, career wins) create persistent "labels" that anchor evaluations regardless of current performance.

**Overconfidence:** Teams believe they can predict future performance better than base rates suggest.

**Signaling:** Letting a player reach free agency signals the team's private information that the player is overvalued. Players who never hit FA are paid more because their teams preemptively extend them.

---

## 6. Demographic and Non-Performance Factors

### 6.1 Race and Compensation

Draisey (2016) finds that after controlling for performance:

**Non-white players earn approximately 17% less than white counterparts with equivalent statistics.**

This disparity persists across the sample and represents a significant market inefficiency - teams undervaluing non-white players could exploit this to acquire talent below market rates.

### 6.2 Off-Field Behavior

Players with arrest records receive approximately 26% lower cap values, controlling for on-field performance (Draisey, 2016). This "character discount" may or may not reflect actual risk of future incidents affecting availability.

### 6.3 Draft Position and Rookie Salaries

For rookies, draft position almost entirely determines salary regardless of performance expectations (Draisey, 2016). The slotted rookie wage scale (implemented in 2011 CBA) removed most negotiating leverage, making draft position the primary salary determinant.

---

## 7. Implications for Football Simulation

### 7.1 Contract Valuation System

A realistic contract system should incorporate:

1. **Rookie scale contracts** with 4-year terms and predetermined values by draft position
2. **Effective salary calculations** that recognize rookie contract value exceeds cap hit
3. **Age-based depreciation** that real GMs underweight
4. **Position-specific market rates** with different slopes for salary-performance relationships

### 7.2 AI General Manager Behavior

Realistic AI GMs should exhibit documented biases:

- Overvalue recent performance (recency)
- Anchor on achievements (Pro Bowl, wins)
- Be overconfident in predictions
- Overpay older veterans
- Undervalue running backs, interior defenders
- Overvalue left tackles
- Use free agency as a negative signal
- Prioritize draft pick accumulation

### 7.3 Team Building Strategy

The research suggests optimal strategies include:

1. **Draft-centric approach:** Rookie contracts provide 2x value
2. **Extend early:** Lock up valuable players before free agency
3. **Let marginal players walk:** Free agency signals overvaluation
4. **Invest in trenches:** Interior defensive line provides undervalued wins
5. **Avoid RB premiums:** Running back production is replaceable
6. **Youth over experience:** Age is underweighted in pricing

### 7.4 Performance Metrics

For cross-position player evaluation:

- **Approximate Value (AV):** Established, available, comparable across positions
- **Fantasy PPG:** Intuitive, explains 46% of salary variance
- **NFL Career Score:** Simple formula for receivers (Yards + 19.3×TDs)
- **Win contribution:** Position-weighted AV conversion

### 7.5 The Interaction Model

Calvetti's framework of position interactions provides a foundation for more sophisticated player evaluation:

- Player value depends on teammates
- Elite players at synergistic positions compound value
- Optimal allocation is roster-dependent, not universal

---

## 8. Methodological Notes

### 8.1 Data Sources

All papers rely on publicly available data:
- **Spotrac.com:** Salary cap data
- **Pro-Football-Reference.com:** AV, statistics, roster data
- **NFL.com:** Game results
- **ESPN Free Agent Tracker:** Free agency transactions

### 8.2 Time Periods

| Paper | Years Covered |
|-------|---------------|
| Bhartiya (2004) | 1993-2003 |
| Draisey (2016) | 2011-2015 |
| Mulholland & Jensen (2019) | 2011-2015 |
| Mulholland & Jensen (2020) | 2005-2013 |
| Calvetti (2023) | 2011-2021 |

### 8.3 Limitations

1. **Sample sizes:** NFL generates only 32 team-seasons per year, limiting statistical power
2. **Regime changes:** Rule changes, CBA modifications, and strategic evolution may invalidate historical patterns
3. **Endogeneity:** Salary both reflects and influences performance
4. **Unobservables:** Coaching, scheme fit, injury history, and intangibles are difficult to capture
5. **Selection bias:** Free agents are non-random samples of the player population

---

## 9. Research Gaps and Future Directions

### 9.1 Defensive Analysis

Most research focuses on offense. Calvetti explicitly limits scope to offensive positions. A parallel analysis of defensive allocation would be valuable.

### 9.2 Coaching Effects

No paper adequately controls for coaching quality, despite its likely substantial impact on player performance and scheme fit.

### 9.3 Dynamic Optimization

All models are single-period. Multi-year optimization incorporating aging curves, contract structures, and draft pick accumulation would better reflect actual team-building.

### 9.4 Position Flexibility

Modern NFL trends toward position versatility (e.g., "movable chess piece" defenders, receiving backs) are not captured by rigid positional categories.

### 9.5 Cap Manipulation

Teams use signing bonus proration, restructures, and void years to manipulate cap timing. No paper models these strategic cap management tools.

---

## 10. Summary of Key Findings

| Finding | Source | Confidence |
|---------|--------|------------|
| Rookie contracts provide ~2x value vs veteran | Calvetti 2023 | High |
| Drafting well correlates 0.9 with wins | M&J 2019 | High |
| Running backs should receive minimal cap | M&J 2019 | High |
| Left tackles are overvalued | M&J 2019 | Medium |
| Teams overpay older players | M&J 2020 | High |
| Age is the strongest predictor of decline | M&J 2020 | High |
| Fantasy PPG explains 46% of salary variance | Draisey 2016 | High |
| Non-white players are underpaid ~17% | Draisey 2016 | Medium |
| Teams are overconfident in predictions | Bhartiya 2004 | Medium |
| Player interactions affect optimal allocation | Calvetti 2023 | High |
| Interior defensive line is undervalued | M&J 2019 | Medium |
| Smaller receivers provide more FA value | M&J 2020 | Medium |

---

## References

1. Bhartiya, D. (2004). *Compensation, Free Agency, and Future Performance in the National Football League*. Duke University.

2. Calvetti, P. G. (2023). *Optimizing the Allocation of Capital Among Offensive Positions in the NFL*. MIT Master's Thesis.

3. Draisey, B. C. (2016). *The Determinants of NFL Player Salaries*. CMC Senior Theses.

4. Mulholland, J., & Jensen, S. T. (2019). Optimizing the allocation of funds of an NFL team under the salary cap. *International Journal of Forecasting*, 35(2), 767-775.

5. Mulholland, J., & Jensen, S. T. (2020). Predicting the Future of Free Agent Receivers and Tight Ends in the NFL. *Statistica Applicata - Italian Journal of Applied Statistics*, 30(2), 269-294.
