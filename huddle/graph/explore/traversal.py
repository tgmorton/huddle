"""
Graph traversal utilities for AI exploration.

Provides high-level traversal operations that AI agents can use
to navigate the football world semantically.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from huddle.graph.connection import GraphConnection, get_graph, is_graph_enabled
from huddle.graph.schema import NodeLabels, RelTypes

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """
    A node in the graph with its properties and traversal methods.

    This is the primary interface for AI exploration - start from any node
    and follow relationships to discover connected entities.
    """
    id: str
    label: str
    properties: dict = field(default_factory=dict)
    _graph: GraphConnection = field(default=None, repr=False)

    def __post_init__(self):
        if self._graph is None:
            self._graph = get_graph()

    def follow(
        self,
        relationship: str,
        direction: str = "outgoing",
        limit: int = 10,
    ) -> list["GraphNode"]:
        """
        Follow a relationship to connected nodes.

        Args:
            relationship: Relationship type (e.g., "PLAYS_FOR", "PLAYED_IN")
            direction: "outgoing", "incoming", or "both"
            limit: Maximum nodes to return

        Returns:
            List of connected GraphNode objects
        """
        if direction == "outgoing":
            pattern = f"(a)-[r:{relationship}]->(b)"
        elif direction == "incoming":
            pattern = f"(a)<-[r:{relationship}]-(b)"
        else:
            pattern = f"(a)-[r:{relationship}]-(b)"

        query = f"""
        MATCH {pattern}
        WHERE a.id = $id
        RETURN b, labels(b) as labels, r
        LIMIT $limit
        """

        try:
            results = self._graph.run_query(query, {"id": self.id, "limit": limit})
            nodes = []
            for record in results:
                node_data = dict(record["b"])
                labels = record["labels"]
                label = labels[0] if labels else "Unknown"
                nodes.append(GraphNode(
                    id=node_data.get("id", ""),
                    label=label,
                    properties=node_data,
                    _graph=self._graph,
                ))
            return nodes
        except Exception as e:
            logger.error(f"Failed to follow {relationship}: {e}")
            return []

    def get_property(self, name: str, default: Any = None) -> Any:
        """Get a property value."""
        return self.properties.get(name, default)

    def has_relationship(self, relationship: str, target_id: Optional[str] = None) -> bool:
        """Check if this node has a specific relationship."""
        if target_id:
            query = f"""
            MATCH (a {{id: $id}})-[r:{relationship}]->(b {{id: $target_id}})
            RETURN count(r) > 0 as exists
            """
            params = {"id": self.id, "target_id": target_id}
        else:
            query = f"""
            MATCH (a {{id: $id}})-[r:{relationship}]->()
            RETURN count(r) > 0 as exists
            """
            params = {"id": self.id}

        try:
            results = self._graph.run_query(query, params)
            return results[0]["exists"] if results else False
        except Exception:
            return False

    def count_relationships(self, relationship: str) -> int:
        """Count relationships of a specific type."""
        query = f"""
        MATCH (a {{id: $id}})-[r:{relationship}]->()
        RETURN count(r) as count
        """
        try:
            results = self._graph.run_query(query, {"id": self.id})
            return results[0]["count"] if results else 0
        except Exception:
            return 0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "label": self.label,
            "properties": self.properties,
        }

    def __repr__(self) -> str:
        name = self.properties.get("name", self.properties.get("abbr", self.id))
        return f"<{self.label}: {name}>"


@dataclass
class GraphPath:
    """A path through the graph connecting two nodes."""
    start: GraphNode
    end: GraphNode
    nodes: list[GraphNode]
    relationships: list[str]
    length: int

    def describe(self) -> str:
        """Generate a human-readable description of the path."""
        if self.length == 0:
            return f"{self.start} (same node)"

        parts = [str(self.start)]
        for i, rel in enumerate(self.relationships):
            parts.append(f"-[{rel}]->")
            if i < len(self.nodes):
                parts.append(str(self.nodes[i]))
        parts.append(str(self.end))
        return " ".join(parts)


class GraphTraversal:
    """
    High-level graph traversal operations.

    Provides semantic navigation methods for AI agents.
    """

    def __init__(self, graph: Optional[GraphConnection] = None):
        self._graph = graph or get_graph()

    def explore(self, entity_type: str, identifier: str) -> Optional[GraphNode]:
        """
        Start exploration from any entity.

        Args:
            entity_type: "player", "team", "game", etc.
            identifier: ID, name, or abbreviation

        Returns:
            GraphNode if found, None otherwise

        Examples:
            explore("player", "Jalen Hurts")
            explore("team", "PHI")
            explore("game", "game_123")
        """
        label = self._normalize_label(entity_type)

        # Try exact ID match first
        query = f"""
        MATCH (n:{label} {{id: $id}})
        RETURN n, labels(n) as labels
        """
        results = self._graph.run_query(query, {"id": identifier})

        if not results:
            # Try name/abbr match
            query = f"""
            MATCH (n:{label})
            WHERE n.name = $identifier OR n.abbr = $identifier
            RETURN n, labels(n) as labels
            LIMIT 1
            """
            results = self._graph.run_query(query, {"identifier": identifier})

        if results:
            node_data = dict(results[0]["n"])
            labels = results[0]["labels"]
            return GraphNode(
                id=node_data.get("id", identifier),
                label=labels[0] if labels else label,
                properties=node_data,
                _graph=self._graph,
            )

        return None

    def find_path(
        self,
        start: GraphNode,
        end: GraphNode,
        max_depth: int = 4,
    ) -> Optional[GraphPath]:
        """
        Find the shortest path between two nodes.

        Args:
            start: Starting node
            end: Ending node
            max_depth: Maximum path length to search

        Returns:
            GraphPath if found, None otherwise
        """
        query = """
        MATCH (a {id: $start_id}), (b {id: $end_id})
        MATCH path = shortestPath((a)-[*..%d]-(b))
        RETURN path, [r in relationships(path) | type(r)] as rel_types
        """ % max_depth

        try:
            results = self._graph.run_query(query, {
                "start_id": start.id,
                "end_id": end.id,
            })

            if not results:
                return None

            path_data = results[0]["path"]
            rel_types = results[0]["rel_types"]

            # Extract intermediate nodes
            nodes = []
            for node in path_data.nodes[1:-1]:  # Exclude start and end
                node_dict = dict(node)
                labels = list(node.labels)
                nodes.append(GraphNode(
                    id=node_dict.get("id", ""),
                    label=labels[0] if labels else "Unknown",
                    properties=node_dict,
                    _graph=self._graph,
                ))

            return GraphPath(
                start=start,
                end=end,
                nodes=nodes,
                relationships=rel_types,
                length=len(rel_types),
            )
        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return None

    def find_similar(
        self,
        node: GraphNode,
        by: str = "properties",
        limit: int = 5,
    ) -> list[GraphNode]:
        """
        Find nodes similar to the given node.

        Args:
            node: Reference node
            by: Similarity criteria - "properties", "connections", "position"
            limit: Maximum results

        Returns:
            List of similar nodes
        """
        if by == "position" and node.label == "Player":
            # Find players at same position
            position = node.properties.get("position", "")
            query = """
            MATCH (n:Player)
            WHERE n.position = $position AND n.id <> $id
            RETURN n, labels(n) as labels
            ORDER BY abs(n.overall - $overall)
            LIMIT $limit
            """
            params = {
                "position": position,
                "id": node.id,
                "overall": node.properties.get("overall", 75),
                "limit": limit,
            }
        elif by == "connections":
            # Find nodes with similar connection patterns
            query = """
            MATCH (a {id: $id})-[r]->(common)<-[r2]-(similar)
            WHERE similar.id <> $id
            WITH similar, count(common) as shared
            ORDER BY shared DESC
            LIMIT $limit
            MATCH (similar)
            RETURN similar as n, labels(similar) as labels
            """
            params = {"id": node.id, "limit": limit}
        else:
            # Default: similar properties
            if node.label == "Player":
                query = """
                MATCH (n:Player)
                WHERE n.id <> $id
                AND n.position = $position
                AND abs(n.age - $age) <= 3
                AND abs(n.overall - $overall) <= 5
                RETURN n, labels(n) as labels
                LIMIT $limit
                """
                params = {
                    "id": node.id,
                    "position": node.properties.get("position", ""),
                    "age": node.properties.get("age", 25),
                    "overall": node.properties.get("overall", 75),
                    "limit": limit,
                }
            else:
                # Generic label match
                query = f"""
                MATCH (n:{node.label})
                WHERE n.id <> $id
                RETURN n, labels(n) as labels
                LIMIT $limit
                """
                params = {"id": node.id, "limit": limit}

        try:
            results = self._graph.run_query(query, params)
            return [
                GraphNode(
                    id=dict(r["n"]).get("id", ""),
                    label=r["labels"][0] if r["labels"] else node.label,
                    properties=dict(r["n"]),
                    _graph=self._graph,
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Failed to find similar: {e}")
            return []

    def query(
        self,
        cypher: str,
        parameters: Optional[dict] = None,
    ) -> list[dict]:
        """
        Execute a raw Cypher query.

        For advanced exploration when high-level methods aren't sufficient.

        Args:
            cypher: Cypher query string
            parameters: Query parameters

        Returns:
            Query results as list of dicts
        """
        return self._graph.run_query(cypher, parameters or {})

    def _normalize_label(self, entity_type: str) -> str:
        """Normalize entity type to graph label."""
        mapping = {
            "player": NodeLabels.PLAYER,
            "team": NodeLabels.TEAM,
            "game": NodeLabels.GAME,
            "season": NodeLabels.SEASON,
            "division": NodeLabels.DIVISION,
            "conference": NodeLabels.CONFERENCE,
            "drive": NodeLabels.DRIVE,
            "contract": NodeLabels.CONTRACT,
            "narrative": NodeLabels.NARRATIVE,
        }
        return mapping.get(entity_type.lower(), entity_type)


# Convenience function
def explore(entity_type: str, identifier: str) -> Optional[GraphNode]:
    """
    Quick exploration entry point.

    Usage:
        player = explore("player", "Jalen Hurts")
        team = explore("team", "PHI")
    """
    traversal = GraphTraversal()
    return traversal.explore(entity_type, identifier)
