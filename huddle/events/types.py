"""Event types for game simulation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from huddle.core.models.play import DriveResult, PlayResult


@dataclass
class GameEvent:
    """Base class for all game events."""

    timestamp: datetime = field(default_factory=datetime.now)
    game_id: UUID = None

    # Game context at time of event
    quarter: int = 1
    time_remaining: str = "15:00"
    home_score: int = 0
    away_score: int = 0


@dataclass
class PlayCompletedEvent(GameEvent):
    """Fired when a play is completed."""

    result: "PlayResult" = None

    # Down/distance info
    down: int = 1
    yards_to_go: int = 10
    field_position: str = ""  # e.g., "OWN 25"
    line_of_scrimmage: int = 20  # 0-100 yard line
    first_down_marker: int = 30  # 0-100 yard line

    # Possession info
    offense_is_home: bool = False


@dataclass
class DriveCompletedEvent(GameEvent):
    """Fired when a drive is completed (in fast simulation mode)."""

    result: "DriveResult" = None
    offensive_team_id: UUID = None


@dataclass
class ScoringEvent(GameEvent):
    """Fired when points are scored."""

    team_id: UUID = None
    points: int = 0
    scoring_type: str = ""  # "TD", "FG", "Safety", "XP", "2PT"
    scorer_id: UUID = None  # Player who scored (if applicable)
    description: str = ""


@dataclass
class TurnoverEvent(GameEvent):
    """Fired on turnovers."""

    losing_team_id: UUID = None
    gaining_team_id: UUID = None
    turnover_type: str = ""  # "INT", "FUMBLE", "DOWNS"
    player_who_lost_id: UUID = None  # Player who threw INT or fumbled
    player_who_gained_id: UUID = None  # Player who intercepted or recovered


@dataclass
class QuarterEndEvent(GameEvent):
    """Fired at end of a quarter."""

    quarter_ended: int = 1


@dataclass
class GameEndEvent(GameEvent):
    """Fired when game ends."""

    winner_id: UUID = None  # None if tie
    final_home_score: int = 0
    final_away_score: int = 0
    is_overtime: bool = False
