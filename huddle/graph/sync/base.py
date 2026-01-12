"""
Base sync utilities for the graph module.

Provides the core sync infrastructure: batching, error handling,
and the main full_sync entry point.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from huddle.graph.connection import get_graph, GraphConnection
from huddle.graph.schema import init_schema, NodeLabels, RelTypes

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def __add__(self, other: "SyncResult") -> "SyncResult":
        """Combine two sync results."""
        return SyncResult(
            success=self.success and other.success,
            nodes_created=self.nodes_created + other.nodes_created,
            nodes_updated=self.nodes_updated + other.nodes_updated,
            relationships_created=self.relationships_created + other.relationships_created,
            errors=self.errors + other.errors,
            duration_ms=self.duration_ms + other.duration_ms,
        )


def sync_entity(
    entity_type: str,
    entity_id: str | UUID,
    properties: dict[str, Any],
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a single entity to the graph using MERGE.

    Args:
        entity_type: Node label (e.g., "Player", "Team")
        entity_id: Unique identifier
        properties: Node properties to set

    Returns:
        SyncResult with operation stats
    """
    graph = graph or get_graph()
    start = datetime.now()

    if not graph.is_enabled:
        return SyncResult(success=True, duration_ms=0)

    try:
        # Convert UUID to string for Neo4j
        id_str = str(entity_id)

        # Build MERGE query
        query = f"""
        MERGE (n:{entity_type} {{id: $id}})
        SET n += $properties
        RETURN n
        """

        result = graph.run_write(query, {"id": id_str, "properties": properties})

        duration = (datetime.now() - start).total_seconds() * 1000
        return SyncResult(
            success=True,
            nodes_created=result.get("nodes_created", 0),
            nodes_updated=1 if result.get("properties_set", 0) > 0 else 0,
            duration_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() * 1000
        logger.error(f"Failed to sync {entity_type} {entity_id}: {e}")
        return SyncResult(success=False, errors=[str(e)], duration_ms=duration)


def sync_entity_by_key(
    entity_type: str,
    key_name: str,
    key_value: str,
    properties: dict[str, Any],
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync an entity using a specific key for MERGE (not just 'id').

    Useful for stable entities like Teams where abbreviation is the natural key.
    """
    graph = graph or get_graph()
    start = datetime.now()

    if not graph.is_enabled:
        return SyncResult(success=True, duration_ms=0)

    try:
        query = f"""
        MERGE (n:{entity_type} {{{key_name}: $key_value}})
        SET n += $properties
        RETURN n
        """

        result = graph.run_write(query, {"key_value": key_value, "properties": properties})

        duration = (datetime.now() - start).total_seconds() * 1000
        return SyncResult(
            success=True,
            nodes_created=result.get("nodes_created", 0),
            nodes_updated=1 if result.get("properties_set", 0) > 0 else 0,
            duration_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() * 1000
        logger.error(f"Failed to sync {entity_type} {key_name}={key_value}: {e}")
        return SyncResult(success=False, errors=[str(e)], duration_ms=duration)


def sync_relationship(
    from_label: str,
    from_id: str | UUID,
    rel_type: str,
    to_label: str,
    to_id: str | UUID,
    properties: Optional[dict[str, Any]] = None,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a relationship between two nodes using MERGE.

    Creates the relationship if it doesn't exist, updates properties if it does.
    """
    graph = graph or get_graph()
    start = datetime.now()

    if not graph.is_enabled:
        return SyncResult(success=True, duration_ms=0)

    try:
        from_id_str = str(from_id)
        to_id_str = str(to_id)

        # Build MERGE query for relationship
        if properties:
            query = f"""
            MATCH (a:{from_label} {{id: $from_id}})
            MATCH (b:{to_label} {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN r
            """
            params = {"from_id": from_id_str, "to_id": to_id_str, "properties": properties}
        else:
            query = f"""
            MATCH (a:{from_label} {{id: $from_id}})
            MATCH (b:{to_label} {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """
            params = {"from_id": from_id_str, "to_id": to_id_str}

        result = graph.run_write(query, params)

        duration = (datetime.now() - start).total_seconds() * 1000
        return SyncResult(
            success=True,
            relationships_created=result.get("relationships_created", 0),
            duration_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() * 1000
        logger.error(f"Failed to sync relationship {from_label}-[{rel_type}]->{to_label}: {e}")
        return SyncResult(success=False, errors=[str(e)], duration_ms=duration)


def sync_relationship_by_keys(
    from_label: str,
    from_key: str,
    from_value: str,
    rel_type: str,
    to_label: str,
    to_key: str,
    to_value: str,
    properties: Optional[dict[str, Any]] = None,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a relationship using custom keys (not just 'id').

    Useful for Teams (keyed by abbr) and Divisions (keyed by name).
    """
    graph = graph or get_graph()
    start = datetime.now()

    if not graph.is_enabled:
        return SyncResult(success=True, duration_ms=0)

    try:
        if properties:
            query = f"""
            MATCH (a:{from_label} {{{from_key}: $from_value}})
            MATCH (b:{to_label} {{{to_key}: $to_value}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN r
            """
            params = {"from_value": from_value, "to_value": to_value, "properties": properties}
        else:
            query = f"""
            MATCH (a:{from_label} {{{from_key}: $from_value}})
            MATCH (b:{to_label} {{{to_key}: $to_value}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """
            params = {"from_value": from_value, "to_value": to_value}

        result = graph.run_write(query, params)

        duration = (datetime.now() - start).total_seconds() * 1000
        return SyncResult(
            success=True,
            relationships_created=result.get("relationships_created", 0),
            duration_ms=duration,
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds() * 1000
        logger.error(f"Failed to sync relationship {from_label}-[{rel_type}]->{to_label}: {e}")
        return SyncResult(success=False, errors=[str(e)], duration_ms=duration)


def full_sync(league: Any, graph: Optional[GraphConnection] = None) -> SyncResult:
    """
    Perform a full sync of all entities from a League object.

    This syncs:
    - All teams (with divisions/conferences)
    - All players on rosters
    - All game logs
    - Relationships between entities

    Args:
        league: The League object containing all game state
        graph: Optional graph connection (uses global if not provided)

    Returns:
        Combined SyncResult for the entire operation
    """
    graph = graph or get_graph()
    start = datetime.now()

    if not graph.is_enabled:
        logger.info("Graph disabled, skipping full sync")
        return SyncResult(success=True, duration_ms=0)

    logger.info("Starting full graph sync...")

    # Initialize schema first
    init_schema(graph)

    total_result = SyncResult(success=True)

    # Sync organizational structure (divisions, conferences)
    logger.info("Syncing organizational structure...")
    org_result = _sync_organization(graph)
    total_result = total_result + org_result

    # Sync teams
    logger.info(f"Syncing {len(league.teams)} teams...")
    for team in league.teams.values():
        team_result = _sync_team(team, graph)
        total_result = total_result + team_result

        # Sync players on this team's roster
        for player in team.roster.players.values():
            player_result = _sync_player(player, team, graph)
            total_result = total_result + player_result

    # Sync game logs
    logger.info(f"Syncing {len(league.game_logs)} game logs...")
    for game_id, game_log in league.game_logs.items():
        game_result = _sync_game(game_log, graph)
        total_result = total_result + game_result

    # Sync season stats relationships
    logger.info(f"Syncing {len(league.season_stats)} season stats...")
    for player_id, stats in league.season_stats.items():
        stats_result = _sync_season_stats(player_id, stats, league.season, graph)
        total_result = total_result + stats_result

    duration = (datetime.now() - start).total_seconds() * 1000
    total_result.duration_ms = duration

    logger.info(
        f"Full sync complete: {total_result.nodes_created} nodes created, "
        f"{total_result.relationships_created} relationships created, "
        f"{len(total_result.errors)} errors, {duration:.0f}ms"
    )

    return total_result


def _sync_organization(graph: GraphConnection) -> SyncResult:
    """Sync NFL organizational structure (conferences, divisions)."""
    result = SyncResult(success=True)

    # Create conferences
    conferences = ["AFC", "NFC"]
    for conf in conferences:
        r = sync_entity(NodeLabels.CONFERENCE, conf, {"name": conf}, graph)
        result = result + r

    # Create divisions with conference relationships
    divisions = {
        "AFC East": "AFC", "AFC North": "AFC", "AFC South": "AFC", "AFC West": "AFC",
        "NFC East": "NFC", "NFC North": "NFC", "NFC South": "NFC", "NFC West": "NFC",
    }

    for div_name, conf_name in divisions.items():
        r = sync_entity(NodeLabels.DIVISION, div_name, {"name": div_name}, graph)
        result = result + r
        r = sync_relationship(
            NodeLabels.DIVISION, div_name,
            RelTypes.IN_CONFERENCE,
            NodeLabels.CONFERENCE, conf_name,
            graph=graph
        )
        result = result + r

    return result


def _sync_team(team: Any, graph: GraphConnection) -> SyncResult:
    """Sync a single team to the graph.

    Teams are merged on abbreviation (not UUID) since they're stable entities.
    """
    from huddle.core.league.nfl_data import NFL_TEAMS

    abbr = team.abbreviation
    properties = {
        "id": str(team.id),  # Store UUID as property, not merge key
        "abbr": abbr,
        "name": team.name,
        "city": team.city,
        "overall": getattr(team, "offense_rating", 0) + getattr(team, "defense_rating", 0),
    }

    # Add tendencies if available
    if hasattr(team, "tendencies") and team.tendencies:
        properties["run_tendency"] = team.tendencies.run_tendency
        properties["aggression"] = team.tendencies.aggression
        properties["blitz_tendency"] = team.tendencies.blitz_tendency

    # Add financials if available
    if hasattr(team, "financials") and team.financials:
        properties["cap_room"] = team.financials.cap_room

    # Merge on abbr for teams (stable identifier)
    result = sync_entity_by_key(NodeLabels.TEAM, "abbr", abbr, properties, graph)

    # Sync division relationship - lookup from NFL_TEAMS data
    nfl_data = NFL_TEAMS.get(abbr)
    if nfl_data and nfl_data.division:
        # Division enum value is already "AFC East", "NFC West" etc.
        div_name = nfl_data.division.value
        r = sync_relationship_by_keys(
            NodeLabels.TEAM, "abbr", abbr,
            RelTypes.IN_DIVISION,
            NodeLabels.DIVISION, "name", div_name,
            graph=graph
        )
        result = result + r

    return result


def _sync_player(player: Any, team: Any, graph: GraphConnection) -> SyncResult:
    """Sync a single player to the graph."""
    properties = {
        "name": player.full_name,
        "position": player.position.value if hasattr(player.position, "value") else str(player.position),
        "age": player.age,
        "experience": player.experience_years,
        "overall": player.overall,
        "potential": player.potential,
        "team_id": str(team.id),
        "team_abbr": team.abbreviation,
    }

    # Add personality archetype if available
    if hasattr(player, "personality") and player.personality:
        if hasattr(player.personality, "archetype"):
            properties["personality_archetype"] = player.personality.archetype.value

    # Add physical attributes if available
    if hasattr(player, "height_inches"):
        properties["height_inches"] = player.height_inches
    if hasattr(player, "weight_lbs"):
        properties["weight_lbs"] = player.weight_lbs

    result = sync_entity(NodeLabels.PLAYER, player.id, properties, graph)

    # Sync PLAYS_FOR relationship
    r = sync_relationship(
        NodeLabels.PLAYER, player.id,
        RelTypes.PLAYS_FOR,
        NodeLabels.TEAM, team.id,
        {"since": player.years_on_team},
        graph
    )
    result = result + r

    return result


def _sync_game(game_log: Any, graph: GraphConnection) -> SyncResult:
    """Sync a game log to the graph."""
    properties = {
        "week": game_log.week,
        "home_team_abbr": game_log.home_team_abbr,
        "away_team_abbr": game_log.away_team_abbr,
        "home_score": game_log.home_score,
        "away_score": game_log.away_score,
        "is_overtime": getattr(game_log, "is_overtime", False),
        "is_playoff": getattr(game_log, "is_playoff", False),
    }

    result = sync_entity(NodeLabels.GAME, game_log.game_id, properties, graph)

    # Sync team relationships
    # Note: Would need team IDs here, currently have abbreviations
    # This is one place where the team_id improvement would help

    # Sync player participation (PLAYED_IN relationships)
    for player_id, stats in game_log.player_stats.items():
        stats_dict = {
            "passing_yards": getattr(stats.passing, "yards", 0),
            "passing_tds": getattr(stats.passing, "touchdowns", 0),
            "rushing_yards": getattr(stats.rushing, "yards", 0),
            "rushing_tds": getattr(stats.rushing, "touchdowns", 0),
            "receiving_yards": getattr(stats.receiving, "yards", 0),
            "receiving_tds": getattr(stats.receiving, "touchdowns", 0),
        }

        r = sync_relationship(
            NodeLabels.PLAYER, player_id,
            RelTypes.PLAYED_IN,
            NodeLabels.GAME, game_log.game_id,
            stats_dict,
            graph
        )
        result = result + r

    return result


def _sync_season_stats(
    player_id: str,
    stats: Any,
    season_year: int,
    graph: GraphConnection
) -> SyncResult:
    """Sync a player's season stats as a SEASON_STATS relationship."""
    # Ensure season node exists
    result = sync_entity(NodeLabels.SEASON, str(season_year), {"year": season_year}, graph)

    # Create SEASON_STATS relationship with aggregated stats
    stats_dict = {
        "games_played": getattr(stats, "games_played", 0),
        "passing_yards": getattr(stats.passing, "yards", 0) if hasattr(stats, "passing") else 0,
        "passing_tds": getattr(stats.passing, "touchdowns", 0) if hasattr(stats, "passing") else 0,
        "rushing_yards": getattr(stats.rushing, "yards", 0) if hasattr(stats, "rushing") else 0,
        "rushing_tds": getattr(stats.rushing, "touchdowns", 0) if hasattr(stats, "rushing") else 0,
        "receiving_yards": getattr(stats.receiving, "yards", 0) if hasattr(stats, "receiving") else 0,
        "receiving_tds": getattr(stats.receiving, "touchdowns", 0) if hasattr(stats, "receiving") else 0,
    }

    r = sync_relationship(
        NodeLabels.PLAYER, player_id,
        RelTypes.SEASON_STATS,
        NodeLabels.SEASON, str(season_year),
        stats_dict,
        graph
    )

    return result + r
