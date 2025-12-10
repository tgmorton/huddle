"""REST API router for integrated simulation (pocket + play combined)."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from huddle.simulation.sandbox.integrated_sim import (
    IntegratedSimulator,
    IntegratedSimContext,
)
from huddle.simulation.sandbox.play_sim import QBAttributes
from huddle.simulation.sandbox.team_route_sim import (
    Formation,
    CoverageScheme,
    RouteConcept,
)
from huddle.simulation.sandbox.pocket_sim import DefensiveFront, DropbackType
from huddle.simulation.sandbox.shared import FieldContext, HashPosition

router = APIRouter(prefix="/integrated-sim", tags=["integrated-sim"])

# Store active simulators
_simulators: dict[str, IntegratedSimulator] = {}
_session_counter = 0


class QBAttributesRequest(BaseModel):
    """QB attributes for simulation."""
    arm_strength: int = Field(default=85, ge=1, le=99)
    accuracy: int = Field(default=85, ge=1, le=99)
    decision_making: int = Field(default=80, ge=1, le=99)
    pocket_awareness: int = Field(default=75, ge=1, le=99)
    mobility: int = Field(default=75, ge=1, le=99)


class CreateIntegratedSimRequest(BaseModel):
    """Request to create an integrated simulation."""
    # Offense
    formation: str = Field(default="spread")
    concept: str = Field(default="smash")
    dropback_type: str = Field(default="shotgun")  # 3_step, 5_step, 7_step, shotgun

    # Defense
    coverage: str = Field(default="cover_3")
    defensive_front: str = Field(default="4_man")

    # Field position
    yard_line: int = Field(default=25, ge=1, le=99)
    hash_position: str = Field(default="middle")

    # Options
    variance_enabled: bool = Field(default=True)
    qb_attributes: Optional[QBAttributesRequest] = None


class IntegratedSimResponse(BaseModel):
    """Response with integrated simulation state."""
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
}

CONCEPT_MAP = {
    "four_verts": RouteConcept.FOUR_VERTS,
    "mesh": RouteConcept.MESH,
    "smash": RouteConcept.SMASH,
    "flood": RouteConcept.FLOOD,
    "slants": RouteConcept.SLANTS,
}

FRONT_MAP = {
    "3_man": DefensiveFront.THREE_MAN,
    "4_man": DefensiveFront.FOUR_MAN,
    "5_man": DefensiveFront.FIVE_MAN,
}

HASH_MAP = {
    "left": HashPosition.LEFT,
    "middle": HashPosition.MIDDLE,
    "right": HashPosition.RIGHT,
}

DROPBACK_MAP = {
    "3_step": DropbackType.THREE_STEP,
    "5_step": DropbackType.FIVE_STEP,
    "7_step": DropbackType.SEVEN_STEP,
    "shotgun": DropbackType.SHOTGUN,
}


def context_to_dict(context: IntegratedSimContext) -> dict:
    """Convert IntegratedSimContext to a serializable dict."""
    return {
        "tick": context.tick,
        "is_complete": context.is_complete,
        "result": context.result,
        "pressure_state": context.pressure_state.to_dict() if context.pressure_state else None,
        "field_context": context.field_context.to_dict(),
        "target_receiver": context.target_receiver,
        "throw_tick": context.throw_tick,
        "yards_gained": context.yards_gained,
        "pocket_state": context.pocket_state.to_dict() if context.pocket_state else None,
        "play_state": context.play_state.to_dict() if context.play_state else None,
    }


@router.post("/sessions", response_model=IntegratedSimResponse)
async def create_integrated_sim_session(
    request: Optional[CreateIntegratedSimRequest] = None
) -> IntegratedSimResponse:
    """Create a new integrated simulation session."""
    global _session_counter
    _session_counter += 1
    session_id = f"integrated-sim-{_session_counter}"

    if request is None:
        request = CreateIntegratedSimRequest()

    # Parse enums
    formation = FORMATION_MAP.get(request.formation, Formation.SPREAD)
    coverage = COVERAGE_MAP.get(request.coverage, CoverageScheme.COVER_3)
    concept = CONCEPT_MAP.get(request.concept, RouteConcept.SMASH)
    defensive_front = FRONT_MAP.get(request.defensive_front, DefensiveFront.FOUR_MAN)
    hash_position = HASH_MAP.get(request.hash_position, HashPosition.MIDDLE)
    dropback_type = DROPBACK_MAP.get(request.dropback_type, DropbackType.SHOTGUN)

    # Create field context
    field_context = FieldContext.from_yard_line(
        yard_line=request.yard_line,
        hash_position=hash_position,
    )

    # Parse QB attributes
    qb_attrs = None
    if request.qb_attributes:
        qb_attrs = QBAttributes(
            arm_strength=request.qb_attributes.arm_strength,
            accuracy=request.qb_attributes.accuracy,
            decision_making=request.qb_attributes.decision_making,
            pocket_awareness=request.qb_attributes.pocket_awareness,
            mobility=request.qb_attributes.mobility,
        )

    # Create simulator
    sim = IntegratedSimulator(
        formation=formation,
        coverage=coverage,
        concept=concept,
        defensive_front=defensive_front,
        dropback_type=dropback_type,
        qb_attributes=qb_attrs,
        field_context=field_context,
        variance_enabled=request.variance_enabled,
    )
    context = sim.setup()

    _simulators[session_id] = sim

    return IntegratedSimResponse(
        session_id=session_id,
        state=context_to_dict(context),
    )


@router.get("/sessions/{session_id}", response_model=IntegratedSimResponse)
async def get_integrated_sim_session(session_id: str) -> IntegratedSimResponse:
    """Get current integrated simulation state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return IntegratedSimResponse(
        session_id=session_id,
        state=context_to_dict(sim.context),
    )


@router.delete("/sessions/{session_id}")
async def delete_integrated_sim_session(session_id: str) -> dict:
    """Delete an integrated simulation session."""
    if session_id in _simulators:
        del _simulators[session_id]
    return {"deleted": True}


@router.post("/sessions/{session_id}/reset", response_model=IntegratedSimResponse)
async def reset_integrated_sim_session(session_id: str) -> IntegratedSimResponse:
    """Reset integrated simulation to initial state."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    context = sim.setup()  # Re-run setup to reset

    return IntegratedSimResponse(
        session_id=session_id,
        state=context_to_dict(context),
    )


@router.post("/sessions/{session_id}/run-sync")
async def run_integrated_sim_sync(session_id: str) -> list[dict]:
    """Run the full simulation and return all states."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reset first
    sim.setup()

    # Run and collect states
    states = []
    for _ in range(60):  # Max 60 ticks
        context = sim.tick()
        states.append(context_to_dict(context))
        if context.is_complete:
            break

    return states


@router.post("/sessions/{session_id}/tick", response_model=IntegratedSimResponse)
async def tick_integrated_sim_session(session_id: str) -> IntegratedSimResponse:
    """Advance simulation by one tick."""
    sim = _simulators.get(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")

    context = sim.tick()

    return IntegratedSimResponse(
        session_id=session_id,
        state=context_to_dict(context),
    )


@router.get("/options")
async def get_options() -> dict:
    """Get available options for integrated simulation."""
    return {
        "formations": list(FORMATION_MAP.keys()),
        "coverages": list(COVERAGE_MAP.keys()),
        "concepts": list(CONCEPT_MAP.keys()),
        "defensive_fronts": list(FRONT_MAP.keys()),
        "hash_positions": list(HASH_MAP.keys()),
    }
