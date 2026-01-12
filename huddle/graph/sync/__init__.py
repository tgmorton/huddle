"""
Sync module for projecting game state to the graph.

Provides utilities for syncing players, teams, games, and other
entities from the game's data models to Neo4j.

The sync is ONE-WAY: game state -> graph. The graph is a read-optimized
projection, not the source of truth.

Usage:
    from huddle.graph.sync import full_sync, sync_player, sync_game

    # Full sync (startup or manual refresh)
    full_sync(league)

    # Incremental sync (after events)
    sync_player(player, team)
    sync_game(game_log)

    # Event-driven sync
    from huddle.graph.sync import register_game_handlers, graph_sync_enabled
    register_game_handlers(event_bus)

    # Or use context manager
    with graph_sync_enabled(event_bus):
        engine.simulate_game()
"""

from huddle.graph.sync.base import (
    full_sync,
    sync_entity,
    sync_relationship,
    SyncResult,
)

from huddle.graph.sync.players import (
    sync_player,
    sync_player_stats,
    sync_teammates,
    sync_player_faced,
)

from huddle.graph.sync.teams import (
    sync_team,
    sync_team_roster,
    sync_rivalry,
    sync_division_rivalries,
    get_division_for_team,
    get_conference_for_team,
    get_division_rivals,
)

from huddle.graph.sync.games import (
    sync_game,
    sync_drive,
    sync_game_from_event,
)

from huddle.graph.sync.handlers import (
    register_game_handlers,
    unregister_game_handlers,
    graph_sync_enabled,
    sync_after_game,
)

from huddle.graph.sync.computed import (
    sync_all_computed_properties,
    sync_player_career_phase,
    calculate_career_phase,
    calculate_performance_trend,
    detect_narratives,
    CareerPhase,
    PerformanceTrend,
    Narrative,
)

from huddle.graph.sync.historical import (
    HistoricalGraphSync,
    PlayerTeamHistory,
    sync_historical_simulation,
)

__all__ = [
    # Base
    "full_sync",
    "sync_entity",
    "sync_relationship",
    "SyncResult",
    # Players
    "sync_player",
    "sync_player_stats",
    "sync_teammates",
    "sync_player_faced",
    # Teams
    "sync_team",
    "sync_team_roster",
    "sync_rivalry",
    "sync_division_rivalries",
    "get_division_for_team",
    "get_conference_for_team",
    "get_division_rivals",
    # Games
    "sync_game",
    "sync_drive",
    "sync_game_from_event",
    # Handlers
    "register_game_handlers",
    "unregister_game_handlers",
    "graph_sync_enabled",
    "sync_after_game",
    # Computed
    "sync_all_computed_properties",
    "sync_player_career_phase",
    "calculate_career_phase",
    "calculate_performance_trend",
    "detect_narratives",
    "CareerPhase",
    "PerformanceTrend",
    "Narrative",
    # Historical
    "HistoricalGraphSync",
    "PlayerTeamHistory",
    "sync_historical_simulation",
]
