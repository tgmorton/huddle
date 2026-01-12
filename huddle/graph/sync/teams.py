"""
Team sync module.

Handles syncing Team entities and their relationships to the graph.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from huddle.graph.connection import GraphConnection, get_graph, is_graph_enabled
from huddle.graph.schema import NodeLabels, RelTypes
from huddle.graph.sync.base import SyncResult, sync_entity, sync_relationship

logger = logging.getLogger(__name__)

# NFL organizational structure
NFL_STRUCTURE = {
    "AFC": {
        "AFC East": ["BUF", "MIA", "NE", "NYJ"],
        "AFC North": ["BAL", "CIN", "CLE", "PIT"],
        "AFC South": ["HOU", "IND", "JAX", "TEN"],
        "AFC West": ["DEN", "KC", "LV", "LAC"],
    },
    "NFC": {
        "NFC East": ["DAL", "NYG", "PHI", "WAS"],
        "NFC North": ["CHI", "DET", "GB", "MIN"],
        "NFC South": ["ATL", "CAR", "NO", "TB"],
        "NFC West": ["ARI", "LAR", "SF", "SEA"],
    },
}

# Flatten for quick lookup
TEAM_TO_DIVISION = {}
TEAM_TO_CONFERENCE = {}
for conf, divisions in NFL_STRUCTURE.items():
    for div, teams in divisions.items():
        for team in teams:
            TEAM_TO_DIVISION[team] = div
            TEAM_TO_CONFERENCE[team] = conf


def sync_team(
    team: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync a team to the graph.

    Creates/updates the Team node and relationships:
    - IN_DIVISION -> Division
    - Division -[IN_CONFERENCE]-> Conference

    Args:
        team: Team object to sync
        graph: Optional graph connection

    Returns:
        SyncResult with operation stats
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # Build team properties
    properties = _extract_team_properties(team)

    # Sync the team node
    r = sync_entity(NodeLabels.TEAM, team.id, properties, graph)
    result = result + r

    # Sync organizational relationships
    abbr = team.abbreviation
    if abbr in TEAM_TO_DIVISION:
        division = TEAM_TO_DIVISION[abbr]
        conference = TEAM_TO_CONFERENCE[abbr]

        # Ensure division exists
        r = sync_entity(NodeLabels.DIVISION, division, {"name": division}, graph)
        result = result + r

        # Ensure conference exists
        r = sync_entity(NodeLabels.CONFERENCE, conference, {"name": conference}, graph)
        result = result + r

        # Team -> Division
        r = sync_relationship(
            NodeLabels.TEAM, team.id,
            RelTypes.IN_DIVISION,
            NodeLabels.DIVISION, division,
            graph=graph
        )
        result = result + r

        # Division -> Conference
        r = sync_relationship(
            NodeLabels.DIVISION, division,
            RelTypes.IN_CONFERENCE,
            NodeLabels.CONFERENCE, conference,
            graph=graph
        )
        result = result + r

    return result


def sync_team_roster(
    team: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync all players on a team's roster.

    Creates Player nodes and PLAYS_FOR relationships for all rostered players.
    """
    from huddle.graph.sync.players import sync_player

    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    if not hasattr(team, "roster") or not team.roster:
        return result

    players = team.roster.players
    if not players:
        return result

    logger.info(f"Syncing {len(players)} players for {team.abbreviation}")

    for player in players.values():
        r = sync_player(player, team, graph)
        result = result + r

    return result


def sync_rivalry(
    team_a_id: UUID,
    team_b_id: UUID,
    intensity: str = "division",
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Sync RIVALS_WITH relationship between two teams.

    Args:
        team_a_id: First team's ID
        team_b_id: Second team's ID
        intensity: "division", "conference", or "historic"
        graph: Optional graph connection
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    return sync_relationship(
        NodeLabels.TEAM, team_a_id,
        RelTypes.RIVALS_WITH,
        NodeLabels.TEAM, team_b_id,
        {"intensity": intensity},
        graph
    )


def sync_division_rivalries(
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Create RIVALS_WITH relationships for all division rivals.

    Teams in the same division are automatic rivals.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    # For each division, create rivalry relationships between all teams
    for conf, divisions in NFL_STRUCTURE.items():
        for div, teams in divisions.items():
            # Create pairs within division
            for i, team_a in enumerate(teams):
                for team_b in teams[i + 1:]:
                    # Use abbreviation as ID since that's what we have
                    # In practice, would need to look up actual team IDs
                    r = _sync_rivalry_by_abbr(team_a, team_b, "division", graph)
                    result = result + r

    return result


def _sync_rivalry_by_abbr(
    abbr_a: str,
    abbr_b: str,
    intensity: str,
    graph: GraphConnection,
) -> SyncResult:
    """Create rivalry relationship using team abbreviations."""
    query = """
    MATCH (a:Team {abbr: $abbr_a})
    MATCH (b:Team {abbr: $abbr_b})
    MERGE (a)-[r:RIVALS_WITH]->(b)
    SET r.intensity = $intensity
    RETURN r
    """

    try:
        graph.run_write(query, {"abbr_a": abbr_a, "abbr_b": abbr_b, "intensity": intensity})
        return SyncResult(success=True, relationships_created=1)
    except Exception as e:
        logger.warning(f"Failed to create rivalry {abbr_a} vs {abbr_b}: {e}")
        return SyncResult(success=False, errors=[str(e)])


def _extract_team_properties(team: Any) -> dict[str, Any]:
    """Extract properties from a Team object for the graph node."""
    properties = {
        "abbr": team.abbreviation,
        "name": team.name,
        "city": team.city,
    }

    # Tendencies
    if hasattr(team, "tendencies") and team.tendencies:
        t = team.tendencies
        properties["run_tendency"] = getattr(t, "run_tendency", 0.5)
        properties["aggression"] = getattr(t, "aggression", 0.5)
        properties["blitz_tendency"] = getattr(t, "blitz_tendency", 0.3)

    # Financials
    if hasattr(team, "financials") and team.financials:
        f = team.financials
        properties["salary_cap"] = getattr(f, "salary_cap", 255_000_000)
        properties["cap_room"] = getattr(f, "cap_room", 0)
        properties["dead_money"] = getattr(f, "dead_money", 0)

    # Computed ratings
    if hasattr(team, "offense_rating"):
        properties["offense_rating"] = team.offense_rating
    if hasattr(team, "defense_rating"):
        properties["defense_rating"] = team.defense_rating

    # Status
    if hasattr(team, "status") and team.status:
        s = team.status
        if hasattr(s, "window"):
            properties["championship_window"] = s.window.value if hasattr(s.window, "value") else str(s.window)

    return properties


def get_division_for_team(abbr: str) -> Optional[str]:
    """Get division name for a team abbreviation."""
    return TEAM_TO_DIVISION.get(abbr)


def get_conference_for_team(abbr: str) -> Optional[str]:
    """Get conference name for a team abbreviation."""
    return TEAM_TO_CONFERENCE.get(abbr)


def get_division_rivals(abbr: str) -> list[str]:
    """Get list of division rivals for a team."""
    division = TEAM_TO_DIVISION.get(abbr)
    if not division:
        return []

    for conf, divisions in NFL_STRUCTURE.items():
        if division in divisions:
            return [t for t in divisions[division] if t != abbr]

    return []
