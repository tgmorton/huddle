"""Router for V2 simulation - full orchestrator-based play visualization.

This router provides real-time simulation using the full orchestrator with:
- All AI brains (QB, WR, RB, OL, DL, DB, LB)
- BlockResolver for OL/DL engagements
- Route running and coverage systems
- Pass/catch resolution
- Tackle resolution

WebSocket streams all state including:
- Player positions, velocities, facing
- Blocking engagements and shed progress
- DB recognition state
- Pursuit targets
- Ballcarrier moves
"""

import asyncio
import json
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import (
    Player, Team, Position, PlayerAttributes, Ball, BallState
)
from huddle.simulation.v2.core.clock import Clock
from huddle.simulation.v2.core.events import EventBus, Event, EventType
from huddle.simulation.v2.orchestrator import (
    Orchestrator, PlayConfig, PlayPhase, PlayResult, BrainDecision, DropbackType
)
from huddle.simulation.v2.plays.routes import RouteType, ROUTE_LIBRARY
from huddle.simulation.v2.plays.concepts import CONCEPT_LIBRARY
from huddle.simulation.v2.plays.schemes import SCHEME_LIBRARY
from huddle.simulation.v2.plays.matchup import create_matchup, describe_matchup, CLASSIC_MATCHUPS
from huddle.simulation.v2.plays.run_concepts import get_run_concept, list_run_concepts, RUN_CONCEPT_LIBRARY
from huddle.simulation.v2.systems.route_runner import RouteAssignment
from huddle.simulation.v2.systems.coverage import (
    CoverageType, CoverageAssignment, ZoneType, ZONE_BOUNDARIES
)
from huddle.simulation.v2.ai.qb_brain import (
    qb_brain, enable_trace, get_trace, _get_state as get_qb_state
)
from huddle.simulation.v2.core.trace import get_trace_system
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.lb_brain import lb_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain
from huddle.simulation.v2.resolution.blocking import get_play_blocking_quality
import random


router = APIRouter(prefix="/v2-sim", tags=["v2-simulation"])


# =============================================================================
# Blocking Test Scenarios
# =============================================================================
# These scenarios are designed to test and visualize specific blocking behaviors
# They range from simple 1v1 interactions to full line play

BLOCKING_SCENARIOS = {
    "1_1_fire_off": {
        "name": "1.1 OL Fire Off",
        "tier": 1,
        "description": "Single OL fires off at snap - tests initial movement",
        "expected": "LG moves from y=-0.5 to y=0 in first 0.2s",
        "is_run_play": True,  # Force run blocking mode
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
        ],
        "defense": [],
    },
    "1_2_dl_hold_gap": {
        "name": "1.2 DL Hold Gap",
        "tier": 1,
        "description": "DL holds gap position on run play",
        "expected": "DT holds x=1.5, moves toward LOS",
        "is_run_play": True,  # Force run defense mode
        "offense": [
            {"name": "RB", "position": "RB", "x": 0, "y": -4},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": 1.5, "y": 0.5},
        ],
    },
    "1_3_basic_engagement": {
        "name": "1.3 Basic Engagement",
        "tier": 1,
        "description": "1 OL head-up on 1 DL - basic blocking",
        "expected": "LG and DT meet near y=0, minimal movement",
        "is_run_play": True,  # Force run blocking mode
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": -1.5, "y": 0.5},
        ],
    },
    "1_4_ol_wins": {
        "name": "1.4 OL Wins Engagement",
        "tier": 1,
        "description": "Strong OL (90 block) vs weak DL (60)",
        "expected": "OL gains leverage, pushes DL back",
        "is_run_play": True,  # Force run blocking mode
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 90, "strength": 90},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": -1.5, "y": 0.5, "strength": 60, "pass_rush": 60},
        ],
    },
    "1_5_dl_wins": {
        "name": "1.5 DL Wins Engagement",
        "tier": 1,
        "description": "Weak OL (60) vs strong DL (90)",
        "expected": "DL gains negative leverage, shed progress increases",
        "is_run_play": True,  # Force run blocking mode
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 60, "strength": 60},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": -1.5, "y": 0.5, "strength": 90, "pass_rush": 90},
        ],
    },
    "2_1_zone_step": {
        "name": "2.1 Zone Step",
        "tier": 2,
        "description": "OL with zone_step assignment engages DL in gap",
        "expected": "LG zone steps playside, engages DT",
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
            {"name": "C", "position": "C", "x": 0, "y": -0.5},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5},
            {"name": "RB", "position": "RB", "x": 0, "y": -4},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": -1.0, "y": 0.5},
        ],
        "run_concept": "inside_zone_right",
    },
    "3_1_combo_block": {
        "name": "3.1 Combo Block",
        "tier": 3,
        "description": "LG + C combo on DT, one should climb to LB",
        "expected": "Both engage DT, one climbs to LB after 0.8s",
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
            {"name": "C", "position": "C", "x": 0, "y": -0.5},
            {"name": "RB", "position": "RB", "x": 0, "y": -4},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": -0.75, "y": 0.5},
            {"name": "MLB", "position": "MLB", "x": 0, "y": 4.0},
        ],
        "run_concept": "inside_zone_right",
    },
    "3_3_gap_integrity": {
        "name": "3.3 Gap Integrity",
        "tier": 3,
        "description": "2 OL vs 2 DL head-up - each blocks their man",
        "expected": "LG blocks LDT, RG blocks RDT, gaps maintained",
        "is_run_play": True,  # Force run blocking mode
        "offense": [
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5},
            {"name": "RB", "position": "RB", "x": 0, "y": -4},
        ],
        "defense": [
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5},
        ],
    },
    "4_1_head_up_defense": {
        "name": "4.1 Full Line Head-Up",
        "tier": 4,
        "description": "5 OL vs 4 DL head-up - clean 1-on-1 matchups with zone blocking",
        "expected": "Each OL blocks their man, C uncovered climbs to 2nd level",
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -3.5},
            {"name": "RB", "position": "RB", "x": -0.5, "y": -4.5},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
            {"name": "C", "position": "C", "x": 0, "y": -0.5},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.0, "y": 0.5},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5},
            {"name": "RDE", "position": "DE", "x": 3.0, "y": 0.5},
        ],
        "run_concept": "inside_zone_right",
    },
    "4_2_inside_zone_right": {
        "name": "4.2 Inside Zone Right",
        "tier": 4,
        "description": "Full inside zone play with blocking assignments",
        "expected": "Zone step playside, cutoff backside, combo on shaded DL",
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -3.5},
            {"name": "RB", "position": "RB", "x": -0.5, "y": -4.5},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5},
            {"name": "C", "position": "C", "x": 0, "y": -0.5},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5},  # 5-tech
            {"name": "LDT", "position": "DT", "x": -2.25, "y": 0.5},  # 3-tech
            {"name": "RDT", "position": "DT", "x": 0.75, "y": 0.5},   # 1-tech
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5},   # 5-tech
            {"name": "MLB", "position": "MLB", "x": 0, "y": 4.5},
        ],
        "run_concept": "inside_zone_right",
    },
    # ==========================================================================
    # Pass Protection Scenarios
    # ==========================================================================
    "5_1_pass_protection": {
        "name": "5.1 Pass Protection",
        "tier": 5,
        "description": "5 OL in pass pro vs 4 DL with elite edge rushers",
        "expected": "OL sets, DL rushes. RDE (92 pass_rush) vs RT (75) is key matchup",
        "is_run_play": False,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 82, "strength": 80},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 76, "strength": 76},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 75, "strength": 74},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -4.0, "y": 0.5, "pass_rush": 88, "strength": 78, "speed": 82},
            {"name": "LDT", "position": "DT", "x": -1.0, "y": 0.5, "pass_rush": 80, "strength": 85},
            {"name": "RDT", "position": "DT", "x": 1.0, "y": 0.5, "pass_rush": 78, "strength": 83},
            {"name": "RDE", "position": "DE", "x": 4.0, "y": 0.5, "pass_rush": 92, "strength": 80, "speed": 85},
        ],
    },
    "5_2_double_team": {
        "name": "5.2 Double Team",
        "tier": 5,
        "description": "2 OL double-team elite NT (95 strength) - neither wins 1v1",
        "expected": "LG + C both engage NT, combined leverage should neutralize",
        "is_run_play": True,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 76, "strength": 76},
            {"name": "RB", "position": "RB", "x": -0.5, "y": -2.5},
        ],
        "defense": [
            {"name": "NT", "position": "NT", "x": -0.5, "y": 0.5, "pass_rush": 92, "strength": 95},
        ],
    },
    "5_3_dl_shed_pursuit": {
        "name": "5.3 DL Shed & Pursuit",
        "tier": 5,
        "description": "Strong DT (85) vs average OL (72) - DT sheds then pursues RB",
        "expected": "DT wins leverage, sheds block ~1.5s, then chases RB running away",
        "is_run_play": True,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 72, "strength": 72},
            {"name": "RB", "position": "RB", "x": -1.0, "y": -2.5, "speed": 85},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 82, "strength": 85, "speed": 78},
        ],
    },
    "5_4_speed_mismatch": {
        "name": "5.4 Speed Mismatch",
        "tier": 5,
        "description": "Speed rusher DE (92 speed) vs slow RT (70 speed)",
        "expected": "DE should win around the edge with speed, forcing pressure",
        "is_run_play": False,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 82, "strength": 84, "speed": 70},
        ],
        "defense": [
            {"name": "DE", "position": "DE", "x": 4.5, "y": 0.5, "pass_rush": 88, "strength": 75, "speed": 92, "acceleration": 90},
        ],
    },
    "5_5_full_line_with_mlb": {
        "name": "5.5 Full Line + MLB",
        "tier": 5,
        "description": "5 OL vs 4 DL + MLB - complete run play with second level",
        "expected": "OL engages DL, RB finds gap, MLB pursues and makes tackle",
        "is_run_play": True,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 76, "strength": 76},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 82, "strength": 82},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 77, "strength": 77},
            {"name": "RB", "position": "RB", "x": 1.0, "y": -2.5, "speed": 88},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -4.0, "y": 0.5, "pass_rush": 82, "strength": 80},
            {"name": "LDT", "position": "DT", "x": -1.0, "y": 0.5, "pass_rush": 80, "strength": 85},
            {"name": "RDT", "position": "DT", "x": 1.0, "y": 0.5, "pass_rush": 78, "strength": 83},
            {"name": "RDE", "position": "DE", "x": 4.0, "y": 0.5, "pass_rush": 84, "strength": 78},
            {"name": "MLB", "position": "MLB", "x": 0, "y": 5.0, "speed": 84, "tackling": 85, "play_recognition": 80},
        ],
    },
    "5_6_run_basic": {
        "name": "5.6 Basic Run (OL Wins)",
        "tier": 5,
        "description": "1 OL (80) vs 1 DL (75) + RB - OL should win and create lane",
        "expected": "RG wins matchup, RB gains 10+ yards",
        "is_run_play": True,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "RB", "position": "RB", "x": 0, "y": -2.5, "speed": 88},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 75, "strength": 75},
        ],
    },
    "5_7_run_dl_wins": {
        "name": "5.7 DL Wins Run (TFL)",
        "tier": 5,
        "description": "Weak OL (60) vs strong DL (90) - DL should penetrate for TFL",
        "expected": "DT dominates, penetrates backfield, RB stuffed behind LOS",
        "is_run_play": True,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -1},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 60, "strength": 60},
            {"name": "RB", "position": "RB", "x": 0, "y": -2.5, "speed": 88},
        ],
        "defense": [
            {"name": "DT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 90, "strength": 90},
        ],
    },
    # ==========================================================================
    # Tier 6: Block Direction & Slide Protection Scenarios
    # ==========================================================================
    "6_1_slide_left": {
        "name": "6.1 Slide Left Protection",
        "tier": 6,
        "description": "Full OL slides left in pass protection - coordinated push direction",
        "expected": "LT/LG/C push DL left, RG/RT block straight. DL on left side pushed laterally.",
        "is_run_play": False,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -5},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 82, "strength": 80},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 80, "strength": 78},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 80, "strength": 78},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 78, "strength": 76},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 80, "strength": 78},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5, "pass_rush": 78, "strength": 82},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 78, "strength": 82},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 85, "strength": 78},
        ],
    },
    "6_2_slide_right": {
        "name": "6.2 Slide Right Protection",
        "tier": 6,
        "description": "Full OL slides right in pass protection - coordinated push direction",
        "expected": "RG/RT/C push DL right, LT/LG block straight. DL on right side pushed laterally.",
        "is_run_play": False,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -5},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 78, "strength": 76},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 80, "strength": 78},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 80, "strength": 78},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 82, "strength": 80},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 85, "strength": 78},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5, "pass_rush": 78, "strength": 82},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 78, "strength": 82},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 80, "strength": 78},
        ],
    },
    "6_3_zone_wash_right": {
        "name": "6.3 Zone Wash Right",
        "tier": 6,
        "description": "Inside zone right - OL winning pushes DL laterally right + back",
        "expected": "OL push DL right toward sideline. Creates cutback lane on left.",
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -3.5},
            {"name": "RB", "position": "RB", "x": -0.5, "y": -4.5, "speed": 88},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 82, "strength": 82},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 84, "strength": 84},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 84, "strength": 84},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 80, "strength": 80},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 75, "strength": 75},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5, "pass_rush": 74, "strength": 78},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 74, "strength": 78},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 75, "strength": 75},
        ],
        "run_concept": "inside_zone_right",
    },
    "6_4_zone_wash_left": {
        "name": "6.4 Zone Wash Left",
        "tier": 6,
        "description": "Inside zone left - OL winning pushes DL laterally left + back",
        "expected": "OL push DL left toward sideline. Creates cutback lane on right.",
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -3.5},
            {"name": "RB", "position": "RB", "x": 0.5, "y": -4.5, "speed": 88},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 84, "strength": 84},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 84, "strength": 84},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 82, "strength": 82},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 75, "strength": 75},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5, "pass_rush": 74, "strength": 78},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 74, "strength": 78},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 75, "strength": 75},
        ],
        "run_concept": "inside_zone_left",
    },
    "6_5_power_down_blocks": {
        "name": "6.5 Power Right (Down Blocks)",
        "tier": 6,
        "description": "Power right - backside OL down-block pushes DL AWAY from play",
        "expected": "LT/LG down-block pushes DL left (away from right). Creates seal for puller.",
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -3.5},
            {"name": "RB", "position": "RB", "x": -1.0, "y": -4.5, "speed": 86},
            {"name": "FB", "position": "FB", "x": 0.5, "y": -3.0, "speed": 78, "block_power": 82},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 82, "strength": 82},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 78, "strength": 78},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 82, "strength": 82},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 80, "strength": 80},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 78, "strength": 78},
            {"name": "LDT", "position": "DT", "x": -1.5, "y": 0.5, "pass_rush": 76, "strength": 80},
            {"name": "RDT", "position": "DT", "x": 1.5, "y": 0.5, "pass_rush": 76, "strength": 80},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 78, "strength": 78},
            {"name": "MLB", "position": "MLB", "x": 0, "y": 4.5, "tackling": 82},
        ],
        "run_concept": "power_right",
    },
    "6_6_slide_vs_blitz": {
        "name": "6.6 Slide Left vs Blitz Right",
        "tier": 6,
        "description": "Slide left with blitz coming from right - tests man-side protection",
        "expected": "Slide side (left) handles normal rush, RG/RT pick up blitzing LB",
        "is_run_play": False,
        "offense": [
            {"name": "QB", "position": "QB", "x": 0, "y": -5},
            {"name": "LT", "position": "LT", "x": -3.0, "y": -0.5, "block_power": 80, "strength": 78},
            {"name": "LG", "position": "LG", "x": -1.5, "y": -0.5, "block_power": 78, "strength": 76},
            {"name": "C", "position": "C", "x": 0, "y": -0.5, "block_power": 76, "strength": 76},
            {"name": "RG", "position": "RG", "x": 1.5, "y": -0.5, "block_power": 80, "strength": 80},
            {"name": "RT", "position": "RT", "x": 3.0, "y": -0.5, "block_power": 82, "strength": 80},
        ],
        "defense": [
            {"name": "LDE", "position": "DE", "x": -3.75, "y": 0.5, "pass_rush": 78, "strength": 76},
            {"name": "LDT", "position": "DT", "x": -1.0, "y": 0.5, "pass_rush": 76, "strength": 80},
            {"name": "RDT", "position": "DT", "x": 1.0, "y": 0.5, "pass_rush": 76, "strength": 80},
            {"name": "RDE", "position": "DE", "x": 3.75, "y": 0.5, "pass_rush": 82, "strength": 78},
            {"name": "ROLB", "position": "OLB", "x": 4.5, "y": 2.0, "pass_rush": 75, "speed": 85},
        ],
    },
}


# =============================================================================
# DL Technique Alignments
# =============================================================================
# Techniques define where DL align relative to OL
# Based on standard 1.5 yard OL spacing with C at x=0

# Technique positions (x-offset from center, positive = right side)
# These match real NFL alignment techniques
DL_TECHNIQUES = {
    # Head-up alignments
    "0": 0.0,        # Head up on center
    "2": 1.5,        # Head up on guard
    "4": 3.0,        # Head up on tackle
    "6": 4.5,        # Head up on tight end

    # Shade/gap alignments (between positions)
    "1": 0.75,       # Shade on center (A gap)
    "2i": 1.25,      # Inside shade on guard
    "3": 2.25,       # Outside shade on guard (B gap)
    "4i": 2.75,      # Inside shade on tackle
    "5": 3.75,       # Outside shade on tackle (C gap)
    "6i": 4.25,      # Inside shade on TE
    "7": 5.0,        # Outside shade on TE (D gap)
    "9": 5.5,        # Wide 9, outside everything
}


def get_technique_x(technique: str, side: str = "left") -> float:
    """Get x-position for a DL technique.

    Args:
        technique: Technique number ("0", "1", "2i", "3", "5", etc.)
        side: "left" or "right" - which side of the line

    Returns:
        x-coordinate for alignment
    """
    base_x = DL_TECHNIQUES.get(technique, 2.25)  # Default to 3-tech
    return -base_x if side == "left" else base_x


# =============================================================================
# Request/Response Models
# =============================================================================

class PlayerConfig(BaseModel):
    """Configuration for any player."""
    name: str
    position: str  # QB, WR, RB, TE, OL, DL, LB, CB, S
    alignment_x: float
    alignment_y: float = 0.0

    # Route (for receivers)
    route_type: Optional[str] = None
    read_order: int = 1
    is_hot_route: bool = False

    # Coverage (for DBs/LBs)
    coverage_type: Optional[str] = None  # "man" or "zone"
    man_target: Optional[str] = None
    zone_type: Optional[str] = None

    # Attributes (all 0-99)
    speed: int = 85
    acceleration: int = 85
    agility: int = 85
    strength: int = 75
    awareness: int = 75

    # Position-specific
    throw_power: int = 85
    throw_accuracy: int = 85
    route_running: int = 85
    catching: int = 85
    elusiveness: int = 75
    vision: int = 75
    block_power: int = 75
    block_finesse: int = 75
    pass_rush: int = 75
    man_coverage: int = 75
    zone_coverage: int = 75
    play_recognition: int = 75
    press: int = 75
    tackling: int = 75


class SimulationConfig(BaseModel):
    """Configuration for a simulation."""
    offense: List[PlayerConfig]
    defense: List[PlayerConfig]
    tick_rate_ms: int = 50
    max_time: float = 8.0
    throw_timing: Optional[float] = None  # Auto-throw after X seconds
    throw_target: Optional[str] = None    # Who to throw to
    # Run play config (set when creating run plays)
    is_run_play: bool = False
    run_concept: Optional[str] = None


class SessionInfo(BaseModel):
    """Info about an active session."""
    session_id: str
    tick_rate_ms: int
    max_time: float


# =============================================================================
# Play Outcome (for frontend)
# =============================================================================

class PlayOutcome(str, Enum):
    """Outcome of the play."""
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"
    TACKLED = "tackled"
    SACK = "sack"
    TOUCHDOWN = "touchdown"


# =============================================================================
# Session Management
# =============================================================================

@dataclass
class V2SimSession:
    """Active simulation session wrapping the orchestrator."""
    session_id: UUID
    config: SimulationConfig
    orchestrator: Orchestrator

    # Player references for serialization
    offense_players: List[Player] = field(default_factory=list)
    defense_players: List[Player] = field(default_factory=list)

    # Session state
    is_running: bool = False
    is_paused: bool = False
    is_complete: bool = False
    play_outcome: PlayOutcome = PlayOutcome.IN_PROGRESS

    # Tracking for visualization
    ball_carrier_id: Optional[str] = None
    tackle_position: Optional[Vec2] = None
    tackler_id: Optional[str] = None


class V2SessionManager:
    """Manages active v2 simulation sessions."""

    def __init__(self):
        self.sessions: Dict[UUID, V2SimSession] = {}

    def create_session(self, config: SimulationConfig) -> V2SimSession:
        """Create a new simulation session with full orchestrator."""
        # Check if this is a run play - delegate to specialized creator
        if config.is_run_play and config.run_concept:
            from huddle.simulation.v2.plays.run_concepts import get_run_concept
            run_concept = get_run_concept(config.run_concept)
            if run_concept:
                return _create_run_session(config, run_concept)

        session_id = uuid4()

        # Create orchestrator
        orchestrator = Orchestrator()

        # Build offensive players
        offense_players = []
        routes_config: Dict[str, str] = {}

        for pc in config.offense:
            player = self._create_player(pc, Team.OFFENSE)
            offense_players.append(player)

            # Register route if specified
            if pc.route_type and player.position in (Position.WR, Position.TE, Position.RB):
                routes_config[player.id] = pc.route_type

            # Register brain
            brain = self._get_brain_for_position(player.position, Team.OFFENSE)
            if brain:
                orchestrator.register_brain(player.id, brain)

        # Build defensive players
        defense_players = []
        man_assignments: Dict[str, str] = {}
        zone_assignments: Dict[str, str] = {}

        for pc in config.defense:
            player = self._create_player(pc, Team.DEFENSE)
            defense_players.append(player)

            # Register coverage
            if pc.coverage_type == "man" and pc.man_target:
                # Find target player ID
                target = next(
                    (p for p in offense_players if p.name.lower() == pc.man_target.lower()),
                    None
                )
                if target:
                    man_assignments[player.id] = target.id
            elif pc.coverage_type == "zone" and pc.zone_type:
                zone_assignments[player.id] = pc.zone_type

            # Register brain
            brain = self._get_brain_for_position(player.position, Team.DEFENSE)
            if brain:
                orchestrator.register_brain(player.id, brain)

        # Register role-based brains (not tied to specific player IDs)
        # The orchestrator looks for "ballcarrier" key when switching brains after catch
        orchestrator.register_brain("ballcarrier", ballcarrier_brain)

        # Create play config
        play_config = PlayConfig(
            routes=routes_config,
            man_assignments=man_assignments,
            zone_assignments=zone_assignments,
            max_duration=config.max_time,
            throw_timing=config.throw_timing,
            throw_target=config.throw_target,
            is_run_play=config.is_run_play,  # Pass through for OL/DL brains
        )

        # Setup the play
        orchestrator.setup_play(offense_players, defense_players, play_config)

        session = V2SimSession(
            session_id=session_id,
            config=config,
            orchestrator=orchestrator,
            offense_players=offense_players,
            defense_players=defense_players,
        )

        self.sessions[session_id] = session
        return session

    def _create_player(self, config: PlayerConfig, team: Team) -> Player:
        """Create a player from config."""
        position = Position(config.position.upper())

        attrs = PlayerAttributes(
            speed=config.speed,
            acceleration=config.acceleration,
            agility=config.agility,
            strength=config.strength,
            awareness=config.awareness,
            vision=config.vision,
            play_recognition=config.play_recognition,
            throw_power=config.throw_power,
            throw_accuracy=config.throw_accuracy,
            route_running=config.route_running,
            catching=config.catching,
            elusiveness=config.elusiveness,
            block_power=config.block_power,
            block_finesse=config.block_finesse,
            pass_rush=config.pass_rush,
            man_coverage=config.man_coverage,
            zone_coverage=config.zone_coverage,
            press=config.press,
            tackling=config.tackling,
        )

        return Player(
            id=config.name.lower().replace(" ", "_"),
            name=config.name,
            team=team,
            position=position,
            pos=Vec2(config.alignment_x, config.alignment_y),
            attributes=attrs,
            read_order=config.read_order,
            is_hot_route=config.is_hot_route,
        )

    def _get_brain_for_position(self, position: Position, team: Team):
        """Get the appropriate brain function for a position."""
        if team == Team.OFFENSE:
            if position == Position.QB:
                return qb_brain
            elif position in (Position.WR, Position.TE):
                return receiver_brain
            elif position == Position.RB:
                return receiver_brain  # RB uses receiver brain for routes
            elif position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
                return ol_brain
        else:  # Defense
            if position in (Position.CB, Position.SS, Position.FS):
                return db_brain
            elif position in (Position.MLB, Position.OLB, Position.ILB):
                return lb_brain
            elif position in (Position.DE, Position.DT, Position.NT):
                return dl_brain
        return None

    def get_session(self, session_id: UUID) -> Optional[V2SimSession]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: UUID):
        if session_id in self.sessions:
            del self.sessions[session_id]


# Global session manager
session_manager = V2SessionManager()


# =============================================================================
# State Serialization
# =============================================================================

def player_to_dict(
    player: Player,
    orchestrator: Orchestrator,
    session: V2SimSession,
) -> dict:
    """Convert player state to dict with all visualization fields."""

    # Base data
    data = {
        "id": player.id,
        "name": player.name,
        "team": player.team.value,
        "position": player.position.value,
        "x": player.pos.x,
        "y": player.pos.y,
        "vx": player.velocity.x,
        "vy": player.velocity.y,
        "speed": player.velocity.length(),
        "facing_x": player.facing.x,
        "facing_y": player.facing.y,
        "has_ball": player.has_ball,
        "is_engaged": player.is_engaged,
    }

    # Determine player_type for frontend
    if player.position == Position.QB:
        data["player_type"] = "qb"
    elif player.position == Position.RB:
        data["player_type"] = "rb"
    elif player.position == Position.FB:
        data["player_type"] = "fb"
    elif player.position in (Position.WR, Position.TE):
        data["player_type"] = "receiver"
    elif player.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
        data["player_type"] = "ol"
    elif player.position in (Position.DE, Position.DT, Position.NT):
        data["player_type"] = "dl"
    elif player.position in (Position.CB, Position.SS, Position.FS):
        data["player_type"] = "defender"
    elif player.position in (Position.MLB, Position.OLB, Position.ILB):
        data["player_type"] = "defender"
    else:
        data["player_type"] = "receiver" if player.team == Team.OFFENSE else "defender"

    # Goal direction
    data["goal_direction"] = 1 if player.team == Team.OFFENSE else -1

    # Route info (for receivers)
    route_assignment = orchestrator.route_runner.get_assignment(player.id)
    if route_assignment:
        data["route_name"] = route_assignment.route.name
        data["route_phase"] = route_assignment.phase.value
        data["current_waypoint"] = route_assignment.current_waypoint_idx
        data["total_waypoints"] = len(route_assignment.route.waypoints)
        if route_assignment.current_target:
            data["target_x"] = route_assignment.current_target.x
            data["target_y"] = route_assignment.current_target.y

    # Coverage info (for defenders)
    coverage_assignment = orchestrator.coverage_system.assignments.get(player.id)
    if coverage_assignment:
        data["coverage_type"] = coverage_assignment.coverage_type.value
        data["coverage_phase"] = coverage_assignment.phase.value

        if coverage_assignment.coverage_type == CoverageType.MAN:
            data["man_target_id"] = coverage_assignment.man_target_id
            data["has_reacted_to_break"] = coverage_assignment.has_reacted_to_break
            # DB recognition state
            data["has_recognized_break"] = coverage_assignment.has_reacted_to_break
            base_delay = 0.25  # seconds
            data["recognition_delay"] = base_delay
            # Timer based on reaction_delay_remaining (ticks at 50ms)
            tick_rate = 0.05
            elapsed_ticks = 5 - coverage_assignment.reaction_delay_remaining
            data["recognition_timer"] = max(0, elapsed_ticks * tick_rate)
        else:
            data["zone_type"] = coverage_assignment.zone_type.value if coverage_assignment.zone_type else None
            data["has_triggered"] = coverage_assignment.has_triggered
            data["zone_target_id"] = coverage_assignment.zone_target_id

        if coverage_assignment.anticipated_position:
            data["anticipated_x"] = coverage_assignment.anticipated_position.x
            data["anticipated_y"] = coverage_assignment.anticipated_position.y

    # Blocking engagement info (for OL/DL)
    engagement = orchestrator.block_resolver.get_engagement_for_player(player.id)
    if engagement:
        data["is_engaged"] = True
        if player.team == Team.OFFENSE:
            data["engaged_with_id"] = engagement.dl_id
        else:
            data["engaged_with_id"] = engagement.ol_id
        data["block_shed_progress"] = engagement.shed_progress

    # Pursuit target (for defenders chasing ball carrier)
    if session.ball_carrier_id and player.team == Team.DEFENSE:
        ball_carrier = next(
            (p for p in session.offense_players if p.id == session.ball_carrier_id),
            None
        )
        if ball_carrier and orchestrator.phase in (PlayPhase.AFTER_CATCH, PlayPhase.RUN_ACTIVE):
            data["pursuit_target_x"] = ball_carrier.pos.x
            data["pursuit_target_y"] = ball_carrier.pos.y

    # Ballcarrier info
    if player.id == session.ball_carrier_id:
        data["is_ball_carrier"] = True
        # Check for evasion move from brain decision
        # The orchestrator stores last action on player._last_action
        last_action = getattr(player, '_last_action', None)
        evasion_moves = {'juke', 'spin', 'truck', 'stiff_arm', 'hurdle', 'dead_leg', 'cut', 'speed_burst'}
        if last_action and last_action in evasion_moves:
            data["current_move"] = last_action
            # Note: move_success would need additional tracking from MoveResolver
            # For now, we just show the move being attempted

        # Tackle engagement info (for ballcarrier being tackled)
        tackle_engagement = orchestrator.tackle_resolver.get_engagement(player.id)
        if tackle_engagement:
            data["in_tackle"] = True
            data["tackle_leverage"] = tackle_engagement.leverage  # -1 (tackler winning) to +1 (BC winning)
            data["tackle_ticks"] = tackle_engagement.ticks_engaged
            data["tackle_yards_gained"] = tackle_engagement.yards_gained_in_engagement
            # Include primary tackler ID for visualization
            if tackle_engagement.primary_tackler_id:
                data["primary_tackler_id"] = tackle_engagement.primary_tackler_id

    # Run play specific fields
    if orchestrator._run_concept:
        run_concept = orchestrator._run_concept
        pos_name = player.position.value.upper() if player.position else ""

        # OL blocking assignment fields
        if data["player_type"] == "ol":
            ol_assign = run_concept.get_ol_assignment(pos_name)
            if ol_assign:
                data["blocking_assignment"] = ol_assign.assignment.value
                data["is_pulling"] = ol_assign.assignment.value in ("pull_lead", "pull_wrap")
                # Pull target is roughly the aiming point area
                if data["is_pulling"]:
                    pull_dir = ol_assign.pull_direction or run_concept.play_side
                    # Calculate approximate pull target
                    pull_x = 6 if pull_dir == "right" else -6
                    data["pull_target_x"] = pull_x
                    data["pull_target_y"] = 2  # Just past LOS

        # RB/ballcarrier fields
        if player.position in (Position.RB, Position.FB):
            rb_assign = run_concept.get_backfield_assignment(pos_name)
            if rb_assign:
                data["target_gap"] = rb_assign.aiming_point.value if rb_assign.aiming_point else None
                data["designed_gap"] = run_concept.aiming_point.value if run_concept.aiming_point else None
                # Read point is first waypoint
                if rb_assign.path:
                    data["read_point_x"] = rb_assign.path[0].x
                    data["read_point_y"] = rb_assign.path[0].y
                    # Vision target is next waypoint in path
                    if len(rb_assign.path) > 1:
                        data["vision_target_x"] = rb_assign.path[1].x
                        data["vision_target_y"] = rb_assign.path[1].y

    return data


def ball_to_dict(ball: Ball, current_time: float) -> dict:
    """Convert ball state to dict."""
    pos, height = ball.full_position_at_time(current_time)

    data = {
        "state": ball.state.value,
        "x": pos.x,
        "y": pos.y,
        "height": height,
        "carrier_id": ball.carrier_id,
    }

    if ball.state == BallState.IN_FLIGHT:
        data["flight_origin_x"] = ball.flight_origin.x if ball.flight_origin else None
        data["flight_origin_y"] = ball.flight_origin.y if ball.flight_origin else None
        data["flight_target_x"] = ball.flight_target.x if ball.flight_target else None
        data["flight_target_y"] = ball.flight_target.y if ball.flight_target else None
        data["flight_progress"] = (
            (current_time - ball.flight_start_time) / ball.flight_duration
            if ball.flight_duration > 0 else 1.0
        )
        data["intended_receiver_id"] = ball.intended_receiver_id
        if ball.throw_type:
            data["throw_type"] = ball.throw_type.value
        data["peak_height"] = ball.peak_height

    return data


def event_to_dict(event: Event) -> dict:
    """Convert event to dict."""
    return {
        "time": event.time,
        "type": event.type.value,
        "player_id": event.player_id,
        "target_id": event.target_id,
        "description": event.description,
        "data": event.data,
    }


def waypoints_to_dict(orchestrator: Orchestrator, player_id: str) -> List[dict]:
    """Get waypoints for a player's route."""
    assignment = orchestrator.route_runner.get_assignment(player_id)
    if not assignment or not hasattr(assignment, '_field_waypoints'):
        return []

    waypoints = []
    for i, wp in enumerate(assignment._field_waypoints):
        if i < len(assignment.route.waypoints):
            wp_def = assignment.route.waypoints[i]
            waypoints.append({
                "x": wp.x,
                "y": wp.y,
                "is_break": wp_def.is_break,
                "phase": wp_def.phase.value,
                "look_for_ball": wp_def.look_for_ball,
            })
    return waypoints


def zone_boundaries_to_dict() -> Dict[str, dict]:
    """Get zone boundaries for visualization."""
    return {
        zone_type.value: {
            "min_x": zone.min_x,
            "max_x": zone.max_x,
            "min_y": zone.min_y,
            "max_y": zone.max_y,
            "anchor_x": zone.anchor.x,
            "anchor_y": zone.anchor.y,
            "is_deep": zone.is_deep,
        }
        for zone_type, zone in ZONE_BOUNDARIES.items()
    }


def session_state_to_dict(session: V2SimSession) -> dict:
    """Get full session state as dict."""
    orchestrator = session.orchestrator
    players = []
    waypoints = {}

    # All players
    for player in session.offense_players + session.defense_players:
        players.append(player_to_dict(player, orchestrator, session))

        # Waypoints for receivers
        route_assignment = orchestrator.route_runner.get_assignment(player.id)
        if route_assignment:
            waypoints[player.id] = waypoints_to_dict(orchestrator, player.id)

    # Run play state
    is_run_play = orchestrator.config.is_run_play if orchestrator.config else False
    run_concept_name = orchestrator.config.run_concept if orchestrator.config else None
    designed_gap = None
    if orchestrator._run_concept:
        designed_gap = orchestrator._run_concept.aiming_point.value

    return {
        "session_id": str(session.session_id),
        "tick": orchestrator.clock.tick_count,
        "time": orchestrator.clock.current_time,
        "phase": orchestrator.phase.value,
        "is_running": session.is_running,
        "is_paused": session.is_paused,
        "is_complete": session.is_complete,
        "play_outcome": session.play_outcome.value,
        "ball_carrier_id": session.ball_carrier_id,
        "tackle_position": {
            "x": session.tackle_position.x,
            "y": session.tackle_position.y
        } if session.tackle_position else None,
        "players": players,
        "ball": ball_to_dict(orchestrator.ball, orchestrator.clock.current_time),
        "waypoints": waypoints,
        "zone_boundaries": zone_boundaries_to_dict(),
        "events": [event_to_dict(e) for e in orchestrator.event_bus.history],
        "config": {
            "tick_rate_ms": session.config.tick_rate_ms,
            "max_time": session.config.max_time,
        },
        # Run play state
        "is_run_play": is_run_play,
        "run_concept": run_concept_name,
        "designed_gap": designed_gap,
    }


# =============================================================================
# Drive Management - Multi-Play Scenarios
# =============================================================================

class DriveStatus(str, Enum):
    """Status of a drive."""
    ACTIVE = "active"
    TOUCHDOWN = "touchdown"
    TURNOVER = "turnover"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"


class PlayResultInfo(BaseModel):
    """Result of a single play."""
    yards_gained: int
    play_type: str  # "pass", "run", "sack", "incomplete"
    description: str
    is_first_down: bool = False
    is_touchdown: bool = False
    is_turnover: bool = False


class DriveState(BaseModel):
    """Current state of a drive."""
    drive_id: str
    down: int  # 1-4
    distance: int  # yards to first down
    ball_on: int  # yard line (1-99, own 1 to opp 1)
    status: DriveStatus
    plays: List[PlayResultInfo] = []
    total_yards: int = 0

    # For display
    down_and_distance: str = ""  # "2nd & 7"
    field_position: str = ""  # "OWN 35" or "OPP 45"


class StartDriveRequest(BaseModel):
    """Request to start a new drive."""
    starting_yard_line: int = 25  # Own 25 by default


class RunPlayRequest(BaseModel):
    """Request to run a play."""
    drive_id: str
    play_type: str  # "pass" or "run"
    play_name: Optional[str] = None  # Specific play/concept name
    # Pass play options
    concept: Optional[str] = None
    routes: Optional[Dict[str, str]] = None
    # Run play options
    run_concept: Optional[str] = None


@dataclass
class Drive:
    """Internal drive state."""
    drive_id: str
    down: int = 1
    distance: int = 10
    ball_on: int = 25  # Yard line from own goal (1-99)
    status: DriveStatus = DriveStatus.ACTIVE
    plays: List[PlayResultInfo] = field(default_factory=list)
    total_yards: int = 0

    def get_down_and_distance(self) -> str:
        """Get formatted down and distance string."""
        down_names = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
        if self.status == DriveStatus.TURNOVER_ON_DOWNS:
            return "Turnover on Downs"
        if self.down > 4:
            return "Turnover on Downs"
        if self.distance >= 10 and self.ball_on + self.distance >= 100:
            return f"{down_names[self.down]} & Goal"
        return f"{down_names[self.down]} & {self.distance}"

    def get_field_position(self) -> str:
        """Get formatted field position string."""
        if self.ball_on <= 50:
            return f"OWN {self.ball_on}"
        else:
            return f"OPP {100 - self.ball_on}"

    def to_state(self) -> DriveState:
        """Convert to API response model."""
        return DriveState(
            drive_id=self.drive_id,
            down=self.down,
            distance=self.distance,
            ball_on=self.ball_on,
            status=self.status,
            plays=self.plays,
            total_yards=self.total_yards,
            down_and_distance=self.get_down_and_distance(),
            field_position=self.get_field_position(),
        )


class DriveManager:
    """Manages active drives."""

    def __init__(self):
        self._drives: Dict[str, Drive] = {}

    def start_drive(self, starting_yard_line: int = 25) -> Drive:
        """Start a new drive."""
        drive_id = str(uuid4())[:8]
        drive = Drive(
            drive_id=drive_id,
            down=1,
            distance=10,
            ball_on=starting_yard_line,
        )
        self._drives[drive_id] = drive
        return drive

    def get_drive(self, drive_id: str) -> Optional[Drive]:
        """Get a drive by ID."""
        return self._drives.get(drive_id)

    def update_after_play(self, drive: Drive, yards_gained: int, is_turnover: bool = False) -> None:
        """Update drive state after a play."""
        if is_turnover:
            drive.status = DriveStatus.TURNOVER
            return

        # Update field position
        drive.ball_on += yards_gained
        drive.total_yards += yards_gained

        # Check for touchdown
        if drive.ball_on >= 100:
            drive.ball_on = 100
            drive.status = DriveStatus.TOUCHDOWN
            return

        # Check for safety (pushed back into own end zone)
        if drive.ball_on <= 0:
            drive.ball_on = 1
            drive.status = DriveStatus.SAFETY
            return

        # Update down and distance
        drive.distance -= yards_gained

        if drive.distance <= 0:
            # First down!
            drive.down = 1
            drive.distance = min(10, 100 - drive.ball_on)  # Goal to go if inside 10
        else:
            drive.down += 1
            if drive.down > 4:
                drive.status = DriveStatus.TURNOVER_ON_DOWNS

    def select_defense(self, drive: Drive) -> Dict[str, Any]:
        """Auto-select defensive play based on situation."""
        # Simple situational defense selection
        if drive.distance <= 3:
            # Short yardage - expect run
            return {
                "coverage": "cover_1",
                "front": "goal_line",
                "description": "Cover 1 Goal Line - expecting run"
            }
        elif drive.distance >= 7:
            # Passing situation
            if drive.down >= 3:
                # 3rd/4th and long - aggressive
                return {
                    "coverage": "cover_3",
                    "front": "nickel",
                    "description": "Cover 3 Nickel - pass rush"
                }
            else:
                return {
                    "coverage": "cover_2",
                    "front": "4-3",
                    "description": "Cover 2 Zone - balanced"
                }
        else:
            # Medium distance - balanced
            return {
                "coverage": "cover_3",
                "front": "4-3",
                "description": "Cover 3 Base - balanced"
            }


# Global drive manager
drive_manager = DriveManager()


# =============================================================================
# REST Endpoints
# =============================================================================

@router.post("/drive/start", response_model=DriveState)
async def start_drive(request: StartDriveRequest) -> DriveState:
    """Start a new drive."""
    drive = drive_manager.start_drive(request.starting_yard_line)
    return drive.to_state()


@router.get("/drive/{drive_id}", response_model=DriveState)
async def get_drive(drive_id: str) -> DriveState:
    """Get current drive state."""
    drive = drive_manager.get_drive(drive_id)
    if not drive:
        raise HTTPException(404, "Drive not found")
    return drive.to_state()


@router.post("/drive/play")
async def run_drive_play(request: RunPlayRequest) -> Dict[str, Any]:
    """Run a play within a drive and return results."""
    drive = drive_manager.get_drive(request.drive_id)
    if not drive:
        raise HTTPException(404, "Drive not found")

    if drive.status != DriveStatus.ACTIVE:
        raise HTTPException(400, f"Drive is not active: {drive.status}")

    # Get auto-selected defense
    defense_call = drive_manager.select_defense(drive)

    # Create session config based on play type
    if request.play_type == "run":
        concept_name = request.run_concept or "inside_zone_right"
        # Use the blocking scenario infrastructure to set up a run play
        config = SimulationConfig(
            offense=[],  # Will be populated by create_run_play_session
            defense=[],
            is_run_play=True,
            run_concept=concept_name,
        )
        session = await create_run_play_session(concept_name, defense_call["coverage"])
    else:
        # Pass play
        concept_name = request.concept or "mesh"
        config = SimulationConfig(
            offense=[],
            defense=[],
            is_run_play=False,
        )
        session = await create_pass_play_session(concept_name, defense_call["coverage"])

    # Run the play to completion
    result = await run_play_to_completion(session)

    # Calculate yards gained
    yards_gained = result.get("yards_gained", 0)
    is_turnover = result.get("is_turnover", False)
    is_touchdown = result.get("is_touchdown", False)

    # Record play result
    play_result = PlayResultInfo(
        yards_gained=yards_gained,
        play_type=request.play_type,
        description=result.get("description", f"Gain of {yards_gained} yards"),
        is_first_down=False,  # Will be set after update
        is_touchdown=is_touchdown,
        is_turnover=is_turnover,
    )

    # Update drive state
    old_down = drive.down
    drive_manager.update_after_play(drive, yards_gained, is_turnover)

    # Check if first down was achieved
    if drive.down == 1 and old_down != 1 and drive.status == DriveStatus.ACTIVE:
        play_result.is_first_down = True

    drive.plays.append(play_result)

    return {
        "play_result": play_result.model_dump(),
        "drive_state": drive.to_state().model_dump(),
        "defense_called": defense_call,
        "session_id": str(session.session_id),  # For replay/visualization
    }


async def create_run_play_session(concept_name: str, coverage: str) -> V2SimSession:
    """Create a session for a run play."""
    # Get run concept
    run_concept = get_run_concept(concept_name)
    if not run_concept:
        run_concept = get_run_concept("inside_zone_right")

    # Standard offensive personnel
    offense_configs = [
        PlayerConfig(name="QB", position="QB", alignment_x=0, alignment_y=-3.5),
        PlayerConfig(name="RB", position="RB", alignment_x=-0.5, alignment_y=-4.5, speed=88, elusiveness=82),
        PlayerConfig(name="LT", position="LT", alignment_x=-3.0, alignment_y=-0.5, block_power=80, strength=82),
        PlayerConfig(name="LG", position="LG", alignment_x=-1.5, alignment_y=-0.5, block_power=78, strength=80),
        PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-0.5, block_power=76, strength=78),
        PlayerConfig(name="RG", position="RG", alignment_x=1.5, alignment_y=-0.5, block_power=78, strength=80),
        PlayerConfig(name="RT", position="RT", alignment_x=3.0, alignment_y=-0.5, block_power=78, strength=80),
        PlayerConfig(name="WR1", position="WR", alignment_x=-15, alignment_y=0),
        PlayerConfig(name="WR2", position="WR", alignment_x=15, alignment_y=0),
        PlayerConfig(name="TE", position="TE", alignment_x=4.5, alignment_y=-0.5, block_power=72),
    ]

    # Standard 4-3 defense
    defense_configs = [
        PlayerConfig(name="LDE", position="DE", alignment_x=-3.5, alignment_y=0.5, pass_rush=78, strength=78),
        PlayerConfig(name="LDT", position="DT", alignment_x=-1.0, alignment_y=0.5, pass_rush=76, strength=82),
        PlayerConfig(name="RDT", position="DT", alignment_x=1.0, alignment_y=0.5, pass_rush=76, strength=82),
        PlayerConfig(name="RDE", position="DE", alignment_x=3.5, alignment_y=0.5, pass_rush=80, strength=78),
        PlayerConfig(name="WLB", position="OLB", alignment_x=-5, alignment_y=3.5, tackling=78, speed=82),
        PlayerConfig(name="MLB", position="MLB", alignment_x=0, alignment_y=4.0, tackling=82, play_recognition=80),
        PlayerConfig(name="SLB", position="OLB", alignment_x=5, alignment_y=3.5, tackling=78, speed=82),
        PlayerConfig(name="LCB", position="CB", alignment_x=-15, alignment_y=5, man_coverage=78, speed=88),
        PlayerConfig(name="RCB", position="CB", alignment_x=15, alignment_y=5, man_coverage=78, speed=88),
        PlayerConfig(name="FS", position="FS", alignment_x=0, alignment_y=15, zone_coverage=80, speed=86),
        PlayerConfig(name="SS", position="SS", alignment_x=5, alignment_y=10, tackling=80, speed=84),
    ]

    config = SimulationConfig(
        offense=offense_configs,
        defense=defense_configs,
        is_run_play=True,
        run_concept=concept_name,
        max_time=10.0,
    )

    return session_manager.create_session(config)


async def create_pass_play_session(concept_name: str, coverage: str) -> V2SimSession:
    """Create a session for a pass play using concept routes with proper read_order."""
    from huddle.simulation.v2.plays.matchup import create_matchup

    # Create matchup to get proper routes with read_order
    matchup = create_matchup(concept_name, coverage)
    if not matchup:
        # Fallback to generic session if concept/coverage not found
        offense_configs = [
            PlayerConfig(name="QB", position="QB", alignment_x=0, alignment_y=-5, throw_power=88, throw_accuracy=85),
            PlayerConfig(name="RB", position="RB", alignment_x=1.5, alignment_y=-4, speed=85),
            PlayerConfig(name="LT", position="LT", alignment_x=-3.0, alignment_y=-0.5, block_power=80, strength=82),
            PlayerConfig(name="LG", position="LG", alignment_x=-1.5, alignment_y=-0.5, block_power=78, strength=80),
            PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-0.5, block_power=76, strength=78),
            PlayerConfig(name="RG", position="RG", alignment_x=1.5, alignment_y=-0.5, block_power=78, strength=80),
            PlayerConfig(name="RT", position="RT", alignment_x=3.0, alignment_y=-0.5, block_power=78, strength=80),
            PlayerConfig(name="X", position="WR", alignment_x=-15, alignment_y=0, route_running=88, speed=90),
            PlayerConfig(name="Z", position="WR", alignment_x=12, alignment_y=0, route_running=85, speed=88),
            PlayerConfig(name="Slot", position="WR", alignment_x=5, alignment_y=-0.5, route_running=82, speed=86),
            PlayerConfig(name="TE", position="TE", alignment_x=4.5, alignment_y=-0.5, route_running=72, catching=78),
        ]
        defense_configs = [
            PlayerConfig(name="LDE", position="DE", alignment_x=-3.5, alignment_y=0.5, pass_rush=82, strength=78),
            PlayerConfig(name="LDT", position="DT", alignment_x=-1.0, alignment_y=0.5, pass_rush=78, strength=82),
            PlayerConfig(name="RDT", position="DT", alignment_x=1.0, alignment_y=0.5, pass_rush=78, strength=82),
            PlayerConfig(name="RDE", position="DE", alignment_x=3.5, alignment_y=0.5, pass_rush=84, strength=78),
            PlayerConfig(name="WLB", position="OLB", alignment_x=-5, alignment_y=3.5, zone_coverage=75, speed=82),
            PlayerConfig(name="MLB", position="MLB", alignment_x=0, alignment_y=4.0, zone_coverage=72, play_recognition=80),
            PlayerConfig(name="SLB", position="OLB", alignment_x=5, alignment_y=3.5, zone_coverage=75, speed=82),
            PlayerConfig(name="LCB", position="CB", alignment_x=-15, alignment_y=5, man_coverage=82, speed=90),
            PlayerConfig(name="RCB", position="CB", alignment_x=12, alignment_y=5, man_coverage=80, speed=88),
            PlayerConfig(name="FS", position="FS", alignment_x=0, alignment_y=18, zone_coverage=82, speed=88),
            PlayerConfig(name="SS", position="SS", alignment_x=8, alignment_y=12, zone_coverage=78, speed=86),
        ]
        config = SimulationConfig(
            offense=offense_configs,
            defense=defense_configs,
            is_run_play=False,
            max_time=10.0,
        )
        return session_manager.create_session(config)

    # Build offense with proper routes and read_order from concept
    receiver_position_map = {
        "x": "WR", "y": "WR", "z": "WR",
        "slot_l": "WR", "slot_r": "WR",
        "h": "TE", "t": "TE",
        "f": "RB", "b": "RB", "rb": "RB",
    }

    receiver_id_to_name: Dict[str, str] = {}

    offense_configs = [
        PlayerConfig(name="QB", position="QB", alignment_x=0, alignment_y=-5, throw_power=88, throw_accuracy=85),
        PlayerConfig(name="LT", position="LT", alignment_x=-3.0, alignment_y=-0.5, block_power=80, strength=82),
        PlayerConfig(name="LG", position="LG", alignment_x=-1.5, alignment_y=-0.5, block_power=78, strength=80),
        PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-0.5, block_power=76, strength=78),
        PlayerConfig(name="RG", position="RG", alignment_x=1.5, alignment_y=-0.5, block_power=78, strength=80),
        PlayerConfig(name="RT", position="RT", alignment_x=3.0, alignment_y=-0.5, block_power=78, strength=80),
    ]

    for r in matchup.receivers:
        pos_key = r["position"].lower()
        position = receiver_position_map.get(pos_key, "WR")
        receiver_name = r["name"]
        receiver_id_to_name[r["id"]] = receiver_name

        offense_configs.append(PlayerConfig(
            name=receiver_name,
            position=position,
            alignment_x=r["x"],
            alignment_y=r.get("y", 0),
            route_type=r["route_type"],
            read_order=r.get("read_order", 1),
            is_hot_route=r.get("hot_route", False),
            route_running=85,
            speed=88,
        ))

    # Build defense from scheme
    defender_position_map = {
        "cb1": "CB", "cb2": "CB", "cb3": "CB", "slot_cb": "CB", "ncb": "CB",
        "fs": "FS", "ss": "SS", "s": "SS",
        "mlb": "MLB", "wlb": "OLB", "slb": "OLB", "olb": "OLB", "ilb": "ILB",
        "de": "DE", "dt": "DT", "nt": "NT",
    }

    # 4-3 front default
    defense_configs = [
        PlayerConfig(name="LDE", position="DE", alignment_x=-3.5, alignment_y=0.5, pass_rush=82, strength=78),
        PlayerConfig(name="LDT", position="DT", alignment_x=-1.0, alignment_y=0.5, pass_rush=78, strength=82),
        PlayerConfig(name="RDT", position="DT", alignment_x=1.0, alignment_y=0.5, pass_rush=78, strength=82),
        PlayerConfig(name="RDE", position="DE", alignment_x=3.5, alignment_y=0.5, pass_rush=84, strength=78),
    ]

    for d in matchup.defenders:
        pos_key = d["position"].lower()
        position = defender_position_map.get(pos_key, "CB")
        man_target_id = d.get("man_target_id")
        man_target_name = receiver_id_to_name.get(man_target_id) if man_target_id else None

        defense_configs.append(PlayerConfig(
            name=d["name"],
            position=position,
            alignment_x=d["x"],
            alignment_y=d["y"],
            coverage_type=d["coverage_type"],
            man_target=man_target_name,
            zone_type=d.get("zone_type"),
            speed=85,
        ))

    config = SimulationConfig(
        offense=offense_configs,
        defense=defense_configs,
        is_run_play=False,
        max_time=10.0,
    )

    return session_manager.create_session(config)


async def run_play_to_completion(session: V2SimSession) -> Dict[str, Any]:
    """Run a play session to completion and return results."""
    orch = session.orchestrator

    # Run pre-snap and snap
    orch._do_pre_snap_reads()
    orch._do_snap()

    # Run until play ends
    start_ball_y = orch.ball.pos.y if orch.ball else 0
    max_ticks = 200  # 10 seconds max

    for _ in range(max_ticks):
        dt = orch.clock.tick()
        orch._update_tick(dt)

        if orch.phase == PlayPhase.POST_PLAY:
            break

    # Calculate result
    end_ball_y = 0
    if orch.ball and orch.ball.carrier_id:
        carrier = orch._get_player(orch.ball.carrier_id)
        if carrier:
            end_ball_y = carrier.pos.y

    # Yards gained (positive = toward defense end zone)
    yards_gained = int(end_ball_y - start_ball_y)

    # Apply play-level blocking quality adjustment for runs
    # This creates realistic run distribution (stuffs, explosives, etc.)
    # NFL targets: 17% for 0 or loss, 11.6% for 10+, 2.5% for 20+, mean 4.5, median 3.0
    is_run_play = orch.config.is_run_play if orch.config else False
    if is_run_play:
        quality = getattr(orch, '_play_blocking_quality', 'average')
        if quality == "great":
            # 15% of plays: OL dominates → explosive potential
            # 20% of great plays (3% overall) are "breakaway" big plays
            if random.random() < 0.20:
                # Breakaway: RB breaks into secondary for 20+ yard gain
                bonus = random.randint(18, 35)
            else:
                # Normal great block: solid 3-11 yard gain (fills 7-9 good bucket)
                bonus = random.randint(3, 11)
            yards_gained += bonus
        elif quality == "poor":
            # 20% of plays: DL wins → stuff potential
            # Subtract 2-5 yards (creates losses and no-gains)
            penalty = random.randint(2, 5)
            yards_gained -= penalty
        else:
            # Average blocking (65%): variable outcome
            # Creates distribution across short (1-3), medium (4-6), and some good (7-9)
            # 10% chance of "congestion" (defense fills gaps quickly) → 0 or loss
            if random.random() < 0.10:
                # Congested play: gaps close fast, RB hits a wall
                adjustment = random.randint(-3, 0)
            else:
                # Normal average: spread across short, medium, and occasional good
                adjustment = random.randint(-2, 3)
            yards_gained += adjustment

    # Determine outcome
    outcome = orch._result_outcome or "unknown"
    is_turnover = outcome in ("interception", "fumble_lost")
    is_touchdown = yards_gained >= 100 - 25  # Simplified: if crossed goal line from own 25

    description = ""
    if outcome == "complete":
        description = f"Complete pass for {yards_gained} yards"
    elif outcome == "incomplete":
        description = "Incomplete pass"
        yards_gained = 0
    elif outcome == "interception":
        description = "INTERCEPTED!"
    elif outcome == "tackle":
        description = f"Run for {yards_gained} yards"
    elif outcome == "sack":
        description = f"SACKED for loss of {abs(yards_gained)} yards"
    else:
        description = f"Play result: {outcome}, {yards_gained} yards"

    return {
        "yards_gained": yards_gained,
        "outcome": outcome,
        "description": description,
        "is_turnover": is_turnover,
        "is_touchdown": is_touchdown,
    }


@router.post("/sessions", response_model=SessionInfo)
async def create_session(config: SimulationConfig) -> SessionInfo:
    """Create a new simulation session."""
    session = session_manager.create_session(config)
    return SessionInfo(
        session_id=str(session.session_id),
        tick_rate_ms=config.tick_rate_ms,
        max_time=config.max_time,
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session state."""
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session ID")

    session = session_manager.get_session(uuid)
    if not session:
        raise HTTPException(404, "Session not found")

    return session_state_to_dict(session)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session."""
    try:
        uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session ID")

    session_manager.remove_session(uuid)
    return {"status": "deleted"}


@router.get("/routes")
async def list_routes() -> List[dict]:
    """List available route types."""
    return [
        {
            "type": rt.value,
            "name": ROUTE_LIBRARY[rt].name,
            "break_depth": ROUTE_LIBRARY[rt].break_depth,
            "total_depth": ROUTE_LIBRARY[rt].total_depth,
            "route_side": ROUTE_LIBRARY[rt].route_side,
            "is_quick": ROUTE_LIBRARY[rt].is_quick_route,
        }
        for rt in RouteType
        if rt in ROUTE_LIBRARY
    ]


@router.get("/zones")
async def list_zones() -> List[dict]:
    """List available zone types."""
    return [
        {
            "type": zt.value,
            "min_x": zone.min_x,
            "max_x": zone.max_x,
            "min_y": zone.min_y,
            "max_y": zone.max_y,
            "anchor_x": zone.anchor.x,
            "anchor_y": zone.anchor.y,
            "is_deep": zone.is_deep,
        }
        for zt, zone in ZONE_BOUNDARIES.items()
    ]


@router.get("/concepts")
async def list_concepts() -> List[dict]:
    """List available play concepts."""
    return [
        {
            "name": name,
            "display_name": concept.name,
            "description": concept.description,
            "formation": concept.formation.value,
            "timing": concept.timing,
            "coverage_beaters": concept.coverage_beaters,
            "route_count": len(concept.routes),
        }
        for name, concept in CONCEPT_LIBRARY.items()
    ]


@router.get("/schemes")
async def list_schemes() -> List[dict]:
    """List available defensive schemes."""
    return [
        {
            "name": name,
            "display_name": scheme.name,
            "scheme_type": scheme.scheme_type.value,
            "description": scheme.description,
            "strengths": scheme.strengths,
            "weaknesses": scheme.weaknesses,
        }
        for name, scheme in SCHEME_LIBRARY.items()
    ]


@router.get("/matchups")
async def list_matchups() -> List[dict]:
    """List classic matchup scenarios."""
    return [
        {
            "concept": concept,
            "scheme": scheme,
            "description": describe_matchup(concept, scheme),
        }
        for concept, scheme in CLASSIC_MATCHUPS
    ]


@router.get("/run-concepts")
async def list_run_concepts_endpoint() -> List[dict]:
    """List available run concepts."""
    return [
        {
            "name": name,
            "display_name": concept.name,
            "description": concept.description,
            "scheme": concept.scheme.value,
            "play_side": concept.play_side,
            "aiming_point": concept.aiming_point.value,
            "mesh_depth": concept.mesh_depth,
            "handoff_timing": concept.handoff_timing,
        }
        for name, concept in RUN_CONCEPT_LIBRARY.items()
    ]


@router.get("/blocking-scenarios")
async def list_blocking_scenarios() -> List[dict]:
    """List available blocking test scenarios.

    These scenarios are designed to test and visualize specific blocking behaviors,
    from simple 1v1 interactions to full line play.
    """
    return [
        {
            "id": scenario_id,
            "name": scenario["name"],
            "tier": scenario["tier"],
            "description": scenario["description"],
            "expected": scenario["expected"],
            "offense_count": len(scenario["offense"]),
            "defense_count": len(scenario["defense"]),
            "run_concept": scenario.get("run_concept"),
        }
        for scenario_id, scenario in BLOCKING_SCENARIOS.items()
    ]


class BlockingScenarioRequest(BaseModel):
    """Request to create a blocking scenario session."""
    scenario_id: str
    tick_rate_ms: int = 50
    max_time: float = 3.0


@router.post("/blocking-scenario", response_model=SessionInfo)
async def create_blocking_scenario_session(request: BlockingScenarioRequest) -> SessionInfo:
    """Create a simulation session from a blocking test scenario.

    This is designed for testing and visualizing specific blocking behaviors.
    """
    scenario = BLOCKING_SCENARIOS.get(request.scenario_id)
    if not scenario:
        available = list(BLOCKING_SCENARIOS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario_id: '{request.scenario_id}'. Available: {available}"
        )

    # Build offense players
    offense = []
    for p in scenario["offense"]:
        player_config = PlayerConfig(
            name=p["name"],
            position=p["position"],
            alignment_x=p["x"],
            alignment_y=p.get("y", 0),
            block_power=p.get("block_power", 75),
            block_finesse=p.get("block_finesse", 75),
            strength=p.get("strength", 75),
            speed=p.get("speed", 75),
            acceleration=p.get("acceleration", 75),
        )
        offense.append(player_config)

    # Build defense players
    defense = []
    for p in scenario["defense"]:
        player_config = PlayerConfig(
            name=p["name"],
            position=p["position"],
            alignment_x=p["x"],
            alignment_y=p.get("y", 0.5),
            pass_rush=p.get("pass_rush", 75),
            strength=p.get("strength", 75),
            tackling=p.get("tackling", 75),
            play_recognition=p.get("play_recognition", 75),
        )
        defense.append(player_config)

    # Determine if this is a run play (explicit flag or has run_concept)
    run_concept = scenario.get("run_concept")
    is_run_play = scenario.get("is_run_play", run_concept is not None)

    config = SimulationConfig(
        offense=offense,
        defense=defense,
        tick_rate_ms=request.tick_rate_ms,
        max_time=request.max_time,
        is_run_play=is_run_play,
        run_concept=run_concept,
    )

    # Create session
    if is_run_play and run_concept:
        run_concept_obj = get_run_concept(run_concept)
        if run_concept_obj:
            session = _create_run_session(config, run_concept_obj)
        else:
            session = session_manager.create_session(config)
    else:
        session = session_manager.create_session(config)

    return SessionInfo(
        session_id=str(session.session_id),
        tick_rate_ms=config.tick_rate_ms,
        max_time=config.max_time,
    )


class MatchupRequest(BaseModel):
    """Request to create a matchup session."""
    concept: str
    scheme: str
    tick_rate_ms: int = 50
    max_time: float = 6.0
    is_run_play: bool = False


async def _create_run_matchup_session(request: MatchupRequest) -> SessionInfo:
    """Create a run play simulation session.

    Sets up a run play with OL, RB (and FB if needed), vs defense.
    """
    # get_run_concept handles partial names like "inside_zone" -> "inside_zone_right"
    run_concept = get_run_concept(request.concept)

    if not run_concept:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid run concept: '{request.concept}'. Available: {list_run_concepts()}"
        )

    # Use the concept's name which is the resolved full name
    concept_name = run_concept.name.lower().replace(" ", "_")

    # Build offense: QB, OL, RB (and FB for power/counter)
    offense = [
        PlayerConfig(
            name="QB",
            position="QB",
            alignment_x=0,
            alignment_y=-3.5,  # Closer for run play handoff
        ),
        # Standard OL - realistic spacing (~1.5 yards apart)
        PlayerConfig(name="LT", position="LT", alignment_x=-3.0, alignment_y=-0.5, block_power=80, block_finesse=75),
        PlayerConfig(name="LG", position="LG", alignment_x=-1.5, alignment_y=-0.5, block_power=82, block_finesse=72),
        PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-0.5, block_power=78, block_finesse=78, awareness=85),
        PlayerConfig(name="RG", position="RG", alignment_x=1.5, alignment_y=-0.5, block_power=82, block_finesse=72),
        PlayerConfig(name="RT", position="RT", alignment_x=3.0, alignment_y=-0.5, block_power=78, block_finesse=77),
        # RB - offset behind guard
        PlayerConfig(
            name="RB",
            position="RB",
            alignment_x=-0.5,
            alignment_y=-4.5,
            speed=90,
            acceleration=88,
            agility=88,
            elusiveness=85,
            vision=82,
        ),
    ]

    # Add FB for power/counter schemes
    if run_concept.scheme.value in ("power", "counter"):
        offense.append(PlayerConfig(
            name="FB",
            position="FB",
            alignment_x=0.5,
            alignment_y=-3.0,
            speed=78,
            acceleration=80,
            strength=85,
            block_power=82,
        ))

    # Build defense based on scheme
    scheme_lower = request.scheme.lower().replace(" ", "_")
    is_34_front = scheme_lower in ("cover_1", "cover_0", "3_4")

    if is_34_front:
        # 3-4 front: 2 DE (5-tech) + 1 NT (0-tech) + 4 LBs
        # DEs align on outside shoulder of tackles, NT head-up on center
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=get_technique_x("5", "left"), alignment_y=0.5, pass_rush=82, strength=80),
            PlayerConfig(name="NT", position="NT", alignment_x=get_technique_x("0"), alignment_y=0.5, pass_rush=75, strength=88),
            PlayerConfig(name="RDE", position="DE", alignment_x=get_technique_x("5", "right"), alignment_y=0.5, pass_rush=82, strength=80),
            # LBs - stacked behind gaps
            PlayerConfig(name="LOLB", position="OLB", alignment_x=-4.0, alignment_y=3.5, tackling=82, play_recognition=80),
            PlayerConfig(name="LILB", position="ILB", alignment_x=-1.0, alignment_y=3.5, tackling=85, play_recognition=82),
            PlayerConfig(name="RILB", position="ILB", alignment_x=1.0, alignment_y=3.5, tackling=85, play_recognition=82),
            PlayerConfig(name="ROLB", position="OLB", alignment_x=4.0, alignment_y=3.5, tackling=82, play_recognition=80),
        ]
    else:
        # 4-3 Under front (common vs run):
        # LDE: 5-tech (outside LT), LDT: 3-tech (outside LG), RDT: 1-tech (shade C), RDE: 5-tech (outside RT)
        # This creates a strong side (left) and weak side (right)
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=get_technique_x("5", "left"), alignment_y=0.5, pass_rush=84, strength=78),
            PlayerConfig(name="LDT", position="DT", alignment_x=get_technique_x("3", "left"), alignment_y=0.5, pass_rush=76, strength=85),
            PlayerConfig(name="RDT", position="DT", alignment_x=get_technique_x("1", "right"), alignment_y=0.5, pass_rush=76, strength=85),
            PlayerConfig(name="RDE", position="DE", alignment_x=get_technique_x("5", "right"), alignment_y=0.5, pass_rush=84, strength=78),
            # LBs - off the ball, reading gaps
            PlayerConfig(name="WLB", position="OLB", alignment_x=-3.0, alignment_y=4.0, tackling=82, play_recognition=80),
            PlayerConfig(name="MLB", position="MLB", alignment_x=0, alignment_y=4.5, tackling=85, play_recognition=85),
            PlayerConfig(name="SLB", position="OLB", alignment_x=3.0, alignment_y=4.0, tackling=82, play_recognition=80),
        ]

    config = SimulationConfig(
        offense=offense,
        defense=defense,
        tick_rate_ms=request.tick_rate_ms,
        max_time=request.max_time,
        is_run_play=True,
        run_concept=concept_name,
    )

    # Create session with run play config
    session = _create_run_session(config, run_concept)
    return SessionInfo(
        session_id=str(session.session_id),
        tick_rate_ms=config.tick_rate_ms,
        max_time=config.max_time,
    )


def _create_run_session(config: SimulationConfig, run_concept) -> V2SimSession:
    """Create a session configured for run play.

    The config must have is_run_play=True and run_concept set.
    """
    session_id = uuid4()
    concept_name = config.run_concept

    # Create orchestrator
    orchestrator = Orchestrator()

    # Build offensive players
    offense_players = []
    rb_id = None

    for pc in config.offense:
        player = session_manager._create_player(pc, Team.OFFENSE)
        offense_players.append(player)

        if pc.position.upper() in ("RB", "HB"):
            rb_id = player.id

        # Register brain
        brain = session_manager._get_brain_for_position(player.position, Team.OFFENSE)
        if brain:
            orchestrator.register_brain(player.id, brain)

    # Build defensive players
    defense_players = []

    for pc in config.defense:
        player = session_manager._create_player(pc, Team.DEFENSE)
        defense_players.append(player)

        # Register brain
        brain = session_manager._get_brain_for_position(player.position, Team.DEFENSE)
        if brain:
            orchestrator.register_brain(player.id, brain)

    # Register ballcarrier brain
    orchestrator.register_brain("ballcarrier", ballcarrier_brain)

    # Create run play config
    # Use SHOTGUN dropback (2 yards) so QB stays close to RB for handoff
    play_config = PlayConfig(
        routes={},  # No routes for run plays
        man_assignments={},
        zone_assignments={},
        max_duration=config.max_time,
        dropback_type=DropbackType.SHOTGUN,  # Minimal dropback for handoff
        is_run_play=True,
        run_concept=concept_name,
        handoff_timing=run_concept.handoff_timing,
        ball_carrier_id=rb_id,
    )

    # Setup the play
    orchestrator.setup_play(offense_players, defense_players, play_config)

    session = V2SimSession(
        session_id=session_id,
        config=config,
        orchestrator=orchestrator,
        offense_players=offense_players,
        defense_players=defense_players,
    )

    session_manager.sessions[session_id] = session
    return session


@router.post("/matchup", response_model=SessionInfo)
async def create_matchup_session(request: MatchupRequest) -> SessionInfo:
    """Create a simulation session from a concept vs scheme matchup.

    This is a convenience endpoint that converts concept/scheme names
    into a full SimulationConfig with all players and creates a session.

    For run plays (is_run_play=True), the concept should be a run concept name
    like "inside_zone", "outside_zone", "power", "counter", etc.

    Auto-detects run plays: if concept matches a run concept name, it's treated as a run.
    """
    # Auto-detect run plays from concept name
    # get_run_concept now handles partial names like "inside_zone" -> "inside_zone_right"
    run_concept_check = get_run_concept(request.concept)
    is_run = request.is_run_play or (run_concept_check is not None)

    print(f"[MATCHUP] concept={request.concept}, is_run_play={request.is_run_play}, "
          f"run_concept_found={run_concept_check is not None}, final_is_run={is_run}")

    # Handle run plays
    if is_run:
        return await _create_run_matchup_session(request)

    matchup = create_matchup(request.concept, request.scheme)
    if not matchup:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid matchup: concept '{request.concept}' or scheme '{request.scheme}' not found"
        )

    # Build offense players from matchup receivers
    offense = [
        # Add QB
        PlayerConfig(
            name="QB",
            position="QB",
            alignment_x=0,
            alignment_y=-5,
        ),
        # Standard OL - realistic 1.5 yard spacing, slight setback for pass protection
        PlayerConfig(name="LT", position="LT", alignment_x=-3.0, alignment_y=-0.5, block_power=80, block_finesse=75),
        PlayerConfig(name="LG", position="LG", alignment_x=-1.5, alignment_y=-0.5, block_power=82, block_finesse=72),
        PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-0.5, block_power=78, block_finesse=78, awareness=85),
        PlayerConfig(name="RG", position="RG", alignment_x=1.5, alignment_y=-0.5, block_power=82, block_finesse=72),
        PlayerConfig(name="RT", position="RT", alignment_x=3.0, alignment_y=-0.5, block_power=78, block_finesse=77),
    ]

    # Map receiver positions (X, Y, Z, H, F, slot) to actual positions
    receiver_position_map = {
        "x": "WR", "y": "WR", "z": "WR",  # X, Y, Z are typically WRs
        "slot_l": "WR", "slot_r": "WR",    # Slot receivers are WRs
        "h": "TE", "t": "TE",              # H-back, Tight end
        "f": "RB", "b": "RB", "rb": "RB",  # Fullback, Running back
    }

    # Build a map from matchup receiver IDs (like "wr1") to receiver names (like "X")
    # This is needed to properly link man coverage assignments
    receiver_id_to_name: Dict[str, str] = {}

    for r in matchup.receivers:
        pos_key = r["position"].lower()
        position = receiver_position_map.get(pos_key, "WR")
        receiver_name = r["name"]
        receiver_id_to_name[r["id"]] = receiver_name  # Map "wr1" -> "X"

        offense.append(PlayerConfig(
            name=receiver_name,
            position=position,
            alignment_x=r["x"],
            alignment_y=r.get("y", 0),
            route_type=r["route_type"],
            read_order=r.get("read_order", 1),
            is_hot_route=r.get("hot_route", False),
        ))

    # Map defender positions to actual positions
    defender_position_map = {
        "cb1": "CB", "cb2": "CB", "cb3": "CB", "slot_cb": "CB", "ncb": "CB",
        "fs": "FS", "ss": "SS", "s": "SS",
        "mlb": "MLB", "wlb": "OLB", "slb": "OLB", "olb": "OLB", "ilb": "ILB",
        "de": "DE", "dt": "DT", "nt": "NT",
    }

    # Build defense players from matchup defenders
    # Start with DL based on scheme (4-3 default, 3-4 for certain schemes)
    scheme_lower = request.scheme.lower().replace(" ", "_")
    is_34_front = scheme_lower in ("cover_1", "cover_0", "3_4")  # 3-4 fronts

    if is_34_front:
        # 3-4 front: 2 DE (5-tech) + 1 NT (0-tech)
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=get_technique_x("5", "left"), alignment_y=0.5, pass_rush=82, strength=80),
            PlayerConfig(name="NT", position="NT", alignment_x=get_technique_x("0"), alignment_y=0.5, pass_rush=75, strength=88),
            PlayerConfig(name="RDE", position="DE", alignment_x=get_technique_x("5", "right"), alignment_y=0.5, pass_rush=82, strength=80),
        ]
    else:
        # 4-3 front: DEs at 5-tech (outside shoulder of tackle), DTs at 3-tech (B gap)
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=get_technique_x("5", "left"), alignment_y=0.5, pass_rush=84, strength=78),
            PlayerConfig(name="LDT", position="DT", alignment_x=get_technique_x("3", "left"), alignment_y=0.5, pass_rush=76, strength=85),
            PlayerConfig(name="RDT", position="DT", alignment_x=get_technique_x("3", "right"), alignment_y=0.5, pass_rush=76, strength=85),
            PlayerConfig(name="RDE", position="DE", alignment_x=get_technique_x("5", "right"), alignment_y=0.5, pass_rush=84, strength=78),
        ]

    # Add coverage defenders from scheme
    for d in matchup.defenders:
        pos_key = d["position"].lower()
        position = defender_position_map.get(pos_key, "CB")

        # Translate man_target_id (like "wr1") to actual receiver name (like "X")
        man_target_id = d.get("man_target_id")
        man_target_name = receiver_id_to_name.get(man_target_id) if man_target_id else None

        defense.append(PlayerConfig(
            name=d["name"],
            position=position,
            alignment_x=d["x"],
            alignment_y=d["y"],
            coverage_type=d["coverage_type"],
            man_target=man_target_name,  # Use translated name, not raw ID
            zone_type=d.get("zone_type"),
        ))

    config = SimulationConfig(
        offense=offense,
        defense=defense,
        tick_rate_ms=request.tick_rate_ms,
        max_time=request.max_time,
    )

    session = session_manager.create_session(config)
    return SessionInfo(
        session_id=str(session.session_id),
        tick_rate_ms=config.tick_rate_ms,
        max_time=config.max_time,
    )


# =============================================================================
# WebSocket
# =============================================================================

@router.websocket("/ws/{session_id}")
async def v2_sim_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket for real-time simulation updates.

    Client messages:
    - start: Start simulation
    - pause: Pause simulation
    - resume: Resume simulation
    - reset: Reset to initial state
    - step: Advance one tick (when paused)
    - sync: Request full state sync

    Server messages:
    - state_sync: Full state on connect/request
    - tick: Each simulation tick with player states
    - event: Simulation events
    - complete: Simulation finished
    - error: Error message
    """
    await websocket.accept()

    try:
        uuid = UUID(session_id)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Invalid session ID"})
        await websocket.close()
        return

    session = session_manager.get_session(uuid)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    # Send initial state
    await websocket.send_json({
        "type": "state_sync",
        "payload": session_state_to_dict(session),
    })

    # Track events for this session
    pending_events: List[Event] = []

    def on_event(event: Event):
        pending_events.append(event)

    session.orchestrator.event_bus.subscribe_all(on_event)

    def run_tick() -> Tuple[bool, Optional[dict]]:
        """Run a single tick and return (is_complete, catch_result)."""
        orchestrator = session.orchestrator

        # Tick the clock
        dt = orchestrator.clock.tick()

        # Update all players via orchestrator's internal method
        orchestrator._update_tick(dt)

        # Update session tracking
        if orchestrator.ball.carrier_id:
            session.ball_carrier_id = orchestrator.ball.carrier_id

        # Check for play completion
        is_complete = orchestrator._should_stop()

        # Update play outcome based on phase
        if orchestrator.phase == PlayPhase.POST_PLAY:
            is_complete = True
            # Determine outcome from events
            events = orchestrator.event_bus.history
            for event in reversed(events):
                if event.type == EventType.CATCH:
                    # Don't set COMPLETE yet - RAC phase should continue
                    # Outcome will be set when play truly ends (tackle/TD/OOB)
                    # Just track the ball carrier for pursuit visualization
                    session.ball_carrier_id = event.player_id
                    # Keep IN_PROGRESS to let RAC continue
                    break
                elif event.type == EventType.INCOMPLETE:
                    session.play_outcome = PlayOutcome.INCOMPLETE
                    break
                elif event.type == EventType.INTERCEPTION:
                    session.play_outcome = PlayOutcome.INTERCEPTION
                    break
                elif event.type == EventType.TACKLE:
                    # Check if this was a completed pass that ended in tackle (YAC)
                    # If so, keep outcome as COMPLETE, not TACKLED
                    was_pass_play = any(e.type == EventType.CATCH for e in events)
                    if was_pass_play:
                        session.play_outcome = PlayOutcome.COMPLETE
                    else:
                        session.play_outcome = PlayOutcome.TACKLED
                    # Position is stored as tuple (x, y), not separate x/y keys
                    pos = event.data.get("position")
                    if pos:
                        session.tackle_position = Vec2(pos[0], pos[1])
                    # Capture the tackler's ID
                    tackler = event.data.get("player_id")
                    if tackler:
                        session.tackler_id = str(tackler)
                    break
                elif event.type == EventType.SACK:
                    session.play_outcome = PlayOutcome.SACK
                    break
                elif event.type == EventType.TOUCHDOWN:
                    session.play_outcome = PlayOutcome.TOUCHDOWN
                    break

        return is_complete, None

    async def run_simulation():
        """Run simulation loop."""
        orchestrator = session.orchestrator

        # Debug: print run play config
        orch_config = orchestrator.config
        print(f"[START] orchestrator.config.is_run_play={orch_config.is_run_play if orch_config else 'None'}, "
              f"run_concept={orch_config.run_concept if orch_config else 'None'}, "
              f"_run_concept={orchestrator._run_concept is not None}")

        # If play is already over (POST_PLAY), don't run - require reset
        if orchestrator.phase == PlayPhase.POST_PLAY:
            session.is_complete = True
            return

        session.is_running = True
        session.is_paused = False
        session.is_complete = False
        # Only reset outcome if we're starting fresh (pre-snap)
        # Don't reset if resuming mid-play (e.g., AFTER_CATCH for RAC)
        if orchestrator.phase == PlayPhase.PRE_SNAP:
            session.play_outcome = PlayOutcome.IN_PROGRESS

        # Enable trace systems for debugging/analysis
        enable_trace(True)
        get_trace_system().enable(True)

        # Only do pre-snap/snap if we haven't already
        # This allows resuming mid-play (e.g., continuing RAC after catch)
        if orchestrator.phase == PlayPhase.PRE_SNAP:
            # Execute pre-snap reads
            orchestrator._do_pre_snap_reads()
            # Snap
            orchestrator._do_snap()

        while session.is_running and not session.is_complete:
            if session.is_paused:
                await asyncio.sleep(0.05)
                continue

            is_complete, _ = run_tick()
            session.is_complete = is_complete

            # Build tick payload
            players = [
                player_to_dict(p, orchestrator, session)
                for p in session.offense_players + session.defense_players
            ]

            # Get QB state for analysis panel
            qb_state_data = None
            qb_id = None
            for p in session.offense_players:
                if p.position == Position.QB:
                    qb_id = p.id
                    break
            if qb_id:
                try:
                    qb_state = get_qb_state(qb_id)
                    qb_state_data = {
                        "pressure_level": qb_state.pressure_level.value,
                        "current_read": qb_state.current_read,
                        "time_in_pocket": qb_state.time_in_pocket,
                        "dropback_complete": qb_state.dropback_complete,
                    }
                except Exception:
                    pass

            # Run play state
            is_run_play = orchestrator.config.is_run_play if orchestrator.config else False
            run_concept_name = orchestrator.config.run_concept if orchestrator.config else None
            designed_gap = None
            if orchestrator._run_concept:
                designed_gap = orchestrator._run_concept.aiming_point.value

            tick_data = {
                "type": "tick",
                "payload": {
                    "tick": orchestrator.clock.tick_count,
                    "time": orchestrator.clock.current_time,
                    "phase": orchestrator.phase.value,
                    "players": players,
                    "ball": ball_to_dict(orchestrator.ball, orchestrator.clock.current_time),
                    "play_outcome": session.play_outcome.value,
                    "ball_carrier_id": session.ball_carrier_id,
                    "qb_state": qb_state_data,
                    "qb_trace": get_trace(),
                    # Centralized player traces for SimAnalyzer
                    "player_traces": get_trace_system().to_dict_list(
                        get_trace_system().get_new_entries()
                    ),
                    # Include running state so frontend can show correct controls
                    "is_running": session.is_running,
                    "is_paused": session.is_paused,
                    "is_complete": session.is_complete,
                    # Run play state
                    "is_run_play": is_run_play,
                    "run_concept": run_concept_name,
                    "designed_gap": designed_gap,
                },
            }

            if session.tackle_position:
                tick_data["payload"]["tackle_position"] = {
                    "x": session.tackle_position.x,
                    "y": session.tackle_position.y,
                }

            if session.tackler_id:
                tick_data["payload"]["tackler_id"] = session.tackler_id

            if pending_events:
                tick_data["payload"]["events"] = [event_to_dict(e) for e in pending_events]
                pending_events.clear()

            try:
                await websocket.send_json(tick_data)
            except Exception:
                session.is_running = False
                break

            if session.is_complete:
                break

            # Sleep for tick rate
            await asyncio.sleep(session.config.tick_rate_ms / 1000.0)

        session.is_running = False
        session.is_complete = True

        try:
            await websocket.send_json({
                "type": "complete",
                "payload": session_state_to_dict(session),
            })
        except Exception:
            pass

    def reset_session():
        """Reset session to initial state."""
        # Re-create the session from config
        print(f"[RESET] config.is_run_play={session.config.is_run_play}, "
              f"config.run_concept={session.config.run_concept}")
        new_session = session_manager.create_session(session.config)

        # Update in-place
        session.orchestrator = new_session.orchestrator
        session.offense_players = new_session.offense_players
        session.defense_players = new_session.defense_players
        session.is_running = False
        session.is_paused = False
        session.is_complete = False
        session.play_outcome = PlayOutcome.IN_PROGRESS
        session.ball_carrier_id = None
        session.tackle_position = None
        session.tackler_id = None

        # Update session manager
        session_manager.sessions[session.session_id] = session

        # Re-subscribe to events
        pending_events.clear()
        session.orchestrator.event_bus.subscribe_all(on_event)

    simulation_task: Optional[asyncio.Task] = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "start":
                if not session.is_running:
                    simulation_task = asyncio.create_task(run_simulation())

            elif msg_type == "pause":
                session.is_paused = True

            elif msg_type == "resume":
                session.is_paused = False

            elif msg_type == "reset":
                session.is_running = False
                if simulation_task:
                    simulation_task.cancel()
                    try:
                        await simulation_task
                    except asyncio.CancelledError:
                        pass

                reset_session()

                await websocket.send_json({
                    "type": "state_sync",
                    "payload": session_state_to_dict(session),
                })

            elif msg_type == "step":
                if session.is_paused or not session.is_running:
                    orchestrator = session.orchestrator

                    # Start if first step
                    if orchestrator.phase == PlayPhase.PRE_SNAP:
                        orchestrator._do_pre_snap_reads()
                        orchestrator._do_snap()

                    is_complete, _ = run_tick()
                    session.is_complete = is_complete

                    players = [
                        player_to_dict(p, orchestrator, session)
                        for p in session.offense_players + session.defense_players
                    ]

                    tick_data = {
                        "type": "tick",
                        "payload": {
                            "tick": orchestrator.clock.tick_count,
                            "time": orchestrator.clock.current_time,
                            "phase": orchestrator.phase.value,
                            "players": players,
                            "ball": ball_to_dict(orchestrator.ball, orchestrator.clock.current_time),
                            "play_outcome": session.play_outcome.value,
                            "ball_carrier_id": session.ball_carrier_id,
                        },
                    }

                    if pending_events:
                        tick_data["payload"]["events"] = [event_to_dict(e) for e in pending_events]
                        pending_events.clear()

                    await websocket.send_json(tick_data)

            elif msg_type == "sync":
                await websocket.send_json({
                    "type": "state_sync",
                    "payload": session_state_to_dict(session),
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        session.is_running = False
        if simulation_task:
            simulation_task.cancel()
