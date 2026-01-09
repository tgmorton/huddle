"""
NFL League Calendar System.

Day-based calendar tracking all important league dates:
- Offseason phases (free agency, draft, OTAs, training camp)
- Regular season weeks
- Playoffs
- Key deadlines (roster cuts, trade deadline, etc.)
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Optional


class LeaguePeriod(Enum):
    """Major period of the league year."""
    OFFSEASON_EARLY = auto()      # Post-Super Bowl to FA
    FREE_AGENCY = auto()          # Legal tampering + FA signing period
    DRAFT_PREP = auto()           # Pro days, visits, pre-draft
    DRAFT = auto()                # Draft days
    POST_DRAFT = auto()           # UDFA signings, rookie minicamps
    OTAs = auto()                 # Organized team activities
    TRAINING_CAMP = auto()        # Training camp
    PRESEASON = auto()            # Preseason games
    REGULAR_SEASON = auto()       # Regular season
    PLAYOFFS = auto()             # Postseason
    SUPER_BOWL = auto()           # Championship


class LeagueEvent(Enum):
    """Specific league events/deadlines."""
    FRANCHISE_TAG_DEADLINE = auto()
    LEGAL_TAMPERING_START = auto()
    FREE_AGENCY_START = auto()
    DRAFT_START = auto()
    DRAFT_END = auto()
    ROOKIE_MINICAMP = auto()
    OTA_START = auto()
    MANDATORY_MINICAMP = auto()
    TRAINING_CAMP_START = auto()
    ROSTER_CUT_90 = auto()
    ROSTER_CUT_85 = auto()
    ROSTER_CUT_53 = auto()
    PRACTICE_SQUAD_FORM = auto()
    REGULAR_SEASON_START = auto()
    TRADE_DEADLINE = auto()
    PLAYOFF_START = auto()
    CONFERENCE_CHAMPIONSHIP = auto()
    SUPER_BOWL = auto()
    NEW_LEAGUE_YEAR = auto()


@dataclass
class CalendarEvent:
    """A specific event on the calendar."""
    event_type: LeagueEvent
    event_date: date
    description: str
    affects_roster: bool = False  # Does this require roster action?
    deadline: bool = False        # Is this a deadline?


# Standard NFL calendar offsets from league year start (typically mid-March)
# All values are days from the start of the league year
STANDARD_CALENDAR_OFFSETS = {
    LeagueEvent.FRANCHISE_TAG_DEADLINE: -7,      # Week before new league year
    LeagueEvent.LEGAL_TAMPERING_START: -2,       # 2 days before FA
    LeagueEvent.FREE_AGENCY_START: 0,            # League year start
    LeagueEvent.DRAFT_START: 45,                 # Late April (~6 weeks after FA)
    LeagueEvent.DRAFT_END: 47,                   # 3 days of draft
    LeagueEvent.ROOKIE_MINICAMP: 55,             # ~Week after draft
    LeagueEvent.OTA_START: 65,                   # Mid-May
    LeagueEvent.MANDATORY_MINICAMP: 95,          # Mid-June
    LeagueEvent.TRAINING_CAMP_START: 135,        # Late July
    LeagueEvent.ROSTER_CUT_90: 155,              # Mid-August
    LeagueEvent.ROSTER_CUT_85: 162,              # Late August
    LeagueEvent.ROSTER_CUT_53: 175,              # Before Week 1
    LeagueEvent.PRACTICE_SQUAD_FORM: 176,        # Day after final cuts
    LeagueEvent.REGULAR_SEASON_START: 180,       # Early September
    LeagueEvent.TRADE_DEADLINE: 237,             # ~Week 9
    LeagueEvent.PLAYOFF_START: 299,              # Mid-January
    LeagueEvent.CONFERENCE_CHAMPIONSHIP: 313,   # Late January
    LeagueEvent.SUPER_BOWL: 320,                 # Early February
    LeagueEvent.NEW_LEAGUE_YEAR: 365,            # Next year
}


@dataclass
class LeagueCalendar:
    """
    Calendar for a league season.

    Tracks current date, generates events, and determines league period.
    """
    season: int                    # e.g., 2024
    league_year_start: date        # When FA starts (typically mid-March)
    current_date: date = None
    events: list[CalendarEvent] = field(default_factory=list)

    def __post_init__(self):
        if self.current_date is None:
            self.current_date = self.league_year_start
        if not self.events:
            self._generate_events()

    def _generate_events(self) -> None:
        """Generate all calendar events for the season."""
        self.events = []

        for event_type, offset in STANDARD_CALENDAR_OFFSETS.items():
            event_date = self.league_year_start + timedelta(days=offset)

            description = self._get_event_description(event_type)
            affects_roster = event_type in {
                LeagueEvent.ROSTER_CUT_90,
                LeagueEvent.ROSTER_CUT_85,
                LeagueEvent.ROSTER_CUT_53,
                LeagueEvent.PRACTICE_SQUAD_FORM,
            }
            is_deadline = "DEADLINE" in event_type.name or "CUT" in event_type.name

            self.events.append(CalendarEvent(
                event_type=event_type,
                event_date=event_date,
                description=description,
                affects_roster=affects_roster,
                deadline=is_deadline,
            ))

        # Sort by date
        self.events.sort(key=lambda e: e.event_date)

    def _get_event_description(self, event_type: LeagueEvent) -> str:
        """Get human-readable description for event."""
        descriptions = {
            LeagueEvent.FRANCHISE_TAG_DEADLINE: "Deadline to apply franchise tag",
            LeagueEvent.LEGAL_TAMPERING_START: "Legal tampering period begins",
            LeagueEvent.FREE_AGENCY_START: "Free agency begins - new league year",
            LeagueEvent.DRAFT_START: f"{self.season} NFL Draft begins",
            LeagueEvent.DRAFT_END: "Draft concludes",
            LeagueEvent.ROOKIE_MINICAMP: "Rookie minicamp",
            LeagueEvent.OTA_START: "OTAs begin",
            LeagueEvent.MANDATORY_MINICAMP: "Mandatory minicamp",
            LeagueEvent.TRAINING_CAMP_START: "Training camp opens",
            LeagueEvent.ROSTER_CUT_90: "Roster must be cut to 90 players",
            LeagueEvent.ROSTER_CUT_85: "Roster must be cut to 85 players",
            LeagueEvent.ROSTER_CUT_53: "Final roster cuts - 53 man limit",
            LeagueEvent.PRACTICE_SQUAD_FORM: "Practice squads can be formed",
            LeagueEvent.REGULAR_SEASON_START: "Regular season begins",
            LeagueEvent.TRADE_DEADLINE: "Trade deadline",
            LeagueEvent.PLAYOFF_START: "Playoffs begin",
            LeagueEvent.CONFERENCE_CHAMPIONSHIP: "Conference championships",
            LeagueEvent.SUPER_BOWL: f"Super Bowl {self._get_super_bowl_numeral()}",
            LeagueEvent.NEW_LEAGUE_YEAR: "New league year begins",
        }
        return descriptions.get(event_type, event_type.name)

    def _get_super_bowl_numeral(self) -> str:
        """Get Super Bowl roman numeral based on season."""
        # Super Bowl I was after 1966 season
        number = self.season - 1966 + 1
        # This is simplified - real conversion is complex
        return str(number)

    @property
    def current_period(self) -> LeaguePeriod:
        """Get current period of league year."""
        days_since_start = (self.current_date - self.league_year_start).days

        if days_since_start < 0:
            return LeaguePeriod.OFFSEASON_EARLY
        elif days_since_start < 45:
            return LeaguePeriod.FREE_AGENCY
        elif days_since_start < 48:
            return LeaguePeriod.DRAFT
        elif days_since_start < 65:
            return LeaguePeriod.POST_DRAFT
        elif days_since_start < 135:
            return LeaguePeriod.OTAs
        elif days_since_start < 180:
            return LeaguePeriod.TRAINING_CAMP
        elif days_since_start < 299:
            return LeaguePeriod.REGULAR_SEASON
        elif days_since_start < 320:
            return LeaguePeriod.PLAYOFFS
        elif days_since_start < 365:
            return LeaguePeriod.SUPER_BOWL
        else:
            return LeaguePeriod.OFFSEASON_EARLY

    @property
    def current_week(self) -> int:
        """
        Get current week of regular season (1-18).

        Returns 0 if not in regular season.
        """
        if self.current_period != LeaguePeriod.REGULAR_SEASON:
            return 0

        season_start = self.get_event_date(LeagueEvent.REGULAR_SEASON_START)
        if season_start is None:
            return 0

        days_into_season = (self.current_date - season_start).days
        return min(18, max(1, (days_into_season // 7) + 1))

    def get_event_date(self, event_type: LeagueEvent) -> Optional[date]:
        """Get date of a specific event."""
        for event in self.events:
            if event.event_type == event_type:
                return event.event_date
        return None

    def get_upcoming_events(self, days: int = 7) -> list[CalendarEvent]:
        """Get events within the next N days."""
        cutoff = self.current_date + timedelta(days=days)
        return [e for e in self.events
                if self.current_date <= e.event_date <= cutoff]

    def get_upcoming_deadlines(self, days: int = 14) -> list[CalendarEvent]:
        """Get deadlines within the next N days."""
        cutoff = self.current_date + timedelta(days=days)
        return [e for e in self.events
                if self.current_date <= e.event_date <= cutoff and e.deadline]

    def advance_day(self) -> list[CalendarEvent]:
        """
        Advance calendar by one day.

        Returns list of events that occurred on the new day.
        """
        self.current_date += timedelta(days=1)
        return [e for e in self.events if e.event_date == self.current_date]

    def advance_to_date(self, target_date: date) -> list[CalendarEvent]:
        """
        Advance calendar to a specific date.

        Returns all events that occurred during the advancement.
        """
        events_occurred = []
        while self.current_date < target_date:
            self.current_date += timedelta(days=1)
            events_occurred.extend(
                e for e in self.events if e.event_date == self.current_date
            )
        return events_occurred

    def advance_to_event(self, event_type: LeagueEvent) -> list[CalendarEvent]:
        """Advance to a specific event."""
        event_date = self.get_event_date(event_type)
        if event_date and event_date > self.current_date:
            return self.advance_to_date(event_date)
        return []

    def is_trade_period(self) -> bool:
        """Can trades be made today?"""
        # Trades allowed from draft through trade deadline
        draft_end = self.get_event_date(LeagueEvent.DRAFT_END)
        trade_deadline = self.get_event_date(LeagueEvent.TRADE_DEADLINE)

        if draft_end and trade_deadline:
            return draft_end <= self.current_date <= trade_deadline

        return self.current_period in {
            LeaguePeriod.POST_DRAFT,
            LeaguePeriod.OTAs,
            LeaguePeriod.TRAINING_CAMP,
            LeaguePeriod.REGULAR_SEASON,
        }

    def is_free_agency_period(self) -> bool:
        """Is free agency currently active?"""
        return self.current_period == LeaguePeriod.FREE_AGENCY

    def days_until(self, event_type: LeagueEvent) -> int:
        """Days until a specific event."""
        event_date = self.get_event_date(event_type)
        if event_date:
            return (event_date - self.current_date).days
        return -1

    def to_dict(self) -> dict:
        return {
            "season": self.season,
            "league_year_start": self.league_year_start.isoformat(),
            "current_date": self.current_date.isoformat(),
            "events": [
                {
                    "event_type": e.event_type.name,
                    "event_date": e.event_date.isoformat(),
                    "description": e.description,
                    "affects_roster": e.affects_roster,
                    "deadline": e.deadline,
                }
                for e in self.events
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LeagueCalendar":
        cal = cls(
            season=data["season"],
            league_year_start=date.fromisoformat(data["league_year_start"]),
            current_date=date.fromisoformat(data["current_date"]),
        )
        cal.events = [
            CalendarEvent(
                event_type=LeagueEvent[e["event_type"]],
                event_date=date.fromisoformat(e["event_date"]),
                description=e["description"],
                affects_roster=e.get("affects_roster", False),
                deadline=e.get("deadline", False),
            )
            for e in data.get("events", [])
        ]
        return cal


def create_calendar_for_season(season: int, league_year_start: date = None) -> LeagueCalendar:
    """
    Create a calendar for a specific season.

    Args:
        season: The NFL season year (e.g., 2024)
        league_year_start: When FA starts (defaults to March 13th)
    """
    if league_year_start is None:
        # NFL league year typically starts 2nd Wednesday of March
        # Simplified: March 13th
        league_year_start = date(season, 3, 13)

    return LeagueCalendar(
        season=season,
        league_year_start=league_year_start,
    )
