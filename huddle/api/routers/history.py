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

from uuid import UUID

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
    # Franchise creation schemas
    StartFranchiseResponse,
    PlayerDevelopmentResponse,
)
from huddle.api.services import history_service
from huddle.api.services.management_service import management_session_manager
from huddle.management import SeasonPhase

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


# =============================================================================
# Save/Load Endpoints
# =============================================================================


@router.post("/simulations/{sim_id}/save")
async def save_simulation(sim_id: str):
    """
    Save a simulation to disk.

    Persists the simulation data so it can be loaded later, even after
    server restart.
    """
    success = history_service.save_simulation(sim_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found in memory")
    return {"status": "saved", "sim_id": sim_id}


@router.post("/simulations/{sim_id}/load")
async def load_simulation(sim_id: str):
    """
    Load a saved simulation from disk into memory.

    After loading, the simulation can be queried via other endpoints.
    """
    summary = history_service.load_simulation(sim_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Saved simulation not found")
    return summary


@router.get("/saved-simulations")
async def list_saved_simulations():
    """
    List all saved simulations on disk.

    Returns simulations that have been saved but may not be loaded in memory.
    """
    return history_service.list_saved_simulations()


@router.delete("/saved-simulations/{sim_id}")
async def delete_saved_simulation(sim_id: str):
    """
    Delete a saved simulation from disk.

    Also removes from memory if currently loaded.
    """
    # Remove from memory if present
    history_service.delete_simulation(sim_id)

    # Delete from disk
    success = history_service.delete_saved_simulation(sim_id)
    if not success:
        raise HTTPException(status_code=404, detail="Saved simulation not found")
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


# =============================================================================
# Franchise Creation from Simulation
# =============================================================================


@router.post("/simulations/{sim_id}/start-franchise", response_model=StartFranchiseResponse)
async def start_franchise_from_simulation(
    sim_id: str,
    team_id: str = Query(..., description="Team abbreviation to play as (e.g., KC, NE, DAL)"),
):
    """
    Start a playable franchise from a historical simulation.

    Converts the simulation result to a playable league and creates a franchise
    for the specified team. The franchise can then be used with ManagementV2.

    Flow:
    1. Validates simulation exists and team is valid
    2. Converts SimulationResult to a League object
    3. Sets the league as active
    4. Creates a franchise/management session for the player's team
    5. Returns franchise_id for use with management API

    The converted league includes:
    - All 32 teams with rosters and contracts
    - GM archetype metadata preserved
    - Standings from the final simulated season
    - A fresh schedule and draft class for the new season
    """
    # Import here to avoid circular imports
    from huddle.api.routers.admin import _active_league
    import huddle.api.routers.admin as admin_module

    # Validate simulation exists
    sim_data = history_service.get_simulation_result(sim_id)
    if sim_data is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_result, config = sim_data

    # Validate team exists in simulation
    if team_id not in sim_result.teams:
        available_teams = sorted(sim_result.teams.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Team '{team_id}' not found in simulation. Available: {', '.join(available_teams)}"
        )

    # Convert simulation to playable league
    try:
        league = history_service.convert_simulation_to_league(sim_result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert simulation to league: {str(e)}"
        )

    # Set as active league (same pattern as admin.py)
    admin_module._active_league = league

    # Find the team's UUID
    team = league.get_team(team_id)
    if not team:
        raise HTTPException(
            status_code=400,
            detail=f"Team '{team_id}' not found in converted league"
        )

    # Create franchise/management session
    try:
        session = await management_session_manager.create_session(
            team_id=team.id,
            season_year=league.season,
            start_phase=SeasonPhase.TRAINING_CAMP,
            league=league,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create franchise session: {str(e)}"
        )

    return StartFranchiseResponse(
        franchise_id=str(session.franchise_id),
        team_id=team_id,
        team_name=team.full_name,
        league_id=str(league.id),
        season=league.season,
        message=f"Franchise created for {team.full_name} ({league.season} season)",
    )


@router.get("/simulations/{sim_id}/players/{player_id}/development", response_model=PlayerDevelopmentResponse)
async def get_player_development(
    sim_id: str,
    player_id: str,
):
    """
    Get player development history across simulated seasons.

    Returns the player's career arc showing overall rating progression
    over time. Useful for visualizing player development curves.
    """
    result = history_service.get_player_development_history(sim_id, player_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Player or simulation not found"
        )
    return result
