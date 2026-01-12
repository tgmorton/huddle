"""
Event handlers for graph sync.

Provides handlers that can be registered with the EventBus to automatically
sync game events to the graph.

Usage:
    from huddle.graph.sync.handlers import register_game_handlers

    # Register handlers with event bus
    register_game_handlers(event_bus)

    # Or use the context manager
    with graph_sync_enabled(event_bus):
        # Game simulation runs here
        # Events automatically sync to graph
"""

import logging
from typing import Any, Callable, Optional

from huddle.graph.config import is_graph_enabled
from huddle.graph.connection import get_graph, GraphConnection
from huddle.graph.sync.base import SyncResult

logger = logging.getLogger(__name__)

# Track registered handlers for cleanup
_registered_handlers: list[tuple[Any, Any, Callable]] = []


def register_game_handlers(
    event_bus: Any,
    graph: Optional[GraphConnection] = None,
) -> None:
    """
    Register graph sync handlers with an EventBus.

    Subscribes to relevant game events and syncs changes to the graph.
    Does nothing if graph is disabled.

    Args:
        event_bus: EventBus instance to register with
        graph: Optional graph connection
    """
    if not is_graph_enabled():
        logger.debug("Graph disabled, not registering handlers")
        return

    graph = graph or get_graph()

    # Import event types here to avoid circular imports
    from huddle.events.types import (
        GameEndEvent,
        ScoringEvent,
        TurnoverEvent,
        QuarterEndEvent,
    )

    # Create handlers
    def on_game_end(event: GameEndEvent) -> None:
        _handle_game_end(event, graph)

    def on_scoring(event: ScoringEvent) -> None:
        _handle_scoring(event, graph)

    def on_turnover(event: TurnoverEvent) -> None:
        _handle_turnover(event, graph)

    def on_quarter_end(event: QuarterEndEvent) -> None:
        _handle_quarter_end(event, graph)

    # Register handlers
    event_bus.subscribe(GameEndEvent, on_game_end)
    event_bus.subscribe(ScoringEvent, on_scoring)
    event_bus.subscribe(TurnoverEvent, on_turnover)
    event_bus.subscribe(QuarterEndEvent, on_quarter_end)

    # Track for cleanup
    _registered_handlers.extend([
        (event_bus, GameEndEvent, on_game_end),
        (event_bus, ScoringEvent, on_scoring),
        (event_bus, TurnoverEvent, on_turnover),
        (event_bus, QuarterEndEvent, on_quarter_end),
    ])

    logger.info("Registered graph sync handlers with event bus")


def unregister_game_handlers(event_bus: Any) -> None:
    """
    Unregister all graph sync handlers from an EventBus.
    """
    global _registered_handlers

    for bus, event_type, handler in _registered_handlers:
        if bus is event_bus:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception:
                pass

    _registered_handlers = [
        (bus, et, h) for bus, et, h in _registered_handlers
        if bus is not event_bus
    ]

    logger.info("Unregistered graph sync handlers")


class GraphSyncContext:
    """
    Context manager for enabling graph sync during game simulation.

    Usage:
        with GraphSyncContext(event_bus):
            # Run simulation
            engine.simulate_game()
        # Handlers automatically cleaned up
    """

    def __init__(
        self,
        event_bus: Any,
        graph: Optional[GraphConnection] = None,
    ):
        self.event_bus = event_bus
        self.graph = graph

    def __enter__(self) -> "GraphSyncContext":
        register_game_handlers(self.event_bus, self.graph)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        unregister_game_handlers(self.event_bus)
        return False


# Alias for cleaner import
graph_sync_enabled = GraphSyncContext


def _handle_game_end(event: Any, graph: GraphConnection) -> None:
    """
    Handle GameEndEvent - sync completed game to graph.

    This is the main sync point for games. When a game ends,
    we sync the full game with all stats.
    """
    try:
        logger.info(f"Syncing game end: {event.game_id}")

        # Update game node with final state
        from huddle.graph.sync.games import sync_game_from_event

        # Note: We'd need access to the teams and game_log here
        # In practice, this would be passed through context or fetched
        # For now, just update the game node properties

        from huddle.graph.sync.base import sync_entity
        from huddle.graph.schema import NodeLabels

        game_id = str(event.game_id) if event.game_id else "unknown"

        properties = {
            "final_home_score": event.final_home_score,
            "final_away_score": event.final_away_score,
            "is_overtime": event.is_overtime,
            "is_complete": True,
        }

        if event.winner_id:
            properties["winner_id"] = str(event.winner_id)

        result = sync_entity(NodeLabels.GAME, game_id, properties, graph)

        if result.success:
            logger.debug(f"Game end synced: {game_id}")
        else:
            logger.warning(f"Game end sync had errors: {result.errors}")

    except Exception as e:
        logger.error(f"Failed to handle game end event: {e}")


def _handle_scoring(event: Any, graph: GraphConnection) -> None:
    """
    Handle ScoringEvent - update game and player stats.

    Scoring events are important for narratives (touchdowns, field goals).
    """
    try:
        # For now, just log - scoring is captured in final game stats
        logger.debug(
            f"Scoring event: {event.scoring_type} by team {event.team_id}, "
            f"scorer: {event.scorer_id}"
        )

        # Could update running narrative here
        # e.g., track hat tricks, scoring streaks, etc.

    except Exception as e:
        logger.error(f"Failed to handle scoring event: {e}")


def _handle_turnover(event: Any, graph: GraphConnection) -> None:
    """
    Handle TurnoverEvent - track for narratives.

    Turnovers are important for momentum narratives.
    """
    try:
        logger.debug(
            f"Turnover event: {event.turnover_type} by {event.player_who_lost_id}, "
            f"recovered by {event.player_who_gained_id}"
        )

        # Could track turnover-prone players, clutch defenders, etc.

    except Exception as e:
        logger.error(f"Failed to handle turnover event: {e}")


def _handle_quarter_end(event: Any, graph: GraphConnection) -> None:
    """
    Handle QuarterEndEvent - potential sync point.

    Quarter ends are natural sync points for incremental updates.
    """
    try:
        logger.debug(f"Quarter {event.quarter_ended} ended")

        # Could sync running stats at quarter breaks
        # Useful for live commentary context updates

    except Exception as e:
        logger.error(f"Failed to handle quarter end event: {e}")


def sync_after_game(
    game_log: Any,
    home_team: Any,
    away_team: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Convenience function to sync a completed game with full context.

    Call this after a game completes when you have access to all the data.

    Args:
        game_log: GameLog with full game stats
        home_team: Home Team object
        away_team: Away Team object
        graph: Optional graph connection

    Returns:
        SyncResult with operation stats
    """
    from huddle.graph.sync.games import sync_game
    from huddle.graph.sync.teams import sync_team_roster

    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # Sync game
    r = sync_game(game_log, graph)
    result = result + r

    # Optionally refresh team rosters (in case of mid-game changes)
    # Usually not needed but available
    # r = sync_team_roster(home_team, graph)
    # result = result + r
    # r = sync_team_roster(away_team, graph)
    # result = result + r

    logger.info(
        f"Post-game sync complete: {result.nodes_created} nodes, "
        f"{result.relationships_created} relationships"
    )

    return result
