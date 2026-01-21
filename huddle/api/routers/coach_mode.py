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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import asyncio

import orjson
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from huddle.simulation.v2.core.entities import Player, Team, Position
from huddle.simulation.v2.core.phases import PlayPhase
from huddle.simulation.v2.core.huddle_positions import HuddleConfig, DEFAULT_HUDDLE_CONFIG
from huddle.simulation.v2.orchestrator import Orchestrator
from huddle.simulation.v2.systems.coverage import CoverageType
from huddle.core.models.field import FieldPosition

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

def _player_to_frame_dict_fast(
    player: Player,
    los_y: float,
    route_assignment: Optional[Any],
    coverage_assignment: Optional[Any],
    engagement: Optional[Any],
    ball_carrier_id: Optional[str],
    ball_carrier_pos: Optional[tuple],
    tackle_engagement: Optional[Any],
    phase: PlayPhase,
) -> Dict[str, Any]:
    """Convert player state to dict for visualization (optimized version).

    Takes pre-built lookups for O(1) access instead of repeated O(n) lookups.

    IMPORTANT: Coordinates are converted to LOS-relative format for the frontend:
    - x: lateral position (0 = center, negative = left, positive = right)
    - y: depth from LOS (0 = at LOS, negative = backfield, positive = downfield)
    """
    rel_y = player.pos.y - los_y

    data = {
        "id": player.id,
        "name": player.name,
        "team": player.team.value,
        "position": player.position.value if player.position else "unknown",
        "x": player.pos.x,
        "y": rel_y,
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

    # Route info (for receivers) - using pre-built lookup
    if route_assignment:
        data["route_name"] = route_assignment.route.name
        data["route_phase"] = route_assignment.phase.value
        data["current_waypoint"] = route_assignment.current_waypoint_idx
        data["total_waypoints"] = len(route_assignment.route.waypoints)
        if route_assignment.current_target:
            data["target_x"] = route_assignment.current_target.x
            data["target_y"] = route_assignment.current_target.y - los_y

    # Coverage info (for defenders) - using pre-built lookup
    if coverage_assignment:
        data["coverage_type"] = coverage_assignment.coverage_type.value
        data["coverage_phase"] = coverage_assignment.phase.value

        if coverage_assignment.coverage_type == CoverageType.MAN:
            data["man_target_id"] = coverage_assignment.man_target_id
            data["has_recognized_break"] = coverage_assignment.has_reacted_to_break
        else:
            data["zone_type"] = coverage_assignment.zone_type.value if coverage_assignment.zone_type else None
            data["has_triggered"] = coverage_assignment.has_triggered

    # Blocking engagement info - using pre-built lookup
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
        if tackle_engagement:
            data["in_tackle"] = True
            data["tackle_leverage"] = tackle_engagement.leverage

    # Pursuit target for defenders
    if ball_carrier_id and player.team == Team.DEFENSE and ball_carrier_pos:
        if phase in (PlayPhase.AFTER_CATCH, PlayPhase.RUN_ACTIVE):
            data["pursuit_target_x"] = ball_carrier_pos[0]
            data["pursuit_target_y"] = ball_carrier_pos[1] - los_y

    return data


def _player_to_frame_dict(
    player: Player,
    orchestrator: Orchestrator,
    ball_carrier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert player state to dict for visualization (legacy version).

    Simplified version of v2_sim.player_to_dict focused on essential fields.
    Use _player_to_frame_dict_fast with pre-built lookups for better performance.
    """
    los_y = orchestrator.los_y
    route_assignment = orchestrator.route_runner.get_assignment(player.id)
    coverage_assignment = orchestrator.coverage_system.assignments.get(player.id)
    engagement = orchestrator.block_resolver.get_engagement_for_player(player.id)

    ball_carrier_pos = None
    if ball_carrier_id:
        for p in orchestrator.offense:
            if p.id == ball_carrier_id:
                ball_carrier_pos = (p.pos.x, p.pos.y)
                break

    tackle_engagement = None
    if player.id == ball_carrier_id:
        tackle_engagement = orchestrator.tackle_resolver.get_engagement(player.id)

    return _player_to_frame_dict_fast(
        player, los_y, route_assignment, coverage_assignment,
        engagement, ball_carrier_id, ball_carrier_pos, tackle_engagement,
        orchestrator.phase
    )


def _collect_frame(
    orchestrator: Orchestrator,
    offense: List[Player],
    defense: List[Player],
    ball_carrier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Collect a single frame of play state for visualization.

    Optimized with pre-built lookups for O(1) access instead of O(n) per player.
    """
    los_y = orchestrator.los_y
    phase = orchestrator.phase

    # Pre-build lookup dictionaries once per frame for O(1) access
    route_assignments = {
        player.id: orchestrator.route_runner.get_assignment(player.id)
        for player in offense
    }
    coverage_assignments = dict(orchestrator.coverage_system.assignments)

    # Build engagement lookup - get all engagements once
    engagements = {}
    if hasattr(orchestrator.block_resolver, 'get_all_engagements'):
        engagements = orchestrator.block_resolver.get_all_engagements()
    else:
        # Fallback: build from individual lookups
        for player in offense + defense:
            eng = orchestrator.block_resolver.get_engagement_for_player(player.id)
            if eng:
                engagements[player.id] = eng

    # Find ball carrier position once
    ball_carrier_pos = None
    if ball_carrier_id:
        for p in offense:
            if p.id == ball_carrier_id:
                ball_carrier_pos = (p.pos.x, p.pos.y)
                break

    # Get tackle engagement for ball carrier
    tackle_engagement = None
    if ball_carrier_id:
        tackle_engagement = orchestrator.tackle_resolver.get_engagement(ball_carrier_id)

    # Build player data with O(1) lookups
    players = []
    waypoints = {}

    for player in offense + defense:
        route_assignment = route_assignments.get(player.id)
        coverage_assignment = coverage_assignments.get(player.id)
        engagement = engagements.get(player.id)

        player_tackle = tackle_engagement if player.id == ball_carrier_id else None

        players.append(_player_to_frame_dict_fast(
            player, los_y, route_assignment, coverage_assignment,
            engagement, ball_carrier_id, ball_carrier_pos, player_tackle, phase
        ))

        # Collect waypoints for receivers
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

    # Ball state (LOS-relative coordinates)
    ball = orchestrator.ball
    current_time = orchestrator.clock.current_time

    # Calculate current ball height (approximation for visualization)
    ball_height = 0.0
    if ball.is_in_flight and ball.flight_duration > 0:
        t = (current_time - ball.flight_start_time) / ball.flight_duration
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        # Parabolic arc: h = release + 4*peak*t*(1-t)
        ball_height = ball.release_height + 4 * ball.peak_height * t * (1 - t)
    elif ball.is_held:
        ball_height = 2.0  # ~6 feet when held

    ball_data = {
        "x": ball.pos.x,
        "y": ball.pos.y - los_y,  # LOS-relative
        "height": ball_height,
        "state": ball.state.value,
        "carrier_id": ball.carrier_id,
        # Spin physics data (only meaningful during flight)
        "spin_rate": ball.spin_rate if ball.is_in_flight else 0,
        "is_stable": ball.is_stable_spiral,
    }

    # Add orientation during flight for ball visualization
    if ball.is_in_flight and ball.flight_duration > 0:
        progress = (current_time - ball.flight_start_time) / ball.flight_duration
        progress = max(0.0, min(1.0, progress))
        ox, oy, oz = ball.orientation_at_progress(progress)
        ball_data["orientation"] = {"x": ox, "y": oy, "z": oz}

    return {
        "tick": orchestrator.clock.tick_count,
        "time": current_time,
        "phase": phase.value,
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


def _run_huddle_with_frames(
    orchestrator: Orchestrator,
    offense: List[Player],
    defense: List[Player],
    next_los_y: float,
    ball_x: float = 0.0,
    config: HuddleConfig = None,
) -> List[Dict]:
    """Run huddle transition, collecting frames for visualization.

    Animates players moving from their current positions (post-play) to
    huddle formation, then breaking to pre-snap positions.

    Args:
        orchestrator: The orchestrator instance (must be in POST_PLAY phase)
        offense: List of offensive players
        defense: List of defensive players
        next_los_y: Line of scrimmage for the next play
        ball_x: X coordinate of the ball (hash position)
        config: Optional huddle configuration

    Returns:
        List of frame dicts for visualization
    """
    frames = []

    # Ensure we're in POST_PLAY phase
    if orchestrator.phase != PlayPhase.POST_PLAY:
        # Force transition to POST_PLAY if needed (e.g., between plays)
        orchestrator._phase_machine.reset(PlayPhase.POST_PLAY)

    # Start huddle phase
    orchestrator.start_huddle_phase(next_los_y, ball_x, config)

    # Collect initial frame
    frames.append(_collect_frame(orchestrator, offense, defense, None))

    # Safety limit to prevent infinite loops
    max_huddle_ticks = 400  # ~20 seconds at 20 ticks/sec

    # Run tick-by-tick until we reach PRE_SNAP
    tick_count = 0
    while orchestrator.phase in (PlayPhase.HUDDLE, PlayPhase.FORMATION_MOVE):
        if tick_count >= max_huddle_ticks:
            # Force transition to PRE_SNAP if taking too long
            orchestrator._transition_to(PlayPhase.PRE_SNAP, "huddle timeout", validate=False)
            break

        dt = orchestrator.clock.tick()
        orchestrator._update_tick(dt)
        frames.append(_collect_frame(orchestrator, offense, defense, None))
        tick_count += 1

    return frames


async def _execute_auto_play_with_frames(
    game_id: str,
    manager,
    home_team,
    away_team,
    offense_is_home: bool,
    plays_this_drive: int,
) -> tuple:
    """Execute one AI-controlled play with frame collection and huddle animation.

    Args:
        game_id: The game ID for broadcasting
        manager: The GameManager instance
        home_team: Home team object
        away_team: Away team object
        offense_is_home: Whether home team is on offense
        plays_this_drive: Number of plays already run this drive (0 = first play)

    Returns:
        Tuple of (play_result dict, play_code) or (None, None) for special teams
    """
    from huddle.game.coordinator import OffensiveCoordinator, SituationContext
    from huddle.game.decision_logic import fourth_down_decision, FourthDownDecision

    offense_team = home_team if offense_is_home else away_team
    situation = manager.get_situation()
    los_value = situation["los"]

    # Check for 4th down decisions
    if situation["down"] == 4:
        context = SituationContext(
            down=situation["down"],
            distance=situation["distance"],
            los=los_value,
            quarter=situation["quarter"],
            time_remaining=manager.time_remaining,
            score_diff=situation["home_score"] - situation["away_score"] if offense_is_home else situation["away_score"] - situation["home_score"],
            timeouts=situation["home_timeouts"] if offense_is_home else situation["away_timeouts"],
        )

        decision = fourth_down_decision(
            yard_line=int(los_value),
            yards_to_go=int(situation["distance"]),
            score_diff=context.score_diff,
            time_remaining=int(manager.time_remaining),
        )

        if decision == FourthDownDecision.PUNT:
            st_result = manager.execute_special_teams("punt")
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": st_result})
            return None, None

        elif decision == FourthDownDecision.FIELD_GOAL:
            st_result = manager.execute_special_teams("field_goal")
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": st_result})
            if st_result["points_scored"] > 0:
                await broadcast_score_update(game_id, manager.home_score, manager.away_score)
            return None, None

    # AI calls the play
    context = SituationContext(
        down=situation["down"],
        distance=situation["distance"],
        los=los_value,
        quarter=situation["quarter"],
        time_remaining=manager.time_remaining,
        score_diff=situation["home_score"] - situation["away_score"] if offense_is_home else situation["away_score"] - situation["home_score"],
        timeouts=situation["home_timeouts"] if offense_is_home else situation["away_timeouts"],
    )
    oc = OffensiveCoordinator(team=offense_team)
    play_code = oc.call_play(context)

    # Set up play with GameManager (for frame collection)
    orchestrator, offense, defense = manager.execute_play_by_code_with_frames(play_code, shotgun=True)

    # Run huddle transition if not first play of drive
    if plays_this_drive > 0:
        ball_x = situation.get("ball_x", 0.0)
        huddle_frames = _run_huddle_with_frames(
            orchestrator, offense, defense, los_value, ball_x
        )

        # Broadcast huddle frames
        await connection_manager.broadcast(game_id, {
            "type": "huddle_frames",
            "frames": huddle_frames,
            "total_frames": len(huddle_frames),
        })

        # Small delay to let frontend render huddle (real-time at ~20fps)
        await asyncio.sleep(len(huddle_frames) * 0.05)

    # Run play with frame collection
    result, play_frames = _run_play_with_frames(orchestrator, offense, defense)

    # Broadcast play frames
    await connection_manager.broadcast(game_id, {
        "type": "play_frames",
        "frames": play_frames,
        "total_frames": len(play_frames),
    })

    # Small delay to let frontend render play
    await asyncio.sleep(len(play_frames) * 0.05)

    # Finalize result
    play_result = manager.finalize_play_result(result)

    # Build and broadcast text result
    description = _format_play_description_from_dict(play_result, offense, defense)
    await connection_manager.broadcast(game_id, {
        "type": "play_result",
        "result": {
            "outcome": play_result["outcome"],
            "yards_gained": play_result["yards_gained"],
            "description": description,
            "new_down": play_result["new_down"],
            "new_distance": play_result["new_distance"],
            "new_los": play_result["new_los"],
            "first_down": play_result["is_first_down"],
            "touchdown": play_result["is_touchdown"],
            "turnover": play_result["is_turnover"],
            "is_drive_over": play_result["is_drive_over"],
            "drive_end_reason": play_result["drive_end_reason"],
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

    # Handle touchdown scoring sequence
    if play_result["is_touchdown"]:
        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

        # Handle PAT via GameManager
        pat_result = manager.execute_special_teams("pat", go_for_two=False)
        await connection_manager.broadcast(game_id, {
            "type": "special_teams",
            "result": pat_result,
        })
        if pat_result["points_scored"] > 0:
            await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    return play_result, play_code


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
    stream_frames: bool = True  # If True, stream visualization frames (with huddle)

    @property
    def delay_seconds(self) -> float:
        """Get delay between plays based on pacing.

        When streaming frames, delay is minimal since frame rendering provides pacing.
        """
        if self.stream_frames:
            # Frames provide natural pacing, just a brief delay for network
            return 0.1
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
        """Send a message to all clients connected to a game.

        Pre-serializes the message once with orjson for better performance
        when broadcasting to multiple clients.
        """
        if game_id not in self.active_connections:
            return

        # Pre-serialize once with orjson (5-10x faster than stdlib json)
        serialized = orjson.dumps(message)

        disconnected = []
        for connection in self.active_connections[game_id]:
            try:
                await connection.send_bytes(serialized)
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
# In-Memory Game Session Store with TTL
# =============================================================================

@dataclass
class GameSession:
    """A game session with metadata for TTL tracking."""
    data: dict
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class GameSessionManager:
    """Manages game sessions with TTL-based expiration.

    Prevents memory leaks from abandoned game sessions by automatically
    cleaning up sessions that haven't been accessed within the TTL.
    """

    def __init__(self, ttl_minutes: int = 60):
        self._sessions: Dict[str, GameSession] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get(self, game_id: str) -> Optional[dict]:
        """Get a session, updating last_activity timestamp."""
        session = self._sessions.get(game_id)
        if session:
            session.last_activity = datetime.utcnow()
            return session.data
        return None

    def set(self, game_id: str, data: dict):
        """Create or update a session."""
        self._sessions[game_id] = GameSession(data=data)

    def delete(self, game_id: str):
        """Remove a session."""
        self._sessions.pop(game_id, None)

    def contains(self, game_id: str) -> bool:
        """Check if a session exists."""
        return game_id in self._sessions

    def cleanup_expired(self):
        """Remove sessions older than TTL."""
        now = datetime.utcnow()
        expired = [
            gid for gid, session in self._sessions.items()
            if now - session.last_activity > self._ttl
        ]
        for gid in expired:
            # Clean up auto-play tasks if running
            session = self._sessions.get(gid)
            if session and session.data.get("auto_play_state"):
                auto_state = session.data["auto_play_state"]
                if auto_state.task and not auto_state.task.done():
                    auto_state.is_running = False
                    auto_state.task.cancel()
            del self._sessions[gid]
        if expired:
            print(f"[GameSessionManager] Cleaned up {len(expired)} expired sessions")

    def __iter__(self):
        """Iterate over session IDs."""
        return iter(self._sessions)

    def __len__(self):
        """Return number of active sessions."""
        return len(self._sessions)


# Global session manager with 60-minute TTL
_game_sessions = GameSessionManager(ttl_minutes=60)


def _get_game(game_id: str) -> dict:
    """Get a game session or raise 404."""
    game = _game_sessions.get(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game


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

    # Store session with TTL tracking
    _game_sessions.set(game_id, {
        "manager": game_manager,
        "home_team": home_team,
        "away_team": away_team,
        "user_controls_home": request.user_controls_home,
        "auto_play_state": AutoPlayState(),
    })

    # Build situation response
    situation = _build_situation_response(game_id, game_manager, request.user_controls_home)

    # Determine coin toss message
    if game_manager.possession_home:
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
    user_on_offense = manager.possession_home == user_controls_home

    if not user_on_offense:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot get plays - user is on defense",
        )

    # Get situation from GameManager
    situation = manager.get_situation()
    context = SituationContext(
        down=situation["down"],
        distance=situation["distance"],
        los=situation["los"],  # Already numeric
        quarter=situation["quarter"],
        time_remaining=manager.time_remaining,
        score_diff=situation["home_score"] - situation["away_score"] if user_controls_home else situation["away_score"] - situation["home_score"],
        timeouts=situation["home_timeouts"] if user_controls_home else situation["away_timeouts"],
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
    Broadcasts play frames via WebSocket for visualization.
    """
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
    if manager.possession_home != user_controls_home:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot call plays - user is on defense",
        )

    # Set up play with frames collection
    orchestrator, offense, defense = manager.execute_play_by_code_with_frames(
        request.play_code, request.shotgun
    )

    # Run play and collect frames for visualization
    sim_result, frames = _run_play_with_frames(orchestrator, offense, defense)

    # Broadcast frames for play visualization
    await connection_manager.broadcast(game_id, {
        "type": "play_frames",
        "frames": frames,
        "total_frames": len(frames),
    })

    # Finalize result (updates state, scoring, clock)
    result = manager.finalize_play_result(sim_result)

    # Get player names for description
    description = _format_play_description_from_dict(result, offense, defense)

    play_response = PlayResultResponse(
        outcome=result["outcome"],
        yards_gained=result["yards_gained"],
        description=description,
        new_down=result["new_down"],
        new_distance=result["new_distance"],
        new_los=result["new_los"],
        first_down=result["is_first_down"],
        touchdown=result["is_touchdown"],
        turnover=result["is_turnover"],
        is_drive_over=result["is_drive_over"],
        drive_end_reason=result["drive_end_reason"],
        passer_name=_get_player_name(result["passer_id"], offense),
        receiver_name=_get_player_name(result["receiver_id"], offense),
        tackler_name=_get_player_name(result["tackler_id"], defense),
        # Include frames for play visualization (coach mode)
        frames=frames,
        total_frames=len(frames),
    )

    # Broadcast play result to WebSocket clients
    await broadcast_play_result(game_id, play_response)

    # Broadcast situation update
    situation = _build_situation_response(game_id, manager, user_controls_home)
    await broadcast_situation_update(game_id, situation)

    # Broadcast score if touchdown
    if result["is_touchdown"]:
        await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    return play_response


@router.post("/{game_id}/special", response_model=SpecialTeamsResultResponse)
async def execute_special_teams(game_id: str, request: SpecialTeamsRequest) -> SpecialTeamsResultResponse:
    """Execute a special teams play (FG, punt, PAT, kickoff)."""
    game = _get_game(game_id)
    manager = game["manager"]
    user_controls_home = game["user_controls_home"]

    # Map request play type to manager method parameters
    play_type_map = {
        PlayTypeEnum.FIELD_GOAL: "field_goal",
        PlayTypeEnum.PUNT: "punt",
        PlayTypeEnum.PAT: "pat",
        PlayTypeEnum.KICKOFF: "kickoff",
    }

    if request.play_type not in play_type_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown special teams play type: {request.play_type}",
        )

    # Let GameManager handle all logic
    result = manager.execute_special_teams(
        play_type=play_type_map[request.play_type],
        go_for_two=request.go_for_two if request.play_type == PlayTypeEnum.PAT else False,
        onside=request.onside if request.play_type == PlayTypeEnum.KICKOFF else False,
    )

    response = SpecialTeamsResultResponse(
        play_type=result["play_type"],
        result=result["result"],
        new_los=result["new_los"],
        points_scored=result["points_scored"],
        description=result["description"],
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
    if manager.possession_home == user_controls_home:
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
async def step_play(game_id: str, include_huddle: bool = False) -> Dict:
    """Execute a single play (step mode).

    Runs one play with AI controlling both teams and returns the result.
    Does not require auto-play to be running. Includes frame collection for visualization.

    Args:
        game_id: The game ID
        include_huddle: If True, include huddle animation frames before the play.
            Set to False for first play of a drive (players already in formation).
    """
    from huddle.game.coordinator import OffensiveCoordinator, SituationContext
    from huddle.game.decision_logic import fourth_down_decision, FourthDownDecision

    game = _get_game(game_id)
    manager = game["manager"]
    home_team = game["home_team"]
    away_team = game["away_team"]

    if manager.is_game_over:
        return {"message": "Game is over", "game_over": True}

    offense_is_home = manager.possession_home
    offense_team = home_team if offense_is_home else away_team

    # Get situation from GameManager
    situation = manager.get_situation()
    los_value = situation["los"]

    drive_over = False
    drive_reason = None
    result_data = None

    # Check for 4th down decisions
    if situation["down"] == 4:
        context = SituationContext(
            down=situation["down"],
            distance=situation["distance"],
            los=los_value,
            quarter=situation["quarter"],
            time_remaining=manager.time_remaining,
            score_diff=situation["home_score"] - situation["away_score"] if offense_is_home else situation["away_score"] - situation["home_score"],
            timeouts=situation["home_timeouts"] if offense_is_home else situation["away_timeouts"],
        )

        decision = fourth_down_decision(
            yard_line=int(los_value),
            yards_to_go=int(situation["distance"]),
            score_diff=context.score_diff,
            time_remaining=int(manager.time_remaining),
        )

        if decision == FourthDownDecision.PUNT:
            st_result = manager.execute_special_teams("punt")
            result_data = {"type": "special_teams", **st_result}
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": st_result})
            drive_over = True
            drive_reason = "punt"

        elif decision == FourthDownDecision.FIELD_GOAL:
            st_result = manager.execute_special_teams("field_goal")
            result_data = {"type": "special_teams", **st_result}
            await connection_manager.broadcast(game_id, {"type": "special_teams", "result": st_result})
            if st_result["points_scored"] > 0:
                await broadcast_score_update(game_id, manager.home_score, manager.away_score)
            drive_over = True
            drive_reason = "field_goal_made" if st_result["points_scored"] > 0 else "field_goal_missed"

    # Regular play (not 4th down special teams)
    if not drive_over:
        # AI calls the play
        context = SituationContext(
            down=situation["down"],
            distance=situation["distance"],
            los=los_value,
            quarter=situation["quarter"],
            time_remaining=manager.time_remaining,
            score_diff=situation["home_score"] - situation["away_score"] if offense_is_home else situation["away_score"] - situation["home_score"],
            timeouts=situation["home_timeouts"] if offense_is_home else situation["away_timeouts"],
        )
        oc = OffensiveCoordinator(team=offense_team)
        play_code = oc.call_play(context)

        # Set up play with GameManager (for frame collection)
        orchestrator, offense, defense = manager.execute_play_by_code_with_frames(play_code, shotgun=True)

        all_frames = []
        huddle_frame_count = 0

        # Run huddle transition if requested
        if include_huddle:
            # Get ball position for huddle
            ball_x = situation.get("ball_x", 0.0)
            huddle_frames = _run_huddle_with_frames(
                orchestrator, offense, defense, los_value, ball_x
            )
            all_frames.extend(huddle_frames)
            huddle_frame_count = len(huddle_frames)

            # Broadcast huddle frames separately for immediate playback
            await connection_manager.broadcast(game_id, {
                "type": "huddle_frames",
                "frames": huddle_frames,
                "total_frames": huddle_frame_count,
            })

            # Re-setup play after huddle (orchestrator is now in PRE_SNAP)
            # The setup was already done, players are in position

        # Run with frame collection for visualization
        result, play_frames = _run_play_with_frames(orchestrator, offense, defense)
        all_frames.extend(play_frames)

        # Broadcast play frames for visualization
        await connection_manager.broadcast(game_id, {
            "type": "play_frames",
            "frames": play_frames,
            "total_frames": len(play_frames),
            "huddle_frame_count": huddle_frame_count,
        })

        # Finalize result (updates state, scoring, clock)
        play_result = manager.finalize_play_result(result)
        drive_over = play_result["is_drive_over"]
        drive_reason = play_result["drive_end_reason"]

        # Build description
        description = _format_play_description_from_dict(play_result, offense, defense)

        result_data = {
            "outcome": play_result["outcome"],
            "yards_gained": play_result["yards_gained"],
            "description": description,
            "new_down": play_result["new_down"],
            "new_distance": play_result["new_distance"],
            "new_los": play_result["new_los"],
            "first_down": play_result["is_first_down"],
            "touchdown": play_result["is_touchdown"],
            "turnover": play_result["is_turnover"],
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

        # Handle touchdown scoring sequence
        if play_result["is_touchdown"]:
            await broadcast_score_update(game_id, manager.home_score, manager.away_score)

            # Handle PAT via GameManager
            pat_result = manager.execute_special_teams("pat", go_for_two=False)
            await connection_manager.broadcast(game_id, {
                "type": "special_teams",
                "result": pat_result,
            })
            if pat_result["points_scored"] > 0:
                await broadcast_score_update(game_id, manager.home_score, manager.away_score)

    # Handle drive end and possession change
    if drive_over:
        await connection_manager.broadcast(game_id, {
            "type": "drive_ended",
            "offense": offense_team.abbreviation,
            "result": drive_reason,
        })

        if not manager.is_game_over:
            # Let GameManager handle possession change
            possession_info = manager.handle_drive_end(drive_reason)

            # Broadcast kickoff if there was one
            if possession_info.get("kickoff_result"):
                await connection_manager.broadcast(game_id, {
                    "type": "special_teams",
                    "result": possession_info["kickoff_result"],
                })

            # Broadcast new drive start
            new_offense = home_team if manager.possession_home else away_team
            await connection_manager.broadcast(game_id, {
                "type": "drive_start",
                "offense": new_offense.abbreviation,
                "offense_is_home": manager.possession_home,
                "starting_los": possession_info["new_los"],
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
    broadcasting results to WebSocket clients. Delegates game logic to GameManager.
    """
    game = _game_sessions.get(game_id)
    if not game:
        return

    manager = game["manager"]
    home_team = game["home_team"]
    away_team = game["away_team"]
    auto_state: AutoPlayState = game["auto_play_state"]

    try:
        while auto_state.is_running and not manager.is_game_over:
            # Handle pause
            while auto_state.is_paused and auto_state.is_running:
                await asyncio.sleep(0.1)

            if not auto_state.is_running:
                break

            # Get current possession info from GameManager
            situation = manager.get_situation()
            offense_is_home = situation["possession_home"]
            offense_team = home_team if offense_is_home else away_team
            los_value = situation["los"]

            # Broadcast drive start
            await connection_manager.broadcast(game_id, {
                "type": "drive_start",
                "offense": offense_team.abbreviation,
                "offense_is_home": offense_is_home,
                "starting_los": los_value,
                "quarter": manager.quarter,
                "time_remaining": f"{int(manager.time_remaining // 60)}:{int(manager.time_remaining % 60):02d}",
            })

            # Run plays until drive ends
            drive_over = False
            drive_reason = None
            plays_this_drive = 0

            while not drive_over and auto_state.is_running and not manager.is_game_over:
                # Handle pause
                while auto_state.is_paused and auto_state.is_running:
                    await asyncio.sleep(0.1)

                if not auto_state.is_running:
                    break

                # Frame-based execution with huddle animation
                if auto_state.stream_frames:
                    play_result, play_code = await _execute_auto_play_with_frames(
                        game_id, manager, home_team, away_team, offense_is_home,
                        plays_this_drive
                    )
                    plays_this_drive += 1

                    if play_result is None:
                        # Special teams play was executed, continue
                        drive_over = manager.get_situation().get("is_drive_over", False)
                        drive_reason = "special_teams"
                        await asyncio.sleep(auto_state.delay_seconds)
                        continue

                    drive_over = play_result["is_drive_over"]
                    drive_reason = play_result["drive_end_reason"]

                else:
                    # Legacy text-only execution (no frames)
                    step_result = manager.step_auto_play()
                    plays_this_drive += 1

                    # Broadcast based on play type
                    if step_result["type"] == "special_teams":
                        # Special teams play (punt or FG)
                        await connection_manager.broadcast(game_id, {
                            "type": "special_teams",
                            "result": step_result["result"],
                        })
                        if step_result["result"].get("points_scored", 0) > 0:
                            await broadcast_score_update(game_id, manager.home_score, manager.away_score)
                    else:
                        # Regular play
                        play_result = step_result["result"]
                        offense, defense = manager.get_players_for_drive()
                        description = _format_play_description_from_dict(play_result, offense, defense)

                        await connection_manager.broadcast(game_id, {
                            "type": "play_result",
                            "result": {
                                "outcome": play_result["outcome"],
                                "yards_gained": play_result["yards_gained"],
                                "description": description,
                                "new_down": play_result["new_down"],
                                "new_distance": play_result["new_distance"],
                                "new_los": play_result["new_los"],
                                "first_down": play_result["is_first_down"],
                                "touchdown": play_result["is_touchdown"],
                                "turnover": play_result["is_turnover"],
                                "is_drive_over": play_result["is_drive_over"],
                                "drive_end_reason": play_result["drive_end_reason"],
                                "play_call": step_result.get("play_code"),
                                "offense_is_home": offense_is_home,
                            },
                        })

                        # Broadcast situation update
                        situation = _build_situation_response(game_id, manager, False)
                        await connection_manager.broadcast(game_id, {
                            "type": "situation_update",
                            "situation": situation.__dict__,
                        })

                        # Handle touchdown scoring sequence
                        if play_result["is_touchdown"]:
                            await broadcast_score_update(game_id, manager.home_score, manager.away_score)

                            # Handle PAT via GameManager
                            pat_result = manager.execute_special_teams("pat", go_for_two=False)
                            await connection_manager.broadcast(game_id, {
                                "type": "special_teams",
                                "result": pat_result,
                            })
                            if pat_result["points_scored"] > 0:
                                await broadcast_score_update(game_id, manager.home_score, manager.away_score)

                    # Check if drive ended
                    drive_over = step_result["is_drive_over"]
                    drive_reason = step_result["drive_end_reason"]

                # Delay based on pacing
                await asyncio.sleep(auto_state.delay_seconds)

            # Drive ended - broadcast summary
            await connection_manager.broadcast(game_id, {
                "type": "drive_ended",
                "offense": offense_team.abbreviation,
                "plays": plays_this_drive,
                "result": drive_reason if drive_over else "in_progress",
            })

            # Handle possession change via GameManager
            if drive_over and not manager.is_game_over:
                possession_info = manager.handle_drive_end(drive_reason)

                # Broadcast kickoff if there was one
                if possession_info.get("kickoff_result"):
                    await connection_manager.broadcast(game_id, {
                        "type": "special_teams",
                        "result": possession_info["kickoff_result"],
                    })

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
    if _game_sessions.contains(game_id):
        # Notify connected clients
        await connection_manager.broadcast(game_id, {
            "type": "game_ended",
            "message": "Game session ended",
        })
        _game_sessions.delete(game_id)
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
    if not _game_sessions.contains(game_id):
        await websocket.close(code=4004, reason="Game not found")
        return

    await connection_manager.connect(websocket, game_id)

    try:
        game = _game_sessions.get(game_id)
        if not game:
            await websocket.close(code=4004, reason="Game not found")
            return
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
    """Build a GameSituationResponse from manager state.

    Uses manager.get_situation() for core game state data.
    """
    # Get core situation from GameManager
    situation = manager.get_situation()
    los = situation["los"]  # Already numeric from get_situation()

    # Determine phase enum
    phase_map = {
        1: GamePhaseEnum.FIRST_QUARTER,
        2: GamePhaseEnum.SECOND_QUARTER,
        3: GamePhaseEnum.THIRD_QUARTER,
        4: GamePhaseEnum.FOURTH_QUARTER,
        5: GamePhaseEnum.OVERTIME,
    }
    phase = phase_map.get(situation["quarter"], GamePhaseEnum.FIRST_QUARTER)
    if manager.is_game_over:
        phase = GamePhaseEnum.FINAL

    return GameSituationResponse(
        game_id=game_id,
        quarter=situation["quarter"],
        time_remaining=situation["time"],
        home_score=situation["home_score"],
        away_score=situation["away_score"],
        possession_home=situation["possession_home"],
        down=situation["down"],
        distance=situation["distance"],
        los=los,
        yard_line_display=situation["yard_line"],
        is_red_zone=los >= 80,
        is_goal_to_go=situation["distance"] >= (100 - los),
        phase=phase,
        user_on_offense=situation["possession_home"] == user_controls_home,
        user_on_defense=situation["possession_home"] != user_controls_home,
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
    """Format a human-readable play description from PlayResult object."""
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


def _format_play_description_from_dict(result: dict, offense, defense) -> str:
    """Format a human-readable play description from result dict."""
    passer = _get_player_name(result.get("passer_id"), offense) or "QB"
    receiver = _get_player_name(result.get("receiver_id"), offense) or "receiver"
    tackler = _get_player_name(result.get("tackler_id"), defense) or "defender"
    yards = result.get("yards_gained", 0)
    outcome = result.get("outcome", "unknown")

    if outcome == "complete":
        return f"{passer} pass complete to {receiver} for {yards:.0f} yards"
    elif outcome == "incomplete":
        return f"{passer} pass incomplete intended for {receiver}"
    elif outcome == "interception":
        return f"{passer} INTERCEPTED by {tackler}"
    elif outcome == "sack":
        return f"{passer} sacked by {tackler} for {abs(yards):.0f} yard loss"
    elif outcome == "run":
        return f"{receiver} runs for {yards:.0f} yards"
    elif outcome == "fumble":
        return f"{receiver} FUMBLES, recovered by defense"
    else:
        return f"Play result: {outcome}, {yards:.0f} yards"


def _get_player_name(player_id: Optional[str], players: list) -> Optional[str]:
    """Get player name from ID."""
    if not player_id:
        return None
    for p in players:
        if p.id == player_id:
            return p.name
    return None
