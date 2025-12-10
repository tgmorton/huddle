"""REST API router for team route/coverage simulation (multi WR vs multi DB)."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from huddle.simulation.sandbox.team_route_sim import (
    TeamRouteSimulator,
    Formation,
    CoverageScheme,
    RouteConcept,
)

router = APIRouter(prefix="/team-routes", tags=["team-routes"])

# Store active simulators
_simulators: dict[str, TeamRouteSimulator] = {}
_session_counter = 0


class CreateTeamRouteRequest(BaseModel):
    """Request to create a team route simulation."""
    formation: str = Field(default="spread")
    coverage: str = Field(default="cover_3")
    concept: str = Field(default="four_verts")


class TeamRouteResponse(BaseModel):
    """Response with team route simulation state."""
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


@router.post("/sessions", response_model=TeamRouteResponse)
async def create_team_route_session(request: Optional[CreateTeamRouteRequest] = None) -> TeamRouteResponse:
    """Create a new team route simulation session."""
    global _session_counter
    _session_counter += 1
    session_id = f"team-route-{_session_counter}"

    if request is None:
        request = CreateTeamRouteRequest()

    # Parse enums
    formation = FORMATION_MAP.get(request.formation, Formation.SPREAD)
    coverage = COVERAGE_MAP.get(request.coverage, CoverageScheme.COVER_3)
    concept = CONCEPT_MAP.get(request.concept, RouteConcept.FOUR_VERTS)

    # Create simulator
    sim = TeamRouteSimulator(
        formation=formation,
        coverage=coverage,
        concept=concept,
    )
    sim.setup()

    _simulators[session_id] = sim

    return TeamRouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.get("/sessions/{session_id}", response_model=TeamRouteResponse)
async def get_team_route_session(session_id: str) -> TeamRouteResponse:
    """Get current team route simulation state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return TeamRouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.delete("/sessions/{session_id}")
async def delete_team_route_session(session_id: str) -> dict:
    """Delete a team route simulation session."""
    if session_id in _simulators:
        del _simulators[session_id]
    return {"deleted": True}


@router.post("/sessions/{session_id}/reset", response_model=TeamRouteResponse)
async def reset_team_route_session(session_id: str) -> TeamRouteResponse:
    """Reset team route simulation to initial state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sim.reset()

    return TeamRouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.post("/sessions/{session_id}/run-sync")
async def run_team_route_sync(session_id: str) -> list[dict]:
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
