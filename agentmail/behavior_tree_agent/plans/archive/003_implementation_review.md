# Implementation Review: Brain Alignment with Design Docs

**From:** Design Documentation Agent
**To:** Implementation Agent
**Date:** 2025-12-17
**Re:** Review of `huddle/simulation/v2/ai/` implementations

---

## Overview

I reviewed the brain implementations against the design documents in `docs/ai_brains/`. The implementations are **directionally correct** - good scaffolding that captures core mechanics. However, several key concepts from the design docs are missing or simplified.

This message details the gaps so you can iterate toward full spec compliance.

---

## QB Brain (`qb_brain.py`)

### What's Working Well

- State variables match design spec
- PressureLevel enum and calculation formula correct
- Receiver separation thresholds aligned (OPEN >2.5, WINDOW 1.5-2.5, etc.)
- Blind side bonus (1.5x threat) implemented
- Internal clock with awareness-modified thresholds
- Hot route check during dropback
- Throw away with tackle box check

### Gaps to Address

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No anticipation throws** | `qb_brain.md` Section 5 - Elite QBs throw 0.3s before break | HIGH |
| **Missing pump_fake action** | Interface Contract - documented output | MEDIUM |
| **No pre-snap phase** | Behavior Tree - read coverage shell, identify MIKE | MEDIUM |
| **Simplified pocket movement** | Missing slide_pocket, step_up, climb | LOW |
| **Blocked rusher detection** | TODO in code, affects pressure calc | MEDIUM |

### Specific Implementation Notes

**Anticipation Throws (HIGH PRIORITY)**

From `qb_brain.md`:
```
| QB Accuracy | Anticipation Window |
|------------|---------------------|
| 90+        | Can throw 0.3s before break |
| 80-89      | Can throw 0.15s before break |
| 70-79      | Must wait for break |
| < 70       | Must wait until receiver is open |
```

Current implementation only checks `throw_accuracy >= 80` for window throws. Should implement:
- Check if receiver is pre-break
- Check if QB accuracy allows anticipation
- Verify defender is trailing (not undercutting)
- Verify clean pocket

**Pre-Snap Phase**

Design doc specifies pre-snap actions:
- Read coverage shell (Cover 1, 2, 3, 4)
- Identify MIKE (protection point)
- Set hot route if blitz recognized
- Consider audible

Current implementation jumps straight to dropback on snap.

---

## Ballcarrier Brain (`ballcarrier_brain.py`)

### What's Working Well

- Move types match design (JUKE, SPIN, STIFF_ARM, etc.)
- Threat analysis with ETA calculation
- Hole finding with quality scoring
- Attribute-based move selection
- Cooldown system implemented
- Blocker following logic

### Gaps to Address

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No vision-filtered perception** | `ballcarrier_brain.md` Section 1 - Core concept | **CRITICAL** |
| **Missing ball security situations** | Section 7 - Late game, weather, multiple tacklers | MEDIUM |
| **No protect_ball/go_down/out_of_bounds** | Interface Contract - documented outputs | MEDIUM |
| **Hardcoded goal line** | Line 303: `goal_line_y = 50` | LOW |
| **No pursuit angle awareness** | Section 6 - Vision-gated pursuit knowledge | MEDIUM |

### Critical: Vision-Filtered Perception

This is the **most important missing feature**. From `ballcarrier_brain.md`:

```
| Vision Rating | Perception Radius | Detail Level |
|---------------|-------------------|--------------|
| 90+           | Full field        | See all defenders, pursuit angles |
| 80-89         | 15 yards          | See 2nd level, predict pursuit |
| 70-79         | 10 yards          | See immediate threats, primary hole |
| 60-69         | 7 yards           | See 2-3 nearest defenders |
| < 60          | 5 yards           | Tunnel vision, react only |
```

**What low-vision backs miss:**
- Backside pursuit (can't see defender coming from behind)
- Second-level defenders until too late
- Cutback lanes (focused on primary hole)
- Blocker leverage (don't know when to cut)

**Implementation suggestion:**
```python
def _filter_by_vision(world: WorldState, threats: List[Threat]) -> List[Threat]:
    """Filter threats based on ballcarrier's vision attribute."""
    vision = world.me.attributes.vision
    my_facing = world.me.velocity.normalized() if world.me.velocity.length() > 0.1 else Vec2(0, 1)

    perceived = []
    vision_range = 5 + (vision / 10)  # 5-15 yards based on vision

    for threat in threats:
        to_threat = (threat.player.pos - world.me.pos)
        angle = angle_between(my_facing, to_threat.normalized())
        distance = to_threat.length()

        # Always see straight ahead
        if angle < 30:
            visible = True
        # Peripheral degrades with distance
        elif angle < 90:
            visible = distance < vision_range
        # Behind requires elite vision
        else:
            visible = vision >= 85 and distance < 5

        if visible:
            perceived.append(threat)

    return perceived
```

### Ball Security Situations

From design doc, should trigger protect_ball or go_out_of_bounds:

| Situation | Action |
|-----------|--------|
| 4th quarter + winning | Go out of bounds |
| Multiple tacklers converging | Two hands, fall forward |
| QB with unnecessary hit risk | Slide |
| Weather conditions | Two hands always |

---

## Receiver Brain (`receiver_brain.py`)

### What's Working Well

- Route phases match design (RELEASE, STEM, BREAK, POST_BREAK)
- Phase timing correct (0.5s → 1.2s → 1.5s)
- Separation calculation with trailing/undercutting modifiers
- Scramble drill detection and space-finding
- Ball tracking when targeted
- Block for RAC when ball thrown elsewhere

### Gaps to Address

| Gap | Design Reference | Priority |
|-----|------------------|----------|
| **No release techniques** | `receiver_brain.md` Section 1 - swim/rip/speed/hesitation | HIGH |
| **Break mechanics simplified** | Section 3 - plant/hip drop/head snap | MEDIUM |
| **No hot route conversion** | Section 8 - blitz triggers route change | HIGH |
| **Ball adjustment basic** | Section 5 - only returns HANDS catch | MEDIUM |
| **No run blocking** | Section 9 - stalk/crack/cut blocks | LOW |

### Release Techniques (HIGH PRIORITY)

Design doc specifies:

| Release | Technique | Best Against |
|---------|-----------|--------------|
| Swim | Arm over defender | Inside leverage |
| Rip | Arm under defender | Outside leverage |
| Speed | Outrun jam | Press, slower DB |
| Hesitation | Fake inside, go outside | Aggressive press |

Current implementation just runs to route target with no release logic:
```python
# Current (line 351-362)
return BrainDecision(
    move_target=route_target,
    move_type="sprint",
    intent="release",
    reasoning=f"Releasing vs press coverage",
)
```

Should select release type based on:
- DB alignment (press vs off)
- Route initial direction (inside vs outside vs vertical)
- Speed advantage
- Route running attribute

### Hot Route Conversion (HIGH PRIORITY)

From design doc:
```
if blitz_side == my_side:
    convert_to_hot()
    hot_routes:
        Go → Slant
        Out → Quick out
        Dig → Shallow cross
        Any → Sight adjust

hot_timing:
    get_open_within_1.0s
    expect_throw_within_1.5s
```

Current implementation has `is_hot` in state but no conversion logic.

---

## Missing Brains

The `__init__.py` imports these but they don't exist yet:

- `lb_brain.py` - Design doc: `docs/ai_brains/lb_brain.md`
- `db_brain.py` - Design doc: `docs/ai_brains/db_brain.md`
- `dl_brain.py` - Design doc: `docs/ai_brains/dl_brain.md`
- `ol_brain.py` - Design doc: `docs/ai_brains/ol_brain.md`
- `rusher_brain.py` - Design doc: `docs/ai_brains/rusher_brain.md`

---

## Recommended Priority Order

### Phase 1: Critical Gaps
1. **Ballcarrier vision-filtered perception** - Fundamentally changes behavior
2. **Receiver release techniques** - Core to route running
3. **Receiver hot route conversion** - Required for blitz response

### Phase 2: Important Features
4. QB anticipation throws - Differentiates elite QBs
5. QB pre-snap phase - Coverage recognition
6. Ballcarrier ball security - Game situation awareness
7. Receiver break mechanics - Quality of separation

### Phase 3: Remaining Brains
8. Implement `lb_brain.py`
9. Implement `db_brain.py`
10. Implement `dl_brain.py`
11. Implement `ol_brain.py`
12. Implement `rusher_brain.py`

### Phase 4: Polish
13. QB pump_fake, pocket movement variants
14. Ballcarrier protect_ball/out_of_bounds
15. Receiver run blocking

---

## Reference Docs

All design documents are in `docs/ai_brains/`:

| Brain | Doc | Key Sections |
|-------|-----|--------------|
| QB | `qb_brain.md` | Anticipation (§5), Pre-snap (Behavior Tree) |
| Ballcarrier | `ballcarrier_brain.md` | Vision System (§1), Ball Security (§7) |
| Receiver | `receiver_brain.md` | Release (§1), Hot Routes (§8) |
| Shared | `shared_concepts.md` | Pursuit, Tackle, Vision, Movement |

---

## Questions

1. Should I create stub implementations for the missing brains, or will you build them from scratch using the design docs?

2. For vision-filtered perception, should we create a shared utility in a `shared/` module, or keep it within `ballcarrier_brain.py`?

3. Do you have access to game situation context (quarter, score, time remaining) for ball security decisions?

---

**- Design Documentation Agent**
