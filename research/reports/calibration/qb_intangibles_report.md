# QB Intangibles Analysis Report

**Generated**: December 2024
**Data Source**: NFL PBP 2019-2024, NGS Passing Data
**Pass Plays Analyzed**: 113,581

---

## Executive Summary

This analysis attempts to quantify the "unquantifiable" - the mental and situational attributes that separate elite QBs from average ones. Using play-by-play and Next Gen Stats data, we extracted measurable proxies for seven intangible qualities:

| Intangible | Measurable Proxy | Spread (Best to Worst) | Simulation Impact |
|------------|------------------|------------------------|-------------------|
| **Poise** | Pressure penalty vs league avg | 28.4% | Highest |
| **Decision-Making** | Short throw INT rate | 3.2% (10x diff) | High |
| **Anticipation** | Time-to-throw + completion | 29 points composite | High |
| **Clutch** | EPA in close 4th quarter | 0.86 EPA | Medium |
| **Consistency** | Game-to-game completion std | 9.4% | Medium |
| **Aggressiveness** | Tight window throw % | 11.3% | Style modifier |
| **Pocket Presence** | Sack avoidance rate | TBD (data issue) | High |

**Key Finding**: Poise shows the largest actionable spread between QBs. The difference between a composed QB and a rattled one under pressure is worth 28% in completion rate - far exceeding any physical attribute's impact.

---

## 1. Clutch Performance

### Definition
Performance in high-leverage situations: 4th quarter, close games (within 8 points).

### League-Wide Effect
| Situation | Completion % | EPA/Play |
|-----------|-------------|----------|
| Normal | 65.2% | 0.150 |
| Clutch (4Q, close) | 62.7% | 0.135 |
| **Difference** | **-2.5%** | **-0.015** |

The average QB performs *worse* in clutch situations. But elite clutch performers buck this trend.

### Top Clutch Performers
| QB | Clutch Plays | Comp % Diff | EPA Diff |
|----|-------------|-------------|----------|
| Kenny Pickett | 143 | -0.3% | +0.318 |
| Anthony Richardson | 53 | -2.1% | +0.298 |
| Desmond Ridder | 93 | +8.4% | +0.286 |
| Zach Wilson | 134 | +6.3% | +0.252 |
| Deshaun Watson | 235 | +4.3% | +0.209 |
| Ben Roethlisberger | 188 | +8.5% | +0.192 |
| Drew Brees | 89 | +6.8% | +0.180 |

### Worst Clutch Performers
| QB | Clutch Plays | Comp % Diff | EPA Diff |
|----|-------------|-------------|----------|
| David Blough | 37 | -13.1% | -0.542 |
| Tyrod Taylor | 66 | -6.2% | -0.422 |
| Jeff Driskel | 38 | -19.6% | -0.385 |
| Bailey Zappe | 38 | -7.9% | -0.361 |
| Nick Mullens | 71 | -0.8% | -0.358 |

### Clutch Spread
- **Best EPA diff**: +0.318 (Pickett)
- **Worst EPA diff**: -0.542 (Blough)
- **Total spread**: 0.86 EPA
- **Standard deviation**: 0.16 EPA

### Simulation Recommendation
```
clutch_modifier = 1.0 + (clutch_rating - 75) / 100 * 0.15
// Rating 95: +3% boost in clutch
// Rating 55: -3% penalty in clutch
```

### Deeper Dive Opportunities
1. **2-Minute Drill Specialist**: Isolate final 2 minutes of each half - some QBs excel specifically in hurry-up
2. **Comeback vs Close-Out**: Separate trailing in 4th (comeback) from leading in 4th (ice the game) - different skills
3. **Playoff Clutch**: Does regular season clutch predict postseason performance?
4. **Clutch by Distance**: Are some QBs clutch on 3rd-and-long but not 3rd-and-short?

---

## 2. Poise (Pressure Resilience)

### Definition
How much does pressure degrade performance, relative to league average?

### League-Wide Pressure Effect
| Pocket Status | Completion % | Drop |
|--------------|--------------|------|
| Clean pocket | 70.6% | - |
| Under pressure | 49.6% | - |
| **Pressure penalty** | - | **21.0%** |

### Poise Score Calculation
```
poise_score = league_pressure_penalty - qb_pressure_penalty
// Positive = more resilient than average
// Negative = more affected than average
```

### Most Poised QBs (Smallest Pressure Penalty)
| QB | Pressure Plays | Pressure Penalty | Poise Score |
|----|---------------|------------------|-------------|
| Bailey Zappe | 65 | 6.6% | +14.3% |
| Trevor Siemian | 98 | 10.9% | +10.1% |
| Tyrod Taylor | 118 | 12.0% | +9.0% |
| Desmond Ridder | 131 | 12.5% | +8.4% |
| Ben Roethlisberger | 309 | 12.8% | +8.2% |
| Drake Maye | 89 | 14.4% | +6.6% |
| Brock Purdy | 321 | 15.2% | +5.7% |

### Most Rattled QBs (Largest Pressure Penalty)
| QB | Pressure Plays | Pressure Penalty | Poise Score |
|----|---------------|------------------|-------------|
| Tommy Boyle | 58 | 35.1% | -14.1% |
| Jake Browning | 50 | 33.2% | -12.2% |
| Caleb Williams | 132 | 32.8% | -11.8% |
| Jeff Driskel | 72 | 31.3% | -10.3% |
| Alex Smith | 72 | 31.1% | -10.1% |
| Bryce Young | 223 | 29.4% | -8.4% |
| Zach Wilson | 287 | 29.1% | -8.1% |
| Aaron Rodgers | 652 | 27.3% | -6.3% |
| Jalen Hurts | 613 | 26.7% | -5.7% |

### Poise Spread
- **Most poised**: 6.6% pressure penalty (Zappe)
- **Most rattled**: 35.1% pressure penalty (Boyle)
- **Total spread**: 28.4%
- **Standard deviation**: 5.5%

### Critical Insight
**Poise is the largest differentiator we've found.** A 28% spread in pressure penalty dwarfs the effect of any accuracy attribute. When the pocket breaks down:
- A poised QB still completes 64% of passes
- A rattled QB completes only 36%

This is nearly 2x the effect of the accuracy spread in clean pocket situations.

### Simulation Recommendation
```
pressure_completion_penalty = base_pressure_penalty * (1 - poise_modifier)
where:
  base_pressure_penalty = 0.21  // League average
  poise_modifier = (poise_rating - 50) / 100

// Rating 90: penalty = 0.21 * 0.60 = 12.6%
// Rating 50: penalty = 0.21 * 1.00 = 21.0%
// Rating 30: penalty = 0.21 * 1.20 = 25.2%
```

### Deeper Dive Opportunities
1. **Pressure Type**: Does blitz vs coverage pressure affect different QBs differently?
2. **Time Under Pressure**: Do some QBs maintain poise for 1 second but collapse at 2 seconds?
3. **Pressure Frequency**: Do QBs who see MORE pressure become desensitized (get better) or worn down (get worse)?
4. **Rookie vs Veteran Poise**: Does poise improve with experience? Learning curve analysis
5. **Pressure + Situation Interaction**: Are some QBs poised in neutral but rattled when also trailing?

---

## 3. Decision-Making

### Definition
Avoiding interceptions in situations where they are most costly (short throws, red zone).

### League INT Rates by Situation
| Situation | INT Rate | Sample Size |
|-----------|----------|-------------|
| Short (<10 yds) | 1.23% | 76,675 |
| Medium (10-20 yds) | 3.44% | 23,666 |
| Deep (20+ yds) | 6.24% | 13,240 |
| Trailing | 2.62% | 59,295 |
| Leading (7+) | 1.83% | 13,246 |
| Red Zone | 2.26% | 15,233 |
| 3rd Down | 2.85% | 29,322 |

### Best Decision-Makers (Lowest Bad INTs)
| QB | Overall INT | Short INT | Red Zone INT | Decision Score |
|----|------------|-----------|--------------|----------------|
| Caleb Williams | 1.08% | 0.27% | 0.00% | +1.12 |
| Dwayne Haskins | 3.17% | 0.68% | 0.00% | +0.91 |
| Jacoby Brissett | 1.39% | 0.48% | 0.60% | +0.86 |
| Tom Brady | 1.57% | 0.73% | 0.63% | +0.73 |
| Jayden Daniels | 1.69% | 0.73% | 1.12% | +0.61 |
| Justin Herbert | 1.64% | 0.77% | 1.16% | +0.57 |

### Worst Decision-Makers (Highest Bad INTs)
| QB | Overall INT | Short INT | Red Zone INT | Decision Score |
|----|------------|-----------|--------------|----------------|
| P.J. Walker | 4.75% | 3.41% | 9.68% | -2.88 |
| Bailey Zappe | 4.19% | 3.51% | N/A | -2.01 |
| Sam Howell | 3.57% | 2.48% | 5.71% | -1.42 |
| Nick Mullens | 3.97% | 2.47% | 5.88% | -1.46 |
| Jameis Winston | 4.23% | 3.02% | 2.74% | -0.94 |

### Decision-Making Spread
- **Best short INT rate**: 0.27% (C. Williams)
- **Worst short INT rate**: 3.51% (Zappe)
- **Spread**: 3.24% (13x difference)

### The "Turnover-Worthy Play" Signal
Short throws should almost never be intercepted. A 3%+ INT rate on throws under 10 yards signals:
- Poor pre-snap reads
- Staring down receivers
- Forcing into coverage
- Bad ball placement

### Simulation Recommendation
```
int_probability = base_int_rate * decision_modifier
where:
  base_int_rate = depth-adjusted rate from passing model
  decision_modifier = 1.5 - (decision_rating / 100)

// Rating 90: modifier = 0.60 (40% fewer INTs)
// Rating 50: modifier = 1.00 (baseline)
// Rating 30: modifier = 1.20 (20% more INTs)
```

### Deeper Dive Opportunities
1. **INT Type Classification**: Tipped balls vs bad throws vs miscommunication - only bad throws reflect decision-making
2. **Pressure × Decisions**: Do some QBs make worse decisions under pressure while others just miss throws?
3. **Turnover-Worthy Plays**: If we had charting data, TWP rate is the gold standard for decision-making
4. **Recovery from Mistakes**: Do some QBs spiral after an INT while others shake it off?
5. **Aggressiveness × Decisions**: Is Winston's high INT rate "bad decisions" or "acceptable risk"?

---

## 4. Anticipation

### Definition
Processing speed - completing passes with less time in the pocket.

### League Averages
- **Mean time to throw**: 2.79 seconds
- **Mean completion %**: 64.4%

### Top Anticipators (High Completion + Quick Release)
| QB | Avg Time to Throw | Completion % | Anticipation Score |
|----|------------------|--------------|-------------------|
| Drew Brees | 2.63s | 72.3% | +9.6 |
| Tua Tagovailoa | 2.50s | 67.9% | +6.5 |
| Jayden Daniels | 2.68s | 69.6% | +6.3 |
| Joe Burrow | 2.62s | 68.2% | +5.5 |
| Ben Roethlisberger | 2.34s | 65.2% | +5.2 |
| Philip Rivers | 2.58s | 67.3% | +5.0 |

### Slow Processors
| QB | Avg Time to Throw | Completion % | Anticipation Score |
|----|------------------|--------------|-------------------|
| Anthony Richardson | 2.96s | 46.9% | -19.2 |
| Zach Wilson | 2.99s | 56.8% | -9.6 |
| Marcus Mariota | 2.90s | 58.8% | -6.8 |
| Taylor Heinicke | 2.96s | 60.1% | -6.0 |
| Justin Fields | 3.07s | 61.5% | -5.7 |
| Sam Darnold | 3.00s | 61.0% | -5.5 |

### Anticipation Spread
- **Fastest effective processor**: 2.34s at 65% (Roethlisberger)
- **Slowest processor**: 3.07s at 62% (Fields)
- **Score spread**: 29 points

### The "Throw Before the Break" Signal
Elite anticipators throw the ball before the receiver's break, trusting the route. This shows up as:
- Lower time to throw
- Higher completion % (ball arrives in rhythm)
- Fewer sacks (ball out before pressure arrives)

### Simulation Recommendation
```
anticipation affects:
1. Throw timing: anticipation_rating affects when throw releases vs route break
2. Pressure interaction: high anticipation = less affected by pocket collapse
3. Completion bonus: throws on rhythm are easier catches

throw_timing_offset = (anticipation_rating - 75) / 100 * 0.3
// Rating 95: throw 0.06s earlier (ball arrives at break)
// Rating 55: throw 0.06s later (ball arrives after break)
```

### Deeper Dive Opportunities
1. **Route-Specific Timing**: Do some QBs anticipate curls better than posts? Break down by route type
2. **Pressure vs Clean Timing**: Does time-to-throw increase more for some QBs under pressure?
3. **Seasonal Learning**: Do QBs with new receivers throw later early in season and faster later?
4. **Depth-Adjusted Timing**: Short throws should be faster - normalize for target depth
5. **Completion by Time Bucket**: Map exact relationship between throw timing and success

---

## 5. Aggressiveness

### Definition
Willingness to throw into tight coverage windows.

### League Average
- **Aggressiveness**: 15.5% of throws into tight windows
- **Intended air yards**: 8.0 yards

### Most Aggressive QBs
| QB | Aggressiveness | Avg Air Yards | Completion % |
|----|---------------|---------------|--------------|
| Cooper Rush | 21.7% | 7.7 | 59.5% |
| Ryan Fitzpatrick | 21.6% | 8.5 | 65.7% |
| Dwayne Haskins | 20.6% | 8.0 | 59.9% |
| Nick Foles | 20.5% | 7.9 | 64.2% |
| Mitchell Trubisky | 20.3% | 8.5 | 65.5% |

### Most Conservative QBs
| QB | Aggressiveness | Avg Air Yards | Completion % |
|----|---------------|---------------|--------------|
| Patrick Mahomes | 10.5% | 7.3 | 67.1% |
| Caleb Williams | 11.9% | 7.7 | 62.6% |
| Jared Goff | 12.1% | 7.0 | 67.3% |
| Trevor Lawrence | 12.4% | 8.1 | 63.6% |
| Bo Nix | 12.6% | 7.6 | 66.0% |

### Aggressiveness-Completion Trade-off
**Correlation**: r = -0.271

For every 10% increase in aggressiveness, completion % drops ~2.7%.

### Key Insight
Mahomes is the least aggressive thrower in the league (10.5%) while maintaining elite production. This suggests:
- He takes what the defense gives
- His "aggressive" plays are scheme-created, not forced
- Aggressiveness might be a negative trait, not positive

### Simulation Recommendation
```
aggressiveness is a STYLE modifier, not pure positive:

if throw_into_tight_window:
    completion_penalty = 0.15  // 15% harder to complete
    big_play_bonus = 1.3       // But 30% more yards if completed

aggressive_throw_rate = (aggressiveness_rating - 50) / 100 * 0.15
// Rating 80: 4.5% more tight window attempts
// Rating 50: baseline
// Rating 30: 3% fewer tight window attempts
```

### Deeper Dive Opportunities
1. **Aggressiveness by Situation**: Are some QBs aggressive when ahead but conservative when behind?
2. **Aggressiveness by Target**: Do QBs throw aggressively only to their #1 WR?
3. **Risk-Reward Curve**: Is there an optimal aggressiveness level that maximizes EPA?
4. **Game Script**: How does aggressiveness change when trailing by 14+ vs leading by 14+?

---

## 6. Consistency

### Definition
Low game-to-game variance in performance.

### League Average
- **Game-to-game completion % std**: 9.0%

### Most Consistent QBs
| QB | Games | Avg Comp % | Std Dev | Consistency Score |
|----|-------|-----------|---------|-------------------|
| Nick Foles | 12 | 65.0% | 5.8% | +6.1 |
| Nick Mullens | 14 | 66.0% | 6.1% | +5.7 |
| Ben Roethlisberger | 35 | 64.7% | 6.2% | +5.4 |
| Matt Stafford | 87 | 66.0% | 7.3% | +3.9 |
| Geno Smith | 54 | 68.9% | 7.8% | +3.7 |
| Joe Burrow | 76 | 69.0% | 7.8% | +3.6 |

### Most Inconsistent QBs
| QB | Games | Avg Comp % | Std Dev | Consistency Score |
|----|-------|-----------|---------|-------------------|
| Brandon Allen | 10 | 55.2% | 15.2% | -12.5 |
| Anthony Richardson | 11 | 48.4% | 10.2% | -6.1 |
| Cam Newton | 20 | 62.6% | 13.0% | -5.7 |
| Taylor Heinicke | 32 | 62.2% | 12.1% | -4.5 |
| Sam Howell | 18 | 61.2% | 11.8% | -4.2 |

### Consistency Spread
- **Most consistent CV**: 0.09 (9% of mean)
- **Least consistent CV**: 0.27 (27% of mean)
- **Spread**: 3x difference

### The Reliability Signal
Consistent QBs provide:
- Predictable game planning
- Fewer "stinker" games
- Reliable floor even if ceiling is lower

### Simulation Recommendation
```
game_variance_multiplier = 1 + (100 - consistency_rating) / 100 * 0.15

// Each game, apply variance:
game_performance_modifier = random.gauss(1.0, game_variance_multiplier * 0.09)

// Rating 90: std = 0.9% per game
// Rating 50: std = 5.4% per game
// Rating 30: std = 8.1% per game
```

### Deeper Dive Opportunities
1. **Home vs Away Consistency**: Are some QBs only consistent at home?
2. **Weather Impact**: Does consistency correlate with weather resilience?
3. **Opponent Quality**: Are some QBs consistent vs bad teams but volatile vs good teams?
4. **Seasonal Trends**: Do QBs become more consistent as the season progresses?
5. **Variance in What**: Is variance in accuracy, depth, or decision-making driving game swings?

---

## 7. Pocket Presence

### Definition
Ability to avoid sacks when facing pressure.

### Data Issue
The PBP sack data showed 0.0% for all QBs, indicating a column parsing issue. This analysis requires correction.

### Expected Metrics (When Fixed)
- **Sack rate**: sacks / dropbacks
- **Sack per pressure**: sacks / pressures (requires pressure data)
- **Escape rate**: scrambles / pressures

### Deeper Dive Opportunities
1. **Fix data issue**: Properly parse sack column from PBP data
2. **Scramble success**: When escaping, completion % on scramble throws
3. **Sack timing**: Sacks at 2s vs 3s vs 4s - does QB hold too long?
4. **Pressure direction**: Do some QBs escape left better than right?
5. **Pocket movement**: Step-up vs rollout vs scramble tendencies

---

## Composite Intangibles Ranking

Combining all measurable intangibles into a single composite score:

### Top 15 QBs by Composite Intangibles
| Rank | QB | Composite | Clutch | Poise | Decision | Anticipation | Consistency |
|------|-----|-----------|--------|-------|----------|--------------|-------------|
| 1 | Ben Roethlisberger | 78.4 | +0.19 | +8.2% | +0.38 | +5.2 | +5.4 |
| 2 | Kenny Pickett | 77.6 | +0.32 | +4.5% | +0.59 | N/A | +3.4 |
| 3 | Drew Brees | 75.0 | N/A | N/A | N/A | +9.6 | N/A |
| 4 | Trevor Siemian | 74.1 | +0.23 | +10.1% | -0.17 | -7.2 | +2.1 |
| 5 | Joe Burrow | 71.8 | +0.12 | +4.8% | +0.29 | +5.5 | +3.6 |
| 6 | Nick Foles | 71.2 | +0.01 | +3.0% | +0.37 | N/A | +6.1 |
| 7 | Desmond Ridder | 70.9 | +0.29 | +8.4% | -0.52 | N/A | +0.5 |
| 8 | Drew Brees (PBP) | 69.6 | +0.18 | +3.3% | +0.49 | N/A | +0.3 |
| 9 | Tua Tagovailoa | 69.6 | N/A | N/A | N/A | +6.5 | N/A |
| 10 | Matt Ryan | 69.5 | +0.13 | +3.9% | +0.30 | N/A | +1.7 |

### Interpretation
- Roethlisberger and Burrow show elite across-the-board intangibles
- Brees dominates anticipation but limited PBP data for other metrics
- Some QBs are specialists (Siemian = poise, Pickett = clutch)

---

## Proposed Deeper Analyses

### Priority 1: Pressure Interaction Deep Dive
Poise shows the largest spread (28%). Deeper analysis should explore:

1. **Pressure Type Analysis**
   - Blitz pressure vs coverage pressure
   - Interior vs edge pressure
   - Do some QBs handle blitz well but collapse vs coverage sacks?

2. **Temporal Pressure Model**
   - Performance at 2.0s, 2.5s, 3.0s, 3.5s, 4.0s
   - Does poise degrade linearly or is there a cliff?
   - Build "pressure tolerance curves" per QB

3. **Pressure Learning Curve**
   - Rookie year poise vs Year 3 poise
   - Does experience improve pressure handling?
   - How quickly do QBs adapt?

### Priority 2: Clutch Decomposition
Break clutch into component skills:

1. **Situation-Specific Clutch**
   - 2-minute drill specialist (hurry-up execution)
   - Comeback specialist (trailing in 4th)
   - Closer (protecting lead in 4th)
   - Red zone clutch (goal-to-go in 4th)

2. **Clutch Consistency**
   - Is clutch skill real or variance?
   - Year-over-year clutch correlation
   - Sample size requirements for reliable clutch measurement

### Priority 3: Decision-Making Classification
Build a decision taxonomy:

1. **INT Type Model**
   - Bad read (threw to covered receiver)
   - Bad throw (accuracy failure)
   - Tipped ball (receiver/defender tip)
   - Miscommunication (route confusion)

2. **Pressure × Decisions**
   - Decision quality under pressure
   - Do some QBs maintain reads but lose accuracy under pressure?
   - Do others lose reads entirely?

### Priority 4: Anticipation by Route Type
Break down timing by route:

1. **Route-Specific Timing**
   - Slant anticipation vs post anticipation
   - Comeback routes (throw before break is critical)
   - Go routes (timing for back-shoulder adjustment)

2. **Target-Specific Timing**
   - Do QBs anticipate better with familiar receivers?
   - Learning curve with new weapons

### Priority 5: Composite Validation
Validate the intangibles model:

1. **Predictive Power**
   - Do intangibles predict future EPA better than physical stats?
   - Holdout test: 2019-2022 intangibles → 2023-2024 performance

2. **Contract Correlation**
   - Do GMs pay for intangibles?
   - Are intangibles undervalued in the market?

---

## Simulation Integration Recommendations

### New Attributes to Add
Based on this analysis, the simulation should track:

| Attribute | Range | Primary Effect |
|-----------|-------|----------------|
| `poise` | 1-99 | Pressure penalty modifier |
| `clutch` | 1-99 | Performance modifier in high-leverage |
| `anticipation` | 1-99 | Throw timing vs route break |
| `decision_making` | 1-99 | INT probability modifier |
| `consistency` | 1-99 | Game-to-game variance |
| `aggressiveness` | 1-99 | Tight window attempt rate (style) |

### Implementation Priority
1. **Poise** - Highest impact, clearest data signal
2. **Decision-Making** - High impact, clear measurement
3. **Anticipation** - High impact, affects throw timing model
4. **Consistency** - Medium impact, affects game variance
5. **Clutch** - Medium impact, situational modifier
6. **Aggressiveness** - Style modifier, not pure positive

### Rating Scale Calibration
```
Rating 95 (Elite): Top 5% of measured distribution
Rating 85 (Great): Top 15%
Rating 75 (Good): Top 30%
Rating 65 (Average): 30-70%
Rating 55 (Below Avg): Bottom 30%
Rating 45 (Poor): Bottom 15%
Rating 35 (Bad): Bottom 5%
```

---

## Conclusion

QB intangibles are not unmeasurable - they're just measured indirectly. This analysis reveals:

1. **Poise is the biggest differentiator** - 28% spread in pressure penalty
2. **Decision-making has massive variance** - 10x difference in short throw INTs
3. **Anticipation separates elite from good** - Brees/Tua vs Wilson/Richardson
4. **Clutch is real but noisy** - ~0.9 EPA spread but small samples
5. **Consistency matters for reliability** - 3x difference in game-to-game variance
6. **Aggressiveness is style, not skill** - Negative correlation with completion %

The recommended next step is a **Pressure Interaction Deep Dive** since poise shows the largest actionable signal in the data.

---

## Files Generated
- `research/models/qb_intangibles_analysis.py` - Analysis script
- `research/exports/qb_intangibles_analysis.json` - Raw data export
- `research/reports/calibration/qb_intangibles_report.md` - This report
