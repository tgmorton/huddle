# Event System

Pub/sub event bus for simulation state changes, logging, and inter-system communication.

## EventBus (`core/events.py`)

### Usage

```python
from huddle.simulation.v2.core.events import EventBus, EventType, Event

# Create bus
bus = EventBus()

# Subscribe to specific event
bus.subscribe(EventType.CATCH, on_catch_handler)

# Subscribe to all events
bus.subscribe_all(logging_handler)

# Emit event
bus.emit(Event(
    type=EventType.CATCH,
    tick=50,
    time=2.5,
    player_id="WR1",
    description="8-yard catch over the middle"
))

# Convenience method
bus.emit_simple(EventType.THROW, tick=45, time=2.25,
                player_id="QB1", target_id="WR1",
                description="Quick slant", air_yards=8)
```

### Event Structure

```python
@dataclass
class Event:
    type: EventType           # What happened
    tick: int                 # When (tick number)
    time: float               # When (seconds)
    player_id: Optional[str]  # Primary player
    target_id: Optional[str]  # Secondary player
    data: dict                # Additional event-specific data
    description: str          # Human-readable
```

---

## Event Types

### Play Lifecycle

| Event | Description | Data |
|-------|-------------|------|
| PLAY_START | Play setup complete | formation, concept |
| SNAP | Ball snapped | time |
| HANDOFF | Handoff complete | from_id, to_id |
| THROW | Pass thrown | target_id, air_yards, throw_type |
| CATCH | Pass completed | yards, yac |
| INCOMPLETE | Pass incomplete | reason (dropped, defended, overthrown) |
| INTERCEPTION | Pass intercepted | defender_id |
| FUMBLE | Ball fumbled | cause, recovery_team |
| TACKLE | Ballcarrier tackled | tackler_id, yards_gained |
| OUT_OF_BOUNDS | Runner went OOB | position |
| TOUCHDOWN | Touchdown scored | yards |
| SAFETY | Safety recorded | - |
| PLAY_END | Play complete | result, duration |

### Movement/Position

| Event | Description | Data |
|-------|-------------|------|
| ROUTE_BREAK | Receiver broke on route | route_type, phase |
| ROUTE_COMPLETE | Route finished | separation |
| PLAYER_MOVED | Significant position change | from_pos, to_pos |
| CROSSED_LOS | Player crossed line of scrimmage | direction |
| ENTERED_ENDZONE | Player entered endzone | - |
| WENT_OUT_OF_BOUNDS | Player stepped out | position |

### QB Events

| Event | Description | Data |
|-------|-------------|------|
| HOT_ROUTE | Hot route called | receiver_id, new_route |
| PROTECTION_CALL | Protection adjustment | mike_id, slide_dir |
| DROPBACK_COMPLETE | QB set in pocket | time, depth |
| READ_ADVANCED | Moved to next read | from_read, to_read |
| PRESSURE_LEVEL_CHANGED | Pressure increased | level, free_rusher |
| SCRAMBLE_INITIATED | QB scrambling | direction |
| THROW_DECISION | Decided to throw | target, open_rating |
| SACK | QB sacked | rusher_id, yards_lost |

### Blocking/Rush

| Event | Description | Data |
|-------|-------------|------|
| BLOCK_ENGAGED | OL/DL engaged | ol_id, dl_id |
| BLOCK_SHED | DL shed block | dl_id, shed_time |
| BLOCK_SUSTAINED | OL sustained block | duration |
| RUSHER_FREE | Rusher has free path to QB | rusher_id, distance |

### Coverage

| Event | Description | Data |
|-------|-------------|------|
| COVERAGE_BROKEN | Receiver got open | separation, defender_id |
| SEPARATION_CREATED | Receiver created space | yards, route_phase |
| BALL_HAWK | Defender tracking ball | defender_id |
| COVERAGE_BREAK_REACTION | DB broke on ball | reaction_time |
| ZONE_TRIGGER | Zone triggered by receiver | zone, receiver_id |
| ZONE_HANDOFF | Receiver passed between zones | from_zone, to_zone |

### Ballcarrier

| Event | Description | Data |
|-------|-------------|------|
| HOLE_HIT | Runner hit designed hole | gap, blocking |
| CUTBACK | Runner cut back | direction |
| BOUNCE_OUTSIDE | Runner bounced to edge | side |
| MOVE_ATTEMPTED | Evasion move attempted | move_type |
| MOVE_SUCCESS | Move succeeded | move_type, yards_gained |
| MOVE_FAILED | Move failed | move_type |
| YARDS_AFTER_CONTACT | YAC accumulated | yards, contacts |

### Encounters

| Event | Description | Data |
|-------|-------------|------|
| TACKLE_ATTEMPT | Tackle attempted | tackler_id, tackle_type |
| MISSED_TACKLE | Tackle missed | tackler_id, reason |
| CATCH_CONTEST | Contested catch | defender_id, result |

### AI/Decision

| Event | Description | Data |
|-------|-------------|------|
| DECISION_MADE | Brain made decision | player_id, decision, reason |
| BEHAVIOR_TREE_EVAL | BT node evaluated | node, result |

---

## Event Handling

### Handler Registration

```python
# Type-specific
def on_catch(event: Event):
    print(f"{event.player_id} caught for {event.data.get('yards')} yards")

bus.subscribe(EventType.CATCH, on_catch)

# All events
def log_event(event: Event):
    logger.info(str(event))

bus.subscribe_all(log_event)
```

### Unsubscribe

```python
bus.unsubscribe(EventType.CATCH, on_catch)
```

### Event History

```python
# Get all events
history = bus.history

# Get by type
throws = bus.get_events_by_type(EventType.THROW)

# Get for player
qb_events = bus.get_events_for_player("QB1")

# Format for logging
print(bus.format_history(last_n=10))
print(bus.format_history_detailed())

# Clear
bus.clear_history()
```

### Recording Control

```python
# Disable recording (for performance)
bus.set_recording(False)

# Re-enable
bus.set_recording(True)
```

---

## Event Flow Examples

### Pass Play

```
PLAY_START
SNAP
ROUTE_BREAK (WR1, slant)
DROPBACK_COMPLETE (QB1)
READ_ADVANCED (1 -> 2)
SEPARATION_CREATED (WR1, 3.2 yards)
THROW_DECISION (WR1, open)
THROW (QB1 -> WR1, 8 air yards)
CATCH (WR1, 8 yards)
TACKLE_ATTEMPT (CB1)
TACKLE (CB1, 11 total yards)
PLAY_END (complete, 11 yards)
```

### Sack

```
PLAY_START
SNAP
BLOCK_ENGAGED (LT1, DE1)
DROPBACK_COMPLETE (QB1)
PRESSURE_LEVEL_CHANGED (moderate)
BLOCK_SHED (DE1)
RUSHER_FREE (DE1, 3 yards)
PRESSURE_LEVEL_CHANGED (critical)
SACK (DE1, -7 yards)
PLAY_END (sack, -7 yards)
```

---

## Honest Assessment

### What Works

1. **Clean Pub/Sub**: Simple subscribe/emit pattern
2. **Rich Event Types**: 40+ event types cover most situations
3. **History Tracking**: Can replay and analyze events
4. **Flexible Data**: Additional data via dict

### Issues

1. **Fire and Forget**
   - No acknowledgment pattern
   - No error handling on handler exceptions
   - Can't cancel or modify events

2. **No Event Replay**
   - No built-in replay/debugging support
   - Can't step through events

3. **Some Redundancy**
   - TACKLE and PLAY_END both indicate tackle
   - THROW and CATCH could be combined with outcomes

4. **Missing Events**
   - No penalty events
   - No formation/motion events
   - No pre-snap read events

### Recommended Improvements

1. Add event acknowledgment for critical events
2. Build replay/debugging tool using event history
3. Add penalty and formation events
4. Consider event batching for performance

---

## Key Files

| Component | Location |
|-----------|----------|
| EventBus | `core/events.py:167-278` |
| EventType | `core/events.py:15-98` |
| Event | `core/events.py:100-161` |

## See Also

- [ORCHESTRATOR.md](ORCHESTRATOR.md) - Event emission points
- [AI_BRAINS.md](AI_BRAINS.md) - Brain decision events
