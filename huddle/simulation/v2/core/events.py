"""Event system for simulation state changes.

Events are emitted by systems and can be subscribed to by other systems
or logging infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional
from collections import defaultdict


class EventType(str, Enum):
    """Types of events that can occur during simulation."""

    # =========================================================================
    # Play Lifecycle
    # =========================================================================
    PLAY_START = "play_start"
    SNAP = "snap"
    HANDOFF = "handoff"
    THROW = "throw"
    CATCH = "catch"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"
    FUMBLE = "fumble"
    TACKLE = "tackle"
    OUT_OF_BOUNDS = "out_of_bounds"
    TOUCHDOWN = "touchdown"
    SAFETY = "safety"
    PLAY_END = "play_end"

    # =========================================================================
    # Movement / Position
    # =========================================================================
    ROUTE_BREAK = "route_break"
    ROUTE_COMPLETE = "route_complete"
    PLAYER_MOVED = "player_moved"
    CROSSED_LOS = "crossed_los"
    ENTERED_ENDZONE = "entered_endzone"
    WENT_OUT_OF_BOUNDS = "went_out_of_bounds"

    # =========================================================================
    # QB Events
    # =========================================================================
    HOT_ROUTE = "hot_route"
    PROTECTION_CALL = "protection_call"
    DROPBACK_COMPLETE = "dropback_complete"
    READ_ADVANCED = "read_advanced"
    PRESSURE_LEVEL_CHANGED = "pressure_level_changed"
    SCRAMBLE_INITIATED = "scramble_initiated"
    THROW_DECISION = "throw_decision"
    SACK = "sack"

    # =========================================================================
    # Blocking / Rush
    # =========================================================================
    BLOCK_ENGAGED = "block_engaged"
    BLOCK_SHED = "block_shed"
    BLOCK_SUSTAINED = "block_sustained"
    RUSHER_FREE = "rusher_free"

    # =========================================================================
    # Coverage
    # =========================================================================
    COVERAGE_BROKEN = "coverage_broken"
    SEPARATION_CREATED = "separation_created"
    BALL_HAWK = "ball_hawk"
    COVERAGE_BREAK_REACTION = "coverage_break_reaction"
    ZONE_TRIGGER = "zone_trigger"
    ZONE_HANDOFF = "zone_handoff"

    # =========================================================================
    # Ballcarrier
    # =========================================================================
    HOLE_HIT = "hole_hit"
    CUTBACK = "cutback"
    BOUNCE_OUTSIDE = "bounce_outside"
    MOVE_ATTEMPTED = "move_attempted"
    MOVE_SUCCESS = "move_success"
    MOVE_FAILED = "move_failed"
    YARDS_AFTER_CONTACT = "yards_after_contact"

    # =========================================================================
    # Encounters
    # =========================================================================
    TACKLE_ATTEMPT = "tackle_attempt"
    MISSED_TACKLE = "missed_tackle"
    CATCH_CONTEST = "catch_contest"

    # =========================================================================
    # AI / Decision
    # =========================================================================
    DECISION_MADE = "decision_made"
    BEHAVIOR_TREE_EVAL = "behavior_tree_eval"

    # =========================================================================
    # Phase / System
    # =========================================================================
    PHASE_CHANGE = "phase_change"  # Play phase transition
    ERROR = "error"  # System error or exception


@dataclass
class Event:
    """An event that occurred during simulation.

    Events carry data about what happened and who was involved.
    They're used for logging, state transitions, and inter-system communication.

    Attributes:
        type: The type of event
        tick: When the event occurred
        time: Time in seconds when event occurred
        player_id: Primary player involved (if any)
        target_id: Secondary player involved (if any)
        data: Additional event-specific data
        description: Human-readable description
    """
    type: EventType
    tick: int
    time: float
    player_id: Optional[str] = None
    target_id: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __str__(self) -> str:
        """Readable event string for logging."""
        parts = [f"[{self.time:.2f}s]", f"{self.type.value}"]

        if self.player_id:
            parts.append(f"by {self.player_id}")

        if self.target_id:
            parts.append(f"→ {self.target_id}")

        if self.description:
            parts.append(f"- {self.description}")

        return " ".join(parts)

    def format_detailed(self) -> str:
        """Detailed multi-line format for analysis."""
        lines = [
            f"Event: {self.type.value}",
            f"  Time: {self.time:.3f}s (tick {self.tick})",
        ]

        if self.player_id:
            lines.append(f"  Player: {self.player_id}")

        if self.target_id:
            lines.append(f"  Target: {self.target_id}")

        if self.description:
            lines.append(f"  Description: {self.description}")

        if self.data:
            lines.append("  Data:")
            for key, value in self.data.items():
                lines.append(f"    {key}: {value}")

        return "\n".join(lines)


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Pub/sub event bus for simulation events.

    Systems can subscribe to event types and emit events.
    Events are also logged for later analysis.

    Usage:
        bus = EventBus()

        # Subscribe to events
        bus.subscribe(EventType.SNAP, my_handler)
        bus.subscribe_all(my_logger)

        # Emit events
        bus.emit(Event(type=EventType.SNAP, tick=0, time=0.0))
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._history: list[Event] = []
        self._recording: bool = True

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe from a specific event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        # Record to history
        if self._recording:
            self._history.append(event)

        # Notify type-specific handlers
        for handler in self._handlers[event.type]:
            handler(event)

        # Notify global handlers
        for handler in self._global_handlers:
            handler(event)

    def emit_simple(
        self,
        event_type: EventType,
        tick: int,
        time: float,
        player_id: Optional[str] = None,
        description: str = "",
        **data: Any,
    ) -> Event:
        """Convenience method to emit an event with less boilerplate."""
        event = Event(
            type=event_type,
            tick=tick,
            time=time,
            player_id=player_id,
            description=description,
            data=data,
        )
        self.emit(event)
        return event

    @property
    def history(self) -> list[Event]:
        """Get all recorded events."""
        return self._history

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    def set_recording(self, enabled: bool) -> None:
        """Enable or disable event recording."""
        self._recording = enabled

    def get_events_by_type(self, event_type: EventType) -> list[Event]:
        """Get all events of a specific type from history."""
        return [e for e in self._history if e.type == event_type]

    def get_events_for_player(self, player_id: str) -> list[Event]:
        """Get all events involving a specific player."""
        return [
            e for e in self._history
            if e.player_id == player_id or e.target_id == player_id
        ]

    def format_history(self, last_n: Optional[int] = None) -> str:
        """Format event history as readable text."""
        events = self._history[-last_n:] if last_n else self._history
        return "\n".join(str(e) for e in events)

    def format_history_detailed(self, last_n: Optional[int] = None) -> str:
        """Format event history with full details."""
        events = self._history[-last_n:] if last_n else self._history
        return "\n\n".join(e.format_detailed() for e in events)

    def __len__(self) -> int:
        return len(self._history)

    def __bool__(self) -> bool:
        """EventBus is always truthy (even with empty history)."""
        return True
