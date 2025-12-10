"""REST API router for route/coverage simulation."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from huddle.simulation.sandbox.route_sim import (
    RouteSimulator,
    RouteType,
    CoverageType,
    ReceiverAttributes,
    DBAttributes,
)

router = APIRouter(prefix="/routes", tags=["routes"])

# Store active simulators (simple in-memory for now)
_simulators: dict[str, RouteSimulator] = {}
_session_counter = 0


class WRAttributesRequest(BaseModel):
    """WR attributes in request."""
    speed: int = Field(default=85, ge=40, le=99)
    acceleration: int = Field(default=85, ge=40, le=99)
    route_running: int = Field(default=85, ge=40, le=99)
    release: int = Field(default=80, ge=40, le=99)


class DBAttributesRequest(BaseModel):
    """DB attributes in request."""
    speed: int = Field(default=88, ge=40, le=99)
    acceleration: int = Field(default=86, ge=40, le=99)
    man_coverage: int = Field(default=85, ge=40, le=99)
    zone_coverage: int = Field(default=80, ge=40, le=99)
    play_recognition: int = Field(default=75, ge=40, le=99)
    press: int = Field(default=80, ge=40, le=99)


class CreateRouteRequest(BaseModel):
    """Request to create a route simulation."""
    route_type: str = Field(default="out")
    coverage_type: str = Field(default="man_off")
    wr_attributes: Optional[WRAttributesRequest] = None
    db_attributes: Optional[DBAttributesRequest] = None


class RouteResponse(BaseModel):
    """Response with route simulation state."""
    session_id: str
    state: dict


@router.post("/sessions", response_model=RouteResponse)
async def create_route_session(request: Optional[CreateRouteRequest] = None) -> RouteResponse:
    """Create a new route simulation session."""
    global _session_counter
    _session_counter += 1
    session_id = f"route-{_session_counter}"

    # Parse request
    if request is None:
        request = CreateRouteRequest()

    # Parse route type
    route_map = {
        "flat": RouteType.FLAT,
        "slant": RouteType.SLANT,
        "comeback": RouteType.COMEBACK,
        "curl": RouteType.CURL,
        "out": RouteType.OUT,
        "in": RouteType.IN,
        "corner": RouteType.CORNER,
        "post": RouteType.POST,
        "go": RouteType.GO,
        "hitch": RouteType.HITCH,
    }
    route_type = route_map.get(request.route_type, RouteType.OUT)

    # Parse coverage type
    coverage_map = {
        "man_press": CoverageType.MAN_PRESS,
        "man_off": CoverageType.MAN_OFF,
        "zone_flat": CoverageType.ZONE_FLAT,
        "zone_deep": CoverageType.ZONE_DEEP,
    }
    coverage_type = coverage_map.get(request.coverage_type, CoverageType.MAN_OFF)

    # Parse attributes
    wr_attrs = None
    if request.wr_attributes:
        wr_attrs = ReceiverAttributes(
            speed=request.wr_attributes.speed,
            acceleration=request.wr_attributes.acceleration,
            route_running=request.wr_attributes.route_running,
            release=request.wr_attributes.release,
        )

    db_attrs = None
    if request.db_attributes:
        db_attrs = DBAttributes(
            speed=request.db_attributes.speed,
            acceleration=request.db_attributes.acceleration,
            man_coverage=request.db_attributes.man_coverage,
            zone_coverage=request.db_attributes.zone_coverage,
            play_recognition=request.db_attributes.play_recognition,
            press=request.db_attributes.press,
        )

    # Create simulator
    sim = RouteSimulator(
        route_type=route_type,
        coverage_type=coverage_type,
        wr_attributes=wr_attrs,
        db_attributes=db_attrs,
    )
    sim.setup()

    _simulators[session_id] = sim

    return RouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.get("/sessions/{session_id}", response_model=RouteResponse)
async def get_route_session(session_id: str) -> RouteResponse:
    """Get current route simulation state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return RouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.delete("/sessions/{session_id}")
async def delete_route_session(session_id: str) -> dict:
    """Delete a route simulation session."""
    if session_id in _simulators:
        del _simulators[session_id]
    return {"deleted": True}


@router.post("/sessions/{session_id}/reset", response_model=RouteResponse)
async def reset_route_session(session_id: str) -> RouteResponse:
    """Reset route simulation to initial state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sim.reset()

    return RouteResponse(
        session_id=session_id,
        state=sim.state.to_dict(),
    )


@router.post("/sessions/{session_id}/run-sync")
async def run_route_sync(session_id: str) -> list[dict]:
    """Run the full simulation and return all states."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reset first
    sim.reset()

    # Run and return all states
    return sim.run_full()
