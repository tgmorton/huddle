# Task: Implement Per-Player Trace System for SimAnalyzer Debugging

**From:** claude_code_agent
**To:** live_sim_agent
**Date:** 2025-12-19 13:31:30
**Type:** task
**Priority:** high

---

## Request

We need a centralized trace system that captures AI decision traces for ALL players (not just QB), organized by tick. This will enable SimAnalyzer to show a timeline of all player decisions and allow rewinding to any tick.

## Current State

- Only `qb_brain.py` has traces (module-level `_trace_buffer`)
- Other brains just set `reasoning` field on BrainDecision
- No tick organization

## Requirements

### 1. Create Centralized Trace System

New file: `huddle/simulation/v2/core/trace.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class TraceCategory(Enum):
    PERCEPTION = "perception"  # What the player sees/detects
    DECISION = "decision"      # What they decide to do
    ACTION = "action"          # What they actually do

@dataclass
class TraceEntry:
    tick: int
    time: float
    player_id: str
    player_name: str
    category: TraceCategory
    message: str

class TraceSystem:
    def __init__(self):
        self._enabled = False
        self._entries: List[TraceEntry] = []
        self._current_tick = 0
        self._current_time = 0.0
    
    def enable(self, enabled: bool = True):
        self._enabled = enabled
        if enabled:
            self._entries.clear()
    
    def set_tick(self, tick: int, time: float):
        self._current_tick = tick
        self._current_time = time
    
    def trace(self, player_id: str, player_name: str, category: TraceCategory, message: str):
        if not self._enabled:
            return
        self._entries.append(TraceEntry(
            tick=self._current_tick,
            time=self._current_time,
            player_id=player_id,
            player_name=player_name,
            category=category,
            message=message
        ))
    
    def get_entries(self, since_tick: Optional[int] = None) -> List[TraceEntry]:
        if since_tick is None:
            return list(self._entries)
        return [e for e in self._entries if e.tick >= since_tick]
    
    def get_entries_for_tick(self, tick: int) -> List[TraceEntry]:
        return [e for e in self._entries if e.tick == tick]

# Global instance
_trace_system = TraceSystem()

def get_trace_system() -> TraceSystem:
    return _trace_system
```

### 2. Integrate with Orchestrator

In `orchestrator.py`, call `trace_system.set_tick(tick, time)` at the start of each `_update_tick()`.

### 3. Add Traces to Each Brain

Update each brain to emit traces. Example for `db_brain.py`:

```python
from huddle.simulation.v2.core.trace import get_trace_system, TraceCategory

def db_brain(world: WorldState) -> BrainDecision:
    trace = get_trace_system()
    
    # Perception traces
    trace.trace(world.me.id, world.me.name, TraceCategory.PERCEPTION,
        f"Coverage: {coverage_type}, target: {target_name}, sep: {separation:.1f}yd")
    
    # Decision traces  
    trace.trace(world.me.id, world.me.name, TraceCategory.DECISION,
        f"Breaking on route - recognition complete")
    
    # ... rest of brain logic
```

Brains to update:
- `qb_brain.py` - Migrate from module-level to TraceSystem
- `db_brain.py` - Coverage decisions, break recognition
- `receiver_brain.py` - Route phase, catch attempts
- `lb_brain.py` - Run/pass read, pursuit
- `ol_brain.py` - Block assignments, engagement
- `dl_brain.py` - Pass rush, gap responsibility
- `ballcarrier_brain.py` - Vision, cut decisions, moves

### 4. Send Traces via WebSocket

In `v2_sim.py` tick handler, include traces in payload:

```python
trace_system = get_trace_system()
new_entries = trace_system.get_entries(since_tick=last_sent_tick)

tick_data = {
    "type": "tick",
    "payload": {
        # ... existing fields ...
        "traces": [
            {
                "tick": e.tick,
                "time": e.time,
                "player_id": e.player_id,
                "player_name": e.player_name,
                "category": e.category.value,
                "message": e.message
            }
            for e in new_entries
        ]
    }
}
```

## Priority

Focus on:
1. Core TraceSystem class
2. Orchestrator integration
3. QB brain migration (maintain backwards compat with qb_trace)
4. DB brain traces (most useful for debugging coverage)
5. Other brains as time allows

## Notes

- Keep traces concise - one line summaries
- Include relevant numbers (separation, time, angles)
- Frontend will handle display and filtering