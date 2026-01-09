# V2 Simulation System

Tick-based American football play simulator with emergent gameplay and attribute-driven outcomes.

## What It Does

V2 Sim executes individual football plays at 20 ticks per second (50ms per tick). Unlike scripted animations, outcomes emerge from the interaction of:

- **AI Brains**: Each position has decision-making logic
- **Physics**: Movement, acceleration, collisions
- **Resolution**: Blocking, tackling, catching outcomes
- **Variance**: Attribute-modulated randomness

A single play (snap to whistle) typically runs 100-200 ticks (2-5 seconds real-time, representing 5-10 seconds game-time).

## Quick Start

```python
from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig
from huddle.simulation.v2.core.entities import Player, Position, Vec2

# Create players
qb = Player(id="QB1", position=Position.QB, pos=Vec2(0, -5), has_ball=True)
wr = Player(id="WR1", position=Position.WR, pos=Vec2(20, 0))
cb = Player(id="CB1", position=Position.CB, pos=Vec2(18, 7))

# Configure play
config = PlayConfig(
    routes={"WR1": "slant"},
    man_assignments={"CB1": "WR1"},
    max_duration=5.0,
)

# Run simulation
orch = Orchestrator()
orch.setup_play([qb, wr], [cb], config)
result = orch.run()

print(result.format_summary())
# "Complete to WR1 for 8 yards (5 air + 3 YAC)"
```

## Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | System overview, directory structure, data flow |
| [orchestrator.md](orchestrator.md) | Game loop, phases, brain coordination |
| [brains/](brains/) | Position-specific AI decision making |
| [physics.md](physics.md) | Movement, spatial influence, body model |
| [resolution.md](resolution.md) | Blocking, tackling, evasion outcomes |
| [plays.md](plays.md) | Routes, formations, defensive schemes |
| [events.md](events.md) | Event bus architecture, event types |
| [variance.md](variance.md) | Randomness, pressure effects |
| [historical.md](historical.md) | Multi-season league history generator |
| [improvements.md](improvements.md) | Gaps and opportunities for improvement |
| [roadmap.md](roadmap.md) | Foundational roadmap and sequencing |

## Design Principles

### Emergence Over Scripting

Plays aren't animated - they emerge from independent AI decisions. A slant route completion happens because:
1. WR brain runs the route (separation-focused)
2. CB brain reacts (man coverage logic)
3. QB brain reads coverage (completion-first philosophy)
4. Physics calculates ball flight
5. Resolution determines catch outcome

### Attribute-Driven Outcomes

Player attributes (0-99 scale) affect every decision and resolution:
- **Speed/Acceleration**: Movement solver limits
- **Route Running**: Break crispness, separation
- **Throw Accuracy**: Ball placement variance
- **Awareness**: Read speed, reaction time

### Honest Simulation

The system aims for realistic outcomes, not user-pleasing ones:
- Fast CBs catch slow WRs
- Pressured QBs make mistakes (Easterbrook Hypothesis)
- Good blocking creates running lanes
- Mismatches matter

## Simulation vs Other Systems

| System | Purpose | Location |
|--------|---------|----------|
| **V2 Sim** | Detailed play execution with AI brains | `huddle/simulation/v2/` |
| **Historical Sim** | Multi-season league history generator | `huddle/core/simulation/historical_sim.py` |
| **Season Sim** | Full season simulation with games | `huddle/simulation/season.py` |
| **Sandbox** | Quick prototyping and testing | `huddle/simulation/sandbox/` |
| **Original** | Legacy system (deprecated) | `huddle/simulation/` (root) |

V2 Sim is the production system for game simulation. Historical Sim is used to generate league state before franchise mode starts.

## Key Files

```
huddle/simulation/v2/
├── orchestrator.py          # Main entry point
├── game_state.py            # Play history, game situation
├── export.py                # Frame export for visualization
├── ai/                      # Position brains
├── core/                    # Entities, vectors, events
├── physics/                 # Movement, spatial
├── resolution/              # Outcomes (block, tackle, move)
├── plays/                   # Routes, concepts, schemes
├── systems/                 # Coverage, passing, routes
└── testing/                 # Scenario runner
```

## Current State

V2 Sim handles:
- Pass plays (routes, coverage, throws, catches)
- Run plays (handoffs, blocking, ballcarrier decisions)
- Blocking engagements (OL vs DL, shed mechanics)
- Tackle resolution (missed/broken tackles, gang tackles)
- Evasion moves (juke, spin, truck)

See [improvements.md](improvements.md) for what's missing or incomplete.
