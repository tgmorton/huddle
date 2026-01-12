"""Coach Mode Game API Router.

Provides REST and WebSocket endpoints for playing games in coach mode where
the user makes play-calling decisions.

REST Endpoints:
- POST /coach/start - Start a new coach mode game
- GET /coach/{game_id}/situation - Get current game situation
- GET /coach/{game_id}/plays - Get available plays
- POST /coach/{game_id}/play - Execute a play
- POST /coach/{game_id}/special - Execute special teams play
- GET /coach/{game_id}/box-score - Get current box score
- POST /coach/{game_id}/simulate-defense - Let AI handle defensive possession

WebSocket Endpoints:
- WS /coach/{game_id}/stream - Real-time play-by-play streaming
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from uuid import UUID
import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from huddle.simulation.v2.core.entities import Player, Team, Position
from huddle.simulation.v2.core.phases import PlayPhase
from huddle.simulation.v2.orchestrator import Orchestrator
from huddle.simulation.v2.systems.coverage import CoverageType

from huddle.api.schemas.coach_mode import (
    StartGameRequest,
    StartGameWithLeagueRequest,
    CallPlayRequest,
    SpecialTeamsRequest,
    GameSituationResponse,
    AvailablePlaysResponse,
    PlayResultResponse,
    SpecialTeamsResultResponse,
    GameStartedResponse,
    BoxScoreResponse,
    GameOverResponse,
    GamePhaseEnum,
    PlayTypeEnum,
    PacingEnum,
    AutoPlayRequest,
    AutoPlayResponse,
)


# =============================================================================
# Frame Serialization for Play Visualization
# =============================================================================

def _player_to_frame_dict(
    player: Player,
    orchestrator: Orchestrator,
    ball_carrier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert player state to dict for visualization.

    Simplified version of v2_sim.player_to_dict focused on essential fields.
    """
    data = {
        "id": player.id,
        "name": player.name,
        "team": player.team.value,
        "position": player.position.value if player.position else "unknown",
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

    # Determine player_type for frontend visualization
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
    elif player.position in (Position.CB, Position.SS, Position.FS, Position.MLB, Position.OLB, Position.ILB):
        data["player_type"] = "defender"
    else:
        data["player_type"] = "receiver" if player.team == Team.OFFENSE else "defender"

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
            data["has_recognized_break"] = coverage_assignment.has_reacted_to_break
        else:
            data["zone_type"] = coverage_assignment.zone_type.value if coverage_assignment.zone_type else None
            data["has_triggered"] = coverage_assignment.has_triggered

    # Blocking engagement info
    engagement = orchestrator.block_resolver.get_engagement_for_player(player.id)
    if engagement:
        data["is_engaged"] = True
        if player.team == Team.OFFENSE:
            data["engaged_with_id"] = engagement.dl_id
        else:
            data["engaged_with_id"] = engagement.ol_id
        data["block_shed_progress"] = engagement.shed_progress

    # Ballcarrier info
    if player.id == ball_carrier_id:
        data["is_ball_carrier"] = True
        tackle_engagement = orchestrator.tackle_resolver.get_engagement(player.id)
        if tackle_engagement:
            data["in_tackle"] = True
            data["tackle_leverage"] = tackle_engagement.leverage

    # Pursuit target for defenders
    if ball_carrier_id and player.team == Team.DEFENSE:
        if orchestrator.phase in (PlayPhase.AFTER_CATCH, PlayPhase.RUN_ACTIVE):
            # Find ball carrier position
            for p in orchestrator.offense:
                if p.id == ball_carrier_id:
                    data["pursuit_target_x"] = p.pos.x
                    data["pursuit_target_y"] = p.pos.y
                    break

    return data


def _collect_frame(
    orchestrator: Orchestrator,
    offense: List[Player],
    defense: List[Player],
    ball_carrier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Collect a single frame of play state for visualization."""
    players = []
    waypoints = {}

    for player in offense + defense:
        players.append(_player_to_frame_dict(player, orchestrator, ball_carrier_id))

        # Collect waypoints for receivers
        route_assignment = orchestrator.route_runner.get_assignment(player.id)
        if route_assignment and route_assignment.route.waypoints:
            waypoints[player.id] = [
                {
                    "x": wp.offset.x if hasattr(wp, 'offset') else (wp.position.x if hasattr(wp, 'position') else 0),
                    "y": wp.offset.y if hasattr(wp, 'offset') else (wp.position.y if hasattr(wp, 'position') else 0),
                    "is_break": wp.is_break if hasattr(wp, 'is_break') else False,
                    "phase": wp.phase.value if hasattr(wp, 'phase') else "stem",
                }
                for wp in route_assignment.route.waypoints
            ]

    # Ball state
    ball = orchestrator.ball
    # Calculate current ball height (approximation for visualization)
    ball_height = 0.0
    if ball.is_in_flight and ball.flight_duration > 0:
        current_time = orchestrator.clock.current_time
        t = (current_time - ball.flight_start_time) / ball.flight_duration
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        # Parabolic arc: h = release + 4*peak*t*(1-t)
        ball_height = ball.release_height + 4 * ball.peak_height * t * (1 - t)
    elif ball.is_held:
        ball_height = 2.0  # ~6 feet when held
    ball_data = {
        "x": ball.pos.x,
        "y": ball.pos.y,
        "height": ball_height,
        "state": ball.state.value,
        "carrier_id": ball.carrier_id,
    }

    return {
        "tick": orchestrator.clock.tick_count,
        "time": orchestrator.clock.current_time,
        "phase": orchestrator.phase.value,
        "players": players,
        "ball": ball_data,
        "waypoints": waypoints,
    }


def _run_play_with_frames(
    orchestrator: Orchestrator,
    offense: List[Player],
    defense: List[Player],
) -> tuple:
    """Run play tick-by-tick, collecting frames for visualization.

    Returns:
        Tuple of (PlayResult, list of frames)
    """
    from huddle.simulation.v2.core.events import EventType

    if orchestrator.phase != PlayPhase.PRE_SNAP:
        raise RuntimeError("Must call setup_play() before running")

    frames = []
    ball_carrier_id = None

    # Pre-snap reads
    orchestrator._do_pre_snap_reads()

    # Snap
    orchestrator._do_snap()

    # Collect initial frame after snap
    frames.append(_collect_frame(orchestrator, offense, defense, ball_carrier_id))

    # Main loop - run tick by tick
    while not orchestrator._should_stop():
        dt = orchestrator.clock.tick()
        orchestrator._update_tick(dt)

        # Track ball carrier from events
        for event in orchestrator.event_bus.history:
            if event.type == EventType.CATCH and hasattr(event, 'player_id'):
                ball_carrier_id = event.player_id

        # Also check ball.carrier_id directly
        if orchestrator.ball.carrier_id:
            ball_carrier_id = orchestrator.ball.carrier_id

        # Collect frame
        frames.append(_collect_frame(orchestrator, offense, defense, ball_carrier_id))

    # Compile result
    result = orchestrator._compile_result()

    return result, frames


# =============================================================================
# Auto-Play State Management
# =============================================================================

@dataclass
class AutoPlayState:
    """Tracks auto-play mode state for a game."""
    is_running: bool = False
    is_paused: bool = False
    pacing: PacingEnum = PacingEnum.NORMAL
    task: Optional[asyncio.Task] = None

    @property
    def delay_seconds(self) -> float:
        """Get delay between plays based on pacing."""
        delays = {
            PacingEnum.SLOW: 2.0,
            PacingEnum.NORMAL: 1.0,
            PacingEnum.FAST: 0.3,
        }
        return delays.get(self.pacing, 1.0)

router = APIRouter(prefix="/coach", tags=["coach-mode"])


# =============================================================================
# WebSocket Connection Manager
# =============================================================================

class GameConnectionManager:
    """Manages WebSocket connections for game streaming.

    Each game can have multiple connected clients that receive
    real-time play-by-play updates.
    """

    def __init__(self):
        # game_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        """Accept a WebSocket connection for a game."""
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        """Remove a WebSocket connection."""
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
            # Clean up empty game lists
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast(self, game_id: str, message: dict):
        """Send a message to all clients connected to a game."""
        if game_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, game_id)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    def get_connection_count(self, game_id: str) -> int:
        """Get number of clients connected to a game."""
        return len(self.active_connections.get(game_id, []))


# Global connection manager
connection_manager = GameConnectionManager()


# =============================================================================
# In-Memory Game Session Store
# =============================================================================

# Store active coach mode games
# In production, this would be Redis or database
_active_games: Dict[str, dict] = {}


def _get_game(game_id: str) -> dict:
    """Get a game session or raise 404."""
    if game_id not in _active_games:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return _active_games[game_id]


# =============================================================================
# Game Lifecycle Endpoints
# =============================================================================

@router.post("/start", response_model=GameStartedResponse, status_code=status.HTTP_201_CREATED)
async def start_game(request: StartGameRequest) -> GameStartedResponse:
    """Start a new coach mode game.

    Creates a game between two teams and returns the initial situation
    after the coin toss and opening kickoff.

    Teams can be specified by UUID or abbreviation. If abbreviations are
    provided, teams are looked up from the loaded league.
    """
    from huddle.api.services.management_service import management_session_manager
    from huddle.api.routers.admin import get_active_league
    from huddle.game.manager import GameManager
    import uuid

    # Get teams from league
    home_team = None
    away_team = None
    league = None

    # Try to get league from management session first
    for session in management_session_manager._sessions.values():
        if session.service and session.service.league:
            league = session.service.league
            break

    # Fall back to admin's active league
    if not league:
        league = get_active_league()

    # Look up teams from the league
    if league:
        for team in league.teams.values():
            # Match by ID
            if request.home_team_id and str(team.id) == str(request.home_team_id):
                home_team = team
            elif request.away_team_id and str(team.id) == str(request.away_team_id):
                away_team = team
            # Match by abbreviation
            elif request.home_team_abbr and team.abbreviation == request.home_team_abbr:
                home_team = team
            elif request.away_team_abbr and team.abbreviation == request.away_team_abbr:
                away_team = team

    if not home_team or not away_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teams not found. Make sure a league is loaded and team IDs/abbreviations are valid.",
        )

    # Create game manager
    game_manager = GameManager(home_team, away_team, coach_mode=True)
    game_manager.start_game()

    # Generate game ID
    game_id = f"game_{uuid.uuid4().hex[:8]}"

    # Store session
    _active_games[game_id] = {
        "manager": game_manager,
        "home_team": home_team,
        "away_team": away_team,
        "user_controls_home": request.user_controls_home,
        "auto_play_state": AutoPlayState(),
    }

    # Build situation response
    situation = _build_situation_response(game_id, game_manager, request.user_controls_home)

    # Determine coin toss message
    if game_manager._possession_home:
        toss_msg = f"{away_team.full_name} won the toss and deferred."
    else:
        toss_msg = f"{home_team.full_name} won the toss and deferred."

    return GameStartedResponse(
        game_id=game_id,
        home_team_name=home_team.full_name,
        away_team_name=away_team.full_name,
        situation=situation,
        message=toss_msg,
    )


@router.post("/start-with-league", response_model=GameStartedResponse, status_code=status.HTTP_201_CREATED)
async def start_game_with_league(request: StartGameWithLeagueRequest) -> GameStartedResponse:
    """Start a game from a league schedule matchup.

    Finds the matchup for the given week and starts the game.
    """
    # TODO: Implement league schedule lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="League schedule integration not yet implemented",
    )


@router.get("/{game_id}/situation", response_model=GameSituationResponse)
async def get_situation(game_id: str) -> GameSituationResponse:
    """Get the current game situation.

    Returns down, distance, field position, score, time, etc.
    """
    game = _get_game(game_id)
    manager = game["manager"]
    user_controls_home = game["user_controls_home"]

    return _build_situation_response(game_id, manager, user_controls_home)


@router.get("/{game_id}/plays", response_model=AvailablePlaysResponse)
async def get_available_plays(game_id: str) -> AvailablePlaysResponse:
    """Get available plays for the current situation.

    Returns a list of play codes appropriate for the down/distance.
    """
    from huddle.game.coordinator import OffensiveCoordinator, SituationContext

    game = _get_game(game_id)
    manager = game["manager"]

    # Check if user is on offense
    user_controls_home = game["user_controls_home"]
    user_on_offense = manager._possession_home == user_controls_home

    if not user_on_offense:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get plays - user is on defense",
        )

    # Build situation context
    down_state = manager._game_state.down_state
    context = SituationContext(
        down=down_state.down,
        distance=down_state.yards_to_go,
        los=down_state.line_of_scrimmage,
        quarter=manager.quarter,
        time_remaining=manager.time_remaining,
        score_diff=manager.home_score - manager.away_score if user_controls_home else manager.away_score - manager.home_score,
        timeouts=3,  # TODO: Track timeouts
    )

    # Get available plays from playbook
    team = game["home_team"] if user_controls_home else game["away_team"]
    oc = OffensiveCoordinator(team=team)

    # Filter plays by situation
    plays = _get_situation_plays(context)

    # Get AI recommendation
    recommended = oc.call_play(context)

    # Generate tips
    tips = _generate_situation_tips(context)

    return AvailablePlaysResponse(
        plays=plays,
        recommended=recommended,
        situation_tips=tips,
    )


@router.post("/{game_id}/play", response_model=PlayResultResponse)
async def execute_play(game_id: str, request: CallPlayRequest) -> PlayResultResponse:
    """Execute an offensive play.

    Runs the V2 simulation with the called play and returns the result.
    """
    from huddle.game.play_adapter import PlayAdapter
    from huddle.game.coordinator import DefensiveCoordinator, SituationContext
    from huddle.simulation.v2.orchestrator import PlayConfig

    game = _get_game(game_id)
    manager = game["manager"]
    user_controls_home = game["user_controls_home"]

    # Check game isn't over
    if manager.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is over",
        )

    # Check user is on offense
    if manager._possession_home != user_controls_home:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot call plays - user is on defense",
        )

    # Get players
    offense, defense = manager._get_players_for_drive()

    # Build play config
    adapter = PlayAdapter(offense, defense)
    config = adapter.build_offensive_config(request.play_code, request.shotgun)

    # Get AI defensive call
    down_state = manager._game_state.down_state
    context = SituationContext(
        down=down_state.down,
        distance=down_state.yards_to_go,
        los=down_state.line_of_scrimmage,
        quarter=manager.quarter,
        time_remaining=manager.time_remaining,
        score_diff=manager.home_score - manager.away_score,
        timeouts=3,
    )
    dc = DefensiveCoordinator()
    def_play = dc.call_coverage(context)
    man_assign, zone_assign = adapter.build_defensive_config(def_play)
    config.man_assignments = man_assign
    config.zone_assignments = zone_assign

    # Execute play
    los_y = down_state.line_of_scrimmage
    manager._orchestrator.setup_play(offense, defense, config, los_y)
    result = manager._orchestrator.run()

    # Check for TD
    is_touchdown = down_state.line_of_scrimmage + result.yards_gained >= 100

    # Update game state
    old_down = down_state.down
    old_distance = down_state.yards_to_go

    # Process result
    if result.outcome in ("interception", "fumble"):
        is_turnover = True
        drive_over = True
        drive_reason = "turnover"
    elif is_touchdown:
        is_turnover = False
        drive_over = True
        drive_reason = "touchdown"
        manager._add_score(6)
    else:
        is_turnover = False
        # Update down/distance
        if result.yards_gained >= old_distance:
            # First down
            down_state.down = 1
            down_state.yards_to_go = min(10, int(100 - down_state.line_of_scrimmage - result.yards_gained))
            first_down = True
        else:
            down_state.down += 1
            down_state.yards_to_go = max(1, old_distance - int(result.yards_gained))
            first_down = False

        down_state.line_of_scrimmage += result.yards_gained

        # Check for turnover on downs
        if down_state.down > 4:
            drive_over = True
            drive_reason = "turnover_on_downs"
        else:
            drive_over = False
            drive_reason = None

    # Build description
    description = _format_play_description(result, offense, defense)

    play_response = PlayResultResponse(
        outcome=result.outcome,
        yards_gained=result.yards_gained,
        description=description,
        new_down=down_state.down,
        new_distance=down_state.yards_to_go,
        new_los=down_state.line_of_scrimmage,
        first_down=result.yards_gained >= old_distance,
        touchdown=is_touchdown,
        turnover=is_turnover,
        is_drive_over=drive_over,
        drive_end_reason=drive_reason,
        passer_name=_get_player_name(result.passer_id, offense),
        receiver_name=_get_player_name(result.receiver_id, offense),
        tackler_name=_get_player_name(result.tackler_id, defense),
    )

    # Broadcast to WebSocket clients
    await broadcast_play_result(game_id, play_response)

    # Broadcast situation update
    situation = _build_situation_response(game_id, manager, user_controls_home)
    await broadcast_situation_update(game_id, situation)

    # Broadcast score if touchdown
    if is_touchdown:
        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    return play_response


@router.post("/{game_id}/special", response_model=SpecialTeamsResultResponse)
async def execute_special_teams(game_id: str, request: SpecialTeamsRequest) -> SpecialTeamsResultResponse:
    """Execute a special teams play (FG, punt, PAT, kickoff)."""
    game = _get_game(game_id)
    manager = game["manager"]
    user_controls_home = game["user_controls_home"]
    response: SpecialTeamsResultResponse

    if request.play_type == PlayTypeEnum.FIELD_GOAL:
        # Calculate distance
        los = manager._game_state.down_state.line_of_scrimmage
        distance = (100 - los) + 17  # Add 17 for snap + end zone

        result = manager._handle_field_goal(distance)

        if result.points > 0:
            manager._add_score(3)
            desc = f"{distance:.0f}-yard field goal is GOOD"
        else:
            desc = f"{distance:.0f}-yard field goal is NO GOOD"

        response = SpecialTeamsResultResponse(
            play_type="field_goal",
            result=result.result,
            new_los=result.new_los,
            points_scored=result.points,
            description=desc,
        )

    elif request.play_type == PlayTypeEnum.PUNT:
        result = manager._handle_punt()

        desc = f"Punt from the {manager._game_state.down_state.line_of_scrimmage:.0f}"
        if result.result == "touchback":
            desc += " - Touchback"
        elif result.result == "fair_catch":
            desc += f" - Fair catch at the {result.new_los:.0f}"
        else:
            desc += f" - Returned to the {result.new_los:.0f}"

        response = SpecialTeamsResultResponse(
            play_type="punt",
            result=result.result,
            new_los=result.new_los,
            points_scored=0,
            description=desc,
        )

    elif request.play_type == PlayTypeEnum.PAT:
        result = manager._handle_pat(go_for_two=request.go_for_two)

        if request.go_for_two:
            desc = "Two-point conversion " + ("GOOD" if result.points > 0 else "FAILED")
        else:
            desc = "Extra point is " + ("GOOD" if result.points > 0 else "NO GOOD")

        if result.points > 0:
            manager._add_score(result.points)

        response = SpecialTeamsResultResponse(
            play_type="pat" if not request.go_for_two else "two_point",
            result=result.result,
            new_los=25.0,  # Next drive starts at 25
            points_scored=result.points,
            description=desc,
        )

    elif request.play_type == PlayTypeEnum.KICKOFF:
        result = manager._handle_kickoff(onside=request.onside)

        if request.onside:
            desc = "Onside kick " + ("RECOVERED" if result.kicking_team_ball else "FAILED")
        elif result.result == "touchback":
            desc = "Kickoff - Touchback"
        else:
            desc = f"Kickoff returned to the {result.new_los:.0f}"

        response = SpecialTeamsResultResponse(
            play_type="kickoff",
            result=result.result,
            new_los=result.new_los,
            points_scored=0,
            description=desc,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown special teams play type: {request.play_type}",
        )

    # Broadcast to WebSocket clients
    await broadcast_special_teams(game_id, response)

    # Broadcast situation update
    situation = _build_situation_response(game_id, manager, user_controls_home)
    await broadcast_situation_update(game_id, situation)

    # Broadcast score if points scored
    if response.points_scored > 0:
        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    return response


@router.post("/{game_id}/simulate-defense")
async def simulate_defensive_possession(game_id: str) -> Dict:
    """Simulate the opponent's offensive possession.

    When user is on defense, this runs the AI offense until
    the drive ends.
    """
    game = _get_game(game_id)
    manager = game["manager"]
    user_controls_home = game["user_controls_home"]

    # Check user is on defense
    if manager._possession_home == user_controls_home:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot simulate - user is on offense",
        )

    # Run AI drive
    drive_result = manager._play_drive()

    # Broadcast drive result to WebSocket clients
    await connection_manager.broadcast(game_id, {
        "type": "drive_ended",
        "drive_result": {
            "plays": drive_result.play_count,
            "yards": drive_result.total_yards,
            "time_of_possession": f"{drive_result.time_of_possession / 60:.0f}:{drive_result.time_of_possession % 60:02.0f}",
            "result": drive_result.end_reason.value,
            "points_scored": drive_result.points_scored,
        },
    })

    # Broadcast situation update
    situation = _build_situation_response(game_id, manager, user_controls_home)
    await broadcast_situation_update(game_id, situation)

    # Broadcast score if points scored
    if drive_result.points_scored > 0:
        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    return {
        "drive_result": {
            "plays": drive_result.play_count,
            "yards": drive_result.total_yards,
            "time_of_possession": f"{drive_result.time_of_possession / 60:.0f}:{drive_result.time_of_possession % 60:02.0f}",
            "result": drive_result.end_reason.value,
            "points_scored": drive_result.points_scored,
        },
        "new_situation": situation.__dict__,
    }


@router.get("/{game_id}/box-score", response_model=BoxScoreResponse)
async def get_box_score(game_id: str) -> BoxScoreResponse:
    """Get the current box score."""
    # TODO: Implement with ResultHandler
    return BoxScoreResponse(
        home={"total_yards": "0", "passing_yards": "0", "rushing_yards": "0", "first_downs": "0", "turnovers": "0", "time_of_possession": "0:00", "third_down": "0/0"},
        away={"total_yards": "0", "passing_yards": "0", "rushing_yards": "0", "first_downs": "0", "turnovers": "0", "time_of_possession": "0:00", "third_down": "0/0"},
    )


# =============================================================================
# Auto-Play Endpoints (Spectator Mode)
# =============================================================================

@router.post("/{game_id}/auto-play", response_model=AutoPlayResponse)
async def start_auto_play(game_id: str, request: AutoPlayRequest = None) -> AutoPlayResponse:
    """Start auto-play mode for spectator viewing.

    AI controls both teams, streaming play-by-play events to WebSocket clients.
    """
    game = _get_game(game_id)
    auto_state: AutoPlayState = game["auto_play_state"]

    # Check if already running
    if auto_state.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-play is already running",
        )

    # Set pacing
    if request and request.pacing:
        auto_state.pacing = request.pacing

    # Start the auto-play task
    auto_state.is_running = True
    auto_state.is_paused = False
    auto_state.task = asyncio.create_task(_run_auto_play_loop(game_id))

    # Broadcast auto-play started
    await connection_manager.broadcast(game_id, {
        "type": "auto_play_started",
        "pacing": auto_state.pacing.value,
    })

    return AutoPlayResponse(
        message="Auto-play started",
        pacing=auto_state.pacing.value,
        is_running=True,
    )


@router.post("/{game_id}/auto-play/pause")
async def pause_auto_play(game_id: str) -> Dict:
    """Pause auto-play mode."""
    game = _get_game(game_id)
    auto_state: AutoPlayState = game["auto_play_state"]

    if not auto_state.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-play is not running",
        )

    auto_state.is_paused = True

    await connection_manager.broadcast(game_id, {
        "type": "auto_play_paused",
    })

    return {"message": "Auto-play paused", "is_paused": True}


@router.post("/{game_id}/auto-play/resume")
async def resume_auto_play(game_id: str) -> Dict:
    """Resume auto-play mode."""
    game = _get_game(game_id)
    auto_state: AutoPlayState = game["auto_play_state"]

    if not auto_state.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-play is not running",
        )

    auto_state.is_paused = False

    await connection_manager.broadcast(game_id, {
        "type": "auto_play_resumed",
    })

    return {"message": "Auto-play resumed", "is_paused": False}


@router.post("/{game_id}/auto-play/pacing")
async def set_auto_play_pacing(game_id: str, pacing: PacingEnum) -> Dict:
    """Change auto-play pacing."""
    game = _get_game(game_id)
    auto_state: AutoPlayState = game["auto_play_state"]

    auto_state.pacing = pacing

    await connection_manager.broadcast(game_id, {
        "type": "pacing_changed",
        "pacing": pacing.value,
    })

    return {"message": f"Pacing set to {pacing.value}", "pacing": pacing.value}


@router.post("/{game_id}/auto-play/stop")
async def stop_auto_play(game_id: str) -> Dict:
    """Stop auto-play mode."""
    game = _get_game(game_id)
    auto_state: AutoPlayState = game["auto_play_state"]

    if auto_state.task and not auto_state.task.done():
        auto_state.is_running = False
        auto_state.task.cancel()
        try:
            await auto_state.task
        except asyncio.CancelledError:
            pass

    await connection_manager.broadcast(game_id, {
        "type": "auto_play_stopped",
    })

    return {"message": "Auto-play stopped", "is_running": False}


@router.post("/{game_id}/step")
async def step_play(game_id: str) -> Dict:
    """Execute a single play (step mode).

    Runs one play with AI controlling both teams and returns the result.
    Does not require auto-play to be running.
    """
    from huddle.game.coordinator import OffensiveCoordinator, DefensiveCoordinator, SituationContext
    from huddle.game.play_adapter import PlayAdapter

    game = _get_game(game_id)
    manager = game["manager"]
    home_team = game["home_team"]
    away_team = game["away_team"]

    if manager.is_game_over:
        return {"message": "Game is over", "game_over": True}

    # Get current state
    down_state = manager._game_state.down_state
    offense_is_home = manager._possession_home
    offense_team = home_team if offense_is_home else away_team
    defense_team = away_team if offense_is_home else home_team

    # Create coordinators
    oc = OffensiveCoordinator(team=offense_team)
    dc = DefensiveCoordinator()

    # Build situation context
    context = SituationContext(
        down=down_state.down,
        distance=down_state.yards_to_go,
        los=down_state.line_of_scrimmage,
        quarter=manager.quarter,
        time_remaining=manager.time_remaining,
        score_diff=manager.home_score - manager.away_score if offense_is_home else manager.away_score - manager.home_score,
        timeouts=3,
    )

    drive_over = False
    drive_reason = None
    result_data = None

    # Check for 4th down decisions
    if down_state.down == 4:
        from huddle.game.decision_logic import fourth_down_decision, FourthDownDecision

        decision = fourth_down_decision(
            yard_line=int(down_state.line_of_scrimmage),
            yards_to_go=int(down_state.yards_to_go),
            score_diff=context.score_diff,
            time_remaining=int(manager.time_remaining),
        )

        if decision == FourthDownDecision.PUNT:
            result = manager._handle_punt()
            result_data = {
                "type": "special_teams",
                "play_type": "punt",
                "result": result.result,
                "new_los": result.new_los,
                "points_scored": 0,
                "description": f"Punt from the {down_state.line_of_scrimmage:.0f}",
            }
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": result_data})
            drive_over = True
            drive_reason = "punt"

        elif decision == FourthDownDecision.FIELD_GOAL:
            distance = (100 - down_state.line_of_scrimmage) + 17
            result = manager._handle_field_goal(distance)
            points = 3 if result.points > 0 else 0
            if points > 0:
                manager._add_score(3)

            result_data = {
                "type": "special_teams",
                "play_type": "field_goal",
                "result": result.result,
                "new_los": result.new_los,
                "points_scored": points,
                "description": f"{distance:.0f}-yard field goal {'GOOD' if points else 'NO GOOD'}",
            }
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": result_data})
            if points > 0:
                await broadcast_score_update(game_id, manager.home_score, manager.away_score)
            drive_over = True
            drive_reason = "field_goal"

    # Regular play (not 4th down special teams)
    if not drive_over:
        # AI calls the play
        play_code = oc.call_play(context)

        # Get players
        offense, defense = manager._get_players_for_drive()

        # Build play config
        adapter = PlayAdapter(offense, defense)
        config = adapter.build_offensive_config(play_code, shotgun=True)

        # Get AI defensive call
        def_play = dc.call_coverage(context)
        man_assign, zone_assign = adapter.build_defensive_config(def_play)
        config.man_assignments = man_assign
        config.zone_assignments = zone_assign

        # Execute play with frame collection for visualization
        los_y = down_state.line_of_scrimmage
        manager._orchestrator.setup_play(offense, defense, config, los_y)
        result, frames = _run_play_with_frames(manager._orchestrator, offense, defense)

        # Broadcast frames for visualization (before result so client can buffer)
        await connection_manager.broadcast(game_id, {
            "type": "play_frames",
            "frames": frames,
            "total_frames": len(frames),
        })

        # Check for TD
        is_touchdown = down_state.line_of_scrimmage + result.yards_gained >= 100

        # Process result
        old_down = down_state.down
        old_distance = down_state.yards_to_go

        if result.outcome in ("interception", "fumble"):
            is_turnover = True
            drive_over = True
            drive_reason = "turnover"
        elif is_touchdown:
            is_turnover = False
            drive_over = True
            drive_reason = "touchdown"
            manager._add_score(6)
        else:
            is_turnover = False
            # Update down/distance
            if result.yards_gained >= old_distance:
                down_state.down = 1
                down_state.yards_to_go = min(10, int(100 - down_state.line_of_scrimmage - result.yards_gained))
                first_down = True
            else:
                down_state.down += 1
                down_state.yards_to_go = max(1, old_distance - int(result.yards_gained))
                first_down = False

            down_state.line_of_scrimmage += result.yards_gained

            # Check for turnover on downs
            if down_state.down > 4:
                drive_over = True
                drive_reason = "turnover_on_downs"

        # Build description
        description = _format_play_description(result, offense, defense)

        result_data = {
            "outcome": result.outcome,
            "yards_gained": result.yards_gained,
            "description": description,
            "new_down": down_state.down,
            "new_distance": down_state.yards_to_go,
            "new_los": down_state.line_of_scrimmage,
            "first_down": result.yards_gained >= old_distance,
            "touchdown": is_touchdown,
            "turnover": is_turnover,
            "is_drive_over": drive_over,
            "drive_end_reason": drive_reason,
            "play_call": play_code,
            "offense_is_home": offense_is_home,
        }

        # Broadcast play result
        await connection_manager.broadcast(game_id, {"type": "play_result", "result": result_data})

        # Broadcast situation update
        situation = _build_situation_response(game_id, manager, False)
        await connection_manager.broadcast(game_id, {"type": "situation_update", "situation": situation.__dict__})

        # Handle touchdown scoring
        if is_touchdown:
            await broadcast_score_update(game_id, manager.home_score, manager.away_score)

            # Handle PAT
            pat_result = manager._handle_pat(go_for_two=False)
            if pat_result.points > 0:
                manager._add_score(1)
                await broadcast_score_update(game_id, manager.home_score, manager.away_score)

            await connection_manager.broadcast(game_id, {
                "type": "special_teams",
                "result": {
                    "play_type": "pat",
                    "result": pat_result.result,
                    "new_los": 25.0,
                    "points_scored": pat_result.points,
                    "description": f"Extra point {'GOOD' if pat_result.points > 0 else 'NO GOOD'}",
                },
            })

    # Handle drive end and possession change
    if drive_over:
        await connection_manager.broadcast(game_id, {
            "type": "drive_ended",
            "offense": offense_team.abbreviation,
            "result": drive_reason,
        })

        if not manager.is_game_over:
            # Possession change
            if drive_reason == "touchdown":
                kickoff_result = manager._handle_kickoff(onside=False)
                manager._possession_home = not manager._possession_home
                down_state.line_of_scrimmage = kickoff_result.new_los
                down_state.down = 1
                down_state.yards_to_go = 10

                await connection_manager.broadcast(game_id, {
                    "type": "special_teams",
                    "result": {
                        "play_type": "kickoff",
                        "result": kickoff_result.result,
                        "new_los": kickoff_result.new_los,
                        "points_scored": 0,
                        "description": f"Kickoff returned to the {kickoff_result.new_los:.0f}",
                    },
                })
            elif drive_reason in ("punt", "field_goal", "turnover", "turnover_on_downs"):
                manager._possession_home = not manager._possession_home
                down_state.down = 1
                down_state.yards_to_go = 10

            # Broadcast new drive start
            new_offense = home_team if manager._possession_home else away_team
            await connection_manager.broadcast(game_id, {
                "type": "drive_start",
                "offense": new_offense.abbreviation,
                "offense_is_home": manager._possession_home,
                "starting_los": down_state.line_of_scrimmage,
                "quarter": manager.quarter,
                "time_remaining": f"{int(manager.time_remaining // 60)}:{int(manager.time_remaining % 60):02d}",
            })

    # Check for game over
    if manager.is_game_over:
        await connection_manager.broadcast(game_id, {
            "type": "game_over",
            "home_score": manager.home_score,
            "away_score": manager.away_score,
            "winner": "home" if manager.home_score > manager.away_score else "away" if manager.away_score > manager.home_score else "tie",
        })

    return {
        "message": "Play executed",
        "result": result_data,
        "game_over": manager.is_game_over,
    }


async def _run_auto_play_loop(game_id: str):
    """Background task that runs the game automatically.

    Executes plays for both teams using AI coordinators,
    broadcasting results to WebSocket clients.
    """
    from huddle.game.coordinator import OffensiveCoordinator, DefensiveCoordinator, SituationContext
    from huddle.game.play_adapter import PlayAdapter

    game = _active_games.get(game_id)
    if not game:
        return

    manager = game["manager"]
    home_team = game["home_team"]
    away_team = game["away_team"]
    auto_state: AutoPlayState = game["auto_play_state"]

    # Create coordinators for both teams
    home_oc = OffensiveCoordinator(team=home_team)
    away_oc = OffensiveCoordinator(team=away_team)
    dc = DefensiveCoordinator()

    try:
        while auto_state.is_running and not manager.is_game_over:
            # Handle pause
            while auto_state.is_paused and auto_state.is_running:
                await asyncio.sleep(0.1)

            if not auto_state.is_running:
                break

            # Get current situation
            down_state = manager._game_state.down_state
            offense_is_home = manager._possession_home
            offense_team = home_team if offense_is_home else away_team
            defense_team = away_team if offense_is_home else home_team
            oc = home_oc if offense_is_home else away_oc

            # Broadcast drive start
            await connection_manager.broadcast(game_id, {
                "type": "drive_start",
                "offense": offense_team.abbreviation,
                "offense_is_home": offense_is_home,
                "starting_los": down_state.line_of_scrimmage,
                "quarter": manager.quarter,
                "time_remaining": f"{int(manager.time_remaining // 60)}:{int(manager.time_remaining % 60):02d}",
            })

            # Run plays until drive ends
            drive_over = False
            plays_this_drive = 0

            while not drive_over and auto_state.is_running and not manager.is_game_over:
                # Handle pause
                while auto_state.is_paused and auto_state.is_running:
                    await asyncio.sleep(0.1)

                if not auto_state.is_running:
                    break

                # Build situation context
                context = SituationContext(
                    down=down_state.down,
                    distance=down_state.yards_to_go,
                    los=down_state.line_of_scrimmage,
                    quarter=manager.quarter,
                    time_remaining=manager.time_remaining,
                    score_diff=manager.home_score - manager.away_score if offense_is_home else manager.away_score - manager.home_score,
                    timeouts=3,
                )

                # Check for 4th down decisions
                if down_state.down == 4:
                    # Use decision logic
                    from huddle.game.decision_logic import fourth_down_decision, FourthDownDecision

                    decision = fourth_down_decision(
                        yard_line=down_state.line_of_scrimmage,
                        distance=down_state.yards_to_go,
                        score_diff=context.score_diff,
                        time_remaining=manager.time_remaining,
                    )

                    if decision == FourthDownDecision.PUNT:
                        result = manager._handle_punt()
                        await connection_manager.broadcast(game_id, {
                            "type": "special_teams",
                            "result": {
                                "play_type": "punt",
                                "result": result.result,
                                "new_los": result.new_los,
                                "points_scored": 0,
                                "description": f"Punt from the {down_state.line_of_scrimmage:.0f}",
                            },
                        })
                        drive_over = True
                        continue

                    elif decision == FourthDownDecision.FIELD_GOAL:
                        distance = (100 - down_state.line_of_scrimmage) + 17
                        result = manager._handle_field_goal(distance)
                        points = 3 if result.points > 0 else 0
                        if points > 0:
                            manager._add_score(3)

                        await connection_manager.broadcast(game_id, {
                            "type": "special_teams",
                            "result": {
                                "play_type": "field_goal",
                                "result": result.result,
                                "new_los": result.new_los,
                                "points_scored": points,
                                "description": f"{distance:.0f}-yard field goal {'GOOD' if points else 'NO GOOD'}",
                            },
                        })

                        if points > 0:
                            await broadcast_score_update(game_id, manager.home_score, manager.away_score)

                        drive_over = True
                        continue

                # AI calls the play
                play_code = oc.call_play(context)

                # Get players
                offense, defense = manager._get_players_for_drive()

                # Build play config
                adapter = PlayAdapter(offense, defense)
                config = adapter.build_offensive_config(play_code, shotgun=True)

                # Get AI defensive call
                def_play = dc.call_coverage(context)
                man_assign, zone_assign = adapter.build_defensive_config(def_play)
                config.man_assignments = man_assign
                config.zone_assignments = zone_assign

                # Execute play
                los_y = down_state.line_of_scrimmage
                manager._orchestrator.setup_play(offense, defense, config, los_y)
                result = manager._orchestrator.run()

                plays_this_drive += 1

                # Check for TD
                is_touchdown = down_state.line_of_scrimmage + result.yards_gained >= 100

                # Process result
                old_down = down_state.down
                old_distance = down_state.yards_to_go

                if result.outcome in ("interception", "fumble"):
                    is_turnover = True
                    drive_over = True
                    drive_reason = "turnover"
                elif is_touchdown:
                    is_turnover = False
                    drive_over = True
                    drive_reason = "touchdown"
                    manager._add_score(6)
                else:
                    is_turnover = False
                    # Update down/distance
                    if result.yards_gained >= old_distance:
                        down_state.down = 1
                        down_state.yards_to_go = min(10, int(100 - down_state.line_of_scrimmage - result.yards_gained))
                        first_down = True
                    else:
                        down_state.down += 1
                        down_state.yards_to_go = max(1, old_distance - int(result.yards_gained))
                        first_down = False

                    down_state.line_of_scrimmage += result.yards_gained

                    # Check for turnover on downs
                    if down_state.down > 4:
                        drive_over = True
                        drive_reason = "turnover_on_downs"
                    else:
                        drive_over = False
                        drive_reason = None

                # Build description
                description = _format_play_description(result, offense, defense)

                # Broadcast play result
                await connection_manager.broadcast(game_id, {
                    "type": "play_result",
                    "result": {
                        "outcome": result.outcome,
                        "yards_gained": result.yards_gained,
                        "description": description,
                        "new_down": down_state.down,
                        "new_distance": down_state.yards_to_go,
                        "new_los": down_state.line_of_scrimmage,
                        "first_down": result.yards_gained >= old_distance,
                        "touchdown": is_touchdown,
                        "turnover": is_turnover,
                        "is_drive_over": drive_over,
                        "drive_end_reason": drive_reason if drive_over else None,
                        "play_call": play_code,
                        "offense_is_home": offense_is_home,
                    },
                })

                # Broadcast situation update
                situation = _build_situation_response(game_id, manager, False)
                await connection_manager.broadcast(game_id, {
                    "type": "situation_update",
                    "situation": situation.__dict__,
                })

                # Broadcast score if touchdown
                if is_touchdown:
                    await broadcast_score_update(game_id, manager.home_score, manager.away_score)

                    # Handle PAT (auto-kick for now)
                    pat_result = manager._handle_pat(go_for_two=False)
                    if pat_result.points > 0:
                        manager._add_score(1)
                        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

                    await connection_manager.broadcast(game_id, {
                        "type": "special_teams",
                        "result": {
                            "play_type": "pat",
                            "result": pat_result.result,
                            "new_los": 25.0,
                            "points_scored": pat_result.points,
                            "description": f"Extra point {'GOOD' if pat_result.points > 0 else 'NO GOOD'}",
                        },
                    })

                # Delay based on pacing
                await asyncio.sleep(auto_state.delay_seconds)

            # Drive ended - broadcast summary
            await connection_manager.broadcast(game_id, {
                "type": "drive_ended",
                "offense": offense_team.abbreviation,
                "plays": plays_this_drive,
                "result": drive_reason if drive_over else "in_progress",
            })

            # Handle possession change
            if not manager.is_game_over:
                # Handle kickoff after scoring
                if drive_reason == "touchdown":
                    kickoff_result = manager._handle_kickoff(onside=False)
                    manager._possession_home = not manager._possession_home
                    down_state.line_of_scrimmage = kickoff_result.new_los
                    down_state.down = 1
                    down_state.yards_to_go = 10

                    await connection_manager.broadcast(game_id, {
                        "type": "special_teams",
                        "result": {
                            "play_type": "kickoff",
                            "result": kickoff_result.result,
                            "new_los": kickoff_result.new_los,
                            "points_scored": 0,
                            "description": "Kickoff - " + ("Touchback" if kickoff_result.result == "touchback" else f"Returned to the {kickoff_result.new_los:.0f}"),
                        },
                    })

                elif drive_reason in ("turnover", "turnover_on_downs", "punt"):
                    # Flip possession
                    manager._possession_home = not manager._possession_home
                    # Flip field position
                    down_state.line_of_scrimmage = 100 - down_state.line_of_scrimmage
                    down_state.down = 1
                    down_state.yards_to_go = 10

                await asyncio.sleep(auto_state.delay_seconds)

        # Game over
        if manager.is_game_over:
            winner = "home" if manager.home_score > manager.away_score else ("away" if manager.away_score > manager.home_score else "tie")
            await broadcast_game_over(game_id, manager.home_score, manager.away_score, winner)

    except asyncio.CancelledError:
        # Task was cancelled (auto-play stopped)
        pass
    except Exception as e:
        # Broadcast error
        await connection_manager.broadcast(game_id, {
            "type": "error",
            "message": f"Auto-play error: {str(e)}",
        })
    finally:
        auto_state.is_running = False
        auto_state.task = None


@router.delete("/{game_id}")
async def end_game(game_id: str) -> Dict:
    """End a game session."""
    if game_id in _active_games:
        # Notify connected clients
        await connection_manager.broadcast(game_id, {
            "type": "game_ended",
            "message": "Game session ended",
        })
        del _active_games[game_id]
        return {"message": f"Game {game_id} ended"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Game {game_id} not found",
    )


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/{game_id}/stream")
async def game_stream(websocket: WebSocket, game_id: str):
    """WebSocket endpoint for real-time game streaming.

    Clients connect to receive live play-by-play updates.

    Message Types Sent:
    - connected: Initial connection confirmation with current situation
    - play_result: Result of an executed play
    - special_teams: Result of special teams play
    - drive_ended: Drive finished (TD, FG, punt, turnover)
    - quarter_changed: Quarter transition
    - score_update: Score changed
    - game_over: Game has ended
    - error: Error message

    Message Types Received:
    - ping: Keep-alive (responds with pong)
    - get_situation: Request current situation
    """
    # Verify game exists
    if game_id not in _active_games:
        await websocket.close(code=4004, reason="Game not found")
        return

    await connection_manager.connect(websocket, game_id)

    try:
        game = _active_games[game_id]
        manager = game["manager"]
        user_controls_home = game["user_controls_home"]

        # Send initial situation
        situation = _build_situation_response(game_id, manager, user_controls_home)
        await connection_manager.send_personal(websocket, {
            "type": "connected",
            "game_id": game_id,
            "situation": situation.__dict__,
            "connections": connection_manager.get_connection_count(game_id),
        })

        # Listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0  # 60 second timeout
                )

                msg_type = data.get("type", "")

                if msg_type == "ping":
                    await connection_manager.send_personal(websocket, {
                        "type": "pong",
                        "timestamp": data.get("timestamp"),
                    })

                elif msg_type == "get_situation":
                    situation = _build_situation_response(game_id, manager, user_controls_home)
                    await connection_manager.send_personal(websocket, {
                        "type": "situation",
                        "situation": situation.__dict__,
                    })

                # Auto-play control messages
                elif msg_type == "pause":
                    auto_state = game.get("auto_play_state")
                    if auto_state and auto_state.is_running:
                        auto_state.is_paused = True
                        await connection_manager.broadcast(game_id, {"type": "auto_play_paused"})

                elif msg_type == "resume":
                    auto_state = game.get("auto_play_state")
                    if auto_state and auto_state.is_running:
                        auto_state.is_paused = False
                        await connection_manager.broadcast(game_id, {"type": "auto_play_resumed"})

                elif msg_type == "set_pacing":
                    auto_state = game.get("auto_play_state")
                    if auto_state:
                        pacing_str = data.get("payload", {}).get("pacing", "normal")
                        try:
                            auto_state.pacing = PacingEnum(pacing_str)
                            await connection_manager.broadcast(game_id, {
                                "type": "pacing_changed",
                                "pacing": auto_state.pacing.value,
                            })
                        except ValueError:
                            await connection_manager.send_personal(websocket, {
                                "type": "error",
                                "message": f"Invalid pacing value: {pacing_str}",
                            })

                elif msg_type == "stop_auto_play":
                    auto_state = game.get("auto_play_state")
                    if auto_state and auto_state.task and not auto_state.task.done():
                        auto_state.is_running = False
                        auto_state.task.cancel()
                        await connection_manager.broadcast(game_id, {"type": "auto_play_stopped"})

                else:
                    await connection_manager.send_personal(websocket, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })

            except asyncio.TimeoutError:
                # Send keep-alive ping
                await connection_manager.send_personal(websocket, {
                    "type": "keep_alive",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await connection_manager.send_personal(websocket, {
            "type": "error",
            "message": str(e),
        })
    finally:
        connection_manager.disconnect(websocket, game_id)


async def broadcast_play_result(game_id: str, result: PlayResultResponse):
    """Broadcast a play result to all connected clients."""
    await connection_manager.broadcast(game_id, {
        "type": "play_result",
        "result": {
            "outcome": result.outcome,
            "yards_gained": result.yards_gained,
            "description": result.description,
            "new_down": result.new_down,
            "new_distance": result.new_distance,
            "new_los": result.new_los,
            "first_down": result.first_down,
            "touchdown": result.touchdown,
            "turnover": result.turnover,
            "is_drive_over": result.is_drive_over,
            "drive_end_reason": result.drive_end_reason,
        },
    })


async def broadcast_special_teams(game_id: str, result: SpecialTeamsResultResponse):
    """Broadcast a special teams result to all connected clients."""
    await connection_manager.broadcast(game_id, {
        "type": "special_teams",
        "result": {
            "play_type": result.play_type,
            "result": result.result,
            "new_los": result.new_los,
            "points_scored": result.points_scored,
            "description": result.description,
        },
    })


async def broadcast_situation_update(game_id: str, situation: GameSituationResponse):
    """Broadcast updated situation to all connected clients."""
    await connection_manager.broadcast(game_id, {
        "type": "situation_update",
        "situation": situation.__dict__,
    })


async def broadcast_score_update(game_id: str, home_score: int, away_score: int):
    """Broadcast score update to all connected clients."""
    await connection_manager.broadcast(game_id, {
        "type": "score_update",
        "home_score": home_score,
        "away_score": away_score,
    })


async def broadcast_game_over(game_id: str, home_score: int, away_score: int, winner: str):
    """Broadcast game over to all connected clients."""
    await connection_manager.broadcast(game_id, {
        "type": "game_over",
        "final_score": {
            "home": home_score,
            "away": away_score,
        },
        "winner": winner,
    })


# =============================================================================
# Helper Functions
# =============================================================================

def _build_situation_response(
    game_id: str,
    manager,
    user_controls_home: bool,
) -> GameSituationResponse:
    """Build a GameSituationResponse from manager state."""
    down_state = manager._game_state.down_state

    # Determine phase enum
    phase_map = {
        1: GamePhaseEnum.FIRST_QUARTER,
        2: GamePhaseEnum.SECOND_QUARTER,
        3: GamePhaseEnum.THIRD_QUARTER,
        4: GamePhaseEnum.FOURTH_QUARTER,
        5: GamePhaseEnum.OVERTIME,
    }
    phase = phase_map.get(manager.quarter, GamePhaseEnum.FIRST_QUARTER)
    if manager.is_game_over:
        phase = GamePhaseEnum.FINAL

    # Format time
    mins = int(manager.time_remaining // 60)
    secs = int(manager.time_remaining % 60)
    time_str = f"{mins}:{secs:02d}"

    # Yard line display
    los = down_state.line_of_scrimmage
    if los >= 50:
        yard_line = f"OPP {100 - los:.0f}"
    else:
        yard_line = f"OWN {los:.0f}"

    return GameSituationResponse(
        game_id=game_id,
        quarter=manager.quarter,
        time_remaining=time_str,
        home_score=manager.home_score,
        away_score=manager.away_score,
        possession_home=manager._possession_home,
        down=down_state.down,
        distance=down_state.yards_to_go,
        los=los,
        yard_line_display=yard_line,
        is_red_zone=los >= 80,
        is_goal_to_go=down_state.yards_to_go >= (100 - los),
        phase=phase,
        user_on_offense=manager._possession_home == user_controls_home,
        user_on_defense=manager._possession_home != user_controls_home,
    )


def _get_situation_plays(context) -> list:
    """Get appropriate plays for the situation."""
    from huddle.core.playbook.play_codes import OFFENSIVE_PLAYS

    # Start with all plays
    plays = list(OFFENSIVE_PLAYS.keys())

    # Filter based on situation
    if context.is_short_yardage:
        # Prefer power runs and quick passes
        preferred = [p for p in plays if "POWER" in p or "SNEAK" in p or "SLANT" in p or "HITCH" in p]
        return preferred + [p for p in plays if p not in preferred]

    if context.is_long_yardage:
        # Prefer deep passes and screens
        preferred = [p for p in plays if "VERTS" in p or "POST" in p or "CORNER" in p or "SCREEN" in p]
        return preferred + [p for p in plays if p not in preferred]

    return plays


def _generate_situation_tips(context) -> list:
    """Generate situational tips for play selection."""
    tips = []

    if context.down == 1:
        tips.append("1st down - establish the run or take a shot")
    elif context.down == 2:
        if context.distance <= 4:
            tips.append("2nd and short - good position, can be aggressive")
        elif context.distance >= 8:
            tips.append("2nd and long - need chunk play to get manageable 3rd down")
    elif context.down == 3:
        if context.distance <= 3:
            tips.append("3rd and short - run or quick pass")
        elif context.distance >= 10:
            tips.append("3rd and long - need conversion, consider screens")

    if context.is_red_zone:
        tips.append("Red zone - tighter windows, consider fades and slants")

    if context.game_situation.value == "two_minute":
        tips.append("Two-minute drill - quick passes, stay in bounds")

    return tips


def _format_play_description(result, offense, defense) -> str:
    """Format a human-readable play description."""
    passer = _get_player_name(result.passer_id, offense) or "QB"
    receiver = _get_player_name(result.receiver_id, offense) or "receiver"
    tackler = _get_player_name(result.tackler_id, defense) or "defender"

    if result.outcome == "complete":
        return f"{passer} pass complete to {receiver} for {result.yards_gained:.0f} yards"
    elif result.outcome == "incomplete":
        return f"{passer} pass incomplete intended for {receiver}"
    elif result.outcome == "interception":
        return f"{passer} INTERCEPTED by {tackler}"
    elif result.outcome == "sack":
        return f"{passer} sacked by {tackler} for {abs(result.yards_gained):.0f} yard loss"
    elif result.outcome == "run":
        return f"{receiver} runs for {result.yards_gained:.0f} yards"
    elif result.outcome == "fumble":
        return f"{receiver} FUMBLES, recovered by defense"
    else:
        return f"Play result: {result.outcome}, {result.yards_gained:.0f} yards"


def _get_player_name(player_id: Optional[str], players: list) -> Optional[str]:
    """Get player name from ID."""
    if not player_id:
        return None
    for p in players:
        if p.id == player_id:
            return p.name
    return None
