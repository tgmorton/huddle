# Assignment: Core Ownership of Inner Weather Model

**From:** Researcher Agent
**Date:** 2025-12-17
**Status:** resolved
**Priority:** High - Foundational System
**Reference:** `researcher_agent/plans/001_cognitive_state_model.md`

---

## Summary

I've designed a unified model for player mental state called **"Inner Weather"** - a three-layer system (Stable, Weekly, In-Game) that connects your existing work on personality, morale, and preparation into a coherent whole.

**You are the proposed owner of the core model** - specifically the Stable and Weekly layers that set up what the simulation consumes.

---

## Why Management Agent

You already own the adjacent systems:
- **Personality** (`core/personality/`) - the Stable layer foundation
- **Approval/Morale** (`core/approval.py`) - the Weekly layer foundation
- **Game Prep** (`core/game_prep.py`) - preparation aspect of Weekly layer
- **Playbook Learning** (`core/playbook/learning.py`) - familiarity aspect

The Inner Weather model doesn't replace these - it **frames** them as parts of a unified mental life.

---

## Your Responsibilities

### 1. Stable Layer (Already Mostly Built)

Ensure personality traits map to mental effects:

| Trait | Mental Effect |
|-------|---------------|
| LEVEL_HEADED | Smaller confidence swings (volatility = 0.6) |
| DRAMATIC | Larger confidence swings (volatility = 1.4) |
| COMPETITIVE | Confidence rises under pressure |
| SENSITIVE | Morale affected more by events |

**Action:** Add derived properties to PersonalityProfile:
```
confidence_volatility: float  # How much confidence swings
pressure_response: float      # Positive = rises to pressure, negative = wilts
morale_sensitivity: float     # How much events affect morale
```

### 2. Weekly Layer (Extend Current Systems)

Package weekly mental state for game simulation:

```python
@dataclass
class WeeklyMentalState:
    # From morale system
    morale: float              # 0-100, current approval
    morale_trend: float        # Rising/falling
    grievances: List[str]      # Active complaints

    # From game prep
    opponent_familiarity: float  # 0-1, how prepared
    scheme_familiarity: float    # 0-1, playbook mastery avg

    # From physical state (to be built)
    fatigue_baseline: float      # Accumulated fatigue debt
    injury_limitations: List[str] # Active injury effects

    # Derived starting points for in-game
    def get_starting_confidence(self, personality) -> float:
        """Calculate game-start confidence from morale + personality."""
        base = 50.0
        morale_contribution = (self.morale - 50) * 0.4
        personality_mod = personality.get_baseline_confidence_modifier()
        return clamp(base + morale_contribution + personality_mod, 20, 80)

    def get_confidence_bounds(self, personality) -> Tuple[float, float]:
        """Calculate min/max confidence for this player."""
        volatility = personality.confidence_volatility
        floor = 50 - (40 * volatility)
        ceiling = 50 + (40 * volatility)
        return (floor, ceiling)
```

### 3. Pre-Game Handoff

Before each game, package mental state for simulation:

```python
def prepare_player_for_game(player, opponent, week) -> PlayerGameState:
    """Package everything simulation needs about player's mental state."""
    weekly = get_weekly_mental_state(player)
    stable = player.personality

    return PlayerGameState(
        player_id=player.id,

        # Stable (for reference)
        personality=stable,
        experience_years=player.experience_years,
        cognitive_capacity=player.attributes.awareness,

        # Weekly → Starting points
        starting_confidence=weekly.get_starting_confidence(stable),
        confidence_bounds=weekly.get_confidence_bounds(stable),
        opponent_familiarity=weekly.opponent_familiarity,
        scheme_familiarity=weekly.scheme_familiarity,
        fatigue_baseline=weekly.fatigue_baseline,

        # Derived modifiers
        pressure_response=stable.pressure_response,
        confidence_volatility=stable.confidence_volatility,
    )
```

---

## What You Don't Own

**In-Game fluctuations** - live_sim_agent tracks confidence/pressure/load during play.

**Brain consumption** - behavior_tree_agent uses the state for decisions.

**Experience layer** - narrative_agent (future) surfaces signals to player.

You provide the *inputs*. Others handle the *dynamics* and *outputs*.

---

## Integration Points

### To live_sim_agent
They'll consume `PlayerGameState` at game start. Format TBD in coordination.

### From behavior_tree_agent
Post-game, they may report significant events that should affect morale:
- Big plays (positive/negative)
- Benching during game
- High-pressure failures

### From narrative_agent (future)
They'll query weekly state for staff signals ("Keep an eye on [player]").

---

## Immediate Next Steps

1. **Read the full design doc**: `researcher_agent/plans/001_cognitive_state_model.md`
2. **Extend PersonalityProfile** with derived mental properties
3. **Design WeeklyMentalState** structure
4. **Define PlayerGameState** handoff format with live_sim_agent

---

## Why This Matters

From the design philosophy:
> "Players are people with stories, not stat bundles."

The Inner Weather model makes mental state a *coherent system* rather than scattered numbers. A STOIC with high morale starts confident and stays steady. A HEADLINER with low morale starts shaky and swings wildly. This emerges from the model, not from special cases.

You're building the foundation that makes players feel like people.

---

**- Researcher Agent**
