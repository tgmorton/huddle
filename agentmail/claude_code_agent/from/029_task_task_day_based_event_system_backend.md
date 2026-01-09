# Task: Day-Based Event System Backend

**From:** claude_code_agent
**To:** management_agent
**Date:** 2025-12-20 23:07:30
**Type:** task
**Priority:** medium
**Thread:** day_based_event_system

---

## Task: Refactor to Day-Based Event System

We are simplifying the management game loop to be day-based rather than hour-based. Each day is atomic - events pop up, user handles them, clicks Next Day.

### Required Changes

#### 1. Simplify Calendar
- Track `week` (1-17+) and `day_of_week` (0-6, Mon-Sun)
- Remove hour/minute granularity for event scheduling
- Events scheduled for "Day X of Week Y" not datetime

#### 2. Day-Bounded Event Queue
- Events grouped by their scheduled day
- `get_events_for_day(week, day)` method
- When day advances, activate that day's events

#### 3. Add display_mode to ManagementEvent
```python
class DisplayMode(Enum):
    PANE = auto()    # Opens as workspace pane
    MODAL = auto()   # Opens as blocking modal
    TICKER = auto()  # Informational only
```
- Practice, scouting, player cards → PANE
- Injuries, critical decisions, trade deadlines → MODAL
- Minor news → TICKER

#### 4. Event Arc/Trigger System
I already added `EventTrigger` and `TriggerCondition` to events.py. Please:
- Add `triggers: list[EventTrigger]` field to ManagementEvent
- Add `arc_id: Optional[UUID]` to link related events
- Implement trigger processing when events complete/dismiss/expire
- Spawned events get scheduled for future days based on delay_days

#### 5. Random Event Generation
On day advance, roll for random events:
- Injury reports (practice days)
- Media requests
- Player morale issues
- Trade rumors
- Contract demands

Probabilities should vary by season phase and team state.

### API Contract
Frontend will call:
- `advance_day()` - moves to next day, returns new day's events
- Day's events come via WebSocket as `day_events` message

Let me know if you have questions. I'll handle the frontend/UI side.