"""Service for managing franchise/career mode state."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, TYPE_CHECKING
from uuid import UUID

from fastapi import WebSocket

from huddle.management import (
    LeagueState,
    SeasonPhase,
    TimeSpeed,
    EventGenerator,
    ManagementEvent,
    ClipboardTab,
)

if TYPE_CHECKING:
    from huddle.core.league import League
from huddle.api.schemas.management import (
    LeagueStateResponse,
    CalendarStateResponse,
    EventQueueResponse,
    ManagementEventResponse,
    ClipboardStateResponse,
    PanelContextResponse,
    TickerFeedResponse,
    TickerItemResponse,
    SeasonPhaseSchema,
    TimeSpeedSchema,
    EventCategorySchema,
    EventPrioritySchema,
    EventStatusSchema,
    ClipboardTabSchema,
    TickerCategorySchema,
)


def _to_season_phase_schema(phase: SeasonPhase) -> SeasonPhaseSchema:
    """Convert SeasonPhase to schema enum."""
    return SeasonPhaseSchema(phase.name)


def _to_time_speed_schema(speed: TimeSpeed) -> TimeSpeedSchema:
    """Convert TimeSpeed to schema enum."""
    return TimeSpeedSchema(speed.name)


def _event_to_response(event: ManagementEvent) -> ManagementEventResponse:
    """Convert ManagementEvent to response schema."""
    return ManagementEventResponse(
        id=event.id,
        event_type=event.event_type,
        category=EventCategorySchema(event.category.name),
        priority=EventPrioritySchema(event.priority.name),
        title=event.title,
        description=event.description,
        icon=event.icon,
        created_at=event.created_at,
        scheduled_for=event.scheduled_for,
        deadline=event.deadline,
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


class ManagementService:
    """
    Service that manages a franchise/career mode session.

    Wraps LeagueState and provides async tick loop for WebSocket updates.
    Uses the core League for all game data (teams, players, schedule, stats).
    """

    def __init__(self, state: LeagueState, league: "League") -> None:
        self.state = state
        self.league = league  # Core league with teams, players, schedule
        self._is_running = False
        self._tick_task: Optional[asyncio.Task] = None
        self._websocket: Optional[WebSocket] = None

        # Callbacks for WebSocket updates
        self._update_callbacks: list[Callable] = []

        # Event generator
        self._generator = EventGenerator(
            calendar=state.calendar,
            events=state.events,
            ticker=state.ticker,
            player_team_id=state.player_team_id,
        )

        # Build schedule from core league
        from huddle.management.generators import ScheduledGame as MgmtScheduledGame
        from datetime import datetime, timedelta
        mgmt_schedule = []
        player_team_abbr = "PHI"  # TODO: get from state

        # NFL season typically starts first Sunday in September
        season_start = datetime(state.season_year, 9, 1)
        # Find first Sunday
        days_until_sunday = (6 - season_start.weekday()) % 7
        first_sunday = season_start + timedelta(days=days_until_sunday)

        if league.schedule:
            for game in league.schedule:
                # Find games involving player's team
                if game.home_team_abbr == player_team_abbr or game.away_team_abbr == player_team_abbr:
                    is_home = game.home_team_abbr == player_team_abbr
                    opponent = game.away_team_abbr if is_home else game.home_team_abbr
                    # Compute game_time from week (1pm Sunday)
                    game_sunday = first_sunday + timedelta(weeks=game.week - 1)
                    game_time = game_sunday.replace(hour=13, minute=0)
                    mgmt_schedule.append(MgmtScheduledGame(
                        week=game.week,
                        opponent_id=game.id,
                        opponent_name=opponent,
                        is_home=is_home,
                        game_time=game_time,
                        is_divisional=game.is_divisional if hasattr(game, 'is_divisional') else False,
                    ))
        self._generator.set_schedule(mgmt_schedule)

        # Get free agents from core league
        from huddle.management.generators import FreeAgentInfo
        fa_list = []
        if hasattr(league, 'free_agents') and league.free_agents:
            for player in league.free_agents:
                fa_list.append(FreeAgentInfo(
                    player_id=player.id,
                    name=player.full_name,
                    position=player.position.value if hasattr(player.position, 'value') else str(player.position),
                    overall=player.overall,
                    age=player.age,
                    asking_price=player.salary // 1000 if player.salary else 1000,
                ))
        self._generator.set_free_agents(fa_list)

        # Register state callbacks
        self.state.on_pause(self._on_pause)
        self.state.on_event_needs_attention(self._on_event_activated)

    @property
    def is_running(self) -> bool:
        """Check if tick loop is running."""
        return self._is_running

    async def start(self) -> None:
        """Start the tick loop."""
        if self._is_running:
            return

        self._is_running = True
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        """Stop the tick loop."""
        self._is_running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
            self._tick_task = None

    async def _tick_loop(self) -> None:
        """Main tick loop - runs continuously while service is active."""
        last_tick_time = datetime.now()
        last_calendar_update = datetime.now()

        # Tick interval in seconds - fast enough for smooth minute-by-minute display
        tick_interval = 0.05  # 50ms = 20 ticks per second

        while self._is_running:
            try:
                now = datetime.now()
                elapsed = (now - last_tick_time).total_seconds()
                last_tick_time = now

                # Tick the state with actual elapsed time
                minutes_advanced = self.state.tick(elapsed)

                # Send calendar updates whenever time actually advanced
                # This gives smooth visual feedback of time ticking
                if not self.state.is_paused and minutes_advanced > 0:
                    # Throttle updates to max ~10 per second to avoid flooding
                    if (now - last_calendar_update).total_seconds() >= 0.1:
                        await self._send_calendar_update()
                        last_calendar_update = now

                await asyncio.sleep(tick_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in management tick loop: {e}")
                await asyncio.sleep(1.0)  # Back off on error

    def _on_pause(self, state: LeagueState) -> None:
        """Handle auto-pause."""
        # Will notify via WebSocket
        asyncio.create_task(self._send_auto_paused())

    def _on_event_activated(self, state: LeagueState, event: ManagementEvent) -> None:
        """Handle event activation."""
        asyncio.create_task(self._send_event_added(event))

    async def _send_calendar_update(self) -> None:
        """Send calendar and events update via WebSocket."""
        if not self._websocket:
            return

        from huddle.api.schemas.management import ManagementWSMessage

        try:
            calendar = self._get_calendar_response()
            events_response = self._get_events_response()
            msg = ManagementWSMessage.calendar_update(calendar, events_response.pending)
            await self._websocket.send_json(msg.model_dump(mode="json"))
        except Exception:
            pass  # WebSocket may be closed

    async def _send_event_added(self, event: ManagementEvent) -> None:
        """Send event added via WebSocket."""
        if not self._websocket:
            return

        from huddle.api.schemas.management import ManagementWSMessage

        try:
            event_resp = _event_to_response(event)
            msg = ManagementWSMessage.event_added(event_resp)
            await self._websocket.send_json(msg.model_dump(mode="json"))
        except Exception:
            pass

    async def _send_auto_paused(self) -> None:
        """Send auto-paused notification via WebSocket."""
        if not self._websocket:
            return

        from huddle.api.schemas.management import ManagementWSMessage

        try:
            # Find the event that caused the pause
            urgent = self.state.get_urgent_events()
            event_id = urgent[0].id if urgent else None
            reason = urgent[0].title if urgent else "Important event"

            msg = ManagementWSMessage.auto_paused(reason, event_id)
            await self._websocket.send_json(msg.model_dump(mode="json"))
        except Exception:
            pass

    def attach_websocket(self, websocket: WebSocket) -> None:
        """Attach a WebSocket for updates."""
        self._websocket = websocket

    def detach_websocket(self) -> None:
        """Detach the WebSocket."""
        self._websocket = None

    # === Time Controls ===

    def pause(self) -> None:
        """Pause time."""
        self.state.pause()

    def play(self, speed: TimeSpeed = TimeSpeed.NORMAL) -> None:
        """Play/resume time."""
        self.state.play(speed)

    def set_speed(self, speed: TimeSpeed) -> None:
        """Set time speed."""
        self.state.set_speed(speed)

    # === Clipboard Controls ===

    def select_tab(self, tab: ClipboardTab) -> None:
        """Select a clipboard tab."""
        self.state.clipboard.select_tab(tab)

    def attend_event(self, event_id: UUID) -> Optional[ManagementEvent]:
        """Attend an event."""
        return self.state.attend_event(event_id)

    def dismiss_event(self, event_id: UUID) -> bool:
        """Dismiss an event."""
        return self.state.dismiss_event(event_id)

    def run_practice(
        self,
        event_id: UUID,
        playbook: int = 34,
        development: int = 33,
        game_prep: int = 33,
    ) -> bool:
        """
        Run a practice session with the given allocation.

        Args:
            event_id: The practice event ID
            playbook: Percentage of time on playbook learning (0-100)
            development: Percentage of time on player development (0-100)
            game_prep: Percentage of time on game preparation (0-100)

        Returns:
            True if practice was run successfully
        """
        return self.state.run_practice(event_id, playbook, development, game_prep)

    def sim_game(self, event_id: UUID) -> bool:
        """
        Simulate a game using the full simulation engine.

        Args:
            event_id: The game event ID

        Returns:
            True if game was simulated successfully
        """
        return self.state.sim_game(event_id, self.league)

    def go_back(self) -> bool:
        """Go back in panel navigation."""
        return self.state.clipboard.go_back()

    # === State Getters ===

    def _get_calendar_response(self) -> CalendarStateResponse:
        """Get calendar state response."""
        cal = self.state.calendar
        return CalendarStateResponse(
            season_year=cal.season_year,
            current_date=cal.current_date,
            phase=_to_season_phase_schema(cal.phase),
            current_week=cal.current_week,
            speed=_to_time_speed_schema(cal.speed),
            is_paused=cal.is_paused,
            day_name=cal.day_name,
            time_display=cal.time_display,
            date_display=cal.date_display,
            week_display=cal.week_display,
        )

    def _get_events_response(self) -> EventQueueResponse:
        """Get event queue response."""
        pending = self.state.get_pending_events()
        return EventQueueResponse(
            pending=[_event_to_response(e) for e in pending],
            urgent_count=len(self.state.get_urgent_events()),
            total_count=self.state.events.count,
        )

    def _get_clipboard_response(self) -> ClipboardStateResponse:
        """Get clipboard state response."""
        cb = self.state.clipboard
        return ClipboardStateResponse(
            active_tab=ClipboardTabSchema(cb.active_tab.name),
            panel=PanelContextResponse(
                panel_type=cb.panel.panel_type.name,
                event_id=cb.panel.event_id,
                player_id=cb.panel.player_id,
                team_id=cb.panel.team_id,
                game_id=cb.panel.game_id,
                can_go_back=cb.panel.can_go_back,
            ),
            available_tabs=[ClipboardTabSchema(t.name) for t in cb.available_tabs],
            tab_badges={t.name: c for t, c in cb.tab_badges.items()},
        )

    def _get_ticker_response(self) -> TickerFeedResponse:
        """Get ticker feed response."""
        items = self.state.ticker.get_recent(20)
        return TickerFeedResponse(
            items=[
                TickerItemResponse(
                    id=item.id,
                    category=TickerCategorySchema(item.category.name),
                    headline=item.headline,
                    detail=item.detail,
                    timestamp=item.timestamp,
                    is_breaking=item.is_breaking,
                    priority=item.priority,
                    is_read=item.is_read,
                    is_clickable=item.is_clickable,
                    link_event_id=item.link_event_id,
                    age_display=item.age_display,
                )
                for item in items
            ],
            unread_count=self.state.ticker.unread_count,
            breaking_count=self.state.ticker.breaking_count,
        )

    def get_full_state(self) -> LeagueStateResponse:
        """Get complete league state response."""
        return LeagueStateResponse(
            id=self.state.id,
            player_team_id=self.state.player_team_id,
            calendar=self._get_calendar_response(),
            events=self._get_events_response(),
            clipboard=self._get_clipboard_response(),
            ticker=self._get_ticker_response(),
        )


@dataclass
class ManagementSession:
    """A management session with its service."""

    franchise_id: UUID
    service: ManagementService
    websocket: Optional[WebSocket] = None
    created_at: datetime = field(default_factory=datetime.now)

    async def start(self) -> None:
        """Start the session."""
        await self.service.start()

    async def stop(self) -> None:
        """Stop the session."""
        await self.service.stop()


class ManagementSessionManager:
    """Manages active management sessions."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, ManagementSession] = {}

    async def create_session(
        self,
        team_id: UUID,
        season_year: int = 2024,
        start_phase: SeasonPhase = SeasonPhase.TRAINING_CAMP,
        league: "League" = None,
    ) -> ManagementSession:
        """Create a new management session with the core League."""
        if not league:
            raise ValueError("League is required to create a management session")

        state = LeagueState.new_franchise(
            player_team_id=team_id,
            season_year=season_year,
            start_phase=start_phase,
        )

        service = ManagementService(state, league)
        session = ManagementSession(
            franchise_id=state.id,
            service=service,
        )

        self._sessions[state.id] = session
        await session.start()

        return session

    def get_session(self, franchise_id: UUID) -> Optional[ManagementSession]:
        """Get a session by ID."""
        return self._sessions.get(franchise_id)

    async def remove_session(self, franchise_id: UUID) -> None:
        """Remove and stop a session."""
        session = self._sessions.pop(franchise_id, None)
        if session:
            await session.stop()

    def attach_websocket(self, franchise_id: UUID, websocket: WebSocket) -> bool:
        """Attach a WebSocket to a session."""
        session = self._sessions.get(franchise_id)
        if session:
            session.websocket = websocket
            session.service.attach_websocket(websocket)
            return True
        return False

    def detach_websocket(self, franchise_id: UUID) -> None:
        """Detach a WebSocket from a session."""
        session = self._sessions.get(franchise_id)
        if session:
            session.websocket = None
            session.service.detach_websocket()

    @property
    def active_sessions(self) -> list[UUID]:
        """Get list of active session IDs."""
        return list(self._sessions.keys())

    async def cleanup_all(self) -> None:
        """Stop all sessions."""
        for session in list(self._sessions.values()):
            await session.stop()
        self._sessions.clear()


# Global session manager
management_session_manager = ManagementSessionManager()
