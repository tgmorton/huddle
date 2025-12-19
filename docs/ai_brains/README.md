# AI Brains Documentation

This folder contains comprehensive design documentation for each AI brain in the v2 simulation system. These documents serve as implementation guides for the Python brain classes in `huddle/simulation/v2/ai/`.

---

## Overview

The AI brain system separates **decision-making** from **physics execution**. Each brain observes the world state, makes a decision, and emits an intention. The orchestrator then executes that intention through the physics and resolution systems.

```
WorldState → Brain.decide() → BrainDecision → Orchestrator → Physics/Resolution
```

### Design Principles

1. **Brains observe, they don't modify** - Brains read WorldState but never mutate it directly
2. **One decision per tick** - Each brain returns exactly one BrainDecision per tick
3. **Stateful across ticks** - Brains maintain internal state (read index, pressure level, etc.)
4. **Attribute-driven** - Player attributes influence thresholds and capabilities, not tree structure
5. **Position-agnostic where possible** - Ballcarrier brain works for RB, WR after catch, QB scramble, etc.

---

## Brain Hierarchy

```
                    ┌─────────────────┐
                    │   Orchestrator   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │ Offense │        │ Defense │        │ Special │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
    ┌────┴────────┐    ┌───┴────────┐         │
    │             │    │            │         │
┌───▼──┐ ┌───────▼┐ ┌─▼───┐ ┌─────▼┐    ┌───▼───┐
│  QB  │ │Receiver│ │ DL  │ │  LB  │    │Return │
└──┬───┘ └───┬────┘ └──┬──┘ └───┬──┘    │ Brain │
   │         │         │        │       └───────┘
   ▼         ▼         ▼        ▼
┌──────────────────────────────────┐
│       Ballcarrier Brain          │ ← Universal, any player with ball
└──────────────────────────────────┘
```

---

## Interface Contract

All brains implement the same interface:

### BrainDecision (Output)

| Field | Type | Description |
|-------|------|-------------|
| `action` | str | What to do (e.g., "throw", "run_to", "zone_drop") |
| `target_pos` | Optional[Vec2] | Where to go (for movement actions) |
| `target_id` | Optional[str] | Who to target (receiver, defender, etc.) |
| `urgency` | float | 0-1 scale, affects speed/commitment |
| `reasoning` | str | Human-readable explanation for debugging |
| `data` | dict | Action-specific data (move type, throw type, etc.) |

### Brain Base Class

```
Brain.decide(player, world_state, clock, dt) → BrainDecision
```

- `player`: The player this brain controls
- `world_state`: Snapshot of all players, ball, field, assignments
- `clock`: Time information (time since snap, play clock, etc.)
- `dt`: Time delta since last tick

---

## WorldState (Input)

Each brain receives a WorldState snapshot containing:

| Field | Type | Description |
|-------|------|-------------|
| `offense` | List[Player] | All offensive players |
| `defense` | List[Player] | All defensive players |
| `ballcarrier` | Optional[Player] | Current ballcarrier (if any) |
| `ball` | Ball | Ball state and position |
| `field` | Field | Field geometry, LOS, bounds |
| `play_phase` | PlayPhase | PRE_SNAP, DEVELOPMENT, POST_RESOLUTION |
| `spatial` | SpatialQuery | Pre-computed spatial queries |
| `route_assignments` | Dict[str, RouteAssignment] | Receiver route info (keyed by player ID) |
| `coverage_assignments` | Dict[str, CoverageAssignment] | Defender coverage info |

### SpatialQuery Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `find_nearest(pos, team, n)` | List[Player] | N nearest players from team |
| `find_in_radius(pos, radius, team)` | List[Player] | All players within radius |
| `find_threats(ballcarrier, horizon)` | List[ThreatVector] | Defenders who can reach ballcarrier |
| `find_holes(los)` | List[Hole] | Gaps in the defensive line |
| `get_influence_at(pos)` | float | Net influence (-1 to 1, defense to offense) |
| `get_open_space(pos, direction)` | float | Yards of open space in direction |

---

## Brain Documents

### Tier 1: Core Brains

| Document | Description | Priority |
|----------|-------------|----------|
| [qb_brain.md](qb_brain.md) | Read progression, pressure response, throw/scramble decisions | 1 |
| [ballcarrier_brain.md](ballcarrier_brain.md) | Vision, hole finding, move selection - any player with ball | 2 |
| [lb_brain.md](lb_brain.md) | Run/pass read, gap fit, zone/man coverage, blitz | 3 |
| [db_brain.md](db_brain.md) | Man/zone coverage, ball-hawking, run support | 4 |

### Tier 2: Supporting Brains

| Document | Description |
|----------|-------------|
| [receiver_brain.md](receiver_brain.md) | Route execution, release moves, blocking |
| [rusher_brain.md](rusher_brain.md) | RB path selection, blocking, route running |
| [dl_brain.md](dl_brain.md) | Pass rush moves, run fits, gap control |
| [ol_brain.md](ol_brain.md) | Pass protection, run blocking, communication |

### Tier 3: Shared Concepts

| Document | Description |
|----------|-------------|
| [shared_concepts.md](shared_concepts.md) | Pursuit angles, tackle geometry, spatial awareness |

---

## Player Attributes

All attributes are on a 0-99 scale:
- 60-70: Below average NFL player
- 70-80: Average NFL starter
- 80-90: Above average / Pro Bowl caliber
- 90+: Elite / All-Pro

### Physical Attributes

| Attribute | Description | Primary Users |
|-----------|-------------|---------------|
| `speed` | Top speed | All |
| `acceleration` | Time to top speed | All |
| `agility` | Change of direction | Skill positions, DBs |
| `strength` | Contact outcomes | Linemen, ballcarriers |

### Mental Attributes

| Attribute | Description | Primary Users |
|-----------|-------------|---------------|
| `awareness` | Reaction time, reads | All |
| `vision` | Field vision (ballcarrier) | RB, WR after catch |
| `play_recognition` | Run/pass read speed | LB, DB, OL |

### Position-Specific Attributes

| Attribute | Description | Primary Users |
|-----------|-------------|---------------|
| `route_running` | Route crispness | WR, TE, RB |
| `catching` | Catch probability | WR, TE, RB |
| `throw_power` | Arm strength | QB |
| `throw_accuracy` | Accuracy | QB |
| `tackling` | Tackle success | Defense |
| `man_coverage` | Man coverage ability | DB, LB |
| `zone_coverage` | Zone coverage ability | DB, LB |
| `press` | Press technique | CB |
| `block_power` | Drive blocking | OL, TE |
| `block_finesse` | Pass pro technique | OL, TE |
| `pass_rush` | Rush move effectiveness | DL |
| `elusiveness` | Tackle avoidance | Skill positions |

---

## Play Phases

Brains behave differently based on play phase:

### PRE_SNAP
- QB: Read defense, consider audibles
- Receivers: Hold alignment
- Defense: Disguise coverage, adjust to motion

### DEVELOPMENT
- QB: Execute dropback, read progression
- Receivers: Run routes
- OL: Execute protection scheme
- Defense: Execute coverage/rush assignments

### POST_RESOLUTION (ball caught or run game active)
- Ballcarrier brain takes over for whoever has ball
- Defense: Pursuit mode
- Offense: Block for ballcarrier

---

## Event Integration

Brains can emit requests for events (executed by orchestrator):

| Event | Triggered By | Data |
|-------|--------------|------|
| `THROW` | QB Brain | receiver_id, throw_type, target_pos |
| `HANDOFF` | QB/RB coordination | receiver_id |
| `SCRAMBLE_COMMIT` | QB Brain | direction |
| `ROUTE_BREAK` | Receiver Brain | break_direction |
| `COVERAGE_TRIGGER` | DB Brain | target_id, action |
| `BLITZ_COMMIT` | LB Brain | gap, timing |

---

## Debugging

Each brain should populate `BrainDecision.reasoning` with human-readable explanations:

```
"Read 2 of 4: Z receiver open (3.2 yd separation), throwing"
"Cutback lane open (2.1 yd width), 1 second-level defender"
"Run diagnosed (OL low hat), fitting B-gap"
"Ball to my receiver, trailing by 1.8 yards, breaking on ball"
```

This enables replay analysis and decision visualization.

---

## Implementation Order

1. **QBBrain** - Most complex, establishes patterns
2. **BallcarrierBrain** - Universal applicability
3. **LBBrain** - Key defensive brain
4. **DBBrain** - Coverage decisions
5. **ReceiverBrain** - Route execution
6. **RusherBrain** - RB decisions
7. **DLBrain** - Pass rush
8. **OLBrain** - Protection

Each brain builds on patterns established by earlier implementations.
