# Improvement Areas

Consolidated honest assessment of gaps, issues, and opportunities for improvement in the V2 simulation system.

## Recently Completed

| Item | Description | Date |
|------|-------------|------|
| Block Type Fix | Run plays now use RUN_BLOCK from snap, not just after handoff | Dec 2024 |
| Threshold Alignment | CONTESTED_CATCH_RADIUS aligned with QB's CONTESTED_THRESHOLD (both 1.5 yds) | Dec 2024 |
| Play-Level Blocking Quality | Great/average/poor blocking affects initial leverage | Dec 2024 |
| Quick Beat Mechanic | Calibrated to 2% base for realistic pass rush explosiveness | Dec 2024 |
| Trace System | Per-player debug tracing for brain decisions | Dec 2024 |

## Priority Matrix

| Priority | Area | Effort | Impact |
|----------|------|--------|--------|
| **HIGH** | Pass Game Calibration | Medium | High |
| **HIGH** | QB Scramble Logic | Medium | High |
| **HIGH** | OL Slide Protection | Medium | High |
| **HIGH** | Pattern Matching Coverage | High | High |
| **MEDIUM** | Pre-snap Motion | Medium | Medium |
| **MEDIUM** | Stunt Coordination | Medium | Medium |
| **MEDIUM** | Sigmoid Probability Curves | Low | Medium |
| **LOW** | Event Replay/Debug | Medium | Low |
| **LOW** | Clutch Mechanics | Low | Low |

---

## Architecture Issues

### 1. Brain-Resolution Coupling

**Problem**: Some resolution logic exists in brains instead of resolution systems.

**Examples**:
- Tackle immunity set in ballcarrier brain
- Shed immunity managed in orchestrator
- Some catch resolution inline in receiver brain

**Impact**: Hard to modify resolution without touching brains.

**Fix**: Extract all immunity and resolution logic to resolution systems.

---

### 2. Phase Transition Logic Scattered

**Problem**: Phase transitions happen in multiple places.

**Current locations**:
- `_update_tick()` - main tick updates
- `_on_*` event handlers
- `_resolve_*` methods

**Impact**: Hard to understand or modify phase flow.

**Fix**: Create explicit `PhaseStateMachine` class:
```python
class PhaseStateMachine:
    def check_transition(self, state: GameState) -> Optional[PlayPhase]:
        """Centralized transition logic."""
```

---

### 3. WorldState Overloaded

**Problem**: WorldState has many optional fields for different roles.

**Current state**: ~30+ fields, many only used by specific brains.

**Impact**: Large object passed every tick, hard to understand what's relevant.

**Fix**: Split into base + role contexts:
```python
@dataclass
class WorldState:
    # Common
    me: Player
    ball: Ball
    time: float

@dataclass
class QBContext(WorldState):
    receivers: List[ReceiverEval]
    pressure_level: PressureLevel

@dataclass
class ReceiverContext(WorldState):
    route: RouteDefinition
    coverage: DefenderView
```

---

### 4. Module-Level Brain State

**Problem**: Brain states stored in module-level dicts.

```python
_qb_states: dict[str, QBState] = {}
```

**Impact**: State persists between plays, can cause bugs.

**Fix**:
- Reset state at play start
- Or move state into orchestrator's player tracking

---

### 5. Brain Execution Order

**Problem**: Offense always updates before defense each tick.

**Impact**: Subtle timing advantage for offense.

**Fix**: Interleave or randomize update order.

---

## Missing Game Mechanics

### QB Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Scramble Decision** | No logic for when to leave pocket | HIGH |
| **Designed Runs** | No QB keeper/draw plays | MEDIUM |
| **Post-Snap Reads** | No coverage adjustment after snap | MEDIUM |
| **Pump Fakes** | Flag exists but unused | LOW |

**Current state**: QB either throws or gets sacked. No scramble option.

---

### Receiver Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Option Routes** | Adjust route based on coverage | HIGH |
| **Double Moves** | Route tree lacks stutter-go, etc. | MEDIUM |
| **QB Chemistry** | Timing not affected by rapport | LOW |
| **Scramble Drill** | Basic scramble adjustments | LOW |

---

### Offensive Line Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Slide Protection** | No coordinated slide left/right | HIGH |
| **Stunt Pickup** | Poor handling of DL games | HIGH |
| **Chip Blocks** | TE/RB chip before releasing | MEDIUM |
| **Combo Blocks** | Zone blocking combinations | MEDIUM |

**Current state**: Each OL independently finds target. No coordinated protection.

---

### Defensive Line Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Stunt Coordination** | No TED, EGT games | HIGH |
| **Two-Gap Technique** | Partially implemented | MEDIUM |
| **Contain Responsibility** | Basic edge setting | MEDIUM |

---

### Coverage Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Pattern Matching** | No route pattern recognition | HIGH |
| **Bracket Coverage** | No inside/outside help coordination | HIGH |
| **Zone Handoffs** | Receivers don't pass between zones | MEDIUM |
| **Coverage Disguises** | No pre-snap shell changes | MEDIUM |

**Current state**: Zone defenders patrol static areas. No route combination recognition.

---

### Ballcarrier Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **Patience** | No waiting for blocks | MEDIUM |
| **Pursuit Angle Awareness** | Cuts don't consider angles | MEDIUM |
| **Sideline Awareness** | No boundary recognition | LOW |

---

### Play/Concept Mechanics

| Missing | Description | Priority |
|---------|-------------|----------|
| **RPO** | Run-pass options | HIGH |
| **Play-Action** | Fake handoff mechanics | HIGH |
| **Pre-Snap Motion** | Jet, orbit, shift | MEDIUM |
| **Audibles** | Full audible system | LOW |

---

## Technical Debt

### 1. Magic Numbers

Many tuning constants inline in code.

**Examples**:
```python
ENGAGEMENT_RANGE = 1.5  # Undocumented why 1.5
BASE_TACKLE_PROBABILITY = 0.70  # Arbitrary?
```

**Fix**: Extract to config file with documentation:
```python
# config/tuning.py
BLOCKING_CONFIG = {
    "engagement_range": 1.5,  # Based on NFL average wingspan
    "shed_threshold": 1.0,    # 1 second of winning = shed
}
```

---

### 2. Inconsistent Brain Patterns

Some brains use state machines, others don't.

**Examples**:
- QB brain: Has explicit `QBPhase` enum
- Receiver brain: Uses `RoutePhase`
- DB brain: Has `DBPhase`
- LB brain: No phase tracking

**Fix**: Establish common brain pattern with base class.

---

### 3. Linear Probability Formulas

Resolution uses linear formulas:
```python
probability = 0.7 + (tackling - 75) * 0.005
```

**Problem**:
- 80 vs 90 rated is same difference as 70 vs 80
- Should be exponential at extremes

**Fix**: Use sigmoid curves:
```python
def attribute_probability(attr: int, base: float = 0.5) -> float:
    # Sigmoid centered at 75
    return 1 / (1 + exp(-0.1 * (attr - 75)))
```

---

### 4. Sparse Inline Comments

Many functions lack comments explaining "why".

**Fix**: Add docstrings explaining purpose, not just parameters.

---

### 5. Testing Coverage

Scenario runner exists but few scenarios defined.

**Current state**:
- `testing/scenario_runner.py` exists
- Maybe 5-10 test scenarios

**Fix**: Build comprehensive scenario library:
- Route vs coverage matchups
- Blocking scheme tests
- Edge cases (fumbles, INTs)

---

## Balance Concerns

### Short Passes May Be Too Easy

**Observation**: Slants and drags complete at very high rates.

**Possible issues**:
- Recognition delay too short for DBs
- Separation thresholds too generous
- Throw timing too quick

**Needs**: Playtesting data to validate.

---

### Pressure May Be Too Punishing

**Observation**: Heavy pressure dramatically hurts QB.

**Possible issues**:
- Easterbrook effect too strong
- Pressure levels ramp too fast
- No recovery from pressure spike

**Needs**: Tuning based on feel.

---

### Elite Players Dominate

**Observation**: 95+ rated players rarely fail.

**Possible issues**:
- Variance too low for elite
- Should still have bad plays
- No "any given Sunday" upsets

**Needs**: Consider floor on variance.

---

## Recommended Priorities

### Phase 1: Core Mechanics (High Impact)

1. **Add QB Scramble Logic**
   - Trigger conditions (pressure level, time in pocket)
   - Scramble decision (run vs extend)
   - Receiver scramble drill adjustments

2. **Add OL Slide Protection**
   - Slide direction calls
   - Coordinated slide movement
   - Stunt recognition and handoff

3. **Add Pattern Matching**
   - Route combination recognition
   - Zone defender adjustments
   - Bracket coverage coordination

### Phase 2: Play Expansion (Medium Impact)

4. **Add RPO Framework**
   - Pre-snap read option
   - Run/pass decision point
   - Mesh point timing

5. **Add Play-Action**
   - Fake handoff animation time
   - LOS freeze for defense
   - Boot/rollout protection

6. **Add Pre-Snap Motion**
   - Jet motion
   - Orbit motion
   - Shift mechanics

### Phase 3: Polish (Lower Impact)

7. **Extract Constants to Config**
   - Create tuning.yaml or similar
   - Document each constant

8. **Switch to Sigmoid Curves**
   - Replace linear formulas
   - Better high/low end distribution

9. **Add Event Replay**
   - Step-through debugger
   - Play visualization from events

---

## Tracking Progress

When implementing improvements:

1. Document change in commit message
2. Update relevant doc file's "Honest Assessment"
3. Add test scenario validating fix
4. Update this file to mark complete

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System structure
- [AI_BRAINS.md](AI_BRAINS.md) - Brain-specific gaps
- [RESOLUTION.md](RESOLUTION.md) - Resolution formula issues
