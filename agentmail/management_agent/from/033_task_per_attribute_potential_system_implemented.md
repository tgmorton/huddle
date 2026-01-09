# Per-Attribute Potential System Implemented

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19 17:24:55
**Type:** task
**Priority:** medium

---

# Per-Attribute Potential System

Implemented a new per-attribute potential system for draft prospects. Each attribute now has its own ceiling based on growth category.

## Data Structure Changes

### Player Model (`huddle/core/models/player.py`)

New field added:
```python
perceived_potentials: Optional[dict[str, int]] = None
```

### PlayerAttributes (`huddle/core/attributes/registry.py`)

New methods:
- `get_potential(attr_name)` → returns ceiling for attribute
- `set_potential(attr_name, value)` → sets ceiling
- `get_growth_room(attr_name)` → returns (potential - current)
- `get_all_potentials()` → returns dict of all potentials

## How to Access

### Actual Potentials (true ceilings)
Stored in `player.attributes` with `_potential` suffix:
```python
player.attributes.get_potential("speed")  # e.g., 92
player.attributes.get_growth_room("speed")  # e.g., 4
# Or direct access:
player.attributes._values["speed_potential"]  # 92
```

### Perceived Potentials (scout estimates - can be wrong)
```python
player.perceived_potentials["speed_potential"]  # e.g., 88 (underrated)
```

## Growth Categories

| Category | Growth Range | Attributes |
|----------|--------------|------------|
| PHYSICAL | +0-5 | speed, acceleration, jumping |
| PHYSICAL | +1-6 | strength, agility, stamina |
| MENTAL | +5-18 | awareness, play_recognition, zone_coverage |
| TECHNIQUE | +4-15 | throwing, catching, blocking, tackling |

## Distribution (realistic variance)

- **19% Peaked** - already at ceiling (growth = 0)
- **58% Minimal** - limited upside (+1-2)
- **12% Normal** - decent growth (+3-4)
- **12% Raw** - big upside (+5-9)

## Example Data

Elite WR prospect:
```json
{
  "speed": 88,
  "speed_potential": 90,
  "awareness": 72,
  "awareness_potential": 88,
  "perceived_potentials": {
    "speed_potential": 92,
    "awareness_potential": 80
  }
}
```

In this example:
- Speed: 88 → 90 (peaked, only +2 room)
- Awareness: 72 → 88 (big growth room +16)
- Scout OVERRATES speed (thinks 92 vs actual 90)
- Scout UNDERRATES awareness (thinks 80 vs actual 88)

## API Changes Needed

The `/management/franchise/{id}/draft-prospects` endpoint should expose:
1. Per-attribute potentials (or growth room)
2. Perceived vs actual for scouting UI

Let me know if you need specific API schema changes.

## Files Created/Modified

- `huddle/core/attributes/growth_profiles.py` (NEW)
- `huddle/generators/potential.py` (NEW)
- `huddle/core/attributes/registry.py` (modified)
- `huddle/core/models/player.py` (modified)
- `huddle/generators/player.py` (modified)