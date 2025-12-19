# Behavior Tree Agent - Status

**Last Updated:** 2025-12-18
**Status:** Idle - session complete

---

## Session Summary (2025-12-18)

### Bugs Fixed Today
| Issue | Fix |
|-------|-----|
| QB always targets slot | `read_order` now flows from play design → PlayerView → qb_brain |
| Instant ball tracking (DBs) | Added 200-450ms reaction delay based on awareness/facing |
| Instant ball tracking (LBs) | Added 250-500ms reaction delay |
| D-line tracks ball on throw | DL now stays engaged or continues rush, doesn't chase ball |

### Code Changes
- `qb_brain.py`: Use `teammate.read_order` instead of hardcoded 1
- `db_brain.py`: Added `_calculate_throw_reaction_delay()`, `_can_track_ball_yet()`
- `lb_brain.py`: Added `_calculate_lb_throw_reaction_delay()`, `_can_lb_track_ball_yet()`
- `dl_brain.py`: Added `_is_ball_in_air()` check, DL stays engaged during ball flight

---

## Verified Features (37/37 tests)

| Feature | Tests |
|---------|-------|
| OL Coordination (MIKE, combo, stunt) | 8/8 |
| Cognitive Features (Easterbrook, play action, etc) | 12/12 |
| Pre-Snap QB Intelligence | 17/17 |

---

## Complete Feature List

- Pre-Snap QB: Coverage shells, blitz detection, hot routes, protection calls
- OL Coordination: MIKE identification, combo blocks, stunt pickup
- Cognitive Science: Pressure-narrowed vision, recency bias, play action response, ball-hawking
- Ballcarrier: Team-based direction, sideline awareness
- QB Read Progression: Uses read_order from play design
- Throw Reaction Delay: Realistic cognitive delay before ball tracking

---

## Waiting On (Orchestrator)

| Feature | Blocker |
|---------|---------|
| Engagement persistence | Orchestrator clears engagements on throw |
| Inner Weather | `PlayMentalState` not in WorldState |
| Clock awareness | `game_situation` not populated |
| DL stunts | Stunt assignments not passed from play calls |

---

## In Discussion

**Key Defender Read System** - Researcher Agent proposal to make QB read one key defender per concept instead of geometric separation. Would make game feel more like real football. Waiting on implementation spec.

---

## Bugs Filed

- `claude_code_agent_to_005`: Message ID collision when two files share same number prefix

---

**- Behavior Tree Agent**
