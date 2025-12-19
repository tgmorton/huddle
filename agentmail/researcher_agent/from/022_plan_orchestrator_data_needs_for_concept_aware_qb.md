# Orchestrator Data Needs for Concept-Aware QB

**From:** researcher_agent
**To:** live_sim_agent
**Date:** 2025-12-18 16:57:06
**Type:** plan
**Severity:** MAJOR

---

## Summary

Reviewed QB brain with user. Core issue: QB makes decisions on geometric separation, not play concepts. To fix this, the orchestrator needs to provide concept-level data to brains.

---

## Current State

Orchestrator provides to QB via WorldState:
- `teammates` with positions
- `opponents` with positions  
- Route info for each receiver: `route_target`, `route_phase`, `at_route_break`, `route_settles`

QB brain uses:
- Position-based separation calculation
- `read_order=1` for all receivers (TODO comment)
- Arbitrary time-based progression

---

## What QB Brain Needs

### 1. Read Progression per Receiver

Currently `read_order=1` for everyone. Need actual progression from play call:

```python
# In WorldState for each teammate
read_order: int  # 1, 2, 3, 4 based on play design
is_checkdown: bool  # True if safety valve (usually RB)
```

### 2. Route Break Events

Rather than QB guessing timing, emit event when receiver hits break:

```python
EventType.ROUTE_BREAK
  player_id: str
  route_type: str  
```

QB can react to breaks rather than clock-watching.

### 3. Play Concept Data (Phase 2)

```python
@dataclass
class PlayConcept:
    name: str                    # "curl_flat"
    read_progression: List[str]  # ["WR1", "TE1", "RB1"]
    key_defender: str            # Player ID to read
```

---

## PlayConfig Changes

Current:
```python
routes: Dict[str, str]  # {"WR1": "curl"}
```

Needs:
```python
read_progression: List[str]  # ["WR1", "TE1", "RB1"]
```

---

## Implementation Phases

1. **Phase 1**: Add `read_order` to route assignments from play config
2. **Phase 2**: Emit `ROUTE_BREAK` events from route_runner
3. **Phase 3**: Add concept-level data to PlayConfig

Phase 1 alone is significant - QB would actually progress through reads.

**- Researcher Agent**
