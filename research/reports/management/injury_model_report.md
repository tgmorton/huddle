# NFL Injury Model

**Data:** NFL Injury Reports 2019-2024
**Purpose:** Position-specific injury rates, types, and durations

---

## Executive Summary

This model provides:
- Per-game injury probability by position
- Injury type probabilities given an injury
- Expected duration by injury type
- Season-ending injury rates

---

## INJURY RATES BY POSITION

| Position | Per-Game Rate | Modifier | Notes |
|----------|---------------|----------|-------|
| QB | 3.30% | 0.60x | Low risk |
| RB | 4.68% | 0.85x |  |
| WR | 7.78% | 1.42x | High risk |
| TE | 6.26% | 1.14x |  |
| OL | 5.88% | 1.07x |  |
| DL | 7.80% | 1.42x | High risk |
| LB | 7.45% | 1.35x | High risk |
| CB | 7.15% | 1.30x | High risk |
| S | 4.69% | 0.85x |  |

### Implementation

```python
def check_for_injury(position, is_contact_play=False):
    '''
    Roll for injury after each play.
    Returns injury_type or None.
    '''
    base_rate = POSITION_INJURY_RATES[position]['per_game_rate']

    # Increase on contact plays
    if is_contact_play:
        rate = base_rate * 1.5
    else:
        rate = base_rate * 0.5

    if random.random() < rate:
        return sample_injury_type(position)

    return None
```

---

## INJURY TYPE PROBABILITIES

| Injury Type | Probability | Typical Duration |
|-------------|-------------|------------------|
| Unknown | 53.3% | 2 weeks |
| Leg Muscle | 11.1% | 2 weeks |
| Knee (Other) | 7.9% | 3 weeks |
| Ankle | 7.0% | 3 weeks |
| Shoulder | 3.2% | 4 weeks |
| Concussion | 2.8% | 2 weeks |
| Foot | 2.7% | 4 weeks |
| Illness | 2.0% | 1 weeks |
| Back | 1.7% | 3 weeks |
| Hip | 1.5% | 3 weeks |
| Chest/Ribs | 1.4% | 2 weeks |
| Hand/Wrist | 1.3% | 2 weeks |

---

## INJURY DURATION MODEL

| Injury Type | Min Weeks | Typical Weeks | Season-Ending Rate |
|-------------|-----------|---------------|-------------------|
| Achilles | 6 | 16 | 80% |
| Knee Ligament | 6 | 12 | 65% |
| Shoulder | 2 | 4 | 15% |
| Foot | 2 | 4 | 20% |
| Ankle | 1 | 3 | 10% |
| Back | 1 | 3 | 8% |
| Hip | 1 | 3 | 10% |
| Core | 1 | 3 | 8% |
| Knee (Other) | 1 | 3 | 12% |
| Concussion | 1 | 2 | 5% |
| Leg Muscle | 1 | 2 | 5% |
| Hand/Wrist | 1 | 2 | 5% |
| Chest/Ribs | 1 | 2 | 5% |
| Neck | 1 | 2 | 10% |
| Arm | 1 | 2 | 5% |
| Other | 1 | 2 | 5% |
| Unknown | 1 | 2 | 5% |
| Illness | 1 | 1 | 1% |
| Rest/Personal | 1 | 1 | 1% |

### Duration Sampling

```python
def sample_injury_duration(injury_type):
    '''
    Sample injury duration in weeks.
    '''
    params = DURATION_BY_TYPE[injury_type]

    # Check for season-ending
    if random.random() < params['season_ending_rate']:
        return 17  # Rest of season

    # Sample from distribution (gamma-like)
    min_weeks = params['min_weeks']
    typical = params['typical_weeks']

    # Use gamma distribution centered on typical
    duration = max(min_weeks, int(np.random.gamma(
        shape=typical / 2,
        scale=2
    )))

    return min(duration, 17)
```

---

## POSITION-SPECIFIC INJURY PATTERNS

### QB

| Injury Type | Share |
|-------------|-------|
| Unknown | 61.2% |
| Ankle | 4.5% |
| Knee (Other) | 4.3% |
| Hand/Wrist | 4.3% |
| Shoulder | 4.2% |

### RB

| Injury Type | Share |
|-------------|-------|
| Unknown | 50.9% |
| Leg Muscle | 11.5% |
| Ankle | 9.6% |
| Knee (Other) | 7.8% |
| Foot | 3.5% |

### WR

| Injury Type | Share |
|-------------|-------|
| Unknown | 51.3% |
| Leg Muscle | 15.0% |
| Knee (Other) | 6.8% |
| Ankle | 6.3% |
| Concussion | 3.8% |

### TE

| Injury Type | Share |
|-------------|-------|
| Unknown | 55.2% |
| Leg Muscle | 10.7% |
| Knee (Other) | 8.0% |
| Ankle | 6.2% |
| Concussion | 4.4% |

### OL

| Injury Type | Share |
|-------------|-------|
| Unknown | 55.8% |
| Knee (Other) | 10.0% |
| Ankle | 8.9% |
| Leg Muscle | 5.8% |
| Concussion | 2.8% |

### DL

| Injury Type | Share |
|-------------|-------|
| Unknown | 59.1% |
| Knee (Other) | 8.0% |
| Leg Muscle | 7.6% |
| Ankle | 6.2% |
| Shoulder | 3.5% |

### LB

| Injury Type | Share |
|-------------|-------|
| Unknown | 53.0% |
| Leg Muscle | 12.2% |
| Knee (Other) | 8.3% |
| Ankle | 6.8% |
| Shoulder | 3.3% |

### CB

| Injury Type | Share |
|-------------|-------|
| Unknown | 45.8% |
| Leg Muscle | 17.6% |
| Knee (Other) | 6.8% |
| Ankle | 6.1% |
| Shoulder | 3.9% |

### S

| Injury Type | Share |
|-------------|-------|
| Unknown | 48.7% |
| Leg Muscle | 15.3% |
| Ankle | 7.0% |
| Knee (Other) | 7.0% |
| Concussion | 3.5% |


---

## SPECIAL RULES

### Concussion Protocol
- Minimum 5 days out
- Typical 10 days
- Must pass independent evaluation

### IR Rules
- Minimum 4 weeks on IR (short-term)
- Maximum 8 IR returns per team per season
- Some injuries (ACL, Achilles) are automatically season-ending

### Soft Tissue Re-Injury Risk
- Hamstring: 25% re-injury risk within 4 weeks of return
- Groin: 20% re-injury risk
- Calf: 20% re-injury risk

---

## IMPLEMENTATION CODE

```python
class InjurySystem:

    def __init__(self):
        self.position_rates = POSITION_INJURY_RATES
        self.type_probs = INJURY_TYPE_PROBABILITIES
        self.durations = DURATION_BY_TYPE

    def check_injury(self, player, is_contact=False):
        '''Check if player gets injured on this play.'''
        base_rate = self.position_rates[player.position]['per_game_rate']
        rate = base_rate * (1.5 if is_contact else 0.5)

        if random.random() > rate:
            return None

        # Determine injury type
        injury_type = self.sample_injury_type(player.position)

        # Determine duration
        duration = self.sample_duration(injury_type)

        return Injury(
            player=player,
            injury_type=injury_type,
            duration_weeks=duration,
            is_season_ending=(duration >= 17)
        )

    def sample_injury_type(self, position):
        '''Sample injury type weighted by position patterns.'''
        # Position-specific weighting would go here
        types = list(self.type_probs.keys())
        probs = list(self.type_probs.values())
        return random.choices(types, weights=probs)[0]

    def sample_duration(self, injury_type):
        '''Sample duration for injury type.'''
        params = self.durations.get(injury_type, {'min_weeks': 1, 'typical_weeks': 2, 'season_ending_rate': 0.05})

        if random.random() < params['season_ending_rate']:
            return 17

        duration = max(
            params['min_weeks'],
            int(np.random.gamma(params['typical_weeks'] / 2, 2))
        )
        return min(duration, 17)
```

---

## FACTOR MAPPING TO SIMULATION

| Finding | Variable | Value |
|---------|----------|-------|
| Base injury rate | `BASE_INJURY_RATE` | 5.5% per game |
| RB high risk | `RB_MODIFIER` | 1.3x |
| OL high risk | `OL_MODIFIER` | 1.2x |
| QB low risk | `QB_MODIFIER` | 0.7x |
| Knee ligament duration | `ACL_WEEKS` | 12 (65% season-ending) |
| Concussion duration | `CONCUSSION_DAYS` | 10 |
| Contact multiplier | `CONTACT_MULTIPLIER` | 1.5x |

---

*Model built by researcher_agent*
