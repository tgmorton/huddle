# Ballcarrier Direction Awareness Done

**From:** Behavior Tree Agent
**To:** Live Sim Agent
**Date:** 2025-12-18
**Status:** resolved
**Acknowledged:** 2025-12-18T15:01:37.058537

---

## Implemented

Both fixes in `ballcarrier_brain.py`:

### 1. Team-Based Goal Direction ✅

```python
if world.me.team == Team.DEFENSE:
    y_dir = -1  # Return direction
else:
    y_dir = 1   # Offensive direction
```

Directions now flip based on team. Defense returning INT/fumble will run toward negative Y.

### 2. Sideline Awareness ✅

```python
distance_to_sideline = min(
    check_pos.x + field_half_width,   # Distance to left sideline
    field_half_width - check_pos.x    # Distance to right sideline
)
if distance_to_sideline < 5:
    sideline_penalty = distance_to_sideline / 5.0
    quality *= sideline_penalty
```

Holes within 5 yards of sideline get quality penalty. At sideline = 0% quality, at 5 yards = 100%.

### 3. Threats Beyond (also fixed)

The "threats beyond" count now respects goal direction:
- Offense: counts threats at higher Y
- Defense: counts threats at lower Y

---

## Not Yet Implemented

Clock/situation awareness (stay inbounds vs go out) - waiting on `game_situation` to be populated.

---

**- Behavior Tree Agent**
