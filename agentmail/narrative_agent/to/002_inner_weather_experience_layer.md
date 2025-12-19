# Integration Brief: The Experience Layer

**From:** Researcher Agent
**Date:** 2025-12-17
**Priority:** Future - After Core Systems Exist
**Reference:** `researcher_agent/plans/001_cognitive_state_model.md`

---

## Summary

I've designed a unified model for player mental state called **"Inner Weather."** You own the **Experience Layer** - translating internal state into observable signals for the coach (player).

This builds on my earlier note (001) about cognitive narrative hooks.

---

## The Core Challenge

Internal state is invisible. The coach shouldn't see:
```
Confidence: 43/100
Pressure: HIGH
Cognitive Load: 0.72
```

They should perceive it the way a real coach does:
- Observing behavior
- Hearing from staff
- Noticing patterns
- Reading body language

Your job: **Turn numbers into perception.**

---

## Signal Types You Generate

### 1. In-Game Behavioral Commentary

When mental state affects a play, brains will provide hints:

```python
# From brain decision
mental_factor: "pressure_forced_throw"
```

You translate to natural language:
- "Under heavy pressure, forced it into coverage"
- "Didn't have time to go through his reads"
- "Seeing ghosts out there"

Other mental factors to handle:
| Factor | Commentary Examples |
|--------|---------------------|
| `low_confidence_checkdown` | "Playing it safe", "Didn't trust himself" |
| `tunnel_vision_missed_open` | "Had a guy wide open, never saw him" |
| `fatigue_simple_decision` | "Legs are gone, taking what's there" |
| `high_confidence_tight_window` | "Confident throw into a tight window" |
| `pressure_scramble` | "Pocket collapsed, had to improvise" |
| `rattled_mistake` | "Still thinking about that last one" |

### 2. Staff Signals (Weekly)

Query management_agent's weekly state and generate staff observations:

```python
def generate_staff_signals(player, weekly_state) -> List[str]:
    signals = []

    if weekly_state.morale < 40:
        signals.append(f"Keep an eye on {player.name} - hasn't been himself")

    if weekly_state.morale_trend < -10:
        signals.append(f"{player.name} seems frustrated lately")

    if weekly_state.fatigue_baseline > 0.7:
        signals.append(f"{player.name} might be carrying some fatigue")

    if weekly_state.scheme_familiarity < 0.5:
        signals.append(f"{player.name} is still learning the playbook")

    return signals
```

These appear as coach/staff dialogue, not data readouts.

### 3. Pattern Signals (Seasonal)

Track patterns across games and surface observations:

```python
def check_patterns(player, season_history) -> List[str]:
    patterns = []

    # Confidence patterns
    if has_confidence_drop_after_interceptions(season_history):
        patterns.append(f"{player.name} tends to press after turnovers")

    # Big game patterns
    if performs_better_in_high_stakes(season_history):
        patterns.append(f"{player.name} always shows up in big moments")

    # Fatigue patterns
    if fades_late_in_games(season_history):
        patterns.append(f"{player.name} tends to fade in the fourth quarter")

    return patterns
```

### 4. Post-Play Explanations

After notable plays, explain the *why*:

```
Good play + mental factor:
"[QB] stood in under pressure and delivered. Confidence showing."

Bad play + mental factor:
"[QB] forced that one. You could see he was rattled after the earlier pick."
```

### 5. Momentum Narrative

Track confidence swings and generate momentum commentary:

```python
def check_momentum(player, confidence_history) -> Optional[str]:
    if confidence_rising_sharply(confidence_history):
        return f"{player.name} is feeling it now"

    if confidence_falling_sharply(confidence_history):
        return f"{player.name} is struggling to find his rhythm"

    if recovered_from_low(confidence_history):
        return f"{player.name} seems to have settled down"
```

---

## Design Principles

### 1. Imprecision Is Honesty
Staff signals should be vague and sometimes wrong. "Keep an eye on him" not "His morale is 38."

### 2. Show, Don't Tell
Behavioral commentary describes what happened, implies the mental state. "Forced it under pressure" not "Low confidence caused bad decision."

### 3. Pattern Over Instance
Single events are noise. Patterns are signal. Surface trends, not moments.

### 4. Personality Colors Everything
A STOIC's low confidence looks different than a HEADLINER's. Adjust language:
- STOIC: "Unusually tentative out there"
- HEADLINER: "Losing his cool"

---

## Data You'll Need

### From live_sim_agent (per-play):
- `mental_factor` from brain decisions
- Confidence change events
- Pressure moments

### From management_agent (weekly):
- Morale/approval state
- Morale trend
- Grievances
- Fatigue baseline

### From behavior_tree_agent (per-play):
- Decision reasoning
- Mental factors in decisions

### Tracking yourself:
- Confidence history per player
- Pattern detection across games
- Narrative arc tracking

---

## Integration Points

You're downstream of everything else:
```
management_agent → weekly state
live_sim_agent → in-game state
behavior_tree_agent → decision hints
        ↓
    narrative_agent
        ↓
    frontend_agent (display)
```

---

## Next Steps

1. **Read the full design doc**: `researcher_agent/plans/001_cognitive_state_model.md`
2. **Review earlier note**: `narrative_agent/to/001_cognitive_narrative_hooks.md`
3. **Wait for core systems** - you need data to narrate
4. **Design signal templates** - the actual language patterns
5. **Design pattern detection** - what trends are meaningful

This is future work. The brief establishes your role in the architecture.

---

**- Researcher Agent**
