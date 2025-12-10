"""Core game models."""

from huddle.core.models.field import DownState, FieldPosition, FieldZone
from huddle.core.models.game import GameClock, GamePhase, GameState, PossessionState, ScoreState
from huddle.core.models.play import DefensiveCall, PlayCall, PlayResult
from huddle.core.models.player import Player
from huddle.core.models.stats import (
    DefensiveStats,
    GameLog,
    KickingStats,
    PassingStats,
    PlayerGameStats,
    PlayerSeasonStats,
    ReceivingStats,
    RushingStats,
    TeamGameStats,
)
from huddle.core.models.team import DepthChart, Roster, Team
from huddle.core.models.tendencies import (
    CapManagement,
    DefensiveScheme,
    DraftStrategy,
    FuturePickValue,
    NegotiationTone,
    OffensiveScheme,
    TeamTendencies,
    TradeAggression,
)
# Note: PositionalPhilosophy and PositionalPriority have been replaced by
# the HC09-style philosophy system in huddle.core.philosophy

__all__ = [
    "CapManagement",
    "DefensiveCall",
    "DefensiveScheme",
    "DefensiveStats",
    "DepthChart",
    "DownState",
    "DraftStrategy",
    "FieldPosition",
    "FieldZone",
    "FuturePickValue",
    "GameClock",
    "GameLog",
    "GamePhase",
    "GameState",
    "KickingStats",
    "NegotiationTone",
    "OffensiveScheme",
    "PassingStats",
    "PlayCall",
    "PlayResult",
    "Player",
    "PlayerGameStats",
    "PlayerSeasonStats",
    "PossessionState",
    "ReceivingStats",
    "Roster",
    "RushingStats",
    "ScoreState",
    "Team",
    "TeamGameStats",
    "TeamTendencies",
    "TradeAggression",
]
