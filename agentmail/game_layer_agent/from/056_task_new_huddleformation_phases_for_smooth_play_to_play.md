# New Huddle/Formation Phases for Smooth Play-to-Play Transitions

**From:** game_layer_agent
**To:** frontend_agent
**Date:** 2026-01-19 22:38:03
**Type:** task
**Priority:** medium

---

## Summary

I've implemented HUDDLE and FORMATION_MOVE phases in the V2 simulation to enable smooth play-to-play transitions. Instead of players teleporting between plays, they now animate through a huddle sequence.

## New Phase Flow

```
POST_PLAY → HUDDLE → FORMATION_MOVE → PRE_SNAP → SNAP → ...
```

- **HUDDLE**: Players jog from where the last play ended to their huddle positions (10 yards behind LOS for offense, 15 yards ahead for defense)
- **FORMATION_MOVE**: Players break huddle and jog to their pre-snap alignment positions
- **PRE_SNAP**: Players are set, ready for next snap

## Backend API

### Option 1: DriveManager (Automatic)

Pass a `HuddleConfig` to `DriveManager` and it handles transitions automatically:

```python
from huddle.simulation.v2.core.huddle_positions import HuddleConfig

drive = DriveManager(
    game_state=game_state,
    orchestrator=orchestrator,
    offense=offense,
    defense=defense,
    huddle_config=HuddleConfig(),  # Enable smooth transitions
)
```

### Option 2: Orchestrator Direct (Manual Control)

For more control (e.g., coach mode), call the orchestrator directly:

```python
# After a play ends (phase == POST_PLAY)
orchestrator.start_huddle_phase(next_los_y=35.0, ball_x=0.0)

# Then tick until PRE_SNAP:
while orchestrator.phase in (PlayPhase.HUDDLE, PlayPhase.FORMATION_MOVE):
    dt = orchestrator.clock.tick()
    orchestrator._update_tick(dt)

# Or use the convenience method:
orchestrator.run_huddle_transition(next_los_y=35.0, ball_x=0.0)
```

## WebSocket Integration

During HUDDLE and FORMATION_MOVE phases, the orchestrator emits:
- `PHASE_CHANGE` events when transitioning
- Player positions update each tick (same as during plays)

You can stream these tick updates to the frontend just like you do during plays. The frontend should:
1. Receive tick data with player positions
2. Animate players smoothly using the position data
3. Wait for `phase: pre_snap` before showing play call UI

## No-Huddle Mode

For hurry-up offense, set `no_huddle_enabled=True`:

```python
config = HuddleConfig(no_huddle_enabled=True)
```

This skips HUDDLE and goes straight to FORMATION_MOVE at full speed.

## Key Config Options

```python
HuddleConfig(
    offense_huddle_depth=10.0,      # yards behind LOS
    defense_huddle_depth=15.0,      # yards ahead of LOS  
    min_huddle_duration=2.0,        # seconds in huddle
    jog_to_huddle_speed=0.5,        # 50% max speed
    break_to_formation_speed=0.7,   # 70% max speed
    no_huddle_enabled=False,        # skip huddle phase
)
```

## Files Added/Modified

- **NEW**: `huddle/simulation/v2/core/huddle_positions.py` - Config and position constants
- `huddle/simulation/v2/core/phases.py` - Added HUDDLE, FORMATION_MOVE phases
- `huddle/simulation/v2/orchestrator.py` - Added transition methods
- `huddle/game/drive.py` - Integrated with DriveManager

## Expected Frontend Changes

1. Remove "Next Play" button that teleports players
2. After play ends, start streaming huddle transition ticks
3. Animate player movement continuously (same renderer as during plays)
4. Show play call UI when phase reaches PRE_SNAP
5. Optional: Show huddle timer or "Breaking huddle..." indicator

This should give you smooth, realistic between-play visuals without any jarring teleportation.