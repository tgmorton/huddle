# Research Brief: Cognitive Narrative Hooks

**From:** Researcher Agent
**Date:** 2025-12-17
**Re:** Generating commentary from cognitive states

---

## Context

The design philosophy emphasizes "Narrative Everywhere":
> "The game should constantly generate small narratives that make your franchise feel alive."

There's no narrative/commentary system yet. When one is built, it should be able to draw on the cognitive states we're building into player behavior.

This document outlines hooks between cognitive systems and narrative generation.

---

## Cognitive States That Generate Narrative

### 1. Pressure-Induced Errors

When a player makes a mistake under pressure, the narrative should reflect the mental aspect:

| Cognitive Event | Narrative Hook |
|----------------|---------------|
| QB throws into coverage under CRITICAL pressure | "Under heavy pressure, [QB] forced it into traffic" |
| DB gets tunnel vision, misses crossing route | "[DB] lost track of [WR] in the chaos" |
| Ballcarrier attempts risky move, fails | "Tried to do too much there" |
| LB bites on play action due to recency bias | "[LB] was cheating toward the run after three straight carries" |

### 2. Confidence/Momentum Swings

Track confidence changes and generate narrative:

```python
def on_confidence_change(player, old_conf, new_conf, event):
    if new_conf < old_conf - 15:
        # Big negative swing
        yield f"{player.name} looks rattled after that {event}"
    elif new_conf > old_conf + 15:
        yield f"{player.name} is feeling it now"
```

### 3. Personality-Driven Moments

Different archetypes should generate different narratives:

| Archetype | Positive Moment | Negative Moment |
|-----------|----------------|-----------------|
| **TITAN** | "Forces his way through" | "Sometimes you can't just power through" |
| **HEADLINER** | "Lives for these moments" | "The spotlight can be cruel" |
| **STOIC** | "Cool as ever" | "Even [player] showing frustration" |
| **COMMANDER** | "Leading by example" | "The leader struggling to right the ship" |

### 4. Expertise vs Inexperience

When System 1/2 processing matters:

```python
def on_play_result(player, play, result, mastery):
    if mastery == MasteryLevel.MASTERED and result.success:
        yield f"Ran that {play.name} in his sleep"
    elif mastery == MasteryLevel.UNLEARNED and result.failure:
        yield f"Still learning that {play.name}"
```

### 5. Scouting Vindication/Regret

When draft picks/signings play out:

```python
def check_player_milestones(player, original_projection):
    actual_ovr = player.overall
    projected_ovr = original_projection.projected_value

    if actual_ovr > projected_ovr + 10:
        yield f"Remember when some scouts had concerns about {player.name}?"
    elif actual_ovr < projected_ovr - 10:
        yield f"{player.name} hasn't lived up to the hype"
```

---

## Commentary Types

### In-Game (Real-Time)

Short, immediate reactions to plays:
- "Under pressure, forces it..."
- "Read that perfectly"
- "Looks lost out there"

### Post-Game (Summary)

Longer narrative about the game story:
- "The turning point came when [QB] threw his second interception. You could see the confidence drain."
- "[RB] was unstoppable in the second half, breaking tackle after tackle."

### Season-Long (Arcs)

Track trends across games:
- "[QB] has been rattled ever since that 4-INT game in Week 3"
- "[WR] is on a tear - 5 straight games with 100+ yards"

### Career (Legacy)

Multi-season narratives:
- "That 6th round pick you took a chance on? He's now a Pro Bowler."
- "The contract that haunted you for three years finally comes off the books."

---

## Data Structures for Narrative

### Narrative Event

```python
@dataclass
class NarrativeEvent:
    event_type: str  # "confidence_drop", "expertise_moment", etc.
    player_id: UUID
    timestamp: datetime
    context: dict  # Cognitive state that triggered this
    severity: float  # 0.0-1.0, how significant
    templates: List[str]  # Possible narrative strings
```

### Narrative Arc

```python
@dataclass
class NarrativeArc:
    arc_type: str  # "redemption", "collapse", "emergence"
    player_id: UUID
    start_event: NarrativeEvent
    current_state: str  # "building", "climax", "resolved"
    events: List[NarrativeEvent]
```

---

## Integration Points

### From Behavior Tree Agent

Expose cognitive state in BrainDecision or via events:

```python
@dataclass
class BrainDecision:
    # ... existing fields ...

    # Narrative hooks
    cognitive_state: Optional[str] = None  # "pressured", "confident", "rattled"
    narrative_hint: Optional[str] = None  # "forced_throw", "tunnel_vision"
```

### From Management Agent

Expose morale/approval for narrative:

```python
def get_narrative_state(player):
    return {
        "morale": player.approval.approval,
        "trend": player.approval.trend,
        "grievances": player.approval.grievances,
        "personality": player.personality.archetype.value,
    }
```

---

## Philosophy

The best sports narratives come from **why**, not just **what**.

- **What**: "QB threw an interception"
- **Why**: "Under heavy pressure, with two defenders in his face, trying to force it to his favorite target who was double-covered"

Cognitive systems give us the **why**. Narrative systems translate it to story.

---

## Status

This agent doesn't exist yet. Creating the folder and this brief to establish the interface between cognitive systems and future narrative generation.

---

**- Researcher Agent**
