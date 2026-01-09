# Management System - Backend

Comprehensive documentation for the management/franchise backend systems.

**Location**: `huddle/management/`

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [LeagueState - Central Orchestrator](#leaguestate---central-orchestrator)
3. [LeagueCalendar - Time Management](#leaguecalendar---time-management)
4. [Events System](#events-system)
5. [Event Generators](#event-generators)
6. [Clipboard/UI State](#clipboardui-state)
7. [Ticker/News Feed](#tickernews-feed)
8. [Health System](#health-system)
9. [Draft Board](#draft-board)
10. [Management Service](#management-service)
11. [Data Flow](#data-flow)
12. [Integration Points](#integration-points)
13. [Core Infrastructure Extensions](#core-infrastructure-extensions)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React/TypeScript)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ Management   │  │   Zustand    │  │  useManagementWebSocket  │   │
│  │   Screen     │←─│    Store     │←─│        Hook              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑ WebSocket + REST
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  management  │  │  management  │  │   ManagementService +    │   │
│  │   router     │  │   websocket  │  │   SessionManager         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                    Management Layer (Game Loop)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ LeagueState  │  │  Calendar    │  │  EventQueue + Generator  │   │
│  │ (controller) │  │  (time)      │  │  (events)                │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                       Core Domain Models                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Player  │ │   Team   │ │ League   │ │ Contract │ │ Scouting │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Structure

| File | Purpose | Key Classes |
|------|---------|-------------|
| `league.py` | State orchestration | `LeagueState` |
| `calendar.py` | Time progression | `LeagueCalendar`, `SeasonPhase`, `TimeSpeed` |
| `events.py` | Event lifecycle | `ManagementEvent`, `EventQueue`, `EventTrigger` |
| `generators.py` | Event spawning | `EventGenerator`, `EventGeneratorConfig` |
| `clipboard.py` | UI state | `ClipboardState`, `PanelContext` |
| `ticker.py` | News feed | `TickerFeed`, `TickerItem` |
| `health.py` | Injuries/fatigue | `Injury`, `PlayerFatigue`, `PlayerHealth` |
| `draft_board.py` | Draft rankings | `DraftBoard`, `BoardEntry` |

---

## LeagueState - Central Orchestrator

**File**: `huddle/management/league.py`

LeagueState is the single source of truth for franchise/career mode. It coordinates time, events, UI state, and the news feed.

### Class Definition

```python
@dataclass
class LeagueState:
    # Identity
    id: UUID                          # Unique franchise ID
    player_team_id: UUID              # Team controlled by player

    # Subsystems
    calendar: LeagueCalendar          # Time management
    events: EventQueue                # Management events
    clipboard: ClipboardState         # UI navigation state
    ticker: TickerFeed                # News items

    # Auto-pause settings
    auto_pause_on_critical: bool = True
    auto_pause_on_game_day: bool = True
    auto_pause_on_deadline: bool = True

    # Callbacks (not serialized)
    _pause_callbacks: List[Callable]
    _event_callbacks: List[Callable]
    _phase_callbacks: List[Callable]
    _tick_callbacks: List[Callable]
```

### Core Methods

#### `tick(elapsed_seconds: float) -> int`

Main game loop entry point. Returns minutes advanced.

```python
def tick(self, elapsed_seconds: float) -> int:
    """Advance game time and process events.

    1. Advance calendar time
    2. Update event queue (activate/expire)
    3. Check auto-pause conditions
    4. Process event triggers
    5. Clean up completed events
    6. Clean up expired ticker items
    7. Fire callbacks

    Returns: Minutes of game time advanced
    """
```

#### Time Control

```python
def pause(self) -> None:
    """Pause the game clock."""

def play(self, speed: TimeSpeed = TimeSpeed.NORMAL) -> None:
    """Resume at specified speed."""

def toggle_pause(self) -> None:
    """Toggle between paused and playing."""
```

#### Event Management

```python
def add_event(self, event: ManagementEvent) -> None:
    """Add event to queue, auto-pause if critical."""

def attend_event(self, event_id: str) -> ManagementEvent:
    """Mark event as attended, return for UI display."""

def dismiss_event(self, event_id: str) -> bool:
    """Dismiss event if dismissable."""
```

#### Practice System

```python
def run_practice(
    self,
    playbook_pct: float,      # 0-100, time on playbook reps
    development_pct: float,   # 0-100, time on player development
    game_prep_pct: float      # 0-100, time on opponent prep
) -> PracticeResult:
    """Execute practice with time allocation.

    Effects:
    - Playbook: Increases play mastery for players
    - Development: Progresses attribute growth
    - Game Prep: Builds opponent familiarity bonus
    """
```

#### Approval System

```python
def process_weekly_approval(self) -> None:
    """Apply weekly approval drift based on performance."""

def apply_team_result_approval(self, win: bool, margin: int) -> None:
    """Adjust owner/fan approval based on game result."""

def update_depth_chart(self, changes: Dict) -> None:
    """Modify depth chart, may affect approval."""
```

### Auto-Pause Logic

LeagueState implements intelligent auto-pausing:

```python
def _check_auto_pause(self, event: ManagementEvent) -> bool:
    """Determine if event should trigger auto-pause.

    Pauses for:
    - CRITICAL priority events (if auto_pause=True on event)
    - Events affecting player's team specifically
    - Game events for player's team
    - Deadline events (if auto_pause_on_deadline enabled)

    Slows (but doesn't pause) for:
    - HIGH priority events requiring attention
    """
```

### Callback System

Register handlers for game events:

```python
def on_pause(self, callback: Callable[[str], None]) -> None:
    """Called when auto-pause triggers. Receives reason string."""

def on_event_needs_attention(self, callback: Callable[[ManagementEvent], None]) -> None:
    """Called when event becomes PENDING and requires attention."""

def on_phase_change(self, callback: Callable[[SeasonPhase, SeasonPhase], None]) -> None:
    """Called when season phase changes. Receives (old, new)."""

def on_tick(self, callback: Callable[[int], None]) -> None:
    """Called every tick. Receives minutes advanced."""
```

### Serialization

```python
def to_dict(self) -> Dict:
    """Serialize state for persistence/API response."""

@classmethod
def from_dict(cls, data: Dict) -> 'LeagueState':
    """Restore state from serialized form."""
```

---

## LeagueCalendar - Time Management

**File**: `huddle/management/calendar.py`

Manages the passage of time through an NFL season with smooth minute-by-minute progression.

### SeasonPhase Enum

14 distinct season phases:

```python
class SeasonPhase(str, Enum):
    # Offseason (February - March)
    OFFSEASON_EARLY = "offseason_early"
    FREE_AGENCY_LEGAL_TAMPERING = "free_agency_legal_tampering"
    FREE_AGENCY = "free_agency"

    # Draft (April)
    PRE_DRAFT = "pre_draft"
    DRAFT = "draft"
    POST_DRAFT = "post_draft"

    # Programs (May - August)
    OTA = "ota"                    # Organized Team Activities
    MINICAMP = "minicamp"
    TRAINING_CAMP = "training_camp"
    PRESEASON = "preseason"

    # Season (September - February)
    REGULAR_SEASON = "regular_season"
    WILD_CARD = "wild_card"
    DIVISIONAL = "divisional"
    CONFERENCE_CHAMPIONSHIP = "conference_championship"
    SUPER_BOWL = "super_bowl"
```

#### Phase Properties

```python
@property
def is_offseason(self) -> bool:
    """True during offseason phases."""

@property
def is_regular_season(self) -> bool:
    """True during regular season only."""

@property
def is_playoffs(self) -> bool:
    """True during any playoff round."""

@property
def allows_trades(self) -> bool:
    """True if trades can be executed."""

@property
def allows_free_agent_signings(self) -> bool:
    """True if FA signings allowed."""
```

### TimeSpeed Enum

6 simulation speeds:

```python
class TimeSpeed(str, Enum):
    PAUSED = "paused"           # 0x - frozen
    SLOW = "slow"               # 2x - detailed observation
    NORMAL = "normal"           # 30x - standard play
    FAST = "fast"               # 240x - quick progression
    VERY_FAST = "very_fast"     # 720x - rapid sim
    INSTANT = "instant"         # 2880x - skip to next event
```

Speed represents **game minutes per real second**:
- SLOW: 2 game minutes per real second
- NORMAL: 30 game minutes per real second (1 hour = 2 real seconds)
- INSTANT: 2880 game minutes per real second (1 day = 0.5 real seconds)

### LeagueCalendar Class

```python
@dataclass
class LeagueCalendar:
    season_year: int              # e.g., 2024
    current_date: datetime        # Current game date/time
    phase: SeasonPhase            # Current season phase
    current_week: int             # Week number (1-18 for regular season)
    speed: TimeSpeed              # Current simulation speed

    # Callbacks
    _phase_callbacks: List[Callable]
    _daily_callbacks: List[Callable]
    _weekly_callbacks: List[Callable]
```

#### Time Progression

```python
def tick(self, real_elapsed_seconds: float) -> int:
    """Advance time based on elapsed real time.

    - Converts real seconds to game minutes using speed multiplier
    - Advances minute-by-minute (max 5 minutes per tick for smoothness)
    - Checks for day/week boundaries
    - Triggers phase transitions when appropriate

    Returns: Game minutes advanced
    """

def advance_minutes(self, minutes: int) -> None:
    """Immediately advance by fixed minutes (ignores speed)."""

def advance_to_next_day(self) -> None:
    """Skip to start of next day."""

def advance_to_next_week(self) -> None:
    """Skip to start of next week."""
```

#### Phase Transitions

```python
def _check_phase_transition(self) -> Optional[SeasonPhase]:
    """Determine if date triggers phase change.

    Phase transitions are date-based:
    - March 1: FREE_AGENCY_LEGAL_TAMPERING
    - March 15: FREE_AGENCY
    - April 1: PRE_DRAFT
    - April 25: DRAFT (3 days)
    - April 28: POST_DRAFT
    - May 1: OTA
    - June 1: MINICAMP
    - July 15: TRAINING_CAMP
    - August 1: PRESEASON
    - September (week 1): REGULAR_SEASON
    - etc.
    """
```

#### Display Properties

```python
@property
def day_of_week(self) -> int:
    """0=Monday, 6=Sunday"""

@property
def day_name(self) -> str:
    """'Monday', 'Tuesday', etc."""

@property
def is_game_day(self) -> bool:
    """True on Sundays during regular season."""

@property
def time_display(self) -> str:
    """'2:30 PM' format"""

@property
def date_display(self) -> str:
    """'September 10, 2024' format"""

@property
def week_display(self) -> str:
    """'Week 1' or 'Wild Card' etc."""
```

#### Factory Methods

```python
@classmethod
def new_season(
    cls,
    year: int,
    phase: SeasonPhase = SeasonPhase.TRAINING_CAMP
) -> 'LeagueCalendar':
    """Create calendar at specific phase start date."""
```

---

## Events System

**File**: `huddle/management/events.py`

The event system manages all management tasks, decisions, and notifications.

### EventCategory Enum

16 categories of events:

```python
class EventCategory(str, Enum):
    FREE_AGENCY = "free_agency"
    TRADE = "trade"
    CONTRACT = "contract"
    ROSTER = "roster"
    PRACTICE = "practice"
    MEETING = "meeting"
    GAME = "game"
    TEAM = "team"
    PLAYER = "player"
    SCOUTING = "scouting"
    DRAFT = "draft"
    STAFF = "staff"
    MEDIA = "media"
    INJURY = "injury"
    DEADLINE = "deadline"
    SYSTEM = "system"
```

### EventPriority Enum

5 priority levels:

```python
class EventPriority(int, Enum):
    CRITICAL = 1    # Game day, must-handle deadlines
    HIGH = 2        # Important decisions, top FA available
    NORMAL = 3      # Standard events
    LOW = 4         # Optional, can defer
    BACKGROUND = 5  # Informational only
```

### EventStatus Enum

7 lifecycle states:

```python
class EventStatus(str, Enum):
    SCHEDULED = "scheduled"      # Future event, not yet active
    PENDING = "pending"          # Active, awaiting attention
    IN_PROGRESS = "in_progress"  # Player is handling it
    ATTENDED = "attended"        # Completed successfully
    EXPIRED = "expired"          # Deadline passed
    DISMISSED = "dismissed"      # Player chose to skip
    AUTO_RESOLVED = "auto_resolved"  # System handled it
```

### DisplayMode Enum

How events appear in UI:

```python
class DisplayMode(str, Enum):
    PANE = "pane"      # Workspace card/pane
    MODAL = "modal"    # Blocking overlay dialog
    TICKER = "ticker"  # News ticker only (no interaction)
```

### ManagementEvent Class

```python
@dataclass
class ManagementEvent:
    # Identity
    id: str                        # Unique event ID
    event_type: str                # Specific type (e.g., "free_agent_available")
    category: EventCategory
    priority: EventPriority

    # Display
    title: str                     # "Star WR Available"
    description: str               # Markdown content
    icon: str                      # Icon name for UI
    display_mode: DisplayMode

    # Timing
    created_at: datetime
    scheduled_for: Optional[datetime]  # When to activate
    deadline: Optional[datetime]       # When it expires
    duration_minutes: int              # How long event takes
    scheduled_week: Optional[int]      # NFL week (1-18)
    scheduled_day: Optional[int]       # Day of week (0-6)

    # Lifecycle
    status: EventStatus = EventStatus.SCHEDULED

    # Behavior
    auto_pause: bool = False       # Pause game when activated
    requires_attention: bool = False  # Can't be ignored
    can_dismiss: bool = True       # Player can skip
    can_delegate: bool = False     # Can assign to assistant

    # Relations
    team_id: Optional[UUID]        # Related team
    player_ids: List[UUID]         # Related players
    staff_ids: List[UUID]          # Related staff
    arc_id: Optional[str]          # Event arc grouping

    # Data
    payload: Dict[str, Any]        # Event-specific data

    # Triggers (for follow-up events)
    triggers: List[EventTrigger] = field(default_factory=list)
```

#### Lifecycle Methods

```python
def activate(self) -> None:
    """Transition SCHEDULED → PENDING."""

def attend(self) -> None:
    """Transition PENDING → IN_PROGRESS → ATTENDED."""

def complete(self) -> None:
    """Mark as ATTENDED."""

def expire(self) -> None:
    """Mark as EXPIRED (deadline passed)."""

def dismiss(self) -> bool:
    """Mark as DISMISSED if can_dismiss=True."""

def delegate(self) -> bool:
    """Delegate if can_delegate=True."""
```

#### Properties

```python
@property
def is_active(self) -> bool:
    """True if PENDING or IN_PROGRESS."""

@property
def is_expired(self) -> bool:
    """True if past deadline."""

@property
def is_urgent(self) -> bool:
    """True if CRITICAL or HIGH priority and requires attention."""
```

### EventTrigger Class

Creates follow-up events when parent events resolve:

```python
@dataclass
class EventTrigger:
    condition: TriggerCondition  # When to fire
    spawn_event_type: str        # Event type to create
    delay_days: int = 0          # Days after trigger
    delay_hours: int = 0         # Hours after trigger
    probability: float = 1.0     # Chance to fire (0-1)
    arc_id: Optional[str] = None # Link to event arc
```

**TriggerCondition Enum**:

```python
class TriggerCondition(str, Enum):
    ON_COMPLETE = "on_complete"  # When attended
    ON_DISMISS = "on_dismiss"    # When dismissed
    ON_EXPIRE = "on_expire"      # When deadline passes
    ON_CHOICE = "on_choice"      # Based on player decision
```

### EventQueue Class

Manages the collection of events:

```python
@dataclass
class EventQueue:
    events: List[ManagementEvent] = field(default_factory=list)

    # Callbacks
    _activation_callbacks: List[Callable]
    _expiration_callbacks: List[Callable]
```

#### CRUD Operations

```python
def add(self, event: ManagementEvent) -> None:
    """Add event to queue."""

def remove(self, event_id: str) -> bool:
    """Remove event by ID."""

def get(self, event_id: str) -> Optional[ManagementEvent]:
    """Get event by ID."""
```

#### Lifecycle Processing

```python
def update(self, current_time: datetime) -> None:
    """Process event lifecycle transitions.

    1. Activate SCHEDULED events whose time has come
    2. Expire PENDING events past deadline
    3. Fire appropriate callbacks
    """

def process_triggers(self, event: ManagementEvent) -> List[ManagementEvent]:
    """Spawn follow-up events from triggers."""

def clear_completed(self) -> int:
    """Remove terminal status events. Returns count removed."""
```

#### Query Methods

```python
def get_pending(self) -> List[ManagementEvent]:
    """Get all PENDING events."""

def get_by_category(self, category: EventCategory) -> List[ManagementEvent]:
    """Filter by category."""

def get_by_status(self, status: EventStatus) -> List[ManagementEvent]:
    """Filter by status."""

def get_upcoming(self, days: int = 7) -> List[ManagementEvent]:
    """Get SCHEDULED events in next N days."""

def get_urgent(self) -> List[ManagementEvent]:
    """Get urgent events (CRITICAL/HIGH, requires attention)."""

def get_events_for_day(self, week: int, day: int) -> List[ManagementEvent]:
    """Get events scheduled for specific week/day."""
```

### Event Factory Functions

Common event creation:

```python
def create_free_agent_event(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    asking_price: int
) -> ManagementEvent:
    """Create FA available event."""

def create_practice_event(
    week: int,
    day: int,
    practice_type: str = "regular"
) -> ManagementEvent:
    """Create practice session event."""

def create_game_event(
    week: int,
    opponent_id: UUID,
    opponent_name: str,
    is_home: bool,
    is_primetime: bool = False
) -> ManagementEvent:
    """Create game day event."""

def create_trade_offer_event(
    offering_team_id: UUID,
    offering_team_name: str,
    players_offered: List[Dict],
    players_requested: List[Dict],
    picks_offered: List[str],
    picks_requested: List[str]
) -> ManagementEvent:
    """Create incoming trade offer."""

def create_contract_event(
    player_id: UUID,
    player_name: str,
    event_subtype: str,  # "expiring", "holdout", "extension_request"
    years_remaining: int,
    current_salary: int
) -> ManagementEvent:
    """Create contract-related event."""

def create_scouting_event(
    prospect_id: UUID,
    prospect_name: str,
    position: str,
    school: str,
    event_subtype: str  # "pro_day", "private_workout", "interview"
) -> ManagementEvent:
    """Create scouting opportunity."""

def create_deadline_event(
    deadline_type: str,
    deadline_date: datetime,
    description: str
) -> ManagementEvent:
    """Create deadline reminder."""

def create_scout_report_event(
    opponent_id: UUID,
    opponent_name: str,
    week: int,
    tendencies: Dict
) -> ManagementEvent:
    """Create opponent scout report with AI-generated tendencies."""
```

#### Specialized Event Factories

```python
def create_bidding_war_event(player_id, player_name, teams_involved) -> ManagementEvent
def create_cap_warning_event(current_cap, cap_limit, overage) -> ManagementEvent
def create_cut_recommendation_event(player_id, player_name, savings) -> ManagementEvent
def create_injury_event(player_id, player_name, injury_type, weeks_out) -> ManagementEvent
def create_media_event(topic, questions, player_ids) -> ManagementEvent
def create_team_meeting_event(meeting_type, agenda) -> ManagementEvent
```

---

## Event Generators

**File**: `huddle/management/generators.py`

Automatically spawns events based on calendar progression and game state.

### ScheduledGame Class

```python
@dataclass
class ScheduledGame:
    week: int
    opponent_id: UUID
    opponent_name: str
    is_home: bool
    game_time: datetime
    is_divisional: bool
    is_primetime: bool
```

### FreeAgentInfo Class

```python
@dataclass
class FreeAgentInfo:
    player_id: UUID
    name: str
    position: str
    overall: int
    age: int
    asking_price: int
```

### EventGeneratorConfig Class

```python
@dataclass
class EventGeneratorConfig:
    # Practice
    practice_days: List[int] = field(default_factory=lambda: [1, 2, 3, 4])  # Tue-Fri
    practice_time_hour: int = 14  # 2 PM

    # Free Agency
    fa_check_interval_hours: int = 12
    top_fa_threshold: int = 80  # OVR threshold for "top FA" events

    # Trades
    trade_offer_chance: float = 0.10  # 10% per day

    # Scouting
    workouts_per_week: int = 3

    # Ticker
    ticker_events_per_day: int = 5
```

### EventGenerator Class

```python
class EventGenerator:
    def __init__(
        self,
        config: EventGeneratorConfig = None,
        event_queue: EventQueue = None,
        ticker: TickerFeed = None
    ):
        self.config = config or EventGeneratorConfig()
        self.queue = event_queue
        self.ticker = ticker
        self.schedule: List[ScheduledGame] = []
        self.free_agents: List[FreeAgentInfo] = []
```

#### Setup Methods

```python
def set_schedule(self, games: List[ScheduledGame]) -> None:
    """Set team's schedule for game event generation."""

def set_free_agents(self, agents: List[FreeAgentInfo]) -> None:
    """Set available free agents for FA events."""

def generate_sample_schedule(self, team_id: UUID) -> List[ScheduledGame]:
    """Generate placeholder schedule for testing."""

def generate_sample_free_agents(self, count: int = 50) -> List[FreeAgentInfo]:
    """Generate placeholder FAs for testing."""
```

#### Calendar Integration

```python
def register_with_calendar(self, calendar: LeagueCalendar) -> None:
    """Register callbacks for daily/weekly/phase events."""

def _on_new_day(self) -> None:
    """Called each new day - generate daily events."""

def _on_new_week(self) -> None:
    """Called each new week - generate weekly events."""

def _on_phase_change(self, old: SeasonPhase, new: SeasonPhase) -> None:
    """Called on phase transitions - generate phase-specific events."""
```

#### Event Generation

```python
def generate_random_day_events(
    self,
    week: int,
    day: int,
    phase: SeasonPhase
) -> List[ManagementEvent]:
    """Generate events for a specific day following NFL patterns.

    NFL Weekly Pattern:
    - Monday: Film review, injury updates
    - Tuesday: Practice + Scout Report
    - Wednesday: Practice + random events
    - Thursday: Practice + media availability
    - Friday: Practice + travel prep
    - Saturday: Light walkthrough, meetings
    - Sunday: GAME DAY

    Returns list of events to add to queue.
    """
```

#### Phase-Specific Generators

```python
def _generate_free_agency_start(self) -> List[ManagementEvent]:
    """Generate events for FA period opening."""

def _generate_draft_start(self) -> List[ManagementEvent]:
    """Generate events for draft week."""

def _generate_training_camp_start(self) -> List[ManagementEvent]:
    """Generate events for camp opening."""

def _generate_regular_season_start(self) -> List[ManagementEvent]:
    """Generate events for season opener."""
```

### Trigger Event Creation

```python
def create_triggered_event(
    trigger: EventTrigger,
    parent_event: ManagementEvent,
    current_time: datetime
) -> ManagementEvent:
    """Create follow-up event from trigger.

    - Inherits arc_id from parent if trigger doesn't specify
    - Schedules based on delay_days/delay_hours
    - Links to parent via payload
    """
```

---

## Clipboard/UI State

**File**: `huddle/management/clipboard.py`

Manages frontend UI navigation state server-side for sync across devices.

### ClipboardTab Enum

15 navigation tabs:

```python
class ClipboardTab(str, Enum):
    # Primary
    EVENTS = "events"
    ROSTER = "roster"
    DEPTH_CHART = "depth_chart"
    SCHEDULE = "schedule"

    # Personnel
    FREE_AGENTS = "free_agents"
    TRADE_BLOCK = "trade_block"
    DRAFT_BOARD = "draft_board"

    # Staff
    COACHING_STAFF = "coaching_staff"
    FRONT_OFFICE = "front_office"

    # Team
    PLAYBOOK = "playbook"
    GAMEPLAN = "gameplan"
    FINANCES = "finances"

    # League
    STANDINGS = "standings"
    LEAGUE_LEADERS = "league_leaders"
    TRANSACTIONS = "transactions"
```

### PanelType Enum

24 panel types for detailed views:

```python
class PanelType(str, Enum):
    # Event panels
    PRACTICE_DETAIL = "practice_detail"
    GAME_DETAIL = "game_detail"
    MEETING_DETAIL = "meeting_detail"
    CONTRACT_DETAIL = "contract_detail"
    TRADE_DETAIL = "trade_detail"
    SCOUTING_DETAIL = "scouting_detail"

    # Roster panels
    ROSTER_LIST = "roster_list"
    PLAYER_DETAIL = "player_detail"
    PLAYER_CONTRACT = "player_contract"
    PLAYER_STATS = "player_stats"

    # More panels...
    DEPTH_CHART = "depth_chart"
    SCHEDULE = "schedule"
    FA_LIST = "fa_list"
    FA_DETAIL = "fa_detail"
    TRADE_BLOCK = "trade_block"
    DRAFT_BOARD = "draft_board"
    PROSPECT_DETAIL = "prospect_detail"

    # Staff
    STAFF_LIST = "staff_list"
    STAFF_DETAIL = "staff_detail"

    # Team
    PLAYBOOK = "playbook"
    GAMEPLAN = "gameplan"
    FINANCES = "finances"

    # League
    STANDINGS = "standings"
    LEADERS = "leaders"
    LEAGUE_TRANSACTIONS = "league_transactions"

    # Special
    EMPTY = "empty"
    LOADING = "loading"
```

### PanelContext Class

Current panel state with navigation history:

```python
@dataclass
class PanelContext:
    panel_type: PanelType

    # Entity references
    event_id: Optional[str] = None
    player_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    game_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    prospect_id: Optional[UUID] = None

    # Additional state
    context_data: Dict[str, Any] = field(default_factory=dict)

    # Navigation history
    previous_panel: Optional['PanelContext'] = None
```

#### Navigation Methods

```python
def with_player(self, player_id: UUID) -> 'PanelContext':
    """Create new context for player detail, preserving history."""

def with_event(self, event_id: str) -> 'PanelContext':
    """Create new context for event detail."""

def with_game(self, game_id: UUID) -> 'PanelContext':
    """Create new context for game detail."""

@property
def can_go_back(self) -> bool:
    """True if navigation history exists."""

def go_back(self) -> Optional['PanelContext']:
    """Return previous panel context."""
```

### ClipboardState Class

Complete clipboard UI state:

```python
@dataclass
class ClipboardState:
    active_tab: ClipboardTab = ClipboardTab.EVENTS
    panel: PanelContext = field(default_factory=lambda: PanelContext(PanelType.EMPTY))

    # Available tabs (changes by phase)
    available_tabs: Set[ClipboardTab] = field(default_factory=set)

    # Tab-specific state
    roster_sort: str = "overall"
    roster_filter: Optional[str] = None  # Position filter
    fa_sort: str = "overall"
    fa_filter: Optional[str] = None
    draft_sort: str = "rank"
    draft_filter: Optional[str] = None

    # Search
    search_query: str = ""
    search_active: bool = False

    # Notification badges
    tab_badges: Dict[ClipboardTab, int] = field(default_factory=dict)
```

#### Navigation Methods

```python
def select_tab(self, tab: ClipboardTab) -> None:
    """Switch to tab if available."""

def set_panel(self, context: PanelContext) -> None:
    """Set current panel with history preservation."""

def navigate_to_player(self, player_id: UUID) -> None:
    """Navigate to player detail panel."""

def navigate_to_event(self, event_id: str) -> None:
    """Navigate to event detail panel."""

def go_back(self) -> bool:
    """Go to previous panel. Returns success."""

def set_badge(self, tab: ClipboardTab, count: int) -> None:
    """Set notification badge count."""

def update_available_tabs(self, phase: SeasonPhase) -> None:
    """Update available tabs based on season phase.

    - DRAFT_BOARD only during draft season
    - FREE_AGENTS only during free agency
    - TRADE_BLOCK only when trades allowed
    """
```

---

## Ticker/News Feed

**File**: `huddle/management/ticker.py`

Real-time news feed for league happenings.

### TickerCategory Enum

15 news categories with visual properties:

```python
class TickerCategory(str, Enum):
    # Transactions
    SIGNING = "signing"
    RELEASE = "release"
    TRADE = "trade"
    WAIVER = "waiver"

    # Games
    SCORE = "score"
    INJURY = "injury"
    INJURY_REPORT = "injury_report"

    # Personnel
    SUSPENSION = "suspension"
    RETIREMENT = "retirement"
    HOLDOUT = "holdout"

    # Draft
    DRAFT_PICK = "draft_pick"
    DRAFT_TRADE = "draft_trade"

    # League
    DEADLINE = "deadline"
    RECORD = "record"
    AWARD = "award"
    RUMOR = "rumor"

    @property
    def icon(self) -> str:
        """Icon name for this category."""

    @property
    def color(self) -> str:
        """Color code for this category."""
```

### TickerItem Class

Single news item:

```python
@dataclass
class TickerItem:
    # Content
    id: str
    headline: str              # "Eagles sign WR A.J. Brown"
    detail: str                # "4 years, $100M with $57M guaranteed"
    category: TickerCategory

    # Timing
    timestamp: datetime
    expires_at: datetime       # When to remove

    # Relevance
    is_breaking: bool = False  # Breaking news emphasis
    priority: int = 5          # 0-10 scale

    # Relations
    team_ids: List[UUID] = field(default_factory=list)
    player_ids: List[UUID] = field(default_factory=list)

    # Interaction
    is_read: bool = False
    is_clickable: bool = False
    link_event_id: Optional[str] = None  # Link to management event
```

#### Properties

```python
@property
def age_seconds(self) -> float:
    """Seconds since creation."""

@property
def age_display(self) -> str:
    """Humanized age: '2h ago', '3d ago', 'just now'"""

@property
def is_expired(self) -> bool:
    """True if past expiration time."""
```

### Ticker Factory Functions

```python
def ticker_signing(
    player_name: str,
    team_name: str,
    years: int,
    total_value: int,
    guaranteed: int,
    player_id: UUID,
    team_id: UUID
) -> TickerItem:
    """Create signing news item."""

def ticker_release(player_name, team_name, cap_savings, player_id, team_id) -> TickerItem
def ticker_trade(teams, players_moved, picks_moved) -> TickerItem
def ticker_score(home_team, away_team, home_score, away_score, is_final) -> TickerItem
def ticker_injury(player_name, team_name, injury_type, status, player_id) -> TickerItem
def ticker_draft_pick(team_name, pick_number, player_name, position, school) -> TickerItem
def ticker_rumor(subject, rumor_text, believability) -> TickerItem
def ticker_deadline(deadline_type, time_remaining) -> TickerItem
```

### TickerFeed Class

Ring buffer of news items:

```python
@dataclass
class TickerFeed:
    items: List[TickerItem] = field(default_factory=list)
    max_size: int = 100
    default_ttl_hours: int = 24
```

#### Methods

```python
def add(self, item: TickerItem) -> None:
    """Add item to feed.

    - Sets expiration if not set
    - Enforces max_size by removing oldest
    """

def get_active(self) -> List[TickerItem]:
    """Get non-expired items, sorted by priority then time."""

def get_breaking(self) -> List[TickerItem]:
    """Get only breaking news items."""

def get_by_category(self, category: TickerCategory) -> List[TickerItem]:
    """Filter by category."""

def get_for_team(self, team_id: UUID) -> List[TickerItem]:
    """Get items involving specific team."""

def get_recent(self, hours: int = 1) -> List[TickerItem]:
    """Get items from last N hours."""

def get_unread(self) -> List[TickerItem]:
    """Get unread items."""

def mark_read(self, item_id: str) -> None:
    """Mark single item as read."""

def mark_all_read(self) -> None:
    """Mark all items as read."""

def cleanup_expired(self) -> int:
    """Remove expired items. Returns count removed."""
```

#### Properties

```python
@property
def count(self) -> int:
    """Total active items."""

@property
def unread_count(self) -> int:
    """Count of unread items."""

@property
def breaking_count(self) -> int:
    """Count of breaking news items."""
```

---

## Health System

**File**: `huddle/management/health.py` (992 lines)

Comprehensive injury generation, fatigue tracking, body-part durability, and in-game fatigue systems. Calibrated from NFL injury data.

### Calibration Data

Loads from `research/exports/injury_model.json` and `fatigue_model.json` at module import.

### InjuryStatus Enum

```python
class InjuryStatus(Enum):
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"  # Game-time decision
    DOUBTFUL = "doubtful"          # Unlikely to play
    OUT = "out"                    # Will not play
    IR = "ir"                      # Injured reserve (min 4 weeks)
    PUP = "pup"                    # Physically unable to perform
```

### InjuryType Enum

16 injury types with display names:

```python
class InjuryType(Enum):
    LEG_MUSCLE = "Leg Muscle"       # Hamstring, quad, calf
    KNEE_OTHER = "Knee (Other)"     # Non-ligament knee
    KNEE_LIGAMENT = "Knee Ligament" # ACL, MCL, meniscus
    ANKLE = "Ankle"                 # Sprain, fracture
    SHOULDER = "Shoulder"           # Rotator cuff, dislocation
    CONCUSSION = "Concussion"       # Head injury
    FOOT = "Foot"                   # Turf toe, Lisfranc
    BACK = "Back"                   # Disc, muscle
    HIP = "Hip"                     # Flexor, groin
    CHEST_RIBS = "Chest/Ribs"       # Bruised, fractured
    HAND_WRIST = "Hand/Wrist"       # Finger, wrist
    NECK = "Neck"                   # Stinger, strain
    ARM = "Arm"                     # Elbow, bicep
    ACHILLES = "Achilles"           # Season-ending risk
    ILLNESS = "Illness"             # Non-injury
    OTHER = "Other"                 # Miscellaneous
```

### Position Injury Rates

Per-game injury probability by position:

| Position | Per-Game Rate | Modifier |
|----------|---------------|----------|
| QB | 3.3% | 0.6x |
| RB | 4.7% | 0.85x |
| WR | 7.8% | 1.42x |
| TE | 6.3% | 1.14x |
| OL | 5.9% | 1.07x |
| DL | 7.8% | 1.42x |
| LB | 7.5% | 1.35x |
| CB | 7.2% | 1.30x |
| S | 4.7% | 0.85x |

### Injury Type Probabilities

```python
INJURY_TYPE_PROBS = {
    "Leg Muscle": 0.111,      # Most common
    "Knee (Other)": 0.079,
    "Ankle": 0.070,
    "Shoulder": 0.032,
    "Concussion": 0.028,
    "Foot": 0.027,
    "Back": 0.017,
    "Hip": 0.015,
    "Chest/Ribs": 0.014,
    "Hand/Wrist": 0.013,
    "Neck": 0.010,
    "Arm": 0.007,
    "Other": 0.577,           # Catch-all
}
```

### Injury Duration Distributions

| Type | Min Weeks | Typical Weeks | Season-Ending Rate |
|------|-----------|---------------|-------------------|
| Leg Muscle | 1 | 2 | 5% |
| Knee (Other) | 1 | 3 | 12% |
| **Knee Ligament** | 6 | 12 | **65%** |
| Ankle | 1 | 3 | 10% |
| Shoulder | 2 | 4 | 15% |
| Concussion | 1 | 2 | 5% |
| Foot | 2 | 4 | 20% |
| **Achilles** | 6 | 16 | **80%** |
| Other | 1 | 2 | 5% |

### Injury Class

```python
@dataclass
class Injury:
    id: UUID = field(default_factory=uuid4)
    injury_type: str = "Other"
    body_part: str = "Unknown"
    severity: str = "minor"        # "minor", "moderate", "severe", "season_ending"
    weeks_remaining: int = 1
    occurred_date: Optional[datetime] = None
    is_season_ending: bool = False
    on_ir: bool = False            # Management decision, not automatic
    weeks_on_ir: int = 0           # Track for activation eligibility
    affected_side: str = "unknown" # "left", "right", "unknown"
```

#### Injury Status Property

```python
@property
def status(self) -> InjuryStatus:
    """Get game status based on weeks remaining."""
    if self.on_ir:
        return InjuryStatus.IR
    if self.is_season_ending:
        return InjuryStatus.OUT  # Not IR until placed there
    if self.weeks_remaining >= 2:
        return InjuryStatus.OUT
    if self.weeks_remaining == 1:
        return InjuryStatus.DOUBTFUL
    return InjuryStatus.QUESTIONABLE
```

#### Injury Methods

```python
def heal_week(self) -> bool:
    """Advance healing by one week. Returns True if healed."""

def place_on_ir(self) -> None:
    """Management decision to place on IR. Resets weeks_on_ir counter."""

def activate_from_ir(self) -> bool:
    """Attempt activation from IR. Returns False if <4 weeks on IR."""

@property
def ir_eligible_for_return(self) -> bool:
    """True if player has served minimum 4 weeks on IR."""
```

---

### Fatigue System

#### Snap Percentage Targets

Target snap percentages by position (NFL averages):

| Position | Starter Target | Rotation Target |
|----------|---------------|-----------------|
| QB | 100% | 100% |
| RB | 69% | 27% |
| WR | 92% | 53% |
| TE | 83% | 41% |
| OL | 100% | 100% |
| DL | 77% | 47% |
| EDGE | 90% | 42% |
| LB | 100% | 37% |
| CB | 100% | 60% |
| S | 100% | 65% |

#### Fatigue Curve

Performance penalty by snap percentage:

| Snap % | Base Modifier | Notes |
|--------|---------------|-------|
| 0-50% | 1.00 | No penalty |
| 70% | 0.99 | -1% |
| 80% | 0.97 | -3% |
| 90% | 0.94 | -6% |
| 95% | 0.90 | -10% |
| 100% | 0.85 | -15% |

Position modifiers scale the penalty:
- QB: 0.7x (less affected)
- RB: 1.3x (more affected)
- DL: 1.4x (most affected)

#### Cumulative Effects

Multi-game fatigue penalties:

```python
CUMULATIVE_EFFECTS = {
    "games_1": 1.0,          # Fresh
    "games_2": 0.98,         # -2%
    "games_3": 0.95,         # -5%
    "games_4": 0.92,         # -8%
    "bye_week_recovery": 1.05,
    "thursday_game_penalty": 0.97,
}
```

#### Rotation Recommendations

```python
ROTATION_RECS = {
    "RB": {"typical_rotation_size": 2, "optimal_lead_pct": 0.70},
    "DL": {"typical_rotation_size": 6, "optimal_lead_pct": 0.30},
    "WR": {"typical_rotation_size": 4, "optimal_lead_pct": 0.50},
    "TE": {"typical_rotation_size": 2, "optimal_lead_pct": 0.70},
    "LB": {"typical_rotation_size": 4, "optimal_lead_pct": 0.50},
    "CB": {"typical_rotation_size": 3, "optimal_lead_pct": 0.60},
}
```

### PlayerFatigue Class

Cumulative game-to-game fatigue tracking:

```python
@dataclass
class PlayerFatigue:
    player_id: UUID
    current_fatigue: float = 0.0   # 0.0 to 1.0
    games_since_rest: int = 0
    snap_pct_last_game: float = 0.0
    is_rested: bool = True
```

#### Methods

```python
def apply_game(self, snap_pct: float, position: str) -> None:
    """Apply fatigue from a game.

    Fatigue gain = snap_pct × 0.3 × position_modifier
    """

def apply_rest(self, is_bye_week: bool = False) -> None:
    """Apply rest/recovery.

    - Bye week: Full recovery (fatigue = 0)
    - Normal week: Recovers 0.4 if rested, 0.25 if not
    """

def get_performance_modifier(self, position: str) -> float:
    """Get performance modifier based on fatigue.

    Fatigue 0-30%: No penalty
    Fatigue 30-50%: -2%
    Fatigue 50-70%: -5%
    Fatigue 70-90%: -10%
    Fatigue 90%+: -15%

    Also applies cumulative games penalty.
    """
```

---

### PlayerHealth Class

Complete health state combining injuries and fatigue:

```python
@dataclass
class PlayerHealth:
    player_id: UUID
    injuries: list[Injury] = field(default_factory=list)
    fatigue: PlayerFatigue  # Auto-initialized with player_id
    injury_history: list[dict] = field(default_factory=list)
```

#### Properties

```python
@property
def is_healthy(self) -> bool:
    """True if no active injuries."""

@property
def status(self) -> InjuryStatus:
    """Worst status among all active injuries."""

@property
def can_play(self) -> bool:
    """True if HEALTHY or QUESTIONABLE."""
```

#### Methods

```python
def add_injury(self, injury: Injury) -> None:
    """Add a new injury."""

def heal_week(self) -> list[Injury]:
    """Advance healing by one week. Returns list of healed injuries.

    Healed injuries are moved to injury_history.
    """
```

---

### Action-Based Injury System

Injuries can occur from specific in-game actions, with risk based on body-part durability.

#### Action → Body Part Stress

```python
ACTION_BODY_STRESS = {
    # Ballcarrier moves
    "juke": ["left_leg", "right_leg"],
    "spin": ["left_leg", "right_leg", "torso"],
    "cut": ["left_leg", "right_leg"],  # High ACL risk
    "truck": ["torso", "left_arm", "right_arm"],
    "hurdle": ["left_leg", "right_leg"],
    "stiff_arm": ["left_arm", "right_arm"],

    # Receiver actions
    "route_break": ["left_leg", "right_leg"],
    "catch_contested": ["left_arm", "right_arm", "head"],

    # QB actions
    "throw": ["right_arm", "torso"],
    "scramble": ["left_leg", "right_leg"],
    "sack": ["torso", "head", "left_arm", "right_arm"],

    # Blocking/tackling
    "block": ["left_arm", "right_arm", "torso"],
    "pass_block": ["left_arm", "right_arm", "left_leg", "right_leg"],
    "run_block": ["torso", "left_arm", "right_arm"],
    "tackle": ["left_arm", "right_arm", "head"],
    "get_tackled": ["left_leg", "right_leg", "torso", "head"],

    # Coverage
    "backpedal": ["left_leg", "right_leg"],
    "break_on_ball": ["left_leg", "right_leg"],
}
```

#### Action Base Risk

Per-occurrence injury probability:

```python
ACTION_BASE_RISK = {
    # High risk
    "cut": 0.0008,        # ACL risk
    "tackle": 0.0006,
    "get_tackled": 0.0005,
    "sack": 0.0010,

    # Medium risk
    "juke": 0.0004,
    "hurdle": 0.0005,
    "truck": 0.0004,
    "route_break": 0.0003,
    "block": 0.0003,
    "catch_contested": 0.0004,
    "dive": 0.0006,

    # Low risk
    "spin": 0.0002,
    "throw": 0.0001,
    "sprint": 0.0001,
    # ...
}
```

#### Body Part → Injury Types

```python
BODY_PART_INJURIES = {
    "left_leg": ["Leg Muscle", "Knee (Other)", "Knee Ligament",
                 "Ankle", "Foot", "Hip", "Achilles"],
    "right_leg": ["Leg Muscle", "Knee (Other)", "Knee Ligament",
                  "Ankle", "Foot", "Hip", "Achilles"],
    "left_arm": ["Shoulder", "Arm", "Hand/Wrist"],
    "right_arm": ["Shoulder", "Arm", "Hand/Wrist"],
    "torso": ["Back", "Chest/Ribs", "Hip"],
    "head": ["Concussion", "Neck"],
}
```

#### check_action_injury Function

```python
def check_action_injury(
    player_durability: dict[str, int],  # Body part → durability (40-99)
    action: str,
    intensity: float = 1.0,  # 0.5=light, 1.0=normal, 1.5=critical
    current_date: Optional[datetime] = None,
) -> Optional[Injury]:
    """Check if an action causes injury based on body-part durability.

    Risk formula: base_risk × ((100 - durability) / 50) × intensity

    99 durability = 0.02x risk (almost injury-proof)
    75 durability = 0.50x risk (average)
    50 durability = 1.00x risk (fragile)
    40 durability = 1.20x risk (glass)
    """
```

---

### Injury Degradation System

Injuries cause permanent durability loss:

```python
INJURY_DEGRADATION = {
    "Knee Ligament": (8, 15),  # ACL/MCL tears most impactful
    "Achilles": (10, 18),       # Very serious
    "Shoulder": (5, 10),
    "Concussion": (3, 8),       # Cumulative concern
    "Knee (Other)": (3, 7),
    "Ankle": (2, 5),
    "Leg Muscle": (1, 4),
    "Foot": (2, 5),
    "Back": (3, 7),
    "Hip": (2, 5),
    "Chest/Ribs": (1, 3),
    "Hand/Wrist": (1, 3),
    "Neck": (2, 5),
    "Arm": (1, 3),
    "Other": (1, 3),
}
```

```python
def calculate_injury_degradation(injury: Injury) -> int:
    """Calculate durability points to subtract from affected body part.

    Severity affects degradation:
    - season_ending: Max degradation
    - severe: High range
    - moderate: Mid range
    - minor: Low range
    """

def get_durability_attribute_name(body_part: str) -> str:
    """Map body part to attribute name.

    e.g., 'left_leg' → 'left_leg_durability'
    """
```

---

### Body-Part Fatigue System

Per-body-part fatigue tracking during games (separate from cumulative PlayerFatigue):

```python
@dataclass
class BodyPartFatigue:
    legs: float = 0.0    # Affects speed, acceleration, agility
    arms: float = 0.0    # Affects throw power, catch, tackle
    core: float = 0.0    # Affects balance, blocking, break tackle
    cardio: float = 0.0  # Affects stamina, pursuit, awareness
```

#### Action Fatigue Accumulation

```python
ACTION_FATIGUE = {
    # Movement
    "sprint": {"legs": 0.02, "cardio": 0.01},
    "cut": {"legs": 0.03},
    "juke": {"legs": 0.02, "core": 0.01},
    "spin": {"legs": 0.02, "core": 0.015},
    "hurdle": {"legs": 0.025, "core": 0.01},
    "scramble": {"legs": 0.025, "cardio": 0.015},

    # Contact
    "truck": {"core": 0.02, "arms": 0.01},
    "block": {"arms": 0.02, "core": 0.02, "legs": 0.01},
    "pass_block": {"arms": 0.015, "core": 0.015, "legs": 0.01},
    "run_block": {"arms": 0.02, "core": 0.025, "legs": 0.01},
    "tackle": {"arms": 0.02, "legs": 0.02, "cardio": 0.01},
    "get_tackled": {"core": 0.015, "legs": 0.01},

    # Skill actions
    "throw": {"arms": 0.015, "core": 0.01},
    "route_break": {"legs": 0.02},
    "catch_contested": {"arms": 0.015, "core": 0.01},
}
```

#### Fatigue → Attribute Impact

```python
FATIGUE_ATTRIBUTE_IMPACT = {
    "legs": ["speed", "acceleration", "agility", "jumping", "elusiveness"],
    "arms": ["throw_power", "throw_accuracy_short", "throw_accuracy_mid",
             "throw_accuracy_deep", "catching", "tackle", "block_strength"],
    "core": ["balance", "break_tackle", "trucking", "block_shed",
             "impact_blocking", "run_blocking", "pass_blocking"],
    "cardio": ["stamina", "pursuit", "play_recognition", "awareness"],
}
```

#### Fatigue to Modifier

```python
def _fatigue_to_modifier(fatigue_level: float) -> float:
    """Convert fatigue (0.0-1.0) to attribute penalty.

    0.0 fatigue = 1.00x (no penalty)
    0.5 fatigue = 0.925x (-7.5%)
    1.0 fatigue = 0.85x (-15%)
    """
    return 1.0 - (fatigue_level * 0.15)
```

#### BodyPartFatigue Methods

```python
def reset(self) -> None:
    """Reset all fatigue (between games)."""

def apply_action(self, action: str) -> None:
    """Apply fatigue from an action. Clamps to 1.0 max."""

def get_attribute_modifier(self, attribute: str) -> float:
    """Get performance modifier for a specific attribute (0.85-1.0)."""

def get_all_modifiers(self) -> dict[str, float]:
    """Get modifiers for all affected attributes."""
```

---

### Injury Generation Functions

```python
def get_injury_rate(position: str) -> float:
    """Get per-game injury rate for a position.

    Normalizes positions (OT/OG/C → OL, EDGE/NT/DE/DT → DL).
    """

def sample_injury_type() -> str:
    """Sample an injury type based on INJURY_TYPE_PROBS."""

def generate_injury(
    position: str,
    current_date: Optional[datetime] = None
) -> Optional[Injury]:
    """Check if a player gets injured and generate injury details.

    Uses triangular distribution for duration.
    """

def check_practice_injury(
    position: str,
    intensity: str = "normal"  # "light", "normal", "intense"
) -> Optional[Injury]:
    """Check for injury during practice.

    Practice injury rate = 10% of game rate.
    Intensity modifiers: light=0.5x, normal=1.0x, intense=1.5x
    """
```

### Performance Impact Functions

```python
def calculate_snap_penalty(snap_pct: float, position: str) -> float:
    """Calculate performance penalty from snap percentage.

    Returns multiplier (0.85-1.0).
    """

def get_optimal_snap_share(position: str, is_starter: bool = True) -> float:
    """Get optimal snap percentage for a position."""

def get_rotation_recommendation(position: str) -> dict:
    """Get rotation size recommendation for a position.

    Returns: {"typical_rotation_size": int, "optimal_lead_pct": float}
    """
```

---

## Draft Board

**File**: `huddle/management/draft_board.py`

User's personal draft rankings.

### BoardEntry Class

```python
@dataclass
class BoardEntry:
    prospect_id: UUID
    rank: int           # 1-based position
    tier: int           # 1-5 (Elite to Flier)
    notes: str = ""     # User notes
```

### Tier System

| Tier | Name | Description |
|------|------|-------------|
| 1 | Elite | Franchise-changing talent |
| 2 | Blue Chip | Day 1 starters |
| 3 | Starter | Should start within 2 years |
| 4 | Contributor | Depth/special teams |
| 5 | Flier | Worth a late pick |

### DraftBoard Class

```python
@dataclass
class DraftBoard:
    entries: List[BoardEntry] = field(default_factory=list)
```

#### Methods

```python
def add_prospect(self, prospect_id: UUID, tier: int = 3) -> BoardEntry:
    """Add prospect at end of board."""

def remove_prospect(self, prospect_id: UUID) -> bool:
    """Remove prospect and reindex ranks."""

def has_prospect(self, prospect_id: UUID) -> bool:
    """Check if prospect is on board."""

def get_entry(self, prospect_id: UUID) -> Optional[BoardEntry]:
    """Get entry for prospect."""

def set_tier(self, prospect_id: UUID, tier: int) -> bool:
    """Update prospect's tier."""

def set_notes(self, prospect_id: UUID, notes: str) -> bool:
    """Update prospect's notes."""

def reorder(self, prospect_id: UUID, new_rank: int) -> bool:
    """Move prospect to new rank position."""

def move_before(self, prospect_id: UUID, before_id: UUID) -> bool:
    """Move prospect before another prospect."""

def get_by_tier(self, tier: int) -> List[BoardEntry]:
    """Get all entries in tier."""

@property
def count(self) -> int:
    """Number of prospects on board."""
```

---

## Management Service

**File**: `huddle/api/services/management_service.py`

Wraps LeagueState and provides async tick loop + WebSocket integration.

### ManagementService Class

```python
class ManagementService:
    def __init__(self, state: LeagueState, league: League):
        self.state = state
        self.league = league
        self.generator = EventGenerator()
        self._task: Optional[asyncio.Task] = None
        self._websocket: Optional[WebSocket] = None
        self._running = False

        # Additional state
        self.drawer_items: List[Dict] = []
        self.week_journal: List[Dict] = []
        self.draft_board = DraftBoard()
```

### Lifecycle Methods

```python
async def start(self) -> None:
    """Start the async tick loop."""

async def stop(self) -> None:
    """Stop the tick loop gracefully."""
```

### Time Control (Delegation)

```python
def pause(self) -> None:
    """Pause via state."""

def play(self, speed: TimeSpeed = TimeSpeed.NORMAL) -> None:
    """Resume via state."""

def set_speed(self, speed: TimeSpeed) -> None:
    """Set speed via state."""
```

### Event Management (Delegation)

```python
def attend_event(self, event_id: str) -> ManagementEvent:
    """Attend event via state."""

def dismiss_event(self, event_id: str) -> bool:
    """Dismiss event via state."""
```

### Tick Loop

```python
async def _tick_loop(self) -> None:
    """Main async game loop.

    Runs continuously while service is active:
    1. Calculate real elapsed time since last tick
    2. Call state.tick(elapsed)
    3. If time advanced, send WebSocket update
    4. Sleep briefly (0.05s) to prevent busy-wait
    5. Catch and log errors, back off on failure
    """
```

### WebSocket Integration

```python
def attach_websocket(self, ws: WebSocket) -> None:
    """Attach WebSocket for real-time updates."""

def detach_websocket(self) -> None:
    """Detach WebSocket connection."""

async def _send_calendar_update(self) -> None:
    """Send calendar + events state via WebSocket."""

async def _send_event_added(self, event: ManagementEvent) -> None:
    """Send new event notification."""

async def _send_auto_paused(self, reason: str, event_id: str) -> None:
    """Notify of auto-pause."""
```

### State Response Methods

```python
def get_full_state(self) -> LeagueStateResponse:
    """Get complete state for API response."""

def _get_calendar_response(self) -> CalendarStateResponse:
    """Convert calendar to schema."""

def _get_events_response(self) -> EventQueueResponse:
    """Convert events to schema."""

def _get_clipboard_response(self) -> ClipboardStateResponse:
    """Convert clipboard to schema."""
```

### Session Manager

```python
class ManagementSessionManager:
    """Manages multiple active franchise sessions."""

    sessions: Dict[UUID, ManagementService] = {}

    async def create_session(
        self,
        franchise_id: UUID,
        state: LeagueState,
        league: League
    ) -> ManagementService:
        """Create and start new session."""

    async def get_session(self, franchise_id: UUID) -> Optional[ManagementService]:
        """Get existing session."""

    async def destroy_session(self, franchise_id: UUID) -> None:
        """Stop and remove session."""
```

---

## Data Flow

### Game Loop Cycle

```
Frontend WebSocket ─────────────────────────────────────────┐
                                                            │
ManagementService._tick_loop                                │
        │                                                   │
        ▼                                                   │
LeagueState.tick(elapsed_seconds)                          │
        │                                                   │
        ├──► LeagueCalendar.tick()                         │
        │         │                                        │
        │         └──► advance minutes                     │
        │         └──► check phase transitions             │
        │         └──► fire daily/weekly callbacks         │
        │                                                   │
        ├──► EventQueue.update()                           │
        │         │                                        │
        │         └──► SCHEDULED → PENDING                 │
        │         └──► check expirations                   │
        │         └──► fire activation callbacks           │
        │                                                   │
        ├──► _check_auto_pause()                           │
        │         │                                        │
        │         └──► pause if needed                     │
        │         └──► fire pause callbacks                │
        │                                                   │
        ├──► EventQueue.clear_completed()                  │
        │                                                   │
        └──► TickerFeed.cleanup_expired()                  │
                                                            │
        │                                                   │
        ▼                                                   │
WebSocket updates ◄─────────────────────────────────────────┘
```

### Event Lifecycle

```
EventGenerator creates event
        │
        ▼ (SCHEDULED)
ManagementEvent added to EventQueue
        │
        │  (current_date >= scheduled_for)
        ▼
ManagementEvent.activate() → PENDING
        │
        ▼
EventQueue.update() fires _on_event_activated
        │
        ▼
LeagueState._handle_event_activated()
        ├──► Check auto-pause
        ├──► Add to ticker if HIGH+ priority
        └──► Notify WebSocket
        │
        ▼
Player interaction:
        ├──► attend() → IN_PROGRESS → ATTENDED
        ├──► dismiss() → DISMISSED (if can_dismiss)
        └──► (deadline) → EXPIRED
        │
        ▼
EventQueue.clear_completed() removes terminal events
```

---

## Integration Points

### With Core League

```python
# ManagementService holds reference to core League
self.league: League

# Builds schedule from league data
schedule = [
    ScheduledGame(
        week=game.week,
        opponent_id=game.opponent.id,
        opponent_name=game.opponent.name,
        ...
    )
    for game in league.schedule.get_team_games(team_id)
]

# Gets free agents
free_agents = [
    FreeAgentInfo(
        player_id=player.id,
        name=player.name,
        ...
    )
    for player in league.free_agents
]

# References teams
team = league.teams[team_id]

# Accesses player data
player = league.get_player(player_id)
```

### With Core Models

```python
# Events reference UUIDs
event.player_ids: List[UUID]
event.team_id: UUID
event.staff_ids: List[UUID]

# Payloads contain game-specific data
event.payload = {
    "opponent_name": "Eagles",
    "week": 5,
    "is_home": True,
    ...
}

# Practice effects apply to core objects
for player in team.roster:
    player.playbook_mastery[play_id] += improvement
    player.attributes.speed += development_gain
```

### With Simulation

```python
# Game simulation
from huddle.simulation import SeasonSimulator

def sim_game(self, event_id: str) -> GameResult:
    event = self.events.get(event_id)
    game = self._get_game_from_event(event)

    simulator = SeasonSimulator()
    result = simulator.simulate_game(
        home_team=game.home_team,
        away_team=game.away_team
    )

    return result
```

### With Admin/Auth

```python
# Create franchise requires active league
@router.post("/franchise")
async def create_franchise(
    request: CreateFranchiseRequest,
    league: League = Depends(get_active_league)  # From /admin/league/generate
):
    state = LeagueState(
        id=uuid4(),
        player_team_id=request.team_id,
        calendar=LeagueCalendar.new_season(request.year, request.phase),
        ...
    )

    session = await session_manager.create_session(
        franchise_id=state.id,
        state=state,
        league=league
    )

    return {"franchise_id": state.id}
```

---

## Design Patterns

### 1. State as Single Source of Truth

All game state lives in the `LeagueState` dataclass. Services provide view operations and delegate mutations to state methods. This enables:
- Serialization via `to_dict()`/`from_dict()`
- State snapshots for debugging
- Clean separation between API and logic

### 2. Callback-Driven Architecture

Events propagate through callbacks:

```python
# Calendar fires phase changes
calendar.on_phase(lambda old, new: update_available_tabs(new))

# Events fire activation
events.on_activation(lambda e: check_auto_pause(e))

# State fires pause
state.on_pause(lambda reason: send_ws_notification(reason))
```

This decouples systems while allowing coordination.

### 3. Event Arc System

Related events link via `arc_id`:

```python
# Initial contract expiring event
event1 = create_contract_event(...)
event1.arc_id = "player_123_contract"

# Follow-up holdout event
event1.triggers.append(EventTrigger(
    condition=TriggerCondition.ON_EXPIRE,
    spawn_event_type="player_holdout",
    delay_days=7,
    probability=0.3,
    arc_id="player_123_contract"
))
```

This creates coherent storylines.

### 4. Auto-Pause Logic

Intelligent pausing prevents missing important moments:

- **CRITICAL**: Pause unconditionally
- **Team-specific**: Only pause for player's team
- **HIGH**: Slow time instead of pause
- **Background**: No interruption

### 5. Clipboard Navigation Stack

Breadcrumb-like navigation:

```python
context = PanelContext(PanelType.ROSTER_LIST)
context = context.with_player(player_id)  # preserves previous
context = context.with_player(other_id)   # stacks
context.go_back()  # returns to previous
```

### 6. Async Tick Loop

WebSocket-optional continuous simulation:

```python
async def _tick_loop(self):
    while self._running:
        try:
            elapsed = time.monotonic() - self._last_tick
            self._last_tick = time.monotonic()

            minutes = self.state.tick(elapsed)

            if minutes > 0 and self._websocket:
                await self._send_calendar_update()

        except Exception as e:
            logger.error(f"Tick error: {e}")
            await asyncio.sleep(1)  # Back off

        await asyncio.sleep(0.05)  # 20 ticks/second max
```

### 7. Layered Serialization

Clean separation:

```
Management Objects → Pydantic Schemas → JSON
     ↓                    ↓               ↓
LeagueState       CalendarStateResponse  API Response
ManagementEvent   ManagementEventResponse
EventQueue        EventQueueResponse
```

Both directions supported for persistence and API.

---

## Core Infrastructure Extensions

**Added:** 2024-12 | **Status:** Active

These modules integrate new infrastructure (Contract, TransactionLog, DraftPickInventory) with existing core models (Player, Team, League).

### Contract Integration Module

**File:** `huddle/core/contracts/integration.py`

Bridges legacy player contract fields with the new `Contract` class system. Use these functions instead of directly manipulating contract fields.

#### Key Functions

| Function | Purpose |
|----------|---------|
| `sync_contract_to_player()` | Sync Contract object to legacy fields |
| `assign_contract_with_sync()` | Assign contract (recommended entry point) |
| `assign_rookie_contract_with_sync()` | Assign rookie contract by draft position |
| `advance_contract_year()` | Advance contract by one year |
| `clear_contract()` | Clear contract for release/FA (returns dead money) |
| `restructure_contract()` | Convert salary to bonus (returns cap savings) |
| `get_contract_summary()` | Get display-ready contract info |
| `upgrade_roster_contracts()` | Migrate legacy fields to Contract objects |
| `create_contract_from_legacy()` | Create Contract from legacy fields |

#### Usage Examples

```python
from huddle.core.contracts import assign_contract_with_sync
from datetime import date

# Assign a contract with market value calculation
contract = assign_contract_with_sync(
    player=player,
    team_id=str(team.id),
    years=3,
    salary=5000,
    signing_bonus=2000,
    signed_date=date(2024, 3, 15),
)
# Both player.contract AND legacy fields (salary, contract_years, etc.) are set

# Assign rookie contract
from huddle.core.contracts import assign_rookie_contract_with_sync

contract = assign_rookie_contract_with_sync(
    player=rookie,
    team_id=str(team.id),
    pick_number=15,
    signed_date=date(2024, 5, 10),
)

# Release player (get dead money)
from huddle.core.contracts import clear_contract

dead_money = clear_contract(player)  # Clears both Contract and legacy fields
```

#### Legacy Field Sync

When a Contract is assigned, these legacy Player fields are updated:

| Legacy Field | Source from Contract |
|--------------|---------------------|
| `contract_years` | `contract.total_years` |
| `contract_year_remaining` | `contract.years_remaining` |
| `salary` | `contract.current_year_data().base_salary` |
| `signing_bonus` | `contract.signing_bonus` |
| `signing_bonus_remaining` | Calculated proration |

---

### TransactionLog

**File:** `huddle/core/transactions/transaction_log.py`

Records all roster moves, trades, signings, and player movements. Provides audit trail for all team/player changes.

#### Transaction Types

```python
class TransactionType(Enum):
    # Draft
    DRAFT_SELECTION      # Player selected
    DRAFT_TRADE          # Trade during draft

    # Free Agency
    FA_SIGNING           # Free agent signed
    EXTENSION            # Contract extension
    RESTRUCTURE          # Contract restructure

    # Roster Moves
    CUT                  # Player released
    CUT_JUNE1            # June 1 cut (split dead money)
    WAIVER_CLAIM         # Claimed off waivers

    # Practice Squad
    PS_SIGN, PS_ELEVATE, PS_RELEASE, PS_PROTECT

    # Injured Reserve
    IR_PLACE, IR_RETURN, IR_DESIGNATE_RETURN

    # PUP/NFI
    PUP_PLACE, PUP_ACTIVATE, NFI_PLACE, NFI_ACTIVATE

    # Trades
    TRADE

    # Tags
    FRANCHISE_TAG, TRANSITION_TAG, TAG_REMOVE

    # Other
    RETIREMENT, SUSPENSION, RESERVE_LIST
```

#### Transaction Class

```python
@dataclass
class Transaction:
    transaction_id: str           # Unique ID
    transaction_type: TransactionType
    transaction_date: date
    season: int
    week: int                     # 0=offseason, 1-18=regular, 19+=playoffs

    # Primary party
    team_id: str
    team_name: str
    player_id: Optional[str]
    player_name: Optional[str]

    # For trades
    other_team_id: Optional[str]
    assets_sent: list[TradeAsset]
    assets_received: list[TradeAsset]

    # Contract details
    contract_years: Optional[int]
    contract_total_value: Optional[int]
    contract_guaranteed: Optional[int]

    # Cap implications
    cap_hit: int
    dead_money: int
    cap_savings: int

    def get_headline(self) -> str:
        """Generate news headline for this transaction."""
```

#### TransactionLog Class

```python
@dataclass
class TransactionLog:
    league_id: str
    transactions: list[Transaction]

    # Query methods
    def add(transaction: Transaction) -> None
    def get_by_team(team_id: str, season: int = None) -> list[Transaction]
    def get_by_player(player_id: str) -> list[Transaction]
    def get_by_type(transaction_type: TransactionType, season: int = None) -> list
    def get_by_date_range(start: date, end: date) -> list[Transaction]
    def get_by_season(season: int) -> list[Transaction]
    def get_recent(count: int = 10) -> list[Transaction]

    # Convenience methods
    def get_trades(season: int = None) -> list[Transaction]
    def get_signings(season: int = None) -> list[Transaction]
    def get_cuts(season: int = None) -> list[Transaction]
    def get_draft_selections(year: int) -> list[Transaction]

    # Calculations
    def calculate_team_dead_money(team_id: str, season: int) -> int
```

#### Factory Functions

```python
# Create specific transaction types
create_draft_transaction(team_id, player_id, pick_number, ...)
create_signing_transaction(team_id, player_id, contract_years, contract_value, ...)
create_cut_transaction(team_id, player_id, dead_money, cap_savings, is_june1=False, ...)
create_trade_transaction(team_id, other_team_id, assets_sent, assets_received, ...)
create_ir_transaction(team_id, player_id, injury_type, is_return=False, ...)
```

---

### DraftPickInventory

**File:** `huddle/core/draft/picks.py`

Tracks draft pick ownership, conditions, protections, and trade value.

#### DraftPick Class

```python
@dataclass
class DraftPick:
    pick_id: str
    year: int                           # Draft year
    round: int                          # Round (1-7)

    # Ownership
    original_team_id: str               # Team that originally held pick
    current_team_id: str                # Current owner

    # Conditions
    protection: PickProtection          # TOP_1, TOP_3, TOP_10, etc.
    protection_converts_to: Optional[str]  # "2026 2nd" if protected

    # After draft
    pick_number: Optional[int]          # Actual overall pick (1-224)
    player_selected_id: Optional[str]

    # Trade tracking
    times_traded: int
    trade_history: list[str]            # Transaction IDs
    is_compensatory: bool

    # Properties
    is_owned_by_original: bool
    is_conditional: bool
    estimated_value: int                # Jimmy Johnson chart

    def check_protection(actual_pick: int) -> bool:
        """True if pick conveys (protection NOT triggered)."""
```

#### PickProtection Enum

```python
class PickProtection(Enum):
    NONE = auto()       # Unprotected
    TOP_1 = auto()      # Top 1 protected
    TOP_3 = auto()      # Top 3 protected
    TOP_5 = auto()      # Top 5 protected
    TOP_10 = auto()     # Top 10 protected
    TOP_15 = auto()     # Top 15 protected
    TOP_20 = auto()     # Top 20 protected
    LOTTERY = auto()    # Top 14 protected
```

#### DraftPickInventory Class

```python
@dataclass
class DraftPickInventory:
    team_id: str
    picks: list[DraftPick]

    # Query methods
    def get_picks_for_year(year: int) -> list[DraftPick]
    def get_picks_by_round(year: int, round_num: int) -> list[DraftPick]
    def get_own_picks(year: int) -> list[DraftPick]        # Originally this team's
    def get_acquired_picks(year: int) -> list[DraftPick]   # From trades
    def get_traded_away_picks(year: int) -> list[DraftPick]

    # Calculations
    def total_value_for_year(year: int) -> int
    def has_first_round_pick(year: int) -> bool
    def count_picks(year: int) -> int
    def can_trade_pick(pick: DraftPick) -> bool

    # Mutations
    def add_pick(pick: DraftPick) -> None
    def remove_pick(pick_id: str) -> Optional[DraftPick]
    def transfer_pick(pick_id: str, to_team_id: str, transaction_id: str) -> bool
```

#### Jimmy Johnson Trade Value Chart

Pick values for trade evaluation (classic chart):

| Pick | Value | Pick | Value | Pick | Value |
|------|-------|------|-------|------|-------|
| 1 | 3000 | 11 | 1250 | 21 | 800 |
| 2 | 2600 | 12 | 1200 | 22 | 780 |
| 3 | 2200 | 13 | 1150 | 23 | 760 |
| 4 | 1800 | 14 | 1100 | 24 | 740 |
| 5 | 1700 | 15 | 1050 | 25 | 720 |
| ... | ... | ... | ... | ... | ... |

```python
from huddle.core.draft.picks import get_pick_value

value = get_pick_value(15)  # Returns 1050
```

#### Factory Functions

```python
# Create initial picks for a team (3 years ahead, 7 rounds)
inventory = create_initial_picks_for_team(
    team_id="team_123",
    start_year=2024,
    years_ahead=3,
    rounds=7
)

# Create for entire league
inventories = create_league_draft_picks(
    team_ids=["team_1", "team_2", ...],
    start_year=2024,
    years_ahead=3
)
```

---

### Model Field Additions

These fields were added to core models to integrate the new infrastructure:

#### Player Model (`huddle/core/models/player.py`)

```python
# New field (line 82)
contract: Optional[Contract] = None

# New properties (lines 143-174)
@property
def current_salary(self) -> int: ...
@property
def cap_hit(self) -> int: ...
@property
def dead_money(self) -> int: ...
@property
def is_contract_expiring(self) -> bool: ...
```

**Note:** Legacy fields (`salary`, `contract_years`, `contract_year_remaining`, `signing_bonus`, `signing_bonus_remaining`) are preserved for backward compatibility. New code should use the `Contract` object.

#### Team Model (`huddle/core/models/team.py`)

```python
# New fields (lines 292-295)
draft_picks: Optional[DraftPickInventory] = None
status: Optional[TeamStatusState] = None

# New properties (lines 371-401)
@property
def is_contending(self) -> bool: ...
@property
def is_rebuilding(self) -> bool: ...

def get_owned_picks(self) -> list[DraftPick]: ...
def get_traded_picks(self) -> list[DraftPick]: ...
```

#### League Model (`huddle/core/league/league.py`)

```python
# New fields (lines 246-252)
transactions: Optional[TransactionLog] = None
calendar: Optional[DayCalendar] = None
draft_picks: Optional[DraftPickInventory] = None

# New method (lines 916-983)
def initialize_new_systems(self, year: int) -> None:
    """Initialize transactions, calendar, and draft picks for all teams."""

# Updated methods (lines 872-906)
@property
def is_offseason(self) -> bool: ...    # Now uses calendar if available
@property
def is_regular_season(self) -> bool: ...
@property
def is_playoffs(self) -> bool: ...

# New convenience methods (lines 913-934)
@property
def current_date_display(self) -> str: ...
@property
def current_period_display(self) -> str: ...

def log_transaction(self, transaction: Transaction) -> None: ...
```

---

### Calendar Deprecation Notice

**File:** `huddle/management/calendar.py`

The minute-based `LeagueCalendar` in `huddle/management/calendar.py` is **deprecated** in favor of the day-based `DayCalendar` in `huddle/core/calendar/league_calendar.py`.

| Old (Deprecated) | New (Preferred) |
|------------------|-----------------|
| `huddle/management/calendar.py` | `huddle/core/calendar/league_calendar.py` |
| Minute-based progression | Day-based progression |
| `LeagueCalendar` | `DayCalendar` |

The old calendar still works but new code should use `DayCalendar` via `League.calendar`.

---

### Usage: Initialize New Systems

```python
from huddle.core.league.league import League

# Create or load league
league = League(current_season=2024)

# Initialize new infrastructure (creates transactions, calendar, picks)
league.initialize_new_systems(2024)

# Now available:
# - league.transactions (TransactionLog)
# - league.calendar (DayCalendar)
# - league.draft_picks (all picks across all teams)
# - team.draft_picks (picks for each team)
```
