# Brief for Simulation Agent: Game Prep Integration

**From:** Management Agent
**Date:** 2025-12-17
**Subject:** Game Prep Bonus System

---

## Overview

The management agent has implemented a **Game Prep Bonus System** that provides temporary bonuses when a team studies their upcoming opponent during practice. These bonuses should be applied during game simulation.

---

## New Module: `huddle/core/game_prep.py`

The following has been created:

```python
@dataclass
class GamePrepBonus:
    opponent_id: Optional[UUID]    # Who the prep is for
    opponent_name: str             # Display name
    prep_level: float              # 0.0-1.0 (how much prep done)
    week: int                      # Game week this prep is for
    scheme_recognition: float      # +% to play recognition (0-0.10)
    execution_bonus: float         # +% to execution (0-0.05)
```

---

## Key Interface for Simulation

### Checking for Game Prep Bonus

When simulating a game, check if the team has prepared:

```python
from huddle.core.models.team import Team

team: Team = ...
opponent_id: UUID = ...

# Option 1: Get total bonus multiplier
bonus = team.get_game_prep_bonus(opponent_id)
# Returns 1.0 (no prep) to ~1.075 (full prep)

# Option 2: Access individual bonuses
if team.game_prep_bonus and team.game_prep_bonus.is_valid_for_opponent(opponent_id):
    scheme_mult = team.game_prep_bonus.get_scheme_multiplier()      # 1.0 to 1.10
    execution_mult = team.game_prep_bonus.get_execution_multiplier() # 1.0 to 1.05
```

### When to Apply Bonuses

1. **Scheme Recognition Bonus** (`scheme_recognition`):
   - Apply to play recognition / awareness checks
   - Helps defense read offensive tendencies
   - Helps offense anticipate defensive schemes
   - Example: `effective_awareness = awareness * scheme_mult`

2. **Execution Bonus** (`execution_bonus`):
   - Apply to execution / accuracy checks
   - Bonus when calling plays that counter opponent's tendencies
   - Example: `effective_accuracy = accuracy * execution_mult`

---

## Clearing Prep After Game

After a game is complete, clear the expired prep:

```python
# After game simulation completes
current_week = ...  # The week just played
team.clear_expired_prep(current_week)
```

This prevents the prep from carrying over to future weeks.

---

## Example Integration

```python
def simulate_play(offense_team, defense_team, opponent_id):
    # Get game prep bonuses
    offense_prep = offense_team.get_game_prep_bonus(defense_team.id)
    defense_prep = defense_team.get_game_prep_bonus(offense_team.id)

    # Apply to relevant checks
    # Offense: apply prep bonus to QB reads, route timing
    qb_awareness = qb.attributes.get("awareness") * offense_prep

    # Defense: apply prep bonus to coverage recognition
    cb_play_rec = cb.attributes.get("play_recognition") * defense_prep

    # ... continue with play resolution
```

---

## Bonus Ranges

| Prep Level | Scheme Recognition | Execution Bonus | Total Multiplier |
|------------|-------------------|-----------------|------------------|
| 0% (none)  | +0%               | +0%             | 1.00x            |
| 25%        | +2.5%             | +1.25%          | ~1.02x           |
| 50%        | +5%               | +2.5%           | ~1.04x           |
| 75%        | +7.5%             | +3.75%          | ~1.06x           |
| 100%       | +10%              | +5%             | ~1.075x          |

---

## Files to Reference

- `huddle/core/game_prep.py` - GamePrepBonus dataclass
- `huddle/core/models/team.py` - `Team.get_game_prep_bonus()`, `Team.clear_expired_prep()`
- `huddle/management/league.py` - `_apply_game_prep()` (practice integration)

---

## Summary

1. **Check for prep**: `team.get_game_prep_bonus(opponent_id)` returns multiplier
2. **Apply to attributes**: Multiply relevant attributes (awareness, play_recognition)
3. **Clear after game**: Call `team.clear_expired_prep(week)` after game completes
4. **Both teams can prep**: Both offense and defense may have studied each other
