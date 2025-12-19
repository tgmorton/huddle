"""Router for V2 simulation - route running and coverage visualization."""

import asyncio
import json
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.clock import Clock
from huddle.simulation.v2.core.events import EventBus, Event
from huddle.simulation.v2.physics.movement import MovementProfile
from huddle.simulation.v2.plays.routes import RouteType, ROUTE_LIBRARY
from huddle.simulation.v2.plays.concepts import CONCEPT_LIBRARY, PlayConcept
from huddle.simulation.v2.plays.schemes import SCHEME_LIBRARY, DefensiveScheme
from huddle.simulation.v2.plays.matchup import create_matchup, describe_matchup, CLASSIC_MATCHUPS
from huddle.simulation.v2.systems.route_runner import RouteRunner, RouteAssignment
from huddle.simulation.v2.systems.coverage import (
    CoverageSystem, CoverageType, CoverageAssignment, ZoneType, ZONE_BOUNDARIES
)
from huddle.simulation.v2.systems.passing import PassingSystem, CatchResult, PassState
from huddle.simulation.v2.core.entities import Ball, BallState


router = APIRouter(prefix="/v2-sim", tags=["v2-simulation"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RouteConfig(BaseModel):
    """Configuration for a receiver route."""
    name: str
    route_type: str  # RouteType value
    alignment_x: float
    is_left_side: bool = False
    read_order: int = 1  # QB read progression (1 = first read)
    is_hot_route: bool = False  # Quick throw option vs blitz
    speed: int = 90
    acceleration: int = 88
    agility: int = 88
    route_running: int = 85


class DefenderConfig(BaseModel):
    """Configuration for a defender."""
    name: str
    coverage_type: str  # "man" or "zone"
    alignment_x: float
    alignment_y: float = 5.0  # Depth off LOS
    man_target: Optional[str] = None  # Receiver name for man coverage
    zone_type: Optional[str] = None  # Zone type for zone coverage
    speed: int = 88
    acceleration: int = 86
    agility: int = 85
    man_coverage: int = 80
    zone_coverage: int = 80
    play_recognition: int = 78


class SimulationConfig(BaseModel):
    """Configuration for a simulation."""
    routes: List[RouteConfig]
    defenders: List[DefenderConfig] = []
    tick_rate_ms: int = 50
    max_time: float = 5.0


class SessionInfo(BaseModel):
    """Info about an active session."""
    session_id: str
    routes: List[RouteConfig]
    defenders: List[DefenderConfig]
    tick_rate_ms: int
    max_time: float


# =============================================================================
# Session Management
# =============================================================================

class PlayOutcome(str, Enum):
    """Outcome of the play."""
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"       # Catch made
    INCOMPLETE = "incomplete"   # Pass incomplete
    INTERCEPTION = "interception"
    TACKLED = "tackled"         # Ball carrier tackled


@dataclass
class V2SimSession:
    """Active simulation session."""
    session_id: UUID
    config: SimulationConfig
    clock: Clock
    event_bus: EventBus
    route_runner: RouteRunner
    coverage_system: CoverageSystem
    passing_system: PassingSystem
    ball: Ball
    qb: Player  # QB for throwing
    receivers: List[tuple]  # (player, profile, route_assignment)
    defenders: List[tuple]  # (player, profile, coverage_assignment)
    is_running: bool = False
    is_paused: bool = False
    is_complete: bool = False
    # Post-play state
    play_outcome: PlayOutcome = PlayOutcome.IN_PROGRESS
    ball_carrier_id: Optional[str] = None  # Player who caught the ball
    tackle_position: Optional[Vec2] = None  # Where tackle occurred


class V2SessionManager:
    """Manages active v2 simulation sessions."""

    def __init__(self):
        self.sessions: Dict[UUID, V2SimSession] = {}

    def create_session(self, config: SimulationConfig) -> V2SimSession:
        """Create a new simulation session."""
        session_id = uuid4()

        clock = Clock(tick_rate=config.tick_rate_ms / 1000.0)
        event_bus = EventBus()
        route_runner = RouteRunner(event_bus)
        coverage_system = CoverageSystem(event_bus)

        # Create receivers
        receivers = []
        receiver_map = {}  # name -> player for man coverage lookup

        for route_config in config.routes:
            # Determine X position:
            # - If alignment_x is already negative, use it directly (from concepts)
            # - If alignment_x is positive and is_left_side is True, negate it (from custom UI)
            alignment_x = route_config.alignment_x
            if alignment_x > 0 and route_config.is_left_side:
                alignment_x = -alignment_x
            alignment = Vec2(alignment_x, 0)
            attrs = PlayerAttributes(
                speed=route_config.speed,
                acceleration=route_config.acceleration,
                agility=route_config.agility,
                route_running=route_config.route_running,
            )

            player = Player(
                id=route_config.name.lower().replace(" ", "_"),
                name=route_config.name,
                team=Team.OFFENSE,
                position=Position.WR,
                pos=alignment,
                attributes=attrs,
                read_order=route_config.read_order,
                is_hot_route=route_config.is_hot_route,
            )

            profile = MovementProfile.from_attributes(
                attrs.speed, attrs.acceleration, attrs.agility
            )

            try:
                route_type = RouteType(route_config.route_type)
            except ValueError:
                route_type = RouteType.HITCH

            route = ROUTE_LIBRARY.get(route_type, ROUTE_LIBRARY[RouteType.HITCH])
            assignment = route_runner.assign_route(
                player, route, alignment, route_config.is_left_side
            )

            receivers.append((player, profile, assignment))
            receiver_map[route_config.name.lower()] = player

        # Create defenders
        defenders = []

        for def_config in config.defenders:
            alignment = Vec2(def_config.alignment_x, def_config.alignment_y)
            attrs = PlayerAttributes(
                speed=def_config.speed,
                acceleration=def_config.acceleration,
                agility=def_config.agility,
                man_coverage=def_config.man_coverage,
                zone_coverage=def_config.zone_coverage,
                play_recognition=def_config.play_recognition,
            )

            player = Player(
                id=def_config.name.lower().replace(" ", "_"),
                name=def_config.name,
                team=Team.DEFENSE,
                position=Position.CB,
                pos=alignment,
                attributes=attrs,
            )

            profile = MovementProfile.from_attributes(
                attrs.speed, attrs.acceleration, attrs.agility
            )

            # Assign coverage
            if def_config.coverage_type == "man" and def_config.man_target:
                # Find target receiver
                target_name = def_config.man_target.lower()
                target_player = receiver_map.get(target_name)
                if target_player:
                    cov_assignment = coverage_system.assign_man_coverage(
                        player, target_player.id, alignment
                    )
                else:
                    # Default to first receiver if target not found
                    cov_assignment = coverage_system.assign_man_coverage(
                        player, receivers[0][0].id if receivers else "", alignment
                    )
            elif def_config.coverage_type == "zone" and def_config.zone_type:
                try:
                    zone_type = ZoneType(def_config.zone_type)
                except ValueError:
                    zone_type = ZoneType.DEEP_THIRD_M
                cov_assignment = coverage_system.assign_zone_coverage(
                    player, zone_type, alignment
                )
            else:
                # Default to man coverage on first receiver
                cov_assignment = coverage_system.assign_man_coverage(
                    player, receivers[0][0].id if receivers else "", alignment
                )

            defenders.append((player, profile, cov_assignment))

        # Create QB
        qb = Player(
            id="qb",
            name="QB",
            team=Team.OFFENSE,
            position=Position.QB,
            pos=Vec2(0, -5),  # 5 yards behind LOS
            attributes=PlayerAttributes(
                throw_power=85,
                throw_accuracy=85,
            ),
        )

        # Create ball
        ball = Ball(
            state=BallState.HELD,
            pos=qb.pos,
            carrier_id=qb.id,
        )
        qb.has_ball = True

        # Create passing system
        passing_system = PassingSystem(event_bus)

        session = V2SimSession(
            session_id=session_id,
            config=config,
            clock=clock,
            event_bus=event_bus,
            route_runner=route_runner,
            coverage_system=coverage_system,
            passing_system=passing_system,
            ball=ball,
            qb=qb,
            receivers=receivers,
            defenders=defenders,
        )

        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: UUID) -> Optional[V2SimSession]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: UUID):
        if session_id in self.sessions:
            del self.sessions[session_id]


# Global session manager
session_manager = V2SessionManager()


# =============================================================================
# Helper Functions
# =============================================================================

def receiver_to_dict(
    player: Player,
    assignment: RouteAssignment,
    result,
    reasoning: str,
    is_ball_carrier: bool = False,
    current_move: Optional[str] = None,
    move_success: Optional[bool] = None,
) -> dict:
    """Convert receiver state to dict for transmission."""
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
        "reasoning": reasoning,
        "player_type": "receiver",
        # Goal direction: offense wants to advance toward opponent end zone (positive Y)
        "goal_direction": 1,
    }

    if result:
        data["at_max_speed"] = result.at_max_speed
        data["cut_occurred"] = result.cut_occurred
        data["cut_angle"] = result.cut_angle

    if assignment:
        data["route_name"] = assignment.route.name
        data["route_phase"] = assignment.phase.value
        data["current_waypoint"] = assignment.current_waypoint_idx
        data["total_waypoints"] = len(assignment.route.waypoints)
        if assignment.current_target:
            data["target_x"] = assignment.current_target.x
            data["target_y"] = assignment.current_target.y

    # Ballcarrier move indicators
    if is_ball_carrier and current_move:
        data["current_move"] = current_move
        data["move_success"] = move_success

    return data


def defender_to_dict(
    player: Player,
    assignment: CoverageAssignment,
    result,
    reasoning: str,
    pursuit_target: Optional[Vec2] = None,
) -> dict:
    """Convert defender state to dict for transmission."""
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
        "reasoning": reasoning,
        "player_type": "defender",
        # Goal direction: defense wants to return toward offense end zone (negative Y)
        "goal_direction": -1,
    }

    if result:
        data["at_max_speed"] = result.at_max_speed
        data["cut_occurred"] = result.cut_occurred
        data["cut_angle"] = result.cut_angle

    if assignment:
        data["coverage_type"] = assignment.coverage_type.value
        data["coverage_phase"] = assignment.phase.value

        if assignment.coverage_type == CoverageType.MAN:
            data["man_target_id"] = assignment.man_target_id
            data["has_reacted_to_break"] = assignment.has_reacted_to_break
            # DB recognition state for visualization
            # has_recognized_break maps to has_reacted_to_break
            data["has_recognized_break"] = assignment.has_reacted_to_break
            # Recognition timer/delay (in seconds, at 50ms tick rate)
            # reaction_delay_remaining counts down in ticks
            base_delay_ticks = 5  # BASE_REACTION_DELAY from CoverageSystem
            tick_rate = 0.05  # 50ms
            data["recognition_delay"] = base_delay_ticks * tick_rate
            data["recognition_timer"] = (base_delay_ticks - assignment.reaction_delay_remaining) * tick_rate
        else:
            data["zone_type"] = assignment.zone_type.value if assignment.zone_type else None
            data["has_triggered"] = assignment.has_triggered
            data["zone_target_id"] = assignment.zone_target_id

        if assignment.anticipated_position:
            data["anticipated_x"] = assignment.anticipated_position.x
            data["anticipated_y"] = assignment.anticipated_position.y

    # Pursuit target (when chasing ball carrier)
    if pursuit_target:
        data["pursuit_target_x"] = pursuit_target.x
        data["pursuit_target_y"] = pursuit_target.y

    return data


def waypoints_to_dict(assignment: RouteAssignment) -> List[dict]:
    """Convert waypoints to dict."""
    waypoints = []
    for i, wp in enumerate(assignment._field_waypoints):
        wp_def = assignment.route.waypoints[i]
        waypoints.append({
            "x": wp.x,
            "y": wp.y,
            "is_break": wp_def.is_break,
            "phase": wp_def.phase.value,
            "look_for_ball": wp_def.look_for_ball,
        })
    return waypoints


def event_to_dict(event: Event) -> dict:
    """Convert event to dict."""
    return {
        "time": event.time,
        "type": event.type.value,
        "player_id": event.player_id,
        "description": event.description,
    }


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


def ball_to_dict(ball: Ball, current_time: float) -> dict:
    """Convert ball state to dict."""
    pos, height = ball.full_position_at_time(current_time)
    data = {
        "state": ball.state.value,
        "x": pos.x,
        "y": pos.y,
        "height": height,  # Height in yards for 2.5D visualization
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
        data["throw_type"] = ball.throw_type.value
        data["peak_height"] = ball.peak_height

    return data


def qb_to_dict(qb: Player) -> dict:
    """Convert QB to dict."""
    return {
        "id": qb.id,
        "name": qb.name,
        "team": qb.team.value,
        "position": qb.position.value,
        "x": qb.pos.x,
        "y": qb.pos.y,
        "vx": qb.velocity.x,
        "vy": qb.velocity.y,
        "speed": qb.velocity.length(),
        "has_ball": qb.has_ball,
        "player_type": "qb",
    }


def session_state_to_dict(session: V2SimSession) -> dict:
    """Get full session state as dict."""
    # Waypoints for each receiver
    waypoints = {}
    players = []

    # Add QB
    players.append(qb_to_dict(session.qb))

    for player, profile, assignment in session.receivers:
        waypoints[player.id] = waypoints_to_dict(assignment)
        is_ball_carrier = player.id == session.ball_carrier_id
        players.append(receiver_to_dict(
            player, assignment, None, "",
            is_ball_carrier=is_ball_carrier,
        ))

    for player, profile, assignment in session.defenders:
        players.append(defender_to_dict(player, assignment, None, ""))

    return {
        "session_id": str(session.session_id),
        "tick": session.clock.tick_count,
        "time": session.clock.current_time,
        "is_running": session.is_running,
        "is_paused": session.is_paused,
        "is_complete": session.is_complete,
        "play_outcome": session.play_outcome.value,
        "ball_carrier_id": session.ball_carrier_id,
        "tackle_position": {"x": session.tackle_position.x, "y": session.tackle_position.y} if session.tackle_position else None,
        "players": players,
        "ball": ball_to_dict(session.ball, session.clock.current_time),
        "waypoints": waypoints,
        "zone_boundaries": zone_boundaries_to_dict(),
        "events": [event_to_dict(e) for e in session.event_bus.history],
        "config": {
            "tick_rate_ms": session.config.tick_rate_ms,
            "max_time": session.config.max_time,
            "routes": [r.model_dump() for r in session.config.routes],
            "defenders": [d.model_dump() for d in session.config.defenders],
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
        routes=config.routes,
        defenders=config.defenders,
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
    into a full SimulationConfig and creates a session.
    """
    matchup = create_matchup(request.concept, request.scheme)
    if not matchup:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid matchup: concept '{request.concept}' or scheme '{request.scheme}' not found"
        )

    # Convert matchup to SimulationConfig
    routes = [
        RouteConfig(
            name=r["name"],
            route_type=r["route_type"],
            alignment_x=r["x"],
            is_left_side=r["is_left_side"],
            read_order=r.get("read_order", 1),
            is_hot_route=r.get("hot_route", False),
        )
        for r in matchup.receivers
    ]

    defenders = [
        DefenderConfig(
            name=d["name"],
            coverage_type=d["coverage_type"],
            alignment_x=d["x"],
            alignment_y=d["y"],
            man_target=d["man_target_id"],
            zone_type=d["zone_type"],
        )
        for d in matchup.defenders
    ]

    config = SimulationConfig(
        routes=routes,
        defenders=defenders,
        tick_rate_ms=request.tick_rate_ms,
        max_time=request.max_time,
    )

    session = session_manager.create_session(config)
    return SessionInfo(
        session_id=str(session.session_id),
        routes=config.routes,
        defenders=config.defenders,
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
    - event: Simulation events (snap, route_break, coverage events, etc.)
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

    session.event_bus.subscribe_all(on_event)

    def run_tick() -> Tuple[List[dict], bool, Optional[dict]]:
        """Run a single tick and return player states, completion status, and catch result."""
        session.clock.tick()

        all_complete = True
        player_states = []
        catch_result = None

        # Get receiver players for coverage system
        receiver_players = [r[0] for r in session.receivers]
        defender_players = [d[0] for d in session.defenders]

        # Build route assignments dict for QB brain (maps player_id -> RouteAssignment)
        route_assignments = {r[0].id: r[2] for r in session.receivers}

        # QB decision making - should we throw?
        if session.passing_system.state == PassState.PRE_THROW:
            target = session.passing_system.should_throw(
                receiver_players, defender_players, session.clock, route_assignments
            )
            if target:
                # Execute the throw
                session.qb.has_ball = False

                # Estimate ball speed based on distance (matches throw_ball's throw type selection)
                # BULLET: 22-29 yds/s for <15 yards
                # TOUCH: 18-24 yds/s for 15-30 yards
                # LOB: 14-20 yds/s for >30 yards
                throw_distance = session.qb.pos.distance_to(target.pos)
                if throw_distance <= 15:
                    est_ball_speed = 25.0  # Bullet pass
                elif throw_distance <= 30:
                    est_ball_speed = 21.0  # Touch pass
                else:
                    est_ball_speed = 17.0  # Lob pass

                # Get route-aware anticipated target position and velocity
                # This handles:
                # - Settling routes (curl, hitch): throw to settle point when receiver will stop
                # - Continuing routes (slant, go): lead based on route trajectory
                anticipated_pos, expected_vel = session.route_runner.get_anticipated_throw_target(
                    target,
                    session.qb.pos,
                    ball_speed=est_ball_speed,
                )

                session.passing_system.throw_ball(
                    session.ball,
                    session.qb,
                    target,
                    session.clock,
                    anticipated_target_pos=anticipated_pos,
                    expected_receiver_velocity=expected_vel,
                )

        # Update ball flight and check for catch resolution
        if session.passing_system.state == PassState.IN_FLIGHT:
            resolution = session.passing_system.update(
                session.ball,
                receiver_players,
                defender_players,
                session.clock,
                session.clock.tick_rate,
            )
            if resolution:
                catch_result = {
                    "result": resolution.result.value,
                    "catch_probability": resolution.catch_probability,
                    "int_probability": resolution.int_probability,
                    "receiver_dist": resolution.context.receiver_dist_to_ball,
                    "defender_dist": resolution.context.defender_dist_to_ball,
                    "is_contested": resolution.context.is_contested,
                }
                # Set play outcome based on catch result
                if resolution.result == CatchResult.COMPLETE:
                    session.play_outcome = PlayOutcome.COMPLETE
                    session.ball_carrier_id = resolution.context.targeted_receiver.id
                elif resolution.result == CatchResult.INTERCEPTION:
                    session.play_outcome = PlayOutcome.INTERCEPTION
                    # Find closest defender as interceptor
                    if defender_players:
                        closest_def = min(defender_players, key=lambda d: (d.pos - session.ball.pos).magnitude())
                        session.ball_carrier_id = closest_def.id
                else:  # incomplete
                    session.play_outcome = PlayOutcome.INCOMPLETE

        # Update QB position (stays stationary for now, but include in state)
        player_states.append(qb_to_dict(session.qb))

        # Import MovementSolver once for post-play behavior
        from huddle.simulation.v2.physics.movement import MovementSolver, MovementResult
        solver = MovementSolver()

        # TACKLE CHECK: If we have a ball carrier, check if any defender is close enough to tackle
        TACKLE_RADIUS = 1.5  # yards - distance to make a tackle
        if session.play_outcome == PlayOutcome.COMPLETE and session.ball_carrier_id:
            ball_carrier = next((p for p, _, _ in session.receivers if p.id == session.ball_carrier_id), None)
            if ball_carrier:
                for def_player, _, _ in session.defenders:
                    dist = (def_player.pos - ball_carrier.pos).magnitude()
                    if dist < TACKLE_RADIUS:
                        session.play_outcome = PlayOutcome.TACKLED
                        session.tackle_position = ball_carrier.pos
                        break

        # Update receivers based on play state
        for player, profile, assignment in session.receivers:
            if session.play_outcome == PlayOutcome.INCOMPLETE:
                # Play dead - everyone stops
                player.velocity = Vec2.zero()
                result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                reasoning = "PLAY DEAD - incomplete pass"

            elif session.play_outcome == PlayOutcome.TACKLED:
                # Play dead - everyone stops
                player.velocity = Vec2.zero()
                result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                reasoning = "PLAY DEAD - ball carrier tackled"

            elif session.play_outcome == PlayOutcome.COMPLETE:
                # Ball carrier runs north (upfield), others block
                if player.id == session.ball_carrier_id:
                    # Run north at full speed
                    target = Vec2(player.pos.x, player.pos.y + 20)  # Run upfield
                    result = solver.solve(player.pos, player.velocity, target, profile, session.clock.tick_rate)
                    player.pos = result.new_pos
                    player.velocity = result.new_vel
                    reasoning = "BALL CARRIER - running upfield"
                else:
                    # Other receivers stop (simplified - could add blocking logic later)
                    player.velocity = Vec2.zero()
                    result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                    reasoning = "Catch made - watching play"

            elif session.play_outcome == PlayOutcome.INTERCEPTION:
                # Receivers become defenders, try to tackle
                if session.ball_carrier_id:
                    interceptor = next((p for p, _, _ in session.defenders if p.id == session.ball_carrier_id), None)
                    if interceptor:
                        target = interceptor.pos
                        result = solver.solve(player.pos, player.velocity, target, profile, session.clock.tick_rate)
                        player.pos = result.new_pos
                        player.velocity = result.new_vel
                        reasoning = "PURSUIT - chasing interceptor"
                    else:
                        result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                        reasoning = "Interception"
                else:
                    result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                    reasoning = "Interception"

            else:
                # Check if ball is in flight and this receiver is the target
                ball_in_flight = session.passing_system.state == PassState.IN_FLIGHT
                is_intended_receiver = (
                    ball_in_flight and
                    session.ball.intended_receiver_id == player.id
                )

                if is_intended_receiver and session.ball.flight_target:
                    # BALL TRACKING MODE: Receiver adjusts to meet the ball
                    # Move toward the ball's landing spot (flight_target)
                    ball_target = session.ball.flight_target

                    # Calculate distance to ball target
                    dist_to_ball = player.pos.distance_to(ball_target)

                    if dist_to_ball > 0.5:
                        # Move toward ball target at full speed
                        result = solver.solve(
                            player.pos, player.velocity, ball_target,
                            profile, session.clock.tick_rate
                        )
                        player.pos = result.new_pos
                        player.velocity = result.new_vel
                        reasoning = f"TRACKING BALL - moving to catch point ({dist_to_ball:.1f}yd away)"
                    else:
                        # Close enough - settle at ball target
                        player.pos = ball_target
                        player.velocity = Vec2.zero()
                        result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                        reasoning = "AT CATCH POINT - waiting for ball"
                else:
                    # Normal route running (no ball in flight or not the target)
                    result, reasoning = session.route_runner.update(
                        player, profile, session.clock.tick_rate, session.clock
                    )
                    player.pos = result.new_pos
                    player.velocity = result.new_vel

                if not assignment.is_complete and not is_intended_receiver:
                    all_complete = False

            # Check if this player is the ball carrier
            is_ball_carrier = player.id == session.ball_carrier_id
            player_states.append(receiver_to_dict(
                player, assignment, result, reasoning,
                is_ball_carrier=is_ball_carrier,
            ))

        # Update defenders based on play state
        for player, profile, assignment in session.defenders:
            pursuit_target: Optional[Vec2] = None  # Track pursuit target for visualization

            if session.play_outcome == PlayOutcome.INCOMPLETE:
                # Play dead - everyone stops
                player.velocity = Vec2.zero()
                result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                reasoning = "PLAY DEAD - incomplete pass"

            elif session.play_outcome == PlayOutcome.TACKLED:
                # Play dead - everyone stops
                player.velocity = Vec2.zero()
                result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                reasoning = "PLAY DEAD - tackled the ball carrier"

            elif session.play_outcome == PlayOutcome.COMPLETE:
                # Pursue ball carrier for tackle
                ball_carrier = next((p for p, _, _ in session.receivers if p.id == session.ball_carrier_id), None)
                if ball_carrier:
                    target = ball_carrier.pos
                    pursuit_target = target  # Set pursuit target for visualization
                    result = solver.solve(player.pos, player.velocity, target, profile, session.clock.tick_rate)
                    player.pos = result.new_pos
                    player.velocity = result.new_vel
                    dist = (player.pos - ball_carrier.pos).magnitude()
                    reasoning = f"PURSUIT - {dist:.1f} yds to ball carrier"
                else:
                    result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                    reasoning = "No ball carrier"

            elif session.play_outcome == PlayOutcome.INTERCEPTION:
                # Interceptor runs north, others block
                if player.id == session.ball_carrier_id:
                    # Interceptor runs south (opposite direction - returning)
                    target = Vec2(player.pos.x, player.pos.y - 20)
                    result = solver.solve(player.pos, player.velocity, target, profile, session.clock.tick_rate)
                    player.pos = result.new_pos
                    player.velocity = result.new_vel
                    reasoning = "INTERCEPTION RETURN - running it back"
                else:
                    # Other defenders block (simplified - just stop)
                    player.velocity = Vec2.zero()
                    result = MovementResult(player.pos, Vec2.zero(), False, False, 0.0)
                    reasoning = "Interception - blocking"

            else:
                # Normal coverage (play in progress)
                # Check if defender should track ball instead of coverage
                if session.passing_system.should_defender_track_ball(player, session.ball):
                    ball_target, ball_reasoning = session.passing_system.get_defender_ball_tracking(
                        player, session.ball, session.clock
                    )
                    if ball_target:
                        # Move toward ball instead of coverage
                        pursuit_target = ball_target  # Ball tracking is a form of pursuit
                        result = solver.solve(
                            player.pos, player.velocity, ball_target, profile,
                            session.clock.tick_rate, max_speed_override=profile.max_speed * 0.8
                        )
                        player.pos = result.new_pos
                        player.velocity = result.new_vel
                        player_states.append(defender_to_dict(
                            player, assignment, result, f"BALL TRACKING: {ball_reasoning}",
                            pursuit_target=pursuit_target,
                        ))
                        continue

                result, reasoning = session.coverage_system.update(
                    player, profile, receiver_players, session.clock.tick_rate, session.clock
                )
                player.pos = result.new_pos
                player.velocity = result.new_vel

            player_states.append(defender_to_dict(
                player, assignment, result, reasoning,
                pursuit_target=pursuit_target,
            ))

        return player_states, all_complete, catch_result

    async def run_simulation():
        """Run simulation loop."""
        session.is_running = True
        session.is_paused = False
        session.is_complete = False

        # Start routes and coverage
        session.route_runner.start_all_routes(session.clock)
        session.coverage_system.start_coverage(session.clock)

        while session.is_running and session.clock.current_time < session.config.max_time:
            if session.is_paused:
                await asyncio.sleep(0.05)
                continue

            player_states, all_complete, catch_result = run_tick()

            # Send tick update
            tick_data = {
                "type": "tick",
                "payload": {
                    "tick": session.clock.tick_count,
                    "time": session.clock.current_time,
                    "players": player_states,
                    "ball": ball_to_dict(session.ball, session.clock.current_time),
                    "play_outcome": session.play_outcome.value,
                    "ball_carrier_id": session.ball_carrier_id,
                },
            }

            # Include catch result if resolved this tick
            if catch_result:
                tick_data["payload"]["catch_result"] = catch_result

            # Include tackle position if tackled
            if session.tackle_position:
                tick_data["payload"]["tackle_position"] = {
                    "x": session.tackle_position.x,
                    "y": session.tackle_position.y
                }

            # Include any events from this tick
            if pending_events:
                tick_data["payload"]["events"] = [event_to_dict(e) for e in pending_events]
                pending_events.clear()

            try:
                await websocket.send_json(tick_data)
            except Exception:
                session.is_running = False
                break

            # End conditions:
            # 1. Play is dead (incomplete, tackled, interception tackled)
            # 2. All routes complete AND ball is not in flight AND no catch made yet
            if session.play_outcome in (PlayOutcome.INCOMPLETE, PlayOutcome.TACKLED):
                # Let play run a few more ticks after tackle so user can see it
                await asyncio.sleep(0.3)  # Brief pause to show tackle
                break

            # Don't end if catch was made - let play continue until tackle
            if session.play_outcome in (PlayOutcome.COMPLETE, PlayOutcome.INTERCEPTION):
                # Keep running - waiting for tackle
                await asyncio.sleep(session.config.tick_rate_ms / 1000.0)
                continue

            ball_in_flight = session.passing_system.state == PassState.IN_FLIGHT
            if all_complete and not ball_in_flight:
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
        """Reset session state."""
        session.clock.reset()
        session.event_bus.clear_history()
        session.route_runner.clear_assignments()
        session.coverage_system.clear_assignments()
        session.passing_system.reset()
        session.is_complete = False
        session.is_paused = False
        session.play_outcome = PlayOutcome.IN_PROGRESS
        session.ball_carrier_id = None
        session.tackle_position = None
        pending_events.clear()

        # Reset QB and ball
        session.qb.pos = Vec2(0, -5)
        session.qb.velocity = Vec2.zero()
        session.qb.has_ball = True
        session.ball.state = BallState.HELD
        session.ball.pos = session.qb.pos
        session.ball.carrier_id = session.qb.id
        session.ball.flight_origin = None
        session.ball.flight_target = None

        # Rebuild receiver map
        receiver_map = {}

        # Re-create receivers
        new_receivers = []
        for route_config in session.config.routes:
            alignment_x = route_config.alignment_x
            if alignment_x > 0 and route_config.is_left_side:
                alignment_x = -alignment_x

            alignment = Vec2(alignment_x, 0)
            attrs = PlayerAttributes(
                speed=route_config.speed,
                acceleration=route_config.acceleration,
                agility=route_config.agility,
                route_running=route_config.route_running,
            )

            player = Player(
                id=route_config.name.lower().replace(" ", "_"),
                name=route_config.name,
                team=Team.OFFENSE,
                position=Position.WR,
                pos=alignment,
                attributes=attrs,
                read_order=route_config.read_order,
                is_hot_route=route_config.is_hot_route,
            )

            profile = MovementProfile.from_attributes(
                attrs.speed, attrs.acceleration, attrs.agility
            )

            try:
                route_type = RouteType(route_config.route_type)
            except ValueError:
                route_type = RouteType.HITCH

            route = ROUTE_LIBRARY.get(route_type, ROUTE_LIBRARY[RouteType.HITCH])
            assignment = session.route_runner.assign_route(
                player, route, alignment, route_config.is_left_side
            )

            new_receivers.append((player, profile, assignment))
            receiver_map[route_config.name.lower()] = player

        session.receivers = new_receivers

        # Re-create defenders
        new_defenders = []
        for def_config in session.config.defenders:
            alignment = Vec2(def_config.alignment_x, def_config.alignment_y)
            attrs = PlayerAttributes(
                speed=def_config.speed,
                acceleration=def_config.acceleration,
                agility=def_config.agility,
                man_coverage=def_config.man_coverage,
                zone_coverage=def_config.zone_coverage,
                play_recognition=def_config.play_recognition,
            )

            player = Player(
                id=def_config.name.lower().replace(" ", "_"),
                name=def_config.name,
                team=Team.DEFENSE,
                position=Position.CB,
                pos=alignment,
                attributes=attrs,
            )

            profile = MovementProfile.from_attributes(
                attrs.speed, attrs.acceleration, attrs.agility
            )

            # Assign coverage
            if def_config.coverage_type == "man" and def_config.man_target:
                target_name = def_config.man_target.lower()
                target_player = receiver_map.get(target_name)
                if target_player:
                    cov_assignment = session.coverage_system.assign_man_coverage(
                        player, target_player.id, alignment
                    )
                else:
                    cov_assignment = session.coverage_system.assign_man_coverage(
                        player, new_receivers[0][0].id if new_receivers else "", alignment
                    )
            elif def_config.coverage_type == "zone" and def_config.zone_type:
                try:
                    zone_type = ZoneType(def_config.zone_type)
                except ValueError:
                    zone_type = ZoneType.DEEP_THIRD_M
                cov_assignment = session.coverage_system.assign_zone_coverage(
                    player, zone_type, alignment
                )
            else:
                cov_assignment = session.coverage_system.assign_man_coverage(
                    player, new_receivers[0][0].id if new_receivers else "", alignment
                )

            new_defenders.append((player, profile, cov_assignment))

        session.defenders = new_defenders

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
                # Stop running simulation
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
                # Single step when paused
                if session.is_paused or not session.is_running:
                    if session.clock.current_time == 0:
                        # Start routes and coverage on first step
                        session.route_runner.start_all_routes(session.clock)
                        session.coverage_system.start_coverage(session.clock)

                    player_states, _, catch_result = run_tick()

                    tick_data = {
                        "type": "tick",
                        "payload": {
                            "tick": session.clock.tick_count,
                            "time": session.clock.current_time,
                            "players": player_states,
                            "ball": ball_to_dict(session.ball, session.clock.current_time),
                        },
                    }

                    if catch_result:
                        tick_data["payload"]["catch_result"] = catch_result

                    if pending_events:
                        tick_data["payload"]["events"] = [event_to_dict(e) for e in pending_events]
                        pending_events.clear()

                    await websocket.send_json(tick_data)

            elif msg_type == "throw":
                # Throw to a receiver
                # message format: {"type": "throw", "target": "receiver_name"}
                target_name = message.get("target", "").lower().replace(" ", "_")

                # Find the receiver
                target_receiver = None
                for player, _, _ in session.receivers:
                    if player.id == target_name or player.name.lower() == message.get("target", "").lower():
                        target_receiver = player
                        break

                if not target_receiver:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Receiver not found: {message.get('target')}",
                    })
                else:
                    # Execute throw
                    session.qb.has_ball = False
                    result = session.passing_system.throw_ball(
                        session.ball,
                        session.qb,
                        target_receiver,
                        session.clock,
                        lead_time=message.get("lead_time", 0.3),
                    )

                    await websocket.send_json({
                        "type": "throw_started",
                        "payload": {
                            "target_id": target_receiver.id,
                            "target_name": target_receiver.name,
                            "velocity": result.velocity,
                            "flight_time": result.flight_time,
                            "target_x": result.actual_target.x,
                            "target_y": result.actual_target.y,
                            "accuracy_variance": result.accuracy_variance,
                        },
                    })

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
