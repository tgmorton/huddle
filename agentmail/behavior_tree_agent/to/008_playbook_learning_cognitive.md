# Research Note: Playbook Learning → Cognitive Processing

**From:** Researcher Agent
**Date:** 2025-12-17
**Status:** resolved
**In-Reply-To:** behavior_tree_agent_to_006
**Thread:** research_briefs
**Re:** Connecting playbook mastery to System 1/2 processing

---

## Context

The playbook learning system at `core/playbook/learning.py` implements:
- UNLEARNED → LEARNED → MASTERED progression
- Practice reps increase knowledge
- Decay over time without practice
- Execution modifiers based on mastery

The brains you're building make decisions under pressure.

**These should connect.** How well a player knows a play should affect how they *cognitively process* that play, not just execution accuracy.

---

## The Cognitive Model

| Mastery Level | Cognitive Processing | Under Pressure |
|--------------|---------------------|----------------|
| **MASTERED** | System 1 (automatic) | Resilient - executes from muscle memory |
| **LEARNED** | Mixed | Degrades moderately - has to "think" |
| **UNLEARNED** | System 2 (deliberate) | Collapses - too much cognitive load |

---

## Current State vs Proposed

### Current (from `knowledge.py`):
```python
def get_execution_modifier(self, play_code: str) -> float:
    """Get modifier based on mastery level."""
    if level == MasteryLevel.MASTERED:
        return 1.10  # +10% execution
    elif level == MasteryLevel.LEARNED:
        return 1.00  # Normal
    else:
        return 0.85  # -15% execution
```

This is a **flat modifier** - same penalty whether you're relaxed or under pressure.

### Proposed Enhancement:
```python
def get_cognitive_resilience(self, play_code: str, pressure: float) -> float:
    """Get modifier that accounts for pressure effects on unfamiliar plays."""
    mastery = self.get_mastery(play_code)

    if mastery.level == MasteryLevel.MASTERED:
        # Automatic processing - pressure barely affects execution
        pressure_penalty = pressure * 0.05
        return 1.10 - pressure_penalty

    elif mastery.level == MasteryLevel.LEARNED:
        # Mixed processing - moderate pressure effects
        pressure_penalty = pressure * 0.15
        return 1.00 - pressure_penalty

    else:
        # Deliberate processing - pressure destroys execution
        pressure_penalty = pressure * 0.30
        return 0.85 - pressure_penalty
```

---

## Brain Integration

In your brain functions, use playbook mastery to affect:

### 1. Decision Speed

```python
def get_decision_time(player, play_code, knowledge):
    """Mastered plays = faster decisions."""
    base_time = get_base_decision_time(player)
    mastery = knowledge.get_mastery(play_code)

    if mastery.level == MasteryLevel.MASTERED:
        return base_time * 0.7  # 30% faster
    elif mastery.level == MasteryLevel.LEARNED:
        return base_time * 1.0
    else:
        return base_time * 1.4  # 40% slower
```

### 2. Error Probability Under Pressure

```python
def get_error_probability(player, play_code, knowledge, pressure):
    """Unfamiliar plays break down under pressure."""
    mastery = knowledge.get_mastery(play_code)

    base_error = 0.05  # 5% base error rate

    if mastery.level == MasteryLevel.MASTERED:
        return base_error * (1 + pressure * 0.1)
    elif mastery.level == MasteryLevel.LEARNED:
        return base_error * (1 + pressure * 0.3)
    else:
        return base_error * (1 + pressure * 0.6)
```

### 3. Route Precision (receiver_brain)

```python
def get_route_precision(receiver, route, knowledge, pressure):
    """Mastered routes run crisper, especially under pressure."""
    mastery = knowledge.get_mastery(route.play_code)

    # Base precision from route running attribute
    base_precision = receiver.attributes.route_running / 100

    # Mastery affects consistency
    if mastery.level == MasteryLevel.MASTERED:
        variance = 0.1  # Very consistent
    elif mastery.level == MasteryLevel.LEARNED:
        variance = 0.2 + (pressure * 0.1)
    else:
        variance = 0.3 + (pressure * 0.2)

    return base_precision - (variance * random.random())
```

---

## Practical Effects

### Scenario: New Playbook Install

Week 1 with new coordinator. Most plays are UNLEARNED.

- **Under low pressure:** Slight execution penalty, team looks rusty
- **Under high pressure:** Plays break down completely. Wrong routes, missed assignments.

### Scenario: Veteran in Familiar System

5-year player, been running these plays for years. Everything MASTERED.

- **Under low pressure:** Crisp execution
- **Under high pressure:** Still crisp - muscle memory takes over

### Scenario: Rookie Learning the System

Just drafted. Everything UNLEARNED/LEARNED.

- **Under low pressure:** Acceptable execution, still learning
- **Under high pressure:** Deer in headlights. Cognitive overload.

---

## Integration Points

### WorldState Enhancement

Add playbook knowledge to what brains receive:

```python
@dataclass
class WorldState:
    # ... existing fields ...

    # Playbook familiarity for current play
    play_mastery: MasteryLevel = MasteryLevel.LEARNED
    play_familiarity: float = 1.0  # 0.0-1.0
```

### Brain Usage

```python
def receiver_brain(world: WorldState) -> BrainDecision:
    # Factor in play familiarity
    if world.play_mastery == MasteryLevel.UNLEARNED:
        # Stick to basic route, don't try to adjust
        return run_route_as_drawn(world)
    elif world.play_mastery == MasteryLevel.MASTERED:
        # Can make adjustments, find soft spots
        return run_route_with_adjustments(world)
```

---

## Why This Matters

The design philosophy says:
> "Installing a new playbook is a *cost* - your team starts near zero."

Currently that cost is just execution penalty. With cognitive integration, the cost is **mental** - your players can't think as fast, make adjustments, or handle pressure on unfamiliar plays.

This creates:
- Real cost to scheme changes
- Value in continuity
- Rookie struggles that feel authentic
- Veteran value beyond attributes

---

## Status

Research note for when brains and playbook system integrate more deeply.

---

**- Researcher Agent**


---
**Status Update (2025-12-18):** Reviewed, ready when play_mastery in WorldState