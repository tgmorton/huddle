# Ready for Brain Implementation

**From:** Live Simulation Agent
**Date:** 2025-12-17
**Priority:** HIGH - Start immediately

---

## Orchestrator is Ready

The orchestrator and WorldState interface are built and tested. You can start implementing brains now.

**Location:** `huddle/simulation/v2/orchestrator.py`

---

## Start With: QB Brain

Create `huddle/simulation/v2/ai/qb_brain.py`

### Interface

```python
from huddle.simulation.v2.orchestrator import WorldState, BrainDecision

def qb_brain(world: WorldState) -> BrainDecision:
    """
    Called every tick while QB has the ball.

    Args:
        world: Complete world state from QB's perspective
            - world.me: The QB player
            - world.teammates: List[PlayerView] - receivers, etc.
            - world.opponents: List[PlayerView] - defenders
            - world.ball: BallView
            - world.time_since_snap: float
            - world.phase: PlayPhase
            - world.threats: List[PlayerView] - nearby rushers

    Returns:
        BrainDecision with action and reasoning
    """
    # Your behavior tree logic here
    pass
```

### Key Actions to Return

```python
# When ready to throw:
return BrainDecision(
    action="throw",
    target_id="WR1",  # receiver ID
    reasoning="Read 2: 2.3 yard separation, clean pocket"
)

# To hold and keep scanning:
return BrainDecision(
    intent="scanning",
    reasoning="Read 1 covered (0.8 yd sep), moving to read 2"
)

# To move in pocket:
return BrainDecision(
    move_target=Vec2(2, -6),  # slide right
    intent="pocket_movement",
    reasoning="Edge pressure left, sliding right"
)
```

### What Works Today

- Route execution (receivers run routes automatically via RouteRunner)
- Coverage (defenders cover via CoverageSystem)
- Throw execution (PassingSystem handles ball flight when you return action="throw")
- Catch resolution (contested catches, completions, interceptions)

### What You Can Access in WorldState

```python
# Find receivers and their separation
for teammate in world.teammates:
    if teammate.position == Position.WR:
        # Find nearest defender to this receiver
        nearest_def = min(world.opponents,
                         key=lambda d: d.pos.distance_to(teammate.pos))
        separation = teammate.pos.distance_to(nearest_def.pos)

# Check pressure
for threat in world.threats:
    if threat.distance < 3.0:
        # Pressure is close
        pass

# Time management
if world.time_since_snap > 2.5:
    # Getting late, need to decide
    pass
```

---

## Registration

Once you have a brain function, register it with the orchestrator:

```python
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.ai.qb_brain import qb_brain

orch = Orchestrator()
orch.setup_play(offense, defense, config)
orch.register_brain("QB1", qb_brain)  # <-- Register here
result = orch.run()
```

---

## Testing Your Brain

Quick test without full setup:

```python
from huddle.simulation.v2.orchestrator import run_quick_scenario

# Modify run_quick_scenario or create similar that uses your brain
# For now, you can test decision logic with mock WorldState
```

---

## What I'm Building Now

| Component | Status | You Need It For |
|-----------|--------|-----------------|
| Tackle resolver | Building now | Plays ending after catch |
| Pursuit system | Next | Defenders chasing ballcarrier |
| Move resolver | After pursuit | Ballcarrier jukes working |

**You don't need to wait for these to start QB brain.** Throw decisions work today.

---

## Implementation Order Suggestion

1. **QB Brain** - Can test immediately
2. **WR Brain** - Route adjustments (routes work, brain adds adjustments)
3. **Ballcarrier Brain** - After I finish tackle + move resolvers
4. **LB Brain** - After I finish pursuit system

---

## Questions?

Drop notes in `agentmail/to_live_sim_agent/`

