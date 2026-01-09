"""
Franchise management router.

Handles core franchise CRUD operations and time control endpoints:
- Create/get/delete franchise
- Pause/play/speed controls
- Day advancement
- Session listing
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from huddle.management import TimeSpeed
from huddle.api.schemas.management import (
    CreateFranchiseRequest,
    FranchiseCreatedResponse,
    LeagueStateResponse,
    CalendarStateResponse,
    DayAdvanceResponse,
    ManagementEventResponse,
    SetSpeedRequest,
    SeasonPhaseSchema,
    TimeSpeedSchema,
    EventCategorySchema,
    EventPrioritySchema,
    EventStatusSchema,
    DisplayModeSchema,
)
from huddle.api.services.management_service import management_session_manager
from huddle.api.routers.admin import get_active_league
from huddle.api.routers.portraits import (
    BatchPlayerInput,
    _process_batch_portraits,
    _batch_status,
)
from .deps import (
    get_session,
    schema_to_season_phase,
    schema_to_time_speed,
    event_to_response,
)

router = APIRouter(tags=["franchise"])


@router.post("/franchise", response_model=FranchiseCreatedResponse)
async def create_franchise(
    request: CreateFranchiseRequest,
    background_tasks: BackgroundTasks,
) -> FranchiseCreatedResponse:
    """
    Create a new franchise/career mode session.

    This initializes the management game loop with the specified team
    and starting phase. Requires a league to be loaded via /admin/league/generate.

    Also triggers background portrait generation for all players,
    with the user's team prioritized.
    """
    league = get_active_league()
    if not league:
        raise HTTPException(
            status_code=400,
            detail="No league loaded. Generate a league first via /admin/league/generate",
        )

    session = await management_session_manager.create_session(
        team_id=request.team_id,
        season_year=request.season_year,
        start_phase=schema_to_season_phase(request.start_phase),
        league=league,
    )

    # Queue portrait generation for all players in the league
    # User's team gets priority=100, other teams get priority=0
    player_inputs: list[BatchPlayerInput] = []

    for team in league.teams.values():
        is_user_team = team.id == request.team_id
        priority = 100 if is_user_team else 0

        for player in team.roster.players.values():
            player_inputs.append(
                BatchPlayerInput(
                    player_id=str(player.id),
                    position=player.position.value if player.position else None,
                    age=player.age,
                    weight_lbs=player.weight_lbs,
                    priority=priority,
                )
            )

    # Also include draft prospects and free agents with lower priority
    for player in league.draft_class:
        player_inputs.append(
            BatchPlayerInput(
                player_id=str(player.id),
                position=player.position.value if player.position else None,
                age=player.age,
                weight_lbs=player.weight_lbs,
                priority=0,  # Not on user's team
            )
        )

    for player in league.free_agents:
        player_inputs.append(
            BatchPlayerInput(
                player_id=str(player.id),
                position=player.position.value if player.position else None,
                age=player.age,
                weight_lbs=player.weight_lbs,
                priority=0,  # Not on user's team
            )
        )

    # Trigger background portrait generation
    if player_inputs:
        # Initialize batch status immediately so frontend can track progress
        league_id_str = str(league.id)
        _batch_status[league_id_str] = {
            "total": len(player_inputs),
            "completed": 0,
            "failed": 0,
            "pending": len(player_inputs),
        }
        background_tasks.add_task(
            _process_batch_portraits,
            league_id_str,
            player_inputs,
        )

    return FranchiseCreatedResponse(
        franchise_id=session.franchise_id,
        message=f"Franchise created for {request.season_year} season",
    )


@router.get("/franchise/{franchise_id}", response_model=LeagueStateResponse)
async def get_franchise_state(franchise_id: UUID) -> LeagueStateResponse:
    """Get the complete state of a franchise."""
    session = get_session(franchise_id)
    return session.service.get_full_state()


@router.delete("/franchise/{franchise_id}")
async def delete_franchise(franchise_id: UUID) -> dict:
    """Delete a franchise session."""
    session = get_session(franchise_id)
    await management_session_manager.remove_session(franchise_id)
    return {"message": "Franchise deleted"}


@router.get("/franchise/{franchise_id}/calendar", response_model=CalendarStateResponse)
async def get_calendar(franchise_id: UUID) -> CalendarStateResponse:
    """Get the calendar state for a franchise."""
    session = get_session(franchise_id)
    return session.service._get_calendar_response()


@router.post("/franchise/{franchise_id}/pause")
async def pause_franchise(franchise_id: UUID) -> dict:
    """Pause time progression."""
    session = get_session(franchise_id)
    session.service.pause()
    return {"message": "Paused", "is_paused": True}


from typing import Optional


@router.post("/franchise/{franchise_id}/play")
async def play_franchise(franchise_id: UUID, request: Optional[SetSpeedRequest] = None) -> dict:
    """Resume time progression."""
    session = get_session(franchise_id)

    speed = TimeSpeed.NORMAL
    if request:
        speed = schema_to_time_speed(request.speed)

    session.service.play(speed)
    return {"message": "Playing", "speed": speed.name}


@router.post("/franchise/{franchise_id}/speed")
async def set_speed(franchise_id: UUID, request: SetSpeedRequest) -> dict:
    """Set time progression speed."""
    session = get_session(franchise_id)

    speed = schema_to_time_speed(request.speed)
    session.service.set_speed(speed)
    return {"message": f"Speed set to {speed.name}", "speed": speed.name}


@router.post("/franchise/{franchise_id}/advance-day", response_model=DayAdvanceResponse)
async def advance_day(franchise_id: UUID) -> DayAdvanceResponse:
    """
    Advance the calendar by one day.

    Generates random events for the new day, activates scheduled events,
    and returns both calendar state and the day's events.
    """
    session = get_session(franchise_id)

    calendar = session.service.state.calendar
    events_queue = session.service.state.events

    # Calculate start of next day
    current = calendar.current_date
    next_day = (current + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)

    # Advance to the next day
    calendar.advance_to(next_day)

    # Get the new day info
    new_week = calendar.current_week
    new_day = calendar.current_date.weekday()  # 0=Mon, 6=Sun

    # Generate random events for this day
    generator = session.service._generator
    new_events = generator.generate_random_day_events(new_week, new_day, calendar.phase)

    # Add generated events to the queue
    for event in new_events:
        events_queue.add(event)

    # Activate all events scheduled for this day
    activated = events_queue.activate_day_events(new_week, new_day)

    # Combine new and activated events
    all_day_events = new_events + [e for e in activated if e not in new_events]

    # Tick the state to process any time-based events
    session.service.state.tick(0)

    # Convert events to response format
    day_events_response = [event_to_response(e) for e in all_day_events]

    calendar_response = CalendarStateResponse(
        season_year=calendar.season_year,
        current_date=calendar.current_date,
        phase=SeasonPhaseSchema(calendar.phase.name),
        current_week=calendar.current_week,
        speed=TimeSpeedSchema(calendar.speed.name),
        is_paused=calendar.is_paused,
        day_name=calendar.day_name,
        time_display=calendar.time_display,
        date_display=calendar.date_display,
        week_display=calendar.week_display,
    )

    return DayAdvanceResponse(
        calendar=calendar_response,
        day_events=day_events_response,
        event_count=len(day_events_response),
    )


@router.post("/franchise/{franchise_id}/advance-to-game", response_model=CalendarStateResponse)
async def advance_to_game(franchise_id: UUID) -> CalendarStateResponse:
    """
    Fast-forward to game day (Sunday).

    Auto-processes all intervening days and their events.
    Returns the updated calendar state.
    """
    session = get_session(franchise_id)

    calendar = session.service.state.calendar
    current = calendar.current_date

    # Find next Sunday (weekday 6)
    days_until_sunday = (6 - current.weekday()) % 7
    if days_until_sunday == 0 and current.hour >= 12:
        # Already Sunday afternoon, go to next Sunday
        days_until_sunday = 7

    next_sunday = (current + timedelta(days=days_until_sunday)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    # Advance day by day to trigger events for each day
    while calendar.current_date < next_sunday:
        next_day = (calendar.current_date + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        if next_day > next_sunday:
            next_day = next_sunday
        calendar.advance_to(next_day)
        session.service.state.tick(0)

    # Return updated calendar state
    return CalendarStateResponse(
        season_year=calendar.season_year,
        current_date=calendar.current_date,
        phase=SeasonPhaseSchema(calendar.phase.name),
        current_week=calendar.current_week,
        speed=TimeSpeedSchema(calendar.speed.name),
        is_paused=calendar.is_paused,
        day_name=calendar.day_name,
        time_display=calendar.time_display,
        date_display=calendar.date_display,
        week_display=calendar.week_display,
    )


@router.get("/sessions")
async def list_sessions() -> dict:
    """List active franchise sessions."""
    return {
        "active_sessions": [str(sid) for sid in management_session_manager.active_sessions],
        "count": len(management_session_manager.active_sessions),
    }
