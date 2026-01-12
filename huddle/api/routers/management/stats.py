"""
Stats API router.

Endpoints for querying game logs, player stats, and league leaders.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from huddle.api.schemas.management import (
    GameLogSummaryResponse,
    GameLogsListResponse,
    GameLogDetailResponse,
    PlayerStatLineResponse,
    PlayerSeasonStatsResponse,
    LeaderEntryResponse,
    LeadersResponse,
)
from huddle.api.routers.admin import get_active_league
from .deps import get_session_with_team

router = APIRouter(tags=["stats"])


@router.get("/franchise/{franchise_id}/stats/games", response_model=GameLogsListResponse)
async def list_game_logs(
    franchise_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
) -> GameLogsListResponse:
    """
    List game logs for the franchise's team.

    Returns games sorted by week (most recent first), limited to specified count.
    """
    session = get_session_with_team(franchise_id)
    league = session.service.league
    team_abbr = session.team.abbreviation

    # Get all game logs for this team
    game_logs = league.get_team_game_logs(team_abbr)

    # Sort by week descending (most recent first)
    game_logs.sort(key=lambda g: g.week, reverse=True)

    # Limit results
    game_logs = game_logs[:limit]

    # Convert to summaries
    summaries = []
    for log in game_logs:
        # Determine opponent and home/away
        is_home = log.home_team_abbr == team_abbr
        opponent_abbr = log.away_team_abbr if is_home else log.home_team_abbr

        # Get team stats
        user_stats = log.home_stats if is_home else log.away_stats
        user_score = log.home_score if is_home else log.away_score
        opp_score = log.away_score if is_home else log.home_score

        # Try to get opponent name
        opponent_team = league.get_team(opponent_abbr) if league else None
        opponent_name = opponent_team.name if opponent_team else opponent_abbr

        summaries.append(
            GameLogSummaryResponse(
                game_id=str(log.game_id),
                week=log.week,
                opponent_abbr=opponent_abbr,
                opponent_name=opponent_name,
                is_home=is_home,
                user_score=user_score,
                opponent_score=opp_score,
                won=user_score > opp_score,
                passing_yards=user_stats.passing_yards,
                rushing_yards=user_stats.rushing_yards,
            )
        )

    return GameLogsListResponse(games=summaries, total=len(league.get_team_game_logs(team_abbr)))


@router.get(
    "/franchise/{franchise_id}/stats/games/{game_id}",
    response_model=GameLogDetailResponse,
)
async def get_game_log_detail(
    franchise_id: UUID,
    game_id: UUID,
) -> GameLogDetailResponse:
    """
    Get detailed game log with all player stats.

    Returns full box score including individual player statistics.
    """
    session = get_session_with_team(franchise_id)
    league = session.service.league

    game_log = league.get_game_log(game_id)
    if not game_log:
        raise HTTPException(status_code=404, detail="Game log not found")

    # Convert player stats to response format
    player_stats = []
    for player_id, stats in game_log.player_stats.items():
        stat_line = PlayerStatLineResponse(
            player_id=player_id,
            player_name=stats.player_name,
            position=stats.position,
            team_abbr=stats.team_abbr,
        )

        # Include non-empty stat categories
        if stats.passing.attempts > 0:
            stat_line.passing = stats.passing.to_dict()
        if stats.rushing.attempts > 0:
            stat_line.rushing = stats.rushing.to_dict()
        if stats.receiving.targets > 0:
            stat_line.receiving = stats.receiving.to_dict()
        if stats.defense.tackles > 0 or stats.defense.sacks > 0:
            stat_line.defense = stats.defense.to_dict()

        player_stats.append(stat_line)

    # Sort player stats: offense first (by yards), then defense (by tackles)
    def sort_key(p: PlayerStatLineResponse) -> tuple:
        total_yards = 0
        if p.passing:
            total_yards += p.passing.get("yards", 0)
        if p.rushing:
            total_yards += p.rushing.get("yards", 0)
        if p.receiving:
            total_yards += p.receiving.get("yards", 0)
        tackles = p.defense.get("tackles", 0) if p.defense else 0
        return (-total_yards, -tackles)

    player_stats.sort(key=sort_key)

    return GameLogDetailResponse(
        game_id=str(game_log.game_id),
        week=game_log.week,
        home_team=game_log.home_team_abbr,
        away_team=game_log.away_team_abbr,
        home_score=game_log.home_score,
        away_score=game_log.away_score,
        home_stats=game_log.home_stats.to_dict(),
        away_stats=game_log.away_stats.to_dict(),
        player_stats=player_stats,
    )


@router.get(
    "/franchise/{franchise_id}/stats/players/{player_id}",
    response_model=PlayerSeasonStatsResponse,
)
async def get_player_season_stats(
    franchise_id: UUID,
    player_id: UUID,
) -> PlayerSeasonStatsResponse:
    """
    Get season stats for a specific player.

    Returns accumulated statistics across all games played this season.
    """
    session = get_session_with_team(franchise_id)
    league = session.service.league

    stats = league.get_player_season_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Player stats not found")

    response = PlayerSeasonStatsResponse(
        player_id=str(stats.player_id),
        player_name=stats.player_name,
        team_abbr=stats.team_abbr,
        position=stats.position,
        games_played=stats.games_played,
    )

    # Include non-empty stat categories
    if stats.passing.attempts > 0:
        response.passing = stats.passing.to_dict()
        response.passing["completion_pct"] = round(stats.passing.completion_pct, 1)
        response.passing["passer_rating"] = round(stats.passing.passer_rating, 1)
    if stats.rushing.attempts > 0:
        response.rushing = stats.rushing.to_dict()
        response.rushing["yards_per_carry"] = round(stats.rushing.yards_per_carry, 1)
    if stats.receiving.targets > 0:
        response.receiving = stats.receiving.to_dict()
        response.receiving["yards_per_reception"] = round(stats.receiving.yards_per_reception, 1)
        response.receiving["catch_pct"] = round(stats.receiving.catch_pct, 1)
    if stats.defense.tackles > 0 or stats.defense.sacks > 0:
        response.defense = stats.defense.to_dict()

    return response


@router.get("/franchise/{franchise_id}/stats/leaders", response_model=LeadersResponse)
async def get_stat_leaders(
    franchise_id: UUID,
    category: str = Query(..., description="Stat category: passing, rushing, receiving, defense"),
    stat: str = Query(..., description="Stat name: yards, touchdowns, attempts, etc."),
    limit: int = Query(default=10, ge=1, le=50),
) -> LeadersResponse:
    """
    Get league leaders for a specific statistic.

    Categories: passing, rushing, receiving, defense
    Stats vary by category:
    - passing: yards, touchdowns, attempts, completions, interceptions
    - rushing: yards, touchdowns, attempts
    - receiving: yards, touchdowns, receptions, targets
    - defense: tackles, sacks, interceptions
    """
    session = get_session_with_team(franchise_id)
    league = session.service.league

    # Validate category
    valid_categories = {"passing", "rushing", "receiving", "defense", "kicking"}
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
        )

    # Get leaders using existing league method
    leaders = league.get_season_leaders(category, stat, limit)

    # Convert to response format
    leader_entries = []
    for rank, (player_stats, value) in enumerate(leaders, start=1):
        leader_entries.append(
            LeaderEntryResponse(
                rank=rank,
                player_id=str(player_stats.player_id),
                player_name=player_stats.player_name,
                team_abbr=player_stats.team_abbr,
                position=player_stats.position,
                value=value,
                games_played=player_stats.games_played,
            )
        )

    return LeadersResponse(
        category=category,
        stat=stat,
        leaders=leader_entries,
    )
