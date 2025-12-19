# The Inner Weather: A Unified Model of Player Mental State

**Author:** Researcher Agent
**Date:** 2025-12-17
**Status:** Design Proposal
**Domain:** Cross-cutting (Management, Simulation, Narrative, UX)

---

## Executive Summary

This document proposes a unified conceptual model for player mental state in Huddle - what we call **"inner weather."** Rather than treating morale, confidence, personality, and fatigue as separate systems, we define them as layers of a single mental life that flows through the game at different time scales.

The model answers three questions:
1. **Ontology**: What mental states exist?
2. **Dynamics**: How do they influence each other?
3. **Experience**: How does the coach perceive them?

---

## Part 1: The Ontology

### The Three Layers

Player mental state operates at three time scales, each setting constraints on the next:

```
┌─────────────────────────────────────────────────────────────────┐
│                     STABLE LAYER                                │
│            (Doesn't change during a game or season)             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Personality │  │ Experience  │  │ Cognitive Capacity      │ │
│  │ (archetype, │  │ (years,     │  │ (learning attr,         │ │
│  │  traits)    │  │  games)     │  │  awareness)             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  Sets: Range of reactions, baseline tendencies, ceiling        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WEEKLY LAYER                                │
│              (Changes between games, resets seasonally)         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Morale    │  │ Preparation │  │ Physical Baseline       │ │
│  │ (approval,  │  │ (game prep, │  │ (injury status,         │ │
│  │  grievances)│  │  familiarity│  │  fatigue debt)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  Sets: Starting point for game, constraints on performance     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    IN-GAME LAYER                                │
│                (Fluctuates play-to-play)                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Confidence  │  │  Pressure   │  │ Cognitive Load          │ │
│  │ (current    │  │ (external   │  │ (how much tracking,     │ │
│  │  self-belief│  │  threat)    │  │  complexity of moment)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   Focus     │  │ In-Game     │                              │
│  │ (attention  │  │ Fatigue     │                              │
│  │  width)     │  │             │                              │
│  └─────────────┘  └─────────────┘                              │
│                                                                 │
│  Determines: Actual performance on each play                   │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Interactions

**Stable → Weekly**: Personality determines how events affect morale. A STOIC has smaller morale swings. A DRAMATIC has larger ones. Experience provides resilience.

**Weekly → In-Game**: Morale sets starting confidence. Preparation sets familiarity bonuses. Physical baseline sets fatigue ceiling.

**In-Game ↔ In-Game**: Pressure narrows focus. High cognitive load depletes faster. Confidence affects risk tolerance, which affects decisions, which affect outcomes, which affect confidence.

---

## Part 2: The Components

### STABLE LAYER

#### Personality
Already implemented via archetypes. Key traits for mental model:

| Trait | Mental Effect |
|-------|---------------|
| LEVEL_HEADED | Smaller confidence swings |
| DRAMATIC | Larger confidence swings |
| COMPETITIVE | Confidence rises under pressure |
| SENSITIVE | Morale affected more by events |
| PATIENT | Wider attention under load |
| IMPULSIVE | Faster decisions, narrower attention |
| DRIVEN | Higher morale baseline |
| RECKLESS | Higher risk tolerance floor |
| CONSERVATIVE | Lower risk tolerance ceiling |

#### Experience
Years in league, games played, playoff games. Creates:
- **Familiarity baseline**: Veterans have "seen it all"
- **Pressure resistance**: Big moments feel smaller
- **Recovery speed**: Bounce back from bad plays faster

#### Cognitive Capacity
Derived from attributes (awareness, play recognition, learning). Sets:
- **Processing ceiling**: How much can they track?
- **Recognition speed**: How fast do they read situations?
- **Adaptation rate**: How quickly do they adjust?

---

### WEEKLY LAYER

#### Morale
Current implementation: Approval (0-100) affected by events. Extend to include:
- **Baseline**: Where approval naturally drifts toward
- **Volatility**: How much events move it (personality-driven)
- **Grievances**: Specific complaints that fester

#### Preparation
- **Opponent familiarity**: Game prep bonuses
- **Scheme familiarity**: Playbook mastery for this week's plays
- **Role clarity**: Does the player know their job?

#### Physical Baseline
- **Injury status**: Limitations and pain
- **Fatigue debt**: Accumulated wear from recent games
- **Rest quality**: Bye weeks, short weeks

---

### IN-GAME LAYER

#### Confidence
The central hub of in-game mental state.

**Starting point**: Derived from morale, modified by situation
```
starting_confidence =
    morale_baseline
    + personality_modifier
    + matchup_modifier
    + recent_form_modifier
```

**Fluctuation**: Events move confidence within personality-defined bounds
```
on_event(player, event):
    raw_delta = event.confidence_impact
    personality_delta = raw_delta * player.personality.volatility
    bounded_delta = clamp(personality_delta, player.swing_floor, player.swing_ceiling)
    player.confidence += bounded_delta
```

**Effects**: Confidence → Risk Tolerance → Decision Quality
- High confidence: Attempt difficult throws, aggressive moves
- Low confidence: Conservative choices, check downs, protect ball

#### Pressure
External threat level. Computed from situation:
- Defensive pressure (rushers, coverage)
- Game situation (score, time, down/distance)
- Stakes (playoff game, rivalry, job security)

**Effects**: Pressure → Focus Width → Perception
- High pressure: Attention narrows (tunnel vision)
- Low pressure: Full field awareness

#### Cognitive Load
How much the player is tracking right now:
- Number of relevant threats/options
- Complexity of the current play
- Unfamiliarity (new scheme, unusual situation)

**Effects**: Load → Processing Speed → Decision Quality
- High load + low capacity = slow, poor decisions
- High load + high capacity = manageable
- Mastered situations reduce load (chunking)

#### Focus
Width of attention. Affected by pressure and load:
```
focus_width = base_attention * (1 - pressure * 0.3) * (1 - load_penalty)
```

**Effects**: Focus → Perception → What options are "seen"
- Wide focus: See whole field, all options
- Narrow focus: See primary read, miss backside

#### In-Game Fatigue
Physical and mental depletion during the game:
- Snaps played
- High-intensity plays
- Mental exertion (complex decisions)

**Effects**: Fatigue → All Systems
- Processing slows
- Confidence recovery slows
- Errors increase
- Defaults to simple/familiar actions

---

## Part 3: The Dynamics

### Flow Model

```
STABLE constrains WEEKLY constrains IN-GAME

Events flow upward:
  - In-game events (big play) → Confidence change
  - Significant in-game events → Morale change (post-game)
  - Patterns of events → Personality expression (narrative)

Time flows downward:
  - Season sets personality (stable)
  - Week sets morale, preparation (weekly)
  - Play sets confidence, pressure, load (in-game)
```

### Key Dynamics

#### 1. The Confidence Spiral
Bad play → Confidence drops → Risk aversion increases → Conservative play → Maybe worse outcome → Confidence drops more

OR

Bad play → Confidence drops → Overcompensation (hero ball) → Risky play → Maybe worse outcome → Confidence drops more

Personality determines which spiral: CONSERVATIVE types go safe, AGGRESSIVE types go hero.

#### 2. The Pressure Funnel
High pressure → Narrowed attention → Miss open receiver → Incomplete/INT → Confidence drops → Next pressure moment feels worse

Experience and personality resist the funnel. Veterans keep attention wider under pressure.

#### 3. The Fatigue Cliff
Gradual fatigue → Gradual degradation → Sudden cliff when capacity exceeded

Fresh player handles complex moment fine. Same player at 95% fatigue makes critical error on same situation.

#### 4. The Familiarity Buffer
Mastered play under pressure → Automatic execution → Load stays low → Attention stays wide → Good decision

Unlearned play under pressure → Deliberate execution → Load spikes → Attention narrows → Poor decision

Experience with a scheme creates cognitive buffer against pressure.

---

## Part 4: The Experience

### Design Principle: Signals, Not Numbers

From the design philosophy:
> "You're not reading spreadsheets; you're forming judgments with incomplete data"

The coach should perceive player mental state the way a real coach does:
- Observing behavior
- Reading body language
- Hearing from staff
- Noticing patterns

NOT: "Confidence: 43/100"

### Signal Types

#### Behavioral Signals (In-Game)
What you see on the field:

| Internal State | Observable Signal |
|----------------|-------------------|
| Low confidence | Checking down early, hesitation |
| High confidence | Holding ball longer, tight window throws |
| Narrow focus | Missing open backside receiver |
| High pressure | Rushed throws, happy feet |
| Fatigue | Slower reactions, defaulting to simple |

These aren't labeled - they emerge from the simulation. The coach learns to read them.

#### Staff Signals (Weekly)
What your coaches tell you:

- "Keep an eye on [QB] - he's been pressing in practice"
- "[WR] seems frustrated, hasn't been targeted much lately"
- "[LB] is locked in this week, really studying the film"
- "[RB] might be carrying some fatigue from last week"

Imprecise. Interpretive. Sometimes wrong.

#### Pattern Signals (Seasonal)
What you notice over time:

- "[QB] has been off since that 4-INT game"
- "[WR] always shows up in big moments"
- "[RB] tends to fade in December"
- "[CB] gets better as the game goes on"

The game tracks patterns and surfaces them as observations, not data.

#### Body Language (Visual)
What you see on the sideline:

- Player alone on bench vs engaged with teammates
- Head down vs looking at tablet
- Animated after play vs subdued
- Eye contact with coaches vs avoiding

This is UX/art direction, but the mental model drives it.

### What The Coach Can Do

Mental state isn't just observed - it can be influenced:

| Action | Effect |
|--------|--------|
| Timeout after bad play | Confidence recovery time |
| Call player's number | Show trust → Confidence boost (or pressure) |
| Simple play call | Reduce cognitive load |
| Familiar play | Reduce load via mastery |
| Sub in fresh player | Reset fatigue |
| Halftime talk | Morale adjustment window |
| Public praise (press) | Morale boost (personality-dependent) |
| Rest day in practice | Physical baseline recovery |

The coach manages mental state *indirectly* through decisions, not through a "boost confidence" button.

---

## Part 5: Integration Map

### System Ownership

| Layer | Component | Owner | Notes |
|-------|-----------|-------|-------|
| Stable | Personality | management_agent | Exists, well-designed |
| Stable | Experience | management_agent | Exists in player model |
| Stable | Cognitive Capacity | management_agent | Derived from attributes |
| Weekly | Morale | management_agent | Exists as approval |
| Weekly | Preparation | management_agent | Game prep exists |
| Weekly | Physical Baseline | management_agent | Injury system needed |
| In-Game | Confidence | live_sim_agent | New, core addition |
| In-Game | Pressure | live_sim_agent | Partially exists in brains |
| In-Game | Cognitive Load | behavior_tree_agent | New concept |
| In-Game | Focus | behavior_tree_agent | Partially exists (vision) |
| In-Game | Fatigue | live_sim_agent | Physical exists, mental new |
| Experience | Signals | narrative_agent | Future, surfaces state |
| Experience | Visuals | frontend_agent | Future, body language |

### Data Flow

```
management_agent (stable + weekly)
        │
        │ Pre-game: Package player mental state
        ▼
live_sim_agent (orchestrator)
        │
        │ Per-tick: Update in-game layer
        │ Pass to brains via WorldState
        ▼
behavior_tree_agent (brains)
        │
        │ Consume state for decisions
        │ Return cognitive hints for narrative
        ▼
narrative_agent (experience)
        │
        │ Generate signals, commentary
        ▼
frontend_agent (presentation)
        │
        │ Display body language, sideline
        ▼
Player (coach)
```

---

## Part 6: Design Principles

### 1. Layers Constrain, Don't Determine
Stable layer sets the range. Weekly layer sets the start. In-game layer moves within those bounds. A STOIC doesn't become a HEADLINER under pressure - they stay STOIC, just more or less confident.

### 2. Perception Over Prescription
Don't tell the coach "confidence is low." Show them behavior that implies it. Let them form the judgment.

### 3. Indirect Control
The coach influences mental state through decisions (play calls, personnel, timeouts) not through direct manipulation. This creates gameplay.

### 4. Personality Is Destiny (Within Bounds)
A HEADLINER will always be volatile. You can't coach it out of them. You can manage it, work around it, or lean into it. This creates roster construction strategy.

### 5. Failure Is Interesting
The goal isn't perfect mental state management. It's *interesting* mental state dynamics. The QB who gets rattled in the playoff game is compelling. The steady veteran who holds it together is compelling differently.

### 6. Coherence Over Complexity
Fewer states, well-connected, is better than many states, isolated. The model should feel like one thing (inner weather) not seven separate systems.

---

## Part 7: Open Questions

### For Discussion

1. **Visibility granularity**: How much should the coach be able to infer? Too opaque = frustrating. Too transparent = spreadsheet.

2. **Control granularity**: What levers does the coach have? Timeout, play call, personnel - what else?

3. **Team dynamics**: Does team confidence exist? How does one player's state affect others?

4. **Opponent perception**: Do players have mental models of opponents that affect their state?

5. **Learning**: Do players' stable traits evolve over career based on experiences?

### For Future Development

- Detailed confidence event catalog (what moves it, by how much)
- Pressure calculation formula
- Cognitive load operationalization
- Signal generation rules
- Body language art direction

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| Inner Weather | The totality of a player's mental state |
| Stable Layer | Mental attributes that don't change in-game |
| Weekly Layer | Mental state set between games |
| In-Game Layer | Mental state that fluctuates during play |
| Confidence | Current self-belief, central hub of in-game state |
| Pressure | External threat level from situation |
| Cognitive Load | How much the player is mentally tracking |
| Focus Width | Breadth of attention (wide = sees everything, narrow = tunnel) |
| Signal | Observable indication of internal state |
| Volatility | How much a player's state swings (personality-driven) |

---

## Appendix: References

- `docs/DESIGN_PHILOSOPHY.md` - Core design principles
- `docs/ai_brains/` - Current brain architecture
- `core/personality/` - Personality system
- `core/approval.py` - Current morale system
- `core/playbook/learning.py` - Familiarity/mastery system
- `core/game_prep.py` - Preparation system

---

**End of Document**
