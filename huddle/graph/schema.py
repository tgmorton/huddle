"""
Graph schema definition and initialization.

Defines node labels, relationship types, constraints, and indexes
for the football ontology.
"""

import logging
from typing import Optional

from huddle.graph.connection import GraphConnection, get_graph

logger = logging.getLogger(__name__)


# ============================================================================
# NODE LABELS
# ============================================================================

class NodeLabels:
    """All node labels in the graph."""

    # Core entities
    PLAYER = "Player"
    TEAM = "Team"
    GAME = "Game"
    SEASON = "Season"

    # Organizational
    DIVISION = "Division"
    CONFERENCE = "Conference"

    # Game structure
    DRIVE = "Drive"

    # Contracts and transactions
    CONTRACT = "Contract"
    TRANSACTION = "Transaction"

    # Computed/derived entities
    MATCHUP = "Matchup"  # Player vs Player history
    HEAD_TO_HEAD = "HeadToHead"  # Team vs Team history
    NARRATIVE = "Narrative"  # Detected storylines


# ============================================================================
# RELATIONSHIP TYPES
# ============================================================================

class RelTypes:
    """All relationship types in the graph."""

    # Player relationships
    PLAYS_FOR = "PLAYS_FOR"  # Player -> Team (current)
    PLAYED_FOR = "PLAYED_FOR"  # Player -> Team (historical)
    HAS_CONTRACT = "HAS_CONTRACT"  # Player -> Contract
    DRAFTED_BY = "DRAFTED_BY"  # Player -> Team
    TRADED_FROM = "TRADED_FROM"  # Player -> Team
    PLAYED_IN = "PLAYED_IN"  # Player -> Game (with stats)
    TEAMMATES_WITH = "TEAMMATES_WITH"  # Player <-> Player
    FACED = "FACED"  # Player -> Player (opponents)

    # Team relationships
    IN_DIVISION = "IN_DIVISION"  # Team -> Division
    IN_CONFERENCE = "IN_CONFERENCE"  # Division -> Conference
    RIVALS_WITH = "RIVALS_WITH"  # Team <-> Team
    HOME_TEAM = "HOME_TEAM"  # Game -> Team
    AWAY_TEAM = "AWAY_TEAM"  # Game -> Team
    WON = "WON"  # Team -> Game
    LOST = "LOST"  # Team -> Game

    # Game structure
    IN_SEASON = "IN_SEASON"  # Game -> Season
    CONTAINS = "CONTAINS"  # Game -> Drive, Drive -> Play
    SCORED_BY = "SCORED_BY"  # ScoringPlay -> Player

    # Narrative
    INVOLVED_IN = "INVOLVED_IN"  # Player/Team -> Narrative
    PART_OF = "PART_OF"  # Game -> Narrative

    # Temporal
    SEASON_STATS = "SEASON_STATS"  # Player -> Season (with stats)


# ============================================================================
# SCHEMA INITIALIZATION
# ============================================================================

# Constraints ensure uniqueness and improve query performance
CONSTRAINTS = [
    # Core entities - unique IDs
    "CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT team_abbr IF NOT EXISTS FOR (t:Team) REQUIRE t.abbr IS UNIQUE",
    "CREATE CONSTRAINT game_id IF NOT EXISTS FOR (g:Game) REQUIRE g.id IS UNIQUE",
    "CREATE CONSTRAINT season_year IF NOT EXISTS FOR (s:Season) REQUIRE s.year IS UNIQUE",
    "CREATE CONSTRAINT division_name IF NOT EXISTS FOR (d:Division) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT conference_name IF NOT EXISTS FOR (c:Conference) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT drive_id IF NOT EXISTS FOR (d:Drive) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT narrative_id IF NOT EXISTS FOR (n:Narrative) REQUIRE n.id IS UNIQUE",
]

# Indexes speed up common lookup patterns
INDEXES = [
    # Player lookups
    "CREATE INDEX player_name IF NOT EXISTS FOR (p:Player) ON (p.name)",
    "CREATE INDEX player_position IF NOT EXISTS FOR (p:Player) ON (p.position)",
    "CREATE INDEX player_team_id IF NOT EXISTS FOR (p:Player) ON (p.team_id)",

    # Team lookups
    "CREATE INDEX team_name IF NOT EXISTS FOR (t:Team) ON (t.name)",

    # Game lookups
    "CREATE INDEX game_week IF NOT EXISTS FOR (g:Game) ON (g.week)",
    "CREATE INDEX game_season IF NOT EXISTS FOR (g:Game) ON (g.season_year)",

    # Drive lookups
    "CREATE INDEX drive_game IF NOT EXISTS FOR (d:Drive) ON (d.game_id)",

    # Narrative lookups
    "CREATE INDEX narrative_type IF NOT EXISTS FOR (n:Narrative) ON (n.type)",
    "CREATE INDEX narrative_active IF NOT EXISTS FOR (n:Narrative) ON (n.is_active)",
]


def init_schema(graph: Optional[GraphConnection] = None) -> dict[str, int]:
    """
    Initialize the graph schema with constraints and indexes.

    Safe to run multiple times - uses IF NOT EXISTS.

    Returns:
        Dict with counts of constraints and indexes created
    """
    graph = graph or get_graph()

    if not graph.is_enabled:
        logger.info("Graph disabled, skipping schema initialization")
        return {"constraints": 0, "indexes": 0}

    if not graph.is_connected:
        if not graph.connect():
            logger.error("Cannot connect to Neo4j for schema initialization")
            return {"constraints": 0, "indexes": 0}

    constraints_created = 0
    indexes_created = 0

    with graph.session() as session:
        # Create constraints
        for constraint in CONSTRAINTS:
            try:
                session.run(constraint)
                constraints_created += 1
                logger.debug(f"Created constraint: {constraint[:50]}...")
            except Exception as e:
                # Constraint may already exist (not an error)
                logger.debug(f"Constraint exists or failed: {e}")

        # Create indexes
        for index in INDEXES:
            try:
                session.run(index)
                indexes_created += 1
                logger.debug(f"Created index: {index[:50]}...")
            except Exception as e:
                logger.debug(f"Index exists or failed: {e}")

    logger.info(f"Schema initialized: {constraints_created} constraints, {indexes_created} indexes")
    return {"constraints": constraints_created, "indexes": indexes_created}


def get_schema_info(graph: Optional[GraphConnection] = None) -> dict:
    """
    Get information about the current schema.

    Returns node labels, relationship types, constraints, and indexes.
    """
    graph = graph or get_graph()

    if not graph.is_connected:
        return {"error": "Not connected"}

    with graph.session() as session:
        # Get node labels
        labels_result = session.run("CALL db.labels()")
        labels = [record["label"] for record in labels_result]

        # Get relationship types
        rel_result = session.run("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in rel_result]

        # Get constraints
        constraints_result = session.run("SHOW CONSTRAINTS")
        constraints = [dict(record) for record in constraints_result]

        # Get indexes
        indexes_result = session.run("SHOW INDEXES")
        indexes = [dict(record) for record in indexes_result]

    return {
        "labels": labels,
        "relationship_types": rel_types,
        "constraints": constraints,
        "indexes": indexes,
    }


def get_stats(graph: Optional[GraphConnection] = None) -> dict:
    """
    Get graph statistics: node counts, relationship counts, etc.
    """
    graph = graph or get_graph()

    if not graph.is_connected:
        return {"error": "Not connected"}

    with graph.session() as session:
        # Count nodes by label
        node_counts = {}
        labels_result = session.run("CALL db.labels()")
        for record in labels_result:
            label = record["label"]
            count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            node_counts[label] = count_result.single()["count"]

        # Count relationships by type
        rel_counts = {}
        rel_result = session.run("CALL db.relationshipTypes()")
        for record in rel_result:
            rel_type = record["relationshipType"]
            count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
            rel_counts[rel_type] = count_result.single()["count"]

        # Total counts
        total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

    return {
        "total_nodes": total_nodes,
        "total_relationships": total_rels,
        "nodes_by_label": node_counts,
        "relationships_by_type": rel_counts,
    }
