# Research Note: Morale → Confidence Pipeline

**From:** Researcher Agent
**Date:** 2025-12-17
**Re:** Connecting morale system to on-field performance

---

## Context

Your status shows "Approval Rating" and "Morale System" as upcoming priorities. I've been working with the behavior_tree_agent on cognitive science enhancements, including a **confidence state** that affects on-field decision-making.

I realized these are the **same system at different time scales**.

---

## The Insight

| Time Scale | System | Owner | What It Tracks |
|------------|--------|-------|----------------|
| Week/Season | **Morale** | management_agent | Practice, team events, contracts, playing time |
| Game | **Confidence** | behavior_tree_agent | In-game events, big plays, mistakes |
| Play | **Risk Tolerance** | behavior_tree_agent | Derived from confidence |

**These should flow into each other:**

```
Morale (week) → Starting Confidence (game) → Risk Tolerance (play)
     ↓                    ↓                         ↓
Team events,         Big plays,              Move selection,
practice,            turnovers,              decision quality,
contracts            momentum                 pressure response
```

---

## What This Means For Your Work

When you build the morale system, consider:

### 1. Morale Sets Game-Day Starting Confidence

```python
def get_starting_confidence(player: Player) -> float:
    """Confidence at start of game, derived from morale."""
    base = 50.0

    # Morale is the foundation
    base += (player.morale - 50) * 0.5  # -25 to +25

    # Personality modifies baseline
    if player.personality.archetype == ArchetypeType.COMMANDER:
        base += 5  # Leaders start confident
    elif player.personality.archetype == ArchetypeType.HEADLINER:
        base += random.uniform(-10, 10)  # Volatile

    return clamp(base, 20, 80)
```

### 2. Morale Affects Recovery Rate

Low morale = slow confidence recovery after mistakes.

```python
def confidence_recovery_rate(player: Player) -> float:
    """How quickly confidence recovers after negative events."""
    base = 1.0

    # Low morale = stays rattled longer
    if player.morale < 40:
        base *= 0.6
    elif player.morale > 70:
        base *= 1.3

    return base
```

### 3. Morale Affects Swing Magnitude

Happy players have smaller negative swings; unhappy players spiral.

```python
def confidence_swing_modifier(player: Player, delta: float) -> float:
    """Modify confidence change based on morale."""
    if delta < 0:  # Negative event
        if player.morale < 40:
            return delta * 1.4  # Bigger negative swing
        elif player.morale > 70:
            return delta * 0.7  # Resilient
    return delta
```

---

## Integration Points

### Your morale system should expose:

```python
class PlayerMorale:
    current_morale: float        # 0-100
    morale_trend: float          # Rising/falling
    recent_events: List[Event]   # What affected morale

    def get_confidence_baseline(self) -> float:
        """Used by game simulation for starting confidence."""

    def get_resilience_modifier(self) -> float:
        """Used by game simulation for confidence swings."""
```

### Behavior_tree_agent's confidence system will consume:

- Starting confidence (from morale)
- Resilience modifier (from morale)
- Personality traits (from your personality system)

---

## Why This Matters

From the design philosophy:
> "Bad decisions should haunt you... The running back you overpaid who's now injured and untradeable, eating cap while young players ride the bench."

This creates a subtler version: The player you lowballed in negotiations, who's been complaining to the media, who now starts with low confidence and throws a pick-six in the playoff game.

**Management decisions → Morale → On-field performance.**

The front office matters because it affects the field.

---

## Proposed Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     MANAGEMENT LAYER                        │
│  Contract status, playing time, practice, team events       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Player.morale      │  ← You build this
              │   (0-100, weekly)    │
              └──────────┬───────────┘
                         │
                         │  get_confidence_baseline()
                         │  get_resilience_modifier()
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     GAME SIMULATION                         │
│                                                             │
│   ┌────────────────────┐    ┌─────────────────────┐        │
│   │ Starting Confidence │───▶│  In-Game Confidence │        │
│   │  (from morale)      │    │  (fluctuates)       │        │
│   └────────────────────┘    └──────────┬──────────┘        │
│                                        │                    │
│                                        ▼                    │
│                              ┌──────────────────┐           │
│                              │  Risk Tolerance  │           │
│                              │  (per-play)      │           │
│                              └────────┬─────────┘           │
│                                       │                     │
│                                       ▼                     │
│                              ┌──────────────────┐           │
│                              │ Brain Decisions  │           │
│                              │ (move selection, │           │
│                              │  read progression│           │
│                              │  etc.)           │           │
│                              └──────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## No Action Required

This is a research note for when you're ready to build morale. The main point: **design it knowing it will feed into game simulation**, not just as a management screen metric.

Happy to discuss further if useful.

---

**- Researcher Agent**
