"""
API Router for Historical Simulation Explorer.

Provides endpoints for:
- Running simulations
- Exploring simulation data
- Viewing teams, rosters, standings
- Browsing transactions and drafts
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from huddle.api.schemas.history import (
    SimulationConfig,
    SimulationSummary,
    TeamSnapshot,
    TeamRoster,
    StandingsData,
    DraftData,
    TransactionLog,
    FullSimulationData,
    # New AI visibility schemas
    CapAllocationData,
    TeamProfile,
    FAStrategyData,
    GMComparisonData,
    # Roster planning schemas
    RosterPlan,
)
from huddle.api.services import history_service

router = APIRouter(prefix="/history", tags=["history"])


@router.post("/simulate", response_model=SimulationSummary)
async def run_simulation(config: SimulationConfig):
    """
    Run a new historical simulation.

    Creates a simulated league history with the specified configuration.
    Returns a simulation ID for retrieving results.
    """
    try:
        summary = history_service.run_simulation(config)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/simulate-stream")
async def run_simulation_stream(
    num_teams: int = Query(default=32, ge=4, le=32),
    years_to_simulate: int = Query(default=3, ge=1, le=10),
    start_year: int = Query(default=2021),
):
    """
    Run simulation with streaming progress updates (SSE).

    Returns Server-Sent Events with progress messages.
    Final event contains the simulation summary.
    """
    import queue
    import threading

    progress_queue: queue.Queue[str] = queue.Queue()

    def progress_callback(message: str):
        progress_queue.put(message)

    config = SimulationConfig(
        num_teams=num_teams,
        years_to_simulate=years_to_simulate,
        start_year=start_year,
    )

    # Run simulation in background thread
    result_holder: dict = {}

    def run_sim():
        try:
            summary = history_service.run_simulation_with_progress(config, progress_callback)
            result_holder["summary"] = summary
            result_holder["success"] = True
        except Exception as e:
            result_holder["error"] = str(e)
            result_holder["success"] = False
        finally:
            progress_queue.put("__DONE__")

    thread = threading.Thread(target=run_sim)
    thread.start()

    async def event_generator():
        while True:
            try:
                # Check for progress messages
                message = progress_queue.get(timeout=0.1)
                if message == "__DONE__":
                    if result_holder.get("success"):
                        summary = result_holder["summary"]
                        yield f"data: {json.dumps({'type': 'complete', 'summary': summary.model_dump(mode='json')})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': result_holder.get('error', 'Unknown error')})}\n\n"
                    break
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'message': message})}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/simulations", response_model=list[SimulationSummary])
async def list_simulations():
    """List all available simulations."""
    return history_service.list_simulations()


@router.get("/simulations/{sim_id}", response_model=FullSimulationData)
async def get_simulation(sim_id: str):
    """Get full simulation data."""
    result = history_service.get_simulation(sim_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.delete("/simulations/{sim_id}")
async def delete_simulation(sim_id: str):
    """Delete a simulation from memory."""
    success = history_service.delete_simulation(sim_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"status": "deleted", "sim_id": sim_id}


@router.get("/simulations/{sim_id}/seasons/{season}/teams", response_model=list[TeamSnapshot])
async def get_teams_in_season(sim_id: str, season: int):
    """Get all teams for a specific season."""
    result = history_service.get_teams_in_season(sim_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/simulations/{sim_id}/seasons/{season}/standings", response_model=StandingsData)
async def get_standings(sim_id: str, season: int):
    """Get standings for a specific season."""
    result = history_service.get_standings(sim_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/simulations/{sim_id}/seasons/{season}/draft", response_model=DraftData)
async def get_draft(sim_id: str, season: int):
    """Get draft results for a specific season."""
    result = history_service.get_draft(sim_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/simulations/{sim_id}/transactions", response_model=TransactionLog)
async def get_transactions(
    sim_id: str,
    season: Optional[int] = Query(None, description="Filter by season"),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by type (DRAFT, SIGNING, CUT, TRADE)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get transactions with optional filters."""
    result = history_service.get_transactions(
        sim_id, season, team_id, transaction_type, limit, offset
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/simulations/{sim_id}/teams/{team_id}/roster", response_model=TeamRoster)
async def get_team_roster(sim_id: str, team_id: str, season: int = Query(..., description="Season year")):
    """Get full roster for a team in a specific season."""
    result = history_service.get_team_roster(sim_id, team_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation or team not found")
    return result


# =============================================================================
# New AI Visibility Endpoints
# =============================================================================


@router.get("/simulations/{sim_id}/teams/{team_id}/profile", response_model=TeamProfile)
async def get_team_profile(
    sim_id: str,
    team_id: str,
    season: int = Query(..., description="Season year")
):
    """
    Get team profile showing AI personality and strategy.

    Returns GM archetype, position preferences, draft philosophy, and spending style.
    """
    result = history_service.get_team_profile(sim_id, team_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation or team not found")
    return result


@router.get("/simulations/{sim_id}/teams/{team_id}/allocation", response_model=CapAllocationData)
async def get_team_allocation(
    sim_id: str,
    team_id: str,
    season: int = Query(..., description="Season year")
):
    """
    Get cap allocation analysis for a team.

    Shows actual cap spending by position vs research-backed optimal allocation.
    Positive gap = under-invested, negative gap = over-invested.
    """
    result = history_service.get_team_cap_allocation(sim_id, team_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation or team not found")
    return result


@router.get("/simulations/{sim_id}/teams/{team_id}/fa-strategy", response_model=FAStrategyData)
async def get_team_fa_strategy(
    sim_id: str,
    team_id: str,
    season: int = Query(..., description="Season year")
):
    """
    Get FA strategy comparison: plan vs results.

    Shows which positions research recommended targeting in FA,
    who was actually signed, and how well the plan was executed.
    """
    result = history_service.get_team_fa_strategy(sim_id, team_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation or team not found")
    return result


@router.get("/simulations/{sim_id}/seasons/{season}/gm-comparison", response_model=GMComparisonData)
async def get_gm_comparison(sim_id: str, season: int):
    """
    Compare performance across GM archetypes.

    Shows average wins, playoff appearances, and championships by GM type.
    Useful for seeing which strategies worked best in the simulation.
    """
    result = history_service.get_gm_comparison(sim_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/simulations/{sim_id}/teams/{team_id}/roster-plan", response_model=RosterPlan)
async def get_roster_plan(
    sim_id: str,
    team_id: str,
    season: int = Query(..., description="Season year")
):
    """
    Get position-by-position roster plan for a team.

    Shows for each position:
    - Current starter and their stats
    - FA options with probability weights
    - Draft options with probability weights
    - Option to keep current player

    This helps visualize how the AI team is thinking about roster construction.
    """
    result = history_service.get_roster_plan(sim_id, team_id, season)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation or team not found")
    return result
