"""REST API router for pocket simulation."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from huddle.simulation.sandbox.pocket_sim import (
    PocketSimulator,
    DefensiveFront,
    create_man_protection,
    create_slide_protection,
    create_double_team_scheme,
    create_et_stunt,
    create_te_stunt,
    create_tt_twist,
)

router = APIRouter(prefix="/pocket", tags=["pocket"])

# Store active simulators (simple in-memory for now)
_simulators: dict[str, PocketSimulator] = {}
_session_counter = 0


class CreatePocketRequest(BaseModel):
    """Request to create a pocket simulation."""
    qb_depth: float = Field(default=7.0, ge=3.0, le=12.0)
    defensive_front: str = Field(default="4_man")  # "3_man", "4_man", "5_man"
    blocking_scheme: str = Field(default="man")    # "man", "slide_left", "slide_right", "double"
    stunt: str = Field(default="none")             # "none", "et_left", "et_right", "te_left", "te_right", "tt_twist"


class PocketResponse(BaseModel):
    """Response with pocket state."""
    session_id: str
    state: dict


@router.post("/sessions", response_model=PocketResponse)
async def create_pocket_session(request: Optional[CreatePocketRequest] = None) -> PocketResponse:
    """Create a new pocket simulation session."""
    global _session_counter
    _session_counter += 1
    session_id = f"pocket-{_session_counter}"

    # Parse request
    qb_depth = request.qb_depth if request else 7.0

    # Parse defensive front
    front_map = {
        "3_man": DefensiveFront.THREE_MAN,
        "4_man": DefensiveFront.FOUR_MAN,
        "5_man": DefensiveFront.FIVE_MAN,
    }
    front = front_map.get(request.defensive_front if request else "4_man", DefensiveFront.FOUR_MAN)

    # Parse blocking scheme
    scheme = None
    if request:
        if request.blocking_scheme == "slide_left":
            scheme = create_slide_protection(slide_left=True)
        elif request.blocking_scheme == "slide_right":
            scheme = create_slide_protection(slide_left=False)
        elif request.blocking_scheme == "double":
            scheme = create_double_team_scheme(front)
        else:
            scheme = create_man_protection(front)

    # Parse stunt (only works with 4-man front)
    stunt = None
    if request and front == DefensiveFront.FOUR_MAN:
        stunt_type = request.stunt
        if stunt_type == "et_left":
            stunt = create_et_stunt("left")
        elif stunt_type == "et_right":
            stunt = create_et_stunt("right")
        elif stunt_type == "te_left":
            stunt = create_te_stunt("left")
        elif stunt_type == "te_right":
            stunt = create_te_stunt("right")
        elif stunt_type == "tt_twist":
            stunt = create_tt_twist()

    sim = PocketSimulator(
        qb_depth=qb_depth,
        defensive_front=front,
        blocking_scheme=scheme,
        stunt=stunt,
    )
    sim.setup()

    _simulators[session_id] = sim

    return PocketResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.get("/sessions/{session_id}", response_model=PocketResponse)
async def get_pocket_session(session_id: str) -> PocketResponse:
    """Get current pocket simulation state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return PocketResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.delete("/sessions/{session_id}")
async def delete_pocket_session(session_id: str) -> dict:
    """Delete a pocket simulation session."""
    if session_id in _simulators:
        del _simulators[session_id]
    return {"deleted": True}


@router.post("/sessions/{session_id}/reset", response_model=PocketResponse)
async def reset_pocket_session(session_id: str) -> PocketResponse:
    """Reset pocket simulation to initial state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sim.reset()

    return PocketResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.post("/sessions/{session_id}/run-sync")
async def run_pocket_sync(session_id: str) -> list[dict]:
    """Run the full simulation and return all states."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reset first
    sim.reset()

    # Run and return all states
    return sim.run_full()
