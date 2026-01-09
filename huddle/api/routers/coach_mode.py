"""Coach Mode Game API Router.

Provides REST endpoints for playing games in coach mode where
the user makes play-calling decisions.

Endpoints:
- POST /coach/start - Start a new coach mode game
- GET /coach/{game_id}/situation - Get current game situation
- GET /coach/{game_id}/plays - Get available plays
- POST /coach/{game_id}/play - Execute a play
- POST /coach/{game_id}/special - Execute special teams play
- GET /coach/{game_id}/box-score - Get current box score
- POST /coach/{game_id}/simulate-defense - Let AI handle defensive possession
"""

from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

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
)

router = APIRouter(prefix="/coach", tags=["coach-mode"])


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
    """
    from huddle.api.services.management_service import management_session_manager
    from huddle.game.manager import GameManager
    import uuid

    # Get teams from league
    # For now, generate sample teams if no league loaded
    home_team = None
    away_team = None

    # Try to get teams from management session
    for session in management_session_manager._sessions.values():
        if session.league:
            for team in session.league.teams:
                if team.id == request.home_team_id:
                    home_team = team
                elif team.id == request.away_team_id:
                    away_team = team

    if not home_team or not away_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teams not found. Make sure a league is loaded.",
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

    return PlayResultResponse(
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


@router.post("/{game_id}/special", response_model=SpecialTeamsResultResponse)
async def execute_special_teams(game_id: str, request: SpecialTeamsRequest) -> SpecialTeamsResultResponse:
    """Execute a special teams play (FG, punt, PAT, kickoff)."""
    game = _get_game(game_id)
    manager = game["manager"]

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

        return SpecialTeamsResultResponse(
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

        return SpecialTeamsResultResponse(
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

        return SpecialTeamsResultResponse(
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

        return SpecialTeamsResultResponse(
            play_type="kickoff",
            result=result.result,
            new_los=result.new_los,
            points_scored=0,
            description=desc,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown special teams play type: {request.play_type}",
    )


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

    return {
        "drive_result": {
            "plays": drive_result.play_count,
            "yards": drive_result.total_yards,
            "time_of_possession": f"{drive_result.time_of_possession / 60:.0f}:{drive_result.time_of_possession % 60:02.0f}",
            "result": drive_result.end_reason.value,
            "points_scored": drive_result.points_scored,
        },
        "new_situation": _build_situation_response(game_id, manager, user_controls_home).__dict__,
    }


@router.get("/{game_id}/box-score", response_model=BoxScoreResponse)
async def get_box_score(game_id: str) -> BoxScoreResponse:
    """Get the current box score."""
    # TODO: Implement with ResultHandler
    return BoxScoreResponse(
        home={"total_yards": "0", "passing_yards": "0", "rushing_yards": "0", "first_downs": "0", "turnovers": "0", "time_of_possession": "0:00", "third_down": "0/0"},
        away={"total_yards": "0", "passing_yards": "0", "rushing_yards": "0", "first_downs": "0", "turnovers": "0", "time_of_possession": "0:00", "third_down": "0/0"},
    )


@router.delete("/{game_id}")
async def end_game(game_id: str) -> Dict:
    """End a game session."""
    if game_id in _active_games:
        del _active_games[game_id]
        return {"message": f"Game {game_id} ended"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Game {game_id} not found",
    )


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
