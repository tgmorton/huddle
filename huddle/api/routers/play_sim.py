"""REST API router for play simulation (QB + receivers + ball)."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from huddle.simulation.sandbox.play_sim import (
    PlaySimulator,
    QBAttributes,
)
from huddle.simulation.sandbox.team_route_sim import (
    Formation,
    CoverageScheme,
    RouteConcept,
)

router = APIRouter(prefix="/play-sim", tags=["play-sim"])

# Store active simulators
_simulators: dict[str, PlaySimulator] = {}
_session_counter = 0


class QBAttributesRequest(BaseModel):
    """QB attributes for simulation."""
    arm_strength: int = Field(default=85, ge=1, le=99)
    accuracy: int = Field(default=85, ge=1, le=99)
    decision_making: int = Field(default=80, ge=1, le=99)
    pocket_awareness: int = Field(default=75, ge=1, le=99)


class CreatePlaySimRequest(BaseModel):
    """Request to create a play simulation."""
    formation: str = Field(default="spread")
    coverage: str = Field(default="cover_3")
    concept: str = Field(default="four_verts")
    variance_enabled: bool = Field(default=True)
    qb_attributes: Optional[QBAttributesRequest] = None


class PlaySimResponse(BaseModel):
    """Response with play simulation state."""
    session_id: str
    state: dict


# Mapping strings to enums
FORMATION_MAP = {
    "trips_right": Formation.TRIPS_RIGHT,
    "trips_left": Formation.TRIPS_LEFT,
    "spread": Formation.SPREAD,
    "empty": Formation.EMPTY,
    "doubles": Formation.DOUBLES,
}

COVERAGE_MAP = {
    "cover_0": CoverageScheme.COVER_0,
    "cover_1": CoverageScheme.COVER_1,
    "cover_2": CoverageScheme.COVER_2,
    "cover_3": CoverageScheme.COVER_3,
    "cover_4": CoverageScheme.COVER_4,
    "cover_2_man": CoverageScheme.COVER_2_MAN,
}

CONCEPT_MAP = {
    "four_verts": RouteConcept.FOUR_VERTS,
    "mesh": RouteConcept.MESH,
    "smash": RouteConcept.SMASH,
    "flood": RouteConcept.FLOOD,
    "levels": RouteConcept.LEVELS,
    "slants": RouteConcept.SLANTS,
    "curls": RouteConcept.CURLS,
    "custom": RouteConcept.CUSTOM,
}


@router.post("/sessions", response_model=PlaySimResponse)
async def create_play_sim_session(request: Optional[CreatePlaySimRequest] = None) -> PlaySimResponse:
    """Create a new play simulation session."""
    global _session_counter
    _session_counter += 1
    session_id = f"play-sim-{_session_counter}"

    if request is None:
        request = CreatePlaySimRequest()

    # Parse enums
    formation = FORMATION_MAP.get(request.formation, Formation.SPREAD)
    coverage = COVERAGE_MAP.get(request.coverage, CoverageScheme.COVER_3)
    concept = CONCEPT_MAP.get(request.concept, RouteConcept.FOUR_VERTS)

    # Parse QB attributes
    qb_attrs = None
    if request.qb_attributes:
        qb_attrs = QBAttributes(
            arm_strength=request.qb_attributes.arm_strength,
            accuracy=request.qb_attributes.accuracy,
            decision_making=request.qb_attributes.decision_making,
            pocket_awareness=request.qb_attributes.pocket_awareness,
        )

    # Create simulator
    sim = PlaySimulator(
        formation=formation,
        coverage=coverage,
        concept=concept,
        variance_enabled=request.variance_enabled,
        qb_attributes=qb_attrs,
    )
    sim.setup()

    _simulators[session_id] = sim

    return PlaySimResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.get("/sessions/{session_id}", response_model=PlaySimResponse)
async def get_play_sim_session(session_id: str) -> PlaySimResponse:
    """Get current play simulation state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return PlaySimResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.delete("/sessions/{session_id}")
async def delete_play_sim_session(session_id: str) -> dict:
    """Delete a play simulation session."""
    if session_id in _simulators:
        del _simulators[session_id]
    return {"deleted": True}


@router.post("/sessions/{session_id}/reset", response_model=PlaySimResponse)
async def reset_play_sim_session(session_id: str) -> PlaySimResponse:
    """Reset play simulation to initial state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sim.reset()

    return PlaySimResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.post("/sessions/{session_id}/run-sync")
async def run_play_sim_sync(session_id: str) -> list[dict]:
    """Run the full simulation and return all states."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reset first
    sim.reset()

    # Run and return all states
    return sim.run_full()


@router.get("/options")
async def get_options() -> dict:
    """Get available formations, coverages, and concepts."""
    return {
        "formations": list(FORMATION_MAP.keys()),
        "coverages": list(COVERAGE_MAP.keys()),
        "concepts": list(CONCEPT_MAP.keys()),
    }
