"""
Explore module for AI navigation of the graph.

Provides tools for LLMs to explore the football world semantically:
- Start from any entity and traverse relationships
- Find connections between entities
- Get rich context for narratives and commentary
- Query computed properties and trends

Usage:
    from huddle.graph.explore import explore, GraphTraversal

    # Quick start from any entity
    player = explore("player", "Jalen Hurts")
    team = explore("team", "PHI")

    # Full traversal API
    traversal = GraphTraversal()
    player = traversal.explore("player", "Jalen Hurts")
    team = player.follow("PLAYS_FOR")[0]
    path = traversal.find_path(player, another_player)

    # LLM-callable tools
    from huddle.graph.explore import get_player_context, get_team_context
    result = get_player_context("Jalen Hurts")

    # Context generation for commentary
    from huddle.graph.explore import ContextGenerator, get_game_context_queue
    generator = ContextGenerator()
    generator.generate_matchup_context("PHI", "DAL")
    cards = get_game_context_queue().get_relevant(limit=5)
"""

from huddle.graph.explore.traversal import (
    GraphNode,
    GraphPath,
    GraphTraversal,
    explore,
)

from huddle.graph.explore.tools import (
    ToolResult,
    get_player_context,
    get_team_context,
    get_game_context,
    get_matchup_context,
    search_players,
    find_connection,
    get_tool_descriptions,
    execute_tool,
    TOOL_REGISTRY,
)

from huddle.graph.explore.context import (
    ContextType,
    ContextCard,
    ContextQueue,
    ContextGenerator,
    get_game_context_queue,
    reset_game_context,
)

__all__ = [
    # Traversal
    "GraphNode",
    "GraphPath",
    "GraphTraversal",
    "explore",
    # Tools
    "ToolResult",
    "get_player_context",
    "get_team_context",
    "get_game_context",
    "get_matchup_context",
    "search_players",
    "find_connection",
    "get_tool_descriptions",
    "execute_tool",
    "TOOL_REGISTRY",
    # Context
    "ContextType",
    "ContextCard",
    "ContextQueue",
    "ContextGenerator",
    "get_game_context_queue",
    "reset_game_context",
]
