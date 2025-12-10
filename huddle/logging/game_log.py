"""In-memory game log for accumulating play-by-play events."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from huddle.core.enums import PlayOutcome, PlayType
from huddle.core.models.play import PlayCall
from huddle.events import EventBus, PlayCompletedEvent, ScoringEvent, TurnoverEvent


@dataclass
class LogEntry:
    """Single entry in the game log."""

    timestamp: datetime
    quarter: int
    time_remaining: str
    event_type: str  # "PLAY", "SCORE", "TURNOVER", "QUARTER_END"
    description: str
    home_score: int
    away_score: int

    # Optional play details
    down: Optional[int] = None
    yards_to_go: Optional[int] = None
    field_position: Optional[str] = None
    yards_gained: Optional[int] = None
    is_scoring_play: bool = False
    is_turnover: bool = False

    # For stats tracking
    is_pass: bool = False
    is_rush: bool = False
    is_complete: bool = False
    is_sack: bool = False
    offense_is_home: bool = False


@dataclass
class ScoringPlay:
    """Record of a scoring play."""

    quarter: int
    time_remaining: str
    team_abbrev: str
    scoring_type: str  # "TD", "FG", "Safety", "XP", "2PT"
    points: int
    description: str
    home_score_after: int
    away_score_after: int


@dataclass
class PlayerStats:
    """Accumulated statistics for one player."""

    player_id: UUID
    player_name: str
    position: str
    team_abbrev: str

    # Passing
    pass_attempts: int = 0
    pass_completions: int = 0
    pass_yards: int = 0
    pass_tds: int = 0
    interceptions: int = 0
    sacks_taken: int = 0

    # Rushing
    rush_attempts: int = 0
    rush_yards: int = 0
    rush_tds: int = 0
    fumbles: int = 0

    # Receiving
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0

    # Defense
    tackles: int = 0
    sacks: int = 0
    interceptions_def: int = 0

    @property
    def passer_rating(self) -> float:
        """Calculate NFL passer rating."""
        if self.pass_attempts == 0:
            return 0.0
        a = ((self.pass_completions / self.pass_attempts) - 0.3) * 5
        b = ((self.pass_yards / self.pass_attempts) - 3) * 0.25
        c = (self.pass_tds / self.pass_attempts) * 20
        d = 2.375 - ((self.interceptions / self.pass_attempts) * 25)
        a, b, c, d = [max(0, min(2.375, x)) for x in [a, b, c, d]]
        return ((a + b + c + d) / 6) * 100

    @property
    def yards_per_carry(self) -> float:
        if self.rush_attempts == 0:
            return 0.0
        return self.rush_yards / self.rush_attempts

    @property
    def yards_per_reception(self) -> float:
        if self.receptions == 0:
            return 0.0
        return self.receiving_yards / self.receptions


@dataclass
class TeamStats:
    """Accumulated statistics for one team."""

    # Passing
    pass_attempts: int = 0
    pass_completions: int = 0
    pass_yards: int = 0
    pass_tds: int = 0
    interceptions: int = 0
    sacks: int = 0
    sack_yards: int = 0

    # Rushing
    rush_attempts: int = 0
    rush_yards: int = 0
    rush_tds: int = 0

    # Turnovers
    fumbles_lost: int = 0

    # Scoring
    field_goals_made: int = 0
    field_goals_attempted: int = 0

    @property
    def total_yards(self) -> int:
        return self.pass_yards + self.rush_yards

    @property
    def total_tds(self) -> int:
        return self.pass_tds + self.rush_tds

    @property
    def turnovers(self) -> int:
        return self.interceptions + self.fumbles_lost

    @property
    def completion_pct(self) -> float:
        if self.pass_attempts == 0:
            return 0.0
        return (self.pass_completions / self.pass_attempts) * 100

    @property
    def yards_per_rush(self) -> float:
        if self.rush_attempts == 0:
            return 0.0
        return self.rush_yards / self.rush_attempts

    @property
    def yards_per_pass(self) -> float:
        if self.pass_attempts == 0:
            return 0.0
        return self.pass_yards / self.pass_attempts


class GameLog:
    """
    In-memory accumulator for play-by-play events.

    Subscribes to EventBus for automatic logging of game events.
    Can be used to generate game summaries and markdown output.
    """

    def __init__(
        self,
        home_abbrev: str = "HOME",
        away_abbrev: str = "AWAY",
        home_team_id: Optional[UUID] = None,
        away_team_id: Optional[UUID] = None,
    ) -> None:
        """Initialize game log."""
        self.home_abbrev = home_abbrev
        self.away_abbrev = away_abbrev
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.entries: list[LogEntry] = []
        self.scoring_plays: list[ScoringPlay] = []

        # Team statistics
        self.home_stats = TeamStats()
        self.away_stats = TeamStats()

        # Player statistics: player_id -> PlayerStats
        self.player_stats: dict[UUID, PlayerStats] = {}

        # Player info cache for name lookups
        self._player_cache: dict[UUID, tuple[str, str, str]] = {}  # id -> (name, pos, team)

        # Track current offensive team for scoring attribution
        self._current_offense_is_home: bool = False

    def connect_to_event_bus(self, event_bus: EventBus) -> None:
        """Subscribe to events from an event bus."""
        event_bus.subscribe(PlayCompletedEvent, self._handle_play_completed)
        event_bus.subscribe(ScoringEvent, self._handle_scoring)
        event_bus.subscribe(TurnoverEvent, self._handle_turnover)

    def set_possession(self, is_home_on_offense: bool) -> None:
        """Update current possession for score attribution."""
        self._current_offense_is_home = is_home_on_offense

    def register_player(self, player_id: UUID, name: str, position: str, team_abbrev: str) -> None:
        """Register a player for stats tracking."""
        self._player_cache[player_id] = (name, position, team_abbrev)

    def _get_or_create_player_stats(self, player_id: UUID) -> PlayerStats:
        """Get or create player stats entry."""
        if player_id not in self.player_stats:
            name, pos, team = self._player_cache.get(player_id, ("Unknown", "??", "???"))
            self.player_stats[player_id] = PlayerStats(
                player_id=player_id,
                player_name=name,
                position=pos,
                team_abbrev=team,
            )
        return self.player_stats[player_id]

    def add_entry(
        self,
        quarter: int,
        time_remaining: str,
        event_type: str,
        description: str,
        home_score: int,
        away_score: int,
        **kwargs,
    ) -> None:
        """Add a log entry manually."""
        entry = LogEntry(
            timestamp=datetime.now(),
            quarter=quarter,
            time_remaining=time_remaining,
            event_type=event_type,
            description=description,
            home_score=home_score,
            away_score=away_score,
            **kwargs,
        )
        self.entries.append(entry)

    def _handle_play_completed(self, event: PlayCompletedEvent) -> None:
        """Handle play completion event."""
        result = event.result
        play_call = result.play_call

        # Update possession from event
        self._current_offense_is_home = event.offense_is_home

        # Determine which team's stats to update
        stats = self.home_stats if self._current_offense_is_home else self.away_stats

        # Track play statistics
        is_pass = play_call.is_pass
        is_rush = play_call.is_run
        is_complete = result.outcome == PlayOutcome.COMPLETE
        is_sack = result.is_sack

        if is_pass:
            if is_sack:
                stats.sacks += 1
                stats.sack_yards += abs(result.yards_gained)
                # Track passer sack
                if result.passer_id:
                    passer_stats = self._get_or_create_player_stats(result.passer_id)
                    passer_stats.sacks_taken += 1
                # Track defender sack
                if result.tackler_id:
                    def_stats = self._get_or_create_player_stats(result.tackler_id)
                    def_stats.sacks += 1
            else:
                stats.pass_attempts += 1
                # Track passer stats
                if result.passer_id:
                    passer_stats = self._get_or_create_player_stats(result.passer_id)
                    passer_stats.pass_attempts += 1
                    if is_complete:
                        passer_stats.pass_completions += 1
                        passer_stats.pass_yards += result.yards_gained
                        if result.is_touchdown:
                            passer_stats.pass_tds += 1
                    if result.outcome == PlayOutcome.INTERCEPTION:
                        passer_stats.interceptions += 1

                # Track receiver stats
                if result.receiver_id:
                    rec_stats = self._get_or_create_player_stats(result.receiver_id)
                    rec_stats.targets += 1
                    if is_complete:
                        rec_stats.receptions += 1
                        rec_stats.receiving_yards += result.yards_gained
                        if result.is_touchdown:
                            rec_stats.receiving_tds += 1

                # Track interceptor stats
                if result.interceptor_id:
                    int_stats = self._get_or_create_player_stats(result.interceptor_id)
                    int_stats.interceptions_def += 1

                if is_complete:
                    stats.pass_completions += 1
                    stats.pass_yards += result.yards_gained
                    if result.is_touchdown:
                        stats.pass_tds += 1
                if result.outcome == PlayOutcome.INTERCEPTION:
                    stats.interceptions += 1

        elif is_rush:
            stats.rush_attempts += 1
            stats.rush_yards += result.yards_gained
            if result.is_touchdown:
                stats.rush_tds += 1
            if result.outcome in (PlayOutcome.FUMBLE, PlayOutcome.FUMBLE_LOST):
                stats.fumbles_lost += 1

            # Track rusher stats
            if result.rusher_id:
                rush_stats = self._get_or_create_player_stats(result.rusher_id)
                rush_stats.rush_attempts += 1
                rush_stats.rush_yards += result.yards_gained
                if result.is_touchdown:
                    rush_stats.rush_tds += 1
                if result.outcome in (PlayOutcome.FUMBLE, PlayOutcome.FUMBLE_LOST):
                    rush_stats.fumbles += 1

        # Track tackler stats
        if result.tackler_id and not is_sack:
            tackle_stats = self._get_or_create_player_stats(result.tackler_id)
            tackle_stats.tackles += 1

        # Handle field goal attempts
        if play_call.play_type == PlayType.FIELD_GOAL:
            stats.field_goals_attempted += 1
            if result.outcome == PlayOutcome.FIELD_GOAL_GOOD:
                stats.field_goals_made += 1

        self.add_entry(
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            event_type="PLAY",
            description=result.description,
            home_score=event.home_score,
            away_score=event.away_score,
            down=event.down,
            yards_to_go=event.yards_to_go,
            field_position=event.field_position,
            yards_gained=result.yards_gained,
            is_scoring_play=result.is_touchdown,
            is_turnover=result.is_turnover,
            is_pass=is_pass,
            is_rush=is_rush,
            is_complete=is_complete,
            is_sack=is_sack,
            offense_is_home=self._current_offense_is_home,
        )

    def _handle_scoring(self, event: ScoringEvent) -> None:
        """Handle scoring event."""
        # Determine team from event team_id if available, else fall back to possession
        if event.team_id is not None and self.home_team_id is not None:
            is_home = event.team_id == self.home_team_id
            team = self.home_abbrev if is_home else self.away_abbrev
        else:
            team = self.home_abbrev if self._current_offense_is_home else self.away_abbrev

        scoring_play = ScoringPlay(
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            team_abbrev=team,
            scoring_type=event.scoring_type,
            points=event.points,
            description=event.description,
            home_score_after=event.home_score,
            away_score_after=event.away_score,
        )
        self.scoring_plays.append(scoring_play)

    def _handle_turnover(self, event: TurnoverEvent) -> None:
        """Handle turnover event."""
        self.add_entry(
            quarter=event.quarter,
            time_remaining=event.time_remaining,
            event_type="TURNOVER",
            description=f"TURNOVER: {event.turnover_type}",
            home_score=event.home_score,
            away_score=event.away_score,
            is_turnover=True,
        )

    def get_plays_by_quarter(self) -> dict[int, list[LogEntry]]:
        """Group entries by quarter."""
        by_quarter: dict[int, list[LogEntry]] = {}
        for entry in self.entries:
            if entry.quarter not in by_quarter:
                by_quarter[entry.quarter] = []
            by_quarter[entry.quarter].append(entry)
        return by_quarter

    def get_scoring_summary(self) -> list[ScoringPlay]:
        """Get all scoring plays."""
        return self.scoring_plays.copy()

    @property
    def play_count(self) -> int:
        """Total number of plays logged."""
        return len([e for e in self.entries if e.event_type == "PLAY"])

    @property
    def turnover_count(self) -> int:
        """Total number of turnovers."""
        return len([e for e in self.entries if e.is_turnover])

    def get_team_stats(self, is_home: bool) -> TeamStats:
        """Get statistics for a team."""
        return self.home_stats if is_home else self.away_stats
