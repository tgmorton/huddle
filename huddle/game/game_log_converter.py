"""Game Log Converter - Bridge game layer stats to core stats model.

Converts GameStatSheet (from result_handler.py) to the official
core.models.stats.GameLog format for persistence in the management layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from huddle.core.models.stats import (
    GameLog,
    PlayerGameStats as CorePlayerGameStats,
    TeamGameStats as CoreTeamGameStats,
    PassingStats as CorePassingStats,
    RushingStats as CoreRushingStats,
    ReceivingStats as CoreReceivingStats,
    DefensiveStats as CoreDefensiveStats,
    KickingStats as CoreKickingStats,
)

if TYPE_CHECKING:
    from huddle.game.result_handler import (
        GameStatSheet,
        PlayerGameStats,
        TeamGameStats,
        PassingStats,
        RushingStats,
        ReceivingStats,
        DefensiveStats,
    )
    from huddle.game.manager import GameResult
    from huddle.core.models.player import Player as CorePlayer


def convert_passing_stats(stats: "PassingStats") -> CorePassingStats:
    """Convert game layer passing stats to core model."""
    return CorePassingStats(
        attempts=stats.attempts,
        completions=stats.completions,
        yards=int(stats.yards),
        touchdowns=stats.touchdowns,
        interceptions=stats.interceptions,
        sacks=stats.sacks,
        sack_yards=int(stats.sack_yards),
        longest=int(stats.longest),
    )


def convert_rushing_stats(stats: "RushingStats") -> CoreRushingStats:
    """Convert game layer rushing stats to core model."""
    return CoreRushingStats(
        attempts=stats.attempts,
        yards=int(stats.yards),
        touchdowns=stats.touchdowns,
        fumbles=stats.fumbles,
        fumbles_lost=0,  # Not tracked separately in game layer
        longest=int(stats.longest),
    )


def convert_receiving_stats(stats: "ReceivingStats") -> CoreReceivingStats:
    """Convert game layer receiving stats to core model."""
    return CoreReceivingStats(
        targets=stats.targets,
        receptions=stats.receptions,
        yards=int(stats.yards),
        touchdowns=stats.touchdowns,
        fumbles=0,  # Not tracked separately in game layer
        fumbles_lost=0,
        longest=int(stats.longest),
    )


def convert_defensive_stats(stats: "DefensiveStats") -> CoreDefensiveStats:
    """Convert game layer defensive stats to core model."""
    return CoreDefensiveStats(
        tackles=stats.tackles,
        tackles_for_loss=stats.tackles_for_loss,
        sacks=stats.sacks,
        interceptions=stats.interceptions,
        interception_yards=int(stats.int_yards),
        interception_tds=0,  # Not tracked in game layer yet
        passes_defended=stats.passes_defended,
        forced_fumbles=stats.forced_fumbles,
        fumble_recoveries=stats.fumble_recoveries,
        fumble_return_yards=0,
        fumble_return_tds=0,
        safeties=0,
    )


def convert_player_stats(
    player_id: str,
    stats: "PlayerGameStats",
    team_abbr: str,
    player: Optional["CorePlayer"] = None,
) -> CorePlayerGameStats:
    """Convert game layer player stats to core model.

    Args:
        player_id: Player UUID as string (or UUID object)
        stats: Game layer PlayerGameStats
        team_abbr: Team abbreviation (can be derived from player.team_id if player provided)
        player: Optional Player object for additional metadata

    Returns:
        Core model PlayerGameStats
    """
    # Handle UUID - with standardization, this should always work
    if isinstance(player_id, UUID):
        uuid = player_id
    else:
        try:
            uuid = UUID(player_id)
        except (ValueError, AttributeError):
            uuid = uuid4()

    # Get team_abbr from player if available (uses new team_id field)
    # This is a fallback - team_abbr parameter takes precedence
    resolved_team_abbr = team_abbr
    if not resolved_team_abbr and player and hasattr(player, 'team_id') and player.team_id:
        # Would need league lookup to convert team_id -> abbr
        # For now, keep using passed team_abbr
        pass

    # Get position from player if available
    position = ""
    if player and hasattr(player, 'position'):
        position = player.position or ""

    return CorePlayerGameStats(
        player_id=uuid,
        player_name=stats.player_name or (player.name if player else f"Player {str(uuid)[:8]}"),
        team_abbr=resolved_team_abbr,
        position=position,
        passing=convert_passing_stats(stats.passing),
        rushing=convert_rushing_stats(stats.rushing),
        receiving=convert_receiving_stats(stats.receiving),
        defense=convert_defensive_stats(stats.defense),
        kicking=CoreKickingStats(),  # Not tracked in game layer yet
    )


def convert_team_stats(
    stats: "TeamGameStats",
    team_abbr: str,
    score: int,
) -> CoreTeamGameStats:
    """Convert game layer team stats to core model.

    Args:
        stats: Game layer TeamGameStats
        team_abbr: Team abbreviation
        score: Final score for this team

    Returns:
        Core model TeamGameStats
    """
    # Calculate touchdowns and field goals from score
    # This is an approximation since we don't track scoring plays in detail
    touchdowns = score // 7
    remaining = score - (touchdowns * 7)
    field_goals = remaining // 3

    return CoreTeamGameStats(
        team_abbr=team_abbr,
        total_yards=int(stats.total_yards),
        passing_yards=int(stats.passing_yards),
        rushing_yards=int(stats.rushing_yards),
        first_downs=stats.first_downs,
        third_down_attempts=stats.third_down_attempts,
        third_down_conversions=stats.third_down_conversions,
        fourth_down_attempts=stats.fourth_down_attempts,
        fourth_down_conversions=stats.fourth_down_conversions,
        turnovers=stats.turnovers,
        penalties=stats.penalties,
        penalty_yards=stats.penalty_yards,
        time_of_possession_seconds=int(stats.time_of_possession),
        points=score,
        touchdowns=touchdowns,
        field_goals=field_goals,
    )


def convert_stat_sheet_to_game_log(
    stat_sheet: "GameStatSheet",
    game_result: "GameResult",
    week: int = 1,
) -> GameLog:
    """Convert a complete GameStatSheet to a GameLog.

    Args:
        stat_sheet: Game layer stat sheet with all player and team stats
        game_result: GameResult with final scores and game metadata
        week: Week number in the season

    Returns:
        Core model GameLog ready for persistence
    """
    game_id = uuid4()

    # Get team abbreviations
    home_abbr = stat_sheet.home_team_id
    away_abbr = stat_sheet.away_team_id

    # Convert team stats
    home_stats = convert_team_stats(
        stat_sheet.home_team,
        home_abbr,
        game_result.home_score,
    )
    away_stats = convert_team_stats(
        stat_sheet.away_team,
        away_abbr,
        game_result.away_score,
    )

    # Convert player stats
    player_stats: dict[str, CorePlayerGameStats] = {}

    for player_id, stats in stat_sheet.home_players.items():
        player_stats[player_id] = convert_player_stats(
            player_id, stats, home_abbr
        )

    for player_id, stats in stat_sheet.away_players.items():
        player_stats[player_id] = convert_player_stats(
            player_id, stats, away_abbr
        )

    # Build play-by-play from drive results if available
    plays: list[dict] = []
    scoring_plays: list[dict] = []

    for i, drive in enumerate(game_result.drives):
        for j, play_log in enumerate(drive.plays):
            play_dict = {
                "drive": i + 1,
                "play": j + 1,
                "down": play_log.down,
                "distance": play_log.distance,
                "yard_line": play_log.yard_line,
                "description": play_log.description,
                "yards_gained": play_log.yards_gained,
            }
            plays.append(play_dict)

        # Check for scoring drive
        if drive.result in ("touchdown", "field_goal"):
            scoring_plays.append({
                "drive": i + 1,
                "result": drive.result,
                "description": f"Drive ended with {drive.result}",
            })

    return GameLog(
        game_id=game_id,
        week=week,
        home_team_abbr=home_abbr,
        away_team_abbr=away_abbr,
        home_score=game_result.home_score,
        away_score=game_result.away_score,
        is_overtime=False,  # Could be added to GameResult
        is_playoff=False,   # Could be passed in
        home_stats=home_stats,
        away_stats=away_stats,
        player_stats=player_stats,
        plays=plays,
        scoring_plays=scoring_plays,
    )


def create_game_log_from_result(
    game_result: "GameResult",
    home_team_abbr: str,
    away_team_abbr: str,
    week: int = 1,
) -> GameLog:
    """Create a GameLog directly from a GameResult.

    This is a convenience function when you have the full GameResult
    but not a separate stat sheet.

    Args:
        game_result: Complete game result with stats
        home_team_abbr: Home team abbreviation
        away_team_abbr: Away team abbreviation
        week: Week number

    Returns:
        Core model GameLog
    """
    # Get the stat sheet from result handler (if attached)
    if hasattr(game_result, 'stat_sheet') and game_result.stat_sheet:
        return convert_stat_sheet_to_game_log(
            game_result.stat_sheet,
            game_result,
            week,
        )

    # Otherwise create minimal game log
    return GameLog(
        game_id=uuid4(),
        week=week,
        home_team_abbr=home_team_abbr,
        away_team_abbr=away_team_abbr,
        home_score=game_result.home_score,
        away_score=game_result.away_score,
        home_stats=CoreTeamGameStats(team_abbr=home_team_abbr, points=game_result.home_score),
        away_stats=CoreTeamGameStats(team_abbr=away_team_abbr, points=game_result.away_score),
    )


def persist_game_result(
    game_result: "GameResult",
    league,
    home_team_abbr: str,
    away_team_abbr: str,
    week: Optional[int] = None,
) -> GameLog:
    """Persist a game result to the league's game history.

    This is the main integration point between game layer and management layer.
    Converts the game result to a GameLog and adds it to the league.

    Args:
        game_result: Complete game result from GameManager
        league: League object (from session.service.league or get_active_league())
        home_team_abbr: Home team abbreviation
        away_team_abbr: Away team abbreviation
        week: Week number (defaults to league.current_week)

    Returns:
        The persisted GameLog

    Example:
        ```python
        from huddle.game import persist_game_result
        from huddle.api.routers.admin import get_active_league

        # After game completes
        game_log = persist_game_result(
            game_result=game_result,
            league=get_active_league(),
            home_team_abbr="BUF",
            away_team_abbr="MIA",
        )
        ```
    """
    # Use league's current week if not specified
    if week is None:
        week = getattr(league, 'current_week', 1)

    # Convert to GameLog
    game_log = create_game_log_from_result(
        game_result=game_result,
        home_team_abbr=home_team_abbr,
        away_team_abbr=away_team_abbr,
        week=week,
    )

    # Persist to league
    # league.add_game_log() stores in league.game_logs and
    # auto-aggregates player stats into league.season_stats
    league.add_game_log(game_log)

    return game_log


def persist_game_to_session(
    game_result: "GameResult",
    session,
    home_team_abbr: str,
    away_team_abbr: str,
    week: Optional[int] = None,
) -> GameLog:
    """Persist a game result using a management session.

    Convenience function for router endpoints that have access to session.

    Args:
        game_result: Complete game result
        session: Management session (from get_session(franchise_id))
        home_team_abbr: Home team abbreviation
        away_team_abbr: Away team abbreviation
        week: Week number (defaults to league.current_week)

    Returns:
        The persisted GameLog
    """
    league = session.service.league
    return persist_game_result(
        game_result=game_result,
        league=league,
        home_team_abbr=home_team_abbr,
        away_team_abbr=away_team_abbr,
        week=week,
    )
