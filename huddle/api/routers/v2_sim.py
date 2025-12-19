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
    Orchestrator, PlayConfig, PlayPhase, PlayResult, BrainDecision
)
from huddle.simulation.v2.plays.routes import RouteType, ROUTE_LIBRARY
from huddle.simulation.v2.plays.concepts import CONCEPT_LIBRARY
from huddle.simulation.v2.plays.schemes import SCHEME_LIBRARY
from huddle.simulation.v2.plays.matchup import create_matchup, describe_matchup, CLASSIC_MATCHUPS
from huddle.simulation.v2.systems.route_runner import RouteAssignment
from huddle.simulation.v2.systems.coverage import (
    CoverageType, CoverageAssignment, ZoneType, ZONE_BOUNDARIES
)
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.lb_brain import lb_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain


router = APIRouter(prefix="/v2-sim", tags=["v2-simulation"])


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


class V2SessionManager:
    """Manages active v2 simulation sessions."""

    def __init__(self):
        self.sessions: Dict[UUID, V2SimSession] = {}

    def create_session(self, config: SimulationConfig) -> V2SimSession:
        """Create a new simulation session with full orchestrator."""
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
    elif player.position in (Position.WR, Position.TE, Position.RB):
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
    }


# =============================================================================
# REST Endpoints
# =============================================================================

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


class MatchupRequest(BaseModel):
    """Request to create a matchup session."""
    concept: str
    scheme: str
    tick_rate_ms: int = 50
    max_time: float = 6.0


@router.post("/matchup", response_model=SessionInfo)
async def create_matchup_session(request: MatchupRequest) -> SessionInfo:
    """Create a simulation session from a concept vs scheme matchup.

    This is a convenience endpoint that converts concept/scheme names
    into a full SimulationConfig with all players and creates a session.
    """
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
        # Add standard OL
        PlayerConfig(name="LT", position="LT", alignment_x=-6, alignment_y=-1, block_power=80, block_finesse=75),
        PlayerConfig(name="LG", position="LG", alignment_x=-3, alignment_y=-1, block_power=82, block_finesse=72),
        PlayerConfig(name="C", position="C", alignment_x=0, alignment_y=-1, block_power=78, block_finesse=78, awareness=85),
        PlayerConfig(name="RG", position="RG", alignment_x=3, alignment_y=-1, block_power=82, block_finesse=72),
        PlayerConfig(name="RT", position="RT", alignment_x=6, alignment_y=-1, block_power=78, block_finesse=77),
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
        # 3-4 front: 2 DE + 1 NT
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=-5, alignment_y=1, pass_rush=82, strength=80),
            PlayerConfig(name="NT", position="NT", alignment_x=0, alignment_y=1, pass_rush=75, strength=88),
            PlayerConfig(name="RDE", position="DE", alignment_x=5, alignment_y=1, pass_rush=82, strength=80),
        ]
    else:
        # 4-3 front: 2 DE + 2 DT
        defense = [
            PlayerConfig(name="LDE", position="DE", alignment_x=-6, alignment_y=1, pass_rush=84, strength=78),
            PlayerConfig(name="LDT", position="DT", alignment_x=-2, alignment_y=1, pass_rush=76, strength=85),
            PlayerConfig(name="RDT", position="DT", alignment_x=2, alignment_y=1, pass_rush=76, strength=85),
            PlayerConfig(name="RDE", position="DE", alignment_x=6, alignment_y=1, pass_rush=84, strength=78),
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
                    session.play_outcome = PlayOutcome.COMPLETE
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
        session.is_running = True
        session.is_paused = False
        session.is_complete = False
        session.play_outcome = PlayOutcome.IN_PROGRESS

        orchestrator = session.orchestrator

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

            if session.tackle_position:
                tick_data["payload"]["tackle_position"] = {
                    "x": session.tackle_position.x,
                    "y": session.tackle_position.y,
                }

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
