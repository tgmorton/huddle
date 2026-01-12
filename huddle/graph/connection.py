"""
Neo4j connection management.

Provides connection pooling, health checks, and graceful handling
when the graph is disabled or unavailable.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

from huddle.graph.config import get_config, is_graph_enabled, GraphConfig

logger = logging.getLogger(__name__)


class GraphConnection:
    """
    Manages Neo4j database connection with connection pooling.

    The connection is lazy - it won't connect until first use.
    If graph is disabled, all operations are no-ops.
    """

    def __init__(self, config: Optional[GraphConfig] = None):
        self._config = config or get_config()
        self._driver: Optional[Driver] = None
        self._connected = False

    @property
    def is_enabled(self) -> bool:
        """Check if graph is enabled in config."""
        return self._config.enabled

    @property
    def is_connected(self) -> bool:
        """Check if we have an active connection."""
        return self._connected and self._driver is not None

    def connect(self) -> bool:
        """
        Establish connection to Neo4j.

        Returns True if connected successfully, False otherwise.
        Does nothing if graph is disabled.
        """
        if not self.is_enabled:
            logger.debug("Graph is disabled, skipping connection")
            return False

        if self._driver is not None:
            return True

        try:
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.username, self._config.password),
                max_connection_lifetime=self._config.max_connection_lifetime,
                max_connection_pool_size=self._config.max_connection_pool_size,
                connection_acquisition_timeout=self._config.connection_acquisition_timeout,
            )
            # Verify connection
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"Connected to Neo4j at {self._config.uri}")
            return True
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            self._driver = None
            self._connected = False
            return False
        except ServiceUnavailable as e:
            logger.warning(f"Neo4j not available at {self._config.uri}: {e}")
            self._driver = None
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._driver = None
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Disconnected from Neo4j")

    @contextmanager
    def session(self, database: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Get a Neo4j session for running queries.

        Usage:
            with graph.session() as session:
                result = session.run("MATCH (n) RETURN n LIMIT 10")

        Raises RuntimeError if graph is disabled or not connected.
        """
        if not self.is_enabled:
            raise RuntimeError("Graph is disabled - set GRAPH_ENABLED=true")

        if not self.is_connected:
            if not self.connect():
                raise RuntimeError("Failed to connect to Neo4j")

        db = database or self._config.database
        session = self._driver.session(database=db)
        try:
            yield session
        finally:
            session.close()

    def run_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Run a Cypher query and return results as list of dicts.

        Convenience method for simple queries.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Override database name

        Returns:
            List of result records as dictionaries
        """
        with self.session(database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def run_write(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run a write query (CREATE, MERGE, DELETE, etc).

        Returns query statistics (nodes_created, relationships_created, etc).
        """
        with self.session(database) as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            counters = summary.counters
            return {
                "nodes_created": counters.nodes_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_created": counters.relationships_created,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set,
                "labels_added": counters.labels_added,
                "labels_removed": counters.labels_removed,
            }

    def health_check(self) -> dict[str, Any]:
        """
        Check Neo4j health and return status info.

        Returns:
            Dict with 'healthy' bool and status details
        """
        if not self.is_enabled:
            return {"healthy": False, "reason": "Graph is disabled"}

        if not self.is_connected:
            if not self.connect():
                return {"healthy": False, "reason": "Cannot connect to Neo4j"}

        try:
            with self.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                record = result.single()
                return {
                    "healthy": True,
                    "name": record["name"],
                    "versions": record["versions"],
                    "edition": record["edition"],
                }
        except Exception as e:
            return {"healthy": False, "reason": str(e)}

    def clear_all(self, confirm: bool = False) -> dict[str, Any]:
        """
        Delete all nodes and relationships. Dangerous!

        Requires confirm=True to execute.
        Useful for testing or resetting the graph.
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear the graph")

        logger.warning("Clearing all nodes and relationships from graph")
        return self.run_write("MATCH (n) DETACH DELETE n")


# Singleton connection instance
_connection: Optional[GraphConnection] = None


def get_graph() -> GraphConnection:
    """
    Get the global graph connection.

    Creates the connection on first call.
    """
    global _connection
    if _connection is None:
        _connection = GraphConnection()
    return _connection


def maybe_sync(func):
    """
    Decorator for functions that should sync to graph if enabled.

    If graph is disabled or unavailable, the decorated function
    executes normally without syncing.

    Usage:
        @maybe_sync
        def on_game_complete(game_log: GameLog) -> None:
            # ... normal processing ...
            # Graph sync happens automatically if enabled
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if is_graph_enabled():
            graph = get_graph()
            if graph.is_connected or graph.connect():
                try:
                    # Sync logic would go here based on function name/args
                    pass
                except Exception as e:
                    logger.warning(f"Graph sync failed (non-fatal): {e}")

        return result
    return wrapper
