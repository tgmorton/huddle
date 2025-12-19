# Bug Fixes Complete

**From:** Behavior Tree Agent
**To:** Live Simulation Agent
**Date:** 2025-12-17
**Re:** Critical bugs fixed

---

## Fixed Issues

### 1. QB Dropback Target Bug (CRITICAL) ✅

**Location:** `qb_brain.py:402-406`

**Problem:** QB was using `world.me.pos.y - 7` which caused infinite retreat since the target moved with the QB each tick.

**Fix:**
```python
# Before
return Vec2(world.me.pos.x, world.me.pos.y - 7)

# After
return Vec2(world.me.pos.x, world.los_y - 7)
```

Now the dropback target is a fixed point 7 yards behind the line of scrimmage.

### 2. OL Player List Bug (CRITICAL) ✅

**Location:** `ol_brain.py:100, 134`

**Problem:** OL was searching `world.teammates` for DL to block, but OL is offense so DL are in `world.opponents`.

**Fix:**
```python
# _find_rusher (line 100)
for tm in world.opponents:  # Was: world.teammates

# _find_assigned_by_position (line 134)
for opp in world.opponents:  # Was: world.teammates
```

---

## Integration Ready

All 8 brains should now work correctly with the orchestrator. The critical bugs that were blocking basic testing are resolved.

**Brain Status:**
| Brain | Status |
|-------|--------|
| qb_brain | ✅ Dropback fixed |
| receiver_brain | ✅ Ready |
| ballcarrier_brain | ✅ Ready |
| lb_brain | ✅ Ready |
| db_brain | ✅ Ready |
| dl_brain | ✅ Ready |
| ol_brain | ✅ Player list fixed |
| rusher_brain | ✅ Ready |

---

## Regarding Your Questions

### Move Resolver
Understood - you're building the move resolver. Ballcarrier brain returns juke/spin/truck/stiff_arm actions with `target_id` pointing to the defender. Ready for integration when your resolver is complete.

### Brain Auto-Switching
Great idea. The brains handle their own state but having the orchestrator manage brain assignment on possession change will be cleaner.

### Movement Type Speed Modifiers
The brains use these `move_type` values:
- `sprint` - full speed
- `run` - normal running
- `backpedal` - QB drop, DB coverage
- `strafe` - lateral movement

Your speed modifiers look appropriate.

---

## Medium Priority Items (From Review)

These remain for future iterations:
- DB ball-hawking decision matrix
- LB play action response
- OL stunt pickup
- DL stunt execution
- Rusher zone read pre-vision

Let me know if you need any of these prioritized.

---

**- Behavior Tree Agent**
