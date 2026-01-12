"""
LLM-callable exploration tools.

These tools are designed to be called by AI agents (LLMs) to explore
the football world. They return structured data that can be used for
commentary, analysis, and narrative generation.

Each tool has:
- A clear name and description
- Well-defined input parameters
- Structured output suitable for LLM consumption
"""

import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional

from huddle.graph.connection import get_graph, is_graph_enabled
from huddle.graph.explore.traversal import GraphTraversal, GraphNode, explore
from huddle.graph.sync.computed import (
    calculate_career_phase,
    calculate_head_to_head,
    detect_narratives,
)

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@dataclass
class ToolResult:
    """Standardized tool result for LLM consumption."""
    success: bool
    data: Any
    summary: str  # Human-readable summary
    suggestions: list[str] = None  # Suggested follow-up explorations

    def to_dict(self) -> dict:
        return asdict(self)


def get_player_context(
    identifier: str,
    include_stats: bool = True,
    include_narratives: bool = True,
    include_teammates: bool = True,
) -> ToolResult:
    """
    Get rich context about a player for AI exploration.

    Args:
        identifier: Player name or ID
        include_stats: Include recent performance stats
        include_narratives: Include active narratives involving this player
        include_teammates: Include notable teammates

    Returns:
        ToolResult with player context data
    """
    if not is_graph_enabled():
        return ToolResult(
            success=False,
            data=None,
            summary="Graph is disabled",
        )

    traversal = GraphTraversal()
    player = traversal.explore("player", identifier)

    if not player:
        return ToolResult(
            success=False,
            data=None,
            summary=f"Player '{identifier}' not found",
            suggestions=["Try searching with full name", "Check spelling"],
        )

    # Build context
    context = {
        "player": player.to_dict(),
        "team": None,
        "career_phase": None,
        "recent_games": [],
        "narratives": [],
        "teammates": [],
    }

    # Get team
    teams = player.follow("PLAYS_FOR")
    if teams:
        context["team"] = teams[0].to_dict()

    # Get career phase from properties (synced via computed module)
    career_phase = player.get_property("career_phase")
    if career_phase:
        context["career_phase"] = {
            "phase": career_phase,
            "trajectory": player.get_property("trajectory", "unknown"),
            "years_from_peak": player.get_property("years_from_peak", 0),
        }

    # Get recent games
    if include_stats:
        games = player.follow("PLAYED_IN", limit=5)
        context["recent_games"] = [g.to_dict() for g in games]

    # Get narratives
    if include_narratives:
        narratives = player.follow("INVOLVED_IN")
        context["narratives"] = [n.to_dict() for n in narratives]

    # Get teammates
    if include_teammates and context["team"]:
        team_node = teams[0]
        teammates = team_node.follow("PLAYS_FOR", direction="incoming", limit=5)
        # Exclude the player themselves
        context["teammates"] = [
            t.to_dict() for t in teammates if t.id != player.id
        ][:5]

    # Generate summary
    name = player.get_property("name", identifier)
    position = player.get_property("position", "?")
    overall = player.get_property("overall", "?")
    team_name = context["team"]["properties"].get("name", "Unknown") if context["team"] else "Free Agent"

    summary = f"{name} ({position}, {overall} OVR) - {team_name}"
    if career_phase:
        summary += f" | Career: {career_phase}"

    suggestions = []
    if context["team"]:
        suggestions.append(f"Explore team: {team_name}")
    if context["recent_games"]:
        suggestions.append("Analyze recent game performance")
    if not context["narratives"]:
        suggestions.append("Check for emerging storylines")

    return ToolResult(
        success=True,
        data=context,
        summary=summary,
        suggestions=suggestions,
    )


def get_team_context(
    identifier: str,
    include_roster: bool = True,
    include_recent_games: bool = True,
    include_rivals: bool = True,
) -> ToolResult:
    """
    Get rich context about a team for AI exploration.

    Args:
        identifier: Team name, abbreviation, or ID
        include_roster: Include key roster players
        include_recent_games: Include recent game results
        include_rivals: Include division rivals

    Returns:
        ToolResult with team context data
    """
    if not is_graph_enabled():
        return ToolResult(
            success=False,
            data=None,
            summary="Graph is disabled",
        )

    traversal = GraphTraversal()
    team = traversal.explore("team", identifier)

    if not team:
        return ToolResult(
            success=False,
            data=None,
            summary=f"Team '{identifier}' not found",
            suggestions=["Try team abbreviation (e.g., 'PHI')", "Try full city name"],
        )

    context = {
        "team": team.to_dict(),
        "division": None,
        "conference": None,
        "roster": [],
        "recent_games": [],
        "rivals": [],
        "record": {"wins": 0, "losses": 0},
    }

    # Get division and conference
    divisions = team.follow("IN_DIVISION")
    if divisions:
        div = divisions[0]
        context["division"] = div.to_dict()
        conferences = div.follow("IN_CONFERENCE")
        if conferences:
            context["conference"] = conferences[0].to_dict()

    # Get roster
    if include_roster:
        players = team.follow("PLAYS_FOR", direction="incoming", limit=10)
        # Sort by overall if available
        sorted_players = sorted(
            players,
            key=lambda p: p.get_property("overall", 0),
            reverse=True,
        )
        context["roster"] = [p.to_dict() for p in sorted_players[:10]]

    # Get recent games
    if include_recent_games:
        won_games = team.follow("WON", limit=5)
        lost_games = team.follow("LOST", limit=5)
        context["recent_games"] = (
            [{"result": "W", **g.to_dict()} for g in won_games] +
            [{"result": "L", **g.to_dict()} for g in lost_games]
        )
        context["record"]["wins"] = team.count_relationships("WON")
        context["record"]["losses"] = team.count_relationships("LOST")

    # Get rivals
    if include_rivals:
        rivals = team.follow("RIVALS_WITH")
        context["rivals"] = [r.to_dict() for r in rivals]

    # Generate summary
    name = team.get_property("name", identifier)
    abbr = team.get_property("abbr", "???")
    record = context["record"]

    summary = f"{name} ({abbr}) - {record['wins']}-{record['losses']}"
    if context["division"]:
        div_name = context["division"]["properties"].get("name", "")
        summary += f" | {div_name}"

    suggestions = []
    if context["roster"]:
        top_player = context["roster"][0]["properties"].get("name", "Unknown")
        suggestions.append(f"Explore star player: {top_player}")
    if context["rivals"]:
        rival_name = context["rivals"][0]["properties"].get("name", "Rival")
        suggestions.append(f"Check rivalry history: vs {rival_name}")

    return ToolResult(
        success=True,
        data=context,
        summary=summary,
        suggestions=suggestions,
    )


def get_game_context(
    identifier: str,
    include_stats: bool = True,
    include_narratives: bool = True,
) -> ToolResult:
    """
    Get rich context about a game for AI exploration.

    Args:
        identifier: Game ID
        include_stats: Include detailed player stats
        include_narratives: Include relevant narratives

    Returns:
        ToolResult with game context data
    """
    if not is_graph_enabled():
        return ToolResult(
            success=False,
            data=None,
            summary="Graph is disabled",
        )

    traversal = GraphTraversal()
    game = traversal.explore("game", identifier)

    if not game:
        return ToolResult(
            success=False,
            data=None,
            summary=f"Game '{identifier}' not found",
        )

    context = {
        "game": game.to_dict(),
        "home_team": None,
        "away_team": None,
        "key_players": [],
        "narratives": [],
        "drives": [],
    }

    # Get teams
    home_teams = game.follow("HOME_TEAM")
    away_teams = game.follow("AWAY_TEAM")
    if home_teams:
        context["home_team"] = home_teams[0].to_dict()
    if away_teams:
        context["away_team"] = away_teams[0].to_dict()

    # Get key players (those who played in the game)
    if include_stats:
        players = game.follow("PLAYED_IN", direction="incoming", limit=20)
        # Sort by some criteria (yards, etc.)
        context["key_players"] = [p.to_dict() for p in players]

    # Get narratives
    if include_narratives:
        narratives = game.follow("PART_OF", direction="incoming")
        context["narratives"] = [n.to_dict() for n in narratives]

    # Get drives
    drives = game.follow("CONTAINS", limit=10)
    context["drives"] = [d.to_dict() for d in drives]

    # Generate summary
    home_score = game.get_property("home_score", 0)
    away_score = game.get_property("away_score", 0)
    home_abbr = game.get_property("home_team_abbr", "HOME")
    away_abbr = game.get_property("away_team_abbr", "AWAY")
    week = game.get_property("week", "?")

    summary = f"Week {week}: {away_abbr} {away_score} @ {home_abbr} {home_score}"

    suggestions = []
    if context["home_team"]:
        suggestions.append(f"Explore home team: {home_abbr}")
    if context["away_team"]:
        suggestions.append(f"Explore away team: {away_abbr}")
    if context["key_players"]:
        suggestions.append("Analyze key player performances")

    return ToolResult(
        success=True,
        data=context,
        summary=summary,
        suggestions=suggestions,
    )


def get_matchup_context(
    entity_a: str,
    entity_b: str,
    entity_type: str = "team",
) -> ToolResult:
    """
    Get context about a matchup between two entities.

    Args:
        entity_a: First team/player identifier
        entity_b: Second team/player identifier
        entity_type: "team" or "player"

    Returns:
        ToolResult with matchup analysis
    """
    if not is_graph_enabled():
        return ToolResult(
            success=False,
            data=None,
            summary="Graph is disabled",
        )

    traversal = GraphTraversal()
    node_a = traversal.explore(entity_type, entity_a)
    node_b = traversal.explore(entity_type, entity_b)

    if not node_a:
        return ToolResult(success=False, data=None, summary=f"'{entity_a}' not found")
    if not node_b:
        return ToolResult(success=False, data=None, summary=f"'{entity_b}' not found")

    context = {
        "entity_a": node_a.to_dict(),
        "entity_b": node_b.to_dict(),
        "head_to_head": None,
        "common_opponents": [],
        "key_matchups": [],
    }

    # Find path between them
    path = traversal.find_path(node_a, node_b, max_depth=3)
    if path:
        context["connection"] = path.describe()

    # For teams, look for games between them
    if entity_type == "team":
        # Find games where both participated
        query = """
        MATCH (a:Team {id: $a_id})-[:WON|LOST]->(g:Game)<-[:WON|LOST]-(b:Team {id: $b_id})
        RETURN g
        LIMIT 10
        """
        try:
            results = traversal.query(query, {"a_id": node_a.id, "b_id": node_b.id})
            context["head_to_head_games"] = [dict(r["g"]) for r in results]
        except Exception:
            pass

    # Generate summary
    name_a = node_a.get_property("name", entity_a)
    name_b = node_b.get_property("name", entity_b)

    h2h_games = len(context.get("head_to_head_games", []))
    summary = f"{name_a} vs {name_b}"
    if h2h_games > 0:
        summary += f" ({h2h_games} previous meetings)"

    suggestions = [
        f"Explore {name_a} in detail",
        f"Explore {name_b} in detail",
        "Find key individual matchups",
    ]

    return ToolResult(
        success=True,
        data=context,
        summary=summary,
        suggestions=suggestions,
    )


def search_players(
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    max_age: Optional[int] = None,
    team: Optional[str] = None,
    limit: int = 10,
) -> ToolResult:
    """
    Search for players matching criteria.

    Args:
        position: Filter by position (e.g., "QB", "WR")
        min_overall: Minimum overall rating
        max_age: Maximum age
        team: Filter by team abbreviation
        limit: Maximum results

    Returns:
        ToolResult with matching players
    """
    if not is_graph_enabled():
        return ToolResult(success=False, data=None, summary="Graph is disabled")

    # Build dynamic query
    conditions = []
    params = {"limit": limit}

    if position:
        conditions.append("p.position = $position")
        params["position"] = position.upper()
    if min_overall:
        conditions.append("p.overall >= $min_overall")
        params["min_overall"] = min_overall
    if max_age:
        conditions.append("p.age <= $max_age")
        params["max_age"] = max_age
    if team:
        conditions.append("p.team_abbr = $team")
        params["team"] = team.upper()

    where_clause = " AND ".join(conditions) if conditions else "true"

    query = f"""
    MATCH (p:Player)
    WHERE {where_clause}
    RETURN p
    ORDER BY p.overall DESC
    LIMIT $limit
    """

    try:
        traversal = GraphTraversal()
        results = traversal.query(query, params)
        players = [dict(r["p"]) for r in results]

        summary = f"Found {len(players)} players"
        if position:
            summary += f" at {position}"
        if team:
            summary += f" on {team}"

        return ToolResult(
            success=True,
            data={"players": players, "count": len(players)},
            summary=summary,
            suggestions=["Explore specific player for details"],
        )
    except Exception as e:
        return ToolResult(success=False, data=None, summary=f"Search failed: {e}")


def find_connection(
    entity_a: str,
    entity_b: str,
    max_depth: int = 4,
) -> ToolResult:
    """
    Find how two entities are connected in the graph.

    Useful for discovering non-obvious relationships for narratives.

    Args:
        entity_a: First entity (player name, team abbr, etc.)
        entity_b: Second entity
        max_depth: Maximum path length to search

    Returns:
        ToolResult with connection path
    """
    if not is_graph_enabled():
        return ToolResult(success=False, data=None, summary="Graph is disabled")

    traversal = GraphTraversal()

    # Try to find both entities (could be any type)
    node_a = None
    node_b = None

    for entity_type in ["player", "team", "game"]:
        if not node_a:
            node_a = traversal.explore(entity_type, entity_a)
        if not node_b:
            node_b = traversal.explore(entity_type, entity_b)

    if not node_a:
        return ToolResult(success=False, data=None, summary=f"'{entity_a}' not found")
    if not node_b:
        return ToolResult(success=False, data=None, summary=f"'{entity_b}' not found")

    path = traversal.find_path(node_a, node_b, max_depth)

    if path:
        return ToolResult(
            success=True,
            data={
                "path": path.describe(),
                "length": path.length,
                "start": node_a.to_dict(),
                "end": node_b.to_dict(),
            },
            summary=f"Connected via {path.length} relationships: {path.describe()}",
            suggestions=["Explore intermediate nodes for more context"],
        )
    else:
        return ToolResult(
            success=True,
            data={"path": None, "length": None},
            summary=f"No connection found within {max_depth} hops",
            suggestions=["Try increasing max_depth", "Entities may be unrelated"],
        )


# ============================================================================
# TOOL REGISTRY (for LLM integration)
# ============================================================================

TOOL_REGISTRY = {
    "get_player_context": {
        "function": get_player_context,
        "description": "Get comprehensive context about a player including team, stats, career phase, and narratives",
        "parameters": {
            "identifier": "Player name or ID (required)",
            "include_stats": "Include recent game stats (default: true)",
            "include_narratives": "Include active storylines (default: true)",
            "include_teammates": "Include notable teammates (default: true)",
        },
    },
    "get_team_context": {
        "function": get_team_context,
        "description": "Get comprehensive context about a team including roster, record, and rivals",
        "parameters": {
            "identifier": "Team name, abbreviation, or ID (required)",
            "include_roster": "Include key players (default: true)",
            "include_recent_games": "Include recent results (default: true)",
            "include_rivals": "Include division rivals (default: true)",
        },
    },
    "get_game_context": {
        "function": get_game_context,
        "description": "Get context about a specific game including teams, key players, and narratives",
        "parameters": {
            "identifier": "Game ID (required)",
            "include_stats": "Include player stats (default: true)",
            "include_narratives": "Include relevant storylines (default: true)",
        },
    },
    "get_matchup_context": {
        "function": get_matchup_context,
        "description": "Get analysis of a matchup between two teams or players",
        "parameters": {
            "entity_a": "First team/player (required)",
            "entity_b": "Second team/player (required)",
            "entity_type": "'team' or 'player' (default: 'team')",
        },
    },
    "search_players": {
        "function": search_players,
        "description": "Search for players matching specific criteria",
        "parameters": {
            "position": "Filter by position (e.g., 'QB')",
            "min_overall": "Minimum overall rating",
            "max_age": "Maximum age",
            "team": "Filter by team abbreviation",
            "limit": "Maximum results (default: 10)",
        },
    },
    "find_connection": {
        "function": find_connection,
        "description": "Find how two entities are connected in the graph",
        "parameters": {
            "entity_a": "First entity (required)",
            "entity_b": "Second entity (required)",
            "max_depth": "Maximum path length (default: 4)",
        },
    },
}


def get_tool_descriptions() -> list[dict]:
    """
    Get tool descriptions in a format suitable for LLM tool use.

    Returns a list of tool definitions that can be passed to an LLM.
    """
    return [
        {
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"],
        }
        for name, info in TOOL_REGISTRY.items()
    ]


def execute_tool(name: str, **kwargs) -> ToolResult:
    """
    Execute a tool by name with given parameters.

    Args:
        name: Tool name from registry
        **kwargs: Tool parameters

    Returns:
        ToolResult from the tool execution
    """
    if name not in TOOL_REGISTRY:
        return ToolResult(
            success=False,
            data=None,
            summary=f"Unknown tool: {name}",
            suggestions=[f"Available tools: {list(TOOL_REGISTRY.keys())}"],
        )

    tool_func = TOOL_REGISTRY[name]["function"]
    return tool_func(**kwargs)
