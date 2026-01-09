"""
Shared dependencies for management sub-routers.

Contains common utilities and helpers used across all management endpoints.
"""

from uuid import UUID

from fastapi import HTTPException

from huddle.management import SeasonPhase, TimeSpeed, ClipboardTab
from huddle.api.services.management_service import management_session_manager, ManagementSession
from huddle.api.schemas.management import (
    SeasonPhaseSchema,
    TimeSpeedSchema,
    ClipboardTabSchema,
    EventCategorySchema,
    EventPrioritySchema,
    EventStatusSchema,
    DisplayModeSchema,
    ManagementEventResponse,
)


def get_session(franchise_id: UUID) -> ManagementSession:
    """
    Get a management session by franchise ID.

    Raises HTTPException 404 if not found.
    """
    session = management_session_manager.get_session(franchise_id)
    if not session:
        raise HTTPException(status_code=404, detail="Franchise not found")
    return session


def get_session_with_team(franchise_id: UUID) -> ManagementSession:
    """
    Get a management session and verify the team exists.

    Raises HTTPException 404 if session or team not found.
    """
    session = get_session(franchise_id)
    if not session.team:
        raise HTTPException(status_code=404, detail="Team not found")
    return session


def schema_to_season_phase(schema: SeasonPhaseSchema) -> SeasonPhase:
    """Convert schema enum to SeasonPhase."""
    return SeasonPhase[schema.value]


def schema_to_time_speed(schema: TimeSpeedSchema) -> TimeSpeed:
    """Convert schema enum to TimeSpeed."""
    return TimeSpeed[schema.value]


def schema_to_clipboard_tab(schema: ClipboardTabSchema) -> ClipboardTab:
    """Convert schema enum to ClipboardTab."""
    return ClipboardTab[schema.value]


def event_to_response(event) -> ManagementEventResponse:
    """Convert ManagementEvent to response schema."""
    return ManagementEventResponse(
        id=event.id,
        event_type=event.event_type,
        category=EventCategorySchema(event.category.name),
        priority=EventPrioritySchema(event.priority.name),
        title=event.title,
        description=event.description,
        icon=event.icon,
        display_mode=DisplayModeSchema(event.display_mode.name),
        created_at=event.created_at,
        scheduled_for=event.scheduled_for,
        deadline=event.deadline,
        scheduled_week=event.scheduled_week,
        scheduled_day=event.scheduled_day,
        arc_id=event.arc_id,
        status=EventStatusSchema(event.status.name),
        auto_pause=event.auto_pause,
        requires_attention=event.requires_attention,
        can_dismiss=event.can_dismiss,
        can_delegate=event.can_delegate,
        team_id=event.team_id,
        player_ids=event.player_ids,
        payload=event.payload,
        is_urgent=event.is_urgent,
    )
