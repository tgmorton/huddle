"""
Graph module for AI exploration of the football world.

This module provides a Neo4j-based graph projection of the game state,
enabling AI agents to explore entities and relationships semantically.

The graph is a READ-OPTIMIZED PROJECTION - the game's existing data models
remain the source of truth. The graph can be enabled/disabled without
affecting core game functionality.

Usage:
    from huddle.graph import get_graph, is_graph_enabled

    if is_graph_enabled():
        graph = get_graph()
        player = graph.explore("player", "Jalen Hurts")
        # ... traverse, query, discover

Quick start:
    1. Start Neo4j: docker compose up -d neo4j
    2. Set environment: GRAPH_ENABLED=true
    3. Sync data: python -m huddle.graph.sync
    4. Explore: http://localhost:7474

See docs/ai/GRAPH_ONTOLOGY.md for full documentation.
"""

from huddle.graph.config import GraphConfig, is_graph_enabled
from huddle.graph.connection import GraphConnection, get_graph

__all__ = [
    "GraphConfig",
    "GraphConnection",
    "get_graph",
    "is_graph_enabled",
]
