"""
Game sync module.

Handles syncing Game entities, Drives, and game-related relationships.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from huddle.graph.connection import GraphConnection, get_graph, is_graph_enabled
from huddle.graph.schema import NodeLabels, RelTypes
from huddle.graph.sync.base import SyncResult, sync_entity, sync_relationship

logger = logging.getLogger(__name__)


def sync_game(
    game_log: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a completed game to the graph.

    Creates/updates:
    - Game node with scores and metadata
    - HOME_TEAM and AWAY_TEAM relationships
    - WON/LOST relationships based on outcome
    - PLAYED_IN relationships for all participating players
    - IN_SEASON relationship to Season node

    Args:
        game_log: GameLog object containing game results
        graph: Optional graph connection

    Returns:
        SyncResult with operation stats
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # Extract game properties
    properties = _extract_game_properties(game_log)

    # Sync the game node
    game_id = str(game_log.game_id)
    r = sync_entity(NodeLabels.GAME, game_id, properties, graph)
    result = result + r

    # Sync team relationships
    r = _sync_game_team_relationships(game_log, graph)
    result = result + r

    # Sync player participation (PLAYED_IN)
    r = _sync_player_participation(game_log, graph)
    result = result + r

    # Sync to season
    if hasattr(game_log, "season_year") and game_log.season_year:
        r = _sync_game_to_season(game_id, game_log.season_year, game_log.week, graph)
        result = result + r

    return result


def sync_drive(
    drive: Any,
    game_id: str,
    drive_number: int,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a drive to the graph.

    Creates Drive node and CONTAINS relationship from Game.

    Args:
        drive: Drive object with result and plays
        game_id: Parent game's ID
        drive_number: Sequential drive number in the game
        graph: Optional graph connection
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # Create unique drive ID
    drive_id = f"{game_id}_drive_{drive_number}"

    properties = {
        "game_id": game_id,
        "drive_number": drive_number,
        "start_field_position": getattr(drive, "start_field_position", 0),
        "plays_count": getattr(drive, "plays_count", 0),
        "yards_gained": getattr(drive, "yards_gained", 0),
        "result": getattr(drive, "result", "unknown"),
        "is_scoring": getattr(drive, "is_scoring", False),
    }

    # Sync drive node
    r = sync_entity(NodeLabels.DRIVE, drive_id, properties, graph)
    result = result + r

    # Sync CONTAINS relationship from Game
    r = sync_relationship(
        NodeLabels.GAME, game_id,
        RelTypes.CONTAINS,
        NodeLabels.DRIVE, drive_id,
        {"order": drive_number},
        graph
    )
    result = result + r

    return result


def sync_game_from_event(
    event: Any,
    home_team: Any,
    away_team: Any,
    game_log: Optional[Any] = None,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a game from a GameEndEvent.

    Called by event handlers when a game completes.

    Args:
        event: GameEndEvent with final scores
        home_team: Home Team object
        away_team: Away Team object
        game_log: Optional GameLog for detailed stats
        graph: Optional graph connection
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    game_id = str(event.game_id) if event.game_id else f"game_{event.timestamp.isoformat()}"

    properties = {
        "home_score": event.final_home_score,
        "away_score": event.final_away_score,
        "is_overtime": event.is_overtime,
        "quarter": event.quarter,
        "completed_at": event.timestamp.isoformat(),
    }

    # Sync game node
    r = sync_entity(NodeLabels.GAME, game_id, properties, graph)
    result = result + r

    # Sync team relationships
    r = sync_relationship(
        NodeLabels.GAME, game_id,
        RelTypes.HOME_TEAM,
        NodeLabels.TEAM, home_team.id,
        graph=graph
    )
    result = result + r

    r = sync_relationship(
        NodeLabels.GAME, game_id,
        RelTypes.AWAY_TEAM,
        NodeLabels.TEAM, away_team.id,
        graph=graph
    )
    result = result + r

    # Determine winner and sync WON/LOST
    if event.winner_id:
        winner_id = event.winner_id
        loser_id = away_team.id if winner_id == home_team.id else home_team.id

        r = sync_relationship(
            NodeLabels.TEAM, winner_id,
            RelTypes.WON,
            NodeLabels.GAME, game_id,
            {"score": event.final_home_score if winner_id == home_team.id else event.final_away_score},
            graph
        )
        result = result + r

        r = sync_relationship(
            NodeLabels.TEAM, loser_id,
            RelTypes.LOST,
            NodeLabels.GAME, game_id,
            {"score": event.final_away_score if winner_id == home_team.id else event.final_home_score},
            graph
        )
        result = result + r

    # If we have the full game log, sync player stats
    if game_log:
        r = _sync_player_participation(game_log, graph)
        result = result + r

    return result


def _extract_game_properties(game_log: Any) -> dict[str, Any]:
    """Extract properties from a GameLog for the graph node."""
    properties = {
        "week": game_log.week,
        "home_team_abbr": game_log.home_team_abbr,
        "away_team_abbr": game_log.away_team_abbr,
        "home_score": game_log.home_score,
        "away_score": game_log.away_score,
    }

    # Optional flags
    if hasattr(game_log, "is_overtime"):
        properties["is_overtime"] = game_log.is_overtime
    if hasattr(game_log, "is_playoff"):
        properties["is_playoff"] = game_log.is_playoff
    if hasattr(game_log, "season_year"):
        properties["season_year"] = game_log.season_year

    # Determine winner
    if game_log.home_score > game_log.away_score:
        properties["winner_abbr"] = game_log.home_team_abbr
    elif game_log.away_score > game_log.home_score:
        properties["winner_abbr"] = game_log.away_team_abbr
    else:
        properties["winner_abbr"] = None  # Tie

    # Game totals from team stats
    if hasattr(game_log, "home_stats") and game_log.home_stats:
        h = game_log.home_stats
        properties["home_total_yards"] = getattr(h, "total_yards", 0)
        properties["home_turnovers"] = getattr(h, "turnovers", 0)

    if hasattr(game_log, "away_stats") and game_log.away_stats:
        a = game_log.away_stats
        properties["away_total_yards"] = getattr(a, "total_yards", 0)
        properties["away_turnovers"] = getattr(a, "turnovers", 0)

    return properties


def _sync_game_team_relationships(
    game_log: Any,
    graph: GraphConnection,
) -> SyncResult:
    """Sync HOME_TEAM, AWAY_TEAM, WON, LOST relationships for a game."""
    result = SyncResult(success=True)
    game_id = str(game_log.game_id)

    # We need to find team IDs from abbreviations
    # This is where team_id on game_log would help
    # For now, use abbreviation-based queries

    # HOME_TEAM relationship
    query = """
    MATCH (g:Game {id: $game_id})
    MATCH (t:Team {abbr: $abbr})
    MERGE (g)-[r:HOME_TEAM]->(t)
    RETURN r
    """
    try:
        graph.run_write(query, {"game_id": game_id, "abbr": game_log.home_team_abbr})
        result.relationships_created += 1
    except Exception as e:
        result.errors.append(f"HOME_TEAM: {e}")

    # AWAY_TEAM relationship
    try:
        query = query.replace("HOME_TEAM", "AWAY_TEAM")
        graph.run_write(query, {"game_id": game_id, "abbr": game_log.away_team_abbr})
        result.relationships_created += 1
    except Exception as e:
        result.errors.append(f"AWAY_TEAM: {e}")

    # WON/LOST relationships
    if game_log.home_score > game_log.away_score:
        winner_abbr = game_log.home_team_abbr
        loser_abbr = game_log.away_team_abbr
    elif game_log.away_score > game_log.home_score:
        winner_abbr = game_log.away_team_abbr
        loser_abbr = game_log.home_team_abbr
    else:
        # Tie - no WON/LOST relationships
        return result

    # WON relationship
    query = """
    MATCH (g:Game {id: $game_id})
    MATCH (t:Team {abbr: $abbr})
    MERGE (t)-[r:WON]->(g)
    RETURN r
    """
    try:
        graph.run_write(query, {"game_id": game_id, "abbr": winner_abbr})
        result.relationships_created += 1
    except Exception as e:
        result.errors.append(f"WON: {e}")

    # LOST relationship
    query = """
    MATCH (g:Game {id: $game_id})
    MATCH (t:Team {abbr: $abbr})
    MERGE (t)-[r:LOST]->(g)
    RETURN r
    """
    try:
        graph.run_write(query, {"game_id": game_id, "abbr": loser_abbr})
        result.relationships_created += 1
    except Exception as e:
        result.errors.append(f"LOST: {e}")

    return result


def _sync_player_participation(
    game_log: Any,
    graph: GraphConnection,
) -> SyncResult:
    """Sync PLAYED_IN relationships for all players in a game."""
    from huddle.graph.sync.players import sync_player_stats

    result = SyncResult(success=True)
    game_id = str(game_log.game_id)

    if not hasattr(game_log, "player_stats") or not game_log.player_stats:
        return result

    for player_id, stats in game_log.player_stats.items():
        r = sync_player_stats(player_id, game_id, stats, graph)
        result = result + r

    return result


def _sync_game_to_season(
    game_id: str,
    season_year: int,
    week: int,
    graph: GraphConnection,
) -> SyncResult:
    """Sync IN_SEASON relationship from Game to Season."""
    result = SyncResult(success=True)

    # Ensure season exists
    r = sync_entity(NodeLabels.SEASON, str(season_year), {"year": season_year}, graph)
    result = result + r

    # Create IN_SEASON relationship
    r = sync_relationship(
        NodeLabels.GAME, game_id,
        RelTypes.IN_SEASON,
        NodeLabels.SEASON, str(season_year),
        {"week": week},
        graph
    )
    result = result + r

    return result
