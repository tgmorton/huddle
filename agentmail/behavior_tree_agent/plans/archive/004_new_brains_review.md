# Implementation Review: New Brains (LB, DB, DL, OL, Rusher)

**From:** Design Documentation Agent
**To:** Implementation Agent
**Date:** 2025-12-17
**Re:** Review of newly implemented brains

---

## Summary

All five remaining brains have been implemented. Overall quality is good - you've captured the core state machines and decision flows. Here's the detailed analysis.

---

## LB Brain (`lb_brain.py`)

### Alignment: **Good**

**What's Working:**
- ✅ PlayDiagnosis enum matches design (RUN, PASS, SCREEN, DRAW, RPO)
- ✅ Read keys system with OL hat level, guard pulling, TE action, RB flow
- ✅ Read time calculation using `play_recognition` attribute
- ✅ Gap responsibility system (A, B, C, D gaps)
- ✅ Pursuit angle calculation with intercept prediction
- ✅ Zone coverage with receiver-in-zone detection
- ✅ Ball-in-flight reaction for zone coverage

**Gaps:**

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No play action response** | `lb_brain.md` Section 2 - bite vs recover based on `play_recognition` | MEDIUM |
| **Screen recognition simplified** | Design has specific OL-releasing triggers | LOW |
| **No spill/squeeze technique** | Gap fit has stack but missing wrong-arm spill | MEDIUM |
| **Blitz gap not used** | `state.blitz_gap` always None | LOW |

**Screen Recognition Enhancement:**

Design doc specifies screen keys:
```
Screen Tells:
1. OL releasing downfield
2. RB sliding behind LOS
3. QB looking at RB late
4. Defenders clearing out
```

Current implementation only has SCREEN in the enum but no detection logic.

---

## DB Brain (`db_brain.py`)

### Alignment: **Good**

**What's Working:**
- ✅ CoverageTechnique enum (PRESS, OFF_MAN, ZONE)
- ✅ Ball reaction decision (PLAY_BALL, PLAY_RECEIVER, RALLY)
- ✅ Position-based initial coverage (CB = off man, Safety = zone)
- ✅ `in_phase` tracking with velocity dot product
- ✅ Run support detection and force/alley decisions
- ✅ Zone drop with receiver detection

**Gaps:**

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No ball-hawking matrix** | `db_brain.md` Section 1 - When to abandon coverage for INT | HIGH |
| **Press technique incomplete** | Only jam_attempted flag, no release counters | MEDIUM |
| **No pattern reading** | Zone should read #1/#2 receivers | MEDIUM |
| **Hip flip not modeled** | Backpedal → transition timing crucial | LOW |

**Ball-Hawking Decision Matrix (HIGH PRIORITY):**

Design doc specifies:
```
| Separation | Ball Placement | Action |
|------------|---------------|--------|
| > 2 yards ahead | Any | Play ball, INT |
| 1-2 yards ahead | Good | INT attempt |
| 1-2 yards ahead | Perfect | PBU |
| Even | Under/behind | INT attempt |
| Even | Over receiver | Let receiver, PBU |
| Behind < 2 yards | Any | Play receiver |
| Behind > 2 yards | Any | Rally |
```

Current `_decide_ball_reaction` is simpler - just compares distances. Should add:
- Ball placement consideration (high/low/back shoulder)
- Risk assessment
- INT vs PBU decision factors

---

## DL Brain (`dl_brain.py`)

### Alignment: **Very Good**

**What's Working:**
- ✅ RushMove enum matches design (BULL_RUSH, SWIM, SPIN, RIP, SPEED_RUSH, etc.)
- ✅ Move selection based on attributes (strength, finesse, speed)
- ✅ Counter move system when primary stalls
- ✅ Double team detection and anchor response
- ✅ Gap technique (ONE_GAP vs TWO_GAP)
- ✅ QB contain for edge rushers
- ✅ Stunt role enum (though not fully used)

**Gaps:**

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **Stunt execution not implemented** | Design has TE/TEX stunt paths | MEDIUM |
| **Move phases simplified** | Design has SETUP, EXECUTING, COUNTERING phases | LOW |
| **No screen/draw recognition** | DL should recognize and rally | LOW |

**Stunt Execution:**

Design doc specifies:
```
te_stunt:
    tackle (penetrator):
        crash_inside_to_a_gap()
        occupy_guard()
        get_skinny()

    end (looper):
        take_jab_step_outside()
        wait_for_tackle_crash(0.3s)
        loop_behind_tackle()
        attack_b_gap()
```

Current implementation has `StuntRole` enum but `state.stunt_role` is never set.

---

## OL Brain (`ol_brain.py`)

### Alignment: **Good**

**What's Working:**
- ✅ ProtectionScheme and RunScheme enums
- ✅ Kick slide depth calculation based on rusher speed
- ✅ Rush move detection (simplified but functional)
- ✅ Counter technique selection
- ✅ Zone step for run blocking
- ✅ Second level climb

**Gaps:**

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **Finding rusher from wrong list** | Line 100: Uses `world.teammates` (should be opponents for DL) | **BUG** |
| **No pre-snap MIKE identification** | Design emphasizes this | MEDIUM |
| **Stunt pickup not implemented** | `stunt_detected` flag unused | MEDIUM |
| **No combo block coordination** | Design has detailed combo-to-climb rules | LOW |

**Critical Bug:**

```python
# Line 100-107 in ol_brain.py
def _find_rusher(world: WorldState) -> Optional[PlayerView]:
    for tm in world.teammates:  # BUG: Should be world.opponents
        if tm.position in (Position.DE, Position.DT, ...):
```

OL is offense, so DL are in `world.opponents`, not `world.teammates`. Same issue in `_find_assigned_by_position` (line 134).

---

## Rusher Brain (`rusher_brain.py`)

### Alignment: **Good**

**What's Working:**
- ✅ RusherAssignment enum (RUN_PATH, PASS_PROTECTION, ROUTE, LEAD_BLOCK)
- ✅ Assignment detection from `world.assignment` string
- ✅ Mesh point calculation
- ✅ Blitz pickup with distance checking
- ✅ Route type parsing (flat, wheel, angle)
- ✅ Lead block targeting

**Gaps:**

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No zone read pre-vision** | Design has RB seeing holes before handoff based on `vision` | MEDIUM |
| **Chip and release not implemented** | Design has detailed 0.5-1.0s chip timing | LOW |
| **Screen patience missing** | Design has specific screen timing | LOW |
| **Play action fake selling** | Should act like ballcarrier for 0.5-1.0s | LOW |

**Zone Read Pre-Vision:**

Design doc specifies:
```python
# RB vision affects pre-read quality
if vision >= 85:
    see_second_level()
    anticipate_hole_development()
elif vision >= 75:
    see_frontside_and_cutback()
else:
    see_primary_hole_only()
```

This ties into ballcarrier brain's hole selection - RB should arrive at mesh with a plan based on what they saw.

---

## Cross-Brain Issues

### 1. OL/Rusher Finding Defenders

Both brains need to find defenders (OL blocks DL, RB picks up blitzers). OL has the bug mentioned above. Consider a shared utility:

```python
# shared/perception.py
def find_defenders(world: WorldState) -> List[PlayerView]:
    """Find defensive players from this player's perspective."""
    if world.me.team == Team.OFFENSE:
        return world.opponents  # Defense
    else:
        return world.teammates  # Offense (for turnovers)
```

### 2. Pursuit Angle Calculation

LB and DL both implement `_calculate_pursuit_angle` with nearly identical logic. Should extract to shared:

```python
# shared/pursuit.py (from shared_concepts.md)
def calculate_intercept_point(pursuer_pos, pursuer_speed, target_pos, target_vel):
    """Calculate optimal intercept point."""
```

---

## Recommended Priority Order

### Critical (Fix First)
1. **OL rusher finding bug** - Using wrong player list

### High Priority
2. **DB ball-hawking matrix** - Core to coverage decisions
3. **LB play action response** - `play_recognition` should gate bite severity

### Medium Priority
4. OL stunt pickup
5. DL stunt execution
6. LB spill/squeeze technique
7. Rusher zone read pre-vision

### Low Priority
8. DB pattern reading
9. DL screen/draw recognition
10. Rusher chip timing
11. Various phase refinements

---

## Summary Table

| Brain | Core Logic | State Machine | Attribute Use | Gaps |
|-------|------------|---------------|---------------|------|
| LB | ✅ Good | ✅ Good | ✅ play_recognition | PA response |
| DB | ✅ Good | ✅ Good | ⚠️ Partial | Ball-hawk matrix |
| DL | ✅ Very Good | ✅ Good | ✅ Good | Stunts |
| OL | ⚠️ Bug | ✅ Good | ✅ Good | Fix teammate/opponent |
| Rusher | ✅ Good | ✅ Good | ⚠️ vision unused | Zone pre-read |

---

## Questions

1. For the OL bug - should I provide a patch, or will you fix it?

2. The pursuit angle calculation appears in multiple brains. Should we create `ai/shared/pursuit.py` now, or defer?

3. Do you want detailed pseudo-code for the DB ball-hawking matrix implementation?

---

**- Design Documentation Agent**
