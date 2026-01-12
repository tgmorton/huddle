"""
Graph module configuration.

Controls whether the graph database is enabled and connection settings.
All settings can be overridden via environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GraphConfig:
    """Configuration for the Neo4j graph database connection."""

    # Connection settings
    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    username: str = field(default_factory=lambda: os.getenv("NEO4J_USERNAME", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "huddlegraph"))
    database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))

    # Feature flag - graph is disabled by default
    enabled: bool = field(
        default_factory=lambda: os.getenv("GRAPH_ENABLED", "false").lower() == "true"
    )

    # Sync settings
    sync_batch_size: int = 100  # Nodes per batch during sync
    sync_timeout_seconds: int = 30  # Timeout for sync operations
    async_queue_size: int = 1000  # Max pending sync events during live game

    # Connection pool settings
    max_connection_lifetime: int = 3600  # 1 hour
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60

    @classmethod
    def from_env(cls) -> "GraphConfig":
        """Create config from environment variables."""
        return cls()

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors = []
        if not self.uri:
            errors.append("NEO4J_URI is required")
        if not self.username:
            errors.append("NEO4J_USERNAME is required")
        if not self.password:
            errors.append("NEO4J_PASSWORD is required")
        return errors


# Singleton config instance
_config: Optional[GraphConfig] = None


def get_config() -> GraphConfig:
    """Get the global graph configuration."""
    global _config
    if _config is None:
        _config = GraphConfig.from_env()
    return _config


def is_graph_enabled() -> bool:
    """Check if the graph database is enabled."""
    return get_config().enabled


def set_graph_enabled(enabled: bool) -> None:
    """
    Programmatically enable/disable the graph.

    Useful for testing or runtime toggling.
    """
    config = get_config()
    config.enabled = enabled
