"""
Game simulation router.

Handles game day simulation endpoints.
"""

import random
from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.api.schemas.management import (
    SimGameRequest,
    GameResultResponse,
    GameStatsResponse,
)
from huddle.api.routers.admin import get_active_league
from huddle.core.stats import CorrelatedStatsGenerator, GameContext, select_mvp
from .deps import get_session

router = APIRouter(tags=["game"])


@router.post("/franchise/{franchise_id}/sim-game", response_model=GameResultResponse)
async def sim_game(franchise_id: UUID, request: SimGameRequest) -> GameResultResponse:
    """
    Simulate a game and get the result.

    Takes the game event ID, simulates the game using a simple model,
    updates standings, adds journal entry, and returns the result.
    """
    session = get_session(franchise_id)

    # Get the event
    event = session.service.state.events.get(request.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Game event not found")

    if event.event_type != "game_day":
        raise HTTPException(status_code=400, detail="Event is not a game day event")

    # Get game info from event payload
    opponent_name = event.payload.get("opponent_name", "Opponent")
    is_home = event.payload.get("is_home", True)
    week = event.payload.get("week", 1)

    # Get team info
    user_team = session.team
    user_team_name = user_team.abbreviation if user_team else "USER"

    # Simulate game with simple random model
    # Base scores influenced by slight randomness
    user_base = random.randint(14, 35)
    opp_base = random.randint(10, 31)

    # Home field advantage
    if is_home:
        user_base += random.randint(0, 7)
    else:
        opp_base += random.randint(0, 7)

    # Final scores
    home_score = user_base if is_home else opp_base
    away_score = opp_base if is_home else user_base
    user_score = user_base
    opp_score = opp_base
    won = user_score > opp_score

    # Get league and opponent team for stats generation
    league = get_active_league()
    opponent_id = event.payload.get("opponent_id")
    opponent_team = None
    opponent_abbr = None

    if league and opponent_id:
        opponent_team = league.get_team_by_id(UUID(opponent_id))
        if opponent_team:
            opponent_abbr = opponent_team.abbreviation

    # Generate correlated stats using the stats generator
    generator = CorrelatedStatsGenerator()

    # Determine home/away teams
    home_team_obj = user_team if is_home else opponent_team
    away_team_obj = opponent_team if is_home else user_team

    ctx = GameContext(
        week=week,
        home_team=home_team_obj,
        away_team=away_team_obj,
        home_score=home_score,
        away_score=away_score,
    )
    game_log = generator.generate(ctx)

    # Store the game log on the league (auto-aggregates season stats)
    if league:
        league.add_game_log(game_log)

    # Extract team stats for response
    user_team_stats = game_log.home_stats if is_home else game_log.away_stats
    opp_team_stats = game_log.away_stats if is_home else game_log.home_stats

    user_stats = GameStatsResponse(
        passing_yards=user_team_stats.passing_yards,
        rushing_yards=user_team_stats.rushing_yards,
        total_yards=user_team_stats.total_yards,
        turnovers=user_team_stats.turnovers,
        time_of_possession=user_team_stats.time_of_possession_display,
        third_down_pct=round(user_team_stats.third_down_pct, 1),
        sacks=0,  # Sacks taken stored on player stats
    )
    opp_stats = GameStatsResponse(
        passing_yards=opp_team_stats.passing_yards,
        rushing_yards=opp_team_stats.rushing_yards,
        total_yards=opp_team_stats.total_yards,
        turnovers=opp_team_stats.turnovers,
        time_of_possession=opp_team_stats.time_of_possession_display,
        third_down_pct=round(opp_team_stats.third_down_pct, 1),
        sacks=0,
    )

    # Select MVP from actual player stats
    mvp = select_mvp(game_log, user_team_name if won else None)

    # Update standings in the league
    if league and opponent_abbr:
        # Find and update the scheduled game
        for game in league.schedule:
            if game.week == week and not game.is_played:
                # Check if this is the right game (user team vs opponent)
                game_teams = {game.home_team_abbr, game.away_team_abbr}
                if user_team_name in game_teams and opponent_abbr in game_teams:
                    # Update the game with scores
                    game.home_score = home_score
                    game.away_score = away_score
                    # Update standings
                    league.update_standings_from_game(game)
                    break

    # Mark event as attended
    event.complete()

    # Add journal entry
    result_title = "Victory" if won else "Defeat"
    location = "vs" if is_home else "@"
    session.service.add_journal_entry(
        category="transaction",
        title=result_title,
        effect=f"{user_score}-{opp_score} {location} {opponent_name}",
        detail=f"Week {week}",
    )

    # Return result
    home_team = user_team_name if is_home else opponent_name
    away_team = opponent_name if is_home else user_team_name

    return GameResultResponse(
        success=True,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        won=won,
        is_home=is_home,
        week=week,
        user_stats=user_stats,
        opponent_stats=opp_stats,
        mvp=mvp,
    )
