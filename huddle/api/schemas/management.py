"""Pydantic schemas for management API."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# === Enums (mirroring the management module) ===

class SeasonPhaseSchema(str, Enum):
    """Season phase enum for API."""
    OFFSEASON_EARLY = "OFFSEASON_EARLY"
    FREE_AGENCY_LEGAL_TAMPERING = "FREE_AGENCY_LEGAL_TAMPERING"
    FREE_AGENCY = "FREE_AGENCY"
    PRE_DRAFT = "PRE_DRAFT"
    DRAFT = "DRAFT"
    POST_DRAFT = "POST_DRAFT"
    OTA = "OTA"
    MINICAMP = "MINICAMP"
    TRAINING_CAMP = "TRAINING_CAMP"
    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    WILD_CARD = "WILD_CARD"
    DIVISIONAL = "DIVISIONAL"
    CONFERENCE_CHAMPIONSHIP = "CONFERENCE_CHAMPIONSHIP"
    SUPER_BOWL = "SUPER_BOWL"


class TimeSpeedSchema(str, Enum):
    """Time speed enum for API."""
    PAUSED = "PAUSED"
    SLOW = "SLOW"
    NORMAL = "NORMAL"
    FAST = "FAST"
    VERY_FAST = "VERY_FAST"
    INSTANT = "INSTANT"


class EventCategorySchema(str, Enum):
    """Event category enum for API."""
    FREE_AGENCY = "FREE_AGENCY"
    TRADE = "TRADE"
    CONTRACT = "CONTRACT"
    ROSTER = "ROSTER"
    PRACTICE = "PRACTICE"
    MEETING = "MEETING"
    GAME = "GAME"
    SCOUTING = "SCOUTING"
    DRAFT = "DRAFT"
    STAFF = "STAFF"
    DEADLINE = "DEADLINE"
    SYSTEM = "SYSTEM"


class EventPrioritySchema(str, Enum):
    """Event priority enum for API."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


class EventStatusSchema(str, Enum):
    """Event status enum for API."""
    SCHEDULED = "SCHEDULED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ATTENDED = "ATTENDED"
    EXPIRED = "EXPIRED"
    DISMISSED = "DISMISSED"
    AUTO_RESOLVED = "AUTO_RESOLVED"


class ClipboardTabSchema(str, Enum):
    """Clipboard tab enum for API."""
    EVENTS = "EVENTS"
    ROSTER = "ROSTER"
    DEPTH_CHART = "DEPTH_CHART"
    SCHEDULE = "SCHEDULE"
    FREE_AGENTS = "FREE_AGENTS"
    TRADE_BLOCK = "TRADE_BLOCK"
    DRAFT_BOARD = "DRAFT_BOARD"
    COACHING_STAFF = "COACHING_STAFF"
    FRONT_OFFICE = "FRONT_OFFICE"
    PLAYBOOK = "PLAYBOOK"
    GAMEPLAN = "GAMEPLAN"
    FINANCES = "FINANCES"
    STANDINGS = "STANDINGS"
    LEAGUE_LEADERS = "LEAGUE_LEADERS"
    TRANSACTIONS = "TRANSACTIONS"


class TickerCategorySchema(str, Enum):
    """Ticker category enum for API."""
    SIGNING = "SIGNING"
    RELEASE = "RELEASE"
    TRADE = "TRADE"
    WAIVER = "WAIVER"
    SCORE = "SCORE"
    INJURY = "INJURY"
    INJURY_REPORT = "INJURY_REPORT"
    SUSPENSION = "SUSPENSION"
    RETIREMENT = "RETIREMENT"
    HOLDOUT = "HOLDOUT"
    DRAFT_PICK = "DRAFT_PICK"
    DRAFT_TRADE = "DRAFT_TRADE"
    DEADLINE = "DEADLINE"
    RECORD = "RECORD"
    AWARD = "AWARD"
    RUMOR = "RUMOR"


# === Request Schemas ===

class CreateFranchiseRequest(BaseModel):
    """Request to create a new franchise."""
    team_id: UUID
    team_name: str
    season_year: int = 2024
    start_phase: SeasonPhaseSchema = SeasonPhaseSchema.TRAINING_CAMP


class SetSpeedRequest(BaseModel):
    """Request to set time speed."""
    speed: TimeSpeedSchema


class SelectTabRequest(BaseModel):
    """Request to select a clipboard tab."""
    tab: ClipboardTabSchema


class AttendEventRequest(BaseModel):
    """Request to attend an event."""
    event_id: UUID


class DismissEventRequest(BaseModel):
    """Request to dismiss an event."""
    event_id: UUID


# === Response Schemas ===

class CalendarStateResponse(BaseModel):
    """Calendar state response."""
    season_year: int
    current_date: datetime
    phase: SeasonPhaseSchema
    current_week: int
    speed: TimeSpeedSchema
    is_paused: bool
    day_name: str
    time_display: str
    date_display: str
    week_display: str


class ManagementEventResponse(BaseModel):
    """Management event response."""
    id: UUID
    event_type: str
    category: EventCategorySchema
    priority: EventPrioritySchema
    title: str
    description: str
    icon: str
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None
    status: EventStatusSchema
    auto_pause: bool
    requires_attention: bool
    can_dismiss: bool
    can_delegate: bool
    team_id: Optional[UUID] = None
    player_ids: list[UUID] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_urgent: bool


class EventQueueResponse(BaseModel):
    """Event queue response."""
    pending: list[ManagementEventResponse]
    urgent_count: int
    total_count: int


class PanelContextResponse(BaseModel):
    """Panel context response."""
    panel_type: str
    event_id: Optional[UUID] = None
    player_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    game_id: Optional[UUID] = None
    can_go_back: bool


class ClipboardStateResponse(BaseModel):
    """Clipboard state response."""
    active_tab: ClipboardTabSchema
    panel: PanelContextResponse
    available_tabs: list[ClipboardTabSchema]
    tab_badges: dict[str, int]


class TickerItemResponse(BaseModel):
    """Ticker item response."""
    id: UUID
    category: TickerCategorySchema
    headline: str
    detail: str
    timestamp: datetime
    is_breaking: bool
    priority: int
    is_read: bool
    is_clickable: bool
    link_event_id: Optional[UUID] = None
    age_display: str


class TickerFeedResponse(BaseModel):
    """Ticker feed response."""
    items: list[TickerItemResponse]
    unread_count: int
    breaking_count: int


class LeagueStateResponse(BaseModel):
    """Complete league state response."""
    id: UUID
    player_team_id: Optional[UUID] = None
    calendar: CalendarStateResponse
    events: EventQueueResponse
    clipboard: ClipboardStateResponse
    ticker: TickerFeedResponse


class FranchiseCreatedResponse(BaseModel):
    """Response after creating a franchise."""
    franchise_id: UUID
    message: str


# === WebSocket Message Types ===

class ManagementWSMessageType(str, Enum):
    """WebSocket message types for management."""
    # Server -> Client
    STATE_SYNC = "state_sync"
    CALENDAR_UPDATE = "calendar_update"
    EVENT_ADDED = "event_added"
    EVENT_UPDATED = "event_updated"
    EVENT_REMOVED = "event_removed"
    TICKER_ITEM = "ticker_item"
    CLIPBOARD_UPDATE = "clipboard_update"
    AUTO_PAUSED = "auto_paused"
    ERROR = "error"

    # Client -> Server
    PAUSE = "pause"
    PLAY = "play"
    SET_SPEED = "set_speed"
    SELECT_TAB = "select_tab"
    ATTEND_EVENT = "attend_event"
    DISMISS_EVENT = "dismiss_event"
    GO_BACK = "go_back"
    REQUEST_SYNC = "request_sync"


class ManagementWSMessage(BaseModel):
    """WebSocket message for management."""
    type: ManagementWSMessageType
    payload: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    @classmethod
    def state_sync(cls, state: LeagueStateResponse) -> "ManagementWSMessage":
        """Create a state sync message."""
        return cls(
            type=ManagementWSMessageType.STATE_SYNC,
            payload=state.model_dump(mode="json"),
        )

    @classmethod
    def calendar_update(cls, calendar: CalendarStateResponse) -> "ManagementWSMessage":
        """Create a calendar update message."""
        return cls(
            type=ManagementWSMessageType.CALENDAR_UPDATE,
            payload=calendar.model_dump(mode="json"),
        )

    @classmethod
    def event_added(cls, event: ManagementEventResponse) -> "ManagementWSMessage":
        """Create an event added message."""
        return cls(
            type=ManagementWSMessageType.EVENT_ADDED,
            payload=event.model_dump(mode="json"),
        )

    @classmethod
    def ticker_item(cls, item: TickerItemResponse) -> "ManagementWSMessage":
        """Create a ticker item message."""
        return cls(
            type=ManagementWSMessageType.TICKER_ITEM,
            payload=item.model_dump(mode="json"),
        )

    @classmethod
    def auto_paused(cls, reason: str, event_id: Optional[UUID] = None) -> "ManagementWSMessage":
        """Create an auto-paused message."""
        return cls(
            type=ManagementWSMessageType.AUTO_PAUSED,
            payload={"reason": reason, "event_id": str(event_id) if event_id else None},
        )

    @classmethod
    def create_error(cls, message: str, code: str = "ERROR") -> "ManagementWSMessage":
        """Create an error message."""
        return cls(
            type=ManagementWSMessageType.ERROR,
            error_message=message,
            error_code=code,
        )
