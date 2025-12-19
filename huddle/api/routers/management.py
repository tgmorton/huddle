"""REST API router for management/franchise mode."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.management import SeasonPhase, TimeSpeed, ClipboardTab
from huddle.api.schemas.management import (
    CreateFranchiseRequest,
    FranchiseCreatedResponse,
    LeagueStateResponse,
    CalendarStateResponse,
    EventQueueResponse,
    ClipboardStateResponse,
    TickerFeedResponse,
    SetSpeedRequest,
    SelectTabRequest,
    AttendEventRequest,
    DismissEventRequest,
    SeasonPhaseSchema,
    TimeSpeedSchema,
    ClipboardTabSchema,
)
from huddle.api.services.management_service import management_session_manager
from huddle.api.routers.admin import get_active_league

router = APIRouter(prefix="/management", tags=["management"])


def _schema_to_season_phase(schema: SeasonPhaseSchema) -> SeasonPhase:
    """Convert schema enum to SeasonPhase."""
    return SeasonPhase[schema.value]


def _schema_to_time_speed(schema: TimeSpeedSchema) -> TimeSpeed:
    """Convert schema enum to TimeSpeed."""
    return TimeSpeed[schema.value]


def _schema_to_clipboard_tab(schema: ClipboardTabSchema) -> ClipboardTab:
    """Convert schema enum to ClipboardTab."""
    return ClipboardTab[schema.value]


@router.post("/franchise", response_model=FranchiseCreatedResponse)
async def create_franchise(request: CreateFranchiseRequest) -> FranchiseCreatedResponse:
    """
    Create a new franchise/career mode session.

    This initializes the management game loop with the specified team
    and starting phase. Requires a league to be loaded via /admin/league/generate.
    """
    league = get_active_league()
    if not league:
        raise HTTPException(
            status_code=400,
            detail="No league loaded. Generate a league first via /admin/league/generate"
        )

    session = await management_session_manager.create_session(
        team_id=request.team_id,
        season_year=request.season_year,
        start_phase=_schema_to_season_phase(request.start_phase),
        league=league,
    )

    return FranchiseCreatedResponse(
        franchise_id=session.franchise_id,
        message=f"Franchise created for {request.season_year} season",
    )


@router.get("/franchise/{franchise_id}", response_model=LeagueStateResponse)
async def get_franchise_state(franchise_id: UUID) -> LeagueStateResponse:
    """Get the complete state of a franchise."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    return session.service.get_full_state()


@router.delete("/franchise/{franchise_id}")
async def delete_franchise(franchise_id: UUID) -> dict:
    """Delete a franchise session."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    await management_session_manager.remove_session(franchise_id)
    return {"message": "Franchise deleted"}


@router.get("/franchise/{franchise_id}/calendar", response_model=CalendarStateResponse)
async def get_calendar(franchise_id: UUID) -> CalendarStateResponse:
    """Get the calendar state for a franchise."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    return session.service._get_calendar_response()


@router.post("/franchise/{franchise_id}/pause")
async def pause_franchise(franchise_id: UUID) -> dict:
    """Pause time progression."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    session.service.pause()
    return {"message": "Paused", "is_paused": True}


@router.post("/franchise/{franchise_id}/play")
async def play_franchise(franchise_id: UUID, request: SetSpeedRequest = None) -> dict:
    """Resume time progression."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    speed = TimeSpeed.NORMAL
    if request:
        speed = _schema_to_time_speed(request.speed)

    session.service.play(speed)
    return {"message": "Playing", "speed": speed.name}


@router.post("/franchise/{franchise_id}/speed")
async def set_speed(franchise_id: UUID, request: SetSpeedRequest) -> dict:
    """Set time progression speed."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    speed = _schema_to_time_speed(request.speed)
    session.service.set_speed(speed)
    return {"message": f"Speed set to {speed.name}", "speed": speed.name}


@router.get("/franchise/{franchise_id}/events", response_model=EventQueueResponse)
async def get_events(franchise_id: UUID) -> EventQueueResponse:
    """Get pending events for a franchise."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    return session.service._get_events_response()


@router.post("/franchise/{franchise_id}/events/attend")
async def attend_event(franchise_id: UUID, request: AttendEventRequest) -> dict:
    """Attend an event."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    event = session.service.attend_event(request.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": f"Attending event: {event.title}", "event_id": str(event.id)}


@router.post("/franchise/{franchise_id}/events/dismiss")
async def dismiss_event(franchise_id: UUID, request: DismissEventRequest) -> dict:
    """Dismiss an event."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    success = session.service.dismiss_event(request.event_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot dismiss event")

    return {"message": "Event dismissed", "event_id": str(request.event_id)}


@router.get("/franchise/{franchise_id}/clipboard", response_model=ClipboardStateResponse)
async def get_clipboard(franchise_id: UUID) -> ClipboardStateResponse:
    """Get clipboard state for a franchise."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    return session.service._get_clipboard_response()


@router.post("/franchise/{franchise_id}/clipboard/tab")
async def select_tab(franchise_id: UUID, request: SelectTabRequest) -> dict:
    """Select a clipboard tab."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    tab = _schema_to_clipboard_tab(request.tab)
    session.service.select_tab(tab)
    return {"message": f"Selected tab: {tab.name}", "tab": tab.name}


@router.post("/franchise/{franchise_id}/clipboard/back")
async def go_back(franchise_id: UUID) -> dict:
    """Go back in panel navigation."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    success = session.service.go_back()
    return {"message": "Navigated back" if success else "Already at root", "success": success}


@router.get("/franchise/{franchise_id}/ticker", response_model=TickerFeedResponse)
async def get_ticker(franchise_id: UUID) -> TickerFeedResponse:
    """Get ticker feed for a franchise."""
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")

    return session.service._get_ticker_response()


@router.get("/sessions")
async def list_sessions() -> dict:
    """List active franchise sessions."""
    return {
        "active_sessions": [str(sid) for sid in management_session_manager.active_sessions],
        "count": len(management_session_manager.active_sessions),
    }
