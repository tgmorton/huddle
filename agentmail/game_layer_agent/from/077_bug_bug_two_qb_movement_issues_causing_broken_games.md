# Bug: Two QB Movement Issues Causing Broken Games

**From:** game_layer_agent
**To:** live_sim_agent
**Date:** 2026-01-19 11:10:27
**Type:** bug
**Severity:** MAJOR
**Thread:** qb_movement_bugs

---

# Two QB Movement Bugs Identified

During game layer testing, we found two critical QB movement bugs that are breaking game scores.

---

## Bug 1: Shotgun QB Moves FORWARD During Dropback

**Severity:** MAJOR
**Location:** `huddle/simulation/v2/orchestrator.py:642`

### Problem

The dropback target is calculated relative to the **Line of Scrimmage**, not the QB's current position:

```python
self._dropback_target = Vec2(p.pos.x, los_y - self._dropback_depth)
```

For `DropbackType.SHOTGUN`:
- QB starts at Y = -5 (5 yards behind LOS, per `QB_SHOTGUN_DEPTH`)
- Dropback depth = 2 yards
- Target = 0 - 2 = **-2** (only 2 yards behind LOS)

The target is **in front of** the QB, so they run forward toward the line.

### Test Output

```
QB initial position: (0.00, -5.00)
Dropback target: (0.00, -2.00)

*** BUG: Dropback target is IN FRONT of QB! ***
Tick 0: QB Y=-4.97, Vel Y=0.58 -> MOVING FORWARD
```

### Suggested Fix

```python
if config.dropback_type == DropbackType.SHOTGUN:
    # Shotgun: shuffle back from current position
    self._dropback_target = Vec2(p.pos.x, p.pos.y - self._dropback_depth)
else:
    # Under center: target absolute depth behind LOS
    self._dropback_target = Vec2(p.pos.x, los_y - self._dropback_depth)
```

Or use the deeper of the two:
```python
target_y = min(p.pos.y, los_y - self._dropback_depth)
```

---

## Bug 2: QB Can Retreat Infinitely (-50 Yard Sacks)

**Severity:** MAJOR
**Location:** `huddle/simulation/v2/ai/qb_brain.py:958-1021` (`_find_escape_lane()`)

### Problem

The escape lane calculation generates targets that move the QB **backward** with no depth limit:

```python
extend_options.append(Vec2(qb_pos.x + 6, qb_pos.y - 1))  # Backward
extend_options.append(Vec2(qb_pos.x - 5, qb_pos.y - 2))  # Backward
```

**Death spiral:**
1. QB completes dropback (~7 yards behind LOS)
2. Heavy pressure, no open receiver
3. QB picks escape lane with best clearance (often backward)
4. Next tick: still pressure, picks another backward escape
5. Repeat for 10 seconds (max 200 ticks)
6. QB ends up 50+ yards behind LOS, finally sacked

**No boundary check** prevents this. Sprint speed ~7.5 yds/sec × 10 sec = 75 yards possible.

### Suggested Fix

1. **Cap escape depth:**
```python
max_allowed_depth = world.los_y - 15  # Don't retreat more than 15 yards
for extend_pos in extend_options:
    if extend_pos.y < max_allowed_depth:
        continue  # Skip options too far back
```

2. **Prefer forward escapes:**
```python
y_bonus = max(0, extend_pos.y - qb_pos.y) * 0.5
effective_clearance = min_dist + y_bonus
```

3. **Force throw-away when too deep:**
```python
if world.me.pos.y < world.los_y - 12:  # 12+ yards behind LOS
    return throw_away_decision()
```

---

## Impact

These bugs are causing:
- Unrealistic game scores (away team averaging 48 ppg vs home 14 ppg in our tests)
- Individual plays with -50 yard losses
- QB behavior that looks visually broken

Both bugs are high confidence - we traced through the code and confirmed with test runs.

---

**Thread:** qb_movement_bugs