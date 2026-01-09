# Request: Add combine stat generation for draft prospects

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-19
**Status:** resolved 13:41:04
**Type:** task
**Priority:** medium

---

# Request: Generate Combine Stats for Draft Prospects

The frontend ProspectPane is ready to display combine measurables, but the Player model fields are always null.

## Fields Needed

In `_generate_draft_prospect()` in `huddle/generators/player.py`, please add generation for:

- `player.forty_yard_dash` - float, 4.3-5.2 range (based on speed attr)
- `player.bench_press_reps` - int, 5-35 range (based on strength attr)
- `player.vertical_jump` - float, 25-45 inches (based on acceleration/agility)
- `player.broad_jump` - int, 95-140 inches (based on acceleration/speed)

## Suggested Logic

```python
speed = player.attributes.get("speed", 70)
strength = player.attributes.get("strength", 70)
acceleration = player.attributes.get("acceleration", 70)
agility = player.attributes.get("agility", 70)

# 40-yard: Speed 99 → ~4.30, Speed 50 → ~5.10
player.forty_yard_dash = round(5.30 - (speed * 0.012) + random.uniform(-0.05, 0.05), 2)

# Bench: Strength 99 → ~32 reps
player.bench_press_reps = max(5, int(strength * 0.35 - 3) + random.randint(-3, 3))

# Vertical: 25-45 inch range
player.vertical_jump = round((acceleration + agility) * 0.22 + 10 + random.uniform(-1.5, 1.5), 1)

# Broad: 95-140 inch range
player.broad_jump = max(95, int((acceleration + speed) * 0.45 + 50) + random.randint(-4, 4))
```

Add this right before `return player` in `_generate_draft_prospect()`.

---

**- Frontend Agent**