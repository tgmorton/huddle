"""
API router for the arms prototype visualization.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import math

from huddle.simulation.arms_prototype.vec2 import Vec2
from huddle.simulation.arms_prototype.player import Player, PlayerRole
from huddle.simulation.arms_prototype.attributes import PhysicalAttributes
from huddle.simulation.arms_prototype.simulation import (
    Simulation, SimulationConfig, blocker_intent, rusher_intent
)
from huddle.simulation.arms_prototype.multi_player import (
    MultiPlayerSimulation, create_double_team_scenario, create_3v2_scenario
)
from huddle.simulation.arms_prototype.assignments import BlockType

router = APIRouter(prefix="/arms-prototype", tags=["arms-prototype"])

# Available presets
OL_PRESETS = {
    "average_ol": PhysicalAttributes.average_ol,
    "elite_tackle": PhysicalAttributes.elite_tackle,
    "mauler_guard": PhysicalAttributes.mauler_guard,
    "backup_ol": PhysicalAttributes.backup_ol,
}

DL_PRESETS = {
    "average_dt": PhysicalAttributes.average_dt,
    "elite_pass_rusher": PhysicalAttributes.elite_pass_rusher,
    "power_rusher": PhysicalAttributes.power_rusher,
}


class SimulationRequest(BaseModel):
    """Request to run a simulation."""
    # Scenario type: "1v1", "double_team", "3v2"
    scenario: str = "1v1"

    # 1v1 settings
    ol_weight: int = 315
    dl_weight: int = 280
    ol_preset: Optional[str] = None  # e.g., "elite_tackle", "mauler_guard"
    dl_preset: Optional[str] = None  # e.g., "elite_pass_rusher", "power_rusher"

    # Double team settings (2v1)
    post_preset: Optional[str] = None   # Post blocker preset
    drive_preset: Optional[str] = None  # Drive blocker preset

    # 3v2 settings
    dt1_preset: Optional[str] = None    # Left DT preset
    dt2_preset: Optional[str] = None    # Right DT preset
    c_preset: Optional[str] = None      # Center preset
    lg_preset: Optional[str] = None     # Left Guard preset
    rg_preset: Optional[str] = None     # Right Guard preset
    double_team_target: str = "DT1"     # Which DT to double: "DT1" or "DT2"

    max_ticks: int = 200


class BatchTestRequest(BaseModel):
    """Request to run batch tests."""
    num_tests: int = 20
    ol_weight: int = 315
    dl_weight: int = 280


class SimulationResponse(BaseModel):
    """Response with all simulation frames."""
    frames: List[Dict[str, Any]]
    result: Dict[str, Any]


class BatchTestResponse(BaseModel):
    """Response with batch test results."""
    rusher_wins: int
    blocker_wins: int
    total_tests: int
    avg_time: float
    results: List[Dict[str, Any]]


def get_preset_attrs(preset_name: Optional[str], preset_dict: dict) -> Optional[PhysicalAttributes]:
    """Get attributes from a preset name."""
    if preset_name and preset_name in preset_dict:
        return preset_dict[preset_name]()
    return None


def get_multi_player_frame_data(sim: MultiPlayerSimulation) -> Dict[str, Any]:
    """Get frame data including assignment info for multi-player simulations."""
    frame = sim.get_frame_data()

    # Add assignment data
    assignments = {}
    double_teams = {}

    for blocker_id, assignment in sim.assignments.assignments.items():
        assignments[blocker_id] = {
            "target_id": assignment.target_id,
            "block_type": assignment.block_type.value,
            "partner_id": assignment.partner_id,
        }

    for dl_id, dt in sim.assignments.double_teams.items():
        double_teams[dl_id] = {
            "post_blocker_id": dt.post_blocker_id,
            "drive_blocker_id": dt.drive_blocker_id,
            "active": dt.active,
            "ticks_active": dt.ticks_active,
            "drive_direction": dt.drive_direction,
        }

    frame["assignments"] = assignments
    frame["double_teams"] = double_teams
    frame["shed_players"] = list(sim.state.shed_players.keys())

    return frame


def run_simulation(
    ol_weight: int = 315,
    dl_weight: int = 280,
    ol_preset: Optional[str] = None,
    dl_preset: Optional[str] = None,
    max_ticks: int = 200
) -> Dict[str, Any]:
    """Run a single 1v1 simulation and return all frames."""
    config = SimulationConfig(
        dt=0.05,
        max_ticks=max_ticks,
        target_position=Vec2(0, -5),
    )

    sim = Simulation(config)

    # Get attributes from presets if provided
    ol_attrs = OL_PRESETS.get(ol_preset, PhysicalAttributes.average_ol)() if ol_preset else None
    dl_attrs = DL_PRESETS.get(dl_preset, PhysicalAttributes.average_dt)() if dl_preset else None

    # Create players
    ol = Player.create_lineman(
        id="OL",
        role=PlayerRole.BLOCKER,
        position=Vec2(0, 0),
        facing=math.pi / 2,  # Facing upfield (+y)
        weight=ol_weight,
        attributes=ol_attrs,
    )

    dl = Player.create_lineman(
        id="DL",
        role=PlayerRole.RUSHER,
        position=Vec2(0, 2),
        facing=-math.pi / 2,  # Facing downfield (-y)
        weight=dl_weight,
        attributes=dl_attrs,
    )

    sim.add_player(ol)
    sim.add_player(dl)

    sim.set_intent("OL", blocker_intent)
    sim.set_intent("DL", rusher_intent)

    # Run simulation and collect frames
    frames = []

    while True:
        frame = sim.get_frame_data()
        frames.append(frame)

        if not sim.tick():
            break

    result = {
        "ticks": sim.state.tick,
        "time": sim.state.time,
        "rusher_won": sim.state.rusher_reached_target,
        "blocker_held": sim.state.blocker_held,
    }

    return {"frames": frames, "result": result}


def run_double_team_simulation(
    dl_preset: Optional[str] = None,
    post_preset: Optional[str] = None,
    drive_preset: Optional[str] = None,
    max_ticks: int = 200
) -> Dict[str, Any]:
    """Run a 2v1 double team simulation."""
    dl_attrs = get_preset_attrs(dl_preset, DL_PRESETS) or PhysicalAttributes.average_dt()
    post_attrs = get_preset_attrs(post_preset, OL_PRESETS) or PhysicalAttributes.average_ol()
    drive_attrs = get_preset_attrs(drive_preset, OL_PRESETS) or PhysicalAttributes.average_ol()

    sim = create_double_team_scenario(
        dl_attrs=dl_attrs,
        post_attrs=post_attrs,
        drive_attrs=drive_attrs,
        pocket_time=max_ticks * 0.05,
    )

    frames = []
    while True:
        frame = get_multi_player_frame_data(sim)
        frames.append(frame)

        if not sim.tick():
            break

    result = {
        "ticks": sim.state.tick,
        "time": sim.state.time,
        "rusher_won": sim.state.rusher_reached_target,
        "blocker_held": sim.state.blocker_held,
        "scenario": "double_team",
    }

    return {"frames": frames, "result": result}


def run_3v2_simulation(
    dt1_preset: Optional[str] = None,
    dt2_preset: Optional[str] = None,
    c_preset: Optional[str] = None,
    lg_preset: Optional[str] = None,
    rg_preset: Optional[str] = None,
    double_team_target: str = "DT1",
    max_ticks: int = 200
) -> Dict[str, Any]:
    """Run a 3v2 interior line simulation."""
    dt1_attrs = get_preset_attrs(dt1_preset, DL_PRESETS) or PhysicalAttributes.average_dt()
    dt2_attrs = get_preset_attrs(dt2_preset, DL_PRESETS) or PhysicalAttributes.average_dt()
    c_attrs = get_preset_attrs(c_preset, OL_PRESETS) or PhysicalAttributes.average_ol()
    lg_attrs = get_preset_attrs(lg_preset, OL_PRESETS) or PhysicalAttributes.average_ol()
    rg_attrs = get_preset_attrs(rg_preset, OL_PRESETS) or PhysicalAttributes.average_ol()

    sim = create_3v2_scenario(
        dt1_attrs=dt1_attrs,
        dt2_attrs=dt2_attrs,
        c_attrs=c_attrs,
        lg_attrs=lg_attrs,
        rg_attrs=rg_attrs,
        double_team_target=double_team_target,
        pocket_time=max_ticks * 0.05,
    )

    frames = []
    while True:
        frame = get_multi_player_frame_data(sim)
        frames.append(frame)

        if not sim.tick():
            break

    result = {
        "ticks": sim.state.tick,
        "time": sim.state.time,
        "rusher_won": sim.state.rusher_reached_target,
        "blocker_held": sim.state.blocker_held,
        "scenario": "3v2",
        "double_team_target": double_team_target,
    }

    return {"frames": frames, "result": result}


@router.post("/run", response_model=SimulationResponse)
async def run_arms_simulation(request: SimulationRequest):
    """Run an arms prototype simulation based on scenario type."""
    try:
        if request.scenario == "double_team":
            data = run_double_team_simulation(
                dl_preset=request.dl_preset,
                post_preset=request.post_preset or request.ol_preset,
                drive_preset=request.drive_preset or request.ol_preset,
                max_ticks=request.max_ticks,
            )
        elif request.scenario == "3v2":
            data = run_3v2_simulation(
                dt1_preset=request.dt1_preset or request.dl_preset,
                dt2_preset=request.dt2_preset or request.dl_preset,
                c_preset=request.c_preset or request.ol_preset,
                lg_preset=request.lg_preset or request.ol_preset,
                rg_preset=request.rg_preset or request.ol_preset,
                double_team_target=request.double_team_target,
                max_ticks=request.max_ticks,
            )
        else:  # Default to 1v1
            data = run_simulation(
                ol_weight=request.ol_weight,
                dl_weight=request.dl_weight,
                ol_preset=request.ol_preset,
                dl_preset=request.dl_preset,
                max_ticks=request.max_ticks,
            )
        return SimulationResponse(frames=data["frames"], result=data["result"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_presets():
    """Get available player presets and scenarios."""
    return {
        "scenarios": [
            {"id": "1v1", "name": "1v1", "description": "Single OL vs single DL"},
            {"id": "double_team", "name": "Double Team (2v1)", "description": "Two OL double-teaming one DL"},
            {"id": "3v2", "name": "3v2 Interior", "description": "C, LG, RG vs two DTs"},
        ],
        "ol_presets": [
            {"id": "average_ol", "name": "Average OL", "description": "Typical starting OL (STR 60, AGI 45)"},
            {"id": "elite_tackle", "name": "Elite Tackle", "description": "Trent Williams type (STR 80, AGI 70)"},
            {"id": "mauler_guard", "name": "Mauler Guard", "description": "Quenton Nelson type (STR 90, AGI 50)"},
            {"id": "backup_ol", "name": "Backup OL", "description": "Roster depth (STR 50, AGI 40)"},
        ],
        "dl_presets": [
            {"id": "average_dt", "name": "Average DT", "description": "Typical interior DL (STR 65, AGI 45)"},
            {"id": "elite_pass_rusher", "name": "Elite Edge", "description": "Von Miller/Myles Garrett (STR 75, AGI 85)"},
            {"id": "power_rusher", "name": "Power Rusher", "description": "Aaron Donald type (STR 95, AGI 80)"},
        ],
    }


@router.post("/batch", response_model=BatchTestResponse)
async def run_batch_tests(request: BatchTestRequest):
    """Run multiple simulations and return win rate stats."""
    try:
        rusher_wins = 0
        blocker_wins = 0
        total_time = 0.0
        results = []

        for i in range(request.num_tests):
            data = run_simulation(
                ol_weight=request.ol_weight,
                dl_weight=request.dl_weight,
            )
            result = data["result"]
            total_time += result["time"]

            if result["rusher_won"]:
                rusher_wins += 1
            else:
                blocker_wins += 1

            results.append({
                "test_num": i + 1,
                "rusher_won": result["rusher_won"],
                "time": result["time"],
                "ticks": result["ticks"],
            })

        return BatchTestResponse(
            rusher_wins=rusher_wins,
            blocker_wins=blocker_wins,
            total_tests=request.num_tests,
            avg_time=total_time / request.num_tests if request.num_tests > 0 else 0,
            results=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for arms prototype API."""
    return {"status": "ok", "module": "arms-prototype"}
