import asyncio
import sys
import logging
import random
from uuid import uuid4

# Ensure project root is in path
sys.path.insert(0, ".")

from huddle.simulation.v2.orchestrator import Orchestrator, PlayPhase, PlayConfig
from huddle.simulation.v2.core.trace import get_trace_system, TraceCategory
from huddle.simulation.v2.core.entities import Player, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.lb_brain import lb_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain
from huddle.simulation.v2.plays.matchup import create_matchup
from huddle.simulation.v2.plays.run_concepts import get_run_concept

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def create_player(name, position_str, team, x, y, **attrs):
    position = Position(position_str)
    attributes = PlayerAttributes(**attrs)
    return Player(
        id=name.lower().replace(" ", "_"),
        name=name,
        team=team,
        position=position,
        pos=Vec2(x, y),
        attributes=attributes
    )

def setup_orchestrator(offense, defense, play_config):
    orch = Orchestrator()
    
    # Register brains
    for p in offense:
        if p.position == Position.QB: orch.register_brain(p.id, qb_brain)
        elif p.position in (Position.WR, Position.TE): orch.register_brain(p.id, receiver_brain)
        elif p.position == Position.RB: orch.register_brain(p.id, receiver_brain)
        elif p.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT): orch.register_brain(p.id, ol_brain)
            
    for p in defense:
        if p.position in (Position.CB, Position.SS, Position.FS): orch.register_brain(p.id, db_brain)
        elif p.position in (Position.MLB, Position.OLB, Position.ILB): orch.register_brain(p.id, lb_brain)
        elif p.position in (Position.DE, Position.DT, Position.NT): orch.register_brain(p.id, dl_brain)
        
    orch.register_brain("ballcarrier", ballcarrier_brain)
    
    orch.setup_play(offense, defense, play_config)
    return orch

async def run_debug_pass_play():
    print("\n" + "="*60)
    print("DEBUG: PASS PLAY (Checking Ghost Throw & Psychic Zone)")
    print("="*60)

    # Enable tracing
    trace_system = get_trace_system()
    trace_system.enable(True)

    # 1. Create Players based on Mesh vs Cover 2
    # Simplified from create_pass_play_session
    offense = [
        create_player("QB", "QB", Team.OFFENSE, 0, -5, throw_power=88, throw_accuracy=85),
        create_player("LT", "LT", Team.OFFENSE, -3.0, -0.5, block_power=85),
        create_player("LG", "LG", Team.OFFENSE, -1.5, -0.5, block_power=82),
        create_player("C", "C", Team.OFFENSE, 0, -0.5, block_power=80),
        create_player("RG", "RG", Team.OFFENSE, 1.5, -0.5, block_power=82),
        create_player("RT", "RT", Team.OFFENSE, 3.0, -0.5, block_power=85),
        # Receivers for Mesh
        create_player("X", "WR", Team.OFFENSE, -12, 0, route_running=85, speed=90), # Drag
        create_player("Z", "WR", Team.OFFENSE, 12, 0, route_running=85, speed=88),  # Drag
        create_player("H", "TE", Team.OFFENSE, 4.5, -0.5, route_running=75, catching=80), # Spot/Corner
        create_player("RB", "RB", Team.OFFENSE, -1.5, -4, speed=88), # Wheel/Flat
    ]
    
    defense = [
        # D-Line
        create_player("LDE", "DE", Team.DEFENSE, -3.5, 0.5, pass_rush=82),
        create_player("LDT", "DT", Team.DEFENSE, -1.0, 0.5, pass_rush=80),
        create_player("RDT", "DT", Team.DEFENSE, 1.0, 0.5, pass_rush=80),
        create_player("RDE", "DE", Team.DEFENSE, 3.5, 0.5, pass_rush=82),
        # LBs (Cover 2 Zones)
        create_player("WLB", "OLB", Team.DEFENSE, -4, 4, zone_coverage=75),
        create_player("MLB", "MLB", Team.DEFENSE, 0, 4.5, zone_coverage=80, play_recognition=80),
        create_player("SLB", "OLB", Team.DEFENSE, 4, 4, zone_coverage=75),
        # DBs (Cover 2 Zones)
        create_player("LCB", "CB", Team.DEFENSE, -15, 5, zone_coverage=80, speed=90), # Flat
        create_player("RCB", "CB", Team.DEFENSE, 15, 5, zone_coverage=80, speed=90),  # Flat
        create_player("FS", "FS", Team.DEFENSE, -8, 15, zone_coverage=85, speed=88), # Deep Half
        create_player("SS", "SS", Team.DEFENSE, 8, 15, zone_coverage=85, speed=88),  # Deep Half
    ]

    # 2. Config
    routes = {
        "x": "drag", "z": "drag", "h": "corner", "rb": "flat"
    }
    zone_assignments = {
        "lcb": "flat_l", "rcb": "flat_r", 
        "fs": "deep_half_l", "ss": "deep_half_r",
        "mlb": "middle", "wlb": "hook_l", "slb": "hook_r"
    }
    
    play_config = PlayConfig(
        routes=routes,
        zone_assignments=zone_assignments,
        max_duration=8.0,
        is_run_play=False
    )

    orch = setup_orchestrator(offense, defense, play_config)

    # 3. Run
    print(f"Matchup: Mesh vs Cover 2")
    orch._do_pre_snap_reads()
    orch._do_snap()
    
    print("\n--- SIMULATION START ---")

    for i in range(100): # 5 seconds
        dt = orch.clock.tick()
        orch._update_tick(dt)

        traces = trace_system.get_entries()
        if traces:
            for t in traces:
                if t.tick == orch.clock.tick_count:
                    # Filter for QB decision logic and DB perception
                    if t.category in (TraceCategory.DECISION, TraceCategory.PERCEPTION):
                        # Filter out basic movement traces
                        if "movement" not in t.message and "running" not in t.message:
                             print(f"T{t.tick:3d} [{t.player_name}]: {t.message}")
        
        if orch.phase == PlayPhase.BALL_IN_AIR and orch.ball.flight_start_time == orch.clock.current_time:
             print(f"\n>>> THROW DETECTED at T{orch.clock.tick_count} <<<")
             print(f"Target: {orch.ball.intended_receiver_id}")
             print(f"Type: {orch.ball.throw_type.value}")
             
        if orch.phase == PlayPhase.POST_PLAY:
            print("\n>>> PLAY ENDED <<<")
            print(f"Result: {orch._result_outcome}")
            break
            
    print("="*60)

async def run_debug_run_play():
    print("\n" + "="*60)
    print("DEBUG: RUN PLAY (Checking Sticky Blocks & Patience Trap)")
    print("="*60)

    trace_system = get_trace_system()
    trace_system.enable(True) # Clear previous traces

    # 1. Create Players for Inside Zone
    offense = [
        create_player("QB", "QB", Team.OFFENSE, 0, -3.5),
        create_player("RB", "RB", Team.OFFENSE, -0.5, -4.5, speed=88, vision=80),
        create_player("LT", "LT", Team.OFFENSE, -3.0, -0.5, block_power=80),
        create_player("LG", "LG", Team.OFFENSE, -1.5, -0.5, block_power=82),
        create_player("C", "C", Team.OFFENSE, 0, -0.5, block_power=78),
        create_player("RG", "RG", Team.OFFENSE, 1.5, -0.5, block_power=82),
        create_player("RT", "RT", Team.OFFENSE, 3.0, -0.5, block_power=80),
    ]
    
    defense = [
        # 4-3 Front
        create_player("LDE", "DE", Team.DEFENSE, -3.5, 0.5, strength=78),
        create_player("LDT", "DT", Team.DEFENSE, -1.0, 0.5, strength=82),
        create_player("RDT", "DT", Team.DEFENSE, 1.0, 0.5, strength=82),
        create_player("RDE", "DE", Team.DEFENSE, 3.5, 0.5, strength=78),
        create_player("MLB", "MLB", Team.DEFENSE, 0, 4.0, tackling=85, play_recognition=85),
    ]

    # 2. Config
    play_config = PlayConfig(
        is_run_play=True,
        run_concept="inside_zone_right",
        max_duration=8.0
    )

    orch = setup_orchestrator(offense, defense, play_config)

    print(f"Concept: Inside Zone Right")
    orch._do_pre_snap_reads()
    orch._do_snap()
    
    print("\n--- SIMULATION START ---")

    for i in range(100):
        dt = orch.clock.tick()
        orch._update_tick(dt)

        traces = trace_system.get_entries()
        if traces:
            for t in traces:
                if t.tick == orch.clock.tick_count:
                    # Focus on RB decisions and OL/DL interactions
                    if "rb" in t.player_name or "dt" in t.player_name or "lg" in t.player_name:
                         if "movement" not in t.message:
                             print(f"T{t.tick:3d} [{t.player_name}]: {t.message}")

        if orch.phase == PlayPhase.POST_PLAY:
            print("\n>>> PLAY ENDED <<<")
            print(f"Result: {orch._result_outcome}")
            break

    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_debug_pass_play())
    asyncio.run(run_debug_run_play())