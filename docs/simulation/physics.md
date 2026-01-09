# Physics - Movement and Spatial Systems

The physics layer handles player movement, collisions, and spatial calculations. Physics is deterministic; variance is added at the decision/execution level.

## MovementSolver (`physics/movement.py`)

Single source of truth for all player movement.

### Core Interface

```python
result = movement_solver.solve(
    current_pos=player.pos,
    current_vel=player.velocity,
    target_pos=target,
    profile=profile,
    dt=0.05,  # 50ms tick
)

# Result contains:
result.new_pos      # Vec2
result.new_vel      # Vec2
result.cut_occurred # bool
result.cut_angle    # radians
result.speed_after  # yards/sec
```

### Movement Profiles

Derived from player attributes:

```python
@dataclass
class MovementProfile:
    max_speed: float        # yards/second
    acceleration: float     # yards/second²
    deceleration: float     # yards/second²
    cut_speed_retention: float  # 0-1
    cut_angle_threshold: float  # radians (~30°)
    reaction_time: float    # seconds
```

#### Attribute Mapping

| Attribute | Profile Field | Mapping |
|-----------|---------------|---------|
| Speed 50→99 | max_speed | 4.5→7.5 yds/s |
| Acceleration | accel | 8→16 yds/s² |
| Agility | cut_retention | 40%→85% |
| Agility | reaction_time | 250ms→100ms |

```python
profile = MovementProfile.from_attributes(
    speed=92,      # → max_speed ~7.2 yds/s
    acceleration=88,
    agility=90     # → cut_retention ~80%
)
```

#### Real-World Reference

| Speed Rating | 40-Yard Time | Max Speed |
|--------------|--------------|-----------|
| 99 | 4.2-4.3s | ~7.5 yds/s |
| 92 | 4.4s | ~7.0 yds/s |
| 85 | 4.5s | ~6.5 yds/s |
| 75 | 4.6-4.7s | ~6.0 yds/s |
| 60 | 5.0s+ | ~5.2 yds/s |

### Cut Mechanics

When direction change exceeds `cut_angle_threshold`:

```python
def speed_after_cut(self, current_speed, angle, agility=None):
    # Large angles lose more speed
    angle_factor = min(1.0, abs(angle) / math.pi)
    retention = self.cut_speed_retention * (1 - angle_factor * 0.3)
    result = current_speed * retention

    # Variance makes cuts slightly sharper OR sloppier
    if agility is not None:
        result = execution_precision(result, agility)

    return result
```

Example: 90° cut at 6 yds/s with 70% retention → 4.2 yds/s

### Position-Specific Profiles

```python
create_wr_profile(speed=90, accel=88, agility=88)
create_rb_profile(speed=88, accel=90, agility=90)
create_cb_profile(speed=92, accel=90, agility=92)
create_ol_profile(speed=55, accel=60, agility=55)
```

---

## BodyModel (`physics/body.py`)

Physical dimensions for collision and reach calculations.

### Properties

```python
@dataclass
class BodyModel:
    height: float          # yards
    weight: float          # pounds
    shoulder_width: float  # yards
    arm_length: float      # yards (~0.9 = 33 inches)

    collision_radius = shoulder_width / 2
    tackle_reach = collision_radius + arm_length
    catch_radius = arm_length * 1.1
```

### Position Templates

| Position | Height | Weight | Typical |
|----------|--------|--------|---------|
| WR | 6'1" | 200 lbs | slot_wr, elite_wr, speed_wr |
| RB | 5'10" | 215 lbs | power_rb, scat_rb |
| TE | 6'5" | 255 lbs | receiving_te, blocking_te |
| OL | 6'4"-6'6" | 305-315 lbs | - |
| DL | 6'2"-6'4" | 275-330 lbs | edge_rusher, 3_tech, nose_tackle |
| LB | 6'1"-6'2" | 235-250 lbs | mike_lb, coverage_lb |
| CB | 5'10"-6'1" | 185-200 lbs | press_cb, slot_cb |
| S | 6'0"-6'1" | 200-215 lbs | rangy_safety, box_safety |

### Usage

```python
# From position
body = BodyModel.for_position(Position.WR)

# From template
body = get_body_template("elite_wr")

# From measurements
body = BodyModel.from_measurements(
    height_inches=75,  # 6'3"
    weight_lbs=210,
    arm_length_inches=33
)
```

---

## Spatial Systems (`physics/spatial.py`)

### Collision Detection

OL/DL collision enforcement:

```python
MIN_SEPARATION = 0.8  # yards - body collision radius

def _enforce_lineman_collisions(self):
    for ol in ol_players:
        for dl in dl_players:
            dist = ol.pos.distance_to(dl.pos)
            if dist < MIN_SEPARATION:
                # Push apart
                separation_dir = (dl.pos - ol.pos).normalized()
                half_push = (MIN_SEPARATION - dist) / 2
                ol.pos -= separation_dir * half_push
                dl.pos += separation_dir * half_push
```

### Engagement Range

Blocking engagement detection:

```python
ENGAGEMENT_RANGE = 1.5  # yards

def is_engaged(ol, dl) -> bool:
    return ol.pos.distance_to(dl.pos) < ENGAGEMENT_RANGE
```

### Tackle Reach

When a defender can attempt a tackle:

```python
tackle_possible = distance < player.tackle_reach
# tackle_reach = collision_radius + arm_length (~1.2 yards)
```

---

## Movement Type Modifiers

Different movement types have speed penalties:

| Type | Speed % | Use Case |
|------|---------|----------|
| sprint | 100% | Full speed |
| run | 85% | Normal running |
| dropback | 80% | QB retreat |
| strafe | 65% | Lateral movement |
| backpedal | 55% | DB backpedal |
| coast | 50% | Slowing down |

Applied in orchestrator:

```python
MOVE_TYPE_SPEED = {
    "sprint": 1.0,
    "run": 0.85,
    "dropback": 0.80,
    "backpedal": 0.55,
    "strafe": 0.65,
    "coast": 0.5,
}

modified_profile = MovementProfile(
    max_speed=profile.max_speed * MOVE_TYPE_SPEED[decision.move_type],
    ...
)
```

---

## Honest Assessment

### What Works

1. **Single MovementSolver**: Clean interface, all movement goes through one place
2. **Attribute-derived profiles**: Natural variation based on ratings
3. **Cut speed loss**: Realistic direction change penalties

### Issues

1. **Simplified Physics**
   - No momentum (instant direction change within cut penalty)
   - No fatigue effect on speed
   - No terrain/weather effects

2. **Basic Hitboxes**
   - Circular hitboxes only
   - No player facing in collision
   - Mass doesn't affect push in collisions

3. **Missing Concepts**
   - No body positioning/leverage
   - No stacking (defender getting hip)
   - No physics-based contact (just overlap detection)

### Recommended Improvements

1. Add momentum system for more realistic acceleration
2. Implement elliptical hitboxes based on body orientation
3. Add fatigue modifier to max_speed
4. Consider mass in OL/DL push calculations

---

## Key Files

| Component | Location | Key Classes |
|-----------|----------|-------------|
| MovementSolver | `physics/movement.py` | `MovementSolver`, `MovementResult` |
| MovementProfile | `physics/movement.py` | `MovementProfile`, `from_attributes()` |
| BodyModel | `physics/body.py` | `BodyModel`, `for_position()` |
| Spatial utilities | `physics/spatial.py` | `SpatialQuery`, collision detection |

## See Also

- [RESOLUTION.md](RESOLUTION.md) - How collisions become outcomes
- [AI_BRAINS.md](AI_BRAINS.md) - How brains request movement
- [VARIANCE.md](VARIANCE.md) - Execution variance on cuts
