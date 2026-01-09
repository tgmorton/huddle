"""Result Handler - Extract stats from V2 PlayResult.

Converts V2 simulation results into meaningful player statistics
that can be aggregated for box scores and career tracking.

Handles:
- Passing stats (attempts, completions, yards, TDs, INTs)
- Rushing stats (attempts, yards, TDs)
- Receiving stats (targets, receptions, yards, TDs)
- Defensive stats (tackles, sacks, INTs)
- Team stats (total yards, TOP, turnovers)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from huddle.simulation.v2.orchestrator import PlayResult
    from huddle.game.drive import DriveResult, PlayLog


# =============================================================================
# Individual Stat Lines
# =============================================================================

@dataclass
class PassingStats:
    """Passing statistics for a player."""
    attempts: int = 0
    completions: int = 0
    yards: float = 0.0
    touchdowns: int = 0
    interceptions: int = 0
    sacks: int = 0
    sack_yards: float = 0.0
    air_yards: float = 0.0
    longest: float = 0.0

    @property
    def completion_pct(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.completions / self.attempts * 100

    @property
    def yards_per_attempt(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.yards / self.attempts

    @property
    def passer_rating(self) -> float:
        """Calculate NFL passer rating."""
        if self.attempts == 0:
            return 0.0

        # Components (each capped at 2.375)
        a = max(0, min(2.375, ((self.completions / self.attempts) - 0.3) * 5))
        b = max(0, min(2.375, ((self.yards / self.attempts) - 3) * 0.25))
        c = max(0, min(2.375, (self.touchdowns / self.attempts) * 20))
        d = max(0, min(2.375, 2.375 - ((self.interceptions / self.attempts) * 25)))

        return ((a + b + c + d) / 6) * 100

    def format_line(self) -> str:
        return f"{self.completions}/{self.attempts}, {self.yards:.0f} yds, {self.touchdowns} TD, {self.interceptions} INT"


@dataclass
class RushingStats:
    """Rushing statistics for a player."""
    attempts: int = 0
    yards: float = 0.0
    touchdowns: int = 0
    fumbles: int = 0
    longest: float = 0.0

    @property
    def yards_per_carry(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.yards / self.attempts

    def format_line(self) -> str:
        return f"{self.attempts} car, {self.yards:.0f} yds, {self.touchdowns} TD"


@dataclass
class ReceivingStats:
    """Receiving statistics for a player."""
    targets: int = 0
    receptions: int = 0
    yards: float = 0.0
    touchdowns: int = 0
    air_yards: float = 0.0
    yac: float = 0.0
    longest: float = 0.0
    drops: int = 0

    @property
    def catch_rate(self) -> float:
        if self.targets == 0:
            return 0.0
        return self.receptions / self.targets * 100

    @property
    def yards_per_reception(self) -> float:
        if self.receptions == 0:
            return 0.0
        return self.yards / self.receptions

    def format_line(self) -> str:
        return f"{self.receptions}/{self.targets}, {self.yards:.0f} yds, {self.touchdowns} TD"


@dataclass
class DefensiveStats:
    """Defensive statistics for a player."""
    tackles: int = 0
    solo_tackles: int = 0
    assisted_tackles: int = 0
    sacks: float = 0.0
    sack_yards: float = 0.0
    interceptions: int = 0
    int_yards: float = 0.0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    tackles_for_loss: int = 0

    def format_line(self) -> str:
        parts = [f"{self.tackles} tkl"]
        if self.sacks > 0:
            parts.append(f"{self.sacks:.1f} sck")
        if self.interceptions > 0:
            parts.append(f"{self.interceptions} INT")
        return ", ".join(parts)


# =============================================================================
# Game Stat Sheet
# =============================================================================

@dataclass
class PlayerGameStats:
    """Complete stats for a player in a game."""
    player_id: str
    player_name: str = ""
    passing: PassingStats = field(default_factory=PassingStats)
    rushing: RushingStats = field(default_factory=RushingStats)
    receiving: ReceivingStats = field(default_factory=ReceivingStats)
    defense: DefensiveStats = field(default_factory=DefensiveStats)

    def has_offensive_stats(self) -> bool:
        return (
            self.passing.attempts > 0 or
            self.rushing.attempts > 0 or
            self.receiving.targets > 0
        )

    def has_defensive_stats(self) -> bool:
        return self.defense.tackles > 0 or self.defense.sacks > 0


@dataclass
class TeamGameStats:
    """Team-level statistics for a game."""
    total_yards: float = 0.0
    passing_yards: float = 0.0
    rushing_yards: float = 0.0
    first_downs: int = 0
    third_down_attempts: int = 0
    third_down_conversions: int = 0
    fourth_down_attempts: int = 0
    fourth_down_conversions: int = 0
    turnovers: int = 0
    time_of_possession: float = 0.0  # seconds
    penalties: int = 0
    penalty_yards: int = 0
    sacks_allowed: int = 0
    sack_yards_lost: float = 0.0

    @property
    def third_down_pct(self) -> float:
        if self.third_down_attempts == 0:
            return 0.0
        return self.third_down_conversions / self.third_down_attempts * 100

    @property
    def top_display(self) -> str:
        """Time of possession as MM:SS."""
        mins = int(self.time_of_possession // 60)
        secs = int(self.time_of_possession % 60)
        return f"{mins}:{secs:02d}"


@dataclass
class GameStatSheet:
    """Complete stat sheet for both teams in a game."""
    home_team_id: str
    away_team_id: str
    home_players: Dict[str, PlayerGameStats] = field(default_factory=dict)
    away_players: Dict[str, PlayerGameStats] = field(default_factory=dict)
    home_team: TeamGameStats = field(default_factory=TeamGameStats)
    away_team: TeamGameStats = field(default_factory=TeamGameStats)

    def get_player_stats(self, player_id: str, is_home: bool) -> PlayerGameStats:
        """Get or create player stats entry."""
        players = self.home_players if is_home else self.away_players
        if player_id not in players:
            players[player_id] = PlayerGameStats(player_id=player_id)
        return players[player_id]


# =============================================================================
# Result Handler
# =============================================================================

class ResultHandler:
    """Extracts and aggregates statistics from play results.

    Usage:
        handler = ResultHandler(home_team_id, away_team_id)

        for play_result in game_results:
            handler.process_play(play_result, is_home_offense=True)

        stats = handler.get_stat_sheet()
    """

    def __init__(self, home_team_id: str, away_team_id: str):
        self.stat_sheet = GameStatSheet(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        self._current_down = 1
        self._current_distance = 10

    def process_play(
        self,
        result: "PlayResult",
        is_home_offense: bool,
        down: int = 1,
        distance: int = 10,
        is_touchdown: bool = False,
    ) -> None:
        """Process a single play result and extract stats.

        Args:
            result: V2 PlayResult from orchestrator
            is_home_offense: True if home team has ball
            down: Down before play
            distance: Distance to first down before play
            is_touchdown: Whether play resulted in TD
        """
        self._current_down = down
        self._current_distance = distance

        # Route to appropriate handler based on outcome
        if result.outcome in ("complete", "incomplete", "interception"):
            self._process_pass_play(result, is_home_offense, is_touchdown)
        elif result.outcome == "sack":
            self._process_sack(result, is_home_offense)
        elif result.outcome in ("run", "fumble"):
            self._process_run_play(result, is_home_offense, is_touchdown)

        # Update team totals
        self._update_team_stats(result, is_home_offense)

        # Track third/fourth down conversions
        self._track_down_conversion(result, is_home_offense)

    def _process_pass_play(
        self,
        result: "PlayResult",
        is_home_offense: bool,
        is_touchdown: bool,
    ) -> None:
        """Process a passing play."""
        # Get passer stats
        if result.passer_id:
            passer = self.stat_sheet.get_player_stats(result.passer_id, is_home_offense)
            passer.passing.attempts += 1
            passer.passing.air_yards += result.air_yards

            if result.outcome == "complete":
                passer.passing.completions += 1
                passer.passing.yards += result.yards_gained
                passer.passing.longest = max(passer.passing.longest, result.yards_gained)
                if is_touchdown:
                    passer.passing.touchdowns += 1

            elif result.outcome == "interception":
                passer.passing.interceptions += 1

        # Get receiver stats
        if result.receiver_id:
            receiver = self.stat_sheet.get_player_stats(result.receiver_id, is_home_offense)
            receiver.receiving.targets += 1
            receiver.receiving.air_yards += result.air_yards

            if result.outcome == "complete":
                receiver.receiving.receptions += 1
                receiver.receiving.yards += result.yards_gained
                receiver.receiving.yac += result.yac
                receiver.receiving.longest = max(receiver.receiving.longest, result.yards_gained)
                if is_touchdown:
                    receiver.receiving.touchdowns += 1

        # Get defender stats for interception
        if result.outcome == "interception" and result.tackler_id:
            defender = self.stat_sheet.get_player_stats(result.tackler_id, not is_home_offense)
            defender.defense.interceptions += 1

        # Incomplete = pass defended (if we track defender)
        if result.outcome == "incomplete" and result.tackler_id:
            defender = self.stat_sheet.get_player_stats(result.tackler_id, not is_home_offense)
            defender.defense.passes_defended += 1

    def _process_sack(
        self,
        result: "PlayResult",
        is_home_offense: bool,
    ) -> None:
        """Process a sack."""
        # Passer gets sack recorded
        if result.passer_id:
            passer = self.stat_sheet.get_player_stats(result.passer_id, is_home_offense)
            passer.passing.sacks += 1
            passer.passing.sack_yards += abs(result.yards_gained)

        # Defender gets sack credit
        if result.tackler_id:
            defender = self.stat_sheet.get_player_stats(result.tackler_id, not is_home_offense)
            defender.defense.sacks += 1.0
            defender.defense.sack_yards += abs(result.yards_gained)
            defender.defense.tackles += 1
            defender.defense.tackles_for_loss += 1

        # Team sacks allowed
        team_stats = self.stat_sheet.home_team if is_home_offense else self.stat_sheet.away_team
        team_stats.sacks_allowed += 1
        team_stats.sack_yards_lost += abs(result.yards_gained)

    def _process_run_play(
        self,
        result: "PlayResult",
        is_home_offense: bool,
        is_touchdown: bool,
    ) -> None:
        """Process a rushing play."""
        # Get ball carrier (use receiver_id for now - could add rusher_id)
        rusher_id = result.receiver_id or result.passer_id
        if rusher_id:
            rusher = self.stat_sheet.get_player_stats(rusher_id, is_home_offense)
            rusher.rushing.attempts += 1
            rusher.rushing.yards += result.yards_gained
            rusher.rushing.longest = max(rusher.rushing.longest, result.yards_gained)
            if is_touchdown:
                rusher.rushing.touchdowns += 1
            if result.outcome == "fumble":
                rusher.rushing.fumbles += 1

        # Tackler gets credit
        if result.tackler_id:
            tackler = self.stat_sheet.get_player_stats(result.tackler_id, not is_home_offense)
            tackler.defense.tackles += 1
            if result.yards_gained < 0:
                tackler.defense.tackles_for_loss += 1

        # Fumble recovery
        if result.outcome == "fumble" and result.tackler_id:
            tackler = self.stat_sheet.get_player_stats(result.tackler_id, not is_home_offense)
            tackler.defense.fumble_recoveries += 1

    def _update_team_stats(
        self,
        result: "PlayResult",
        is_home_offense: bool,
    ) -> None:
        """Update team-level statistics."""
        team_stats = self.stat_sheet.home_team if is_home_offense else self.stat_sheet.away_team

        # Yards
        if result.outcome != "sack":
            team_stats.total_yards += result.yards_gained

            if result.outcome in ("complete", "incomplete", "interception"):
                if result.outcome == "complete":
                    team_stats.passing_yards += result.yards_gained
            else:
                team_stats.rushing_yards += result.yards_gained

        # First downs
        if result.yards_gained >= self._current_distance:
            team_stats.first_downs += 1

        # Turnovers
        if result.outcome in ("interception", "fumble"):
            team_stats.turnovers += 1

        # Time of possession
        team_stats.time_of_possession += result.duration

    def _track_down_conversion(
        self,
        result: "PlayResult",
        is_home_offense: bool,
    ) -> None:
        """Track third and fourth down conversions."""
        team_stats = self.stat_sheet.home_team if is_home_offense else self.stat_sheet.away_team

        converted = result.yards_gained >= self._current_distance

        if self._current_down == 3:
            team_stats.third_down_attempts += 1
            if converted:
                team_stats.third_down_conversions += 1
        elif self._current_down == 4:
            team_stats.fourth_down_attempts += 1
            if converted:
                team_stats.fourth_down_conversions += 1

    def process_drive(
        self,
        drive_result: "DriveResult",
        is_home_offense: bool,
    ) -> None:
        """Process all plays in a drive.

        Args:
            drive_result: Complete drive result with play logs
            is_home_offense: True if home team had ball
        """
        for play_log in drive_result.plays:
            # We need the full PlayResult, not just PlayLog
            # This is a limitation - PlayLog doesn't have all details
            # For now, just update team TOP
            pass

        # Update team time of possession
        team_stats = self.stat_sheet.home_team if is_home_offense else self.stat_sheet.away_team
        team_stats.time_of_possession += drive_result.time_of_possession

    def get_stat_sheet(self) -> GameStatSheet:
        """Get the complete stat sheet."""
        return self.stat_sheet

    def get_box_score(self) -> dict:
        """Get a simplified box score for display.

        Returns dict with team totals and top performers.
        """
        return {
            "home": {
                "total_yards": self.stat_sheet.home_team.total_yards,
                "passing_yards": self.stat_sheet.home_team.passing_yards,
                "rushing_yards": self.stat_sheet.home_team.rushing_yards,
                "first_downs": self.stat_sheet.home_team.first_downs,
                "turnovers": self.stat_sheet.home_team.turnovers,
                "time_of_possession": self.stat_sheet.home_team.top_display,
                "third_down": f"{self.stat_sheet.home_team.third_down_conversions}/{self.stat_sheet.home_team.third_down_attempts}",
            },
            "away": {
                "total_yards": self.stat_sheet.away_team.total_yards,
                "passing_yards": self.stat_sheet.away_team.passing_yards,
                "rushing_yards": self.stat_sheet.away_team.rushing_yards,
                "first_downs": self.stat_sheet.away_team.first_downs,
                "turnovers": self.stat_sheet.away_team.turnovers,
                "time_of_possession": self.stat_sheet.away_team.top_display,
                "third_down": f"{self.stat_sheet.away_team.third_down_conversions}/{self.stat_sheet.away_team.third_down_attempts}",
            },
        }
