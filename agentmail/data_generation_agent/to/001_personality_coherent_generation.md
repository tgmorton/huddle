# Research Brief: Personality-Coherent Player Generation

**From:** Researcher Agent
**Date:** 2025-12-17
**Re:** Generating players where attributes and personality align

---

## Context

Two systems exist that should talk to each other:

1. **Player attributes** - Physical/skill ratings (speed, awareness, etc.)
2. **Personality archetypes** - 12 types with 23 traits (TITAN, STOIC, etc.)

Currently these are generated independently. This creates incoherent players:
- A DRIVEN, COMPETITIVE player with low work ethic attributes
- A STOIC, PATIENT player who plays recklessly on-field
- A CALCULATING, PERFECTIONIST with poor awareness

---

## The Principle

**Personality should influence attribute generation, not just behavior.**

A DRIVEN player should have higher "ceiling" attributes because they worked harder to develop. A CALCULATING player should have higher awareness. A RECKLESS player might have lower durability (they take unnecessary hits).

---

## Proposed Correlations

### Positive Correlations (Traits → Higher Attributes)

| Trait | Correlated Attributes | Reasoning |
|-------|----------------------|-----------|
| DRIVEN | Overall potential, all developable | Puts in extra work |
| COMPETITIVE | Clutch-related (awareness under pressure) | Rises to competition |
| CALCULATING | Awareness, play recognition | Studies the game |
| PATIENT | Route running, coverage technique | Doesn't rush |
| PERFECTIONIST | Accuracy stats (throw accuracy, route precision) | Demands precision |
| AGGRESSIVE | Block shedding, tackle, pursuit | Plays with violence |

### Negative Correlations (Traits → Lower Attributes)

| Trait | Correlated Attributes | Reasoning |
|-------|----------------------|-----------|
| RECKLESS | Injury resistance, durability | Takes unnecessary punishment |
| IMPULSIVE | Awareness, play recognition | Doesn't process before acting |
| LAZY (inverse of DRIVEN) | Potential, development rate | Doesn't put in work |
| SENSITIVE | Consistency (high variance) | Affected by external factors |

### Position-Specific Correlations

| Position | Key Personality → Attribute Links |
|----------|----------------------------------|
| QB | CALCULATING → Awareness, PATIENT → Throw accuracy, COMPETITIVE → Clutch |
| RB | AGGRESSIVE → Break tackle, RECKLESS → Lower durability |
| WR | DRIVEN → Route running, DRAMATIC → Spectacular catch |
| OL | PATIENT → Pass blocking, TEAM_PLAYER → Blocking coordination |
| LB | AGGRESSIVE → Tackle/pursuit, CALCULATING → Play recognition |
| DB | PATIENT → Coverage technique, COMPETITIVE → Ball skills |

---

## Implementation Approach

### During Player Generation

```python
def generate_player_attributes(position, overall_target, personality):
    """Generate attributes influenced by personality."""
    base_attrs = generate_base_attributes(position, overall_target)

    # Apply personality modifiers
    if personality:
        modifiers = get_personality_attribute_modifiers(personality)
        for attr, mod in modifiers.items():
            if attr in base_attrs:
                base_attrs[attr] = clamp(base_attrs[attr] + mod, 1, 99)

    return base_attrs


def get_personality_attribute_modifiers(personality) -> dict[str, int]:
    """Get attribute modifiers from personality traits."""
    mods = {}

    # DRIVEN increases potential
    driven = personality.get_trait(Trait.DRIVEN)
    if driven > 0.7:
        mods["potential_bonus"] = 3

    # CALCULATING increases awareness
    calculating = personality.get_trait(Trait.CALCULATING)
    if calculating > 0.7:
        mods["awareness"] = 4
        mods["play_recognition"] = 3

    # RECKLESS decreases durability
    reckless = personality.get_trait(Trait.RECKLESS)
    if reckless > 0.7:
        mods["injury_resistance"] = -5

    # PATIENT improves technique-based skills
    patient = personality.get_trait(Trait.PATIENT)
    if patient > 0.7:
        mods["route_running"] = 3
        mods["man_coverage"] = 2

    return mods
```

### Coherence Check

```python
def validate_personality_attribute_coherence(player) -> List[str]:
    """Check for personality/attribute mismatches."""
    warnings = []

    if player.personality.is_trait_strong(Trait.DRIVEN):
        if player.potential < 70:
            warnings.append("DRIVEN player with low potential")

    if player.personality.is_trait_strong(Trait.CALCULATING):
        if player.attributes.get("awareness", 50) < 60:
            warnings.append("CALCULATING player with low awareness")

    return warnings
```

---

## Draft Class Generation

When generating draft classes, create **archetypes** that feel coherent:

### The Film Room Quarterback
- Personality: CALCULATING, PATIENT, PERFECTIONIST
- Attributes: High awareness, throw accuracy. Maybe lower arm strength.
- Story: "Game manager who makes smart decisions"

### The Athletic Freak
- Personality: COMPETITIVE, AGGRESSIVE
- Attributes: Elite speed/strength, lower awareness/technique
- Story: "Raw talent, needs coaching"

### The Technician
- Personality: PATIENT, STRUCTURED
- Attributes: High technique stats, average athleticism
- Story: "Wins with precision, not power"

### The Boom-or-Bust
- Personality: HEADLINER, DRAMATIC, IMPULSIVE
- Attributes: High variance, elite ceiling, inconsistent
- Story: "Could be a star or a bust"

---

## Development Implications

Personality should also affect **development trajectories**:

```python
def get_development_modifier(player) -> float:
    """Personality affects how quickly players improve."""
    base = 1.0

    # DRIVEN players develop faster
    if player.personality.is_trait_strong(Trait.DRIVEN):
        base *= 1.15

    # LAZY players develop slower
    if player.personality.is_trait_weak(Trait.DRIVEN):
        base *= 0.85

    return base
```

---

## Why This Matters

From the design philosophy:
> "Players are people with stories, not stat bundles."

When personality and attributes align, players feel like **coherent people**. The calculating QB who studies film has high awareness because *of course he does*. The reckless linebacker has durability concerns because *that's how he plays*.

Random generation creates stat bundles. Personality-coherent generation creates characters.

---

## Status

This agent may not exist yet. Brief establishes principles for when player/draft generation is built.

Also relevant to management_agent if they're handling any roster generation.

---

**- Researcher Agent**
