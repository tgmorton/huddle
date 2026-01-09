"""Schemas for Coach Mode game API."""

from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class GamePhaseEnum(str, Enum):
    """Game phase enumeration."""
    PRE_GAME = "pre_game"
    FIRST_QUARTER = "first_quarter"
    SECOND_QUARTER = "second_quarter"
    HALFTIME = "halftime"
    THIRD_QUARTER = "third_quarter"
    FOURTH_QUARTER = "fourth_quarter"
    OVERTIME = "overtime"
    FINAL = "final"


class PlayTypeEnum(str, Enum):
    """Play type enumeration."""
    RUN = "run"
    PASS = "pass"
    PUNT = "punt"
    FIELD_GOAL = "field_goal"
    PAT = "pat"
    TWO_POINT = "two_point"
    KICKOFF = "kickoff"


# =============================================================================
# Request Schemas
# =============================================================================

class StartGameRequest(BaseModel):
    """Request to start a new coach mode game."""
    home_team_id: UUID
    away_team_id: UUID
    user_controls_home: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "home_team_id": "550e8400-e29b-41d4-a716-446655440001",
                "away_team_id": "550e8400-e29b-41d4-a716-446655440002",
                "user_controls_home": True,
            }
        }


class StartGameWithLeagueRequest(BaseModel):
    """Request to start a game from a league matchup."""
    league_id: UUID
    week: int
    matchup_index: int = 0  # Which game in the week's schedule
    user_controls_home: bool = True


class CallPlayRequest(BaseModel):
    """Request to call an offensive play."""
    play_code: str = Field(..., description="PlayCode identifier (e.g., 'PASS_SLANT', 'RUN_POWER')")
    shotgun: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "play_code": "PASS_SLANT",
                "shotgun": True,
            }
        }


class SpecialTeamsRequest(BaseModel):
    """Request for special teams play."""
    play_type: PlayTypeEnum
    onside: bool = False  # For kickoffs
    go_for_two: bool = False  # After TD

    class Config:
        json_schema_extra = {
            "example": {
                "play_type": "field_goal",
            }
        }


# =============================================================================
# Response Schemas
# =============================================================================

class GameSituationResponse(BaseModel):
    """Current game situation for display."""
    game_id: str
    quarter: int
    time_remaining: str  # "12:45" format
    home_score: int
    away_score: int
    possession_home: bool
    down: int
    distance: int
    los: float
    yard_line_display: str  # "OPP 25" or "OWN 35"
    is_red_zone: bool
    is_goal_to_go: bool
    phase: GamePhaseEnum
    user_on_offense: bool
    user_on_defense: bool

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "game_abc123",
                "quarter": 2,
                "time_remaining": "8:42",
                "home_score": 7,
                "away_score": 3,
                "possession_home": True,
                "down": 2,
                "distance": 7,
                "los": 35.0,
                "yard_line_display": "OWN 35",
                "is_red_zone": False,
                "is_goal_to_go": False,
                "phase": "second_quarter",
                "user_on_offense": True,
                "user_on_defense": False,
            }
        }


class AvailablePlaysResponse(BaseModel):
    """Available plays for current situation."""
    plays: List[str]
    recommended: Optional[str] = None
    situation_tips: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "plays": [
                    "PASS_SLANT",
                    "PASS_HITCH",
                    "PASS_DIG",
                    "RUN_INSIDE_ZONE",
                    "RUN_POWER",
                ],
                "recommended": "PASS_DIG",
                "situation_tips": [
                    "2nd and medium - good situation for intermediate routes",
                    "Consider play action to catch defense off guard",
                ],
            }
        }


class PlayResultResponse(BaseModel):
    """Result of executing a play."""
    outcome: str  # complete, incomplete, sack, run, interception, fumble
    yards_gained: float
    description: str  # Human-readable description
    new_down: int
    new_distance: int
    new_los: float
    first_down: bool
    touchdown: bool
    turnover: bool
    is_drive_over: bool
    drive_end_reason: Optional[str] = None

    # Participants
    passer_name: Optional[str] = None
    receiver_name: Optional[str] = None
    tackler_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "outcome": "complete",
                "yards_gained": 12.0,
                "description": "T. Brady pass complete to R. Gronkowski for 12 yards",
                "new_down": 1,
                "new_distance": 10,
                "new_los": 47.0,
                "first_down": True,
                "touchdown": False,
                "turnover": False,
                "is_drive_over": False,
            }
        }


class SpecialTeamsResultResponse(BaseModel):
    """Result of special teams play."""
    play_type: str
    result: str
    new_los: float
    points_scored: int
    description: str

    class Config:
        json_schema_extra = {
            "example": {
                "play_type": "field_goal",
                "result": "good",
                "new_los": 25.0,
                "points_scored": 3,
                "description": "42-yard field goal is GOOD",
            }
        }


class GameStartedResponse(BaseModel):
    """Response when a new game is started."""
    game_id: str
    home_team_name: str
    away_team_name: str
    situation: GameSituationResponse
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "game_abc123",
                "home_team_name": "Philadelphia Eagles",
                "away_team_name": "Dallas Cowboys",
                "message": "Game started! Eagles won the toss and deferred.",
            }
        }


class DriveResultResponse(BaseModel):
    """Summary of a completed drive."""
    plays: int
    yards: float
    time_of_possession: str  # "4:32" format
    result: str  # touchdown, field_goal_made, punt, turnover, etc.
    points_scored: int
    starting_los: float
    ending_los: float


class BoxScoreResponse(BaseModel):
    """Box score for the game."""
    home: Dict[str, str]
    away: Dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "home": {
                    "total_yards": "312",
                    "passing_yards": "218",
                    "rushing_yards": "94",
                    "first_downs": "18",
                    "turnovers": "1",
                    "time_of_possession": "28:42",
                    "third_down": "5/12",
                },
                "away": {
                    "total_yards": "285",
                    "passing_yards": "192",
                    "rushing_yards": "93",
                    "first_downs": "15",
                    "turnovers": "2",
                    "time_of_possession": "31:18",
                    "third_down": "4/11",
                },
            }
        }


class GameOverResponse(BaseModel):
    """Response when game ends."""
    game_id: str
    home_score: int
    away_score: int
    winner: str  # "home", "away", or "tie"
    box_score: BoxScoreResponse
    drives: List[DriveResultResponse]
