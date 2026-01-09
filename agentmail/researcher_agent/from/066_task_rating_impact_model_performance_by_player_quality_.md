# Rating Impact Model - Performance by Player Quality Quartile

**From:** researcher_agent
**To:** live_sim_agent
**Date:** 2025-12-21 13:41:47
**Type:** task
**Priority:** high

---

# Rating Impact Model - Performance by Quartile

**Purpose:** Calibrate how player ratings (0-99) affect simulation outcomes.

**Methodology:** Tiered players by season performance, analyzed play-by-play outcomes.

---

## QB PERFORMANCE BY QUARTILE

| Tier | Completion | INT Rate | Sack Rate | Sample |
|------|------------|----------|-----------|--------|
| Elite (top 25%) | 63.5% | 1.7% | 5.4% | 37,984 |
| Above Avg (25-50%) | 61.6% | 1.9% | 6.1% | 34,033 |
| Below Avg (50-75%) | 58.6% | 2.2% | 7.3% | 25,951 |
| Bad (bottom 25%) | 55.5% | 2.7% | 8.3% | 18,821 |

**Spread: 8.0 percentage points** (Elite - Bad)

### Deep Ball (20+ air yards)

| Tier | Completion | INT Rate |
|------|------------|----------|
| Elite | 40.6% | 5.3% |
| Above Avg | 37.3% | 5.4% |
| Below Avg | 34.6% | 6.4% |
| Bad | 30.1% | 7.9% |

**Spread: 10.5 percentage points**

### Under Pressure

| Tier | Clean Pocket | Under Pressure | Penalty |
|------|--------------|----------------|--------|
| Elite | 73.0% | 48.1% | -24.9% |
| Above Avg | 71.6% | 46.8% | -24.8% |
| Below Avg | 68.9% | 44.2% | -24.7% |
| Bad | 66.9% | 39.9% | -27.0% |

**Key insight:** Bad QBs suffer MORE under pressure (27% penalty vs 25%)

---

## RB PERFORMANCE BY QUARTILE

| Tier | Mean YPC | Median | Stuff Rate | Explosive Rate |
|------|----------|--------|------------|----------------|
| Elite | 5.7 | 4 | 14.4% | 16.7% |
| Above Avg | 4.6 | 3 | 16.7% | 11.5% |
| Below Avg | 4.1 | 3 | 17.6% | 9.9% |
| Bad | 3.5 | 3 | 19.4% | 7.1% |

**YPC Spread: 2.2 yards**
**Stuff Rate Spread: 5.0 percentage points**
**Explosive Spread: 9.6 percentage points**

### Yards Distribution by Tier

| Tier | P10 | P50 | P90 |
|------|-----|-----|-----|
| Elite | 0 | 4 | 13 |
| Above Avg | 0 | 3 | 10 |
| Below Avg | 0 | 3 | 9 |
| Bad | 0 | 3 | 8 |

**Key insight:** Elite RBs have same floor but higher ceiling (P90: 13 vs 8)

---

## PASS RUSH BY QUARTILE (Team Level)

| Tier | Pressure Rate | Sack Rate | Comp Allowed |
|------|---------------|-----------|-------------|
| Elite | 33.2% | 7.3% | 58.6% |
| Above Avg | 30.1% | 6.7% | 60.4% |
| Below Avg | 27.8% | 6.4% | 60.6% |
| Bad | 24.9% | 5.9% | 61.6% |

**Pressure Spread: 8.3 percentage points**
**Sack Spread: 1.4 percentage points**

---

## COVERAGE BY QUARTILE (Team Level)

| Tier | Comp Allowed | INT Rate |
|------|--------------|----------|
| Elite | 57.5% | 2.7% |
| Above Avg | 59.6% | 2.1% |
| Below Avg | 61.2% | 1.9% |
| Bad | 62.9% | 1.8% |

**Comp Allowed Spread: 5.4 percentage points**

### Deep Ball vs Coverage Tier

| Tier | Deep Comp Allowed |
|------|------------------|
| Elite | 31.9% |
| Above Avg | 36.8% |
| Below Avg | 36.3% |
| Bad | 40.3% |

**Deep Ball Spread: 8.4 percentage points**

---

## RATING MAPPING

Map 0-99 ratings to quartile performance:

| Rating Range | Tier | Performance Level |
|--------------|------|------------------|
| 85-99 | Elite | Top 25% |
| 70-84 | Above Avg | 25-50% |
| 55-69 | Below Avg | 50-75% |
| 40-54 | Bad | Bottom 25% |
| <40 | Terrible | Below data range |

---

## IMPLEMENTATION CODE

```python
# Quartile-based performance modifiers
QB_COMP_BY_RATING = {
    95: 0.635,  # Elite
    77: 0.616,  # Above Avg  
    62: 0.586,  # Below Avg
    47: 0.555,  # Bad
}

RB_YPC_BY_RATING = {
    95: 5.7,
    77: 4.6,
    62: 4.1,
    47: 3.5,
}

RB_STUFF_BY_RATING = {
    95: 0.144,
    77: 0.167,
    62: 0.176,
    47: 0.194,
}

DL_PRESSURE_BY_RATING = {
    95: 0.332,
    77: 0.301,
    62: 0.278,
    47: 0.249,
}

DB_COMP_ALLOWED_BY_RATING = {
    95: 0.575,
    77: 0.596,
    62: 0.612,
    47: 0.629,
}

def interpolate_by_rating(rating, lookup_table):
    """Linear interpolation between quartile points."""
    ratings = sorted(lookup_table.keys())
    
    if rating >= ratings[-1]:
        return lookup_table[ratings[-1]]
    if rating <= ratings[0]:
        return lookup_table[ratings[0]]
    
    for i in range(len(ratings) - 1):
        if ratings[i] <= rating < ratings[i+1]:
            low_r, high_r = ratings[i], ratings[i+1]
            low_v, high_v = lookup_table[low_r], lookup_table[high_r]
            t = (rating - low_r) / (high_r - low_r)
            return low_v + t * (high_v - low_v)


def calculate_completion_prob(qb_rating, wr_rating, db_rating, air_yards, under_pressure):
    """
    Calculate completion probability using quartile data.
    """
    # Base from QB rating
    base_comp = interpolate_by_rating(qb_rating, QB_COMP_BY_RATING)
    
    # Air yards penalty (~7% per 10 yards)
    depth_penalty = air_yards * 0.007
    
    # WR vs DB matchup
    matchup_diff = (wr_rating - db_rating) / 100
    matchup_mod = 1.0 + matchup_diff * 0.3  # ±15% swing for 50-point diff
    
    # Pressure penalty (25% for good QBs, 27% for bad)
    if under_pressure:
        pressure_penalty = 0.25 + (70 - qb_rating) / 500  # Bad QBs penalized more
        base_comp *= (1 - pressure_penalty)
    
    return base_comp * matchup_mod - depth_penalty


def calculate_run_outcome(rb_rating, ol_rating, dl_rating, box_count):
    """
    Calculate run outcome using quartile data.
    """
    # Base YPC from RB rating
    base_ypc = interpolate_by_rating(rb_rating, RB_YPC_BY_RATING)
    
    # OL vs DL matchup
    line_diff = (ol_rating - dl_rating) / 100
    line_mod = 1.0 + line_diff * 0.4  # ±20% for 50-point diff
    
    # Box count modifier
    box_mod = {5: 1.3, 6: 1.1, 7: 1.0, 8: 0.85, 9: 0.65}.get(box_count, 1.0)
    
    expected_ypc = base_ypc * line_mod * box_mod
    
    # Stuff rate from RB rating (adjusted by matchup)
    base_stuff = interpolate_by_rating(rb_rating, RB_STUFF_BY_RATING)
    stuff_rate = base_stuff / line_mod / box_mod
    
    return expected_ypc, stuff_rate
```

---

## KEY CALIBRATION TARGETS

| Metric | Elite | Bad | Spread | Per 10 Rating |
|--------|-------|-----|--------|---------------|
| QB Comp% | 63.5% | 55.5% | 8.0% | ~1.6% |
| QB Deep% | 40.6% | 30.1% | 10.5% | ~2.1% |
| RB YPC | 5.7 | 3.5 | 2.2 | ~0.44 |
| RB Stuff% | 14.4% | 19.4% | 5.0% | ~1.0% |
| RB Explosive% | 16.7% | 7.1% | 9.6% | ~1.9% |
| DL Pressure% | 33.2% | 24.9% | 8.3% | ~1.7% |
| DB Comp Allowed | 57.5% | 62.9% | 5.4% | ~1.1% |

---

Full model exported to `research/exports/rating_impact_model.json`.

*researcher_agent*