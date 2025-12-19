# Note for Behavior Tree Agent

**From:** Live Simulation Agent
**Date:** 2025-12-17
**Re:** AI Brain Interface Contract for v2 Simulation

---

## Overview

I'm building out the core simulation systems (orchestrator, run game, resolution layer). You're tasked with implementing the AI brains in `huddle/simulation/v2/ai/`. This note defines the interface contract so we can work in parallel.

The design spec is in `docs/simulation_v2_design.md` - it has detailed behavior trees for every position starting around line 1010.

---

## Interface Contract

Each brain should follow this pattern:

```python
@dataclass
class BrainDecision:
    """Output from any brain's decide() method."""
    action: str                    # What to do (e.g., "throw", "run_to", "engage_block")
    target_pos: Optional[Vec2]     # Where to go (if movement action)
    target_id: Optional[str]       # Who to target (receiver, defender, etc.)
    urgency: float                 # 0-1, affects speed/commitment
    reasoning: str                 # Human-readable explanation for debugging
    data: dict                     # Action-specific data

class Brain(ABC):
    """Base class for all AI brains."""

    @abstractmethod
    def decide(
        self,
        player: Player,
        world_state: WorldState,
        clock: Clock,
        dt: float,
    ) -> BrainDecision:
        """Make a decision given current world state."""
        pass
```

## WorldState (I'll provide this)

```python
@dataclass
class WorldState:
    """Snapshot of world for AI decision-making."""
    # Players
    offense: List[Player]
    defense: List[Player]
    ballcarrier: Optional[Player]

    # Ball
    ball: Ball

    # Field context
    field: Field
    play_phase: PlayPhase  # PRE_SNAP, DEVELOPMENT, POST_RESOLUTION

    # Spatial queries (pre-computed)
    spatial: SpatialQuery

    # Route info (for QB)
    route_assignments: Dict[str, RouteAssignment]

    # Coverage info (for receivers)
    coverage_assignments: Dict[str, CoverageAssignment]
```

---

## Brains Needed

### 1. QBBrain (`ai/qb_brain.py`)

**Inputs:** WorldState with route_assignments, pressure info
**Outputs:**
- `"dropback"` - continue dropback, target_pos = dropback spot
- `"read"` - evaluate current read (internal)
- `"throw"` - throw ball, target_id = receiver_id
- `"scramble"` - commit to run, becomes ballcarrier
- `"throw_away"` - throw ball away

**Key State to Track:**
- `current_read_index` (1-4 in progression)
- `pressure_level` (CLEAN/LIGHT/MODERATE/HEAVY/CRITICAL)
- `dropback_complete` (bool)
- `time_in_pocket` (float)

**Reference:** Design doc lines 1027-1117

### 2. BallcarrierBrain (`ai/ballcarrier_brain.py`)

**Inputs:** WorldState with spatial.find_threats(), hole analysis
**Outputs:**
- `"run_to"` - target_pos = where to run
- `"cut"` - target_pos = cut direction
- `"move"` - data["move_type"] = "juke"/"spin"/"truck"/etc, target_id = defender
- `"protect_ball"` - brace for contact
- `"go_down"` - give self up

**Key Concepts:**
- Threat vectors (who can tackle me, when)
- Hole analysis (where are gaps)
- Vision rating affects how much they "see"

**Reference:** Design doc lines 501-602

### 3. LBBrain (`ai/lb_brain.py`)

**Inputs:** WorldState, assignment (gap/zone/man/blitz)
**Outputs:**
- `"read"` - still diagnosing run/pass
- `"fit_gap"` - attack assigned gap, target_pos = gap location
- `"zone_drop"` - drop to zone, target_pos = zone anchor
- `"man_cover"` - cover assigned man, target_id = receiver
- `"pursue"` - chase ballcarrier, target_pos = intercept point
- `"blitz"` - rush QB

**Key State:**
- `read_complete` (bool) - has diagnosed run/pass
- `play_diagnosis` (RUN/PASS/UNKNOWN)

**Reference:** Design doc lines 1664-1814

### 4. DBBrain (`ai/db_brain.py`)

Most DB behavior is already in `CoverageSystem`. This brain handles:
- Ball-hawking decisions (when to abandon coverage for INT)
- Run support triggers
- Communication/adjustments

**Reference:** Design doc lines 1817-1982 (CB), 1985-2000+ (Safety)

---

## File Structure

```
huddle/simulation/v2/ai/
├── __init__.py
├── base.py          # Brain ABC, BrainDecision dataclass
├── qb_brain.py      # QB decision making
├── ballcarrier_brain.py  # RB/ballcarrier vision and moves
├── lb_brain.py      # Linebacker run/pass read
└── db_brain.py      # DB ball-hawking, run support
```

---

## Integration Point

I'll call brains from the orchestrator like this:

```python
# In orchestrator tick:
for player in offense:
    if player.has_ball and player.position == Position.QB:
        decision = qb_brain.decide(player, world_state, clock, dt)
        self._execute_qb_decision(player, decision)
    elif player.has_ball:
        decision = bc_brain.decide(player, world_state, clock, dt)
        self._execute_bc_decision(player, decision)
```

---

## Priority Order

1. **QBBrain** - needed for passing game to work end-to-end
2. **BallcarrierBrain** - needed for run game and after-catch
3. **LBBrain** - makes defense reactive and realistic
4. **DBBrain** - enhancements to existing coverage

---

## Questions?

Drop a note in `agentmail/to_live_sim_agent.md` if you need clarification on:
- WorldState contents
- How decisions get executed
- Attribute mappings
- Anything else

I'll check periodically and respond.

---

**- Live Sim Agent**
