# Live Sim Agent - Blocking System Implementation Plan

**Date:** 2025-12-18
**Status:** In Progress

---

## Priority 1: Fix Route Waypoint Advancement Bug (BLOCKING)

### Problem

QA Agent reported in `005_bug_route_waypoint_advancement.md`:
- Slant route receiver reaches waypoint 1 (Y=1.0) and STOPS
- Never advances to waypoints 2, 3, 4
- Blocks ballcarrier brain testing (no YAC opportunity)

### Root Cause

When a brain is registered, route_runner.update() never gets called:

```
_update_player():
    if player.id in self._brains:
        brain = self._brains[player.id]
        decision = brain(world_state)
        self._apply_brain_decision(player, decision)
        return  # <-- EXITS HERE, route_runner.update() never called

    # This only runs when NO brain
    self._update_offense_player(player)  # <-- calls route_runner.update()
```

The receiver_brain reads `world.route_target` from WorldState, but that's populated from `route_runner.get_assignment().current_target` which only reads current state - it doesn't ADVANCE waypoints.

### Fix

Option A: Call route_runner.update() even when brain is active (before brain decision)
- Pros: Route system handles advancement, brain just reads
- Cons: Need to make sure we don't double-move the player

Option B: Advance waypoints in _build_world_state when player is near current target
- Pros: Simple, no movement side effects
- Cons: Waypoint advancement logic duplicated

**Recommendation: Option A** - Call `route_runner.advance_waypoint()` (new method) after building world state but before brain decision. Keep movement in brain, but let route system track progress.

### Files to Modify

1. `orchestrator.py` - Call route advancement each tick for route runners
2. `systems/route_runner.py` - Add `advance_waypoint()` method that checks arrival and increments index

---

## Priority 2: BlockResolver Implementation

### Overview

Resolve OL vs DL engagements. Determine who wins each tick and what movement results.

### Design

#### BlockResolver Class

Location: `resolution/blocking.py`

```python
class BlockOutcome(Enum):
    OL_WINNING = "ol_winning"      # OL driving DL back
    OL_HOLDING = "ol_holding"      # Stalemate, OL maintaining
    DL_WINNING = "dl_winning"      # DL pushing through
    DL_SHED = "dl_shed"            # DL beat the block, free
    DISENGAGED = "disengaged"      # Not in contact

@dataclass
class BlockResult:
    outcome: BlockOutcome
    ol_movement: Vec2          # Where OL ends up
    dl_movement: Vec2          # Where DL ends up
    shed_progress: float       # 0.0 to 1.0, DL sheds at 1.0
    reasoning: str
```

#### Key Attributes

| OL Attributes | DL Attributes |
|---------------|---------------|
| pass_block | pass_rush |
| run_block | block_shed |
| strength | strength |
| awareness | agility |

#### Resolution Logic

1. **Engagement Check** - Are OL and DL within 1.5 yards?
2. **Action Matchup** - OL action (anchor/punch/drive) vs DL action (bull_rush/swim/spin)
3. **Attribute Roll** - Calculate win probability based on attributes
4. **Outcome** - Who moves where, shed progress

#### Matchup Matrix (simplified)

| DL Move | Best OL Counter | DL Advantage |
|---------|-----------------|--------------|
| bull_rush | anchor | strength vs strength |
| swim | punch | pass_rush vs pass_block |
| spin | refit | agility vs awareness |
| speed_rush | mirror | speed vs footwork |
| rip | punch | pass_rush vs pass_block |

#### Shed Timing

- DL accumulates "shed progress" each tick they're winning
- At 100% → DL is free (shed)
- OL winning resets/reduces shed progress

```python
if outcome == DL_WINNING:
    shed_progress += 0.15 * (1 + attribute_advantage * 0.1)
elif outcome == OL_WINNING:
    shed_progress = max(0, shed_progress - 0.1)
```

Average shed times:
- DL dominates: 0.5-1.0s
- Close matchup: 1.5-2.5s
- OL dominates: 4.0+s (may never shed)

### Orchestrator Integration

Add to tick loop:

```python
def _resolve_blocks(self):
    """Resolve all OL/DL engagements."""
    for ol in self.offense:
        if ol.position not in OL_POSITIONS:
            continue

        # Find engaged DL
        for dl in self.defense:
            if dl.position not in DL_POSITIONS:
                continue

            if ol.pos.distance_to(dl.pos) < ENGAGEMENT_RANGE:
                result = self.block_resolver.resolve(ol, dl, ol_decision, dl_decision)
                self._apply_block_result(ol, dl, result)
```

### Movement Override

When engaged, player's brain-requested movement is OVERRIDDEN by block result:

```python
def _apply_block_result(self, ol, dl, result):
    # Override positions based on block outcome
    ol.pos = result.ol_movement
    dl.pos = result.dl_movement

    # Track engagement state
    ol.is_engaged = result.outcome != BlockOutcome.DISENGAGED
    dl.is_engaged = result.outcome != BlockOutcome.DL_SHED
```

### Files to Create/Modify

1. **CREATE** `resolution/blocking.py` - BlockResolver class
2. **MODIFY** `orchestrator.py` - Add `_resolve_blocks()`, call in tick loop
3. **MODIFY** `core/entities.py` - Add `is_engaged` flag if not present

---

## Implementation Order

1. **Fix route waypoint bug** (blocks testing)
   - Add waypoint advancement to orchestrator tick
   - Verify slant routes work
   - Notify QA agent

2. **Build BlockResolver skeleton**
   - Create `resolution/blocking.py`
   - Basic engagement detection
   - Simple win/lose resolution

3. **Wire into orchestrator**
   - Call `_resolve_blocks()` in tick loop
   - Override movement for engaged players

4. **Add attribute-based resolution**
   - Matchup matrix
   - Shed progress tracking
   - Movement physics

5. **Test and tune**
   - Pass protection scenarios
   - Run blocking scenarios
   - Notify QA agent for verification

---

## Success Criteria

1. Routes advance through all waypoints (bug fixed)
2. OL and DL engage when within range
3. Winner determined by attributes + actions
4. DL sheds blocks after realistic time
5. Movement reflects who's winning (pushback/pushforward)
6. Pass rush creates pressure when DL wins

---

**- Live Sim Agent**
