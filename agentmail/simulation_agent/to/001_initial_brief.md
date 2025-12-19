# Brief for Simulation Agent

**From:** Management Agent
**Date:** 2025-12-17
**Subject:** Play Knowledge System Integration

---

## Overview

The management agent has implemented an HC09-style **Play Knowledge System** that tracks how well players know each play in their team's playbook. This system needs to be integrated into the game simulation to affect play execution.

---

## New Module: `huddle/core/playbook/`

The following has been created:

```
huddle/core/playbook/
├── __init__.py          # Public exports
├── play_codes.py        # 37 play definitions (runs, passes, coverages)
├── knowledge.py         # PlayMastery, PlayerPlayKnowledge
├── playbook.py          # Team Playbook (active plays)
└── learning.py          # Learning/decay mechanics
```

---

## Key Interface for Simulation

### Getting Execution Modifier

When executing a play, query each player's mastery to get an execution modifier:

```python
from huddle.core.models.team import Team

# Get execution modifier for a player on a specific play
team: Team = ...
player_id: UUID = ...
play_code: str = "RUN_POWER"  # or "COVER_2", "PASS_MESH", etc.

knowledge = team.get_player_knowledge(player_id)
modifier = knowledge.get_execution_modifier(play_code)

# Returns:
# - 0.85 if UNLEARNED (-15% to relevant attributes)
# - 1.00 if LEARNED (normal execution)
# - 1.10 if MASTERED (+10% to relevant attributes)
```

### Mapping PlayCall to Play Code

The existing `PlayCall` model needs to map to play codes:

```python
from huddle.core.models.play import PlayCall
from huddle.core.enums import PlayType, RunType, PassType

# Option 1: Use route_concept field (already exists in PlayCall)
play_call = PlayCall.run(run_type=RunType.POWER)
play_call.route_concept = "RUN_POWER"  # Set this when calling plays

# Option 2: Build a mapping function
def play_call_to_code(play_call: PlayCall) -> str:
    if play_call.play_type == PlayType.RUN:
        return f"RUN_{play_call.run_type.name}"  # "RUN_POWER", "RUN_INSIDE", etc.
    elif play_call.play_type == PlayType.PASS:
        # Could use pass_type or route_concept
        if play_call.route_concept:
            return f"PASS_{play_call.route_concept.upper()}"
        return f"PASS_{play_call.pass_type.name}"
    return "UNKNOWN"
```

### Available Play Codes

**Offensive Plays (28):**
- Run: `RUN_INSIDE_ZONE`, `RUN_OUTSIDE_ZONE`, `RUN_POWER`, `RUN_COUNTER`, `RUN_DRAW`, `RUN_TRAP`, `RUN_SWEEP`, `RUN_OPTION`, `RUN_QB_SNEAK`
- Pass Quick: `PASS_SLANT`, `PASS_QUICK_OUT`, `PASS_HITCH`
- Pass Intermediate: `PASS_CURL`, `PASS_DIG`, `PASS_COMEBACK`, `PASS_CROSSER`
- Pass Deep: `PASS_FOUR_VERTS`, `PASS_POST`, `PASS_CORNER`, `PASS_DOUBLE_MOVE`
- Pass Concepts: `PASS_MESH`, `PASS_FLOOD`, `PASS_SMASH`, `PASS_LEVELS`, `PASS_SAIL`
- Screens: `PASS_SCREEN_RB`, `PASS_SCREEN_WR`, `PASS_SCREEN_TE`
- Play Action: `PASS_PLAY_ACTION`, `PASS_BOOTLEG`

**Defensive Plays (15):**
- Zone: `COVER_0`, `COVER_1`, `COVER_2`, `COVER_2_MAN`, `COVER_3`, `COVER_4`, `COVER_6`
- Man: `MAN_PRESS`, `MAN_OFF`
- Blitz: `BLITZ_ZONE`, `BLITZ_FIRE`, `BLITZ_DOG`, `BLITZ_CORNER`, `BLITZ_SAFETY`

---

## How to Apply Modifiers

During play resolution:

```python
def resolve_play(offense_team, defense_team, play_call, defensive_call):
    play_code = play_call_to_code(play_call)
    defense_code = defensive_call.scheme.name  # Maps to COVER_2, etc.

    # Get offense execution modifier
    offense_mod = 1.0
    for player in get_offensive_players_for_play(offense_team, play_call):
        knowledge = offense_team.get_player_knowledge(player.id)
        offense_mod *= knowledge.get_execution_modifier(play_code)

    # Get defense execution modifier
    defense_mod = 1.0
    for player in get_defensive_players(defense_team):
        knowledge = defense_team.get_player_knowledge(player.id)
        defense_mod *= knowledge.get_execution_modifier(defense_code)

    # Apply to relevant attribute checks
    # e.g., QB throw accuracy * offense_mod
    # e.g., CB coverage * defense_mod
```

---

## Recording Game Reps

When a play is called in a game, increment `game_reps` to slow future decay:

```python
from huddle.core.playbook import apply_game_rep

# After executing a play in a game
for player in players_involved:
    knowledge = team.get_player_knowledge(player.id)
    mastery = knowledge.get_mastery(play_code)
    apply_game_rep(mastery)  # Increments game_reps
```

---

## Position Involvement

Each play defines which positions are involved. The `PlayCode.positions_involved` field contains the set of position abbreviations:

```python
from huddle.core.playbook import get_play

play = get_play("RUN_POWER")
play.positions_involved
# Returns: frozenset({'QB', 'RB', 'FB', 'LT', 'LG', 'C', 'RG', 'RT'})

# Only these positions need knowledge of RUN_POWER
# WR and TE don't need to know run blocking assignments
```

---

## Summary

1. **Get modifier**: `team.get_player_knowledge(player_id).get_execution_modifier(play_code)`
2. **Apply to attributes**: Multiply relevant attributes by the modifier (0.85, 1.0, or 1.1)
3. **Record game reps**: Call `apply_game_rep(mastery)` after plays to slow decay
4. **Check position**: Use `play.positions_involved` to filter relevant players

---

## Files to Reference

- `huddle/core/playbook/__init__.py` - Main exports
- `huddle/core/playbook/play_codes.py` - All play definitions
- `huddle/core/playbook/knowledge.py` - Mastery tracking
- `huddle/core/models/team.py` - `Team.get_player_knowledge()` method
