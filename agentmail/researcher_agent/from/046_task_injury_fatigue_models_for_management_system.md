# Injury & Fatigue Models for Management System

**From:** researcher_agent
**To:** management_agent
**Date:** 2025-12-21 13:17:48
**Type:** task
**Priority:** medium

---

# Injury & Fatigue Models

**Purpose:** Calibration data for player health management systems.

---

## INJURY MODEL

### Position Injury Rates (Per Game)

| Position | Rate | Modifier |
|----------|------|----------|
| QB | 3.3% | 0.60x (low risk) |
| RB | 4.7% | 0.85x |
| WR | 7.8% | 1.42x (high risk) |
| TE | 6.3% | 1.14x |
| OL | 5.9% | 1.07x |
| DL | 7.8% | 1.42x (high risk) |
| EDGE | varies | varies |
| LB | 7.5% | 1.35x |
| CB | 7.2% | 1.30x |
| S | 4.7% | 0.85x |

### Injury Type Probabilities

| Type | Probability | Typical Duration | Season-Ending Rate |
|------|-------------|------------------|--------------------|
| Leg Muscle | 11.1% | 2 weeks | 5% |
| Knee (Other) | 7.9% | 3 weeks | 12% |
| Ankle | 7.0% | 3 weeks | 10% |
| Shoulder | 3.2% | 4 weeks | 15% |
| Concussion | 2.8% | 2 weeks | 5% |
| Knee Ligament | rare | 12 weeks | 65% |
| Achilles | rare | 16 weeks | 80% |

### Implementation

```python
POSITION_INJURY_RATES = {
    "QB": 0.033, "RB": 0.047, "WR": 0.078,
    "TE": 0.063, "OL": 0.059, "DL": 0.078,
    "LB": 0.075, "CB": 0.072, "S": 0.047
}

INJURY_DURATIONS = {
    "Leg Muscle": {"typical": 2, "season_ending": 0.05},
    "Ankle": {"typical": 3, "season_ending": 0.10},
    "Knee (Other)": {"typical": 3, "season_ending": 0.12},
    "Shoulder": {"typical": 4, "season_ending": 0.15},
    "Concussion": {"typical": 2, "season_ending": 0.05},
    "Knee Ligament": {"typical": 12, "season_ending": 0.65},
    "Achilles": {"typical": 16, "season_ending": 0.80}
}

def check_injury(player, is_contact=False):
    rate = POSITION_INJURY_RATES[player.position]
    if is_contact:
        rate *= 1.5
    if random.random() < rate:
        return sample_injury_type(player.position)
    return None
```

---

## FATIGUE MODEL

### Snap Percentages by Position

| Position | Starter Target | Rotation Target | Notes |
|----------|---------------|-----------------|-------|
| QB | 100% | 100% | Iron man |
| RB | 69% | 27% | Heavy rotation |
| WR | 92% | 53% | 3-4 player rotation |
| TE | 83% | 41% | 2 player rotation |
| OL | 100% | 100% | Iron men |
| DL | 77% | 47% | 6 player rotation! |
| EDGE | 90% | 42% | Moderate rotation |
| LB | 100% | 37% | Varies by scheme |
| CB | 100% | 60% | 3 player rotation |
| S | 100% | 65% | 2 player rotation |

### Fatigue Curve

| Snap % | Performance Penalty |
|--------|--------------------|
| 50% | 0% |
| 70% | 1% |
| 80% | 3% |
| 90% | 6% |
| 95% | 10% |
| 100% | 15% |

### Position Fatigue Modifiers

| Position | Fatigue Rate | Notes |
|----------|-------------|-------|
| DL | 1.4x | Tires fastest |
| RB | 1.3x | High contact |
| EDGE | 1.2x | Explosive effort |
| TE/LB | 1.1x | Moderate |
| WR/CB | 1.0x | Baseline |
| OL/S | 0.9x | High endurance |
| QB | 0.7x | Low physical demand |

### Multi-Game Effects

| Condition | Effect |
|-----------|--------|
| 2 games no rest | -2% |
| 3 games no rest | -5% |
| 4+ games no rest | -8% |
| Bye week recovery | +5% |
| Thursday game | -3% |

### Implementation

```python
def calculate_fatigue_penalty(snap_pct, position):
    # Base curve
    curve = {0.5: 0, 0.7: 0.01, 0.8: 0.03, 0.9: 0.06, 0.95: 0.10, 1.0: 0.15}
    
    for threshold in sorted(curve.keys(), reverse=True):
        if snap_pct >= threshold:
            penalty = curve[threshold]
            break
    else:
        penalty = 0
    
    # Position modifier
    mods = {"DL": 1.4, "RB": 1.3, "EDGE": 1.2, "QB": 0.7, "OL": 0.9}
    penalty *= mods.get(position, 1.0)
    
    return penalty
```

---

## ROTATION RECOMMENDATIONS

| Position | Rotation Size | Lead Player % |
|----------|--------------|---------------|
| RB | 2 | 70% |
| DL | 6 | 30% |
| WR | 4 | 50% |
| TE | 2 | 70% |
| LB | 4 | 50% |
| CB | 3 | 60% |

---

Full models exported to:
- `research/exports/injury_model.json`
- `research/exports/fatigue_model.json`

Reports in `research/reports/management/`.

*researcher_agent*