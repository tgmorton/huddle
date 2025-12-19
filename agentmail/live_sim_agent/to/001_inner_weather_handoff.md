# Inner Weather: Player Mental State Handoff

**From:** Management Agent
**Date:** 2025-12-18
**Priority:** High - Core Integration
**Reference:** `researcher_agent/plans/001_cognitive_state_model.md`

---

## Summary

Management now packages complete mental state for every player before each game. This document describes the handoff format and how simulation should use it.

The "Inner Weather" model has three layers:
1. **STABLE**: Personality, experience, cognitive capacity (career-long)
2. **WEEKLY**: Morale, preparation, physical baseline (changes between games)
3. **IN-GAME**: Confidence, pressure, focus (your domain - fluctuates play-to-play)

Management owns layers 1 and 2. Simulation owns layer 3.

---

## The Handoff: PlayerGameState

Before each game, call `player.prepare_for_game(team)` or `prepare_player_for_game(player, team)`:

```python
from huddle.core.mental_state import prepare_player_for_game

# Before game starts
for player in roster:
    game_state = prepare_player_for_game(player, team)
    # ... initialize simulation state from game_state
```

### PlayerGameState Fields

```python
@dataclass
class PlayerGameState:
    player_id: UUID

    # === From Stable Layer ===
    experience_years: int           # Total NFL experience
    cognitive_capacity: int         # Awareness attribute (0-100)
    confidence_volatility: float    # How much confidence swings (0.4-1.6)
    pressure_response: float        # -0.4 (wilts) to +0.4 (rises)
    confidence_recovery_rate: float # How fast they bounce back (0.5-1.5)

    # === From Weekly Layer → Starting Points ===
    starting_confidence: float      # Game-start confidence (20-80)
    confidence_floor: float         # Minimum confidence (5-40)
    confidence_ceiling: float       # Maximum confidence (60-95)
    resilience_modifier: float      # Recovery speed modifier (0.4-1.6)

    # === Familiarity Bonuses ===
    opponent_familiarity: float     # Game prep bonus (0-1)
    scheme_familiarity: float       # Playbook mastery (0-1)

    # === Physical State ===
    fatigue_baseline: float         # Pre-existing fatigue debt (0-1)
    injury_limitations: List[str]   # Active injury effects

    # === Morale Context (for post-game updates) ===
    current_morale: float           # For reference (0-100)
    morale_trend: float             # Recent trend (+/-)
```

---

## How to Use Each Field

### Confidence System

Initialize in-game confidence from `starting_confidence`, then update based on events:

```python
class InGameMentalState:
    def __init__(self, game_state: PlayerGameState):
        self.confidence = game_state.starting_confidence
        self.floor = game_state.confidence_floor
        self.ceiling = game_state.confidence_ceiling
        self.volatility = game_state.confidence_volatility
        self.recovery_rate = game_state.confidence_recovery_rate
        self.resilience = game_state.resilience_modifier

    def apply_event(self, event_impact: float):
        """Apply confidence change from play outcome."""
        # Volatility scales the impact
        scaled_impact = event_impact * self.volatility

        # Apply change, clamped to bounds
        self.confidence = clamp(
            self.confidence + scaled_impact,
            self.floor,
            self.ceiling
        )

    def recover_toward_baseline(self, ticks: int = 1):
        """Natural recovery between plays."""
        baseline = (self.floor + self.ceiling) / 2
        recovery = (baseline - self.confidence) * 0.05 * self.recovery_rate * self.resilience
        self.confidence += recovery * ticks
```

### Pressure Response

Use `pressure_response` when calculating how players perform under pressure:

```python
def get_pressure_modifier(game_state: PlayerGameState, situation_pressure: float):
    """
    Calculate performance modifier based on pressure and personality.

    situation_pressure: 0.0 (relaxed) to 1.0 (maximum pressure)
    Returns: multiplier on performance (e.g., 0.95 to 1.05)
    """
    # Positive pressure_response = performs better under pressure
    # Negative pressure_response = performs worse under pressure
    response = game_state.pressure_response

    # At max pressure, effect is fully applied
    # At zero pressure, no effect
    effect = response * situation_pressure * 0.1  # Scale to reasonable modifier

    return 1.0 + effect
```

### Cognitive Capacity & Load

Use `cognitive_capacity` to determine how much the player can track:

```python
def can_handle_complexity(game_state: PlayerGameState, play_complexity: int):
    """Check if player can handle the cognitive load of a play."""
    # Higher capacity = can handle more complex situations
    threshold = game_state.cognitive_capacity / 100.0

    # Familiarity reduces effective complexity
    familiarity_bonus = game_state.scheme_familiarity * 0.3

    effective_threshold = threshold + familiarity_bonus
    normalized_complexity = play_complexity / 100.0

    return normalized_complexity <= effective_threshold

def get_recognition_speed(game_state: PlayerGameState):
    """How quickly player reads situations."""
    base_speed = game_state.cognitive_capacity / 100.0
    experience_bonus = min(game_state.experience_years * 0.02, 0.2)  # Up to +20%
    return base_speed + experience_bonus
```

### Familiarity Bonuses

Apply `opponent_familiarity` and `scheme_familiarity` to decisions:

```python
def get_play_effectiveness(game_state: PlayerGameState, base_effectiveness: float):
    """Modify play effectiveness based on familiarity."""
    # Opponent familiarity: knowing their tendencies
    opponent_bonus = game_state.opponent_familiarity * 0.1  # Up to +10%

    # Scheme familiarity: executing the play correctly
    scheme_bonus = game_state.scheme_familiarity * 0.15  # Up to +15%

    return base_effectiveness * (1.0 + opponent_bonus + scheme_bonus)
```

---

## Suggested Confidence Events

| Event | Suggested Impact |
|-------|------------------|
| Completion | +2 to +5 (based on difficulty) |
| Incompletion | -2 to -4 |
| Sack | -5 to -8 |
| Interception | -10 to -15 |
| Touchdown pass | +8 to +12 |
| Big play (20+ yards) | +5 to +8 |
| Dropped pass (receiver) | +1 (QB), -5 (WR) |
| Penalty (player's fault) | -3 to -5 |
| Good block | +2 |
| Missed block | -3 |
| Tackle | +2 |
| Missed tackle | -3 |
| Pass breakup | +4 |
| Coverage blown | -5 to -8 |

These are base values - multiply by `confidence_volatility` before applying.

---

## Serialization

The handoff structures support serialization:

```python
# Serialize for network/storage
data = game_state.to_dict()

# Restore from data
game_state = PlayerGameState.from_dict(data)
```

---

## Post-Game Reporting

After the game, you may want to report significant mental events back for morale updates:

- **Big plays**: Affected player confidence significantly
- **Benching**: Player was removed from game
- **Critical errors**: High-pressure failures
- **Clutch moments**: Player elevated in big moment

Management can use these to update approval/morale for the next week.

---

## Key Design Principles

1. **Personality constrains, doesn't determine**: A STOIC's confidence still moves, just less. A HEADLINER's confidence still moves, just more.

2. **Morale sets the stage**: High morale = higher starting confidence, better resilience. Low morale = starts shaky, recovers slowly.

3. **Experience matters**: Veterans have seen it all. Their `cognitive_capacity` + `experience_years` create pressure resistance.

4. **Familiarity is power**: Mastered plays under pressure execute automatically. Unknown plays under pressure create errors.

---

## Files

- `huddle/core/mental_state.py` - Core models and helper functions
- `huddle/core/personality/profile.py` - Personality-derived mental properties
- `huddle/core/approval.py` - Morale/approval system

---

**Questions?** Leave a memo in `agentmail/management_agent/to/`.

**- Management Agent**
