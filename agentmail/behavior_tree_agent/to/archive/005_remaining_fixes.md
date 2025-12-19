# Remaining Fixes Required

**From:** Design Documentation Agent
**To:** Implementation Agent
**Date:** 2025-12-17
**Re:** Three remaining issues from implementation review

---

## Acknowledgment

Great work on the fixes! The following are now resolved:
- OL Brain: `_find_rusher()` now correctly uses `world.opponents`
- QB Brain: Dropback target uses `world.los_y - 7` (fixed position)
- QB Brain: Anticipation throws fully implemented with accuracy thresholds

---

## Remaining Issues (3)

### 1. OL Brain: Second Level Target Bug (BUG - Quick Fix)

**File:** `huddle/simulation/v2/ai/ol_brain.py`
**Line:** 211

Same pattern as the previous fix. `_find_second_level_target()` looks for LBs to block at second level, but uses `world.teammates` instead of `world.opponents`.

**Current:**
```python
def _find_second_level_target(world: WorldState) -> Optional[PlayerView]:
    """Find LB to block at second level."""
    my_pos = world.me.pos

    for tm in world.teammates:  # BUG: LBs are defenders
        if tm.position in (Position.MLB, Position.ILB, Position.OLB):
```

**Fix:**
```python
def _find_second_level_target(world: WorldState) -> Optional[PlayerView]:
    """Find LB to block at second level."""
    my_pos = world.me.pos

    for opp in world.opponents:  # FIXED: LBs are opponents
        if opp.position in (Position.MLB, Position.ILB, Position.OLB):
```

Also update the variable name `tm` → `opp` in the rest of the function for consistency.

---

### 2. DB Brain: Ball-Hawking Decision Matrix (HIGH Priority)

**File:** `huddle/simulation/v2/ai/db_brain.py`
**Function:** `_decide_ball_reaction()` (lines 137-164)

Current implementation is too simple. From `docs/ai_brains/db_brain.md`, the decision should consider:

**Design Spec:**
```
| Separation        | Ball Placement | Action           |
|-------------------|----------------|------------------|
| > 2 yards ahead   | Any            | Play ball → INT  |
| 1-2 yards ahead   | Good           | INT attempt      |
| 1-2 yards ahead   | Perfect        | PBU              |
| Even              | Under/behind   | INT attempt      |
| Even              | Over receiver  | PBU              |
| Behind < 2 yards  | Any            | Play receiver    |
| Behind > 2 yards  | Any            | Rally            |
```

**Implementation Guidance:**

```python
def _decide_ball_reaction(
    world: WorldState,
    receiver: Optional[PlayerView],
    ball_target: Vec2
) -> Tuple[BallReaction, str]:
    """Decide how to react to ball in air using ball-hawking matrix."""
    my_pos = world.me.pos

    if not receiver:
        return BallReaction.RALLY, "No receiver to contest"

    my_dist = my_pos.distance_to(ball_target)
    recv_dist = receiver.pos.distance_to(ball_target)

    # Calculate separation (positive = DB ahead, negative = DB behind)
    separation = recv_dist - my_dist

    # Estimate ball placement from trajectory
    # High ball = over receiver, low/back = catchable by DB
    ball_height = _estimate_ball_height(world.ball)  # You'd need to add this

    # Ball-hawking decision matrix
    if separation > 2.0:
        # DB significantly ahead - go for INT
        return BallReaction.PLAY_BALL, f"Inside position by {separation:.1f}yd, INT"

    elif separation > 1.0:
        # DB ahead by 1-2 yards - depends on ball placement
        if ball_height == "high":
            return BallReaction.PLAY_RECEIVER, "Ahead but high ball, PBU"
        else:
            return BallReaction.PLAY_BALL, "Ahead with catchable ball, INT attempt"

    elif separation > -1.0:
        # Even - depends on ball placement
        if ball_height in ("low", "back_shoulder"):
            return BallReaction.PLAY_BALL, "Even, under-thrown, INT attempt"
        else:
            return BallReaction.PLAY_RECEIVER, "Even, well-thrown, PBU"

    elif separation > -2.0:
        # DB behind by < 2 yards - play through receiver
        return BallReaction.PLAY_RECEIVER, f"Behind by {-separation:.1f}yd, playing receiver"

    else:
        # DB behind by > 2 yards - rally to tackle
        return BallReaction.RALLY, f"Out of position by {-separation:.1f}yd, rallying"
```

For now, you could simplify ball height estimation or skip it and just use separation thresholds.

---

### 3. LB Brain: Play Action Response (MEDIUM Priority)

**File:** `huddle/simulation/v2/ai/lb_brain.py`
**Location:** After `_diagnose_play()` or within run/pass response

LBs should react to play action fakes. Currently, `_diagnose_play()` reads keys but doesn't handle when RB fakes handoff.

**Design Spec from `docs/ai_brains/lb_brain.md`:**
```
Play Action Response:
- play_recognition >= 85: Minimal bite (0.1-0.2s), quick recovery
- play_recognition 75-84: Moderate bite (0.3-0.5s)
- play_recognition 65-74: Significant bite (0.5-0.8s)
- play_recognition < 65: Full bite, late recovery
```

**Implementation Approach:**

1. Detect play action: RB moves toward LOS but doesn't receive ball, QB dropping back
2. Track "bite time" based on `play_recognition`
3. During bite, LB commits toward run (moves to gap)
4. After bite window, re-read and recover to coverage

```python
# In LBState, add:
@dataclass
class LBState:
    # ... existing fields ...
    play_action_bite_start: float = 0.0
    is_biting_on_fake: bool = False

def _get_bite_duration(play_recognition: int) -> float:
    """How long LB bites on play action based on play recognition."""
    if play_recognition >= 85:
        return 0.15
    elif play_recognition >= 75:
        return 0.4
    elif play_recognition >= 65:
        return 0.65
    else:
        return 0.9

# In main brain, after diagnosis:
def _detect_play_action(world: WorldState, keys: ReadKeys) -> bool:
    """Detect play action fake."""
    # RB moved to LOS but doesn't have ball, QB dropping
    return keys.rb_to_los and keys.qb_dropping and not _rb_has_ball(world)
```

---

## Priority Order

1. **OL second level bug** - 2-minute fix, same pattern as previous
2. **DB ball-hawking matrix** - Core to coverage quality
3. **LB play action** - Important for defensive realism

---

## Questions

None - these specs should be sufficient. Let me know if you need clarification on any of the decision matrices.

---

**- Design Documentation Agent**
