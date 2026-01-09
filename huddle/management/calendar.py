"""
NFL Season Calendar and Time Progression System.

DEPRECATED: This minute-based calendar is deprecated in favor of the
day-based calendar at huddle.core.calendar.league_calendar.

The new calendar:
- Uses days instead of minutes for time progression
- Integrates with the League model
- Supports historical simulation
- See: huddle.core.calendar.league_calendar.LeagueCalendar

This module is kept for backward compatibility but new code should use
the day-based calendar instead.

Original description:
This module handles the flow of time through an NFL season, including:
- Season phases (offseason, free agency, draft, regular season, playoffs)
- Real-time progression with pause/speed controls
- NFL week structure and key dates
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Callable, Optional
from uuid import UUID, uuid4


class SeasonPhase(Enum):
    """
    Major phases of an NFL season.

    The season flows through these phases in order, with specific
    events and mechanics available in each phase.
    """

    # Offseason (Feb - March)
    OFFSEASON_EARLY = auto()  # Post-Super Bowl, before free agency

    # Free Agency Period (March)
    FREE_AGENCY_LEGAL_TAMPERING = auto()  # 2-day window before FA opens
    FREE_AGENCY = auto()  # Main free agency period

    # Draft Period (April)
    PRE_DRAFT = auto()  # Pro days, workouts, interviews
    DRAFT = auto()  # The 3-day draft event
    POST_DRAFT = auto()  # UDFA signing period

    # Offseason Programs (May - July)
    OTA = auto()  # Organized Team Activities (voluntary)
    MINICAMP = auto()  # Mandatory minicamp

    # Training & Preseason (Late July - August)
    TRAINING_CAMP = auto()  # Full team practices, roster cuts
    PRESEASON = auto()  # Preseason games

    # Regular Season (September - January)
    REGULAR_SEASON = auto()  # 18-week regular season

    # Playoffs (January - February)
    WILD_CARD = auto()
    DIVISIONAL = auto()
    CONFERENCE_CHAMPIONSHIP = auto()
    SUPER_BOWL = auto()

    @property
    def is_offseason(self) -> bool:
        """Check if this is an offseason phase."""
        return self in {
            SeasonPhase.OFFSEASON_EARLY,
            SeasonPhase.FREE_AGENCY_LEGAL_TAMPERING,
            SeasonPhase.FREE_AGENCY,
            SeasonPhase.PRE_DRAFT,
            SeasonPhase.DRAFT,
            SeasonPhase.POST_DRAFT,
            SeasonPhase.OTA,
            SeasonPhase.MINICAMP,
        }

    @property
    def is_regular_season(self) -> bool:
        """Check if in regular season."""
        return self == SeasonPhase.REGULAR_SEASON

    @property
    def is_playoffs(self) -> bool:
        """Check if in playoffs."""
        return self in {
            SeasonPhase.WILD_CARD,
            SeasonPhase.DIVISIONAL,
            SeasonPhase.CONFERENCE_CHAMPIONSHIP,
            SeasonPhase.SUPER_BOWL,
        }

    @property
    def allows_trades(self) -> bool:
        """Check if trades are allowed in this phase."""
        # Trade deadline is typically Week 8 of regular season
        # For simplicity, we allow trades up through regular season
        return self not in {
            SeasonPhase.DRAFT,
            SeasonPhase.WILD_CARD,
            SeasonPhase.DIVISIONAL,
            SeasonPhase.CONFERENCE_CHAMPIONSHIP,
            SeasonPhase.SUPER_BOWL,
        }

    @property
    def allows_free_agent_signings(self) -> bool:
        """Check if FA signings are allowed."""
        # Can't sign during draft or playoffs
        return self not in {
            SeasonPhase.DRAFT,
            SeasonPhase.WILD_CARD,
            SeasonPhase.DIVISIONAL,
            SeasonPhase.CONFERENCE_CHAMPIONSHIP,
            SeasonPhase.SUPER_BOWL,
        }


class TimeSpeed(Enum):
    """
    Time progression speed settings.

    The multiplier represents game-minutes per real-second.
    Time advances smoothly minute-by-minute at all speeds.

    Target feel: You see every minute tick, just faster or slower.
    SLOW is for when events are active - deliberate, readable pace.
    """

    PAUSED = 0
    SLOW = 2  # 1 real second = 2 game minutes (deliberate, for active events)
    NORMAL = 30  # 1 real second = 30 game minutes
    FAST = 240  # 1 real second = 4 game hours
    VERY_FAST = 720  # 1 real second = 12 game hours (2 sec/day, ~14 sec/week)
    INSTANT = 2880  # 1 real second = 48 hours (instant but still visible)

    @property
    def multiplier(self) -> float:
        """Get the time multiplier for this speed."""
        return float(self.value)


@dataclass
class NFLWeek:
    """
    Represents a week in the NFL season.

    NFL weeks run Tuesday-Monday, with games typically on Sunday,
    Monday night, and Thursday night.
    """

    week_number: int  # 1-18 for regular season, 19+ for playoffs
    phase: SeasonPhase

    # Key dates within the week (day of week: 0=Monday, 6=Sunday)
    game_days: list[int] = field(default_factory=lambda: [6, 0, 3])  # Sun, Mon, Thu

    # Bye week teams (UUIDs)
    bye_teams: list[UUID] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Get display name for this week."""
        if self.phase == SeasonPhase.REGULAR_SEASON:
            return f"Week {self.week_number}"
        elif self.phase == SeasonPhase.WILD_CARD:
            return "Wild Card Round"
        elif self.phase == SeasonPhase.DIVISIONAL:
            return "Divisional Round"
        elif self.phase == SeasonPhase.CONFERENCE_CHAMPIONSHIP:
            return "Conference Championships"
        elif self.phase == SeasonPhase.SUPER_BOWL:
            return "Super Bowl"
        elif self.phase == SeasonPhase.PRESEASON:
            return f"Preseason Week {self.week_number}"
        else:
            return self.phase.name.replace("_", " ").title()


@dataclass
class LeagueCalendar:
    """
    Manages the flow of time through an NFL season.

    This is the central time-keeping system for the management game.
    It tracks the current date, season phase, and handles time progression
    with pause/speed controls.

    Time progresses in real-time (adjusted by speed multiplier), and
    callbacks can be registered to fire when certain dates/phases are reached.
    """

    id: UUID = field(default_factory=uuid4)

    # Current time state
    season_year: int = 2024  # The "2024 season" runs 2024-2025
    current_date: datetime = field(default_factory=lambda: datetime(2024, 9, 3, 8, 0))  # Week 1 Tuesday morning
    phase: SeasonPhase = SeasonPhase.REGULAR_SEASON

    # Current week info
    current_week: int = 1

    # Time progression
    speed: TimeSpeed = TimeSpeed.PAUSED
    _last_tick: datetime = field(default_factory=datetime.now)

    # Accumulated time for partial updates (in game-seconds)
    _accumulated_time: float = 0.0

    # Callbacks for phase transitions and date triggers
    _phase_callbacks: dict[SeasonPhase, list[Callable[["LeagueCalendar"], None]]] = field(
        default_factory=dict
    )
    _daily_callbacks: list[Callable[["LeagueCalendar"], None]] = field(default_factory=list)
    _weekly_callbacks: list[Callable[["LeagueCalendar"], None]] = field(default_factory=list)

    # Track last processed day/week to avoid duplicate callbacks
    _last_processed_date: Optional[datetime] = None
    _last_processed_week: int = 0

    def tick(self, real_elapsed_seconds: float, max_minutes_per_tick: int = 5) -> int:
        """
        Advance time based on real elapsed time and current speed.

        This should be called regularly (e.g., every frame or every 100ms)
        to progress game time. Time advances smoothly minute-by-minute
        so the player can see the clock tick.

        Args:
            real_elapsed_seconds: Real-world seconds since last tick
            max_minutes_per_tick: Cap on minutes to process per call (for smooth UI)

        Returns:
            Number of game minutes advanced this tick
        """
        if self.speed == TimeSpeed.PAUSED:
            return 0

        # Calculate game time to add (in seconds)
        # The multiplier is game-minutes per real-second
        game_minutes = real_elapsed_seconds * self.speed.multiplier
        game_seconds = game_minutes * 60

        self._accumulated_time += game_seconds

        # Process whole minutes, but cap how many per tick for smooth visuals
        # This means at very high speeds, we tick more frequently rather than jumping
        minutes_processed = 0
        while self._accumulated_time >= 60 and minutes_processed < max_minutes_per_tick:
            self._accumulated_time -= 60
            self._advance_one_minute()
            minutes_processed += 1

        return minutes_processed

    def advance_minutes(self, minutes: int) -> None:
        """
        Advance the calendar by a fixed number of game minutes.

        Used when an action takes a known amount of time (e.g., practice).
        This bypasses the speed multiplier and immediately advances time.
        """
        for _ in range(minutes):
            self._advance_one_minute()

    def _advance_one_minute(self) -> None:
        """Advance the calendar by one game minute."""
        old_date = self.current_date
        self.current_date = self.current_date + timedelta(minutes=1)

        # Check for day change
        if self.current_date.date() != old_date.date():
            self._on_new_day()

        # Check for week change (NFL week starts Tuesday)
        if self._is_new_week(old_date, self.current_date):
            self._on_new_week()

    def _is_new_week(self, old_date: datetime, new_date: datetime) -> bool:
        """Check if we've crossed into a new NFL week (Tuesday)."""
        # NFL weeks start on Tuesday (weekday 1)
        old_weekday = old_date.weekday()
        new_weekday = new_date.weekday()

        # Crossed Tuesday boundary
        if old_weekday != 1 and new_weekday == 1:
            return True
        # Or crossed into a new calendar week
        if new_date.date() > old_date.date() and new_weekday < old_weekday:
            return True
        return False

    def _on_new_day(self) -> None:
        """Handle day transition."""
        if self._last_processed_date == self.current_date.date():
            return

        self._last_processed_date = self.current_date.date()

        # Fire daily callbacks
        for callback in self._daily_callbacks:
            callback(self)

        # Check for phase transitions
        self._check_phase_transition()

    def _on_new_week(self) -> None:
        """Handle week transition."""
        if self.phase.is_regular_season or self.phase == SeasonPhase.PRESEASON:
            self.current_week += 1

        if self._last_processed_week == self.current_week:
            return

        self._last_processed_week = self.current_week

        # Fire weekly callbacks
        for callback in self._weekly_callbacks:
            callback(self)

    def _check_phase_transition(self) -> None:
        """Check if we should transition to a new phase based on date."""
        new_phase = self._determine_phase_for_date(self.current_date)

        if new_phase != self.phase:
            old_phase = self.phase
            self.phase = new_phase
            self._on_phase_change(old_phase, new_phase)

    def _determine_phase_for_date(self, date: datetime) -> SeasonPhase:
        """
        Determine what phase we should be in based on the date.

        This uses approximate NFL calendar dates. In a real implementation,
        these would be configurable per season.
        """
        month, day = date.month, date.day
        year = date.year

        # Super Bowl is typically first Sunday in February
        if month == 2 and day <= 15:
            if day <= 7:
                return SeasonPhase.SUPER_BOWL
            return SeasonPhase.OFFSEASON_EARLY

        # Early offseason (Feb-March)
        if month == 2 or (month == 3 and day < 11):
            return SeasonPhase.OFFSEASON_EARLY

        # Legal tampering (March 11-12 typically)
        if month == 3 and 11 <= day <= 12:
            return SeasonPhase.FREE_AGENCY_LEGAL_TAMPERING

        # Free agency (March 13 - April)
        if month == 3 and day >= 13:
            return SeasonPhase.FREE_AGENCY

        # Pre-draft (April before draft)
        if month == 4 and day < 25:
            return SeasonPhase.PRE_DRAFT

        # Draft (typically last weekend of April)
        if month == 4 and 25 <= day <= 27:
            return SeasonPhase.DRAFT

        # Post-draft UDFA period
        if month == 4 and day > 27:
            return SeasonPhase.POST_DRAFT

        # OTAs (May)
        if month == 5:
            return SeasonPhase.OTA

        # Minicamp (June)
        if month == 6:
            return SeasonPhase.MINICAMP

        # Training camp (July)
        if month == 7:
            return SeasonPhase.TRAINING_CAMP

        # Preseason (August)
        if month == 8:
            return SeasonPhase.PRESEASON

        # Regular season (September - December/early January)
        if month >= 9 or month == 1 and day <= 10:
            # Check for playoffs based on week
            if self.current_week >= 19:
                if self.current_week == 19:
                    return SeasonPhase.WILD_CARD
                elif self.current_week == 20:
                    return SeasonPhase.DIVISIONAL
                elif self.current_week == 21:
                    return SeasonPhase.CONFERENCE_CHAMPIONSHIP
                else:
                    return SeasonPhase.SUPER_BOWL
            return SeasonPhase.REGULAR_SEASON

        # January playoffs
        if month == 1:
            if day <= 15:
                return SeasonPhase.WILD_CARD
            elif day <= 22:
                return SeasonPhase.DIVISIONAL
            else:
                return SeasonPhase.CONFERENCE_CHAMPIONSHIP

        return self.phase  # Default to current

    def _on_phase_change(self, old_phase: SeasonPhase, new_phase: SeasonPhase) -> None:
        """Handle phase transition."""
        # Fire phase-specific callbacks
        if new_phase in self._phase_callbacks:
            for callback in self._phase_callbacks[new_phase]:
                callback(self)

        # Reset week counter for new phases
        if new_phase == SeasonPhase.REGULAR_SEASON:
            self.current_week = 1
        elif new_phase == SeasonPhase.PRESEASON:
            self.current_week = 1
        elif new_phase == SeasonPhase.WILD_CARD:
            self.current_week = 19

    # === Speed Controls ===

    def pause(self) -> None:
        """Pause time progression."""
        self.speed = TimeSpeed.PAUSED
        # Clear accumulated time so we don't jump when unpausing
        self._accumulated_time = 0.0

    def play(self, speed: TimeSpeed = TimeSpeed.NORMAL) -> None:
        """Start or resume time progression."""
        if speed == TimeSpeed.PAUSED:
            speed = TimeSpeed.NORMAL
        self.speed = speed
        # Clear accumulated time on speed change
        self._accumulated_time = 0.0

    def set_speed(self, speed: TimeSpeed) -> None:
        """Set time progression speed."""
        self.speed = speed
        # Clear accumulated time so speed change takes effect immediately
        self._accumulated_time = 0.0

    def toggle_pause(self) -> None:
        """Toggle between paused and normal speed."""
        if self.speed == TimeSpeed.PAUSED:
            self.speed = TimeSpeed.NORMAL
        else:
            self.speed = TimeSpeed.PAUSED

    @property
    def is_paused(self) -> bool:
        """Check if time is paused."""
        return self.speed == TimeSpeed.PAUSED

    # === Callback Registration ===

    def on_phase(self, phase: SeasonPhase, callback: Callable[["LeagueCalendar"], None]) -> None:
        """Register a callback for when a specific phase begins."""
        if phase not in self._phase_callbacks:
            self._phase_callbacks[phase] = []
        self._phase_callbacks[phase].append(callback)

    def on_daily(self, callback: Callable[["LeagueCalendar"], None]) -> None:
        """Register a callback that fires every new day."""
        self._daily_callbacks.append(callback)

    def on_weekly(self, callback: Callable[["LeagueCalendar"], None]) -> None:
        """Register a callback that fires every new week."""
        self._weekly_callbacks.append(callback)

    # === Query Methods ===

    @property
    def day_of_week(self) -> int:
        """Get current day of week (0=Monday, 6=Sunday)."""
        return self.current_date.weekday()

    @property
    def day_name(self) -> str:
        """Get current day name."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[self.day_of_week]

    @property
    def is_game_day(self) -> bool:
        """Check if today is a typical game day (Thu, Sun, Mon)."""
        return self.day_of_week in {0, 3, 6}  # Mon, Thu, Sun

    @property
    def time_display(self) -> str:
        """Get formatted time display."""
        return self.current_date.strftime("%I:%M %p")

    @property
    def date_display(self) -> str:
        """Get formatted date display."""
        return self.current_date.strftime("%B %d, %Y")

    @property
    def week_display(self) -> str:
        """Get display string for current week."""
        if self.phase.is_regular_season:
            return f"Week {self.current_week}"
        elif self.phase.is_playoffs:
            if self.phase == SeasonPhase.WILD_CARD:
                return "Wild Card"
            elif self.phase == SeasonPhase.DIVISIONAL:
                return "Divisional"
            elif self.phase == SeasonPhase.CONFERENCE_CHAMPIONSHIP:
                return "Championship"
            elif self.phase == SeasonPhase.SUPER_BOWL:
                return "Super Bowl"
        elif self.phase == SeasonPhase.PRESEASON:
            return f"Preseason Wk {self.current_week}"
        return self.phase.name.replace("_", " ").title()

    def days_until(self, target: datetime) -> int:
        """Get number of days until a target date."""
        delta = target.date() - self.current_date.date()
        return delta.days

    def advance_to(self, target: datetime) -> None:
        """
        Instantly advance time to a target date.

        Useful for skipping through periods with no events.
        Callbacks will still fire for days/weeks crossed.
        """
        while self.current_date < target:
            old_date = self.current_date
            self.current_date = min(
                self.current_date + timedelta(days=1),
                target
            )

            if self.current_date.date() != old_date.date():
                self._on_new_day()

            if self._is_new_week(old_date, self.current_date):
                self._on_new_week()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "season_year": self.season_year,
            "current_date": self.current_date.isoformat(),
            "phase": self.phase.name,
            "current_week": self.current_week,
            "speed": self.speed.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LeagueCalendar":
        """Create from dictionary."""
        calendar = cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            season_year=data.get("season_year", 2024),
            current_date=datetime.fromisoformat(data["current_date"]) if data.get("current_date") else datetime.now(),
            phase=SeasonPhase[data.get("phase", "REGULAR_SEASON")],
            current_week=data.get("current_week", 1),
            speed=TimeSpeed[data.get("speed", "PAUSED")],
        )
        return calendar

    @classmethod
    def new_season(cls, year: int, start_phase: SeasonPhase = SeasonPhase.TRAINING_CAMP) -> "LeagueCalendar":
        """
        Create a calendar for a new season starting at a specific phase.

        Args:
            year: The season year (e.g., 2024 for the 2024-2025 season)
            start_phase: Which phase to start in (default: Training Camp)

        Returns:
            A new LeagueCalendar positioned at the start of that phase
        """
        # Default start dates for each phase
        phase_starts = {
            SeasonPhase.OFFSEASON_EARLY: datetime(year, 2, 12, 8, 0),
            SeasonPhase.FREE_AGENCY_LEGAL_TAMPERING: datetime(year, 3, 11, 12, 0),
            SeasonPhase.FREE_AGENCY: datetime(year, 3, 13, 16, 0),  # 4 PM start
            SeasonPhase.PRE_DRAFT: datetime(year, 4, 1, 8, 0),
            SeasonPhase.DRAFT: datetime(year, 4, 25, 20, 0),  # 8 PM Thursday
            SeasonPhase.POST_DRAFT: datetime(year, 4, 28, 8, 0),
            SeasonPhase.OTA: datetime(year, 5, 20, 8, 0),
            SeasonPhase.MINICAMP: datetime(year, 6, 10, 8, 0),
            SeasonPhase.TRAINING_CAMP: datetime(year, 7, 23, 8, 0),  # Tuesday
            SeasonPhase.PRESEASON: datetime(year, 8, 6, 8, 0),  # Tuesday
            SeasonPhase.REGULAR_SEASON: datetime(year, 9, 3, 8, 0),  # Week 1 Tuesday
        }

        start_date = phase_starts.get(start_phase, datetime(year, 9, 3, 8, 0))

        return cls(
            season_year=year,
            current_date=start_date,
            phase=start_phase,
            current_week=1 if start_phase in {SeasonPhase.REGULAR_SEASON, SeasonPhase.PRESEASON} else 0,
        )
