"""Games API router - REST endpoints for game management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from huddle.api.schemas.game import (
    CreateGameRequest,
    GameResponse,
    GameSettingsUpdate,
    GameStateSchema,
    PlayCallRequest,
    PlayResultSchema,
)
from huddle.api.schemas.team import TeamSummarySchema
from huddle.api.services.session_manager import session_manager
from huddle.core.enums import Formation, PassType, PersonnelPackage, RunType
from huddle.core.models.play import PlayCall
from huddle.generators import generate_team

# Sample NFL teams for random generation
NFL_TEAMS = [
    ("Eagles", "Philadelphia", "PHI", "#004C54", "#A5ACAF"),
    ("Cowboys", "Dallas", "DAL", "#003594", "#869397"),
    ("Giants", "New York", "NYG", "#0B2265", "#A71930"),
    ("Commanders", "Washington", "WAS", "#5A1414", "#FFB612"),
    ("Patriots", "New England", "NE", "#002244", "#C60C30"),
    ("Bills", "Buffalo", "BUF", "#00338D", "#C60C30"),
    ("Dolphins", "Miami", "MIA", "#008E97", "#FC4C02"),
    ("Jets", "New York", "NYJ", "#125740", "#FFFFFF"),
    ("Chiefs", "Kansas City", "KC", "#E31837", "#FFB612"),
    ("Raiders", "Las Vegas", "LV", "#000000", "#A5ACAF"),
    ("Broncos", "Denver", "DEN", "#FB4F14", "#002244"),
    ("Chargers", "Los Angeles", "LAC", "#0080C6", "#FFC20E"),
]

router = APIRouter(prefix="/games", tags=["games"])


def _create_play_call(request: PlayCallRequest) -> PlayCall:
    """Convert PlayCallRequest to PlayCall model."""
    from huddle.core.enums import PlayType as CorePlayType

    play_type = CorePlayType[request.play_type.name]

    if play_type == CorePlayType.RUN:
        run_type = RunType[request.run_type.name] if request.run_type else RunType.INSIDE
        return PlayCall.run(
            run_type=run_type,
            formation=Formation(request.formation.value) if request.formation else None,
            personnel=PersonnelPackage(request.personnel.value) if request.personnel else None,
        )
    elif play_type == CorePlayType.PASS:
        pass_type = PassType[request.pass_type.name] if request.pass_type else PassType.SHORT
        return PlayCall.pass_play(
            pass_type=pass_type,
            formation=Formation(request.formation.value) if request.formation else None,
            personnel=PersonnelPackage(request.personnel.value) if request.personnel else None,
        )
    elif play_type == CorePlayType.PUNT:
        return PlayCall.punt()
    elif play_type == CorePlayType.FIELD_GOAL:
        return PlayCall.field_goal()
    elif play_type == CorePlayType.EXTRA_POINT:
        return PlayCall.extra_point()
    elif play_type == CorePlayType.TWO_POINT:
        return PlayCall.two_point(
            pass_type=PassType[request.pass_type.name] if request.pass_type else None,
            run_type=RunType[request.run_type.name] if request.run_type else None,
        )
    else:
        return PlayCall.run(RunType.INSIDE)


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(request: CreateGameRequest) -> GameResponse:
    """
    Create a new game.

    If team IDs are not provided, generates random teams.
    """
    import random

    # Generate or load teams
    if request.generate_teams or (request.home_team_id is None and request.away_team_id is None):
        # Pick two random teams
        teams = random.sample(NFL_TEAMS, 2)
        home_data = teams[0]
        away_data = teams[1]

        home_team = generate_team(
            name=home_data[0],
            city=home_data[1],
            abbreviation=home_data[2],
            primary_color=home_data[3],
            secondary_color=home_data[4],
            overall_range=(70, 85),
        )
        away_team = generate_team(
            name=away_data[0],
            city=away_data[1],
            abbreviation=away_data[2],
            primary_color=away_data[3],
            secondary_color=away_data[4],
            overall_range=(70, 85),
        )
    else:
        # TODO: Load teams from database
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Loading teams from database not yet implemented",
        )

    # Create game session
    session = session_manager.create_session(
        game_id=None,  # Will be generated
        home_team=home_team,
        away_team=away_team,
    )

    return GameResponse(
        game_state=GameStateSchema.from_model(session.service.game_state),
        home_team=TeamSummarySchema.from_model(home_team),
        away_team=TeamSummarySchema.from_model(away_team),
    )


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: UUID) -> GameResponse:
    """Get current game state."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    return GameResponse(
        game_state=GameStateSchema.from_model(session.service.game_state),
        home_team=TeamSummarySchema.from_model(session.service.home_team),
        away_team=TeamSummarySchema.from_model(session.service.away_team),
    )


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: UUID) -> None:
    """Delete/end a game."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    session_manager.remove_session(game_id)


@router.post("/{game_id}/play", response_model=PlayResultSchema)
async def execute_play(game_id: UUID) -> PlayResultSchema:
    """Execute a single play with AI calls."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if session.service.game_state.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    result = session.service.simulate_single_play()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not execute play",
        )

    return PlayResultSchema.from_model(result)


@router.post("/{game_id}/play-call", response_model=PlayResultSchema)
async def submit_play_call(game_id: UUID, request: PlayCallRequest) -> PlayResultSchema:
    """Submit a manual play call."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if session.service.game_state.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    play_call = _create_play_call(request)
    result = session.service.simulate_with_play_call(play_call)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not execute play call",
        )

    return PlayResultSchema.from_model(result)


@router.post("/{game_id}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_game(game_id: UUID) -> None:
    """Pause game simulation."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    session.service.pause()


@router.post("/{game_id}/resume", status_code=status.HTTP_204_NO_CONTENT)
async def resume_game(game_id: UUID) -> None:
    """Resume game simulation."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    session.service.resume()


@router.post("/{game_id}/step", response_model=PlayResultSchema)
async def step_game(game_id: UUID) -> PlayResultSchema:
    """Advance one play in step mode."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    # For step mode via REST, just execute a single play
    result = session.service.simulate_single_play()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not execute play",
        )

    return PlayResultSchema.from_model(result)


@router.patch("/{game_id}/settings", response_model=GameStateSchema)
async def update_game_settings(game_id: UUID, settings: GameSettingsUpdate) -> GameStateSchema:
    """Update game settings (pacing, mode)."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if settings.pacing:
        session.service.set_pacing(settings.pacing)

    if settings.mode:
        session.service.set_mode(settings.mode)

    return GameStateSchema.from_model(session.service.game_state)


@router.get("/{game_id}/stats/team")
async def get_team_stats(game_id: UUID) -> dict:
    """Get team statistics."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    return session.service.get_team_stats()


@router.get("/{game_id}/stats/players")
async def get_player_stats(game_id: UUID) -> dict:
    """Get player statistics."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    return session.service.get_player_stats()


@router.get("/{game_id}/history")
async def get_play_history(game_id: UUID) -> list[str]:
    """Get play-by-play history."""
    session = session_manager.get_session(game_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    return session.service.get_play_log_entries()
