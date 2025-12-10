"""Pydantic schemas for API request/response models."""

from huddle.api.schemas.game import (
    CreateGameRequest,
    DownStateSchema,
    GameClockSchema,
    GameSettingsUpdate,
    GameStateSchema,
    PlayCallRequest,
    PlayResultSchema,
    PossessionStateSchema,
    ScoreStateSchema,
)
from huddle.api.schemas.team import (
    PlayerSchema,
    RosterSchema,
    TeamSchema,
    TeamSummarySchema,
)
from huddle.api.schemas.events import (
    GameEventSchema,
    PlayCompletedEventSchema,
    ScoringEventSchema,
    TurnoverEventSchema,
    QuarterEndEventSchema,
    GameEndEventSchema,
    WSMessage,
)

__all__ = [
    # Game schemas
    "CreateGameRequest",
    "GameStateSchema",
    "GameClockSchema",
    "ScoreStateSchema",
    "DownStateSchema",
    "PossessionStateSchema",
    "PlayCallRequest",
    "PlayResultSchema",
    "GameSettingsUpdate",
    # Team schemas
    "TeamSchema",
    "TeamSummarySchema",
    "PlayerSchema",
    "RosterSchema",
    # Event schemas
    "GameEventSchema",
    "PlayCompletedEventSchema",
    "ScoringEventSchema",
    "TurnoverEventSchema",
    "QuarterEndEventSchema",
    "GameEndEventSchema",
    "WSMessage",
]
