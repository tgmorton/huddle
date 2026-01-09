# QB Variance Analysis Report

**Data Sources:** NFL PBP 2019-2024, NGS Passing Data
**Purpose:** Understand all sources of QB variance for realistic simulation modeling

---

## Executive Summary

QB performance variance comes from multiple sources that must be modeled separately:

| Variance Source | Magnitude | Key Finding |
|-----------------|-----------|-------------|
| **Time to Throw** | 2.5% completion | Quick (2.58s) vs Slow (2.99s) |
| **Pressure** | 43.6% completion | Clean 66.9% → Pressured 23.2% |
| **Game-to-Game** | ±18% from avg | Individual games swing wildly |
| **Situational** | ~10% completion | 3rd down much harder than 1st |
| **Air Yards** | ~1.5%/yard | Deep throws 3x harder than short |
| **QB Skill (CPOE)** | 7.7% spread | Elite +3.5%, Poor -4.2% |
| **INT Risk** | 4.5x multiplier | Deep 6.24% vs Short 1.39% |

**Critical Insight:** The pressure penalty (-43.6%) is by far the largest single factor affecting completion probability. Modeling pressure timing is essential for realistic simulation.

---

## Time to Throw Analysis

### Distribution

| Metric | Value |
|--------|-------|
| Mean | 2.79 seconds |
| Std Dev | 0.16 seconds |
| 10th percentile | 2.57 seconds |
| 90th percentile | 2.98 seconds |

**Key Insight:** QB time to throw is remarkably consistent. The entire NFL range from quick to slow is only 0.4 seconds.

### Performance by Time to Throw Tier

| Tier | Avg Time | Completion % | Passer Rating | INT Rate |
|------|----------|--------------|---------------|----------|
| Quick | 2.58s | 65.6% | 90.8 | 1.91% |
| Normal-Quick | 2.74s | 65.3% | 90.3 | 2.08% |
| Normal-Slow | 2.84s | 63.5% | 89.0 | 2.07% |
| Slow | 2.99s | 63.0% | 90.4 | 2.02% |

**Findings:**
1. Quick releases (2.58s) have ~2.5% higher completion than slow (2.99s)
2. Passer rating is surprisingly flat across time tiers
3. INT rate doesn't vary much with time to throw
4. The benefit of quick release is modest but real

### Optimal Time to Throw

Based on performance data, the optimal time to throw range is **2.4-2.8 seconds**:
- Below 2.4s: Throwing before routes develop
- 2.4-2.8s: Routes at depth, protection intact
- Above 2.8s: Protection degrading, defenders closing

### Simulation Recommendations

```python
def model_time_to_throw(qb_release_rating):
    """
    Model time to throw based on QB's quick release attribute.

    Quick release: 2.5s baseline
    Slow release: 2.9s baseline
    """
    baseline = 2.9 - (qb_release_rating - 40) / 55 * 0.4
    variance = np.random.normal(0, 0.15)
    return max(2.0, baseline + variance)
```

---

## Pressure Effects (CRITICAL)

### Overall Impact

| Condition | Completion % | Difference |
|-----------|--------------|------------|
| Clean Pocket | 66.9% | - |
| Under Pressure | 23.2% | -43.6% |

**This is the single largest factor in QB performance.** Pressure reduces completion by 43.6 percentage points - more than any other factor.

### What Counts as Pressure

Pressure includes:
- QB hits (not sacked but contacted)
- Sacks
- Hurries/forced movement

Pressure rate across all passes: **15.2%**

### Pressure by Down

| Down | Pressure Rate | Clean Comp | Pressured Comp |
|------|---------------|------------|----------------|
| 1st | 13.8% | 68.1% | 24.1% |
| 2nd | 14.9% | 66.9% | 23.4% |
| 3rd | 17.2% | 60.5% | 21.8% |
| 4th | 18.7% | 56.2% | 19.3% |

**Finding:** Pressure rate increases on later downs (defense more aggressive), AND the completion penalty is worse on 3rd/4th down.

### Sack Rate When Pressured

When a QB is pressured, sack rate is: **42.8%**

This means nearly half of pressured dropbacks result in sacks rather than throws.

### Simulation Recommendations

```python
def model_pressure_outcome(is_pressured, qb_poise_rating):
    """Model what happens under pressure."""

    if not is_pressured:
        return 'clean_throw'

    # Sack probability when pressured
    base_sack_rate = 0.43
    poise_modifier = (qb_poise_rating - 50) / 50 * 0.10  # ±10%
    sack_prob = base_sack_rate - poise_modifier

    if random.random() < sack_prob:
        return 'sack'

    # If not sacked, completion penalty applies
    return 'pressured_throw'  # Apply -43.6% to completion
```

### Time-Based Pressure Model

Protection degrades over time. From previous blocking analysis:

| Time in Pocket | Pressure Probability |
|----------------|---------------------|
| 2.0s | 5% |
| 2.5s | 12% |
| 3.0s | 22% |
| 3.5s | 35% |
| 4.0s | 50% |
| 4.5s | 65% |

**Formula:** `pressure_prob = 0.026 * (time_in_pocket - 1.5)^1.5`

---

## Game-to-Game Variance

### Completion Percentage Variance

| Metric | Value |
|--------|-------|
| Average game-to-game std | 8.9% |
| Typical game range | ±18% from season avg |
| Coefficient of variation | 0.15 |

**Interpretation:** A 65% season completion QB will have individual games ranging roughly from 47% to 83% completion.

### Consistency Tiers

| Tier | Completion Std | Avg Completion | EPA/Play |
|------|----------------|----------------|----------|
| Consistent | 6.2% | 65.1% | 0.12 |
| Average | 8.5% | 64.2% | 0.08 |
| Volatile | 12.1% | 62.8% | 0.04 |

**Finding:** Consistent QBs are also better QBs. Volatility correlates with lower performance.

### Sources of Game Variance

Game-to-game variance comes from:
1. **Opponent quality** - Defense tier affects all outcomes
2. **Weather** - Wind, rain, cold reduce completion
3. **Home/Away** - Small home advantage exists
4. **Rest/Health** - Short weeks reduce performance
5. **Random variance** - Some games just go better/worse

### Simulation Recommendations

```python
def apply_game_variance(qb_baseline_comp, qb_consistency):
    """
    Apply game-level modifier to QB baseline.

    consistency: 0-100 rating
    - High consistency: std ~0.06
    - Low consistency: std ~0.12
    """
    variance_std = 0.12 - (qb_consistency - 40) / 55 * 0.06
    game_modifier = np.random.normal(0, variance_std)

    return qb_baseline_comp + game_modifier
```

---

## Situational Variance

### By Down

| Down | Completion % | Avg Air Yards | INT Rate |
|------|--------------|---------------|----------|
| 1st | 63.7% | 7.8 | 1.83% |
| 2nd | 63.2% | 8.2 | 2.04% |
| 3rd | 53.9% | 8.7 | 2.46% |
| 4th | 49.6% | 7.2 | 3.24% |

**Key Insight:** 3rd down completion is ~10% lower than 1st/2nd. This is because:
1. Defense knows pass is likely
2. Must throw past sticks (longer throws)
3. Coverage is tighter

### By Distance to Go

| Distance | Completion % | Avg Air Yards |
|----------|--------------|---------------|
| Short (1-3) | 65.6% | 4.2 |
| Medium (4-7) | 61.9% | 7.1 |
| Long (8-12) | 55.3% | 10.4 |
| Very Long (13+) | 48.8% | 14.1 |

**Finding:** Completion drops ~1.5% per yard of distance needed.

### By Score Differential

| Situation | Completion % | Air Yards |
|-----------|--------------|-----------|
| Down Big (-14+) | 58.1% | 9.8 |
| Down 2 Scores | 59.7% | 9.1 |
| Down 1 Score | 59.4% | 8.4 |
| Tied | 62.1% | 7.6 |
| Up 1 Score | 60.6% | 7.4 |
| Up 2 Scores | 61.7% | 7.1 |
| Up Big (+14) | 61.2% | 6.4 |

**Findings:**
1. Trailing teams throw longer (9.8 vs 6.4 air yards)
2. Longer throws = lower completion
3. Leading teams play conservative, have higher completion

### By Quarter

| Quarter | Completion % |
|---------|--------------|
| 1st | 61.2% |
| 2nd | 60.8% |
| 3rd | 59.6% |
| 4th | 59.5% |

**Finding:** Small decline through game (~1.7% from Q1 to Q4), likely due to fatigue and game situation.

### By Field Position

| Field Position | Completion % | Air Yards |
|----------------|--------------|-----------|
| Red Zone | 56.6% | 4.1 |
| Midfield | 60.7% | 8.2 |
| Own Territory | 62.2% | 8.6 |

**Finding:** Red zone is hardest - compressed field means tighter coverage.

### Simulation Recommendations

```python
def calculate_situational_modifier(down, distance, score_diff, field_pos):
    """Calculate completion modifier based on situation."""

    modifier = 0

    # Down modifier
    down_mods = {1: 0.02, 2: 0.01, 3: -0.06, 4: -0.10}
    modifier += down_mods.get(down, 0)

    # Distance modifier (-1.5% per yard over 5)
    if distance > 5:
        modifier -= (distance - 5) * 0.015

    # Score modifier
    if score_diff < -14:
        modifier -= 0.04
    elif score_diff > 7:
        modifier += 0.02

    # Field position
    if field_pos <= 20:  # Red zone
        modifier -= 0.04

    return modifier
```

---

## Air Yards Analysis

### Distribution

| Metric | Value |
|--------|-------|
| Mean | 7.9 yards |
| Std Dev | 10.1 yards |
| Median | 7.0 yards |
| 10th percentile | -2.0 yards |
| 90th percentile | 20.0 yards |
| Behind LOS rate | 11.8% |
| Deep (20+) rate | 11.7% |

**Finding:** Air yards has high variance (std 10.1). About 12% of throws are screens/checkdowns behind LOS, and 12% are deep shots.

### Completion by Air Yards Bucket

| Air Yards | Completion % | INT Rate | Avg Yards if Complete |
|-----------|--------------|----------|----------------------|
| Behind LOS | 80.5% | 0.69% | 2.4 |
| Screen (0-4) | 72.6% | 1.04% | 7.1 |
| Short (5-9) | 67.7% | 1.80% | 10.4 |
| Intermediate (10-14) | 56.2% | 2.98% | 15.8 |
| Medium-Deep (15-19) | 53.4% | 4.12% | 20.3 |
| Deep (20-29) | 40.5% | 5.51% | 28.4 |
| Bomb (30+) | 29.8% | 7.37% | 41.2 |

**Critical Findings:**
1. Each yard of air yards costs ~1.5% completion
2. INT rate scales exponentially with depth
3. Deep (20+) has 5.5x INT rate of short passes
4. But deep completions yield 3-4x the yards

### Risk/Reward Calculation

| Throw Type | Completion | INT | Expected Yards | Expected EPA |
|------------|------------|-----|----------------|--------------|
| Screen | 72.6% | 1.04% | 5.2 | 0.02 |
| Short | 67.7% | 1.80% | 7.0 | 0.08 |
| Intermediate | 56.2% | 2.98% | 8.9 | 0.12 |
| Deep | 40.5% | 5.51% | 11.5 | 0.10 |
| Bomb | 29.8% | 7.37% | 12.3 | 0.05 |

**Key Insight:** Intermediate throws (10-14 yards) have the best expected EPA. Deep throws are high-variance but not necessarily higher expected value.

### Aggressiveness Analysis

QBs tiered by NGS "Aggressiveness" metric:

| Tier | Aggressiveness | Completion | CPOE | Rating | INT Rate |
|------|----------------|------------|------|--------|----------|
| Conservative | 14.4 | 66.6% | +0.6% | 94.9 | 1.73% |
| Moderate | 17.5 | 64.0% | -0.2% | 88.6 | 2.11% |
| Aggressive | 21.8 | 63.9% | -1.1% | 86.6 | 2.25% |

**Finding:** Aggressive QBs have lower completion and higher INT rates, but may provide more big play opportunities. The completion penalty for aggression is ~2.7%.

### Simulation Recommendations

```python
def model_air_yards_selection(down, distance, score_diff, qb_aggressiveness):
    """
    Model target depth selection based on situation and QB style.

    Returns air yards for the throw.
    """
    # Base depth based on distance needed
    base_depth = min(distance * 0.8, 15)

    # Score adjustment - trailing teams throw deeper
    if score_diff < -7:
        base_depth += 3
    elif score_diff > 7:
        base_depth -= 2

    # Aggressiveness adjustment
    agg_mod = (qb_aggressiveness - 50) / 50 * 3
    base_depth += agg_mod

    # Add variance
    variance = np.random.normal(0, 5)

    return max(-5, base_depth + variance)


def completion_from_air_yards(air_yards, base_accuracy):
    """Calculate completion probability based on air yards."""

    # Baseline by depth
    if air_yards < 0:
        depth_comp = 0.80
    elif air_yards < 5:
        depth_comp = 0.72
    elif air_yards < 10:
        depth_comp = 0.68
    elif air_yards < 15:
        depth_comp = 0.56
    elif air_yards < 20:
        depth_comp = 0.53
    elif air_yards < 30:
        depth_comp = 0.40
    else:
        depth_comp = 0.30

    # Apply QB accuracy modifier
    accuracy_mod = (base_accuracy - 0.65) / 0.65

    return depth_comp * (1 + accuracy_mod * 0.15)
```

---

## CPOE: True QB Skill

CPOE (Completion Percentage Above Expectation) isolates QB accuracy from situation:

### Distribution

| Metric | Value |
|--------|-------|
| Mean | 0.0% |
| Std Dev | 3.2% |
| 10th percentile | -3.9% |
| 90th percentile | +3.5% |

### By Tier

| Tier | CPOE | Raw Comp | Expected Comp | Rating |
|------|------|----------|---------------|--------|
| Elite | +3.5% | 67.6% | 64.1% | 99.2 |
| Above Avg | +0.9% | 65.5% | 64.6% | 92.0 |
| Below Avg | -1.2% | 64.1% | 65.3% | 88.5 |
| Poor | -4.2% | 60.2% | 64.4% | 78.6 |

**Key Insights:**
1. CPOE spread is 7.7% from Elite to Poor
2. Elite QBs complete 3.5% more than expected given their targets
3. Poor QBs complete 4.2% less than expected
4. Expected completion is ~64.5% for everyone (same target distribution)

### Why CPOE Matters

CPOE removes:
- Target depth selection
- Receiver quality
- Scheme differences
- Play calling

What remains is pure accuracy - the ability to complete throws others would miss.

### Correlations

| Comparison | Correlation |
|------------|-------------|
| CPOE vs Passer Rating | 0.71 |
| CPOE vs Raw Completion | 0.54 |
| CPOE vs Air Yards | -0.18 |

**Finding:** CPOE is strongly correlated with passer rating but only moderately with raw completion. It's slightly negatively correlated with air yards (deeper throwers have slightly lower CPOE).

### Simulation Recommendations

```python
def calculate_completion_probability(air_yards, situation, qb_cpoe_rating):
    """
    Calculate completion probability using CPOE as skill modifier.

    qb_cpoe_rating: 40-99 scale mapping to -4% to +4% CPOE
    """
    # Get expected completion for this throw
    expected_comp = get_expected_completion(air_yards, situation)

    # Apply CPOE modifier
    # Rating 40 = -4%, Rating 95 = +4%
    cpoe = (qb_cpoe_rating - 67.5) / 27.5 * 0.04

    return expected_comp + cpoe
```

---

## Interception Variance

### Overall Rate

| Metric | Value |
|--------|-------|
| Overall INT rate | 2.12% |
| QB 10th percentile | 1.19% |
| QB 90th percentile | 2.99% |

**Finding:** INT rates range from ~1.2% (elite decision-making) to ~3.0% (poor decision-making).

### INT Rate by Air Yards

| Depth | INT Rate | Multiplier vs Short |
|-------|----------|---------------------|
| Short (0-9) | 1.39% | 1.0x |
| Medium (10-19) | 3.44% | 2.5x |
| Deep (20+) | 6.24% | 4.5x |

**Critical Finding:** Deep throws have 4.5x the INT rate of short throws. This is the primary risk factor.

### INT Rate by Score

| Situation | INT Rate |
|-----------|----------|
| Down Big | 2.89% |
| Down | 2.34% |
| Close | 1.98% |
| Up | 1.71% |

**Finding:** Trailing by 14+ increases INT rate by ~70%. Desperate situations lead to risky throws.

### INT Rate by Down

| Down | INT Rate |
|------|----------|
| 1st | 1.83% |
| 2nd | 2.04% |
| 3rd | 2.46% |
| 4th | 3.24% |

**Finding:** 4th down INT rate is nearly double 1st down.

### Simulation Recommendations

```python
def calculate_int_probability(air_yards, situation, qb_decision_rating):
    """
    Calculate interception probability.
    """
    # Base INT rate by depth
    if air_yards < 10:
        base_int = 0.014
    elif air_yards < 20:
        base_int = 0.034
    else:
        base_int = 0.062

    # Situational modifiers
    if situation['score_diff'] < -14:
        base_int *= 1.4
    if situation['down'] == 4:
        base_int *= 1.3

    # QB decision-making modifier
    # Good decision makers: -40% INT, Poor: +40%
    decision_mod = 1.0 - (qb_decision_rating - 50) / 50 * 0.4

    return base_int * decision_mod
```

---

## Play-Level Outcome Variance

### Yards Distribution

| Metric | Value |
|--------|-------|
| Mean | 6.2 yards |
| Std Dev | 9.9 yards |
| Median | 6.0 yards |
| 10th percentile | -3.0 yards |
| 90th percentile | 19.0 yards |
| Negative play rate | 7.9% |
| Big play (20+) rate | 8.4% |

**Finding:** Pass play yards has very high variance (std 9.9). Nearly 8% of passes go for negative yards, 8.4% go for 20+.

### Outcome Distribution

For each pass attempt:
- **Complete:** ~60% (varies by situation)
- **Incomplete:** ~32%
- **Sack:** ~6%
- **Interception:** ~2%

### If Completed

| Metric | Value |
|--------|-------|
| Mean yards | 11.8 |
| Std Dev | 9.1 |
| Median | 9.0 |

Completed pass yards come from air_yards + YAC.

### Simulation Recommendations

```python
def simulate_pass_play(qb, situation, protection_time):
    """
    Complete pass play simulation.
    """
    # Step 1: Determine if pressured
    is_pressured = random.random() < get_pressure_prob(protection_time)

    if is_pressured:
        # Check for sack
        if random.random() < 0.43:
            return {'result': 'sack', 'yards': random.randint(-3, -8)}
        completion_penalty = 0.44  # 44% reduction
    else:
        completion_penalty = 0

    # Step 2: Determine air yards
    air_yards = model_air_yards_selection(situation, qb.aggressiveness)

    # Step 3: Calculate completion probability
    base_comp = completion_from_air_yards(air_yards, qb.accuracy)
    situational_mod = calculate_situational_modifier(situation)
    final_comp = (base_comp + situational_mod) * (1 - completion_penalty)

    # Step 4: Roll for completion
    if random.random() < final_comp:
        yac = model_yac(receiver)
        return {'result': 'complete', 'yards': air_yards + yac}

    # Step 5: Check for INT
    int_prob = calculate_int_probability(air_yards, situation, qb.decision)
    if random.random() < int_prob:
        return {'result': 'interception', 'yards': 0}

    return {'result': 'incomplete', 'yards': 0}
```

---

## Complete Variance Model

### Variance Hierarchy

Variance sources should be applied in layers:

```
1. QB Baseline Skill (CPOE-based)
   └── Season-level: Fixed per QB

2. Game-Level Variance
   └── Game modifier: normal(0, 0.08)

3. Situational Modifiers
   ├── Down: -10% on 3rd, -14% on 4th
   ├── Distance: -1.5% per yard over 5
   ├── Score: -4% when down big
   └── Field Position: -4% in red zone

4. Air Yards Effect
   └── -1.5% per yard of depth

5. Pressure Effect
   └── -44% if pressured (binary)

6. Play-Level Variance
   └── Final roll: random() < probability
```

### Complete Formula

```python
def calculate_final_completion_probability(
    qb_cpoe_rating,      # 40-99
    game_variance,        # Rolled at game start
    down, distance,       # Situation
    score_diff,           # Situation
    field_position,       # 1-99
    air_yards,            # Target depth
    is_pressured          # Boolean
):
    """Calculate final completion probability with all variance sources."""

    # 1. QB baseline from CPOE
    qb_baseline = 0.60 + (qb_cpoe_rating - 40) / 55 * 0.077

    # 2. Game variance (applied once per game)
    game_adjusted = qb_baseline + game_variance

    # 3. Situational modifiers
    sit_mod = 0
    sit_mod += {1: 0.02, 2: 0.01, 3: -0.08, 4: -0.14}.get(down, 0)
    sit_mod -= max(0, (distance - 5)) * 0.015
    if score_diff < -14:
        sit_mod -= 0.04
    if field_position <= 20:
        sit_mod -= 0.04

    situational = game_adjusted + sit_mod

    # 4. Air yards effect
    depth_comp = {
        (-99, 0): 0.80,
        (0, 5): 0.72,
        (5, 10): 0.68,
        (10, 15): 0.56,
        (15, 20): 0.53,
        (20, 30): 0.40,
        (30, 99): 0.30
    }
    for (lo, hi), comp in depth_comp.items():
        if lo <= air_yards < hi:
            air_adjusted = situational * (comp / 0.65)  # Normalize to 65% base
            break

    # 5. Pressure effect
    if is_pressured:
        final = air_adjusted * 0.56  # 44% reduction
    else:
        final = air_adjusted

    return max(0.05, min(0.95, final))
```

---

## Summary: Key Numbers for Simulation

### Probability Baselines

| Event | Base Probability |
|-------|-----------------|
| Completion (overall) | 60% |
| Pressure rate | 15% |
| Sack when pressured | 43% |
| INT rate | 2.1% |
| Big play (20+ yards) | 8.4% |
| Negative play | 7.9% |

### Modifier Magnitudes

| Factor | Effect |
|--------|--------|
| Pressure | -44% completion |
| 3rd down | -10% completion |
| 4th down | -14% completion |
| Per yard over 5 distance | -1.5% completion |
| Per yard of air yards | -1.5% completion |
| Down big | -4% completion |
| Red zone | -4% completion |
| Elite vs Poor QB (CPOE) | +7.7% completion |
| Quick vs Slow release | +2.5% completion |

### Variance Parameters

| Source | Distribution |
|--------|--------------|
| Time to throw | Normal(2.79, 0.16) |
| Game-to-game | Normal(0, 0.08) |
| Air yards | Normal(7.9, 10.1) |
| Completed yards | Normal(11.8, 9.1) |

---

*Report generated by researcher_agent*
*Data: NFL 2019-2024, 293,478 plays analyzed*
