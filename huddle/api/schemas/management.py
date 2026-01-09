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
    TEAM = "TEAM"
    PLAYER = "PLAYER"
    SCOUTING = "SCOUTING"
    DRAFT = "DRAFT"
    STAFF = "STAFF"
    MEDIA = "MEDIA"
    INJURY = "INJURY"
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


class DisplayModeSchema(str, Enum):
    """Display mode for events."""
    PANE = "PANE"
    MODAL = "MODAL"
    TICKER = "TICKER"


class ManagementEventResponse(BaseModel):
    """Management event response."""
    id: UUID
    event_type: str
    category: EventCategorySchema
    priority: EventPrioritySchema
    title: str
    description: str
    icon: str
    display_mode: DisplayModeSchema = DisplayModeSchema.PANE
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None
    scheduled_week: Optional[int] = None
    scheduled_day: Optional[int] = None
    arc_id: Optional[UUID] = None
    status: EventStatusSchema
    auto_pause: bool
    requires_attention: bool
    can_dismiss: bool
    can_delegate: bool
    team_id: Optional[UUID] = None
    player_ids: list[UUID] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    is_urgent: bool


class DayAdvanceResponse(BaseModel):
    """Response from advancing a day."""
    calendar: "CalendarStateResponse"
    day_events: list[ManagementEventResponse]
    event_count: int


class EventQueueResponse(BaseModel):
    """Event queue response."""
    pending: list[ManagementEventResponse]
    upcoming: list[ManagementEventResponse] = []  # Scheduled future events
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
    id: UUID  # Franchise ID
    league_id: UUID  # Core league ID (for portrait API)
    player_team_id: Optional[UUID] = None
    calendar: CalendarStateResponse
    events: EventQueueResponse
    clipboard: ClipboardStateResponse
    ticker: TickerFeedResponse


class FranchiseCreatedResponse(BaseModel):
    """Response after creating a franchise."""
    franchise_id: UUID
    message: str


# === Financial/Contract Schemas ===

class TeamFinancialsResponse(BaseModel):
    """Team salary cap and financial state."""
    team_abbr: str
    salary_cap: int  # In thousands (255000 = $255M)
    total_salary: int
    dead_money: int
    dead_money_next_year: int
    cap_room: int
    cap_used_pct: float


class PlayerContractInfo(BaseModel):
    """Individual player contract details."""
    player_id: str
    name: str
    position: str
    overall: int
    age: int
    salary: int
    signing_bonus: int
    years_total: int
    years_remaining: int
    dead_money_if_cut: int


class ContractsResponse(BaseModel):
    """All player contracts for a team."""
    team_abbr: str
    total_salary: int
    contracts: list[PlayerContractInfo]


# === Contract Actions ===

class RestructureContractRequest(BaseModel):
    """Request to restructure a player's contract."""
    amount_to_convert: int = Field(..., gt=0, description="Salary amount to convert to signing bonus")


class RestructureContractResponse(BaseModel):
    """Result of a contract restructure."""
    success: bool
    player_id: str
    player_name: str
    amount_converted: int
    cap_savings: int
    new_base_salary: int
    new_signing_bonus: int
    restructure_count: int


class CutPlayerRequest(BaseModel):
    """Request to cut a player."""
    june_1_designation: bool = Field(default=False, description="Use June 1 cut designation to split dead money")


class CutPlayerResponse(BaseModel):
    """Result of cutting a player."""
    success: bool
    player_id: str
    player_name: str
    dead_money_this_year: int
    dead_money_next_year: int  # Only applies to June 1 cut
    cap_savings: int
    was_june_1: bool


# === Detailed Contract Info ===

class ContractYearInfo(BaseModel):
    """Single year of a contract."""
    year: int
    base_salary: int
    signing_bonus_proration: int
    roster_bonus: int
    incentives: int
    cap_hit: int
    guaranteed_salary: int
    is_current: bool = False


class ContractDetailInfo(BaseModel):
    """Full contract details for a player."""
    player_id: str
    name: str
    position: str
    overall: int
    age: int
    experience: int
    # Contract summary
    total_value: int
    total_guaranteed: int
    signing_bonus: int
    years_total: int
    years_remaining: int
    current_year: int
    # Year-by-year breakdown
    years: list[ContractYearInfo]
    # Dead money scenarios
    dead_money_if_cut: int
    dead_money_june1_this_year: int
    dead_money_june1_next_year: int
    cap_savings_if_cut: int
    # Flags
    is_restructured: bool
    restructure_count: int
    can_restructure: bool


class FreeAgentInfo(BaseModel):
    """Free agent listing with market evaluation."""
    player_id: str
    name: str
    position: str
    overall: int
    age: int
    tier: str  # ELITE, STARTER, DEPTH, MINIMUM
    market_value: int


class FreeAgentsResponse(BaseModel):
    """Available free agents."""
    count: int
    free_agents: list[FreeAgentInfo]


# === Draft/Prospect Schemas ===

class CombineMeasurables(BaseModel):
    """Combine workout measurables (factual, not opinions)."""
    forty_yard_dash: Optional[float] = None  # e.g., 4.42
    forty_percentile: Optional[int] = None   # 0-100, within position group
    bench_press_reps: Optional[int] = None   # 225lb reps
    bench_percentile: Optional[int] = None   # 0-100, within position group
    vertical_jump: Optional[float] = None    # inches
    vertical_percentile: Optional[int] = None  # 0-100, within position group
    broad_jump: Optional[int] = None         # inches
    broad_percentile: Optional[int] = None   # 0-100, within position group


class ScoutEstimate(BaseModel):
    """Scout's estimate of an attribute with uncertainty."""
    name: str
    projected_value: int
    accuracy: str  # LOW, MEDIUM, HIGH, EXACT
    min_estimate: int
    max_estimate: int
    grade: str  # A+, A, A-, B+, etc.


class ProspectInfo(BaseModel):
    """Draft prospect with scouting data."""
    player_id: str
    name: str
    position: str
    college: Optional[str] = None
    age: int
    height: str  # e.g., "6'2\""
    weight: int

    # Scouting progress
    scouted_percentage: int  # 0-100
    interviewed: bool
    private_workout: bool

    # Measurables (factual)
    combine: CombineMeasurables

    # Scout estimates (opinions with uncertainty)
    scout_estimates: list[ScoutEstimate]
    overall_projection: int  # Scout's projected OVR

    # Draft projection
    projected_round: Optional[int] = None


class DraftProspectsResponse(BaseModel):
    """Draft class with scouting data."""
    count: int
    prospects: list[ProspectInfo]


# === Drawer Schemas ===

class DrawerItemType(str, Enum):
    """Types of items that can be stored in the drawer."""
    PLAYER = "player"
    PROSPECT = "prospect"
    NEWS = "news"
    GAME = "game"


class DrawerItem(BaseModel):
    """A reference/pointer stored in the drawer."""
    id: str  # Unique drawer item ID
    type: DrawerItemType
    ref_id: str  # ID of the referenced entity (player_id, news_id, etc.)
    note: Optional[str] = None
    archived_at: datetime


class DrawerItemResponse(BaseModel):
    """Drawer item with resolved display data."""
    id: str
    type: DrawerItemType
    ref_id: str
    note: Optional[str] = None
    archived_at: datetime
    # Resolved display fields (populated from the referenced entity)
    title: str
    subtitle: Optional[str] = None


class DrawerResponse(BaseModel):
    """Full drawer contents."""
    items: list[DrawerItemResponse]
    count: int


class AddDrawerItemRequest(BaseModel):
    """Request to add an item to the drawer."""
    type: DrawerItemType
    ref_id: str
    note: Optional[str] = None


class UpdateDrawerItemRequest(BaseModel):
    """Request to update a drawer item's note."""
    note: Optional[str] = None


# === Week Journal Schemas ===


class JournalCategory(str, Enum):
    """Categories for journal entries."""
    PRACTICE = "practice"
    CONVERSATION = "conversation"
    INTEL = "intel"
    INJURY = "injury"
    TRANSACTION = "transaction"


class JournalEntry(BaseModel):
    """A single entry in the week journal."""
    id: str
    day: int  # 0-6 (Mon-Sun)
    category: JournalCategory
    title: str  # "Pass Rush Drills", "J. Smith", "KC Run Defense"
    effect: str  # "+2 Pass Rush", "Confident → Content", "Weak inside"
    detail: Optional[str] = None  # "Wed focus", "Extension talk", "Scout report"


class WeekJournal(BaseModel):
    """Journal of accumulated effects for the current week."""
    week: int
    entries: list[JournalEntry]


class AddJournalEntryRequest(BaseModel):
    """Request to add a journal entry."""
    category: JournalCategory
    title: str
    effect: str
    detail: Optional[str] = None
    player: Optional[dict] = None


# === Practice Execution Schemas ===


class RunPracticeRequest(BaseModel):
    """Request to run a practice session."""
    event_id: UUID
    playbook: int = 34  # Percentage for playbook learning
    development: int = 33  # Percentage for player development
    game_prep: int = 33  # Percentage for game preparation
    intensity: str = "normal"  # light, normal, intense (for future use)


class PlaybookPracticeStats(BaseModel):
    """Stats from playbook practice."""
    players_practiced: int = 0
    total_reps_given: int = 0
    tier_advancements: int = 0  # Players who advanced a mastery level
    plays_practiced: int = 0


class DevelopmentPracticeStats(BaseModel):
    """Stats from development practice."""
    players_developed: int = 0
    total_points_gained: float = 0.0
    attributes_improved: dict[str, float] = {}  # {attr_name: total_points}


class GamePrepStats(BaseModel):
    """Stats from game preparation."""
    opponent: Optional[str] = None
    prep_level: float = 0.0  # 0-100% prep level
    scheme_bonus: float = 0.0
    execution_bonus: float = 0.0


class PracticeResultsResponse(BaseModel):
    """Response with practice execution results."""
    success: bool
    error: Optional[str] = None
    duration_minutes: int = 0
    playbook_stats: PlaybookPracticeStats = PlaybookPracticeStats()
    development_stats: DevelopmentPracticeStats = DevelopmentPracticeStats()
    game_prep_stats: GamePrepStats = GamePrepStats()


# === Playbook Mastery Schemas ===


class MasteryLevelSchema(str, Enum):
    """Play mastery level."""
    UNLEARNED = "unlearned"
    LEARNED = "learned"
    MASTERED = "mastered"


class PlayMasteryInfo(BaseModel):
    """Mastery info for a single play."""
    play_id: str
    play_name: str
    status: MasteryLevelSchema
    progress: float  # 0.0-1.0 within current tier
    reps: int


class PlayerPlaybookMastery(BaseModel):
    """Playbook mastery for a single player."""
    player_id: str
    name: str
    position: str
    plays: list[PlayMasteryInfo]
    learned_count: int
    mastered_count: int
    total_plays: int


class PlaybookMasteryResponse(BaseModel):
    """Team playbook mastery response."""
    team_abbr: str
    players: list[PlayerPlaybookMastery]


# === Development/Potential Schemas ===


class AttributePotential(BaseModel):
    """Per-attribute potential info."""
    name: str
    current: int
    potential: int
    growth_room: int  # potential - current


class PlayerDevelopmentInfo(BaseModel):
    """Development info for a player."""
    player_id: str
    name: str
    position: str
    overall: int
    overall_potential: int
    potentials: list[AttributePotential]


class DevelopmentResponse(BaseModel):
    """Team development overview."""
    team_abbr: str
    players: list[PlayerDevelopmentInfo]


# === Weekly Development Schemas ===


class PlayerWeeklyGain(BaseModel):
    """A player's accumulated development gains for the week."""
    player_id: str
    name: str
    position: str
    gains: dict[str, float]  # {attr_name: points_gained}


class WeeklyDevelopmentResponse(BaseModel):
    """Weekly development gains for display in Growth tab."""
    week: int
    players: list[PlayerWeeklyGain]


# === Game Simulation Schemas ===


class SimGameRequest(BaseModel):
    """Request to simulate a game."""
    event_id: UUID


class GameStatsResponse(BaseModel):
    """Game stats for display."""
    passing_yards: int = 0
    rushing_yards: int = 0
    total_yards: int = 0
    turnovers: int = 0
    time_of_possession: str = "30:00"
    third_down_pct: float = 0.0
    sacks: int = 0


class GameResultResponse(BaseModel):
    """Response from simulating a game."""
    success: bool
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    won: bool
    is_home: bool
    week: int
    user_stats: GameStatsResponse
    opponent_stats: GameStatsResponse
    mvp: Optional[dict] = None  # {player_id, name, position, stat_line}


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
    RUN_PRACTICE = "run_practice"
    PLAY_GAME = "play_game"
    SIM_GAME = "sim_game"
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
    def calendar_update(
        cls,
        calendar: CalendarStateResponse,
        events: Optional[list["ManagementEventResponse"]] = None,
    ) -> "ManagementWSMessage":
        """Create a calendar update message, optionally including events."""
        payload = calendar.model_dump(mode="json")
        if events is not None:
            payload["events"] = [e.model_dump(mode="json") for e in events]
        return cls(
            type=ManagementWSMessageType.CALENDAR_UPDATE,
            payload=payload,
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


# === Draft Board Schemas ===


class BoardEntryResponse(BaseModel):
    """A single prospect on the user's draft board."""
    prospect_id: str
    rank: int  # 1-based position on board
    tier: int  # 1=Elite, 2=Great, 3=Good, 4=Solid, 5=Flier
    notes: str = ""
    # Resolved prospect info
    name: str
    position: str
    college: Optional[str] = None
    overall: int


class DraftBoardResponse(BaseModel):
    """User's complete draft board."""
    entries: list[BoardEntryResponse]
    count: int


class AddToBoardRequest(BaseModel):
    """Request to add a prospect to the draft board."""
    prospect_id: str
    tier: int = 3  # Default to "Good"


class UpdateBoardEntryRequest(BaseModel):
    """Request to update a board entry."""
    tier: Optional[int] = None
    notes: Optional[str] = None


class ReorderBoardRequest(BaseModel):
    """Request to reorder a prospect on the board."""
    new_rank: int  # New 1-based position


# === Negotiation Schemas ===


class NegotiationResultSchema(str, Enum):
    """Outcome of a negotiation round."""
    ACCEPTED = "ACCEPTED"
    COUNTER_OFFER = "COUNTER_OFFER"
    REJECTED = "REJECTED"
    WALK_AWAY = "WALK_AWAY"


class NegotiationToneSchema(str, Enum):
    """Tone of the player/agent response."""
    ENTHUSIASTIC = "ENTHUSIASTIC"
    PROFESSIONAL = "PROFESSIONAL"
    DEMANDING = "DEMANDING"
    INSULTED = "INSULTED"


class ContractOfferSchema(BaseModel):
    """A contract offer in negotiation."""
    years: int
    salary: int  # Annual salary in thousands
    signing_bonus: int  # Total signing bonus in thousands
    total_value: int  # Computed total
    guaranteed: int  # Computed guaranteed money


class MarketValueSchema(BaseModel):
    """Player's market value reference."""
    base_salary: int
    signing_bonus: int
    years: int
    total_value: int
    tier: str  # ELITE, STARTER, DEPTH, MINIMUM


class StartNegotiationRequest(BaseModel):
    """Request to start negotiation with a free agent."""
    player_id: str


class StartNegotiationResponse(BaseModel):
    """Response when starting a negotiation."""
    negotiation_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    player_age: int
    market_value: MarketValueSchema
    opening_demand: ContractOfferSchema
    message: str


class SubmitOfferRequest(BaseModel):
    """Request to submit a contract offer."""
    years: int = Field(ge=1, le=7)
    salary: int = Field(ge=0)  # Annual salary in thousands
    signing_bonus: int = Field(ge=0)  # Total signing bonus in thousands


class SubmitOfferResponse(BaseModel):
    """Response after submitting an offer."""
    result: NegotiationResultSchema
    tone: NegotiationToneSchema
    message: str
    offer_pct_of_market: float
    walk_away_chance: float = 0.0
    counter_offer: Optional[ContractOfferSchema] = None
    # If accepted
    agreed_contract: Optional[ContractOfferSchema] = None
    # Negotiation tracking
    rounds: int
    patience: float  # 0-1, low = may walk away


class ActiveNegotiationInfo(BaseModel):
    """Summary of an active negotiation."""
    negotiation_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    rounds: int
    last_offer: Optional[ContractOfferSchema] = None
    current_demand: Optional[ContractOfferSchema] = None
    patience: float


class ActiveNegotiationsResponse(BaseModel):
    """List of active negotiations."""
    negotiations: list[ActiveNegotiationInfo]
    count: int


# === Free Agency Auction Schemas ===


class AuctionPhaseSchema(str, Enum):
    """Phase of the auction process."""
    BIDDING = "BIDDING"         # Teams placing bids
    FINAL_CALL = "FINAL_CALL"   # Last chance to bid
    CLOSED = "CLOSED"           # Auction complete


class AuctionResultSchema(str, Enum):
    """Result of an auction for the user."""
    WON = "WON"                 # User won the auction
    OUTBID = "OUTBID"           # User was outbid
    WITHDREW = "WITHDREW"       # User withdrew from auction
    NO_BID = "NO_BID"           # User never bid


class CompetingTeamBid(BaseModel):
    """A competing team's bid in the auction."""
    team_id: str
    team_name: str
    team_abbrev: str
    interest_level: str  # HIGH, MEDIUM, LOW
    has_bid: bool
    is_top_bid: bool
    # Obscured bid info (AI teams don't reveal exact amounts)
    bid_range: Optional[str] = None  # e.g., "$12M-$15M/yr"


class AuctionBidSchema(BaseModel):
    """A bid in the auction."""
    years: int
    salary: int  # Annual salary in thousands
    signing_bonus: int  # Signing bonus in thousands
    total_value: int
    guaranteed: int


class StartAuctionRequest(BaseModel):
    """Request to start an auction for an elite free agent."""
    player_id: str


class StartAuctionResponse(BaseModel):
    """Response when starting an auction."""
    auction_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    player_age: int
    market_value: MarketValueSchema
    # Auction state
    phase: AuctionPhaseSchema
    round: int
    max_rounds: int
    competing_teams: list[CompetingTeamBid]
    # Minimum acceptable bid
    floor_bid: AuctionBidSchema
    message: str


class SubmitAuctionBidRequest(BaseModel):
    """Request to submit a bid in the auction."""
    years: int = Field(ge=1, le=7)
    salary: int = Field(ge=0)
    signing_bonus: int = Field(ge=0)


class SubmitAuctionBidResponse(BaseModel):
    """Response after submitting a bid."""
    success: bool
    message: str
    # Updated auction state
    phase: AuctionPhaseSchema
    round: int
    your_bid: Optional[AuctionBidSchema] = None
    is_top_bid: bool
    competing_teams: list[CompetingTeamBid]
    # If outbid, show what you need to beat
    top_bid_range: Optional[str] = None  # e.g., "$15M-$18M/yr"


class FinalizeAuctionRequest(BaseModel):
    """Request to finalize/advance the auction."""
    pass  # No parameters needed


class FinalizeAuctionResponse(BaseModel):
    """Response when auction is finalized."""
    result: AuctionResultSchema
    message: str
    # If won
    winning_bid: Optional[AuctionBidSchema] = None
    # If lost
    winning_team: Optional[str] = None
    winning_team_abbrev: Optional[str] = None


class ActiveAuctionInfo(BaseModel):
    """Summary of an active auction."""
    auction_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    phase: AuctionPhaseSchema
    round: int
    max_rounds: int
    your_bid: Optional[AuctionBidSchema] = None
    is_top_bid: bool
    competing_teams_count: int


class ActiveAuctionsResponse(BaseModel):
    """List of active auctions."""
    auctions: list[ActiveAuctionInfo]
    count: int
