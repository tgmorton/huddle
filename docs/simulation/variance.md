# Variance System

Attribute-modulated randomness that creates realistic unpredictability. Higher skill = more consistent performance.

## Design Philosophy

```
Physics stays deterministic (positions, collisions, trajectories)
Human factors add variance (recognition, execution, decisions)
All variance is attribute-modulated (skill reduces variance)
```

Three noise layers:
1. **Recognition** - How quickly/accurately players perceive situations
2. **Execution** - Motor variance in physical actions
3. **Decision** - Cognitive errors under pressure

## Configuration

```python
@dataclass
class VarianceConfig:
    mode: SimulationMode = REALISTIC
    seed: Optional[int] = None  # For reproducibility

    # Layer multipliers (0=disabled, 1=normal, 2=exaggerated)
    recognition_multiplier: float = 1.0
    execution_multiplier: float = 1.0
    decision_multiplier: float = 1.0

    # Inner Weather effects
    pressure_affects_variance: bool = True
    fatigue_affects_variance: bool = True
```

### Simulation Modes

| Mode | Effect |
|------|--------|
| DETERMINISTIC | No variance - for film study, debugging |
| REALISTIC | Full variance - for gameplay |

```python
from huddle.simulation.v2.core.variance import set_config, VarianceConfig

# Reproducible simulation
set_config(VarianceConfig(seed=42))

# Deterministic for testing
set_config(VarianceConfig(mode=SimulationMode.DETERMINISTIC))
```

---

## Layer 1: Recognition Noise

Affects how quickly and accurately players perceive situations.

### Recognition Delay

```python
def recognition_delay(
    base_delay: float,    # Base reaction time (e.g., 0.2s)
    awareness: int,       # Player awareness (0-99)
    pressure: float = 0,  # Pressure level (0-1)
    fatigue: float = 0,   # Fatigue level (0-1)
) -> float:
```

Example:
```python
# Base 200ms reaction time
actual = recognition_delay(0.2, awareness=85, pressure=0.3)
# Returns ~0.18-0.22 seconds (tighter variance for high awareness)

actual = recognition_delay(0.2, awareness=65, pressure=0.5)
# Returns ~0.17-0.28 seconds (wider variance, pressure widens more)
```

### Recognition Accuracy

```python
def recognition_accuracy(awareness: int, pressure: float = 0) -> float:
    """Returns 0.7-1.0 accuracy factor."""
```

Used for: Coverage recognition, route anticipation, blitz pickup.

---

## Layer 2: Execution Noise

Affects timing and precision of physical actions.

### Execution Timing

```python
def execution_timing(
    base_time: float,     # Base time for action
    skill_attribute: int, # Relevant skill (route_running, etc.)
    fatigue: float = 0,
) -> float:
```

Example: Route break timing
```python
# Perfect break at 3.0 seconds
actual = execution_timing(3.0, route_running=92)
# Returns ~2.95-3.05 seconds (elite = consistent)

actual = execution_timing(3.0, route_running=72)
# Returns ~2.85-3.15 seconds (average = more variance)
```

### Execution Precision

```python
def execution_precision(
    base_value: float,    # Base value (yards, degrees)
    skill_attribute: int,
    fatigue: float = 0,
) -> float:
```

Used for: Cut angles, pursuit angles, blocking positions.

### Route Break Sharpness

```python
def route_break_sharpness(
    base_sharpness: float,  # Ideal sharpness (0-1)
    route_running: int,
    fatigue: float = 0,
) -> float:
```

Higher route running → higher mean AND tighter variance.

### Pursuit Angle Accuracy

```python
def pursuit_angle_accuracy(
    awareness: int,
    tackle: int,
    fatigue: float = 0,
) -> float:
    """Returns 0.6-1.0 accuracy factor for pursuit angles."""
```

---

## Layer 3: Decision Noise

Affects choice quality under pressure.

### Suboptimal Decisions

```python
def should_make_suboptimal_decision(
    awareness: int,
    pressure: float = 0,
    cognitive_load: float = 0,  # Situational complexity
) -> bool:
    """Returns True if player should make a mistake."""
```

Error rate scales with:
- Low awareness (inverse)
- High pressure (increases)
- High cognitive load (increases)

Capped at 40% error chance.

### Decision Hesitation

```python
def decision_hesitation(
    base_time: float,    # Base decision time
    awareness: int,
    confidence: float = 1.0,  # 0-1 confidence level
) -> float:
```

Low confidence adds hesitation time.

### Target Selection Noise

```python
def target_selection_noise(
    rankings: list[tuple[str, float]],  # [(target_id, score)]
    awareness: int,
    pressure: float = 0,
) -> list[tuple[str, float]]:
    """Adds noise to rankings, potentially reordering."""
```

Can cause QB to pick suboptimal receiver under pressure.

---

## Attribute Conversion

```python
def attribute_to_factor(attribute: int, base: int = 75) -> float:
    """
    Convert 0-100 attribute to variance factor around 1.0.

    50 attribute → 1.5x variance
    75 attribute → 1.0x variance (average NFL)
    100 attribute → 0.5x variance
    """
```

Higher skill = lower variance factor = more consistent.

---

## Easterbrook Hypothesis

Pressure narrows attentional focus (tunnel vision).

Implemented in QB brain:

```python
effective_fov = calculate_effective_vision(
    awareness=world.me.attributes.awareness,
    pressure=pressure_level,
)
# Clean pocket: 120° field of view
# Heavy pressure: 75° field of view
```

Under pressure, QB may miss open receivers in periphery.

---

## Usage Examples

### Deterministic Testing

```python
# Film study - no variance
set_config(VarianceConfig(mode=SimulationMode.DETERMINISTIC))

# Reproducible - same seed = same results
set_config(VarianceConfig(seed=12345))
```

### Checking Mode

```python
from huddle.simulation.v2.core.variance import is_deterministic

if is_deterministic():
    return base_value  # Skip variance
```

### Per-System Multipliers

```python
# Exaggerate decision noise for testing
set_config(VarianceConfig(
    recognition_multiplier=1.0,
    execution_multiplier=1.0,
    decision_multiplier=2.0,  # 2x decision errors
))
```

---

## Honest Assessment

### What Works

1. **Three-Layer Approach**: Clean separation of variance types
2. **Attribute Modulation**: Skill differences matter
3. **Pressure Effects**: Easterbrook hypothesis creates realism
4. **Deterministic Mode**: Essential for debugging

### Issues

1. **May Be Too Deterministic**
   - Elite players (95+) rarely make mistakes
   - Could use more upsets/variance at high end

2. **Pressure Effects May Be Too Harsh**
   - Heavy pressure dramatically reduces accuracy
   - May need tuning for game feel

3. **No Clutch/Momentum**
   - No "clutch gene" modifier
   - No hot/cold streaks
   - No momentum effects

4. **Fatigue Underutilized**
   - Fatigue effects exist but rarely applied
   - No dynamic fatigue tracking per play

### Recommended Improvements

1. Add clutch modifier for high-stakes situations
2. Tune pressure effects for better game feel
3. Implement fatigue accumulation per play
4. Add momentum/streak mechanics

---

## Key Files

| Component | Location | Key Functions |
|-----------|----------|---------------|
| VarianceConfig | `core/variance.py` | `VarianceConfig`, `set_config()`, `is_deterministic()` |
| Recognition layer | `core/variance.py` | `recognition_delay()`, `recognition_accuracy()` |
| Execution layer | `core/variance.py` | `execution_timing()`, `execution_precision()` |
| Decision layer | `core/variance.py` | `should_make_suboptimal_decision()`, `target_selection_noise()` |
| Attribute conversion | `core/variance.py` | `attribute_to_factor()` |

## See Also

- [AI_BRAINS.md](AI_BRAINS.md) - How brains use variance
- [RESOLUTION.md](RESOLUTION.md) - Variance in outcomes
