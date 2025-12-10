"""Stats Collector - Extracts statistics from game simulation."""

from typing import Optional
from uuid import UUID

from huddle.core.enums import PlayOutcome, PlayType
from huddle.core.models.game import GameState
from huddle.core.models.play import PlayResult
from huddle.core.models.stats import (
    GameLog,
    PlayerGameStats,
    TeamGameStats,
)
from huddle.core.models.team import Team


class StatsCollector:
    """
    Collects and aggregates statistics from game simulation.

    Processes PlayResult objects to build PlayerGameStats and TeamGameStats.
    """

    def __init__(
        self,
        home_team: Team,
        away_team: Team,
    ) -> None:
        """
        Initialize stats collector for a game.

        Args:
            home_team: Home team
            away_team: Away team
        """
        self.home_team = home_team
        self.away_team = away_team

        # Player stats keyed by player_id
        self._player_stats: dict[str, PlayerGameStats] = {}

        # Team stats
        self.home_stats = TeamGameStats(team_abbr=home_team.abbreviation)
        self.away_stats = TeamGameStats(team_abbr=away_team.abbreviation)

        # Play tracking
        self._plays: list[dict] = []
        self._scoring_plays: list[dict] = []

        # Current possession tracking
        self._current_possession_seconds = 0
        self._possession_team_id: Optional[UUID] = None

    def _get_or_create_player_stats(
        self,
        player_id: UUID,
        team: Team,
    ) -> PlayerGameStats:
        """Get or create player stats entry."""
        key = str(player_id)
        if key not in self._player_stats:
            # Find player in team roster
            player = team.roster.get_player(player_id)
            if player:
                self._player_stats[key] = PlayerGameStats(
                    player_id=player_id,
                    player_name=player.full_name,
                    team_abbr=team.abbreviation,
                    position=player.position.value,
                )
            else:
                # Player not found, create placeholder
                self._player_stats[key] = PlayerGameStats(
                    player_id=player_id,
                    player_name="Unknown",
                    team_abbr=team.abbreviation,
                    position="UNK",
                )
        return self._player_stats[key]

    def _get_team_for_player(self, player_id: UUID) -> Optional[Team]:
        """Determine which team a player belongs to."""
        if self.home_team.roster.get_player(player_id):
            return self.home_team
        elif self.away_team.roster.get_player(player_id):
            return self.away_team
        return None

    def process_play(
        self,
        play_result: PlayResult,
        game_state: GameState,
        play_number: int,
    ) -> None:
        """
        Process a play result and update stats.

        Args:
            play_result: The result of the play
            game_state: Current game state (after play)
            play_number: Sequential play number
        """
        # Track possession time
        if game_state.possession.team_with_ball != self._possession_team_id:
            # Possession changed
            if self._possession_team_id == game_state.home_team_id:
                self.home_stats.time_of_possession_seconds += self._current_possession_seconds
            elif self._possession_team_id == game_state.away_team_id:
                self.away_stats.time_of_possession_seconds += self._current_possession_seconds
            self._current_possession_seconds = 0
            self._possession_team_id = game_state.possession.team_with_ball

        self._current_possession_seconds += play_result.time_elapsed_seconds

        # Determine offensive team
        is_home_offense = game_state.is_home_on_offense()
        off_team = self.home_team if is_home_offense else self.away_team
        def_team = self.away_team if is_home_offense else self.home_team
        off_stats = self.home_stats if is_home_offense else self.away_stats
        def_stats = self.away_stats if is_home_offense else self.home_stats

        play_type = play_result.play_call.play_type

        # Track passing plays
        if play_type == PlayType.PASS:
            self._process_pass_play(play_result, off_team, def_team, off_stats, def_stats)

        # Track rushing plays
        elif play_type == PlayType.RUN:
            self._process_rush_play(play_result, off_team, def_team, off_stats, def_stats)

        # Track field goals
        elif play_type == PlayType.FIELD_GOAL:
            self._process_field_goal(play_result, off_team, off_stats)

        # Track extra points
        elif play_type == PlayType.EXTRA_POINT:
            self._process_extra_point(play_result, off_team, off_stats)

        # Track first downs
        if play_result.is_first_down:
            off_stats.first_downs += 1

        # Track penalties
        if play_result.penalty_type and not play_result.penalty_declined:
            if play_result.penalty_on_offense:
                off_stats.penalties += 1
                off_stats.penalty_yards += play_result.penalty_yards
            else:
                def_stats.penalties += 1
                def_stats.penalty_yards += play_result.penalty_yards

        # Track turnovers
        if play_result.is_turnover:
            off_stats.turnovers += 1

        # Record play
        play_dict = {
            "play_number": play_number,
            "quarter": game_state.current_quarter,
            "time": game_state.clock.display,
            "down": game_state.down_state.down,
            "distance": game_state.down_state.yards_to_go,
            "yard_line": game_state.down_state.line_of_scrimmage,
            "offense": off_team.abbreviation,
            "play_type": play_type.name,
            "yards": play_result.yards_gained,
            "outcome": play_result.outcome.name,
            "description": play_result.description,
            "is_scoring": play_result.points_scored > 0,
        }
        self._plays.append(play_dict)

        # Record scoring play
        if play_result.points_scored > 0:
            self._scoring_plays.append({
                **play_dict,
                "points": play_result.points_scored,
                "home_score": game_state.score.home_score,
                "away_score": game_state.score.away_score,
            })

    def _process_pass_play(
        self,
        play_result: PlayResult,
        off_team: Team,
        def_team: Team,
        off_stats: TeamGameStats,
        def_stats: TeamGameStats,
    ) -> None:
        """Process passing play stats."""
        # Get passer stats
        if play_result.passer_id:
            passer_stats = self._get_or_create_player_stats(play_result.passer_id, off_team)

            if play_result.is_sack:
                # Sack
                passer_stats.passing.sacks += 1
                passer_stats.passing.sack_yards += abs(play_result.yards_gained)
            else:
                # Pass attempt
                passer_stats.passing.attempts += 1

                if play_result.outcome == PlayOutcome.COMPLETE:
                    passer_stats.passing.completions += 1
                    passer_stats.passing.yards += play_result.yards_gained
                    passer_stats.passing.longest = max(
                        passer_stats.passing.longest,
                        play_result.yards_gained
                    )
                    off_stats.passing_yards += play_result.yards_gained
                    off_stats.total_yards += play_result.yards_gained

                    if play_result.is_touchdown:
                        passer_stats.passing.touchdowns += 1
                        off_stats.touchdowns += 1

                elif play_result.outcome == PlayOutcome.INTERCEPTION:
                    passer_stats.passing.interceptions += 1

        # Get receiver stats
        if play_result.receiver_id and play_result.outcome == PlayOutcome.COMPLETE:
            receiver_stats = self._get_or_create_player_stats(play_result.receiver_id, off_team)
            receiver_stats.receiving.targets += 1
            receiver_stats.receiving.receptions += 1
            receiver_stats.receiving.yards += play_result.yards_gained
            receiver_stats.receiving.longest = max(
                receiver_stats.receiving.longest,
                play_result.yards_gained
            )
            if play_result.is_touchdown:
                receiver_stats.receiving.touchdowns += 1

        # Track incomplete pass as target
        if play_result.receiver_id and play_result.outcome == PlayOutcome.INCOMPLETE:
            receiver_stats = self._get_or_create_player_stats(play_result.receiver_id, off_team)
            receiver_stats.receiving.targets += 1

        # Defensive stats
        if play_result.tackler_id:
            tackler_stats = self._get_or_create_player_stats(play_result.tackler_id, def_team)
            tackler_stats.defense.tackles += 1
            if play_result.is_sack:
                tackler_stats.defense.sacks += 1.0

        if play_result.interceptor_id:
            int_stats = self._get_or_create_player_stats(play_result.interceptor_id, def_team)
            int_stats.defense.interceptions += 1

        # Passes defended on incomplete
        if play_result.outcome == PlayOutcome.INCOMPLETE and play_result.tackler_id:
            pd_stats = self._get_or_create_player_stats(play_result.tackler_id, def_team)
            pd_stats.defense.passes_defended += 1

    def _process_rush_play(
        self,
        play_result: PlayResult,
        off_team: Team,
        def_team: Team,
        off_stats: TeamGameStats,
        def_stats: TeamGameStats,
    ) -> None:
        """Process rushing play stats."""
        if play_result.rusher_id:
            rusher_stats = self._get_or_create_player_stats(play_result.rusher_id, off_team)
            rusher_stats.rushing.attempts += 1
            rusher_stats.rushing.yards += play_result.yards_gained
            rusher_stats.rushing.longest = max(
                rusher_stats.rushing.longest,
                play_result.yards_gained
            )
            off_stats.rushing_yards += play_result.yards_gained
            off_stats.total_yards += play_result.yards_gained

            if play_result.is_touchdown:
                rusher_stats.rushing.touchdowns += 1
                off_stats.touchdowns += 1

            if play_result.outcome == PlayOutcome.FUMBLE_LOST:
                rusher_stats.rushing.fumbles += 1
                rusher_stats.rushing.fumbles_lost += 1

        # Defensive stats
        if play_result.tackler_id:
            tackler_stats = self._get_or_create_player_stats(play_result.tackler_id, def_team)
            tackler_stats.defense.tackles += 1
            if play_result.yards_gained < 0:
                tackler_stats.defense.tackles_for_loss += 1

        if play_result.fumble_forced_by_id:
            ff_stats = self._get_or_create_player_stats(play_result.fumble_forced_by_id, def_team)
            ff_stats.defense.forced_fumbles += 1

        if play_result.fumble_recovered_by_id:
            fr_team = self._get_team_for_player(play_result.fumble_recovered_by_id)
            if fr_team:
                fr_stats = self._get_or_create_player_stats(play_result.fumble_recovered_by_id, fr_team)
                fr_stats.defense.fumble_recoveries += 1

    def _process_field_goal(
        self,
        play_result: PlayResult,
        off_team: Team,
        off_stats: TeamGameStats,
    ) -> None:
        """Process field goal stats."""
        # Find kicker (should be primary ball carrier for FG)
        kicker_id = None
        kicker = off_team.roster.depth_chart.get_starter("K")
        if kicker:
            kicker_id = kicker

        if kicker_id:
            kicker_stats = self._get_or_create_player_stats(kicker_id, off_team)
            kicker_stats.kicking.fg_attempts += 1
            if play_result.outcome == PlayOutcome.FIELD_GOAL_GOOD:
                kicker_stats.kicking.fg_made += 1
                off_stats.field_goals += 1
                # Estimate distance from yard line
                fg_distance = 100 - play_result.yards_gained + 17  # Add 17 for snap + end zone
                kicker_stats.kicking.fg_longest = max(
                    kicker_stats.kicking.fg_longest,
                    fg_distance
                )

    def _process_extra_point(
        self,
        play_result: PlayResult,
        off_team: Team,
        off_stats: TeamGameStats,
    ) -> None:
        """Process extra point stats."""
        kicker_id = None
        kicker = off_team.roster.depth_chart.get_starter("K")
        if kicker:
            kicker_id = kicker

        if kicker_id:
            kicker_stats = self._get_or_create_player_stats(kicker_id, off_team)
            kicker_stats.kicking.xp_attempts += 1
            if play_result.outcome == PlayOutcome.EXTRA_POINT_GOOD:
                kicker_stats.kicking.xp_made += 1

    def finalize(
        self,
        game_id: UUID,
        week: int,
        home_score: int,
        away_score: int,
        is_overtime: bool = False,
        is_playoff: bool = False,
    ) -> GameLog:
        """
        Finalize stats and create GameLog.

        Args:
            game_id: ID of the game
            week: Week number
            home_score: Final home score
            away_score: Final away score
            is_overtime: Whether game went to OT
            is_playoff: Whether this is a playoff game

        Returns:
            Complete GameLog with all stats
        """
        # Finalize possession time
        if self._possession_team_id == self.home_team.id:
            self.home_stats.time_of_possession_seconds += self._current_possession_seconds
        elif self._possession_team_id == self.away_team.id:
            self.away_stats.time_of_possession_seconds += self._current_possession_seconds

        # Set final scores
        self.home_stats.points = home_score
        self.away_stats.points = away_score

        return GameLog(
            game_id=game_id,
            week=week,
            home_team_abbr=self.home_team.abbreviation,
            away_team_abbr=self.away_team.abbreviation,
            home_score=home_score,
            away_score=away_score,
            is_overtime=is_overtime,
            is_playoff=is_playoff,
            home_stats=self.home_stats,
            away_stats=self.away_stats,
            player_stats=self._player_stats,
            plays=self._plays,
            scoring_plays=self._scoring_plays,
        )
