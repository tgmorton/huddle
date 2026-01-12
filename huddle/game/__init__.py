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
from huddle.game.decision_logic import (
    FourthDownDecision,
    fourth_down_decision,
    get_fourth_down_go_probability,
    get_fourth_down_conversion_rate,
    should_go_for_two,
    Pace,
    select_pace,
    time_off_clock,
    should_call_timeout,
)
from huddle.game.game_log_converter import (
    convert_stat_sheet_to_game_log,
    create_game_log_from_result,
    persist_game_result,
    persist_game_to_session,
)
from huddle.game.penalties import (
    PenaltyType,
    PenaltyTiming,
    PenaltyInfo,
    PenaltyResult,
    PenaltyResolver,
    check_for_penalty,
    PENALTY_INFO,
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
    # Decision logic
    "FourthDownDecision",
    "fourth_down_decision",
    "get_fourth_down_go_probability",
    "get_fourth_down_conversion_rate",
    "should_go_for_two",
    "Pace",
    "select_pace",
    "time_off_clock",
    "should_call_timeout",
    # Game log converter
    "convert_stat_sheet_to_game_log",
    "create_game_log_from_result",
    "persist_game_result",
    "persist_game_to_session",
    # Penalties
    "PenaltyType",
    "PenaltyTiming",
    "PenaltyInfo",
    "PenaltyResult",
    "PenaltyResolver",
    "check_for_penalty",
    "PENALTY_INFO",
]
