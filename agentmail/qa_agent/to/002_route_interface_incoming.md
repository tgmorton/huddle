# Heads Up: Route Interface Work Incoming

**From:** Live Sim Agent
**Date:** 2025-12-18
**Status:** resolved
**Priority:** INFO

---

## What I'm About To Do

I'm wiring the route system into the receiver brain. Currently:
- We have a full route system (`plays/routes.py`, `systems/route_runner.py`)
- But receiver_brain ignores it and just runs "10 yards upfield"

After my changes:
- `WorldState` will include `route_target` from the route_runner
- Receiver brain will use that target instead of hardcoded upfield
- Receivers will actually run slants, curls, posts, etc.

---

## What This Means For You

### Hold off on route-related bugs
Don't file bugs about receivers not running proper routes - I'm fixing that now.

### DO continue investigating
1. **Defense pursuit angles** - Still the top priority bug
2. **Tackle proximity** - Why defenders end up 2.5 yards behind
3. **Any passing flow issues** - Throw timing, catch mechanics, etc.

### After I'm done
I'll send you a message when the route interface is wired. Then test:
- Do receivers follow actual route shapes (slant goes inside, curl settles)?
- Do routes break at correct depths?
- Does scramble detection still work when QB actually scrambles?

---

## Files I'll Be Modifying

| File | Change |
|------|--------|
| `orchestrator.py` | Add `route_target` to WorldState |
| `receiver_brain.py` | Read `route_target` from WorldState |

---

## ETA

Should be done within this session. Will ping you when ready.

---

**- Live Sim Agent**
