# Brain Implementations Complete

**From:** Behavior Tree Agent
**Date:** 2025-12-17
**Re:** AI brains for v2 simulation

---

## Summary

All 8 brain implementations are complete and tested:

| Brain | Location | Status |
|-------|----------|--------|
| QB | `huddle/simulation/v2/ai/qb_brain.py` | Complete |
| Receiver | `huddle/simulation/v2/ai/receiver_brain.py` | Complete |
| Ballcarrier | `huddle/simulation/v2/ai/ballcarrier_brain.py` | Complete |
| LB | `huddle/simulation/v2/ai/lb_brain.py` | Complete |
| DB | `huddle/simulation/v2/ai/db_brain.py` | Complete |
| DL | `huddle/simulation/v2/ai/dl_brain.py` | Complete |
| OL | `huddle/simulation/v2/ai/ol_brain.py` | Complete |
| Rusher (RB/FB) | `huddle/simulation/v2/ai/rusher_brain.py` | Complete |

---

## Design Review Response

Addressed all HIGH/CRITICAL items from `003_implementation_review.md`:

### 1. Ballcarrier Vision-Filtered Perception (CRITICAL)

Added vision system that filters threats based on player's `vision` attribute:

```python
| Vision | Radius | Can See Backside | Can See 2nd Level | Can See Cutback |
|--------|--------|------------------|-------------------|-----------------|
| 90+    | 30yd   | Yes              | Yes               | Yes             |
| 80-89  | 15yd   | Yes              | Yes               | Yes             |
| 70-79  | 10yd   | No               | Yes               | No              |
| 60-69  | 7yd    | No               | No                | No              |
| <60    | 5yd    | No               | No                | No              |
```

Low-vision backs now miss:
- Backside pursuit (unless very close)
- Peripheral defenders
- Cutback lanes

### 2. Receiver Release Techniques (HIGH)

Added release type selection based on defender leverage and receiver attributes:

| Release | Technique | Best Against |
|---------|-----------|--------------|
| Swim | Arm over | Inside leverage |
| Rip | Arm under | Outside leverage |
| Speed | Outrun | Slower DB |
| Hesitation | Fake + go | Aggressive press |

### 3. Receiver Hot Route Conversion (HIGH)

Added blitz detection and automatic hot route conversion:

```
Go/Fly/Streak → Slant
Out → Quick out
Dig/In → Shallow cross
Other → Sight adjust

Hot timing: Open within 1.0s, expect throw within 1.5s
```

### 4. QB Anticipation Throws (HIGH)

Added anticipation throw logic with accuracy thresholds:

```python
| Accuracy | Anticipation Window |
|----------|---------------------|
| 90+      | 0.3s before break   |
| 80-89    | 0.15s before break  |
| 70-79    | Must wait for break |
| <70      | Must wait for open  |
```

Requirements for anticipation:
1. Receiver pre-break
2. QB accuracy allows anticipation
3. Defender trailing (not undercutting)
4. Clean pocket (not heavy/critical pressure)

---

## Registration Example

```python
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai import (
    qb_brain,
    receiver_brain,
    ballcarrier_brain,
    lb_brain,
    db_brain,
)

orch = Orchestrator()
orch.setup_play(offense, defense, config)

# Register brains
orch.register_brain("QB1", qb_brain)
orch.register_brain("WR1", receiver_brain)
orch.register_brain("CB1", db_brain)
orch.register_brain("MLB1", lb_brain)

result = orch.run()
```

---

## Integration Notes

1. **WorldState Interface**: Brains only access `world.me.attributes` for their own player. `PlayerView` objects don't have attributes (by design).

2. **BrainDecision Interface**: Uses `action`, `intent`, `move_target`, `move_type`, `target_id`, `action_target`, and `reasoning` fields. No `data` field.

3. **State Management**: Each brain maintains module-level state dicts keyed by player ID. State resets at tick 0 / time_since_snap < 0.1.

---

## Remaining Items (Medium/Low Priority)

From the review, these remain unaddressed:

- QB pump_fake action
- QB pre-snap phase (coverage shell ID)
- QB detailed pocket movement (slide, step_up, climb)
- Ballcarrier protect_ball/go_out_of_bounds by game situation
- Receiver break mechanics (plant/hip drop/head snap)
- Receiver run blocking

These can be added incrementally as needed.

---

**- Behavior Tree Agent**
