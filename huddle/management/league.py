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
from datetime import datetime, timedelta
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

    def tick(self, elapsed_seconds: Optional[float] = None) -> int:
        """
        Main game loop tick.

        Should be called regularly (e.g., every frame or every 50ms).
        Advances time and processes events.

        Args:
            elapsed_seconds: Real-world seconds since last tick. If None, calculates from wall clock.

        Returns:
            Number of game minutes advanced this tick.
        """
        if elapsed_seconds is None:
            current_time = datetime.now()
            elapsed_seconds = (current_time - self._last_tick_time).total_seconds()
            self._last_tick_time = current_time
        else:
            self._last_tick_time = datetime.now()

        # Advance calendar time (returns minutes advanced)
        minutes_advanced = self.calendar.tick(elapsed_seconds)

        # Update event queue with current game time
        newly_activated = self.events.update(self.calendar.current_date)

        # Check for auto-pause/slow conditions when events activate
        for event in newly_activated:
            if self._should_auto_pause(event):
                self.pause()
                for callback in self._on_pause:
                    callback(self)
                break
            elif self._should_auto_slow(event):
                # Slow down (don't pause) so player notices the event
                self.calendar.set_speed(TimeSpeed.SLOW)
                # Notify via pause callbacks (they handle the UI update)
                for callback in self._on_event_needs_attention:
                    callback(self, event)

        # Update clipboard badges
        self._update_clipboard_badges()

        # Clean up expired/completed events and ticker items periodically
        self.events.clear_completed()
        self.ticker.cleanup_expired()

        # Fire tick callbacks
        for callback in self._on_tick:
            callback(self)

        return minutes_advanced

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

    def _should_auto_slow(self, event: ManagementEvent) -> bool:
        """Check if an event should trigger auto-slow (not pause, just slow down)."""
        # Don't slow for events that would pause (they're handled separately)
        if self._should_auto_pause(event):
            return False

        # Slow down for any pending event that requires attention
        if event.requires_attention and event.status == EventStatus.PENDING:
            # Only for events relevant to player's team (or league-wide)
            if event.team_id is None or event.team_id == self.player_team_id:
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
        # Activate events scheduled for this week/day
        week = calendar.current_week
        day = calendar.current_date.weekday()
        activated = self.events.activate_day_events(week, day)

        # Check for auto-pause on newly activated events
        for event in activated:
            if self._should_auto_pause(event):
                self.pause()
                for callback in self._on_pause:
                    callback(self)
                break

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
        Navigate to an event to interact with it.

        For most events, this marks them as IN_PROGRESS.
        For practice events, we just navigate (status changes when practice runs).

        Returns the event if found, None otherwise.
        """
        event = self.events.get(event_id)
        if event:
            # Practice and Game events stay PENDING until the user takes action
            # - Practice: stays PENDING until user runs the practice
            # - Game: stays PENDING until user sims or plays the game
            # This allows the panel to display and user to interact
            if event.category not in (EventCategory.PRACTICE, EventCategory.GAME):
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

    def run_practice(
        self,
        event_id: UUID,
        playbook: int = 34,
        development: int = 33,
        game_prep: int = 33,
        team=None,
    ) -> dict:
        """
        Run a practice session with the given time allocation.

        This:
        1. Marks the practice event as attended
        2. Advances game time by the practice duration
        3. Applies practice effects based on allocation
        4. Returns to dashboard

        Args:
            event_id: The practice event to run
            playbook: % time on playbook learning (helps team execution)
            development: % time on player development (grows young players)
            game_prep: % time on game preparation (edge vs next opponent)
            team: The team running practice (optional, needed for actual effects)

        Returns:
            Dict with success status and practice results
        """
        event = self.events.get(event_id)
        if not event or event.category != EventCategory.PRACTICE:
            return {"success": False, "error": "Invalid practice event"}

        # Get practice duration from event payload
        duration_minutes = event.payload.get("duration_minutes", 120)

        # Mark event as attended
        event.attend()

        # Advance time by the practice duration
        self.calendar.advance_minutes(duration_minutes)

        # Apply practice effects and get results
        results = self._apply_practice_effects(playbook, development, game_prep, duration_minutes, team)

        # Go back to dashboard
        self.clipboard.go_back()

        # Add ticker item about practice completion
        from huddle.management.ticker import TickerItem, TickerCategory
        practice_item = TickerItem(
            category=TickerCategory.RUMOR,
            headline="Practice complete",
            detail=f"Focus: {playbook}% playbook, {development}% development, {game_prep}% game prep",
            priority=2,
        )
        self.ticker.add(practice_item)

        return {
            "success": True,
            "duration_minutes": duration_minutes,
            "playbook_stats": results.get("playbook", {}),
            "development_stats": results.get("development", {}),
            "game_prep_stats": results.get("game_prep", {}),
        }

    def _apply_practice_effects(
        self,
        playbook_pct: int,
        development_pct: int,
        game_prep_pct: int,
        duration_minutes: int,
        team=None,
    ) -> dict:
        """
        Apply the effects of a practice session.

        This is where the actual game mechanics happen:
        - Playbook learning increases team's play execution rating
        - Development improves young players' skills
        - Game prep gives bonuses vs the next opponent

        Args:
            playbook_pct: Percentage of practice time on playbook (0-100)
            development_pct: Percentage on player development (0-100)
            game_prep_pct: Percentage on game preparation (0-100)
            duration_minutes: Total practice duration
            team: The team running practice (optional)

        Returns:
            Dict with stats from each practice area
        """
        results = {
            "playbook": {},
            "development": {},
            "game_prep": {},
        }

        if team is None:
            return results

        # Initialize playbook if needed
        if team.playbook is None:
            team.initialize_playbook()

        # Calculate practice reps based on time and allocation
        # Roughly 1 rep per 5 minutes of focused practice
        total_reps = duration_minutes // 5
        playbook_reps = int(total_reps * playbook_pct / 100)

        if playbook_reps > 0:
            results["playbook"] = self._practice_playbook(team, playbook_reps)

        # Development effects (improve young player attributes)
        development_reps = int(total_reps * development_pct / 100)
        if development_reps > 0:
            results["development"] = self._apply_development(team, development_reps)

        # Game prep effects (bonuses vs next opponent)
        game_prep_reps = int(total_reps * game_prep_pct / 100)
        if game_prep_reps > 0:
            results["game_prep"] = self._apply_game_prep(team, game_prep_reps)

        return results

    def _practice_playbook(self, team, total_reps: int) -> dict:
        """
        Distribute practice reps across the team's playbook.

        All roster players practice the plays relevant to their position.
        Reps are spread across active plays in the playbook.

        Args:
            team: The team running practice
            total_reps: Total practice reps to distribute

        Returns:
            Dict with statistics about the practice session
        """
        from huddle.core.playbook import apply_practice_rep, ALL_PLAYS

        if not team.playbook:
            return {"error": "No playbook"}

        # Get all active plays
        active_plays = list(team.playbook.offensive_plays | team.playbook.defensive_plays)
        if not active_plays:
            return {"error": "Empty playbook"}

        # Calculate reps per play (spread evenly with minimum of 1)
        reps_per_play = max(1, total_reps // len(active_plays))

        stats = {
            "players_practiced": 0,
            "total_reps_given": 0,
            "tier_advancements": 0,
            "plays_practiced": len(active_plays),
        }

        # Practice each player on relevant plays
        for player in team.roster.players.values():
            knowledge = team.get_player_knowledge(player.id)
            player_reps = 0

            for play_code in active_plays:
                play_def = ALL_PLAYS.get(play_code)
                if not play_def:
                    continue

                # Skip if player's position isn't involved in this play
                if player.position.value not in play_def.positions_involved:
                    continue

                mastery = knowledge.get_mastery(play_code)

                # Apply reps for this play
                for _ in range(reps_per_play):
                    if apply_practice_rep(player, mastery, play_def.complexity):
                        stats["tier_advancements"] += 1
                    player_reps += 1

            if player_reps > 0:
                stats["players_practiced"] += 1
                stats["total_reps_given"] += player_reps

        return stats

    def _apply_development(self, team, development_reps: int) -> dict:
        """
        Apply development reps to improve young player attributes.

        Young players with potential higher than their current overall
        can improve through practice. Development rate depends on:
        - Age (younger = faster)
        - Learning attribute (smarter = faster)
        - Room to grow (more gap = faster)

        Args:
            team: The team running practice
            development_reps: Number of reps allocated to development

        Returns:
            Dict with development statistics including per-player breakdown
        """
        from huddle.core.development import can_develop, develop_player

        stats = {
            "players_developed": 0,
            "total_points_gained": 0.0,
            "attributes_improved": {},
            "per_player_gains": [],  # Per-player breakdown for UI
        }

        # Filter to players who can benefit from development
        developable_players = [
            p for p in team.roster.players.values()
            if can_develop(p)
        ]

        if not developable_players:
            return stats

        # Distribute reps among developable players
        reps_per_player = max(1, development_reps // len(developable_players))

        for player in developable_players:
            gains = develop_player(player, reps_per_player)

            if gains:
                stats["players_developed"] += 1

                # Track per-player gains for UI
                stats["per_player_gains"].append({
                    "player_id": str(player.id),
                    "name": player.full_name,
                    "position": player.position.value if hasattr(player.position, 'value') else str(player.position),
                    "gains": gains,
                })

                # Aggregate stats
                for attr, gain in gains.items():
                    stats["total_points_gained"] += gain
                    if attr not in stats["attributes_improved"]:
                        stats["attributes_improved"][attr] = 0
                    stats["attributes_improved"][attr] += gain

        return stats

    def _apply_game_prep(self, team, game_prep_reps: int) -> dict:
        """
        Apply game prep reps to study the next opponent.

        Creates or strengthens a GamePrepBonus for the upcoming game.
        The bonus provides scheme recognition and execution bonuses
        during the game against that opponent.

        Args:
            team: The team running practice
            game_prep_reps: Number of reps allocated to game prep

        Returns:
            Dict with game prep statistics
        """
        from huddle.core.game_prep import apply_prep_bonus

        stats = {
            "opponent": None,
            "prep_level": 0.0,
            "scheme_bonus": 0.0,
            "execution_bonus": 0.0,
        }

        # Get next opponent from events
        next_game = self._get_next_game_info(team.id)
        if not next_game:
            return stats

        opponent_name = next_game.get("opponent_name", "Unknown")
        opponent_id = next_game.get("opponent_id")
        week = next_game.get("week", 0)

        stats["opponent"] = opponent_name

        # Apply prep bonus
        team.game_prep_bonus = apply_prep_bonus(
            existing=team.game_prep_bonus,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            week=week,
            reps=game_prep_reps,
        )

        stats["prep_level"] = team.game_prep_bonus.prep_level
        stats["scheme_bonus"] = team.game_prep_bonus.scheme_recognition
        stats["execution_bonus"] = team.game_prep_bonus.execution_bonus

        return stats

    def _get_next_game_info(self, team_id: UUID) -> Optional[dict]:
        """
        Get information about the team's next scheduled game.

        Looks through active events for the next GAME event
        for the specified team.

        Args:
            team_id: UUID of the team

        Returns:
            Dict with opponent_name, opponent_id, week, or None if no game found
        """
        from huddle.management.events import EventCategory

        for event in self.events.get_active():
            if event.category == EventCategory.GAME and event.team_id == team_id:
                return {
                    "opponent_name": event.payload.get("opponent_name"),
                    "opponent_id": event.payload.get("opponent_id"),
                    "week": event.payload.get("week"),
                }

        # Also check pending events (future games)
        for event in self.events.get_pending():
            if event.category == EventCategory.GAME and event.team_id == team_id:
                return {
                    "opponent_name": event.payload.get("opponent_name"),
                    "opponent_id": event.payload.get("opponent_id"),
                    "week": event.payload.get("week"),
                }

        return None

    def sim_game(self, event_id: UUID, league) -> bool:
        """
        Simulate a game using the full simulation engine.

        This:
        1. Marks the game event as attended
        2. Runs the full game simulation
        3. Updates the schedule with the score
        4. Advances time by game duration
        5. Returns to dashboard

        Args:
            event_id: The game event to simulate
            league: Core League with teams, players, schedule

        Returns:
            True if game was simulated successfully
        """
        event = self.events.get(event_id)
        if not event or event.category != EventCategory.GAME:
            return False

        # Get game info from event payload
        opponent_name = event.payload.get("opponent_name", "Opponent")
        is_home = event.payload.get("is_home", True)
        week = event.payload.get("week", 1)

        # Use real simulation engine
        from huddle.simulation import SeasonSimulator, SimulationMode

        # Find the scheduled game in the league
        scheduled_game = None
        # Get player team abbreviation from state
        player_team = league.get_team_by_id(self.player_team_id) if self.player_team_id else None
        player_team_abbr = player_team.abbreviation if player_team else "PHI"
        for game in league.schedule:
            if game.week == week:
                if (game.home_team_abbr == player_team_abbr or
                    game.away_team_abbr == player_team_abbr):
                    scheduled_game = game
                    break

        if not scheduled_game:
            return False

        simulator = SeasonSimulator(league, mode=SimulationMode.FAST)
        result = simulator.simulate_game(scheduled_game)

        # Determine scores based on home/away
        if is_home:
            our_score = result.home_score
            their_score = result.away_score
        else:
            our_score = result.away_score
            their_score = result.home_score

        # Determine winner for headline
        if our_score > their_score:
            headline = f"Victory! {player_team_abbr} defeats {opponent_name} {our_score}-{their_score}"
        elif our_score < their_score:
            headline = f"{player_team_abbr} falls to {opponent_name} {their_score}-{our_score}"
        else:
            headline = f"{player_team_abbr} ties {opponent_name} {our_score}-{their_score}"

        # Mark event as attended
        event.attend()

        # Advance time by game duration (3 hours)
        duration_minutes = event.payload.get("duration_minutes", 180)
        self.calendar.advance_minutes(duration_minutes)

        # Go back to dashboard
        self.clipboard.go_back()

        # Add ticker item about game result
        from huddle.management.ticker import TickerItem, TickerCategory
        game_item = TickerItem(
            category=TickerCategory.SCORE,
            headline=headline,
            detail=f"Week {week} {'Home' if is_home else 'Away'} game",
            is_breaking=True,
            priority=5,
        )
        self.ticker.add(game_item)

        return True

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

    def get_upcoming_events(self, days: int = 7) -> list[ManagementEvent]:
        """Get scheduled events coming up within N days from current game date."""
        from huddle.management.events import EventStatus

        current_date = self.calendar.current_date
        cutoff = current_date + timedelta(days=days)

        upcoming = []
        for e in self.events._events.values():
            # Only SCHEDULED events (not yet active)
            if e.status != EventStatus.SCHEDULED:
                continue
            # Must be for player's team or league-wide
            if e.team_id is not None and e.team_id != self.player_team_id:
                continue
            # Must have a scheduled_for date in the future
            if e.scheduled_for and current_date < e.scheduled_for <= cutoff:
                upcoming.append(e)

        # Sort by scheduled date
        return sorted(upcoming, key=lambda e: e.scheduled_for or current_date)

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

    # === Approval & Depth Chart Management ===

    def update_depth_chart(
        self,
        team,
        position: str,
        player_id: UUID,
        new_depth: int,
    ) -> dict:
        """
        Update a player's position on the depth chart with approval tracking.

        Handles the approval implications of promotions and demotions.

        Args:
            team: The team to update
            position: Position code (e.g., "QB", "WR")
            player_id: The player being moved
            new_depth: New depth (1 = starter, 2 = backup, etc.)

        Returns:
            Dict with old_depth, new_depth, and approval_change
        """
        from huddle.core.approval import (
            get_depth_chart_event,
            apply_approval_event,
            create_player_approval,
        )

        result = {
            "player_id": str(player_id),
            "position": position,
            "old_depth": None,
            "new_depth": new_depth,
            "approval_change": 0.0,
            "event": None,
        }

        # Find current depth
        old_depth = None
        for depth in range(1, 10):
            slot = f"{position}{depth}"
            if team.roster.depth_chart.get(slot) == player_id:
                old_depth = depth
                break

        result["old_depth"] = old_depth

        # Get the player
        player = team.roster.get_player(player_id)
        if not player:
            return result

        # Ensure player has approval tracking
        if player.approval is None:
            player.approval = create_player_approval(player_id)

        # Determine approval event
        if old_depth is not None:
            event = get_depth_chart_event(old_depth, new_depth)
            if event:
                result["event"] = event.value
                # Apply approval change
                old_approval = player.approval.approval
                apply_approval_event(player, event, reason=f"Depth chart: {position}{old_depth} → {position}{new_depth}")
                result["approval_change"] = player.approval.approval - old_approval

        # Actually update the depth chart
        new_slot = f"{position}{new_depth}"
        team.roster.depth_chart.set(new_slot, player_id)

        # If this was a swap, we may need to handle the displaced player
        # (The displaced player's approval would be handled in a separate call)

        return result

    def process_weekly_approval(self, team, team_winning: bool = False, team_losing: bool = False) -> dict:
        """
        Process weekly approval drift for all players on a team.

        Should be called at the end of each week to allow approval
        to naturally trend toward baseline.

        Args:
            team: The team to process
            team_winning: True if team is on a winning streak
            team_losing: True if team is on a losing streak

        Returns:
            Dict with processing statistics
        """
        from huddle.core.approval import create_player_approval

        stats = {
            "players_processed": 0,
            "total_drift": 0.0,
            "trade_candidates": 0,
            "holdout_risks": 0,
        }

        for player in team.roster.players.values():
            # Ensure player has approval tracking
            if player.approval is None:
                player.approval = create_player_approval(player.id)
                continue  # New approval starts at baseline, no drift needed

            old_approval = player.approval.approval
            player.approval.apply_weekly_drift(team_winning, team_losing)
            drift = player.approval.approval - old_approval

            stats["players_processed"] += 1
            stats["total_drift"] += drift

            if player.approval.is_trade_candidate():
                stats["trade_candidates"] += 1
            if player.approval.is_holdout_risk():
                stats["holdout_risks"] += 1

        return stats

    def apply_team_result_approval(self, team, won: bool) -> dict:
        """
        Apply approval changes based on a game result.

        Winning helps morale, losing hurts it.

        Args:
            team: The team
            won: True if team won the game

        Returns:
            Dict with processing statistics
        """
        from huddle.core.approval import ApprovalEvent, apply_approval_event, create_player_approval

        event = ApprovalEvent.WIN if won else ApprovalEvent.LOSS

        stats = {
            "players_affected": 0,
            "total_change": 0.0,
        }

        for player in team.roster.players.values():
            if player.approval is None:
                player.approval = create_player_approval(player.id)

            old_approval = player.approval.approval
            apply_approval_event(player, event)
            change = player.approval.approval - old_approval

            stats["players_affected"] += 1
            stats["total_change"] += change

        return stats

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
