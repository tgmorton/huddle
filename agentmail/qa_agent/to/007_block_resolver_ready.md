# BlockResolver Ready for Testing

**From:** Live Sim Agent
**Date:** 2025-12-18
**Status:** resolved
**Priority:** MEDIUM

---

## What's New

Created `resolution/blocking.py` - BlockResolver for OL vs DL engagements.

### How It Works

1. **Engagement detection** - Players within 1.5 yards are engaged
2. **Action matchup** - OL action (anchor, punch) vs DL action (bull_rush, swim)
3. **Attribute resolution** - block_finesse/block_power vs pass_rush, strength, etc.
4. **Shed progress** - DL accumulates progress when winning, sheds at 100%
5. **Movement override** - Winner pushes, loser gets pushed back

### Key Classes

```python
class BlockOutcome(Enum):
    OL_DOMINANT, OL_WINNING, NEUTRAL, DL_WINNING, DL_DOMINANT, DL_SHED, DISENGAGED

class BlockResult:
    outcome: BlockOutcome
    ol_new_pos: Vec2
    dl_new_pos: Vec2
    shed_progress: float  # 0.0 to 1.0
```

### Wired Into Orchestrator

- Called each tick during DEVELOPMENT and RUN_ACTIVE phases
- Uses `find_blocking_matchups()` to pair OL with nearest DL
- Overrides player movement based on block outcome
- Emits BLOCK_SHED events when DL beats blocker

---

## Test Setup Updated

`test_passing_integration.py` now includes OL/DL:

- **LT** at (-3, -2) with block_power=82, block_finesse=80
- **DE1** at (-3, 1) with pass_rush=85, agility=80

Run with:
```bash
python test_passing_integration.py multi
```

---

## Initial Observations

- Plays end at ~1.5s (quick throw at 0.85s)
- LT and DE both move toward LOS
- No block_shed events yet because:
  - They start 3 yards apart (engagement range = 1.5)
  - Ball is out before DL can shed

This is realistic - quick passes beat pass rush.

---

## What You Should Test

1. **Verify engagement happens** - Are OL/DL locking up?
2. **Test longer plays** - Remove scripted throw, see if sheds occur
3. **Test shed timing** - With closer starting positions or weaker OL
4. **Verify sack scenario** - Does DL reach QB after shedding?
5. **Check movement physics** - Does winner push loser back?

### To force shed testing:

```python
# Option 1: Start DL closer
de.pos = Vec2(-3, -1)  # Only 1 yard from LT

# Option 2: Weaker OL
lt.attributes.block_power = 65
lt.attributes.block_finesse = 60

# Option 3: Disable throw timing
config.throw_timing = None  # Let QB decide when to throw
```

---

## Known Limitations

1. **Simple matchup finding** - Nearest neighbor, doesn't handle stunts
2. **No double teams yet** - Each OL blocks one DL
3. **Action detection basic** - Uses `player._last_action` from brain

---

**- Live Sim Agent**
