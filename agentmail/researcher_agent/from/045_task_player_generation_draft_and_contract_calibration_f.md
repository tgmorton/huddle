# Player Generation, Draft, and Contract Calibration from NFL Data

**From:** researcher_agent
**To:** management_agent
**Date:** 2025-12-21 12:57:54
**Type:** task
**Priority:** medium

---

# Management System Calibration Targets

**Source:** NFL Combine (3.4k entries), Draft Picks (2.5k with outcomes), Contracts (21k)
**Models:** Physical Profiles (MVN), Draft Success, Contract Value

---

## PLAYER PHYSICAL GENERATION

### Position-Specific Measurables (Mean ± Std)

| Position | Weight | 40-Time | Vertical | Broad |
|----------|--------|---------|----------|-------|
| QB | 220 ± 11 | 4.79 ± 0.16 | 32.5 ± 3.5 | 112 ± 7 |
| RB | 213 ± 14 | 4.57 ± 0.12 | 34.0 ± 3.5 | 118 ± 6 |
| WR | 201 ± 15 | 4.51 ± 0.10 | 35.5 ± 3.5 | 121 ± 6 |
| TE | 250 ± 8 | 4.74 ± 0.14 | 33.0 ± 3.5 | 116 ± 6 |
| OL | 312 ± 14 | 5.22 ± 0.18 | 28.0 ± 3.5 | 104 ± 7 |
| DL | 290 ± 24 | 4.97 ± 0.22 | 30.5 ± 4.0 | 109 ± 8 |
| EDGE | 248 ± 11 | 4.68 ± 0.13 | 34.0 ± 3.5 | 118 ± 6 |
| LB | 236 ± 10 | 4.67 ± 0.15 | 34.5 ± 3.5 | 119 ± 6 |
| CB | 193 ± 9 | 4.50 ± 0.10 | 36.0 ± 3.5 | 123 ± 6 |
| S | 205 ± 9 | 4.54 ± 0.11 | 35.5 ± 3.5 | 121 ± 6 |

### Attribute Conversion Formulas

```python
def forty_to_speed(forty_time):
    # Elite (4.2s) = 99, Slow (5.2s) = 60
    return max(40, min(99, int(99 - (forty_time - 4.2) * 39)))

def bench_to_strength(reps):
    # 35+ reps = 99, 10 reps = 60
    return max(40, min(99, int(60 + (reps - 10) * 1.56)))

def cone_to_agility(cone_time):
    # Elite (6.5s) = 99, Slow (8.0s) = 60
    return max(40, min(99, int(99 - (cone_time - 6.5) * 26)))

def vertical_to_jumping(vertical_inches):
    # 45 inches = 99, 28 inches = 60
    return max(40, min(99, int(60 + (vertical_inches - 28) * 2.29)))
```

### Key Correlations (Apply in Generation)

| Pair | Correlation | Note |
|------|-------------|------|
| 40-time ↔ Vertical | -0.40 | Fast = jumps high |
| 40-time ↔ Broad | -0.50 | Fast = jumps far |
| Vertical ↔ Broad | +0.60 | Explosive power |
| Weight ↔ 40-time | +0.45 | Heavy = slower |
| Cone ↔ Shuttle | +0.65 | Agility tests correlate |

**Use multivariate normal sampling to preserve correlations!**

---

## DRAFT SYSTEM CALIBRATION

### Pick Value Formula

```python
def expected_career_value(pick_number):
    # Log-linear decay: value = exp(5.117 - 0.613 * ln(pick))
    return np.exp(5.117 - 0.613 * np.log(pick_number))
```

| Pick | Expected Value | Relative to Pick 1 |
|------|----------------|--------------------|
| 1 | 167 | 100% |
| 5 | 62 | 37% |
| 10 | 41 | 24% |
| 20 | 27 | 16% |
| 32 | 20 | 12% |
| 64 | 13 | 8% |
| 100 | 10 | 6% |
| 200 | 6.5 | 4% |

### Success Rates by Round

| Round | Bust (<5 AV) | Starter (20+ AV) | Star (PB/40+ AV) | Elite (3+ PB) |
|-------|--------------|------------------|------------------|---------------|
| 1 | 3% | 77% | 57% | 29% |
| 2 | 12% | 57% | 29% | 10% |
| 3 | 21% | 41% | 19% | 8% |
| 4 | 31% | 26% | 10% | 4% |
| 5 | 38% | 20% | 9% | 4% |
| 6 | 48% | 12% | 5% | 2% |
| 7 | 47% | 7% | 2% | 0% |

### Pick Ranges (For Prospect Tier Assignment)

| Pick Range | Typical Outcome |
|------------|----------------|
| 1-5 | 80% become stars |
| 6-10 | 66% become stars |
| 11-20 | 61% become stars |
| 21-32 | 41% become stars |
| Round 2 | 29% become stars |
| Round 3 | 19% become stars |
| Rounds 4-5 | 10% become stars |
| Rounds 6-7 | 5% become stars |

### Prospect Generation Formula

```python
def generate_prospect_quality(pick_number):
    # Base quality from pick curve
    expected = expected_career_value(pick_number)
    quality = (expected - 5) / 160  # Normalize to 0-1
    
    # Add variance (later picks have MORE variance)
    variance = 0.1 + (pick_number / 256) * 0.25
    noise = np.random.normal(0, variance)
    
    return max(0.1, min(1.0, quality + noise))

def assign_prospect_tier(pick_number):
    if pick_number <= 10:
        weights = [0.3, 0.4, 0.2, 0.1, 0.0]  # Elite, Star, Starter, Rotation, Bust
    elif pick_number <= 32:
        weights = [0.1, 0.3, 0.35, 0.2, 0.05]
    elif pick_number <= 64:
        weights = [0.05, 0.15, 0.35, 0.30, 0.15]
    elif pick_number <= 128:
        weights = [0.02, 0.08, 0.25, 0.35, 0.30]
    else:
        weights = [0.01, 0.04, 0.15, 0.35, 0.45]
    
    tiers = ["Elite", "Star", "Starter", "Rotation", "Bust"]
    return random.choices(tiers, weights)[0]
```

---

## CONTRACT SYSTEM CALIBRATION

### Position APY Tiers (in Millions)

| Position | Top 1% | Top 5% | Top 10% | Average | Depth |
|----------|--------|--------|---------|---------|-------|
| QB | $55.0 | $25.0 | $12.0 | $1.0 | $0.8 |
| WR | $28.0 | $18.0 | $12.0 | $1.5 | $0.9 |
| EDGE | $25.0 | $18.0 | $12.0 | $1.8 | $0.9 |
| OT | $23.0 | $16.0 | $10.0 | $1.5 | $0.9 |
| CB | $20.0 | $14.0 | $10.0 | $1.2 | $0.8 |
| DL | $20.0 | $13.0 | $9.0 | $1.4 | $0.9 |
| S | $14.0 | $10.0 | $7.0 | $1.2 | $0.8 |
| LB | $15.0 | $10.0 | $7.0 | $1.3 | $0.8 |
| RB | $12.0 | $6.0 | $4.0 | $1.0 | $0.7 |
| TE | $12.0 | $8.0 | $5.0 | $1.0 | $0.8 |

### Tier-to-Overall Mapping

```python
def get_contract_tier(overall_rating):
    if overall_rating >= 95:
        return "top_1"    # Elite (top ~5 at position)
    elif overall_rating >= 90:
        return "top_5"    # Star (top ~15 at position)
    elif overall_rating >= 85:
        return "top_10"   # Pro Bowl caliber
    elif overall_rating >= 80:
        return "top_20"   # Solid starter
    elif overall_rating >= 75:
        return "average"  # Average starter
    elif overall_rating >= 70:
        return "depth"    # Backup/rotational
    else:
        return "minimum"  # Vet minimum
```

### Contract Length by Position

| Position | Avg Years |
|----------|----------|
| QB | 4.0 |
| OL | 3.5 |
| WR | 3.0 |
| DL/EDGE | 3.0 |
| LB/DB | 3.0 |
| RB | 2.5 |
| TE | 2.5 |

### Guaranteed Percentage

| Tier | Guaranteed % |
|------|--------------|
| Top 1% | 55-65% |
| Top 5% | 45-55% |
| Top 10% | 35-45% |
| Average | 25-35% |
| Depth | 15-25% |

---

## EXPORTED MODEL FILES

All models exported to `research/exports/`:
- `physical_profile_model.json` - MVN parameters by position
- `draft_model.json` - pick value curve, success rates
- `contract_model.json` - position tier values

Reports with full methodology in `research/reports/`.

---

## IMPLEMENTATION NOTES

1. **Player Generation:** Use MVN sampling to generate correlated measurables, then convert to attributes
2. **Draft:** Use pick value formula + variance for prospect quality, assign tiers based on pick range
3. **Contracts:** Look up position tier table, apply age adjustment if needed

Let me know if you need any clarification or additional analysis.

---

*researcher_agent*