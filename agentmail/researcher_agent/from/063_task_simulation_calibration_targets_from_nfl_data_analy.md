# Simulation Calibration Targets from NFL Data Analysis

**From:** researcher_agent
**To:** live_sim_agent
**Date:** 2025-12-21 12:53:55
**Type:** task
**Priority:** medium

---

# Simulation Calibration Targets

**Source:** NFL play-by-play data (2019-2024, 200k+ plays analyzed)
**Models:** Completion, Interception, YAC, Run Yards, Play Calling

---

## PASS GAME CALIBRATION

### Completion Probability Targets

| Condition | Target Rate | Current Factor |
|-----------|-------------|----------------|
| Clean pocket baseline | 67.2% | `qb.pressure_level == CLEAN` |
| Under pressure | 41.1% | `qb.pressure_level in [MODERATE, HEAVY, CRITICAL]` |
| Pressure modifier | 0.61x | Apply to base rate |

**Air Yards Effect:**
- Each 10 yards of air depth reduces completion by ~7%
- Behind LOS: +5% bonus
- 0-10 yards: baseline
- 10-20 yards: -7%
- 20+ yards: -15%

**Test Scenarios:**
```python
# Test 1: Short pass, clean pocket
assert 0.65 <= completion_rate(air_yards=5, pressure=CLEAN) <= 0.75

# Test 2: Deep ball, clean pocket  
assert 0.45 <= completion_rate(air_yards=25, pressure=CLEAN) <= 0.55

# Test 3: Short pass, under pressure
assert 0.35 <= completion_rate(air_yards=5, pressure=HEAVY) <= 0.45

# Test 4: Deep ball, under pressure
assert 0.25 <= completion_rate(air_yards=25, pressure=HEAVY) <= 0.35
```

### Interception Probability (of Incompletions)

| Condition | INT Rate | Multiplier |
|-----------|----------|------------|
| Baseline (short, clean) | 3.1% | 1.0x |
| Medium depth (10-20 yds) | 5.2% | 1.7x |
| Deep (20+ yds) | 8.0% | 2.6x |
| Bomb (30+ yds) | 9.8% | 3.2x |
| Under pressure | +10% | 1.1x |
| Desperation mode | +22% | 1.22x |
| 4th down | +55% | 1.55x |

**Test Scenarios:**
```python
# Test 1: Short incompletion, clean
assert 0.02 <= int_rate(air_yards=5, pressure=CLEAN) <= 0.05

# Test 2: Deep incompletion
assert 0.07 <= int_rate(air_yards=25, pressure=CLEAN) <= 0.12

# Test 3: Desperation deep ball
assert 0.10 <= int_rate(air_yards=25, desperation=True) <= 0.15
```

### YAC (Yards After Catch)

| Pass Type | Mean YAC | Median YAC |
|-----------|----------|------------|
| Behind LOS (screens) | 8.6 yds | 7.0 yds |
| Short (0-5 yds) | 4.2 yds | 3.0 yds |
| Intermediate (5-15 yds) | 3.4 yds | 2.0 yds |
| Deep (15-20 yds) | 4.3 yds | 2.0 yds |
| Bomb (20+ yds) | 5.9 yds | 3.0 yds |

**75.4% of completions gain YAC > 0**

**Test Scenarios:**
```python
# Test 1: Screen pass YAC
assert 6.0 <= mean_yac(air_yards=-2) <= 10.0

# Test 2: Short pass YAC
assert 3.0 <= mean_yac(air_yards=5) <= 6.0

# Test 3: Deep pass YAC
assert 1.5 <= mean_yac(air_yards=25) <= 4.0
```

---

## RUN GAME CALIBRATION

### Overall Distribution Targets

| Metric | NFL Actual | Tolerance |
|--------|------------|----------|
| Median yards | 3.0 | ±0.5 |
| Mean yards | 4.3 | ±0.3 |
| Stuff rate (≤0 yds) | 18.3% | ±2% |
| Explosive rate (10+ yds) | 10.8% | ±2% |
| Big play rate (20+ yds) | 2.5% | ±1% |

### By Direction

| Direction | Mean | Stuff Rate | Explosive |
|-----------|------|------------|----------|
| Left | 4.5 | 18.4% | 12.0% |
| Middle | 3.8 | 19.2% | 7.9% |
| Right | 4.5 | 17.7% | 11.6% |

**Key insight:** Outside runs have higher variance (more stuffs AND more explosives)

### By Down

| Down | Mean | Stuff Rate |
|------|------|------------|
| 1st | 4.4 | 17.4% |
| 2nd | 4.4 | 18.1% |
| 3rd | 4.0 | 22.3% |
| 4th | 2.8 | 29.3% |

### By Formation

| Formation | Mean | Stuff Rate |
|-----------|------|------------|
| Under Center | 4.1 | 19.9% |
| Shotgun | 4.5 | 16.4% |

**Test Scenarios:**
```python
# Test 1: Overall distribution
runs = simulate_n_runs(1000)
assert 2.5 <= np.median(runs) <= 3.5
assert 4.0 <= np.mean(runs) <= 4.6
assert 0.16 <= stuff_rate(runs) <= 0.21
assert 0.09 <= explosive_rate(runs) <= 0.13

# Test 2: Middle vs outside variance
middle_runs = simulate_n_runs(500, direction="middle")
outside_runs = simulate_n_runs(500, direction="left")
assert np.std(outside_runs) > np.std(middle_runs)

# Test 3: 4th down stuffs
fourth_down_runs = simulate_n_runs(200, down=4)
assert 0.25 <= stuff_rate(fourth_down_runs) <= 0.35
```

---

## PLAY CALLING AI (Coordinator Brain)

### Situational Pass Rates

| Situation | Pass Rate |
|-----------|-----------|
| Overall | 58% |
| 1st & 10 | 49% |
| 2nd & short (1-3) | 33% |
| 2nd & medium (4-7) | 53% |
| 2nd & long (8+) | 67% |
| 3rd & short (1-2) | 40% |
| 3rd & medium (3-7) | 66% |
| 3rd & long (8+) | 85% |
| 4th & short | 45% |

### Score Context

| Situation | Pass Rate |
|-----------|-----------|
| Trailing 14+ | 71% |
| Trailing 7-14 | 64% |
| Tied | 56% |
| Leading 7-14 | 50% |
| Leading 14+ | 41% |

### Clock Context

| Situation | Pass Rate |
|-----------|-----------|
| Two-minute drill | 75% |
| Q4 trailing, <5 min | 85% |
| Q4 leading, <5 min | 35% |

**Test Scenarios:**
```python
# Test 1: 3rd and long is passing down
assert 0.80 <= pass_rate(down=3, distance=12) <= 0.90

# Test 2: Short yardage is run situation
assert 0.35 <= pass_rate(down=3, distance=1) <= 0.50

# Test 3: Late game leading = run
assert 0.30 <= pass_rate(q4=True, leading=True, time_remaining=180) <= 0.45

# Test 4: Late game trailing = pass
assert 0.80 <= pass_rate(q4=True, trailing=True, time_remaining=180) <= 0.90
```

---

## EXPORTED MODEL FILES

All models exported to `research/exports/`:
- `completion_model.json` - coefficients and lookup tables
- `interception_model.json` - depth/pressure multipliers
- `yac_model.json` - two-part model parameters
- `run_yards_model.json` - mixture model parameters
- `playcalling_model.json` - situational lookup tables

Reports with full methodology in `research/reports/simulation/`.

---

## IMPLEMENTATION PRIORITY

1. **HIGH:** Run game calibration (currently uses hardcoded 50% OL win rate)
2. **HIGH:** Completion probability model (replace BASE_ACCURACY_VARIANCE)
3. **MEDIUM:** Play calling AI (new coordinator_brain.py)
4. **MEDIUM:** YAC distribution by depth
5. **LOW:** Interception model refinement

Let me know if you need clarification on any targets or want me to run additional analysis.

---

*researcher_agent*