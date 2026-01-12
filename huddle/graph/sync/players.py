"""
Player sync module.

Handles syncing Player entities and their relationships to the graph.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from huddle.graph.connection import GraphConnection, get_graph, is_graph_enabled
from huddle.graph.schema import NodeLabels, RelTypes
from huddle.graph.sync.base import SyncResult, sync_entity, sync_relationship

logger = logging.getLogger(__name__)


def sync_player(
    player: Any,
    team: Optional[Any] = None,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a player to the graph.

    Creates/updates the Player node and relationships:
    - PLAYS_FOR -> Team (if team provided or player.team_id exists)
    - HAS_CONTRACT -> Contract (if contract exists)

    Args:
        player: Player object to sync
        team: Optional Team the player is on (for PLAYS_FOR relationship)
        graph: Optional graph connection

    Returns:
        SyncResult with operation stats
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # Build player properties
    properties = _extract_player_properties(player)

    # Add team info - prefer player.team_id if available (new field from management_agent)
    team_id = None
    if hasattr(player, "team_id") and player.team_id:
        team_id = player.team_id
        properties["team_id"] = str(team_id)
    elif team:
        team_id = team.id
        properties["team_id"] = str(team.id)
        properties["team_abbr"] = team.abbreviation

    # Sync the player node
    r = sync_entity(NodeLabels.PLAYER, player.id, properties, graph)
    result = result + r

    # Sync PLAYS_FOR relationship if we have team info
    if team_id:
        role = _get_player_role(player, team) if team else "roster"
        r = sync_relationship(
            NodeLabels.PLAYER, player.id,
            RelTypes.PLAYS_FOR,
            NodeLabels.TEAM, team_id,
            {"since": player.years_on_team, "role": role},
            graph
        )
        result = result + r

    # Sync contract if exists
    if hasattr(player, "contract") and player.contract:
        r = _sync_player_contract(player, graph)
        result = result + r

    return result


def sync_player_stats(
    player_id: str | UUID,
    game_id: str,
    stats: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a player's stats for a specific game.

    Creates PLAYED_IN relationship between Player and Game with stats as properties.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    stats_dict = _extract_stats_properties(stats)

    return sync_relationship(
        NodeLabels.PLAYER, str(player_id),
        RelTypes.PLAYED_IN,
        NodeLabels.GAME, game_id,
        stats_dict,
        graph
    )


def sync_teammates(
    player_a_id: UUID,
    player_b_id: UUID,
    seasons_together: int = 1,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync TEAMMATES_WITH relationship between two players.

    This is a bidirectional relationship indicating players on the same team.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    # Create relationship in one direction (Neo4j handles undirected semantically)
    return sync_relationship(
        NodeLabels.PLAYER, player_a_id,
        RelTypes.TEAMMATES_WITH,
        NodeLabels.PLAYER, player_b_id,
        {"seasons": seasons_together},
        graph
    )


def sync_player_faced(
    player_a_id: UUID,
    player_b_id: UUID,
    games_faced: int = 1,
    stats: Optional[dict] = None,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync FACED relationship between two players who played against each other.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    properties = {"games": games_faced}
    if stats:
        properties.update(stats)

    return sync_relationship(
        NodeLabels.PLAYER, player_a_id,
        RelTypes.FACED,
        NodeLabels.PLAYER, player_b_id,
        properties,
        graph
    )


def _extract_player_properties(player: Any) -> dict[str, Any]:
    """Extract properties from a Player object for the graph node."""
    properties = {
        "name": player.full_name,
        "position": player.position.value if hasattr(player.position, "value") else str(player.position),
        "age": player.age,
        "experience": player.experience_years,
        "overall": player.overall,
        "potential": player.potential,
    }

    # Physical attributes
    if hasattr(player, "height_inches") and player.height_inches:
        properties["height_inches"] = player.height_inches
    if hasattr(player, "weight_lbs") and player.weight_lbs:
        properties["weight_lbs"] = player.weight_lbs

    # Combine measurables
    if hasattr(player, "forty_yard_dash") and player.forty_yard_dash:
        properties["forty_time"] = player.forty_yard_dash

    # Personality
    if hasattr(player, "personality") and player.personality:
        if hasattr(player.personality, "archetype") and player.personality.archetype:
            properties["personality_archetype"] = player.personality.archetype.value

    # Draft info
    if hasattr(player, "draft_year") and player.draft_year:
        properties["draft_year"] = player.draft_year
    if hasattr(player, "draft_round") and player.draft_round:
        properties["draft_round"] = player.draft_round
    if hasattr(player, "draft_pick") and player.draft_pick:
        properties["draft_pick"] = player.draft_pick

    # College
    if hasattr(player, "college") and player.college:
        properties["college"] = player.college

    # Contract summary
    if hasattr(player, "current_salary"):
        properties["salary"] = player.current_salary
    if hasattr(player, "contract_years"):
        properties["contract_years"] = player.contract_years

    return properties


def _extract_stats_properties(stats: Any) -> dict[str, Any]:
    """Extract stats properties for PLAYED_IN relationship."""
    properties = {}

    # Passing
    if hasattr(stats, "passing") and stats.passing:
        p = stats.passing
        properties["passing_attempts"] = getattr(p, "attempts", 0)
        properties["passing_completions"] = getattr(p, "completions", 0)
        properties["passing_yards"] = getattr(p, "yards", 0)
        properties["passing_tds"] = getattr(p, "touchdowns", 0)
        properties["passing_ints"] = getattr(p, "interceptions", 0)

    # Rushing
    if hasattr(stats, "rushing") and stats.rushing:
        r = stats.rushing
        properties["rushing_attempts"] = getattr(r, "attempts", 0)
        properties["rushing_yards"] = getattr(r, "yards", 0)
        properties["rushing_tds"] = getattr(r, "touchdowns", 0)

    # Receiving
    if hasattr(stats, "receiving") and stats.receiving:
        rec = stats.receiving
        properties["receiving_targets"] = getattr(rec, "targets", 0)
        properties["receiving_receptions"] = getattr(rec, "receptions", 0)
        properties["receiving_yards"] = getattr(rec, "yards", 0)
        properties["receiving_tds"] = getattr(rec, "touchdowns", 0)

    # Defense
    if hasattr(stats, "defense") and stats.defense:
        d = stats.defense
        properties["tackles"] = getattr(d, "tackles", 0)
        properties["sacks"] = getattr(d, "sacks", 0)
        properties["interceptions"] = getattr(d, "interceptions", 0)
        properties["passes_defended"] = getattr(d, "passes_defended", 0)

    return properties


def _get_player_role(player: Any, team: Any) -> str:
    """Determine player's role on the team (starter, backup, etc)."""
    if not hasattr(team, "roster") or not team.roster:
        return "unknown"

    depth_chart = team.roster.depth_chart
    if not depth_chart:
        return "roster"

    # Check if player is a starter
    position = player.position.value if hasattr(player.position, "value") else str(player.position)
    starter_slot = f"{position}1"

    if hasattr(depth_chart, "get") and depth_chart.get(starter_slot) == player.id:
        return "starter"

    # Check depth
    for i in range(2, 5):
        slot = f"{position}{i}"
        if hasattr(depth_chart, "get") and depth_chart.get(slot) == player.id:
            return f"depth_{i}"

    return "roster"


def _sync_player_contract(player: Any, graph: GraphConnection) -> SyncResult:
    """Sync a player's contract to the graph."""
    contract = player.contract
    if not contract:
        return SyncResult(success=True)

    # Create contract node
    contract_id = f"{player.id}_contract"
    properties = {
        "player_id": str(player.id),
        "total_value": getattr(contract, "total_value", 0),
        "years_remaining": getattr(contract, "years_remaining", 0),
        "cap_hit": getattr(contract, "cap_hit", player.current_salary if hasattr(player, "current_salary") else 0),
        "is_rookie_deal": getattr(contract, "is_rookie_deal", False),
    }

    result = sync_entity(NodeLabels.CONTRACT, contract_id, properties, graph)

    # Create HAS_CONTRACT relationship
    r = sync_relationship(
        NodeLabels.PLAYER, player.id,
        RelTypes.HAS_CONTRACT,
        NodeLabels.CONTRACT, contract_id,
        graph=graph
    )

    return result + r
