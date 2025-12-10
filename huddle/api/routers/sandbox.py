"""REST API router for sandbox simulation sessions."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from huddle.api.schemas.sandbox import (
    CreateSessionRequest,
    SessionResponse,
    SetTickRateRequest,
    UpdatePlayerRequest,
)
from huddle.simulation.sandbox import SandboxPlayer, get_session_manager

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


def _player_to_schema(player: SandboxPlayer) -> dict:
    """Convert SandboxPlayer to schema dict."""
    return {
        "id": str(player.id),
        "name": player.name,
        "role": player.role.value,
        "strength": player.strength,
        "speed": player.speed,
        "agility": player.agility,
        "pass_block": player.pass_block,
        "awareness": player.awareness,
        "block_shedding": player.block_shedding,
        "power_moves": player.power_moves,
        "finesse_moves": player.finesse_moves,
    }


def _session_to_response(session) -> SessionResponse:
    """Convert SandboxSession to response schema."""
    state = session.simulator.get_state()
    return SessionResponse(
        session_id=str(session.session_id),
        blocker=_player_to_schema(session.simulator.blocker),
        rusher=_player_to_schema(session.simulator.rusher),
        tick_rate_ms=session.simulator.tick_rate_ms,
        max_ticks=session.simulator.max_ticks,
        qb_zone_depth=session.simulator.qb_zone_depth,
        current_tick=state.current_tick,
        is_running=not state.is_complete,
        is_complete=state.is_complete,
        blocker_position={"x": state.blocker_position.x, "y": state.blocker_position.y},
        rusher_position={"x": state.rusher_position.x, "y": state.rusher_position.y},
        outcome=state.outcome.value,
        stats={
            "rusher_wins_contest": state.rusher_wins_contest,
            "blocker_wins_contest": state.blocker_wins_contest,
            "neutral_contests": state.neutral_contests,
        },
    )


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: Optional[CreateSessionRequest] = None) -> SessionResponse:
    """Create a new sandbox simulation session."""
    manager = get_session_manager()

    blocker = None
    rusher = None
    tick_rate_ms = 100
    max_ticks = 50
    qb_zone_depth = 7.0

    if request:
        if request.blocker:
            blocker = SandboxPlayer.from_dict(request.blocker.model_dump())
        if request.rusher:
            rusher = SandboxPlayer.from_dict(request.rusher.model_dump())
        tick_rate_ms = request.tick_rate_ms
        max_ticks = request.max_ticks
        qb_zone_depth = request.qb_zone_depth

    session = await manager.create_session(
        blocker=blocker,
        rusher=rusher,
        tick_rate_ms=tick_rate_ms,
        max_ticks=max_ticks,
        qb_zone_depth=qb_zone_depth,
    )

    return _session_to_response(session)


@router.get("/sessions", response_model=list[str])
async def list_sessions() -> list[str]:
    """List all active sandbox session IDs."""
    manager = get_session_manager()
    sessions = await manager.list_sessions()
    return [str(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get a sandbox session by ID."""
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await manager.get_session(uuid)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return _session_to_response(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str) -> None:
    """Delete a sandbox session."""
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    deleted = await manager.delete_session(uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )


@router.post("/sessions/{session_id}/reset", response_model=SessionResponse)
async def reset_session(session_id: str) -> SessionResponse:
    """Reset a sandbox session to initial state."""
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    success = await manager.reset_simulation(uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session = await manager.get_session(uuid)
    return _session_to_response(session)


@router.put("/sessions/{session_id}/player", response_model=SessionResponse)
async def update_player(session_id: str, request: UpdatePlayerRequest) -> SessionResponse:
    """Update a player's attributes (only when simulation is not running)."""
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    success = await manager.update_player(uuid, request.player.model_dump(), request.role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or simulation is running",
        )

    session = await manager.get_session(uuid)
    return _session_to_response(session)


@router.put("/sessions/{session_id}/tick-rate", response_model=SessionResponse)
async def set_tick_rate(session_id: str, request: SetTickRateRequest) -> SessionResponse:
    """Set the tick rate (only when simulation is not running)."""
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    success = await manager.set_tick_rate(uuid, request.tick_rate_ms)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or simulation is running",
        )

    session = await manager.get_session(uuid)
    return _session_to_response(session)


@router.post("/sessions/{session_id}/run-sync", response_model=list[dict])
async def run_simulation_sync(session_id: str) -> list[dict]:
    """
    Run the simulation synchronously and return all tick results.

    Useful for testing or non-real-time scenarios.
    """
    manager = get_session_manager()
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await manager.get_session(uuid)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Reset and run full simulation
    session.simulator.reset()
    results = session.simulator.run_full_simulation()

    return [r.to_dict() for r in results]
