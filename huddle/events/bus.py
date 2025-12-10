"""Event bus for pub/sub communication."""

from collections import defaultdict
from typing import Callable, TypeVar

from huddle.events.types import GameEvent

T = TypeVar("T", bound=GameEvent)
EventHandler = Callable[[GameEvent], None]


class EventBus:
    """
    Simple pub/sub event bus for decoupling simulation from UI/logging.

    Components can subscribe to specific event types and receive
    notifications when those events occur. This allows the simulation
    engine to emit events without knowing who will handle them.

    Example:
        bus = EventBus()

        def on_play(event: PlayCompletedEvent):
            print(f"Play result: {event.result.display}")

        bus.subscribe(PlayCompletedEvent, on_play)
        bus.emit(PlayCompletedEvent(result=some_result))
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[type[GameEvent], list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def subscribe(
        self,
        event_type: type[T],
        handler: Callable[[T], None],
    ) -> None:
        """
        Register a handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: Callback function that receives the event
        """
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Register a handler for all events.

        Args:
            handler: Callback function that receives any event
        """
        self._global_handlers.append(handler)

    def unsubscribe(
        self,
        event_type: type[T],
        handler: Callable[[T], None],
    ) -> None:
        """
        Remove a handler for a specific event type.

        Args:
            event_type: The type of event
            handler: The handler to remove
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """
        Remove a global handler.

        Args:
            handler: The handler to remove
        """
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)

    def emit(self, event: GameEvent) -> None:
        """
        Emit an event to all registered handlers.

        Handlers for the specific event type are called first,
        then global handlers that receive all events.

        Args:
            event: The event to emit
        """
        # Call type-specific handlers
        for handler in self._handlers[type(event)]:
            handler(event)

        # Call global handlers
        for handler in self._global_handlers:
            handler(event)

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
        self._global_handlers.clear()

    def handler_count(self, event_type: type[GameEvent] | None = None) -> int:
        """
        Get the number of registered handlers.

        Args:
            event_type: If provided, count handlers for this type only.
                       If None, count all handlers including global.

        Returns:
            Number of registered handlers
        """
        if event_type is None:
            total = sum(len(handlers) for handlers in self._handlers.values())
            return total + len(self._global_handlers)
        return len(self._handlers[event_type])
