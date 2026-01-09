"""Game Manager - Bridge between Management and V2 Simulation.

The Game Manager layer transforms the v2 simulation "play sandbox" into a
complete game engine that produces meaningful outcomes for the career sim.

Core components:
- GameManager: Main orchestration (quarters, drives, scoring)
- DriveManager: Drive loop (plays until score/turnover)
- RosterBridge: Depth chart → v2 Player objects
- PlayAdapter: Playbook plays → V2 PlayConfig
- SpecialTeams: Statistical resolution for kicks
- ResultHandler: Stat extraction from play results
- Coordinator: AI play-calling
"""

from huddle.game.roster_bridge import RosterBridge, get_offensive_11, get_defensive_11
from huddle.game.play_adapter import PlayAdapter, build_play_config
from huddle.game.special_teams import SpecialTeamsResolver
from huddle.game.drive import DriveManager, DriveResult
from huddle.game.manager import GameManager, GameResult
from huddle.game.result_handler import (
    ResultHandler,
    GameStatSheet,
    PlayerGameStats,
    TeamGameStats,
    PassingStats,
    RushingStats,
    ReceivingStats,
    DefensiveStats,
)
from huddle.game.coordinator import (
    OffensiveCoordinator,
    DefensiveCoordinator,
    SituationContext,
    get_play_call,
)

__all__ = [
    # Roster bridge
    "RosterBridge",
    "get_offensive_11",
    "get_defensive_11",
    # Play adapter
    "PlayAdapter",
    "build_play_config",
    # Special teams
    "SpecialTeamsResolver",
    # Drive
    "DriveManager",
    "DriveResult",
    # Game manager
    "GameManager",
    "GameResult",
    # Result handler
    "ResultHandler",
    "GameStatSheet",
    "PlayerGameStats",
    "TeamGameStats",
    "PassingStats",
    "RushingStats",
    "ReceivingStats",
    "DefensiveStats",
    # Coordinator
    "OffensiveCoordinator",
    "DefensiveCoordinator",
    "SituationContext",
    "get_play_call",
]
