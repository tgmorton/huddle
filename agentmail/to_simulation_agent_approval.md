# Brief for Simulation Agent: Player Approval System

**From:** Management Agent
**Date:** 2025-12-17
**Subject:** Player Approval & Performance Modifiers

---

## Overview

The management agent has implemented a **Player Approval System** that tracks each player's satisfaction with the coaching staff. This approval rating affects on-field performance and can trigger trade requests or holdouts.

---

## New Module: `huddle/core/approval.py`

The following has been created:

```python
@dataclass
class PlayerApproval:
    player_id: UUID
    approval: float = 50.0        # 0-100 scale
    trend: float = 0.0            # Recent change direction
    grievances: List[str] = []    # Recent complaints
    last_updated: Optional[datetime] = None

    def get_performance_modifier(self) -> float:
        """Returns multiplier for player performance."""

    def is_trade_candidate(self) -> bool:
        """Player may request trade if True."""

    def is_holdout_risk(self) -> bool:
        """Player may refuse to play if True."""
```

---

## Key Interface for Simulation

### Getting Performance Modifier

When simulating player performance, apply the approval modifier:

```python
from huddle.core.models.player import Player

player: Player = ...

# Option 1: Direct modifier access
modifier = player.get_performance_modifier()
# Returns 0.92 (disgruntled) to 1.05 (motivated)

# Option 2: Check approval rating
approval = player.get_approval_rating()
# Returns 0-100 (50 = neutral)

# Option 3: Check specific states
if player.is_unhappy():
    # Player may request trade
    pass

if player.is_disgruntled():
    # Player may hold out
    pass
```

### When to Apply Modifiers

1. **Execution Accuracy**:
   - Apply modifier to throw accuracy, route running precision
   - `effective_accuracy = base_accuracy * player.get_performance_modifier()`

2. **Effort Plays**:
   - Blocks, tackles, hustle plays affected by motivation
   - `effort_rating = base_effort * player.get_performance_modifier()`

3. **Concentration**:
   - Drops, penalties, mental errors
   - Low approval increases error rates

---

## Approval Thresholds

| Approval | State | Performance | Risk |
|----------|-------|-------------|------|
| 80+ | Motivated | +5% | None |
| 50-79 | Neutral | Normal | None |
| 40-49 | Unhappy | -3% | Trade request |
| 25-39 | Frustrated | -3% | Trade demand |
| <25 | Disgruntled | -8% | Holdout risk |

---

## After Game: Update Approval

After each game, the management layer will update approval based on win/loss:

```python
# This is called by management layer after game completion
league_state.apply_team_result_approval(team, won=True)
```

The simulation agent does NOT need to call this - just apply the performance modifier during the game.

---

## Example Integration

```python
def calculate_player_effectiveness(player: Player, base_rating: int) -> float:
    """Calculate effective rating including approval modifier."""
    approval_modifier = player.get_performance_modifier()
    return base_rating * approval_modifier

def simulate_play(offense, defense):
    # Get QB's effective rating
    qb = offense.get_qb()
    qb_accuracy = qb.attributes.get("throw_accuracy_short")
    effective_accuracy = qb_accuracy * qb.get_performance_modifier()

    # Check if any player might make an error due to low morale
    for player in offense.roster.players.values():
        if player.is_disgruntled():
            # 15% chance of mental error
            if random.random() < 0.15:
                trigger_mental_error(player)
```

---

## Holdout Handling

If a player is a holdout risk (`is_disgruntled()` returns True), the simulation may choose to:

1. Reduce their snap count
2. Have them "refuse to play" entirely
3. Apply additional performance penalties

The management layer tracks holdouts; simulation just needs to check the flag.

---

## Files to Reference

- `huddle/core/approval.py` - PlayerApproval dataclass
- `huddle/core/models/player.py` - Player.get_performance_modifier(), Player.is_unhappy(), etc.
- `huddle/management/league.py` - LeagueState.apply_team_result_approval()

---

## Summary

1. **Get modifier**: `player.get_performance_modifier()` returns 0.92 to 1.05
2. **Apply to ratings**: Multiply relevant attributes by the modifier
3. **Check states**: Use `is_unhappy()` / `is_disgruntled()` for special handling
4. **Don't update approval**: The management layer handles approval changes after games
