"""
Event Generators - Spawn management events based on calendar state.

These generators hook into the calendar system and automatically create
events based on the current phase, day of week, and game schedule.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional
from uuid import UUID, uuid4
import random

from huddle.management.calendar import LeagueCalendar, SeasonPhase
from huddle.management.events import (
    ManagementEvent,
    EventQueue,
    EventCategory,
    EventPriority,
    DisplayMode,
    EventStatus,
    create_game_event,
    create_practice_event,
    create_free_agent_event,
    create_scouting_event,
    create_deadline_event,
    create_trade_offer_event,
    create_scout_report_event,
)
from huddle.management.ticker import (
    TickerFeed,
    TickerItem,
    ticker_signing,
    ticker_release,
    ticker_trade,
    ticker_score,
    ticker_injury,
    ticker_rumor,
)


@dataclass
class ScheduledGame:
    """A game on the schedule."""
    week: int
    opponent_id: UUID
    opponent_name: str
    is_home: bool
    game_time: datetime  # Day of week encoded in datetime
    is_divisional: bool = False
    is_primetime: bool = False


@dataclass
class FreeAgentInfo:
    """Info about an available free agent."""
    player_id: UUID
    name: str
    position: str
    overall: int
    age: int
    asking_price: int  # In thousands


@dataclass
class EventGeneratorConfig:
    """Configuration for event generation."""

    # Practice settings
    practice_days: list[int] = field(default_factory=lambda: [1, 2, 3, 4])  # Tue-Fri
    practice_time_hour: int = 14  # 2 PM

    # Free agency settings
    fa_check_interval_hours: int = 4
    top_fa_threshold: int = 80  # OVR threshold for "top" FAs

    # Trade settings
    trade_offer_chance: float = 0.1  # 10% chance per day of receiving offer

    # Scouting settings
    workouts_per_week: int = 3

    # News/ticker settings
    ticker_events_per_day: int = 5


class EventGenerator:
    """
    Generates management events based on calendar state.

    This is the main event spawning system. It registers callbacks
    with the calendar and generates appropriate events as time passes.
    """

    def __init__(
        self,
        calendar: LeagueCalendar,
        events: EventQueue,
        ticker: TickerFeed,
        player_team_id: UUID,
        config: Optional[EventGeneratorConfig] = None,
    ) -> None:
        self.calendar = calendar
        self.events = events
        self.ticker = ticker
        self.player_team_id = player_team_id
        self.config = config or EventGeneratorConfig()

        # Game schedule (populated externally)
        self.schedule: list[ScheduledGame] = []

        # Available free agents (populated externally)
        self.free_agents: list[FreeAgentInfo] = []

        # Tracking to avoid duplicate events
        self._generated_game_weeks: set[int] = set()
        self._generated_practice_dates: set[str] = set()  # Track by date string
        self._last_fa_check: Optional[datetime] = None

        # Register calendar callbacks
        self._register_callbacks()

    def _register_callbacks(self) -> None:
        """Register callbacks with the calendar."""
        self.calendar.on_daily(self._on_new_day)
        self.calendar.on_weekly(self._on_new_week)

        # Phase-specific callbacks
        self.calendar.on_phase(SeasonPhase.FREE_AGENCY, self._on_free_agency_start)
        self.calendar.on_phase(SeasonPhase.DRAFT, self._on_draft_start)
        self.calendar.on_phase(SeasonPhase.TRAINING_CAMP, self._on_training_camp_start)
        self.calendar.on_phase(SeasonPhase.REGULAR_SEASON, self._on_regular_season_start)

    def _on_new_day(self, calendar: LeagueCalendar) -> None:
        """Handle daily event generation."""
        current = calendar.current_date

        # Generate practice events on practice days
        if calendar.day_of_week in self.config.practice_days:
            if calendar.phase in {SeasonPhase.REGULAR_SEASON, SeasonPhase.TRAINING_CAMP, SeasonPhase.PRESEASON}:
                self._generate_practice_event(current)

        # Check for free agents during free agency
        if calendar.phase in {SeasonPhase.FREE_AGENCY, SeasonPhase.POST_DRAFT}:
            self._check_free_agents(current)

        # Random trade offers during tradeable phases
        if calendar.phase.allows_trades:
            self._maybe_generate_trade_offer(current)

        # Generate ticker noise (league happenings)
        self._generate_ticker_noise(current)

    def _on_new_week(self, calendar: LeagueCalendar) -> None:
        """Handle weekly event generation."""
        week = calendar.current_week

        # Generate game event for this week
        if calendar.phase.is_regular_season or calendar.phase == SeasonPhase.PRESEASON:
            self._generate_game_event(week)

        # Generate scouting events during draft season
        if calendar.phase in {SeasonPhase.PRE_DRAFT, SeasonPhase.TRAINING_CAMP}:
            self._generate_scouting_events()

    def _on_free_agency_start(self, calendar: LeagueCalendar) -> None:
        """Handle start of free agency."""
        # Create deadline event
        deadline = create_deadline_event(
            deadline_name="Free Agency Frenzy Ends",
            deadline=calendar.current_date + timedelta(days=3),
            description="Initial free agency signing period ends",
            team_id=self.player_team_id,
        )
        self.events.add(deadline)

        # Generate initial batch of top FA events
        self._generate_top_fa_events()

    def _on_draft_start(self, calendar: LeagueCalendar) -> None:
        """Handle draft day."""
        # The draft itself is a critical event
        draft_event = ManagementEvent(
            event_type="draft_day",
            category=EventCategory.DRAFT,
            priority=EventPriority.CRITICAL,
            title="NFL Draft - Day 1",
            description="The NFL Draft begins. Make your selections wisely.",
            icon="draft",
            scheduled_for=calendar.current_date,
            duration_minutes=240,
            auto_pause=True,
            requires_attention=True,
            can_dismiss=False,
            team_id=self.player_team_id,
        )
        self.events.add(draft_event)

    def _on_training_camp_start(self, calendar: LeagueCalendar) -> None:
        """Handle training camp start."""
        camp_event = ManagementEvent(
            event_type="training_camp_start",
            category=EventCategory.PRACTICE,
            priority=EventPriority.HIGH,
            title="Training Camp Opens",
            description="Training camp has begun. Set your practice priorities.",
            icon="camp",
            scheduled_for=calendar.current_date,
            auto_pause=True,
            requires_attention=True,
            team_id=self.player_team_id,
        )
        self.events.add(camp_event)

        # Roster cut deadline
        cut_deadline = create_deadline_event(
            deadline_name="53-Man Roster Deadline",
            deadline=calendar.current_date + timedelta(days=30),
            description="Rosters must be trimmed to 53 players",
            team_id=self.player_team_id,
        )
        self.events.add(cut_deadline)

    def _on_regular_season_start(self, calendar: LeagueCalendar) -> None:
        """Handle regular season start."""
        # Generate Week 1 game event immediately
        self._generate_game_event(1)

        # Trade deadline event (Week 8)
        trade_deadline = create_deadline_event(
            deadline_name="Trade Deadline",
            deadline=calendar.current_date + timedelta(weeks=8),
            description="Last day to make trades",
            team_id=self.player_team_id,
        )
        self.events.add(trade_deadline)

    def _generate_practice_event(self, current: datetime) -> None:
        """Generate a practice event for today."""
        date_key = current.strftime("%Y-%m-%d")
        if date_key in self._generated_practice_dates:
            return  # Already generated for this date

        # Also check if there's already a practice event in the queue for today
        # This handles edge cases where the set wasn't populated
        for event in self.events.get_by_category(EventCategory.PRACTICE):
            if event.scheduled_for and event.scheduled_for.strftime("%Y-%m-%d") == date_key:
                self._generated_practice_dates.add(date_key)
                return  # Practice already exists for this day

        practice_time = current.replace(
            hour=self.config.practice_time_hour,
            minute=0,
            second=0,
        )

        practice = create_practice_event(
            scheduled_for=practice_time,
            practice_type="regular",
            team_id=self.player_team_id,
            duration_minutes=120,
        )
        self.events.add(practice)
        self._generated_practice_dates.add(date_key)

    def _generate_game_event(self, week: int) -> None:
        """Generate a game event for the given week."""
        if week in self._generated_game_weeks:
            return

        # Find game for this week
        game = next(
            (g for g in self.schedule if g.week == week),
            None
        )

        if game:
            event = create_game_event(
                scheduled_for=game.game_time,
                opponent_name=game.opponent_name,
                opponent_id=game.opponent_id,
                is_home=game.is_home,
                team_id=self.player_team_id,
                week=week,
            )
            self.events.add(event)
            self._generated_game_weeks.add(week)

    def _check_free_agents(self, current: datetime) -> None:
        """Check for new free agent availability."""
        if self._last_fa_check:
            hours_since = (current - self._last_fa_check).total_seconds() / 3600
            if hours_since < self.config.fa_check_interval_hours:
                return

        # Generate FA events for available players
        for fa in self.free_agents[:5]:  # Top 5 available
            if fa.overall >= self.config.top_fa_threshold:
                event = create_free_agent_event(
                    player_id=fa.player_id,
                    player_name=fa.name,
                    position=fa.position,
                    overall=fa.overall,
                    deadline=current + timedelta(hours=48),
                    team_id=self.player_team_id,
                )
                self.events.add(event)

        self._last_fa_check = current

    def _generate_top_fa_events(self) -> None:
        """Generate events for top free agents at FA start."""
        current = self.calendar.current_date

        for fa in self.free_agents:
            if fa.overall >= 85:  # Elite tier
                event = create_free_agent_event(
                    player_id=fa.player_id,
                    player_name=fa.name,
                    position=fa.position,
                    overall=fa.overall,
                    deadline=current + timedelta(hours=24),  # Short window
                    team_id=self.player_team_id,
                )
                self.events.add(event)

    def _maybe_generate_trade_offer(self, current: datetime) -> None:
        """Maybe generate a random trade offer."""
        if random.random() > self.config.trade_offer_chance:
            return

        # Generate a random trade offer
        fake_team_id = uuid4()
        teams = ["Patriots", "Cowboys", "Packers", "49ers", "Chiefs", "Eagles", "Bills", "Bengals"]
        team_name = random.choice(teams)

        event = create_trade_offer_event(
            from_team_name=team_name,
            from_team_id=fake_team_id,
            offer_summary=f"{team_name} interested in trading for your player",
            deadline=current + timedelta(hours=24),
            team_id=self.player_team_id,
        )
        self.events.add(event)

    def _generate_scouting_events(self) -> None:
        """Generate scouting events for the week."""
        current = self.calendar.current_date

        # Pro day event
        schools = ["Alabama", "Georgia", "Ohio State", "Michigan", "USC", "LSU", "Clemson"]
        school = random.choice(schools)

        event = create_scouting_event(
            event_name=f"{school} Pro Day",
            scheduled_for=current + timedelta(days=2),
            event_subtype="pro_day",
            team_id=self.player_team_id,
        )
        self.events.add(event)

    def _generate_ticker_noise(self, current: datetime) -> None:
        """Generate random ticker items for league ambiance."""
        # Random transactions
        teams = [
            ("Patriots", uuid4()), ("Cowboys", uuid4()), ("Packers", uuid4()),
            ("49ers", uuid4()), ("Chiefs", uuid4()), ("Eagles", uuid4()),
            ("Bills", uuid4()), ("Bengals", uuid4()), ("Ravens", uuid4()),
            ("Dolphins", uuid4()), ("Jets", uuid4()), ("Broncos", uuid4()),
        ]

        positions = ["QB", "RB", "WR", "TE", "OT", "G", "C", "DE", "DT", "LB", "CB", "S"]

        first_names = ["Marcus", "DeShawn", "Tyler", "Jordan", "Chris", "Mike", "David", "Josh"]
        last_names = ["Johnson", "Williams", "Brown", "Davis", "Wilson", "Moore", "Taylor", "Anderson"]

        # Generate a few random ticker items
        for _ in range(random.randint(1, self.config.ticker_events_per_day)):
            item_type = random.choice(["signing", "release", "injury", "rumor"])
            team_name, team_id = random.choice(teams)
            player_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            position = random.choice(positions)

            if item_type == "signing":
                item = ticker_signing(
                    player_name=player_name,
                    team_name=team_name,
                    position=position,
                    team_id=team_id,
                )
            elif item_type == "release":
                item = ticker_release(
                    player_name=player_name,
                    team_name=team_name,
                    position=position,
                    team_id=team_id,
                )
            elif item_type == "injury":
                injuries = ["hamstring", "knee", "ankle", "shoulder", "back"]
                severities = ["questionable", "doubtful", "out"]
                item = ticker_injury(
                    player_name=player_name,
                    team_name=team_name,
                    injury_type=random.choice(injuries),
                    severity=random.choice(severities),
                    team_id=team_id,
                )
            else:
                rumors = [
                    f"{team_name} exploring trade options",
                    f"{team_name} looking at FA market",
                    f"Contract extension talks ongoing for {player_name}",
                ]
                item = ticker_rumor(headline=random.choice(rumors))

            self.ticker.add(item)

    def set_schedule(self, schedule: list[ScheduledGame]) -> None:
        """Set the game schedule."""
        self.schedule = schedule

    def set_free_agents(self, free_agents: list[FreeAgentInfo]) -> None:
        """Set available free agents."""
        self.free_agents = sorted(free_agents, key=lambda fa: -fa.overall)

    def generate_sample_schedule(self, season_year: int = 2024) -> list[ScheduledGame]:
        """Generate a sample 17-game schedule for testing."""
        schedule = []

        opponents = [
            ("Eagles", uuid4()), ("Giants", uuid4()), ("Commanders", uuid4()),
            ("Cowboys", uuid4()), ("49ers", uuid4()), ("Seahawks", uuid4()),
            ("Rams", uuid4()), ("Cardinals", uuid4()), ("Packers", uuid4()),
            ("Bears", uuid4()), ("Vikings", uuid4()), ("Lions", uuid4()),
            ("Saints", uuid4()), ("Falcons", uuid4()), ("Buccaneers", uuid4()),
            ("Panthers", uuid4()), ("Bills", uuid4()),
        ]

        for week in range(1, 18):
            opponent_name, opponent_id = opponents[(week - 1) % len(opponents)]

            # Determine game day (most are Sunday 1pm)
            # Base date: first Sunday of September
            base_date = datetime(season_year, 9, 8, 13, 0)  # 1 PM
            game_date = base_date + timedelta(weeks=week - 1)

            # Some primetime games
            is_primetime = week in {1, 5, 10, 15}
            if is_primetime:
                if week % 2 == 0:
                    game_date = game_date.replace(hour=20, minute=15)  # SNF
                else:
                    game_date = game_date - timedelta(days=3)  # Thursday
                    game_date = game_date.replace(hour=20, minute=15)

            schedule.append(ScheduledGame(
                week=week,
                opponent_id=opponent_id,
                opponent_name=opponent_name,
                is_home=week % 2 == 1,  # Alternate
                game_time=game_date,
                is_primetime=is_primetime,
            ))

        return schedule

    def generate_sample_free_agents(self, count: int = 50) -> list[FreeAgentInfo]:
        """Generate sample free agents for testing."""
        positions = ["QB", "RB", "WR", "WR", "WR", "TE", "OT", "G", "C",
                     "DE", "DT", "LB", "LB", "CB", "CB", "S"]

        first_names = [
            "Marcus", "DeShawn", "Tyler", "Jordan", "Chris", "Mike", "David",
            "Josh", "Brandon", "Kevin", "Aaron", "Ryan", "Derek", "Justin",
            "Jaylen", "Darius", "Antonio", "Malik", "Terrell", "Cameron",
        ]
        last_names = [
            "Johnson", "Williams", "Brown", "Davis", "Wilson", "Moore",
            "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
            "Martin", "Thompson", "Robinson", "Clark", "Lewis", "Walker",
        ]

        free_agents = []
        for _ in range(count):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            position = random.choice(positions)

            # Overall distribution: most are 65-75, few are 80+
            overall = int(random.gauss(72, 8))
            overall = max(60, min(95, overall))

            age = random.randint(24, 34)
            asking_price = int((overall - 60) * 100 + random.randint(0, 500))

            free_agents.append(FreeAgentInfo(
                player_id=uuid4(),
                name=name,
                position=position,
                overall=overall,
                age=age,
                asking_price=asking_price,
            ))

        return sorted(free_agents, key=lambda fa: -fa.overall)

    def generate_random_day_events(
        self,
        week: int,
        day: int,
        phase: SeasonPhase,
    ) -> list[ManagementEvent]:
        """
        Generate events for a specific day following NFL week pattern.

        Day pattern during regular season:
        - Tuesday (1): Practice, Scout Report for Sunday opponent
        - Wednesday (2): Practice, 30% Injury Report, 20% Media
        - Thursday (3): Practice, 20% Media, 10% Player Meeting
        - Friday (4): Practice (final), 15% Trade/Contract
        - Saturday (5): Travel prep (light day)
        - Sunday (6): GAME DAY

        Returns events that should be added to the queue for that day.
        """
        events = []

        # Only generate during regular season or preseason
        if phase not in {SeasonPhase.REGULAR_SEASON, SeasonPhase.PRESEASON}:
            return events

        # Tuesday (day=1): Practice + Scout Report
        if day == 1:
            events.append(self._create_practice_day_event(week, day))
            # Generate scout report for upcoming opponent
            scout_event = self._create_scout_report_for_week(week, day)
            if scout_event:
                events.append(scout_event)

        # Wednesday (day=2): Practice + random events
        elif day == 2:
            events.append(self._create_practice_day_event(week, day))
            if random.random() < 0.30:
                events.append(self._create_injury_report_event(week, day))
            if random.random() < 0.20:
                events.append(self._create_media_request_event(week, day))

        # Thursday (day=3): Practice + random events
        elif day == 3:
            events.append(self._create_practice_day_event(week, day))
            if random.random() < 0.20:
                events.append(self._create_media_request_event(week, day))
            if random.random() < 0.10:
                events.append(self._create_player_meeting_event(week, day))

        # Friday (day=4): Final practice + maybe trade/contract
        elif day == 4:
            events.append(self._create_practice_day_event(week, day, is_final=True))
            if random.random() < 0.15:
                events.append(self._create_contract_event(week, day))

        # Saturday (day=5): Light travel day - minimal events
        elif day == 5:
            # Very rare event on travel day
            if random.random() < 0.05:
                events.append(self._create_media_request_event(week, day))

        # Sunday (day=6): GAME DAY
        elif day == 6:
            game_event = self._create_game_day_event(week, day)
            if game_event:
                events.append(game_event)

        return events

    def _create_scout_report_for_week(self, week: int, day: int) -> Optional[ManagementEvent]:
        """Create scout report for this week's opponent."""
        # Find game for this week
        game = next(
            (g for g in self.schedule if g.week == week),
            None
        )

        if not game:
            return None

        return create_scout_report_event(
            opponent_name=game.opponent_name,
            opponent_id=game.opponent_id,
            week=week,
            scheduled_week=week,
            scheduled_day=day,
            team_id=self.player_team_id,
        )

    def _create_game_day_event(self, week: int, day: int) -> Optional[ManagementEvent]:
        """Create game day event for this week."""
        # Find game for this week
        game = next(
            (g for g in self.schedule if g.week == week),
            None
        )

        if not game:
            return None

        location = "vs" if game.is_home else "@"
        return ManagementEvent(
            event_type="game_day",
            category=EventCategory.GAME,
            priority=EventPriority.CRITICAL,
            title=f"Week {week}: {location} {game.opponent_name}",
            description=f"Game {'at home' if game.is_home else 'on the road'} against {game.opponent_name}",
            icon="game",
            display_mode=DisplayMode.PANE,
            scheduled_week=week,
            scheduled_day=day,
            auto_pause=True,
            requires_attention=True,
            can_dismiss=False,
            can_delegate=True,  # Can sim
            team_id=self.player_team_id,
            payload={
                "opponent_id": str(game.opponent_id),
                "opponent_name": game.opponent_name,
                "is_home": game.is_home,
                "week": week,
            },
        )

    def _create_contract_event(self, week: int, day: int) -> ManagementEvent:
        """Create a contract/trade related event."""
        event_types = [
            ("trade_offer", "Trade Offer", "A team has expressed interest in your player"),
            ("contract_demand", "Contract Talk", "A player wants to discuss their future"),
        ]
        event_type, title, desc = random.choice(event_types)

        return ManagementEvent(
            event_type=event_type,
            category=EventCategory.CONTRACT,
            priority=EventPriority.NORMAL,
            title=title,
            description=desc,
            icon="contract",
            display_mode=DisplayMode.PANE,
            scheduled_week=week,
            scheduled_day=day,
            requires_attention=True,
            can_dismiss=True,
        )

    def _create_practice_day_event(self, week: int, day: int, is_final: bool = False) -> ManagementEvent:
        """Create a practice event for a specific day."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        title = f"{day_names[day]} Practice"
        if is_final:
            title = "Final Practice"

        return ManagementEvent(
            event_type="practice",
            category=EventCategory.PRACTICE,
            priority=EventPriority.NORMAL,
            title=title,
            description="Allocate practice time and focus areas",
            icon="practice",
            display_mode=DisplayMode.PANE,
            scheduled_week=week,
            scheduled_day=day,
            status=EventStatus.PENDING,
            requires_attention=True,
            can_dismiss=True,
            can_delegate=True,
            payload={
                "is_final": is_final,
            },
        )

    def _create_media_request_event(self, week: int, day: int) -> ManagementEvent:
        """Create a media request event."""
        topics = [
            "Your team's performance this season",
            "The upcoming matchup",
            "A recent controversial call",
            "Your quarterback's development",
            "Team chemistry",
        ]
        return ManagementEvent(
            event_type="media_request",
            category=EventCategory.MEDIA,
            priority=EventPriority.LOW,
            title="Press Conference Request",
            description=f"Media wants to discuss: {random.choice(topics)}",
            icon="media",
            display_mode=DisplayMode.MODAL,
            scheduled_week=week,
            scheduled_day=day,
            requires_attention=False,
            can_dismiss=True,
        )

    def _create_injury_report_event(self, week: int, day: int) -> ManagementEvent:
        """Create an injury report event."""
        return ManagementEvent(
            event_type="injury_report",
            category=EventCategory.INJURY,
            priority=EventPriority.HIGH,
            title="Injury Report Update",
            description="Review player injury statuses",
            icon="injury",
            display_mode=DisplayMode.MODAL,
            scheduled_week=week,
            scheduled_day=day,
            auto_pause=True,
            requires_attention=True,
            can_dismiss=False,
        )

    def _create_player_meeting_event(self, week: int, day: int) -> ManagementEvent:
        """Create a player meeting request event."""
        reasons = [
            "wants to discuss playing time",
            "has concerns about the game plan",
            "wants to talk about their future",
            "requested a private meeting",
        ]
        return ManagementEvent(
            event_type="player_meeting",
            category=EventCategory.PLAYER,
            priority=EventPriority.NORMAL,
            title="Player Meeting Request",
            description=f"A player {random.choice(reasons)}",
            icon="player",
            display_mode=DisplayMode.PANE,
            scheduled_week=week,
            scheduled_day=day,
            requires_attention=True,
            can_dismiss=True,
        )


def create_triggered_event(
    trigger: "EventTrigger",
    source_event: ManagementEvent,
) -> Optional[ManagementEvent]:
    """
    Create a follow-up event from a trigger.

    Called when an event's trigger condition is met.
    The new event is scheduled based on the trigger's delay_days.
    """
    from huddle.management.events import EventTrigger

    # Calculate scheduled day (source day + delay)
    source_week = source_event.scheduled_week or 1
    source_day = source_event.scheduled_day or 0
    total_days = source_day + trigger.delay_days

    new_week = source_week + (total_days // 7)
    new_day = total_days % 7

    # Create the triggered event
    new_event = ManagementEvent(
        event_type=trigger.event_type,
        category=source_event.category,  # Inherit category
        priority=EventPriority.NORMAL,
        title=trigger.event_type.replace("_", " ").title(),
        description=f"Follow-up from: {source_event.title}",
        icon=source_event.icon,
        scheduled_week=new_week,
        scheduled_day=new_day,
        arc_id=source_event.arc_id or source_event.id,  # Link to arc
        payload=trigger.payload.copy() if trigger.payload else {},
    )

    return new_event
