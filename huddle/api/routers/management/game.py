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

    # Generate random stats
    def gen_stats(score: int) -> GameStatsResponse:
        """Generate plausible stats based on score."""
        # Higher scores = more yards
        base_passing = 180 + (score * 5) + random.randint(-30, 50)
        base_rushing = 80 + (score * 2) + random.randint(-20, 40)

        return GameStatsResponse(
            passing_yards=max(100, base_passing),
            rushing_yards=max(40, base_rushing),
            total_yards=max(150, base_passing + base_rushing),
            turnovers=random.randint(0, 3),
            time_of_possession=f"{random.randint(25, 35)}:{random.randint(0, 59):02d}",
            third_down_pct=round(random.uniform(30, 55), 1),
            sacks=random.randint(0, 4),
        )

    user_stats = gen_stats(user_score)
    opp_stats = gen_stats(opp_score)

    # Generate MVP (placeholder - pick random position with good stat line)
    mvp_positions = ["QB", "RB", "WR"]
    mvp_pos = random.choice(mvp_positions)
    if mvp_pos == "QB":
        mvp_stat = f"{random.randint(18, 28)}/{random.randint(28, 38)}, {user_stats.passing_yards} yds, {random.randint(1, 4)} TD"
    elif mvp_pos == "RB":
        mvp_stat = f"{random.randint(15, 25)} car, {user_stats.rushing_yards} yds, {random.randint(0, 2)} TD"
    else:
        mvp_stat = (
            f"{random.randint(5, 10)} rec, {random.randint(80, 140)} yds, {random.randint(0, 2)} TD"
        )

    mvp = (
        {
            "player_id": None,
            "name": "Player MVP",  # Would be actual player in real implementation
            "position": mvp_pos,
            "stat_line": mvp_stat,
        }
        if won
        else None
    )

    # Update standings in the league
    league = get_active_league()
    if league:
        # Get opponent abbreviation from event payload
        opponent_id = event.payload.get("opponent_id")
        opponent_abbr = None

        # Try to find opponent abbreviation
        if opponent_id:
            opponent_team = league.get_team_by_id(UUID(opponent_id))
            if opponent_team:
                opponent_abbr = opponent_team.abbreviation

        if opponent_abbr:
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
