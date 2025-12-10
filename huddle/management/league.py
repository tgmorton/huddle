"""
League State - The Main Management Game Controller.

This module ties together all the management systems:
- Calendar (time progression)
- Event Queue (management events)
- Clipboard (UI state)
- Ticker (news feed)

It coordinates the main game loop, handles auto-pause triggers,
and manages the flow of information between systems.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional
from uuid import UUID, uuid4

from huddle.management.calendar import LeagueCalendar, SeasonPhase, TimeSpeed
from huddle.management.events import (
    EventQueue,
    ManagementEvent,
    EventCategory,
    EventPriority,
    EventStatus,
)
from huddle.management.clipboard import ClipboardState, ClipboardTab
from huddle.management.ticker import TickerFeed, TickerItem


@dataclass
class LeagueState:
    """
    The central state container for the management game.

    This is the single source of truth for the franchise mode.
    It coordinates time progression, event handling, UI state,
    and the news ticker.

    The main game loop calls `tick()` regularly, which:
    1. Advances calendar time (if not paused)
    2. Updates event queue (activates/expires events)
    3. Checks for auto-pause triggers
    4. Updates ticker feed
    5. Fires any registered callbacks
    """

    id: UUID = field(default_factory=uuid4)

    # The player's team
    player_team_id: Optional[UUID] = None

    # Core subsystems
    calendar: LeagueCalendar = field(default_factory=LeagueCalendar)
    events: EventQueue = field(default_factory=EventQueue)
    clipboard: ClipboardState = field(default_factory=ClipboardState)
    ticker: TickerFeed = field(default_factory=TickerFeed)

    # Auto-pause settings
    auto_pause_on_critical: bool = True  # Pause for critical events
    auto_pause_on_game_day: bool = True  # Pause when your game starts
    auto_pause_on_deadline: bool = True  # Pause for important deadlines

    # Callbacks for game loop integration
    _on_pause: list[Callable[["LeagueState"], None]] = field(default_factory=list)
    _on_event_needs_attention: list[Callable[["LeagueState", ManagementEvent], None]] = field(
        default_factory=list
    )
    _on_phase_change: list[Callable[["LeagueState", SeasonPhase], None]] = field(default_factory=list)
    _on_tick: list[Callable[["LeagueState"], None]] = field(default_factory=list)

    # Last tick timestamp for delta calculation
    _last_tick_time: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Set up internal event handlers."""
        # Wire up event queue to trigger pause checks
        self.events.on_event_activated(self._handle_event_activated)

        # Wire up calendar phase changes
        self.calendar.on_daily(self._handle_new_day)
        self.calendar.on_weekly(self._handle_new_week)

    def tick(self, current_time: Optional[datetime] = None) -> None:
        """
        Main game loop tick.

        Should be called regularly (e.g., every frame or every 100ms).
        Advances time and processes events.

        Args:
            current_time: Current real-world time. If None, uses datetime.now()
        """
        if current_time is None:
            current_time = datetime.now()

        # Calculate real elapsed time since last tick
        elapsed = (current_time - self._last_tick_time).total_seconds()
        self._last_tick_time = current_time

        # Advance calendar time
        self.calendar.tick(elapsed)

        # Update event queue with current game time
        newly_activated = self.events.update(self.calendar.current_date)

        # Check for auto-pause conditions
        for event in newly_activated:
            if self._should_auto_pause(event):
                self.pause()
                for callback in self._on_pause:
                    callback(self)
                break

        # Update clipboard badges
        self._update_clipboard_badges()

        # Clean up expired ticker items periodically
        self.ticker.cleanup_expired()

        # Fire tick callbacks
        for callback in self._on_tick:
            callback(self)

    def _should_auto_pause(self, event: ManagementEvent) -> bool:
        """Check if an event should trigger auto-pause."""
        if not event.auto_pause:
            return False

        # Only pause for events relevant to player's team
        if event.team_id and event.team_id != self.player_team_id:
            return False

        if event.priority == EventPriority.CRITICAL and self.auto_pause_on_critical:
            return True

        if event.category == EventCategory.GAME and self.auto_pause_on_game_day:
            return True

        if event.category == EventCategory.DEADLINE and self.auto_pause_on_deadline:
            return True

        return False

    def _handle_event_activated(self, event: ManagementEvent) -> None:
        """Handle when an event becomes active."""
        # Notify listeners
        for callback in self._on_event_needs_attention:
            callback(self, event)

        # Add to ticker if noteworthy
        if event.priority.value <= EventPriority.HIGH.value:
            self.ticker.add(TickerItem(
                category=self._event_to_ticker_category(event),
                headline=event.title,
                detail=event.description,
                is_breaking=event.priority == EventPriority.CRITICAL,
                priority=10 - event.priority.value,  # Invert for ticker
                team_ids=[event.team_id] if event.team_id else [],
                player_ids=event.player_ids,
                link_event_id=event.id,
                is_clickable=True,
            ))

    def _event_to_ticker_category(self, event: ManagementEvent) -> "TickerCategory":
        """Map event category to ticker category."""
        from huddle.management.ticker import TickerCategory

        mapping = {
            EventCategory.FREE_AGENCY: TickerCategory.SIGNING,
            EventCategory.TRADE: TickerCategory.TRADE,
            EventCategory.CONTRACT: TickerCategory.SIGNING,
            EventCategory.ROSTER: TickerCategory.RELEASE,
            EventCategory.GAME: TickerCategory.SCORE,
            EventCategory.DRAFT: TickerCategory.DRAFT_PICK,
            EventCategory.SCOUTING: TickerCategory.RUMOR,
            EventCategory.DEADLINE: TickerCategory.DEADLINE,
        }
        return mapping.get(event.category, TickerCategory.RUMOR)

    def _handle_new_day(self, calendar: LeagueCalendar) -> None:
        """Handle daily transitions."""
        # Could spawn daily events here (e.g., practice)
        pass

    def _handle_new_week(self, calendar: LeagueCalendar) -> None:
        """Handle weekly transitions."""
        # Could spawn weekly events here (e.g., game day)

        # Update clipboard for new phase if needed
        self._update_clipboard_for_phase()

    def _update_clipboard_for_phase(self) -> None:
        """Update clipboard available tabs based on current phase."""
        phase = self.calendar.phase

        is_draft = phase in {
            SeasonPhase.PRE_DRAFT,
            SeasonPhase.DRAFT,
            SeasonPhase.POST_DRAFT,
        }

        is_fa = phase in {
            SeasonPhase.FREE_AGENCY_LEGAL_TAMPERING,
            SeasonPhase.FREE_AGENCY,
        }

        self.clipboard.update_available_tabs(
            is_draft_season=is_draft,
            is_free_agency=is_fa,
        )

    def _update_clipboard_badges(self) -> None:
        """Update notification badges on clipboard tabs."""
        # Events tab badge = pending events needing attention
        pending_count = len([
            e for e in self.events.get_pending()
            if e.requires_attention and e.team_id == self.player_team_id
        ])
        self.clipboard.set_badge(ClipboardTab.EVENTS, pending_count)

        # Could add more badges for other tabs (e.g., expiring contracts)

    # === Time Control ===

    def pause(self) -> None:
        """Pause time progression."""
        self.calendar.pause()

    def play(self, speed: TimeSpeed = TimeSpeed.NORMAL) -> None:
        """Resume time progression."""
        self.calendar.play(speed)

    def set_speed(self, speed: TimeSpeed) -> None:
        """Set time progression speed."""
        self.calendar.set_speed(speed)

    def toggle_pause(self) -> None:
        """Toggle between paused and playing."""
        self.calendar.toggle_pause()

    @property
    def is_paused(self) -> bool:
        """Check if game is paused."""
        return self.calendar.is_paused

    @property
    def current_speed(self) -> TimeSpeed:
        """Get current time speed."""
        return self.calendar.speed

    # === Event Management ===

    def add_event(self, event: ManagementEvent) -> None:
        """Add an event to the queue."""
        self.events.add(event)

    def attend_event(self, event_id: UUID) -> Optional[ManagementEvent]:
        """
        Mark an event as being attended.

        Returns the event if found, None otherwise.
        """
        event = self.events.get(event_id)
        if event:
            event.attend()
            # Navigate clipboard to event
            self.clipboard.navigate_to_event(event_id)
        return event

    def dismiss_event(self, event_id: UUID) -> bool:
        """
        Dismiss an event without acting.

        Returns True if event was dismissed.
        """
        event = self.events.get(event_id)
        if event and event.can_dismiss:
            event.dismiss()
            return True
        return False

    def get_pending_events(self) -> list[ManagementEvent]:
        """Get all pending events for the player's team."""
        return [
            e for e in self.events.get_pending()
            if e.team_id is None or e.team_id == self.player_team_id
        ]

    def get_urgent_events(self) -> list[ManagementEvent]:
        """Get urgent events needing immediate attention."""
        return [
            e for e in self.events.get_urgent()
            if e.team_id is None or e.team_id == self.player_team_id
        ]

    # === Ticker Management ===

    def add_ticker_item(self, item: TickerItem) -> None:
        """Add an item to the news ticker."""
        self.ticker.add(item)

    def get_ticker_items(self, count: int = 10) -> list[TickerItem]:
        """Get recent ticker items."""
        return self.ticker.get_recent(count)

    # === Callback Registration ===

    def on_pause(self, callback: Callable[["LeagueState"], None]) -> None:
        """Register callback for when game pauses."""
        self._on_pause.append(callback)

    def on_event_needs_attention(
        self, callback: Callable[["LeagueState", ManagementEvent], None]
    ) -> None:
        """Register callback for when events need attention."""
        self._on_event_needs_attention.append(callback)

    def on_phase_change(
        self, callback: Callable[["LeagueState", SeasonPhase], None]
    ) -> None:
        """Register callback for phase transitions."""
        self._on_phase_change.append(callback)

    def on_tick(self, callback: Callable[["LeagueState"], None]) -> None:
        """Register callback that fires every tick."""
        self._on_tick.append(callback)

    # === Convenience Properties ===

    @property
    def current_date(self) -> datetime:
        """Get current game date."""
        return self.calendar.current_date

    @property
    def current_phase(self) -> SeasonPhase:
        """Get current season phase."""
        return self.calendar.phase

    @property
    def current_week(self) -> int:
        """Get current week number."""
        return self.calendar.current_week

    @property
    def season_year(self) -> int:
        """Get current season year."""
        return self.calendar.season_year

    # === Serialization ===

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "player_team_id": str(self.player_team_id) if self.player_team_id else None,
            "calendar": self.calendar.to_dict(),
            "events": self.events.to_dict(),
            "clipboard": self.clipboard.to_dict(),
            "ticker": self.ticker.to_dict(),
            "auto_pause_on_critical": self.auto_pause_on_critical,
            "auto_pause_on_game_day": self.auto_pause_on_game_day,
            "auto_pause_on_deadline": self.auto_pause_on_deadline,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LeagueState":
        """Create from dictionary."""
        state = cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            player_team_id=UUID(data["player_team_id"]) if data.get("player_team_id") else None,
            calendar=LeagueCalendar.from_dict(data.get("calendar", {})),
            events=EventQueue.from_dict(data.get("events", {})),
            clipboard=ClipboardState.from_dict(data.get("clipboard", {})),
            ticker=TickerFeed.from_dict(data.get("ticker", {})),
            auto_pause_on_critical=data.get("auto_pause_on_critical", True),
            auto_pause_on_game_day=data.get("auto_pause_on_game_day", True),
            auto_pause_on_deadline=data.get("auto_pause_on_deadline", True),
        )
        return state

    @classmethod
    def new_franchise(
        cls,
        player_team_id: UUID,
        season_year: int = 2024,
        start_phase: SeasonPhase = SeasonPhase.TRAINING_CAMP,
    ) -> "LeagueState":
        """
        Create a new franchise/career mode state.

        Args:
            player_team_id: The team the player controls
            season_year: Starting season year
            start_phase: Which phase to start in

        Returns:
            A fresh LeagueState ready to begin
        """
        calendar = LeagueCalendar.new_season(season_year, start_phase)

        state = cls(
            player_team_id=player_team_id,
            calendar=calendar,
        )

        # Initialize clipboard for current phase
        state._update_clipboard_for_phase()

        return state
