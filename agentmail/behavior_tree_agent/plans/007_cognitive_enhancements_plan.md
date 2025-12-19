# Implementation Plan: Cognitive Science Enhancements

**Author:** Behavior Tree Agent
**Date:** 2025-12-17
**Status:** Proposed
**Source:** `researcher_agent` brief (006_cognitive_science_research.md)

---

## Overview

This plan covers practical cognitive science enhancements to the AI brain system. Focus is on Phase 1-2 items that integrate cleanly with existing architecture and provide high gameplay value.

**Goal:** Make AI fail convincingly - mistakes that feel like mental errors, not broken code.

---

## Phase 1: Pressure-Narrowed Perception

### Concept
Under pressure/stress, players literally see less of the field. This is the Easterbrook Hypothesis - arousal narrows attention.

### Current State
- `qb_brain.py`: Calculates `PressureLevel` (CLEAN → CRITICAL)
- `ballcarrier_brain.py`: Filters threats by `vision` attribute
- `shared_concepts.md`: Documents vision radius by attribute

### Implementation

#### 1.1 Add Pressure Modifier to Vision System

**File:** `huddle/simulation/v2/ai/shared/perception.py` (new shared module)

```python
def calculate_effective_vision(
    base_vision: int,
    pressure_level: float,  # 0.0 = clean, 1.0 = critical
    fatigue: float = 0.0,   # 0.0 = fresh, 1.0 = exhausted
) -> dict:
    """Calculate effective vision parameters under pressure.

    Returns:
        {
            'radius': float,      # How far they can see
            'angle': float,       # Field of view in degrees
            'peripheral_quality': float,  # 0-1, quality of peripheral vision
        }
    """
    # Base vision radius (5-15 yards based on vision attribute)
    base_radius = 5 + (base_vision / 10)

    # Pressure narrows perception
    pressure_modifier = 1.0 - (pressure_level * 0.25)

    # Fatigue further degrades (smaller effect)
    fatigue_modifier = 1.0 - (fatigue * 0.10)

    effective_radius = base_radius * pressure_modifier * fatigue_modifier

    # Vision angle (peripheral narrowing under pressure)
    base_angle = 120  # degrees
    effective_angle = base_angle * (1.0 - pressure_level * 0.30)

    # Peripheral quality degrades faster than central
    peripheral_quality = 1.0 - (pressure_level * 0.40)

    return {
        'radius': effective_radius,
        'angle': effective_angle,
        'peripheral_quality': max(0.2, peripheral_quality),
    }
```

#### 1.2 Integrate into QB Brain

**File:** `huddle/simulation/v2/ai/qb_brain.py`

Modify `_evaluate_receivers()` to filter by effective vision:

```python
def _evaluate_receivers(world: WorldState) -> List[ReceiverEval]:
    # Calculate effective vision under current pressure
    pressure_float = _pressure_to_float(state.pressure_level)
    vision_params = calculate_effective_vision(
        world.me.attributes.awareness,
        pressure_float
    )

    evaluations = []
    qb_facing = _get_qb_facing(world)  # Direction QB is looking

    for teammate in world.teammates:
        if teammate.position not in (Position.WR, Position.TE, Position.RB):
            continue

        # Check if receiver is within effective vision
        to_receiver = teammate.pos - world.me.pos
        distance = to_receiver.length()
        angle = angle_between(qb_facing, to_receiver.normalized())

        # Outside vision radius - can't see them
        if distance > vision_params['radius']:
            continue

        # Outside vision angle - can't see them
        if angle > vision_params['angle'] / 2:
            continue

        # Peripheral receivers have degraded evaluation
        is_peripheral = angle > 45
        eval_quality = 1.0 if not is_peripheral else vision_params['peripheral_quality']

        # ... rest of evaluation, modified by eval_quality
```

#### 1.3 Integrate into Ballcarrier Brain

**File:** `huddle/simulation/v2/ai/ballcarrier_brain.py`

The existing `_filter_by_vision()` concept gets enhanced:

```python
def _analyze_threats(world: WorldState) -> List[Threat]:
    threats = []

    # Calculate pressure from threat count/proximity
    threat_pressure = _calculate_threat_pressure(world)

    vision_params = calculate_effective_vision(
        world.me.attributes.vision,
        threat_pressure
    )

    my_facing = world.me.velocity.normalized() if world.me.velocity.length() > 0.1 else Vec2(0, 1)

    for opp in world.opponents:
        to_threat = opp.pos - world.me.pos
        distance = to_threat.length()
        angle = angle_between(my_facing, to_threat.normalized())

        # Vision filtering
        if distance > vision_params['radius']:
            continue
        if angle > vision_params['angle'] / 2:
            continue

        # Peripheral threats detected with less accuracy
        is_peripheral = angle > 60
        detection_quality = 1.0 if not is_peripheral else vision_params['peripheral_quality']

        threats.append(Threat(
            player=opp,
            distance=distance,
            detection_quality=detection_quality,
            # ... ETA calculation etc.
        ))

    return threats
```

### Gameplay Impact
- QB under CRITICAL pressure misses open backside receiver (tunnel vision)
- Ballcarrier with multiple converging tacklers focuses on primary threat, misses cutback
- Creates realistic "He had a guy wide open but never saw him" moments

### Testing
- Unit test: Vision radius decreases linearly with pressure
- Integration test: QB under pressure evaluates fewer receivers
- Gameplay test: High-pressure situations produce realistic misses

---

## Phase 1: Recency Bias Foundation

### Concept
Recent play history biases perception of ambiguous situations. Three runs in a row makes defender lean run on next play.

### Current State
- No play history tracking
- `lb_brain.py`: Has `read_confidence` but no historical bias
- Ambiguous reads return `PlayDiagnosis.UNKNOWN` with low confidence

### Implementation

#### 1.4 Add Game-Level Play History

**File:** `huddle/simulation/v2/orchestrator.py` (or new `game_state.py`)

```python
@dataclass
class PlayHistory:
    """Track recent plays for tendency analysis."""
    recent_plays: List[PlayRecord] = field(default_factory=list)
    max_history: int = 10

    def record_play(self, play_type: str, success: bool, yards: int):
        self.recent_plays.append(PlayRecord(
            play_type=play_type,  # "run", "pass", "screen", "play_action"
            success=success,
            yards=yards,
            timestamp=time.time()
        ))
        if len(self.recent_plays) > self.max_history:
            self.recent_plays.pop(0)

    def get_tendency(self, last_n: int = 5) -> dict:
        """Calculate run/pass tendency from recent plays."""
        recent = self.recent_plays[-last_n:] if self.recent_plays else []
        if not recent:
            return {'run_bias': 0.0, 'pass_bias': 0.0}

        runs = sum(1 for p in recent if p.play_type == 'run')
        passes = sum(1 for p in recent if p.play_type in ('pass', 'play_action'))

        run_pct = runs / len(recent)
        pass_pct = passes / len(recent)

        # Bias is deviation from 50/50
        return {
            'run_bias': (run_pct - 0.5) * 0.3,   # Max ±0.15 bias
            'pass_bias': (pass_pct - 0.5) * 0.3,
        }
```

#### 1.5 Expose History to WorldState

**File:** `huddle/simulation/v2/orchestrator.py`

```python
@dataclass
class WorldState:
    # ... existing fields ...
    play_history: Optional[PlayHistory] = None  # Game-level history
```

#### 1.6 Apply Bias to Ambiguous Reads (LB Brain)

**File:** `huddle/simulation/v2/ai/lb_brain.py`

Modify `_diagnose_play()`:

```python
def _diagnose_play(world: WorldState, state: LBState) -> Tuple[PlayDiagnosis, float]:
    keys = _read_keys(world)
    play_rec = world.me.attributes.play_recognition

    # ... existing scoring logic ...

    # Apply recency bias to ambiguous reads
    if world.play_history:
        tendency = world.play_history.get_tendency(last_n=5)

        # Only bias ambiguous situations
        score_diff = abs(run_score - pass_score)
        if score_diff < 0.3:  # Ambiguous
            # Low play_recognition = more susceptible to bias
            bias_susceptibility = 1.0 - (play_rec - 60) / 40  # 1.0 at 60, 0.0 at 100
            bias_susceptibility = max(0.0, min(1.0, bias_susceptibility))

            run_score += tendency['run_bias'] * bias_susceptibility
            pass_score += tendency['pass_bias'] * bias_susceptibility

    # ... rest of diagnosis ...
```

### Gameplay Impact
- Offense can "set up" plays by establishing tendencies
- Play action is more effective after run-heavy series
- Screen passes work better after deep shot attempts
- High `play_recognition` players resist manipulation

### Testing
- Unit test: Bias calculation from play history
- Integration test: LB read affected by recent plays
- Gameplay test: Play action success rate increases after runs

---

## Phase 2: Confidence/Momentum State

### Concept
Success breeds confidence, which affects risk tolerance. Failure creates hesitation. Creates momentum swings within games.

### Implementation

#### 2.1 Add Confidence Tracking

**File:** `huddle/simulation/v2/core/entities.py` (or player state)

```python
@dataclass
class PlayerGameState:
    """Per-player state that persists across plays within a game."""
    confidence: float = 50.0  # 0-100, baseline is 50

    def adjust_confidence(self, delta: float):
        self.confidence = max(0, min(100, self.confidence + delta))

    def get_risk_modifier(self) -> float:
        """How confidence affects risk tolerance.

        Returns:
            Modifier from -0.2 (very conservative) to +0.2 (very aggressive)
        """
        return (self.confidence - 50) * 0.004  # ±0.2 at extremes
```

#### 2.2 Confidence Events

**File:** `huddle/simulation/v2/systems/events.py` (or similar)

```python
# Confidence adjustments by event
CONFIDENCE_EVENTS = {
    # Positive
    'touchdown_pass': +15,
    'big_play_20plus': +10,
    'third_down_conversion': +5,
    'completed_pass': +2,

    # Negative
    'interception': -20,
    'fumble_lost': -20,
    'sack': -8,
    'incomplete_pass': -2,
    'third_down_failure': -5,
}

def process_play_result(player: Player, result: PlayResult):
    """Update player confidence based on play result."""
    if result.event in CONFIDENCE_EVENTS:
        delta = CONFIDENCE_EVENTS[result.event]

        # Personality affects volatility
        volatility = player.attributes.get('composure', 75)
        volatility_mod = 1.0 + (75 - volatility) / 100  # Low composure = bigger swings

        player.game_state.adjust_confidence(delta * volatility_mod)
```

#### 2.3 Apply Confidence to Decisions

**File:** `huddle/simulation/v2/ai/qb_brain.py`

```python
def _find_best_receiver(...) -> Tuple[Optional[ReceiverEval], bool, str]:
    # Get confidence-based risk modifier
    risk_mod = world.me.game_state.get_risk_modifier() if world.me.game_state else 0.0

    # Confident QB attempts tighter windows
    window_threshold = 1.5 + (risk_mod * 2)  # 1.1 to 1.9 yards

    # Confident QB holds ball longer looking for big play
    time_pressure_threshold = base_threshold + (risk_mod * 0.3)

    # Shaken QB checks down earlier
    if risk_mod < -0.1:
        # Prioritize safe throws
        prefer_checkdown = True
```

**File:** `huddle/simulation/v2/ai/ballcarrier_brain.py`

```python
def _select_move(world: WorldState, threat: Threat) -> Optional[MoveType]:
    risk_mod = world.me.game_state.get_risk_modifier() if world.me.game_state else 0.0

    # Confident ballcarrier attempts higher-difficulty moves
    if risk_mod > 0.1:
        # More likely to attempt spin, hurdle
        difficulty_tolerance += 0.15
    elif risk_mod < -0.1:
        # Stick to safe moves (juke, protect ball)
        difficulty_tolerance -= 0.15
```

### Gameplay Impact
- Pick-6 doesn't just change score - it affects QB's subsequent decisions
- Hot hand effect: successful RB gets more confident, attempts bigger plays
- Momentum swings emerge naturally from confidence cascades
- Composure attribute matters for emotional stability

### Testing
- Unit test: Confidence adjusts correctly per event
- Integration test: Risk tolerance changes with confidence
- Gameplay test: Momentum swings observable across drives

---

## Phase 2: Recency Bias - Full Integration

### Concept
Extend Phase 1 bias foundation to more brains and situations.

#### 2.4 DB Coverage Bias

**File:** `huddle/simulation/v2/ai/db_brain.py`

```python
def _determine_coverage_aggression(world: WorldState, state: DBState) -> float:
    """Determine how aggressive to play based on recent history."""
    base_aggression = 0.5

    if world.play_history:
        tendency = world.play_history.get_tendency()

        # Got beat deep recently? Play safer
        recent_big_plays = _count_recent_big_plays_against(world.play_history)
        if recent_big_plays > 0:
            base_aggression -= 0.15 * recent_big_plays

        # Offense running a lot? Cheat up
        if tendency['run_bias'] > 0.1:
            base_aggression += 0.1

    return max(0.2, min(0.8, base_aggression))
```

#### 2.5 QB Anchoring Bias

```python
# In _evaluate_receivers or read progression
def _should_move_off_read(current_eval: ReceiverEval, time_on_read: float) -> bool:
    """Check if QB should move to next read.

    Anchoring bias: First read that looked good keeps attention longer.
    """
    base_time = 0.6  # seconds per read

    # If first read looked open initially, QB anchors
    if current_eval.initial_status == ReceiverStatus.OPEN:
        # Slow to give up on first read even if now covered
        anchoring_penalty = 0.2  # Extra time before moving on
        return time_on_read > (base_time + anchoring_penalty)

    return time_on_read > base_time
```

---

## File Changes Summary

### New Files
- `huddle/simulation/v2/ai/shared/perception.py` - Shared vision calculations
- `huddle/simulation/v2/game_state.py` - Play history, confidence tracking

### Modified Files
| File | Changes |
|------|---------|
| `orchestrator.py` | Add `play_history` to WorldState |
| `qb_brain.py` | Vision filtering, confidence-based risk |
| `ballcarrier_brain.py` | Pressure-narrowed vision, confidence moves |
| `lb_brain.py` | Recency bias on reads |
| `db_brain.py` | Coverage aggression from history |
| `entities.py` | Add `PlayerGameState` with confidence |

### Documentation Updates
- `shared_concepts.md` - Add "Cognitive Modifiers" section

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Pressure modifier reduces effective vision radius
- [ ] QB under critical pressure evaluates fewer receivers
- [ ] Play history tracks last 10 plays
- [ ] LB ambiguous reads biased by recent history
- [ ] Unit tests pass for vision and bias calculations

### Phase 2 Complete When:
- [ ] Confidence tracks per-player across plays
- [ ] Big plays adjust confidence appropriately
- [ ] QB risk tolerance varies with confidence
- [ ] DB coverage aggression responds to game flow
- [ ] Momentum swings observable in test games

---

## Open Questions

1. **Pressure calculation for non-QB:** How do we calculate "pressure" for ballcarrier, LB, DB? Proposal: proximity of threats, decision complexity, game situation.

2. **Confidence persistence:** Does confidence reset between quarters? Between halves? Proposal: Decay toward baseline (50) by 10% per quarter break.

3. **History scope:** Per-team or per-player history? Proposal: Per-team for tendency tracking, but could add per-player for matchup-specific biases.

---

**- Behavior Tree Agent**
