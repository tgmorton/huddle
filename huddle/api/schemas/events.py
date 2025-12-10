"""Pydantic schemas for WebSocket event messages."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel

from huddle.api.schemas.game import (
    DownStateSchema,
    GameStateSchema,
    PlayResultSchema,
)
from huddle.api.schemas.team import TeamSummarySchema


class WSMessageType(str, Enum):
    """WebSocket message types."""

    # Server -> Client
    PLAY_COMPLETED = "play_completed"
    SCORING = "scoring"
    TURNOVER = "turnover"
    QUARTER_END = "quarter_end"
    GAME_END = "game_end"
    AWAITING_PLAY_CALL = "awaiting_play_call"
    STATE_SYNC = "state_sync"
    ERROR = "error"

    # Client -> Server
    PLAY_CALL = "play_call"
    PAUSE = "pause"
    RESUME = "resume"
    SET_PACING = "set_pacing"
    REQUEST_SYNC = "request_sync"


class GameEventSchema(BaseModel):
    """Base schema for game events."""

    timestamp: datetime
    game_id: Optional[str] = None
    quarter: int = 1
    time_remaining: str = "15:00"
    home_score: int = 0
    away_score: int = 0


class PlayCompletedEventSchema(GameEventSchema):
    """Play completed event."""

    result: PlayResultSchema
    down: int = 1
    yards_to_go: int = 10
    field_position: str = ""
    line_of_scrimmage: int = 20
    first_down_marker: int = 30
    offense_is_home: bool = False

    @classmethod
    def from_event(cls, event) -> "PlayCompletedEventSchema":
        """Create from PlayCompletedEvent."""
        return cls(
            timestamp=event.timestamp,
            game_id=str(event.game_id) if event.game_id else None,
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            home_score=event.home_score,
            away_score=event.away_score,
            result=PlayResultSchema.from_model(event.result),
            down=event.down,
            yards_to_go=event.yards_to_go,
            field_position=event.field_position,
            line_of_scrimmage=event.line_of_scrimmage,
            first_down_marker=event.first_down_marker,
            offense_is_home=event.offense_is_home,
        )


class ScoringEventSchema(GameEventSchema):
    """Scoring event."""

    team_id: Optional[str] = None
    points: int = 0
    scoring_type: str = ""
    scorer_id: Optional[str] = None
    description: str = ""

    @classmethod
    def from_event(cls, event) -> "ScoringEventSchema":
        """Create from ScoringEvent."""
        return cls(
            timestamp=event.timestamp,
            game_id=str(event.game_id) if event.game_id else None,
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            home_score=event.home_score,
            away_score=event.away_score,
            team_id=str(event.team_id) if event.team_id else None,
            points=event.points,
            scoring_type=event.scoring_type,
            scorer_id=str(event.scorer_id) if event.scorer_id else None,
            description=event.description,
        )


class TurnoverEventSchema(GameEventSchema):
    """Turnover event."""

    losing_team_id: Optional[str] = None
    gaining_team_id: Optional[str] = None
    turnover_type: str = ""
    player_who_lost_id: Optional[str] = None
    player_who_gained_id: Optional[str] = None

    @classmethod
    def from_event(cls, event) -> "TurnoverEventSchema":
        """Create from TurnoverEvent."""
        return cls(
            timestamp=event.timestamp,
            game_id=str(event.game_id) if event.game_id else None,
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            home_score=event.home_score,
            away_score=event.away_score,
            losing_team_id=str(event.losing_team_id) if event.losing_team_id else None,
            gaining_team_id=str(event.gaining_team_id) if event.gaining_team_id else None,
            turnover_type=event.turnover_type,
            player_who_lost_id=str(event.player_who_lost_id)
            if event.player_who_lost_id
            else None,
            player_who_gained_id=str(event.player_who_gained_id)
            if event.player_who_gained_id
            else None,
        )


class QuarterEndEventSchema(GameEventSchema):
    """Quarter end event."""

    quarter_ended: int = 1

    @classmethod
    def from_event(cls, event) -> "QuarterEndEventSchema":
        """Create from QuarterEndEvent."""
        return cls(
            timestamp=event.timestamp,
            game_id=str(event.game_id) if event.game_id else None,
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            home_score=event.home_score,
            away_score=event.away_score,
            quarter_ended=event.quarter_ended,
        )


class GameEndEventSchema(GameEventSchema):
    """Game end event."""

    winner_id: Optional[str] = None
    final_home_score: int = 0
    final_away_score: int = 0
    is_overtime: bool = False

    @classmethod
    def from_event(cls, event) -> "GameEndEventSchema":
        """Create from GameEndEvent."""
        return cls(
            timestamp=event.timestamp,
            game_id=str(event.game_id) if event.game_id else None,
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            home_score=event.home_score,
            away_score=event.away_score,
            winner_id=str(event.winner_id) if event.winner_id else None,
            final_home_score=event.final_home_score,
            final_away_score=event.final_away_score,
            is_overtime=event.is_overtime,
        )


class StateSyncPayload(BaseModel):
    """Full state sync payload."""

    game_state: GameStateSchema
    home_team: TeamSummarySchema
    away_team: TeamSummarySchema


class AwaitingPlayCallPayload(BaseModel):
    """Payload when awaiting manual play call."""

    down_state: DownStateSchema
    available_plays: list[str] = []


class ErrorPayload(BaseModel):
    """Error payload."""

    message: str
    code: Optional[str] = None


# Union of all possible payloads
EventPayload = Union[
    PlayCompletedEventSchema,
    ScoringEventSchema,
    TurnoverEventSchema,
    QuarterEndEventSchema,
    GameEndEventSchema,
    StateSyncPayload,
    AwaitingPlayCallPayload,
    ErrorPayload,
    dict,  # For generic payloads
]


class WSMessage(BaseModel):
    """WebSocket message wrapper."""

    type: WSMessageType
    timestamp: datetime = datetime.now()
    payload: Any = None

    @classmethod
    def play_completed(cls, event) -> "WSMessage":
        """Create play completed message."""
        return cls(
            type=WSMessageType.PLAY_COMPLETED,
            payload=PlayCompletedEventSchema.from_event(event).model_dump(),
        )

    @classmethod
    def scoring(cls, event) -> "WSMessage":
        """Create scoring message."""
        return cls(
            type=WSMessageType.SCORING,
            payload=ScoringEventSchema.from_event(event).model_dump(),
        )

    @classmethod
    def turnover(cls, event) -> "WSMessage":
        """Create turnover message."""
        return cls(
            type=WSMessageType.TURNOVER,
            payload=TurnoverEventSchema.from_event(event).model_dump(),
        )

    @classmethod
    def quarter_end(cls, event) -> "WSMessage":
        """Create quarter end message."""
        return cls(
            type=WSMessageType.QUARTER_END,
            payload=QuarterEndEventSchema.from_event(event).model_dump(),
        )

    @classmethod
    def game_end(cls, event) -> "WSMessage":
        """Create game end message."""
        return cls(
            type=WSMessageType.GAME_END,
            payload=GameEndEventSchema.from_event(event).model_dump(),
        )

    @classmethod
    def state_sync(cls, game_state, home_team, away_team) -> "WSMessage":
        """Create state sync message."""
        return cls(
            type=WSMessageType.STATE_SYNC,
            payload=StateSyncPayload(
                game_state=GameStateSchema.from_model(game_state),
                home_team=TeamSummarySchema.from_model(home_team),
                away_team=TeamSummarySchema.from_model(away_team),
            ).model_dump(),
        )

    @classmethod
    def awaiting_play_call(cls, down_state, available_plays: list[str]) -> "WSMessage":
        """Create awaiting play call message."""
        return cls(
            type=WSMessageType.AWAITING_PLAY_CALL,
            payload=AwaitingPlayCallPayload(
                down_state=DownStateSchema.from_model(down_state),
                available_plays=available_plays,
            ).model_dump(),
        )

    @classmethod
    def error(cls, message: str, code: Optional[str] = None) -> "WSMessage":
        """Create error message."""
        return cls(
            type=WSMessageType.ERROR,
            payload=ErrorPayload(message=message, code=code).model_dump(),
        )
