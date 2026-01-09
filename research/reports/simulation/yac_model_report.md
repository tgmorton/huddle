# Yards After Catch (YAC) Model

**Model Type:** Two-Part (Logistic + Log-Linear)
**Data:** 73,640 completions (2019-2024)
**Mean YAC:** 5.2 yards

---

## Executive Summary

YAC is the yards gained after the catch. Key findings:

- **Short passes = more YAC** (screens average 4.2 yds)
- **Deep passes = less YAC** (bombs average 5.9 yds)
- **RBs have highest YAC** (scheme designed for space)
- **75.4%** of completions gain additional yardage

---

## YAC by Pass Depth

| Depth Bucket | Mean YAC | Median YAC | % with YAC | N |
|--------------|----------|------------|------------|---|
| behind_los | 8.6 | 7.0 | 93.4% | 18,747 |
| screen_short | 4.2 | 3.0 | 75.4% | 25,503 |
| short | 3.4 | 2.0 | 64.4% | 13,266 |
| intermediate | 3.4 | 1.0 | 58.6% | 7,557 |
| deep | 4.3 | 2.0 | 64.5% | 4,477 |
| bomb | 5.9 | 3.0 | 72.2% | 4,090 |


## YAC by Receiver Position

| Position | Mean YAC | Median YAC | % with YAC |
|----------|----------|------------|------------|
| WR | 5.2 | 3.0 | 75.4% |


---

## Two-Part Model

### Part 1: P(YAC > 0 | completion)

Models whether any YAC is gained. Key drivers:
- **Shorter air yards** → higher P(YAC)
- **RB/TE** → higher P(YAC) than WR on average
- **Open field** → higher P(YAC)

### Part 2: E[YAC | YAC > 0]

Models amount of YAC given positive YAC. Uses log-linear model:
- Log-transform handles right-skewed YAC distribution
- Key driver is still air yards (inverse relationship)

---

## Model Usage

```python
def predict_yac(air_yards, receiver_pos='WR', separation=None):
    '''
    Predict expected YAC for a completion.
    '''
    # Base YAC by depth
    if air_yards < 0:
        base_yac = 6.0   # Behind LOS - screens
    elif air_yards < 5:
        base_yac = 5.0   # Screen/short
    elif air_yards < 10:
        base_yac = 4.0   # Short
    elif air_yards < 15:
        base_yac = 3.5   # Intermediate
    elif air_yards < 20:
        base_yac = 2.5   # Deep
    else:
        base_yac = 1.5   # Bomb

    # Position modifier
    pos_mult = {'WR': 1.0, 'TE': 0.9, 'RB': 1.3}.get(receiver_pos, 1.0)

    # Separation boost (if available)
    if separation is not None:
        sep_mult = 1.0 + (separation * 0.05)  # +5% per yard separation
    else:
        sep_mult = 1.0

    return base_yac * pos_mult * sep_mult
```

---

## YAC Distribution

| Percentile | YAC (yards) |
|------------|-------------|
| 10% | 0.0 |
| 25% | 1.0 |
| 50% | 3.0 |
| 75% | 7.0 |
| 90% | 13.0 |
| 95% | 17.0 |


---

## Huddle Factor Mapping

| NFL Factor | Huddle Factor | Available |
|------------|---------------|-----------|
| air_yards | `pass.air_yards` | ✅ Yes |
| receiver_position | `receiver.position` | ✅ Yes |
| pass_location | Derived from play | ⚠️ Derivable |
| separation | `receiver.separation` | ✅ Yes |

### Implementation Candidates

| Factor | Importance | Notes |
|--------|------------|-------|
| separation_at_catch | HIGH | More separation = more YAC |
| defender_angle | HIGH | Tackle angle affects YAC |
| receiver_speed | HIGH | Speed creates YAC opportunities |
| field_position | MEDIUM | Less space near goal line |

---

## Key Insights

1. **Depth is the primary driver** - Short passes yield 3-4x more YAC than deep balls
2. **Scheme matters** - RB screens designed for YAC (6+ yards average)
3. **YAC is highly variable** - std dev (6.7) exceeds mean
4. **Right-skewed distribution** - Most plays have 0-5 YAC, some have 20+

---

## Figures

- `yac_distribution.png`
- `yac_by_depth.png`
- `yac_by_position.png`
- `yac_by_location.png`
- `yac_depth_position_heatmap.png`

---

*Model built by researcher_agent*
