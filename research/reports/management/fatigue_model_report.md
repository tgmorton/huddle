# NFL Fatigue & Snap Count Model

**Data:** NFL Snap Counts 2019-2024
**Purpose:** Manage player fatigue and rotation

---

## Executive Summary

This model provides:
- Typical snap percentages by position
- Performance degradation curves by snap count
- Rotation recommendations
- Multi-game fatigue tracking

---

## SNAP PERCENTAGE BY POSITION

| Position | Mean | Median | Starter Target (P90) |
|----------|------|--------|---------------------|
| QB | 80% | 100% | 100% |
| RB | 31% | 27% | 69% |
| WR | 50% | 53% | 92% |
| TE | 43% | 41% | 83% |
| OL | 67% | 100% | 100% |
| DL | 47% | 47% | 77% |
| EDGE | 46% | 42% | 90% |
| LB | 43% | 37% | 100% |
| CB | 53% | 60% | 100% |
| S | 55% | 65% | 100% |

### Interpretation
- **Starter Target**: Top players at position typically play at this rate
- **Median**: Rotation players typically play at this rate
- Below median = deep backup/special teams only

---

## FATIGUE CURVE

| Snap Percentage | Performance Multiplier | Penalty |
|-----------------|----------------------|---------|
| 0% | 1.00 | -0% |
| 50% | 1.00 | -0% |
| 70% | 0.99 | -1% |
| 80% | 0.97 | -3% |
| 90% | 0.94 | -6% |
| 95% | 0.90 | -10% |
| 100% | 0.85 | -15% |

### Position Fatigue Modifiers

| Position | Fatigue Rate | Notes |
|----------|-------------|-------|
| DL | 1.4x | Tires quickly |
| RB | 1.3x | Tires quickly |
| EDGE | 1.2x |  |
| TE | 1.1x |  |
| LB | 1.1x |  |
| WR | 1.0x |  |
| CB | 1.0x |  |
| OL | 0.9x |  |
| S | 0.9x |  |
| QB | 0.7x | High endurance |

### Implementation

```python
def calculate_fatigue_penalty(player, snap_pct):
    '''
    Calculate performance penalty from fatigue.

    Returns: multiplier (0.85 - 1.0)
    '''
    # Base fatigue curve
    CURVE = {0: 1.0, 0.5: 1.0, 0.7: 0.99, 0.8: 0.97, 0.9: 0.94, 0.95: 0.90, 1.0: 0.85}

    # Find closest point in curve
    for threshold in sorted(CURVE.keys(), reverse=True):
        if snap_pct >= threshold:
            base_penalty = CURVE[threshold]
            break

    # Apply position modifier
    pos_mod = POSITION_FATIGUE_MODIFIERS.get(player.position, 1.0)

    # Stronger penalty for high-fatigue positions
    if pos_mod > 1.0:
        extra_penalty = (1 - base_penalty) * (pos_mod - 1)
        return base_penalty - extra_penalty

    return base_penalty
```

---

## ROTATION RECOMMENDATIONS

| Position | Rotation Size | Lead Player % | Min Share |
|----------|--------------|---------------|-----------|
| RB | 2 | 70% | 33% |
| DL | 6 | 30% | 14% |
| WR | 4 | 50% | 20% |
| TE | 2 | 70% | 33% |
| LB | 4 | 50% | 20% |
| CB | 3 | 60% | 25% |

### Key Insights

1. **RB Committee**: Most teams use 2-3 backs, lead gets 55-65%
2. **DL Rotation**: Heavy rotation (3-4 players), fresh pass rushers matter
3. **WR**: Top 2-3 get most snaps, slot often different player
4. **DB**: CBs play heavy, but nickel allows rotation

---

## MULTI-GAME FATIGUE

| Condition | Effect |
|-----------|--------|
| games_1 | +0% |
| games_2 | -2% |
| games_3 | -5% |
| games_4 | -8% |
| bye_week_recovery | +5% |
| thursday_game_penalty | -3% |

### Implementation

```python
def calculate_weekly_fatigue(player, games_without_rest):
    '''
    Calculate cumulative fatigue from consecutive games.
    '''
    CUMULATIVE = {1: 1.0, 2: 0.98, 3: 0.95, 4: 0.92}

    base = CUMULATIVE.get(min(games_without_rest, 4), 0.92)

    # Adjust for age
    if player.age > 30:
        age_penalty = (player.age - 30) * 0.01
        base -= age_penalty

    return max(0.85, base)
```

---

## IMPLEMENTATION CODE

```python
class FatigueSystem:

    def __init__(self):
        self.snap_targets = SNAP_TARGETS
        self.fatigue_curve = FATIGUE_CURVE
        self.position_mods = POSITION_FATIGUE_MODIFIERS

    def update_player_fatigue(self, player, snap_pct):
        '''Update fatigue after a game.'''

        # In-game fatigue based on snaps
        game_fatigue = self.get_fatigue_penalty(player, snap_pct)

        # Accumulate over season
        player.fatigue_baseline = max(
            0.85,
            player.fatigue_baseline * 0.95 + (1 - game_fatigue) * 0.05
        )

        return player.fatigue_baseline

    def get_fatigue_penalty(self, player, snap_pct):
        '''Get current performance penalty.'''

        # Base from curve
        for threshold in sorted(self.fatigue_curve.keys(), reverse=True):
            if isinstance(threshold, float) and snap_pct >= threshold:
                base = self.fatigue_curve[threshold]
                break
        else:
            base = 1.0

        # Position modifier
        pos_mod = self.position_mods.get(player.position, 1.0)

        if pos_mod > 1.0:
            return base - (1 - base) * (pos_mod - 1)

        return base

    def recommend_snap_target(self, player, is_starter=True):
        '''Get recommended snap percentage for player.'''

        targets = self.snap_targets.get(player.position, {})

        if is_starter:
            return targets.get('starter_target_pct', 0.85)
        else:
            return targets.get('rotation_target_pct', 0.40)
```

---

## FACTOR MAPPING TO SIMULATION

| Finding | Variable | Value |
|---------|----------|-------|
| 95%+ snaps = -10% | `HIGH_SNAP_PENALTY` | 0.90 |
| DL fatigue rate | `DL_FATIGUE_MOD` | 1.4x |
| RB fatigue rate | `RB_FATIGUE_MOD` | 1.3x |
| QB endurance | `QB_FATIGUE_MOD` | 0.7x |
| Bye week boost | `BYE_RECOVERY` | 1.05x |
| Thursday penalty | `SHORT_REST_PENALTY` | 0.97 |
| 4+ games no rest | `CUMULATIVE_FATIGUE` | 0.92 |

---

*Model built by researcher_agent*
