"""Sandbox simulation for 1v1 blocking matchups."""

from .blocking_resolver import BlockingSimulator
from .models import (
    BlockerTechnique,
    MatchupOutcome,
    MatchupState,
    PlayerRole,
    Position2D,
    RusherTechnique,
    SandboxPlayer,
    SimulationState,
    TickResult,
)
from .session_manager import SandboxSession, SandboxSessionManager, get_session_manager
from .route_sim import RouteSimulator, RouteType, CoverageType
from .team_route_sim import (
    TeamRouteSimulator,
    Formation,
    CoverageScheme,
    RouteConcept,
)
from .play_sim import (
    PlaySimulator,
    PlaySimState,
    TeamQB,
    QBAttributes,
    Ball,
    PlayResult,
)

__all__ = [
    "BlockingSimulator",
    "SandboxPlayer",
    "TickResult",
    "SimulationState",
    "MatchupState",
    "MatchupOutcome",
    "RusherTechnique",
    "BlockerTechnique",
    "PlayerRole",
    "Position2D",
    "SandboxSession",
    "SandboxSessionManager",
    "get_session_manager",
    # Route sim
    "RouteSimulator",
    "RouteType",
    "CoverageType",
    # Team route sim
    "TeamRouteSimulator",
    "Formation",
    "CoverageScheme",
    "RouteConcept",
    # Play sim
    "PlaySimulator",
    "PlaySimState",
    "TeamQB",
    "QBAttributes",
    "Ball",
    "PlayResult",
]
