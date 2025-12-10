"""
Season Simulation - Orchestrates simulating games across weeks.

This module provides the SeasonSimulator class which:
- Uses SimulationEngine to simulate individual games
- Works with the League class to manage weekly progression
- Updates standings after each game
- Handles week-by-week simulation through the 18-week regular season
- Collects and stores game statistics
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from uuid import UUID

from huddle.core.league.league import League, ScheduledGame
from huddle.core.models.stats import GameLog
from huddle.core.models.team import Team
from huddle.simulation.engine import SimulationEngine, SimulationMode
from huddle.simulation.stats_collector import StatsCollector


@dataclass
class GameResult:
    """Result of a simulated game."""

    game_id: UUID
    home_team_abbr: str
    away_team_abbr: str
    home_score: int
    away_score: int
    is_overtime: bool = False

    @property
    def winner_abbr(self) -> Optional[str]:
        """Get winner abbreviation, None if tie."""
        if self.home_score > self.away_score:
            return self.home_team_abbr
        elif self.away_score > self.home_score:
            return self.away_team_abbr
        return None

    @property
    def loser_abbr(self) -> Optional[str]:
        """Get loser abbreviation, None if tie."""
        if self.home_score > self.away_score:
            return self.away_team_abbr
        elif self.away_score > self.home_score:
            return self.home_team_abbr
        return None

    @property
    def is_tie(self) -> bool:
        """Check if game ended in a tie."""
        return self.home_score == self.away_score

    def __str__(self) -> str:
        winner = "TIE" if self.is_tie else self.winner_abbr
        ot = " (OT)" if self.is_overtime else ""
        return f"{self.away_team_abbr} {self.away_score} @ {self.home_team_abbr} {self.home_score}{ot} - {winner}"


@dataclass
class WeekResult:
    """Results from simulating a week of games."""

    week: int
    games: list[GameResult] = field(default_factory=list)

    @property
    def total_games(self) -> int:
        return len(self.games)

    def get_team_result(self, abbreviation: str) -> Optional[GameResult]:
        """Get the result for a specific team's game this week."""
        for game in self.games:
            if game.home_team_abbr == abbreviation or game.away_team_abbr == abbreviation:
                return game
        return None

    def __str__(self) -> str:
        lines = [f"Week {self.week} Results ({self.total_games} games):"]
        for game in self.games:
            lines.append(f"  {game}")
        return "\n".join(lines)


class SeasonSimulator:
    """
    Orchestrates season-level game simulation.

    Bridges the SimulationEngine (individual games) with the League
    (schedule, standings, teams) to simulate entire weeks or seasons.
    """

    def __init__(
        self,
        league: League,
        mode: SimulationMode = SimulationMode.FAST,
    ) -> None:
        """
        Initialize season simulator.

        Args:
            league: The League to simulate
            mode: Simulation detail level (FAST or PLAY_BY_PLAY)
        """
        self.league = league
        self.engine = SimulationEngine(mode=mode)

        # Callbacks for UI integration
        self._on_game_complete: list[Callable[[GameResult], None]] = []
        self._on_week_complete: list[Callable[[WeekResult], None]] = []

    def on_game_complete(self, callback: Callable[[GameResult], None]) -> None:
        """Register callback for when each game completes."""
        self._on_game_complete.append(callback)

    def on_week_complete(self, callback: Callable[[WeekResult], None]) -> None:
        """Register callback for when a week completes."""
        self._on_week_complete.append(callback)

    def simulate_game(self, scheduled_game: ScheduledGame) -> GameResult:
        """
        Simulate a single scheduled game.

        Args:
            scheduled_game: The game to simulate

        Returns:
            GameResult with scores and winner
        """
        # Get teams
        home_team = self.league.get_team(scheduled_game.home_team_abbr)
        away_team = self.league.get_team(scheduled_game.away_team_abbr)

        if not home_team or not away_team:
            raise ValueError(
                f"Teams not found: {scheduled_game.home_team_abbr} vs {scheduled_game.away_team_abbr}"
            )

        # Create and run game using engine's simulate_game method
        game_state = self.engine.create_game(home_team, away_team)
        final_state = self.engine.simulate_game(game_state)

        # Check for overtime
        is_overtime = final_state.current_quarter > 4

        # Create result
        result = GameResult(
            game_id=scheduled_game.id,
            home_team_abbr=scheduled_game.home_team_abbr,
            away_team_abbr=scheduled_game.away_team_abbr,
            home_score=final_state.score.home_score,
            away_score=final_state.score.away_score,
            is_overtime=is_overtime,
        )

        # Update the scheduled game with results
        scheduled_game.home_score = result.home_score
        scheduled_game.away_score = result.away_score

        # Extract stats from play history and create game log
        game_log = self._extract_game_log(
            scheduled_game=scheduled_game,
            final_state=final_state,
            home_team=home_team,
            away_team=away_team,
            is_overtime=is_overtime,
        )
        self.league.add_game_log(game_log)

        # Update standings
        self.league.update_standings_from_game(scheduled_game)

        # Fire callbacks
        for callback in self._on_game_complete:
            callback(result)

        return result

    def _extract_game_log(
        self,
        scheduled_game: ScheduledGame,
        final_state,
        home_team,
        away_team,
        is_overtime: bool,
    ) -> GameLog:
        """Extract game log from completed game state."""
        from huddle.core.models.stats import (
            GameLog, TeamGameStats, PlayerGameStats,
            PassingStats, RushingStats, ReceivingStats, DefensiveStats
        )
        from huddle.core.enums import PlayOutcome

        # Track player stats
        player_stats: dict[str, PlayerGameStats] = {}

        def get_player_stats(player_id, team) -> PlayerGameStats:
            """Get or create player stats entry."""
            key = str(player_id)
            if key not in player_stats:
                player = team.roster.get_player(player_id)
                if player:
                    player_stats[key] = PlayerGameStats(
                        player_id=player_id,
                        player_name=player.full_name,
                        team_abbr=team.abbreviation,
                        position=player.position.value,
                    )
            return player_stats.get(key)

        # Calculate team stats from play history
        home_passing = 0
        home_rushing = 0
        away_passing = 0
        away_rushing = 0
        home_turnovers = 0
        away_turnovers = 0

        for play in final_state.play_history:
            yards = play.yards_gained

            # Track passing plays
            if play.passer_id:
                passer_team = home_team if home_team.roster.get_player(play.passer_id) else away_team
                pstats = get_player_stats(play.passer_id, passer_team)
                if pstats:
                    pstats.passing.attempts += 1
                    if play.outcome == PlayOutcome.COMPLETE:
                        pstats.passing.completions += 1
                        pstats.passing.yards += max(0, yards)
                        if passer_team == home_team:
                            home_passing += max(0, yards)
                        else:
                            away_passing += max(0, yards)
                        if play.is_touchdown:
                            pstats.passing.touchdowns += 1
                    elif play.outcome == PlayOutcome.INTERCEPTION:
                        pstats.passing.interceptions += 1
                        if passer_team == home_team:
                            home_turnovers += 1
                        else:
                            away_turnovers += 1
                    elif play.is_sack:
                        pstats.passing.sacks += 1

            # Track receiving
            if play.receiver_id and play.outcome == PlayOutcome.COMPLETE:
                rec_team = home_team if home_team.roster.get_player(play.receiver_id) else away_team
                rstats = get_player_stats(play.receiver_id, rec_team)
                if rstats:
                    rstats.receiving.receptions += 1
                    rstats.receiving.yards += max(0, yards)
                    rstats.receiving.targets += 1
                    if play.is_touchdown:
                        rstats.receiving.touchdowns += 1

            # Track rushing plays
            if play.rusher_id:
                rusher_team = home_team if home_team.roster.get_player(play.rusher_id) else away_team
                rush_stats = get_player_stats(play.rusher_id, rusher_team)
                if rush_stats:
                    rush_stats.rushing.attempts += 1
                    rush_stats.rushing.yards += yards
                    if rusher_team == home_team:
                        home_rushing += yards
                    else:
                        away_rushing += yards
                    if play.is_touchdown:
                        rush_stats.rushing.touchdowns += 1
                    if play.outcome == PlayOutcome.FUMBLE_LOST:
                        rush_stats.rushing.fumbles_lost += 1
                        if rusher_team == home_team:
                            home_turnovers += 1
                        else:
                            away_turnovers += 1

            # Track tackles
            if play.tackler_id:
                tackler_team = home_team if home_team.roster.get_player(play.tackler_id) else away_team
                tstats = get_player_stats(play.tackler_id, tackler_team)
                if tstats:
                    tstats.defense.tackles += 1
                    if play.is_sack:
                        tstats.defense.sacks += 1.0

            # Track interceptions
            if play.interceptor_id:
                int_team = home_team if home_team.roster.get_player(play.interceptor_id) else away_team
                istats = get_player_stats(play.interceptor_id, int_team)
                if istats:
                    istats.defense.interceptions += 1

        home_stats = TeamGameStats(
            team_abbr=home_team.abbreviation,
            total_yards=home_passing + home_rushing,
            passing_yards=home_passing,
            rushing_yards=home_rushing,
            turnovers=home_turnovers,
            points=final_state.score.home_score,
        )

        away_stats = TeamGameStats(
            team_abbr=away_team.abbreviation,
            total_yards=away_passing + away_rushing,
            passing_yards=away_passing,
            rushing_yards=away_rushing,
            turnovers=away_turnovers,
            points=final_state.score.away_score,
        )

        # Build play log
        plays = []
        scoring_plays = []
        for i, play in enumerate(final_state.play_history):
            play_dict = {
                "play_number": i + 1,
                "description": play.description,
                "yards": play.yards_gained,
                "is_scoring": play.points_scored > 0,
            }
            plays.append(play_dict)

            if play.points_scored > 0:
                scoring_plays.append({
                    **play_dict,
                    "points": play.points_scored,
                })

        return GameLog(
            game_id=scheduled_game.id,
            week=scheduled_game.week,
            home_team_abbr=home_team.abbreviation,
            away_team_abbr=away_team.abbreviation,
            home_score=final_state.score.home_score,
            away_score=final_state.score.away_score,
            is_overtime=is_overtime,
            is_playoff=scheduled_game.is_playoff,
            home_stats=home_stats,
            away_stats=away_stats,
            player_stats=player_stats,
            plays=plays,
            scoring_plays=scoring_plays,
        )

    def simulate_week(self, week: Optional[int] = None) -> WeekResult:
        """
        Simulate all games for a week.

        Args:
            week: Week number to simulate. If None, uses league's current_week + 1

        Returns:
            WeekResult with all game results
        """
        if week is None:
            week = self.league.current_week + 1

        # Get games for this week
        games = self.league.get_games_for_week(week)

        if not games:
            return WeekResult(week=week)

        # Filter to unplayed games only
        unplayed = [g for g in games if not g.is_played]

        if not unplayed:
            # Week already simulated
            return WeekResult(
                week=week,
                games=[
                    GameResult(
                        game_id=g.id,
                        home_team_abbr=g.home_team_abbr,
                        away_team_abbr=g.away_team_abbr,
                        home_score=g.home_score or 0,
                        away_score=g.away_score or 0,
                    )
                    for g in games
                ]
            )

        # Simulate each game
        results = []
        for game in unplayed:
            result = self.simulate_game(game)
            results.append(result)

        # Advance league week
        if self.league.current_week < week:
            self.league.current_week = week

        week_result = WeekResult(week=week, games=results)

        # Fire callbacks
        for callback in self._on_week_complete:
            callback(week_result)

        return week_result

    def simulate_to_week(self, target_week: int) -> list[WeekResult]:
        """
        Simulate from current week to target week (inclusive).

        Args:
            target_week: Week to simulate up to (1-18 for regular season)

        Returns:
            List of WeekResults for all simulated weeks
        """
        results = []
        start_week = self.league.current_week + 1

        for week in range(start_week, target_week + 1):
            week_result = self.simulate_week(week)
            results.append(week_result)

        return results

    def simulate_regular_season(self) -> list[WeekResult]:
        """
        Simulate the entire regular season (weeks 1-18).

        Returns:
            List of WeekResults for all 18 weeks
        """
        return self.simulate_to_week(18)

    def simulate_remaining_season(self) -> list[WeekResult]:
        """
        Simulate remaining games from current week to end of regular season.

        Returns:
            List of WeekResults for remaining weeks
        """
        current = self.league.current_week
        if current >= 18:
            return []
        return self.simulate_to_week(18)

    def get_standings_summary(self) -> dict[str, list[dict]]:
        """
        Get current standings organized by division.

        Returns:
            Dict mapping division names to lists of team standings
        """
        from huddle.core.league.nfl_data import Division

        summary = {}

        for division in Division:
            div_standings = self.league.get_division_standings(division)
            summary[division.name] = [
                {
                    "rank": i + 1,
                    "abbreviation": s.abbreviation,
                    "record": s.record_string,
                    "win_pct": s.win_pct,
                    "points_for": s.points_for,
                    "points_against": s.points_against,
                    "point_diff": s.point_diff,
                }
                for i, s in enumerate(div_standings)
            ]

        return summary

    def get_playoff_picture(self) -> dict[str, list[dict]]:
        """
        Get current playoff bracket for both conferences.

        Returns:
            Dict with AFC and NFC playoff standings
        """
        from huddle.core.league.nfl_data import Conference

        picture = {}

        for conference in Conference:
            bracket = self.league.get_playoff_bracket(conference)
            picture[conference.name] = [
                {
                    "seed": i + 1,
                    "abbreviation": s.abbreviation,
                    "record": s.record_string,
                    "win_pct": s.win_pct,
                    "division_winner": i < 4,  # Seeds 1-4 are division winners
                }
                for i, s in enumerate(bracket)
            ]

        return picture

    # ==========================================================================
    # Playoffs
    # ==========================================================================

    def generate_playoff_bracket(self) -> dict[str, list[ScheduledGame]]:
        """
        Generate playoff bracket after regular season ends.

        NFL Playoff Format (14 teams):
        - 7 teams per conference
        - #1 seed gets bye in Wild Card round
        - Wild Card: #2 vs #7, #3 vs #6, #4 vs #5
        - Divisional: #1 vs lowest remaining, other two play
        - Conference Championship: winners play
        - Super Bowl: AFC champ vs NFC champ

        Returns:
            Dict with 'wild_card', 'divisional', 'conference', 'super_bowl' keys
        """
        from huddle.core.league.nfl_data import Conference

        playoff_games = {
            'wild_card': [],
            'divisional': [],
            'conference': [],
            'super_bowl': [],
        }

        # Generate Wild Card games (Week 19)
        for conf in [Conference.AFC, Conference.NFC]:
            bracket = self.league.get_playoff_bracket(conf)
            if len(bracket) < 7:
                continue

            # Wild Card matchups: #2 vs #7, #3 vs #6, #4 vs #5
            matchups = [(1, 6), (2, 5), (3, 4)]  # 0-indexed
            for higher_idx, lower_idx in matchups:
                game = ScheduledGame(
                    week=19,
                    home_team_abbr=bracket[higher_idx].abbreviation,
                    away_team_abbr=bracket[lower_idx].abbreviation,
                    is_conference=True,
                    is_playoff=True,
                )
                playoff_games['wild_card'].append(game)
                self.league.schedule.append(game)

        return playoff_games

    def simulate_wild_card_round(self) -> list[GameResult]:
        """
        Simulate Wild Card round (Week 19).

        Returns:
            List of GameResults
        """
        if self.league.current_week < 18:
            raise ValueError("Regular season must be complete before playoffs")

        results = []
        wild_card_games = [g for g in self.league.schedule if g.week == 19 and not g.is_played]

        for game in wild_card_games:
            result = self.simulate_game(game)
            results.append(result)

        self.league.current_week = 19
        return results

    def generate_divisional_round(self) -> list[ScheduledGame]:
        """
        Generate Divisional round matchups based on Wild Card results.

        #1 seed plays lowest remaining seed.
        Other two winners play each other.

        Returns:
            List of Divisional round games
        """
        from huddle.core.league.nfl_data import Conference

        divisional_games = []

        for conf in [Conference.AFC, Conference.NFC]:
            bracket = self.league.get_playoff_bracket(conf)
            if len(bracket) < 7:
                continue

            # Get #1 seed (bye team)
            bye_team = bracket[0].abbreviation

            # Get Wild Card winners from this conference
            wc_games = [
                g for g in self.league.schedule
                if g.week == 19 and g.is_played and g.is_conference
            ]

            # Filter to this conference's games
            conf_teams = {s.abbreviation for s in bracket}
            conf_wc_games = [g for g in wc_games if g.home_team_abbr in conf_teams]

            # Get winners with their original seeds
            winners = []
            for game in conf_wc_games:
                winner = game.winner_abbr
                if winner:
                    # Find original seed
                    for i, s in enumerate(bracket):
                        if s.abbreviation == winner:
                            winners.append((winner, i + 1))
                            break

            if not winners:
                continue

            # Sort by seed (lowest seed number = highest seed)
            winners.sort(key=lambda x: x[1])

            # #1 seed plays lowest remaining seed (highest seed number)
            lowest_remaining = winners[-1][0]
            game1 = ScheduledGame(
                week=20,
                home_team_abbr=bye_team,
                away_team_abbr=lowest_remaining,
                is_conference=True,
                is_playoff=True,
            )
            divisional_games.append(game1)
            self.league.schedule.append(game1)

            # Other two winners play each other (higher seed hosts)
            if len(winners) >= 2:
                # Remove the lowest remaining that's playing #1
                other_winners = [w for w in winners if w[0] != lowest_remaining]
                if len(other_winners) >= 2:
                    # Higher seed (lower number) hosts
                    other_winners.sort(key=lambda x: x[1])
                    game2 = ScheduledGame(
                        week=20,
                        home_team_abbr=other_winners[0][0],
                        away_team_abbr=other_winners[1][0],
                        is_conference=True,
                        is_playoff=True,
                    )
                    divisional_games.append(game2)
                    self.league.schedule.append(game2)

        return divisional_games

    def simulate_divisional_round(self) -> list[GameResult]:
        """Simulate Divisional round (Week 20)."""
        results = []
        div_games = [g for g in self.league.schedule if g.week == 20 and not g.is_played]

        for game in div_games:
            result = self.simulate_game(game)
            results.append(result)

        self.league.current_week = 20
        return results

    def generate_conference_championships(self) -> list[ScheduledGame]:
        """
        Generate Conference Championship matchups.

        Returns:
            List of Conference Championship games
        """
        from huddle.core.league.nfl_data import Conference

        conf_games = []

        for conf in [Conference.AFC, Conference.NFC]:
            bracket = self.league.get_playoff_bracket(conf)
            conf_teams = {s.abbreviation for s in bracket}

            # Get Divisional round winners from this conference
            div_games = [
                g for g in self.league.schedule
                if g.week == 20 and g.is_played and g.home_team_abbr in conf_teams
            ]

            winners = []
            for game in div_games:
                winner = game.winner_abbr
                if winner:
                    # Find original seed
                    for i, s in enumerate(bracket):
                        if s.abbreviation == winner:
                            winners.append((winner, i + 1))
                            break

            if len(winners) >= 2:
                winners.sort(key=lambda x: x[1])
                game = ScheduledGame(
                    week=21,
                    home_team_abbr=winners[0][0],
                    away_team_abbr=winners[1][0],
                    is_conference=True,
                    is_playoff=True,
                )
                conf_games.append(game)
                self.league.schedule.append(game)

        return conf_games

    def simulate_conference_championships(self) -> list[GameResult]:
        """Simulate Conference Championships (Week 21)."""
        results = []
        conf_games = [g for g in self.league.schedule if g.week == 21 and not g.is_played]

        for game in conf_games:
            result = self.simulate_game(game)
            results.append(result)

        self.league.current_week = 21
        return results

    def generate_super_bowl(self) -> Optional[ScheduledGame]:
        """
        Generate Super Bowl matchup.

        Returns:
            Super Bowl game or None
        """
        from huddle.core.league.nfl_data import Conference

        afc_champ = None
        nfc_champ = None

        # Get conference championship winners
        conf_games = [g for g in self.league.schedule if g.week == 21 and g.is_played]

        for conf in [Conference.AFC, Conference.NFC]:
            bracket = self.league.get_playoff_bracket(conf)
            conf_teams = {s.abbreviation for s in bracket}

            for game in conf_games:
                if game.home_team_abbr in conf_teams:
                    winner = game.winner_abbr
                    if conf == Conference.AFC:
                        afc_champ = winner
                    else:
                        nfc_champ = winner
                    break

        if not afc_champ or not nfc_champ:
            return None

        # Super Bowl is neutral site but for simplicity use alternating home
        game = ScheduledGame(
            week=22,
            home_team_abbr=afc_champ,  # AFC "home" team in even years
            away_team_abbr=nfc_champ,
            is_playoff=True,
        )
        self.league.schedule.append(game)
        return game

    def simulate_super_bowl(self) -> Optional[GameResult]:
        """Simulate Super Bowl (Week 22)."""
        sb_games = [g for g in self.league.schedule if g.week == 22 and not g.is_played]

        if not sb_games:
            return None

        result = self.simulate_game(sb_games[0])

        # Record champion
        if result.winner_abbr:
            self.league.champions[self.league.current_season] = result.winner_abbr

        self.league.current_week = 22
        return result

    def simulate_playoffs(self) -> dict[str, list[GameResult]]:
        """
        Simulate entire playoff bracket.

        Returns:
            Dict with results for each round
        """
        results = {
            'wild_card': [],
            'divisional': [],
            'conference': [],
            'super_bowl': None,
        }

        # Generate and simulate Wild Card
        self.generate_playoff_bracket()
        results['wild_card'] = self.simulate_wild_card_round()

        # Generate and simulate Divisional
        self.generate_divisional_round()
        results['divisional'] = self.simulate_divisional_round()

        # Generate and simulate Conference Championships
        self.generate_conference_championships()
        results['conference'] = self.simulate_conference_championships()

        # Generate and simulate Super Bowl
        self.generate_super_bowl()
        sb_result = self.simulate_super_bowl()
        if sb_result:
            results['super_bowl'] = sb_result

        return results
