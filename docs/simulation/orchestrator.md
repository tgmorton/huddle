# Orchestrator - Game Loop & Phase Management

The Orchestrator (`orchestrator.py`) is the central coordinator for play execution. It manages the tick loop, coordinates AI brains, and handles phase transitions.

## Play Lifecycle

```
                    setup_play()
                         │
                         ▼
                    PRE_SNAP
                    (QB reads)
                         │
                    _do_snap()
                         │
                         ▼
                   DEVELOPMENT
                   (routes, pocket)
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     [throw]        [handoff]      [timeout]
          │              │              │
          ▼              ▼              ▼
     BALL_IN_AIR    RUN_ACTIVE     POST_PLAY
          │              │
     [catch]        [tackle]
          │              │
          ▼              ▼
     AFTER_CATCH    POST_PLAY
          │
     [tackle]
          │
          ▼
      POST_PLAY
```

## Phase Details

### PRE_SNAP

QB gets a chance to read the defense and call hot routes.

```python
def _do_pre_snap_reads(self):
    # Build WorldState for QB
    world = self._build_world_state(qb, dt=0.0)

    # Call QB brain
    decision = qb_brain(world)

    # Apply hot routes
    if decision.hot_routes:
        for player_id, new_route in decision.hot_routes.items():
            self._apply_hot_route(player, new_route)
```

**What Works**: Clean separation of pre-snap adjustments.

**Gaps**: No motion, no full audible system, no protection calls beyond MIKE ID.

### SNAP

Single tick that transitions from pre-snap to active play.

```python
def _do_snap(self):
    self.phase = PlayPhase.SNAP
    self.snap_time = self.clock.current_time
    self.event_bus.emit_simple(EventType.SNAP, ...)
    self.route_runner.start_all_routes(self.clock)
    self.coverage_system.start_coverage(self.clock)
    self.phase = PlayPhase.DEVELOPMENT
```

### DEVELOPMENT

Main phase where play develops:
- Routes run
- Coverage reacts
- QB reads and decides
- Blocking engagements

Key updates each tick:
1. `_update_qb_dropback_state()` - Track QB setting feet
2. `_resolve_blocks()` - OL/DL engagements
3. `_update_player()` - Brain decisions and movement
4. Check for throws, handoffs

### BALL_IN_AIR

Pass has been thrown, ball in flight.

```python
if self.ball.is_in_flight:
    self.ball.pos = self.ball.position_at_time(self.clock.current_time)
    if self.ball.has_arrived(self.clock.current_time):
        self._resolve_pass()
```

Ball flight uses linear interpolation with optional arc height for visualization.

### AFTER_CATCH

Receiver caught the ball, now a ballcarrier seeking YAC.

- Ballcarrier brain takes over
- Evasion moves available
- Tackle resolution active

### RUN_ACTIVE

Designated run or scramble with ballcarrier.

```python
if not self._handoff_complete and time >= self.config.handoff_timing:
    self._do_handoff()  # QB → RB
    self.phase = PlayPhase.RUN_ACTIVE
```

### POST_PLAY

Play complete. Compile results:
- Calculate yards gained
- Compute air yards and YAC
- Record to play history

## Tick Loop Structure

```python
def _update_tick(self, dt: float):
    # 1. Update QB timing
    if self.phase == PlayPhase.DEVELOPMENT:
        self._update_qb_dropback_state(dt)

    # 2. Resolve blocking FIRST (controls OL/DL positions)
    if self.phase in (DEVELOPMENT, RUN_ACTIVE, BALL_IN_AIR):
        self._resolve_blocks(dt)

    # 3. Update all players
    for player in self.offense + self.defense:
        if player.is_engaged:
            self._update_player_brain_only(player, dt)  # Brain runs, no movement
        else:
            self._update_player(player, dt)  # Full brain + movement

    # 4. Update ball in flight
    if self.ball.is_in_flight:
        self.ball.pos = self.ball.position_at_time(...)
        if self.ball.has_arrived(...):
            self._resolve_pass()

    # 5. Enforce lineman collisions
    self._enforce_lineman_collisions()

    # 6. Check tackles
    if self.ball.state == BallState.HELD:
        self._check_tackles()
        self._check_out_of_bounds()

    # 7. Handle scripted events (for testing)
    if self.config.throw_timing and time >= throw_timing:
        self._do_scripted_throw()
```

## Brain Coordination

### Execution Order

Each tick, brains execute in this order:
1. Offense players (not engaged)
2. Defense players (not engaged)
3. Engaged players (brain only, no movement)

**Issue**: Offense processes before defense, which may give slight advantage.

### Brain Registration

```python
# Register brains by player ID
orch.register_brain("QB1", qb_brain)
orch.register_brain("WR1", receiver_brain)

# Or by role (applies to all matching positions)
orch.register_brain("role:WR", receiver_brain)
orch.register_brain("ballcarrier", ballcarrier_brain)
```

### Auto-Switching

When a receiver catches the ball:
```python
# In _get_brain_for_player()
if player.has_ball and self.phase == PlayPhase.AFTER_CATCH:
    if "ballcarrier" in self._brains:
        return self._brains["ballcarrier"]
```

## QB Dropback State Machine

```
Start → DROPBACK → PLANTING → SET (ready to throw)
            │           │
            └───────────┴── (distance/time checks)
```

```python
def _update_qb_dropback_state(self, dt):
    # Check if QB reached target depth
    if not self._qb_reached_depth:
        distance_to_target = qb.pos.distance_to(self._dropback_target)
        if distance_to_target < 0.5:
            self._qb_reached_depth = True
            self._qb_set_start_time = self.clock.current_time
        return

    # Check if planting phase complete
    if not self._qb_is_set:
        time_planting = current_time - self._qb_set_start_time
        if time_planting >= self._required_set_time:
            self._qb_is_set = True
            self._qb_set_time = current_time
            self.event_bus.emit_simple(EventType.DROPBACK_COMPLETE, ...)
```

QB brain reads `world.qb_is_set` to know when throwing is allowed.

## Movement Type Speed Modifiers

```python
MOVE_TYPE_SPEED = {
    "sprint": 1.0,
    "run": 0.85,
    "dropback": 0.80,      # QB drop
    "backpedal": 0.55,     # Defensive backpedal
    "strafe": 0.65,
    "coast": 0.5,
}
```

## Immunity Systems

### Tackle Immunity

After breaking a tackle with an evasion move:
```python
if move_result.outcome == MoveOutcome.SUCCESS:
    self._tackle_immunity[player.id] = current_time + 0.3  # 6 ticks
```

### Shed Immunity

After DL sheds block:
```python
if result.outcome == BlockOutcome.DL_SHED:
    self._shed_immunity[dl.id] = current_time + 0.4
    self._ol_beaten[ol.id] = current_time + 0.4  # OL penalized
```

## PlayConfig

```python
@dataclass
class PlayConfig:
    # Routes (receiver_id -> route_type)
    routes: Dict[str, str]

    # Coverage
    man_assignments: Dict[str, str]  # defender -> target
    zone_assignments: Dict[str, str]  # defender -> zone

    # QB
    dropback_type: DropbackType = STANDARD

    # Run plays
    is_run_play: bool = False
    run_concept: Optional[str] = None
    handoff_timing: float = 0.6
    ball_carrier_id: Optional[str] = None

    # For testing
    throw_timing: Optional[float] = None
    throw_target: Optional[str] = None
```

## PlayResult

```python
@dataclass
class PlayResult:
    outcome: str          # complete, incomplete, sack, run, etc.
    yards_gained: float
    duration: float
    tick_count: int

    air_yards: float      # Pass distance
    yac: float            # Yards after catch

    events: List[Event]   # Full event log
```

## Honest Assessment

### What Works

1. **Clean WorldState/BrainDecision interface** - Brains are well-isolated
2. **Event-driven state changes** - EventBus cleanly handles throw/catch/tackle
3. **QB dropback timing** - Realistic set-and-throw mechanics

### Issues

1. **Phase Transition Logic Scattered**
   - Transitions happen in `_on_*` handlers, `_update_tick`, and `_resolve_*`
   - Should be centralized in a phase machine

2. **Brain Execution Order**
   - Offense always updates before defense
   - Could cause subtle timing advantages

3. **Underutilized Phases**
   - PRE_SNAP: Only hot routes, no motion/audibles
   - POST_PLAY: Just compiles results, no player reactions

4. **WorldState Overloaded**
   - Many optional fields for different roles
   - Could split into RoleContext sub-objects

5. **Scripted Throw Timing**
   - Still used for testing; should migrate to proper QB brain

### Recommended Improvements

1. Create explicit `PhaseStateMachine` class
2. Randomize or interleave offense/defense updates
3. Add motion and audible systems to PRE_SNAP
4. Split WorldState into base + role-specific contexts

## Key Components

| Concept | Location |
|---------|----------|
| Tick loop | `orchestrator.py` - `_update_tick()` method |
| Phase enum | `orchestrator.py` - `PlayPhase` class |
| WorldState | `orchestrator.py` - `WorldState` dataclass |
| QB dropback | `orchestrator.py` - `_update_qb_dropback_state()` |
| Block resolution | `orchestrator.py` - `_resolve_blocks()` |
| Tackle check | `orchestrator.py` - `_check_tackles()` |
| Sack detection | `orchestrator.py` - `_check_sack()` |

## See Also

- [AI_BRAINS.md](AI_BRAINS.md) - Brain implementations
- [RESOLUTION.md](RESOLUTION.md) - Blocking, tackling outcomes
- [EVENTS.md](EVENTS.md) - Event types and handlers
