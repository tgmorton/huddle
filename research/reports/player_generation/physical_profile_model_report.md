# Player Physical Profile Model

**Model Type:** Multivariate Normal (MVN) by Position
**Data:** 3,274 combine entries (2015-2024)
**Positions Modeled:** 10

---

## Executive Summary

This model provides statistical distributions for generating realistic player physical profiles:

- **Height/Weight** distributions by position
- **Athletic measurables** (40, bench, vertical, broad, cone, shuttle)
- **Correlations** between measurables (fast players tend to jump high)
- **Composite athletic scores** for talent classification

---

## Position Profiles

### QB

**Sample Size:** 162

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 220.1 | 10.90 | 207.0 | 234.0 |
| Forty | 4.8 | 0.16 | 4.6 | 5.0 |
| Vertical | 31.5 | 2.94 | 27.5 | 35.5 |
| Broad Jump | 113.9 | 6.29 | 105.0 | 122.0 |
| Cone | 7.1 | 0.19 | 6.9 | 7.3 |
| Shuttle | 4.3 | 0.15 | 4.2 | 4.5 |

### RB

**Sample Size:** 321

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 213.3 | 14.16 | 196.9 | 231.0 |
| Forty | 4.6 | 0.12 | 4.4 | 4.7 |
| Bench | 19.1 | 4.81 | 13.0 | 25.0 |
| Vertical | 34.3 | 3.21 | 30.0 | 38.5 |
| Broad Jump | 119.6 | 5.25 | 113.0 | 126.3 |
| Cone | 7.1 | 0.20 | 6.8 | 7.4 |
| Shuttle | 4.3 | 0.15 | 4.1 | 4.5 |

### WR

**Sample Size:** 483

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 201.4 | 14.95 | 182.0 | 220.0 |
| Forty | 4.5 | 0.10 | 4.4 | 4.6 |
| Bench | 14.3 | 4.07 | 9.0 | 19.0 |
| Vertical | 35.5 | 3.24 | 31.5 | 39.5 |
| Broad Jump | 122.9 | 5.91 | 115.0 | 131.0 |
| Cone | 7.0 | 0.22 | 6.7 | 7.3 |
| Shuttle | 4.3 | 0.15 | 4.1 | 4.5 |

### TE

**Sample Size:** 197

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 250.0 | 7.95 | 241.0 | 259.7 |
| Forty | 4.7 | 0.14 | 4.6 | 4.9 |
| Bench | 19.3 | 3.47 | 15.0 | 23.5 |
| Vertical | 33.5 | 3.02 | 29.5 | 37.5 |
| Broad Jump | 117.8 | 5.70 | 110.0 | 125.0 |
| Cone | 7.2 | 0.21 | 6.9 | 7.4 |
| Shuttle | 4.4 | 0.15 | 4.2 | 4.5 |

### OL

**Sample Size:** 562

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 312.1 | 14.37 | 301.0 | 327.0 |
| Forty | 5.2 | 0.18 | 5.0 | 5.5 |
| Bench | 24.8 | 5.19 | 19.0 | 32.0 |
| Vertical | 28.3 | 3.26 | 24.0 | 32.5 |
| Broad Jump | 105.3 | 6.56 | 97.0 | 113.0 |
| Cone | 7.8 | 0.31 | 7.4 | 8.2 |
| Shuttle | 4.8 | 0.19 | 4.5 | 5.0 |

### DL

**Sample Size:** 442

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 289.7 | 24.35 | 258.0 | 320.0 |
| Forty | 5.0 | 0.22 | 4.7 | 5.3 |
| Bench | 25.1 | 5.06 | 20.0 | 32.0 |
| Vertical | 30.9 | 3.66 | 26.5 | 35.5 |
| Broad Jump | 111.3 | 8.01 | 101.0 | 121.0 |
| Cone | 7.5 | 0.35 | 7.0 | 8.0 |
| Shuttle | 4.6 | 0.23 | 4.3 | 4.9 |

### EDGE

**Sample Size:** 211

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 248.2 | 11.26 | 232.0 | 262.0 |
| Forty | 4.7 | 0.13 | 4.5 | 4.8 |
| Bench | 22.1 | 3.94 | 17.0 | 26.5 |
| Vertical | 34.1 | 3.25 | 30.0 | 38.0 |
| Broad Jump | 120.0 | 6.14 | 112.0 | 128.0 |
| Cone | 7.1 | 0.20 | 6.9 | 7.4 |
| Shuttle | 4.3 | 0.13 | 4.2 | 4.5 |

### LB

**Sample Size:** 268

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 236.0 | 10.23 | 226.0 | 247.0 |
| Forty | 4.7 | 0.15 | 4.5 | 4.9 |
| Bench | 20.5 | 4.05 | 15.0 | 26.0 |
| Vertical | 34.0 | 3.17 | 30.5 | 39.0 |
| Broad Jump | 119.3 | 5.98 | 111.0 | 127.0 |
| Cone | 7.1 | 0.23 | 6.9 | 7.4 |
| Shuttle | 4.3 | 0.16 | 4.1 | 4.5 |

### CB

**Sample Size:** 437

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 193.3 | 9.39 | 181.0 | 205.0 |
| Forty | 4.5 | 0.10 | 4.4 | 4.6 |
| Bench | 14.6 | 3.99 | 10.0 | 19.0 |
| Vertical | 36.1 | 3.04 | 32.5 | 40.5 |
| Broad Jump | 124.1 | 5.67 | 117.0 | 132.0 |
| Cone | 7.0 | 0.20 | 6.7 | 7.2 |
| Shuttle | 4.2 | 0.15 | 4.0 | 4.4 |

### S

**Sample Size:** 191

| Measurable | Mean | Std | P10 | P90 |
|------------|------|-----|-----|-----|
| Wt | 204.9 | 8.90 | 195.0 | 217.0 |
| Forty | 4.5 | 0.11 | 4.4 | 4.7 |
| Bench | 16.6 | 3.53 | 12.0 | 21.0 |
| Vertical | 35.4 | 3.00 | 32.0 | 39.5 |
| Broad Jump | 122.4 | 6.19 | 115.0 | 131.0 |
| Cone | 7.0 | 0.19 | 6.7 | 7.2 |
| Shuttle | 4.2 | 0.13 | 4.1 | 4.4 |

---

## Athletic Tier Distribution

| Position | Poor | Below Avg | Average | Above Avg | Elite |
|----------|------|-----------|---------|-----------|-------|
| QB | 12% | 14% | 45% | 18% | 11% |
| RB | 6% | 16% | 52% | 18% | 7% |
| WR | 7% | 14% | 55% | 15% | 9% |
| TE | 8% | 13% | 53% | 16% | 10% |
| OL | 10% | 13% | 51% | 17% | 10% |
| DL | 11% | 15% | 48% | 16% | 10% |
| EDGE | 8% | 13% | 53% | 19% | 7% |
| LB | 11% | 14% | 49% | 17% | 10% |
| CB | 7% | 14% | 55% | 16% | 10% |
| S | 6% | 18% | 53% | 12% | 11% |


---

## Attribute Conversion Formulas

### Speed (SPD) from 40-Time

```python
def forty_to_speed(forty_time):
    '''
    Convert 40-yard dash time to 0-99 Speed rating.
    '''
    # Elite (4.2s) = 99, Slow (5.2s) = 60
    speed = 99 - ((forty_time - 4.2) * 39)
    return max(40, min(99, int(speed)))
```

### Strength (STR) from Bench Press

```python
def bench_to_strength(reps):
    '''
    Convert bench press reps to 0-99 Strength rating.
    '''
    # 35+ reps = 99, 10 reps = 60
    strength = 60 + ((reps - 10) * 1.56)
    return max(40, min(99, int(strength)))
```

### Agility (AGI) from 3-Cone

```python
def cone_to_agility(cone_time):
    '''
    Convert 3-cone time to 0-99 Agility rating.
    '''
    # Elite (6.5s) = 99, Slow (8.0s) = 60
    agility = 99 - ((cone_time - 6.5) * 26)
    return max(40, min(99, int(agility)))
```

### Jumping (JMP) from Vertical

```python
def vertical_to_jumping(vertical_inches):
    '''
    Convert vertical jump to 0-99 Jumping rating.
    '''
    # 45 inches = 99, 28 inches = 60
    jumping = 60 + ((vertical_inches - 28) * 2.29)
    return max(40, min(99, int(jumping)))
```

---

## Model Usage

### Generating a New Player

```python
import numpy as np

def generate_physical_profile(position):
    '''
    Generate realistic physical measurables for a position.
    Uses multivariate normal to maintain correlations.
    '''
    # Load MVN parameters for position
    mvn_params = PHYSICAL_PROFILES[position]

    # Sample from multivariate normal
    mean = np.array([mvn_params['mean'][v] for v in mvn_params['variables']])
    cov = np.array([[mvn_params['cov'][v1][v2]
                    for v2 in mvn_params['variables']]
                   for v1 in mvn_params['variables']])

    sample = np.random.multivariate_normal(mean, cov)

    # Return as dict
    return dict(zip(mvn_params['variables'], sample))
```

---

## Key Correlations

Across positions, these correlations are consistent:

| Pair | Typical r | Interpretation |
|------|-----------|----------------|
| 40-time ↔ Vertical | -0.40 | Fast players jump high |
| 40-time ↔ Broad | -0.50 | Fast players jump far |
| Vertical ↔ Broad | +0.60 | Explosive power transfers |
| Weight ↔ 40-time | +0.45 | Heavier = slower |
| Weight ↔ Bench | +0.35 | Bigger = stronger |
| Cone ↔ Shuttle | +0.65 | Agility tests correlate |

---

## Position Archetypes

### Speed Positions (WR, CB, RB)
- 40-time: 4.40-4.60
- Vertical: 35-40 inches
- Weight: 175-215 lbs

### Size Positions (OL, DL)
- Weight: 290-330 lbs
- Bench: 25-35 reps
- 40-time: 4.90-5.30

### Hybrid Positions (TE, LB, EDGE)
- Balance of size and speed
- 40-time: 4.55-4.80
- Weight: 240-265 lbs

---

## Figures

- `physical_height_weight.png`
- `physical_forty_by_position.png`
- `physical_correlation_wr.png`
- `physical_position_comparison.png`
- `physical_athletic_scores.png`

---

*Model built by researcher_agent*
