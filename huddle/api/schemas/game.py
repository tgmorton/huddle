"""Pydantic schemas for game-related models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    """Current phase of the game."""

    PREGAME = "PREGAME"
    COIN_TOSS = "COIN_TOSS"
    KICKOFF = "KICKOFF"
    FIRST_QUARTER = "FIRST_QUARTER"
    SECOND_QUARTER = "SECOND_QUARTER"
    HALFTIME = "HALFTIME"
    THIRD_QUARTER = "THIRD_QUARTER"
    FOURTH_QUARTER = "FOURTH_QUARTER"
    OVERTIME = "OVERTIME"
    FINAL = "FINAL"


class PlayType(str, Enum):
    """Type of offensive play."""

    RUN = "RUN"
    PASS = "PASS"
    PUNT = "PUNT"
    FIELD_GOAL = "FIELD_GOAL"
    KICKOFF = "KICKOFF"
    EXTRA_POINT = "EXTRA_POINT"
    TWO_POINT = "TWO_POINT"


class RunType(str, Enum):
    """Type of run play."""

    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"
    DRAW = "DRAW"
    OPTION = "OPTION"
    QB_SNEAK = "QB_SNEAK"
    QB_SCRAMBLE = "QB_SCRAMBLE"


class PassType(str, Enum):
    """Type of pass play."""

    SCREEN = "SCREEN"
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    DEEP = "DEEP"
    HAIL_MARY = "HAIL_MARY"


class Formation(str, Enum):
    """Offensive formation."""

    SHOTGUN = "Shotgun"
    SINGLEBACK = "Singleback"
    I_FORM = "I-Form"
    PISTOL = "Pistol"
    SPREAD = "Spread"
    GOAL_LINE = "Goal Line"
    EMPTY = "Empty"
    UNDER_CENTER = "Under Center"


class PersonnelPackage(str, Enum):
    """Personnel grouping."""

    ELEVEN = "11"
    TWELVE = "12"
    TWENTY_ONE = "21"
    TWENTY_TWO = "22"
    TEN = "10"
    THIRTEEN = "13"
    ZERO_ZERO = "00"


class DefensiveScheme(str, Enum):
    """Defensive coverage scheme."""

    COVER_0 = "COVER_0"
    COVER_1 = "COVER_1"
    COVER_2 = "COVER_2"
    COVER_3 = "COVER_3"
    COVER_4 = "COVER_4"
    MAN_PRESS = "MAN_PRESS"
    MAN_OFF = "MAN_OFF"
    BLITZ_4 = "BLITZ_4"
    BLITZ_5 = "BLITZ_5"
    BLITZ_6 = "BLITZ_6"


class PlayOutcome(str, Enum):
    """Outcome of a play."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    INTERCEPTION = "INTERCEPTION"
    SACK = "SACK"
    RUSH = "RUSH"
    FUMBLE = "FUMBLE"
    FUMBLE_LOST = "FUMBLE_LOST"
    TOUCHDOWN = "TOUCHDOWN"
    FIELD_GOAL_GOOD = "FIELD_GOAL_GOOD"
    FIELD_GOAL_MISSED = "FIELD_GOAL_MISSED"
    SAFETY = "SAFETY"
    EXTRA_POINT_GOOD = "EXTRA_POINT_GOOD"
    EXTRA_POINT_MISSED = "EXTRA_POINT_MISSED"
    TWO_POINT_GOOD = "TWO_POINT_GOOD"
    TWO_POINT_FAILED = "TWO_POINT_FAILED"
    PUNT_RESULT = "PUNT_RESULT"
    KICKOFF_RESULT = "KICKOFF_RESULT"
    TOUCHBACK = "TOUCHBACK"
    PENALTY_OFFENSE = "PENALTY_OFFENSE"
    PENALTY_DEFENSE = "PENALTY_DEFENSE"


# === Request schemas ===


class CreateGameRequest(BaseModel):
    """Request to create a new game."""

    home_team_id: Optional[UUID] = None
    away_team_id: Optional[UUID] = None
    # If team IDs not provided, generate random teams
    generate_teams: bool = True


class PlayCallRequest(BaseModel):
    """Request to submit a manual play call."""

    play_type: PlayType
    run_type: Optional[RunType] = None
    pass_type: Optional[PassType] = None
    formation: Optional[Formation] = None
    personnel: Optional[PersonnelPackage] = None


class GameSettingsUpdate(BaseModel):
    """Request to update game settings."""

    pacing: Optional[str] = Field(None, pattern="^(slow|normal|fast|step)$")
    mode: Optional[str] = Field(None, pattern="^(auto|manual)$")


# === Response schemas ===


class GameClockSchema(BaseModel):
    """Game clock state."""

    quarter: int
    time_remaining_seconds: int
    play_clock: int
    quarter_length_seconds: int

    # Computed properties
    minutes: int = 0
    seconds: int = 0
    display: str = "15:00"
    is_two_minute_warning: bool = False

    @classmethod
    def from_model(cls, clock) -> "GameClockSchema":
        """Create from GameClock model."""
        return cls(
            quarter=clock.quarter,
            time_remaining_seconds=clock.time_remaining_seconds,
            play_clock=clock.play_clock,
            quarter_length_seconds=clock.quarter_length_seconds,
            minutes=clock.minutes,
            seconds=clock.seconds,
            display=clock.display,
            is_two_minute_warning=clock.is_two_minute_warning,
        )


class ScoreStateSchema(BaseModel):
    """Score state."""

    home_score: int
    away_score: int
    home_by_quarter: list[int]
    away_by_quarter: list[int]
    margin: int = 0
    is_tied: bool = False

    @classmethod
    def from_model(cls, score) -> "ScoreStateSchema":
        """Create from ScoreState model."""
        return cls(
            home_score=score.home_score,
            away_score=score.away_score,
            home_by_quarter=score.home_by_quarter,
            away_by_quarter=score.away_by_quarter,
            margin=score.margin,
            is_tied=score.is_tied,
        )


class DownStateSchema(BaseModel):
    """Down and distance state."""

    down: int
    yards_to_go: int
    line_of_scrimmage: int
    display: str = ""
    field_position_display: str = ""
    is_goal_to_go: bool = False
    is_fourth_down: bool = False
    first_down_marker: int = 0

    @classmethod
    def from_model(cls, down_state) -> "DownStateSchema":
        """Create from DownState model."""
        return cls(
            down=down_state.down,
            yards_to_go=down_state.yards_to_go,
            line_of_scrimmage=down_state.line_of_scrimmage.yard_line,
            display=down_state.display,
            field_position_display=down_state.line_of_scrimmage.display,
            is_goal_to_go=down_state.is_goal_to_go,
            is_fourth_down=down_state.is_fourth_down,
            first_down_marker=down_state.first_down_marker,
        )


class PossessionStateSchema(BaseModel):
    """Possession state."""

    team_with_ball: Optional[str] = None
    receiving_second_half: Optional[str] = None
    home_timeouts: int
    away_timeouts: int

    @classmethod
    def from_model(cls, possession) -> "PossessionStateSchema":
        """Create from PossessionState model."""
        return cls(
            team_with_ball=str(possession.team_with_ball) if possession.team_with_ball else None,
            receiving_second_half=str(possession.receiving_second_half)
            if possession.receiving_second_half
            else None,
            home_timeouts=possession.home_timeouts,
            away_timeouts=possession.away_timeouts,
        )


class PlayCallSchema(BaseModel):
    """Play call information."""

    play_type: str
    run_type: Optional[str] = None
    pass_type: Optional[str] = None
    formation: Optional[str] = None
    personnel: Optional[str] = None
    display: str = ""

    @classmethod
    def from_model(cls, play_call) -> "PlayCallSchema":
        """Create from PlayCall model."""
        return cls(
            play_type=play_call.play_type.name,
            run_type=play_call.run_type.name if play_call.run_type else None,
            pass_type=play_call.pass_type.name if play_call.pass_type else None,
            formation=play_call.formation.value if play_call.formation else None,
            personnel=play_call.personnel.value if play_call.personnel else None,
            display=play_call.display,
        )


class DefensiveCallSchema(BaseModel):
    """Defensive call information."""

    scheme: str
    blitz_count: int
    is_blitz: bool = False
    display: str = ""

    @classmethod
    def from_model(cls, def_call) -> "DefensiveCallSchema":
        """Create from DefensiveCall model."""
        return cls(
            scheme=def_call.scheme.name,
            blitz_count=def_call.blitz_count,
            is_blitz=def_call.is_blitz,
            display=def_call.display,
        )


class PlayResultSchema(BaseModel):
    """Result of a simulated play."""

    play_call: PlayCallSchema
    defensive_call: DefensiveCallSchema
    outcome: str
    yards_gained: int
    time_elapsed_seconds: int

    # Player attributions
    passer_id: Optional[str] = None
    receiver_id: Optional[str] = None
    rusher_id: Optional[str] = None
    tackler_id: Optional[str] = None
    interceptor_id: Optional[str] = None

    # Result flags
    is_first_down: bool = False
    is_touchdown: bool = False
    is_turnover: bool = False
    is_sack: bool = False
    is_safety: bool = False

    # Clock
    clock_stopped: bool = False
    clock_stop_reason: Optional[str] = None

    # Scoring
    points_scored: int = 0

    # Penalty
    penalty_on_offense: bool = False
    penalty_yards: int = 0
    penalty_type: Optional[str] = None

    # Narrative
    description: str = ""
    display: str = ""

    @classmethod
    def from_model(cls, result) -> "PlayResultSchema":
        """Create from PlayResult model."""
        return cls(
            play_call=PlayCallSchema.from_model(result.play_call),
            defensive_call=DefensiveCallSchema.from_model(result.defensive_call),
            outcome=result.outcome.name,
            yards_gained=result.yards_gained,
            time_elapsed_seconds=result.time_elapsed_seconds,
            passer_id=str(result.passer_id) if result.passer_id else None,
            receiver_id=str(result.receiver_id) if result.receiver_id else None,
            rusher_id=str(result.rusher_id) if result.rusher_id else None,
            tackler_id=str(result.tackler_id) if result.tackler_id else None,
            interceptor_id=str(result.interceptor_id) if result.interceptor_id else None,
            is_first_down=result.is_first_down,
            is_touchdown=result.is_touchdown,
            is_turnover=result.is_turnover,
            is_sack=result.is_sack,
            is_safety=result.is_safety,
            clock_stopped=result.clock_stopped,
            clock_stop_reason=result.clock_stop_reason,
            points_scored=result.points_scored,
            penalty_on_offense=result.penalty_on_offense,
            penalty_yards=result.penalty_yards,
            penalty_type=result.penalty_type,
            description=result.description,
            display=result.display,
        )


class GameStateSchema(BaseModel):
    """Complete game state."""

    id: str
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    clock: GameClockSchema
    phase: GamePhase
    score: ScoreStateSchema
    down_state: DownStateSchema
    possession: PossessionStateSchema
    is_game_over: bool = False
    current_quarter: int = 1

    @classmethod
    def from_model(cls, game_state) -> "GameStateSchema":
        """Create from GameState model."""
        return cls(
            id=str(game_state.id),
            home_team_id=str(game_state.home_team_id) if game_state.home_team_id else None,
            away_team_id=str(game_state.away_team_id) if game_state.away_team_id else None,
            clock=GameClockSchema.from_model(game_state.clock),
            phase=GamePhase(game_state.phase.name),
            score=ScoreStateSchema.from_model(game_state.score),
            down_state=DownStateSchema.from_model(game_state.down_state),
            possession=PossessionStateSchema.from_model(game_state.possession),
            is_game_over=game_state.is_game_over,
            current_quarter=game_state.current_quarter,
        )


class GameResponse(BaseModel):
    """Full game response with teams."""

    game_state: GameStateSchema
    home_team: Optional["TeamSummarySchema"] = None
    away_team: Optional["TeamSummarySchema"] = None


# Import at end to avoid circular imports
from huddle.api.schemas.team import TeamSummarySchema  # noqa: E402

GameResponse.model_rebuild()
