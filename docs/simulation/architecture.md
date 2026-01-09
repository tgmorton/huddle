# V2 Simulation Architecture

## System Overview

V2 Sim is a tick-based play simulator running at 20 ticks per second. Each tick:

1. Updates QB dropback state
2. Resolves blocking engagements
3. Queries AI brains for decisions
4. Applies movement
5. Checks for tackles/catches
6. Emits events

### Design Philosophy

| Principle | Implementation |
|-----------|----------------|
| **Emergence** | Outcomes emerge from AI decisions, not scripted |
| **Attribute-driven** | Player ratings affect every calculation |
| **Physics stays pure** | Movement is deterministic; human factors add variance |
| **Event-driven** | Systems communicate via EventBus |

## Directory Structure

```
huddle/simulation/v2/
├── orchestrator.py          # Main simulation loop (~2000 lines)
├── game_state.py            # PlayHistory, GameSituation
├── export.py                # Frame export for visualization
│
├── ai/                      # Position-specific AI brains
│   ├── qb_brain.py          # QB decision making
│   ├── receiver_brain.py    # WR/TE route running
│   ├── ballcarrier_brain.py # RB/carrier decisions
│   ├── ol_brain.py          # Offensive line
│   ├── db_brain.py          # Cornerbacks, safeties
│   ├── lb_brain.py          # Linebackers
│   ├── dl_brain.py          # Defensive line
│   ├── rusher_brain.py      # Pass rush
│   └── shared/              # Shared utilities (perception)
│
├── core/                    # Core data structures
│   ├── entities.py          # Player, Ball dataclasses
│   ├── vec2.py              # 2D vector math
│   ├── events.py            # EventBus, Event types
│   ├── variance.py          # Attribute-modulated randomness
│   ├── field.py             # Field geometry
│   ├── clock.py             # Simulation clock
│   └── trace.py             # Debug tracing
│
├── physics/                 # Movement and collisions
│   ├── movement.py          # MovementSolver, profiles
│   ├── body.py              # BodyModel (hitboxes)
│   └── spatial.py           # Influence zones
│
├── resolution/              # Outcome determination
│   ├── blocking.py          # OL/DL engagements
│   ├── tackle.py            # Tackle attempts
│   └── move.py              # Evasion moves (juke, spin)
│
├── plays/                   # Play definitions
│   ├── routes.py            # Route types and waypoints
│   ├── concepts.py          # Pass concepts
│   ├── schemes.py           # Defensive schemes
│   └── run_concepts.py      # Run blocking schemes
│
├── systems/                 # Game systems
│   ├── route_runner.py      # Route execution
│   ├── coverage.py          # Coverage assignments
│   ├── passing.py           # Throw/catch resolution
│   └── pressure.py          # Pressure tracking
│
└── testing/                 # Test infrastructure
    └── scenario_runner.py   # Run predefined scenarios
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                             │
│                                                                  │
│  setup_play(offense, defense, config)                           │
│       ↓                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Tick Loop                              │   │
│  │                                                           │   │
│  │  1. Update QB dropback state                             │   │
│  │  2. Resolve blocks (OL/DL)                               │   │
│  │  3. For each player:                                     │   │
│  │       ├─ Build WorldState                                │   │
│  │       ├─ Call brain (if registered)                      │   │
│  │       └─ Apply BrainDecision                             │   │
│  │  4. Update ball position (if in flight)                  │   │
│  │  5. Check tackles                                        │   │
│  │  6. Check phase transitions                              │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│       ↓                                                          │
│  compile_result() → PlayResult                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Abstractions

### WorldState

What AI brains see each tick. Provides a player's view of the game:

```python
@dataclass
class WorldState:
    me: Player              # The player this brain controls
    teammates: List[PlayerView]
    opponents: List[PlayerView]
    ball: BallView
    phase: PlayPhase

    # Assignment
    assignment: str         # "route:slant", "man:WR1", etc.
    route_target: Vec2      # Current waypoint

    # Context
    threats: List[PlayerView]  # Nearby opponents
    time_since_snap: float
    qb_is_set: bool
```

### BrainDecision

What AI brains return:

```python
@dataclass
class BrainDecision:
    move_target: Vec2           # Where to go
    move_type: str              # "sprint", "backpedal", etc.
    intent: str                 # "route", "coverage", "pursuit"
    action: Optional[str]       # "throw", "juke", etc.
    target_id: Optional[str]    # For actions targeting a player
```

### Vec2

2D vector for positions and velocities:

```python
pos = Vec2(10.5, 25.0)
vel = Vec2(3.0, 4.0)
distance = pos.distance_to(other_pos)
direction = (target - pos).normalized()
```

### EventBus

Pub/sub for simulation events:

```python
# Subscribe
event_bus.subscribe(EventType.CATCH, on_catch)

# Emit
event_bus.emit_simple(EventType.THROW, tick=50, time=2.5,
                      player_id="QB1", description="Pass to WR1")
```

### MovementProfile

Defines movement capabilities derived from attributes:

```python
profile = MovementProfile.from_attributes(
    speed=92,      # → max_speed ~7.2 yds/s
    acceleration=88,
    agility=90     # → cut_retention ~80%
)
```

## Phase State Machine

```
SETUP → PRE_SNAP → SNAP → DEVELOPMENT →
                                    ├→ BALL_IN_AIR → AFTER_CATCH → POST_PLAY
                                    └→ RUN_ACTIVE → POST_PLAY
```

| Phase | Description |
|-------|-------------|
| SETUP | Configuring play (routes, coverages) |
| PRE_SNAP | Players at alignments, QB reads |
| SNAP | Ball snapped (single tick) |
| DEVELOPMENT | Routes running, pocket forming |
| BALL_IN_AIR | Pass thrown, awaiting resolution |
| AFTER_CATCH | Receiver caught, running for YAC |
| RUN_ACTIVE | Ballcarrier has ball (run/scramble) |
| POST_PLAY | Play complete, results compiled |

## Component Relationships

```
Orchestrator
    ├── Clock (tick timing)
    ├── EventBus (event pub/sub)
    ├── Field (geometry)
    │
    ├── Systems
    │   ├── RouteRunner (route execution)
    │   ├── CoverageSystem (man/zone)
    │   └── PassingSystem (throws/catches)
    │
    ├── Resolvers
    │   ├── BlockResolver (OL/DL)
    │   ├── TackleResolver (tackle attempts)
    │   └── MoveResolver (evasion moves)
    │
    ├── MovementSolver (all movement)
    │
    └── AI Brains (registered per-player)
```

## Variance System

Three layers of attribute-modulated noise:

| Layer | Affects | Example |
|-------|---------|---------|
| **Recognition** | Reaction time, reads | DB break on ball |
| **Execution** | Timing, precision | Route break crispness |
| **Decision** | Choice quality | QB target selection |

```python
# Recognition delay with variance
actual_delay = recognition_delay(
    base_delay=0.2,      # Base reaction time
    awareness=85,        # Higher = tighter variance
    pressure=0.3         # Pressure widens variance
)
```

Deterministic mode disables all variance for debugging.

## Trace System

Debug tracing for brain decisions (`core/trace.py`):

```python
from huddle.simulation.v2.core.trace import trace

# In any brain
trace(player.id, "read_progression", f"Checking {receiver.name}: {separation:.1f}yd separation")
trace(player.id, "decision", f"Throwing to {target.name} - best window")
```

Traces are collected per-tick and can be:
- Displayed in SimAnalyzer UI
- Exported for replay analysis
- Filtered by player or category

Categories: `read_progression`, `decision`, `movement`, `coverage`, `blocking`

## Honest Assessment

### Architectural Issues

1. **Brain-Resolution Overlap**: Some resolution logic leaks into brains (e.g., tackle immunity after moves)

2. **Phase Transitions Scattered**: Transition conditions are checked in multiple places (`_update_tick`, `_on_*` handlers)

3. **Missing Abstraction**: No clear "rules engine" separate from physics - rules and movement intermingled in orchestrator

4. **WorldState Bloat**: WorldState has grown to include many optional fields; could benefit from sub-views per role

### What Works Well

1. **Event-Driven Architecture**: EventBus enables clean system communication and logging

2. **Variance System**: Three-layer approach provides realistic human factors

3. **MovementSolver**: Single source of truth for all movement calculations

4. **Brain Interface**: Clean WorldState → BrainDecision pattern allows independent brain development

## See Also

- [ORCHESTRATOR.md](ORCHESTRATOR.md) - Game loop details
- [AI_BRAINS.md](AI_BRAINS.md) - Brain implementations
- [PHYSICS.md](PHYSICS.md) - Movement system
- [EVENTS.md](EVENTS.md) - Event types
