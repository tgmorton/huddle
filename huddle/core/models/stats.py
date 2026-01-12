"""Player and team statistics models."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class PassingStats:
    """Passing statistics."""

    attempts: int = 0
    completions: int = 0
    yards: int = 0
    touchdowns: int = 0
    interceptions: int = 0
    sacks: int = 0
    sack_yards: int = 0
    longest: int = 0

    @property
    def completion_pct(self) -> float:
        """Completion percentage."""
        return (self.completions / self.attempts * 100) if self.attempts > 0 else 0.0

    @property
    def yards_per_attempt(self) -> float:
        """Yards per attempt."""
        return self.yards / self.attempts if self.attempts > 0 else 0.0

    @property
    def passer_rating(self) -> float:
        """NFL passer rating (0-158.3)."""
        if self.attempts == 0:
            return 0.0

        # NFL passer rating formula
        a = max(0, min(2.375, ((self.completions / self.attempts) - 0.3) * 5))
        b = max(0, min(2.375, ((self.yards / self.attempts) - 3) * 0.25))
        c = max(0, min(2.375, (self.touchdowns / self.attempts) * 20))
        d = max(0, min(2.375, 2.375 - ((self.interceptions / self.attempts) * 25)))

        return ((a + b + c + d) / 6) * 100

    def add(self, other: "PassingStats") -> None:
        """Add another PassingStats to this one."""
        self.attempts += other.attempts
        self.completions += other.completions
        self.yards += other.yards
        self.touchdowns += other.touchdowns
        self.interceptions += other.interceptions
        self.sacks += other.sacks
        self.sack_yards += other.sack_yards
        self.longest = max(self.longest, other.longest)

    def to_dict(self) -> dict:
        return {
            "attempts": self.attempts,
            "completions": self.completions,
            "yards": self.yards,
            "touchdowns": self.touchdowns,
            "interceptions": self.interceptions,
            "sacks": self.sacks,
            "sack_yards": self.sack_yards,
            "longest": self.longest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PassingStats":
        return cls(**data)


@dataclass
class RushingStats:
    """Rushing statistics."""

    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles: int = 0
    fumbles_lost: int = 0
    longest: int = 0

    @property
    def yards_per_carry(self) -> float:
        """Yards per carry."""
        return self.yards / self.attempts if self.attempts > 0 else 0.0

    def add(self, other: "RushingStats") -> None:
        """Add another RushingStats to this one."""
        self.attempts += other.attempts
        self.yards += other.yards
        self.touchdowns += other.touchdowns
        self.fumbles += other.fumbles
        self.fumbles_lost += other.fumbles_lost
        self.longest = max(self.longest, other.longest)

    def to_dict(self) -> dict:
        return {
            "attempts": self.attempts,
            "yards": self.yards,
            "touchdowns": self.touchdowns,
            "fumbles": self.fumbles,
            "fumbles_lost": self.fumbles_lost,
            "longest": self.longest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RushingStats":
        return cls(**data)


@dataclass
class ReceivingStats:
    """Receiving statistics."""

    targets: int = 0
    receptions: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles: int = 0
    fumbles_lost: int = 0
    longest: int = 0

    @property
    def yards_per_reception(self) -> float:
        """Yards per reception."""
        return self.yards / self.receptions if self.receptions > 0 else 0.0

    @property
    def catch_pct(self) -> float:
        """Catch percentage."""
        return (self.receptions / self.targets * 100) if self.targets > 0 else 0.0

    def add(self, other: "ReceivingStats") -> None:
        """Add another ReceivingStats to this one."""
        self.targets += other.targets
        self.receptions += other.receptions
        self.yards += other.yards
        self.touchdowns += other.touchdowns
        self.fumbles += other.fumbles
        self.fumbles_lost += other.fumbles_lost
        self.longest = max(self.longest, other.longest)

    def to_dict(self) -> dict:
        return {
            "targets": self.targets,
            "receptions": self.receptions,
            "yards": self.yards,
            "touchdowns": self.touchdowns,
            "fumbles": self.fumbles,
            "fumbles_lost": self.fumbles_lost,
            "longest": self.longest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReceivingStats":
        return cls(**data)


@dataclass
class DefensiveStats:
    """Defensive statistics."""

    tackles: int = 0
    tackles_for_loss: int = 0
    sacks: float = 0.0  # Can be half-sacks
    interceptions: int = 0
    interception_yards: int = 0
    interception_tds: int = 0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    fumble_return_yards: int = 0
    fumble_return_tds: int = 0
    safeties: int = 0

    def add(self, other: "DefensiveStats") -> None:
        """Add another DefensiveStats to this one."""
        self.tackles += other.tackles
        self.tackles_for_loss += other.tackles_for_loss
        self.sacks += other.sacks
        self.interceptions += other.interceptions
        self.interception_yards += other.interception_yards
        self.interception_tds += other.interception_tds
        self.passes_defended += other.passes_defended
        self.forced_fumbles += other.forced_fumbles
        self.fumble_recoveries += other.fumble_recoveries
        self.fumble_return_yards += other.fumble_return_yards
        self.fumble_return_tds += other.fumble_return_tds
        self.safeties += other.safeties

    def to_dict(self) -> dict:
        return {
            "tackles": self.tackles,
            "tackles_for_loss": self.tackles_for_loss,
            "sacks": self.sacks,
            "interceptions": self.interceptions,
            "interception_yards": self.interception_yards,
            "interception_tds": self.interception_tds,
            "passes_defended": self.passes_defended,
            "forced_fumbles": self.forced_fumbles,
            "fumble_recoveries": self.fumble_recoveries,
            "fumble_return_yards": self.fumble_return_yards,
            "fumble_return_tds": self.fumble_return_tds,
            "safeties": self.safeties,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DefensiveStats":
        return cls(**data)


@dataclass
class KickingStats:
    """Kicking statistics."""

    fg_attempts: int = 0
    fg_made: int = 0
    fg_longest: int = 0
    xp_attempts: int = 0
    xp_made: int = 0

    @property
    def fg_pct(self) -> float:
        """Field goal percentage."""
        return (self.fg_made / self.fg_attempts * 100) if self.fg_attempts > 0 else 0.0

    @property
    def xp_pct(self) -> float:
        """Extra point percentage."""
        return (self.xp_made / self.xp_attempts * 100) if self.xp_attempts > 0 else 0.0

    @property
    def points(self) -> int:
        """Total points scored."""
        return (self.fg_made * 3) + self.xp_made

    def add(self, other: "KickingStats") -> None:
        """Add another KickingStats to this one."""
        self.fg_attempts += other.fg_attempts
        self.fg_made += other.fg_made
        self.fg_longest = max(self.fg_longest, other.fg_longest)
        self.xp_attempts += other.xp_attempts
        self.xp_made += other.xp_made

    def to_dict(self) -> dict:
        return {
            "fg_attempts": self.fg_attempts,
            "fg_made": self.fg_made,
            "fg_longest": self.fg_longest,
            "xp_attempts": self.xp_attempts,
            "xp_made": self.xp_made,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KickingStats":
        return cls(**data)


@dataclass
class PlayerGameStats:
    """Complete statistics for a player in a single game."""

    player_id: UUID
    player_name: str
    team_abbr: str
    position: str

    # Stats by category
    passing: PassingStats = field(default_factory=PassingStats)
    rushing: RushingStats = field(default_factory=RushingStats)
    receiving: ReceivingStats = field(default_factory=ReceivingStats)
    defense: DefensiveStats = field(default_factory=DefensiveStats)
    kicking: KickingStats = field(default_factory=KickingStats)

    @property
    def total_touchdowns(self) -> int:
        """Total touchdowns scored."""
        return (
            self.passing.touchdowns +
            self.rushing.touchdowns +
            self.receiving.touchdowns +
            self.defense.interception_tds +
            self.defense.fumble_return_tds
        )

    @property
    def total_yards(self) -> int:
        """Total yards from scrimmage."""
        return self.rushing.yards + self.receiving.yards

    def to_dict(self) -> dict:
        return {
            "player_id": str(self.player_id),
            "player_name": self.player_name,
            "team_abbr": self.team_abbr,
            "position": self.position,
            "passing": self.passing.to_dict(),
            "rushing": self.rushing.to_dict(),
            "receiving": self.receiving.to_dict(),
            "defense": self.defense.to_dict(),
            "kicking": self.kicking.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerGameStats":
        return cls(
            player_id=UUID(data["player_id"]),
            player_name=data["player_name"],
            team_abbr=data["team_abbr"],
            position=data["position"],
            passing=PassingStats.from_dict(data.get("passing", {})),
            rushing=RushingStats.from_dict(data.get("rushing", {})),
            receiving=ReceivingStats.from_dict(data.get("receiving", {})),
            defense=DefensiveStats.from_dict(data.get("defense", {})),
            kicking=KickingStats.from_dict(data.get("kicking", {})),
        )


@dataclass
class PlayerSeasonStats:
    """Complete statistics for a player across a season."""

    player_id: UUID
    player_name: str
    team_abbr: str
    position: str
    season: int

    games_played: int = 0
    games_started: int = 0
    game_ids: list = field(default_factory=list)  # List of game_id strings

    # Stats by category
    passing: PassingStats = field(default_factory=PassingStats)
    rushing: RushingStats = field(default_factory=RushingStats)
    receiving: ReceivingStats = field(default_factory=ReceivingStats)
    defense: DefensiveStats = field(default_factory=DefensiveStats)
    kicking: KickingStats = field(default_factory=KickingStats)

    def add_game(self, game_stats: PlayerGameStats, game_id: str = None) -> None:
        """Add a game's stats to season totals."""
        self.games_played += 1
        if game_id and game_id not in self.game_ids:
            self.game_ids.append(game_id)
        self.passing.add(game_stats.passing)
        self.rushing.add(game_stats.rushing)
        self.receiving.add(game_stats.receiving)
        self.defense.add(game_stats.defense)
        self.kicking.add(game_stats.kicking)

    @property
    def total_touchdowns(self) -> int:
        """Total touchdowns scored."""
        return (
            self.passing.touchdowns +
            self.rushing.touchdowns +
            self.receiving.touchdowns +
            self.defense.interception_tds +
            self.defense.fumble_return_tds
        )

    @property
    def total_yards(self) -> int:
        """Total yards from scrimmage."""
        return self.rushing.yards + self.receiving.yards

    def to_dict(self) -> dict:
        return {
            "player_id": str(self.player_id),
            "player_name": self.player_name,
            "team_abbr": self.team_abbr,
            "position": self.position,
            "season": self.season,
            "games_played": self.games_played,
            "games_started": self.games_started,
            "game_ids": self.game_ids,
            "passing": self.passing.to_dict(),
            "rushing": self.rushing.to_dict(),
            "receiving": self.receiving.to_dict(),
            "defense": self.defense.to_dict(),
            "kicking": self.kicking.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerSeasonStats":
        return cls(
            player_id=UUID(data["player_id"]),
            player_name=data["player_name"],
            team_abbr=data["team_abbr"],
            position=data["position"],
            season=data["season"],
            games_played=data.get("games_played", 0),
            games_started=data.get("games_started", 0),
            game_ids=data.get("game_ids", []),
            passing=PassingStats.from_dict(data.get("passing", {})),
            rushing=RushingStats.from_dict(data.get("rushing", {})),
            receiving=ReceivingStats.from_dict(data.get("receiving", {})),
            defense=DefensiveStats.from_dict(data.get("defense", {})),
            kicking=KickingStats.from_dict(data.get("kicking", {})),
        )


@dataclass
class TeamGameStats:
    """Team statistics for a single game."""

    team_abbr: str

    # Offense
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    first_downs: int = 0
    third_down_attempts: int = 0
    third_down_conversions: int = 0
    fourth_down_attempts: int = 0
    fourth_down_conversions: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    time_of_possession_seconds: int = 0

    # Scoring
    points: int = 0
    touchdowns: int = 0
    field_goals: int = 0

    @property
    def third_down_pct(self) -> float:
        """Third down conversion percentage."""
        return (self.third_down_conversions / self.third_down_attempts * 100) if self.third_down_attempts > 0 else 0.0

    @property
    def time_of_possession_display(self) -> str:
        """Display time of possession as MM:SS."""
        minutes = self.time_of_possession_seconds // 60
        seconds = self.time_of_possession_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def to_dict(self) -> dict:
        return {
            "team_abbr": self.team_abbr,
            "total_yards": self.total_yards,
            "passing_yards": self.passing_yards,
            "rushing_yards": self.rushing_yards,
            "first_downs": self.first_downs,
            "third_down_attempts": self.third_down_attempts,
            "third_down_conversions": self.third_down_conversions,
            "fourth_down_attempts": self.fourth_down_attempts,
            "fourth_down_conversions": self.fourth_down_conversions,
            "turnovers": self.turnovers,
            "penalties": self.penalties,
            "penalty_yards": self.penalty_yards,
            "time_of_possession_seconds": self.time_of_possession_seconds,
            "points": self.points,
            "touchdowns": self.touchdowns,
            "field_goals": self.field_goals,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamGameStats":
        return cls(**data)


@dataclass
class GameLog:
    """Complete log of a game including stats and play-by-play."""

    game_id: UUID
    week: int
    home_team_abbr: str
    away_team_abbr: str
    home_score: int
    away_score: int
    is_overtime: bool = False
    is_playoff: bool = False

    # Team stats
    home_stats: TeamGameStats = field(default_factory=lambda: TeamGameStats(team_abbr=""))
    away_stats: TeamGameStats = field(default_factory=lambda: TeamGameStats(team_abbr=""))

    # Player stats (keyed by player_id string)
    player_stats: dict[str, PlayerGameStats] = field(default_factory=dict)

    # Play-by-play data (list of play dicts)
    plays: list[dict] = field(default_factory=list)

    # Scoring summary
    scoring_plays: list[dict] = field(default_factory=list)

    @property
    def winner_abbr(self) -> Optional[str]:
        """Get winner abbreviation."""
        if self.home_score > self.away_score:
            return self.home_team_abbr
        elif self.away_score > self.home_score:
            return self.away_team_abbr
        return None

    def get_player_stats(self, player_id: UUID) -> Optional[PlayerGameStats]:
        """Get stats for a specific player."""
        return self.player_stats.get(str(player_id))

    def to_dict(self) -> dict:
        return {
            "game_id": str(self.game_id),
            "week": self.week,
            "home_team_abbr": self.home_team_abbr,
            "away_team_abbr": self.away_team_abbr,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "is_overtime": self.is_overtime,
            "is_playoff": self.is_playoff,
            "home_stats": self.home_stats.to_dict(),
            "away_stats": self.away_stats.to_dict(),
            "player_stats": {k: v.to_dict() for k, v in self.player_stats.items()},
            "plays": self.plays,
            "scoring_plays": self.scoring_plays,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameLog":
        return cls(
            game_id=UUID(data["game_id"]),
            week=data["week"],
            home_team_abbr=data["home_team_abbr"],
            away_team_abbr=data["away_team_abbr"],
            home_score=data["home_score"],
            away_score=data["away_score"],
            is_overtime=data.get("is_overtime", False),
            is_playoff=data.get("is_playoff", False),
            home_stats=TeamGameStats.from_dict(data.get("home_stats", {"team_abbr": data["home_team_abbr"]})),
            away_stats=TeamGameStats.from_dict(data.get("away_stats", {"team_abbr": data["away_team_abbr"]})),
            player_stats={k: PlayerGameStats.from_dict(v) for k, v in data.get("player_stats", {}).items()},
            plays=data.get("plays", []),
            scoring_plays=data.get("scoring_plays", []),
        )
