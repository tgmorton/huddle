"""Game state models."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from huddle.core.models.field import DownState, FieldPosition

if TYPE_CHECKING:
    from huddle.core.models.play import PlayResult
    from huddle.core.models.team import Team


class GamePhase(Enum):
    """Current phase of the game."""

    PREGAME = auto()
    COIN_TOSS = auto()
    KICKOFF = auto()
    FIRST_QUARTER = auto()
    SECOND_QUARTER = auto()
    HALFTIME = auto()
    THIRD_QUARTER = auto()
    FOURTH_QUARTER = auto()
    OVERTIME = auto()
    FINAL = auto()

    @property
    def is_active(self) -> bool:
        """Check if game is in active play phase."""
        return self in {
            GamePhase.FIRST_QUARTER,
            GamePhase.SECOND_QUARTER,
            GamePhase.THIRD_QUARTER,
            GamePhase.FOURTH_QUARTER,
            GamePhase.OVERTIME,
        }

    @property
    def quarter_number(self) -> int:
        """Get quarter number (1-4, 5 for OT, 0 otherwise)."""
        mapping = {
            GamePhase.FIRST_QUARTER: 1,
            GamePhase.SECOND_QUARTER: 2,
            GamePhase.THIRD_QUARTER: 3,
            GamePhase.FOURTH_QUARTER: 4,
            GamePhase.OVERTIME: 5,
        }
        return mapping.get(self, 0)


@dataclass
class GameClock:
    """
    Manages game time.

    Time is tracked in seconds remaining in the quarter.
    Standard quarter is 15 minutes (900 seconds).
    """

    quarter: int = 1
    time_remaining_seconds: int = 900  # 15:00
    play_clock: int = 40

    # Game settings
    quarter_length_seconds: int = 900  # Can adjust for faster games

    @property
    def minutes(self) -> int:
        """Minutes remaining in quarter."""
        return self.time_remaining_seconds // 60

    @property
    def seconds(self) -> int:
        """Seconds component of time remaining."""
        return self.time_remaining_seconds % 60

    @property
    def display(self) -> str:
        """Display time as MM:SS."""
        return f"{self.minutes}:{self.seconds:02d}"

    @property
    def is_quarter_over(self) -> bool:
        """Check if quarter has ended."""
        return self.time_remaining_seconds <= 0

    @property
    def is_two_minute_warning(self) -> bool:
        """Check if at two-minute warning (only in 2nd and 4th quarters)."""
        return self.quarter in (2, 4) and self.time_remaining_seconds <= 120

    @property
    def is_hurry_up_time(self) -> bool:
        """Check if in hurry-up situation (last 2 minutes of half)."""
        return self.quarter in (2, 4) and self.time_remaining_seconds <= 120

    def tick(self, seconds: int) -> None:
        """Reduce time remaining by specified seconds."""
        self.time_remaining_seconds = max(0, self.time_remaining_seconds - seconds)

    def next_quarter(self) -> None:
        """Advance to next quarter."""
        self.quarter += 1
        self.time_remaining_seconds = self.quarter_length_seconds

    def reset_play_clock(self, seconds: int = 40) -> None:
        """Reset play clock."""
        self.play_clock = seconds

    def copy(self) -> "GameClock":
        """Create a copy of this clock."""
        return GameClock(
            quarter=self.quarter,
            time_remaining_seconds=self.time_remaining_seconds,
            play_clock=self.play_clock,
            quarter_length_seconds=self.quarter_length_seconds,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "quarter": self.quarter,
            "time_remaining_seconds": self.time_remaining_seconds,
            "play_clock": self.play_clock,
            "quarter_length_seconds": self.quarter_length_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameClock":
        """Create from dictionary."""
        return cls(
            quarter=data.get("quarter", 1),
            time_remaining_seconds=data.get("time_remaining_seconds", 900),
            play_clock=data.get("play_clock", 40),
            quarter_length_seconds=data.get("quarter_length_seconds", 900),
        )


@dataclass
class ScoreState:
    """Tracks game score."""

    home_score: int = 0
    away_score: int = 0

    # Quarter-by-quarter breakdown
    home_by_quarter: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    away_by_quarter: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    def add_score(self, is_home: bool, points: int, quarter: int) -> None:
        """Add points for a team in a specific quarter."""
        if is_home:
            self.home_score += points
            while len(self.home_by_quarter) < quarter:
                self.home_by_quarter.append(0)
            self.home_by_quarter[quarter - 1] += points
        else:
            self.away_score += points
            while len(self.away_by_quarter) < quarter:
                self.away_by_quarter.append(0)
            self.away_by_quarter[quarter - 1] += points

    @property
    def margin(self) -> int:
        """Score margin (positive = home leading)."""
        return self.home_score - self.away_score

    @property
    def is_tied(self) -> bool:
        """Check if game is tied."""
        return self.home_score == self.away_score

    @property
    def display(self) -> str:
        """Display score as 'HOME - AWAY'."""
        return f"{self.home_score} - {self.away_score}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "home_score": self.home_score,
            "away_score": self.away_score,
            "home_by_quarter": self.home_by_quarter.copy(),
            "away_by_quarter": self.away_by_quarter.copy(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoreState":
        """Create from dictionary."""
        return cls(
            home_score=data.get("home_score", 0),
            away_score=data.get("away_score", 0),
            home_by_quarter=data.get("home_by_quarter", [0, 0, 0, 0]),
            away_by_quarter=data.get("away_by_quarter", [0, 0, 0, 0]),
        )


@dataclass
class PossessionState:
    """Tracks which team has the ball and related info."""

    team_with_ball: UUID = None  # Team ID
    receiving_second_half: UUID = None  # Team receiving after halftime

    # Timeouts remaining
    home_timeouts: int = 3
    away_timeouts: int = 3

    def flip_possession(self, home_team_id: UUID, away_team_id: UUID) -> None:
        """Switch possession to the other team."""
        if self.team_with_ball == home_team_id:
            self.team_with_ball = away_team_id
        else:
            self.team_with_ball = home_team_id

    def use_timeout(self, is_home: bool) -> bool:
        """Use a timeout. Returns True if timeout was available."""
        if is_home:
            if self.home_timeouts > 0:
                self.home_timeouts -= 1
                return True
        else:
            if self.away_timeouts > 0:
                self.away_timeouts -= 1
                return True
        return False

    def reset_timeouts(self) -> None:
        """Reset timeouts for new half."""
        self.home_timeouts = 3
        self.away_timeouts = 3

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "team_with_ball": str(self.team_with_ball) if self.team_with_ball else None,
            "receiving_second_half": str(self.receiving_second_half)
            if self.receiving_second_half
            else None,
            "home_timeouts": self.home_timeouts,
            "away_timeouts": self.away_timeouts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PossessionState":
        """Create from dictionary."""
        return cls(
            team_with_ball=UUID(data["team_with_ball"]) if data.get("team_with_ball") else None,
            receiving_second_half=UUID(data["receiving_second_half"])
            if data.get("receiving_second_half")
            else None,
            home_timeouts=data.get("home_timeouts", 3),
            away_timeouts=data.get("away_timeouts", 3),
        )


@dataclass
class GameState:
    """
    Complete game state - the single source of truth for a game.

    This is the central data structure that gets passed to/from the
    simulation engine. All game state lives here.
    """

    id: UUID = field(default_factory=uuid4)

    # Teams (stored as references, actual Team objects passed separately)
    home_team_id: UUID = None
    away_team_id: UUID = None

    # Game state components
    clock: GameClock = field(default_factory=GameClock)
    phase: GamePhase = GamePhase.PREGAME
    score: ScoreState = field(default_factory=ScoreState)
    down_state: DownState = field(default_factory=DownState)
    possession: PossessionState = field(default_factory=PossessionState)

    # Play history for replay and statistics
    play_history: list["PlayResult"] = field(default_factory=list)

    # Cached team references (set during game initialization)
    _home_team: Optional["Team"] = field(default=None, repr=False)
    _away_team: Optional["Team"] = field(default=None, repr=False)

    def set_teams(self, home_team: "Team", away_team: "Team") -> None:
        """Set team references."""
        self._home_team = home_team
        self._away_team = away_team
        self.home_team_id = home_team.id
        self.away_team_id = away_team.id

    @property
    def home_team(self) -> Optional["Team"]:
        """Get home team."""
        return self._home_team

    @property
    def away_team(self) -> Optional["Team"]:
        """Get away team."""
        return self._away_team

    def get_offensive_team(self) -> Optional["Team"]:
        """Get the team currently on offense."""
        if self.possession.team_with_ball == self.home_team_id:
            return self._home_team
        elif self.possession.team_with_ball == self.away_team_id:
            return self._away_team
        return None

    def get_defensive_team(self) -> Optional["Team"]:
        """Get the team currently on defense."""
        if self.possession.team_with_ball == self.home_team_id:
            return self._away_team
        elif self.possession.team_with_ball == self.away_team_id:
            return self._home_team
        return None

    def is_home_on_offense(self) -> bool:
        """Check if home team is on offense."""
        return self.possession.team_with_ball == self.home_team_id

    @property
    def is_game_over(self) -> bool:
        """Check if game has ended."""
        return self.phase == GamePhase.FINAL

    @property
    def current_quarter(self) -> int:
        """Get current quarter number."""
        return self.phase.quarter_number

    def add_play(self, result: "PlayResult") -> None:
        """Add a play result to history."""
        self.play_history.append(result)

    def flip_possession(self) -> None:
        """Change possession to the other team."""
        self.possession.flip_possession(self.home_team_id, self.away_team_id)

    def add_score(self, points: int, for_offense: bool = True) -> None:
        """Add points to the appropriate team."""
        is_home = self.is_home_on_offense() if for_offense else not self.is_home_on_offense()
        self.score.add_score(is_home, points, self.current_quarter)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "home_team_id": str(self.home_team_id) if self.home_team_id else None,
            "away_team_id": str(self.away_team_id) if self.away_team_id else None,
            "clock": self.clock.to_dict(),
            "phase": self.phase.name,
            "score": self.score.to_dict(),
            "down_state": self.down_state.to_dict(),
            "possession": self.possession.to_dict(),
            # play_history serialization handled separately (can be large)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            home_team_id=UUID(data["home_team_id"]) if data.get("home_team_id") else None,
            away_team_id=UUID(data["away_team_id"]) if data.get("away_team_id") else None,
            clock=GameClock.from_dict(data.get("clock", {})),
            phase=GamePhase[data.get("phase", "PREGAME")],
            score=ScoreState.from_dict(data.get("score", {})),
            down_state=DownState.from_dict(data.get("down_state", {})),
            possession=PossessionState.from_dict(data.get("possession", {})),
        )

    def __str__(self) -> str:
        """String representation."""
        home_name = self._home_team.abbreviation if self._home_team else "HOME"
        away_name = self._away_team.abbreviation if self._away_team else "AWAY"
        return (
            f"{away_name} {self.score.away_score} @ {home_name} {self.score.home_score} "
            f"- Q{self.current_quarter} {self.clock.display}"
        )
