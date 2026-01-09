"""
Management Event System.

This module handles the events that populate the clipboard and drive
the management game loop. Events spawn based on calendar triggers
(free agents available, practices, games, etc.) and require player attention.

Events have priority, deadlines, and lifecycle states.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Optional
from uuid import UUID, uuid4


class EventCategory(Enum):
    """Categories for grouping and filtering events."""

    # Personnel
    FREE_AGENCY = auto()  # Free agent signings
    TRADE = auto()  # Trade offers and negotiations
    CONTRACT = auto()  # Contract extensions, holdouts
    ROSTER = auto()  # Roster moves, cuts, claims

    # Team Operations
    PRACTICE = auto()  # Team practices
    MEETING = auto()  # Staff meetings, player meetings
    GAME = auto()  # Game day events
    TEAM = auto()  # General team operations
    PLAYER = auto()  # Player-related events (morale, meetings)

    # Draft
    SCOUTING = auto()  # Scouting events, workouts
    DRAFT = auto()  # Draft day events

    # Staff
    STAFF = auto()  # Staff hiring, firing, meetings

    # Media & Communication
    MEDIA = auto()  # Press conferences, interviews

    # Health
    INJURY = auto()  # Injury reports and updates

    # Administrative
    DEADLINE = auto()  # Important deadlines
    SYSTEM = auto()  # System/tutorial events


class EventPriority(Enum):
    """
    Event priority levels.

    Higher priority events appear first and may trigger auto-pause.
    """

    CRITICAL = 1  # Must attend - auto-pauses game (e.g., your game starting)
    HIGH = 2  # Important - appears prominently (e.g., top FA available)
    NORMAL = 3  # Standard events (e.g., practice scheduled)
    LOW = 4  # Optional/informational (e.g., minor roster move available)
    BACKGROUND = 5  # Passive events that don't need attention


class EventStatus(Enum):
    """Lifecycle status of an event."""

    SCHEDULED = auto()  # Future event, not yet active
    PENDING = auto()  # Active, awaiting player attention
    IN_PROGRESS = auto()  # Currently being attended to
    ATTENDED = auto()  # Player has dealt with this event
    EXPIRED = auto()  # Deadline passed without action
    DISMISSED = auto()  # Player explicitly dismissed
    AUTO_RESOLVED = auto()  # System handled it (e.g., AI made the decision)


class DisplayMode(Enum):
    """How the event should be displayed in the UI."""

    PANE = auto()      # Opens as workspace pane (most events)
    MODAL = auto()     # Opens as blocking modal (critical decisions)
    TICKER = auto()    # Just shows in ticker (informational only)


class TriggerCondition(Enum):
    """When an event trigger should fire."""

    ON_COMPLETE = auto()   # When event is attended/completed
    ON_DISMISS = auto()    # When event is dismissed
    ON_EXPIRE = auto()     # When event expires without action
    ON_CHOICE = auto()     # When a specific choice is made (uses payload.choice_id)


@dataclass
class EventTrigger:
    """
    Defines a follow-up event that can spawn when this event resolves.

    Used for event arcs - e.g., player requests extension → negotiations start,
    or trade rejected → rival makes bigger offer next week.
    """

    condition: TriggerCondition
    spawn_event_type: str  # Type of event to spawn (matches factory function)
    delay_days: int = 0    # Days after trigger to schedule spawned event
    delay_hours: int = 0   # Hours after trigger
    probability: float = 1.0  # Chance this trigger fires (0.0 - 1.0)

    # Filter for ON_CHOICE - only fires if this choice was selected
    choice_id: Optional[str] = None

    # Extra data passed to spawned event's payload
    spawn_payload: dict[str, Any] = field(default_factory=dict)

    # Arc tracking
    arc_id: Optional[UUID] = None  # Links spawned event to same arc
    arc_stage: int = 0  # What stage in the arc this spawns


@dataclass
class ManagementEvent:
    """
    Base class for all management events.

    Events represent things that happen in the game world that may
    require player attention - free agents becoming available, practices,
    games, trade offers, etc.
    """

    id: UUID = field(default_factory=uuid4)

    # Event identity
    event_type: str = ""  # e.g., "free_agent_available", "practice", "game_day"
    category: EventCategory = EventCategory.SYSTEM
    priority: EventPriority = EventPriority.NORMAL

    # Display info
    title: str = ""  # Short title for clipboard
    description: str = ""  # Longer description
    icon: str = ""  # Icon identifier for UI
    display_mode: DisplayMode = DisplayMode.PANE  # How to show in UI

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None  # When event becomes active
    deadline: Optional[datetime] = None  # When event expires
    duration_minutes: int = 0  # How long the event lasts once started

    # Day-based scheduling (simpler alternative to datetime)
    scheduled_week: Optional[int] = None  # Week number (1-17+)
    scheduled_day: Optional[int] = None  # Day of week (0=Mon, 6=Sun)

    # Event arcs - linking related events
    arc_id: Optional[UUID] = None  # Links events in the same arc/storyline
    triggers: list[EventTrigger] = field(default_factory=list)  # Follow-up events

    # Status
    status: EventStatus = EventStatus.SCHEDULED

    # Behavior flags
    auto_pause: bool = False  # Should game pause when this activates?
    requires_attention: bool = True  # Does player need to act?
    can_dismiss: bool = True  # Can player dismiss without acting?
    can_delegate: bool = False  # Can AI/staff handle this?

    # Related entities (UUIDs)
    team_id: Optional[UUID] = None  # Which team this affects
    player_ids: list[UUID] = field(default_factory=list)  # Related players
    staff_ids: list[UUID] = field(default_factory=list)  # Related staff

    # Payload for event-specific data
    payload: dict[str, Any] = field(default_factory=dict)

    # Callbacks
    _on_attend: Optional[Callable[["ManagementEvent"], None]] = field(default=None, repr=False)
    _on_expire: Optional[Callable[["ManagementEvent"], None]] = field(default=None, repr=False)
    _on_dismiss: Optional[Callable[["ManagementEvent"], None]] = field(default=None, repr=False)

    def is_active(self, current_time: datetime) -> bool:
        """Check if event is currently active (between scheduled time and deadline)."""
        if self.status not in {EventStatus.SCHEDULED, EventStatus.PENDING}:
            return False

        if self.scheduled_for and current_time < self.scheduled_for:
            return False

        if self.deadline and current_time > self.deadline:
            return False

        return True

    def is_expired(self, current_time: datetime) -> bool:
        """Check if event has passed its deadline."""
        if self.deadline and current_time > self.deadline:
            return True
        return False

    def should_activate(self, current_time: datetime) -> bool:
        """Check if event should transition from SCHEDULED to PENDING."""
        if self.status != EventStatus.SCHEDULED:
            return False

        if self.scheduled_for is None:
            return True  # No schedule = immediately active

        return current_time >= self.scheduled_for

    def activate(self) -> None:
        """Transition event to pending/active state."""
        if self.status == EventStatus.SCHEDULED:
            self.status = EventStatus.PENDING

    def attend(self) -> None:
        """Mark event as being attended to."""
        self.status = EventStatus.IN_PROGRESS
        if self._on_attend:
            self._on_attend(self)

    def complete(self) -> None:
        """Mark event as fully attended."""
        self.status = EventStatus.ATTENDED

    def expire(self) -> None:
        """Mark event as expired."""
        self.status = EventStatus.EXPIRED
        if self._on_expire:
            self._on_expire(self)

    def dismiss(self) -> None:
        """Dismiss event without acting."""
        if self.can_dismiss:
            self.status = EventStatus.DISMISSED
            if self._on_dismiss:
                self._on_dismiss(self)

    def delegate(self) -> None:
        """Let AI/staff handle this event."""
        if self.can_delegate:
            self.status = EventStatus.AUTO_RESOLVED

    @property
    def time_until_deadline(self) -> Optional[timedelta]:
        """Get time remaining until deadline."""
        if self.deadline:
            return self.deadline - datetime.now()
        return None

    @property
    def is_urgent(self) -> bool:
        """Check if event is urgent (deadline within 1 hour or high priority)."""
        if self.priority in {EventPriority.CRITICAL, EventPriority.HIGH}:
            return True

        if self.deadline:
            remaining = self.deadline - datetime.now()
            if remaining < timedelta(hours=1):
                return True

        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "category": self.category.name,
            "priority": self.priority.name,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "display_mode": self.display_mode.name,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "duration_minutes": self.duration_minutes,
            "scheduled_week": self.scheduled_week,
            "scheduled_day": self.scheduled_day,
            "arc_id": str(self.arc_id) if self.arc_id else None,
            "status": self.status.name,
            "auto_pause": self.auto_pause,
            "requires_attention": self.requires_attention,
            "can_dismiss": self.can_dismiss,
            "can_delegate": self.can_delegate,
            "team_id": str(self.team_id) if self.team_id else None,
            "player_ids": [str(pid) for pid in self.player_ids],
            "staff_ids": [str(sid) for sid in self.staff_ids],
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ManagementEvent":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            event_type=data.get("event_type", ""),
            category=EventCategory[data.get("category", "SYSTEM")],
            priority=EventPriority[data.get("priority", "NORMAL")],
            title=data.get("title", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            display_mode=DisplayMode[data.get("display_mode", "PANE")],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            scheduled_for=datetime.fromisoformat(data["scheduled_for"]) if data.get("scheduled_for") else None,
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            duration_minutes=data.get("duration_minutes", 0),
            scheduled_week=data.get("scheduled_week"),
            scheduled_day=data.get("scheduled_day"),
            arc_id=UUID(data["arc_id"]) if data.get("arc_id") else None,
            status=EventStatus[data.get("status", "SCHEDULED")],
            auto_pause=data.get("auto_pause", False),
            requires_attention=data.get("requires_attention", True),
            can_dismiss=data.get("can_dismiss", True),
            can_delegate=data.get("can_delegate", False),
            team_id=UUID(data["team_id"]) if data.get("team_id") else None,
            player_ids=[UUID(pid) for pid in data.get("player_ids", [])],
            staff_ids=[UUID(sid) for sid in data.get("staff_ids", [])],
            payload=data.get("payload", {}),
        )


# === Concrete Event Types ===
# These factory functions create common event types with sensible defaults


def create_free_agent_event(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    deadline: datetime,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create a free agent available event."""
    priority = EventPriority.HIGH if overall >= 80 else EventPriority.NORMAL
    if overall >= 90:
        priority = EventPriority.CRITICAL

    return ManagementEvent(
        event_type="free_agent_available",
        category=EventCategory.FREE_AGENCY,
        priority=priority,
        title=f"FA: {player_name}",
        description=f"{position} {player_name} ({overall} OVR) is available",
        icon="fa_player",
        deadline=deadline,
        auto_pause=overall >= 85,  # Auto-pause for elite FAs
        requires_attention=True,
        can_delegate=True,  # GM can handle
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
        },
    )


def create_practice_event(
    scheduled_for: datetime,
    practice_type: str = "regular",
    team_id: Optional[UUID] = None,
    duration_minutes: int = 120,
) -> ManagementEvent:
    """Create a practice event."""
    # Practice deadline is when it ends - you can attend anytime during
    deadline = scheduled_for + timedelta(minutes=duration_minutes)

    return ManagementEvent(
        event_type="practice",
        category=EventCategory.PRACTICE,
        priority=EventPriority.NORMAL,
        title=f"{practice_type.title()} Practice",
        description=f"Team practice scheduled",
        icon="practice",
        scheduled_for=scheduled_for,
        deadline=deadline,
        duration_minutes=duration_minutes,
        auto_pause=False,
        requires_attention=True,  # Player can choose to attend and allocate focus
        can_dismiss=False,
        team_id=team_id,
        payload={
            "practice_type": practice_type,
        },
    )


def create_game_event(
    scheduled_for: datetime,
    opponent_name: str,
    opponent_id: UUID,
    is_home: bool,
    team_id: Optional[UUID] = None,
    week: int = 1,
) -> ManagementEvent:
    """Create a game day event."""
    location = "vs" if is_home else "@"
    return ManagementEvent(
        event_type="game_day",
        category=EventCategory.GAME,
        priority=EventPriority.CRITICAL,
        title=f"Week {week}: {location} {opponent_name}",
        description=f"Game {'at home' if is_home else 'on the road'} against {opponent_name}",
        icon="game",
        scheduled_for=scheduled_for,
        duration_minutes=180,  # ~3 hours
        auto_pause=True,  # Always pause for games
        requires_attention=True,
        can_dismiss=False,
        can_delegate=True,  # Can sim
        team_id=team_id,
        payload={
            "opponent_id": str(opponent_id),
            "opponent_name": opponent_name,
            "is_home": is_home,
            "week": week,
        },
    )


def create_trade_offer_event(
    from_team_name: str,
    from_team_id: UUID,
    offer_summary: str,
    deadline: datetime,
    team_id: Optional[UUID] = None,
    player_ids: Optional[list[UUID]] = None,
) -> ManagementEvent:
    """Create a trade offer event."""
    return ManagementEvent(
        event_type="trade_offer",
        category=EventCategory.TRADE,
        priority=EventPriority.HIGH,
        title=f"Trade: {from_team_name}",
        description=offer_summary,
        icon="trade",
        deadline=deadline,
        auto_pause=False,
        requires_attention=True,
        can_dismiss=True,  # Can reject
        can_delegate=True,  # GM can evaluate
        team_id=team_id,
        player_ids=player_ids or [],
        payload={
            "from_team_id": str(from_team_id),
            "from_team_name": from_team_name,
            "offer_summary": offer_summary,
        },
    )


def create_contract_event(
    player_id: UUID,
    player_name: str,
    event_subtype: str,  # "expiring", "holdout", "extension_request"
    deadline: Optional[datetime] = None,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create a contract-related event."""
    titles = {
        "expiring": f"Contract Expiring: {player_name}",
        "holdout": f"Holdout: {player_name}",
        "extension_request": f"Extension Request: {player_name}",
    }
    return ManagementEvent(
        event_type=f"contract_{event_subtype}",
        category=EventCategory.CONTRACT,
        priority=EventPriority.HIGH if event_subtype == "holdout" else EventPriority.NORMAL,
        title=titles.get(event_subtype, f"Contract: {player_name}"),
        description=f"{player_name} contract situation",
        icon="contract",
        deadline=deadline,
        auto_pause=event_subtype == "holdout",
        requires_attention=True,
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "subtype": event_subtype,
            "player_name": player_name,
        },
    )


def create_negotiation_event(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    market_value: int,  # Total market value in thousands
    team_id: Optional[UUID] = None,
    deadline: Optional[datetime] = None,
) -> ManagementEvent:
    """Create a contract negotiation in-progress event."""
    priority = EventPriority.HIGH if overall >= 85 else EventPriority.NORMAL

    return ManagementEvent(
        event_type="contract_negotiation",
        category=EventCategory.CONTRACT,
        priority=priority,
        title=f"Negotiating: {player_name}",
        description=f"Active contract negotiation with {position} {player_name} ({overall} OVR)",
        icon="negotiation",
        deadline=deadline,
        auto_pause=False,
        requires_attention=True,
        can_dismiss=True,  # Can walk away
        can_delegate=True,  # GM can handle
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "market_value": market_value,
        },
    )


# =============================================================================
# Contract Modal Events (urgent, blocking)
# =============================================================================


def create_holdout_modal(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    current_salary: int,
    demanded_salary: int,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create a holdout modal event - player refusing to play until demands are met."""
    return ManagementEvent(
        event_type="contract_holdout",
        category=EventCategory.CONTRACT,
        priority=EventPriority.CRITICAL,
        title=f"HOLDOUT: {player_name}",
        description=f"{position} {player_name} ({overall} OVR) is refusing to report. "
        f"Demanding ${demanded_salary // 1000}M/yr (currently ${current_salary // 1000}M/yr).",
        icon="holdout",
        display_mode=DisplayMode.MODAL,
        auto_pause=True,
        requires_attention=True,
        can_dismiss=False,  # Must address
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "current_salary": current_salary,
            "demanded_salary": demanded_salary,
            "subtype": "holdout",
        },
    )


def create_extension_deadline_modal(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    years_remaining: int,
    team_id: Optional[UUID] = None,
    deadline: Optional[datetime] = None,
) -> ManagementEvent:
    """Create extension deadline modal - player wants answer by end of day."""
    return ManagementEvent(
        event_type="contract_extension_deadline",
        category=EventCategory.CONTRACT,
        priority=EventPriority.HIGH,
        title=f"Extension Deadline: {player_name}",
        description=f"{position} {player_name} ({overall} OVR) wants an answer on his extension today. "
        f"{years_remaining} year(s) left on current deal.",
        icon="deadline",
        display_mode=DisplayMode.MODAL,
        deadline=deadline,
        auto_pause=True,
        requires_attention=True,
        can_dismiss=True,  # Can decline and let play out
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "years_remaining": years_remaining,
            "subtype": "extension_deadline",
        },
    )


def create_agent_demand_modal(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    demand_type: str,  # "new_deal", "trade_request", "restructure"
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create agent demand modal - agent making demands on behalf of player."""
    demand_descriptions = {
        "new_deal": f"{player_name}'s agent is demanding a new contract or the player will request a trade.",
        "trade_request": f"{player_name}'s agent has informed you that the player wants to be traded.",
        "restructure": f"{player_name}'s agent is requesting a restructure to increase guaranteed money.",
    }
    return ManagementEvent(
        event_type=f"contract_agent_{demand_type}",
        category=EventCategory.CONTRACT,
        priority=EventPriority.HIGH,
        title=f"Agent: {player_name}",
        description=demand_descriptions.get(
            demand_type, f"{player_name}'s agent has a request."
        ),
        icon="agent",
        display_mode=DisplayMode.MODAL,
        auto_pause=True,
        requires_attention=True,
        can_dismiss=True,
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "demand_type": demand_type,
            "subtype": "agent_demand",
        },
    )


def create_contract_signed_modal(
    player_id: UUID,
    player_name: str,
    position: str,
    years: int,
    total_value: int,  # in thousands
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create contract signed modal - notification of completed signing."""
    return ManagementEvent(
        event_type="contract_signed",
        category=EventCategory.CONTRACT,
        priority=EventPriority.NORMAL,
        title=f"Signed: {player_name}",
        description=f"{position} {player_name} has signed a {years}-year, "
        f"${total_value // 1000}M contract with your team.",
        icon="signed",
        display_mode=DisplayMode.MODAL,
        auto_pause=False,
        requires_attention=False,  # Just informational
        can_dismiss=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "years": years,
            "total_value": total_value,
            "subtype": "signed",
        },
    )


def create_bidding_war_event(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    interested_teams: list[str],  # List of team abbreviations
    team_id: Optional[UUID] = None,
    deadline: Optional[datetime] = None,
) -> ManagementEvent:
    """Create a bidding war event for an elite free agent."""
    return ManagementEvent(
        event_type="bidding_war",
        category=EventCategory.FREE_AGENCY,
        priority=EventPriority.CRITICAL,
        title=f"Bidding War: {player_name}",
        description=f"Elite FA {position} {player_name} ({overall} OVR) - {len(interested_teams)} teams interested",
        icon="bidding_war",
        deadline=deadline,
        auto_pause=True,  # Always pause for elite FA bidding
        requires_attention=True,
        can_dismiss=True,  # Can pass
        can_delegate=False,  # Too important
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "interested_teams": interested_teams,
        },
    )


def create_cap_warning_event(
    cap_room: int,
    total_salary: int,
    salary_cap: int,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create a salary cap warning event."""
    cap_pct = (total_salary / salary_cap) * 100
    urgency = "Critical" if cap_pct >= 98 else "Warning"

    return ManagementEvent(
        event_type="cap_warning",
        category=EventCategory.ROSTER,
        priority=EventPriority.CRITICAL if cap_pct >= 98 else EventPriority.HIGH,
        title=f"Cap {urgency}: ${cap_room:,}K room",
        description=f"Team is at {cap_pct:.1f}% of salary cap (${cap_room:,}K remaining)",
        icon="cap_warning",
        auto_pause=cap_pct >= 99,  # Auto-pause if almost over
        requires_attention=True,
        can_dismiss=True,
        can_delegate=False,
        team_id=team_id,
        payload={
            "cap_room": cap_room,
            "total_salary": total_salary,
            "salary_cap": salary_cap,
            "cap_pct": cap_pct,
        },
    )


def create_extension_eligible_event(
    player_id: UUID,
    player_name: str,
    position: str,
    overall: int,
    years_remaining: int,
    current_salary: int,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create an event alerting that a player is eligible for extension."""
    priority = EventPriority.HIGH if overall >= 85 else EventPriority.NORMAL

    return ManagementEvent(
        event_type="extension_eligible",
        category=EventCategory.CONTRACT,
        priority=priority,
        title=f"Extension Eligible: {player_name}",
        description=f"{position} {player_name} ({overall} OVR) has {years_remaining} year(s) left - can extend now",
        icon="extension",
        auto_pause=False,
        requires_attention=True,
        can_dismiss=True,
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "overall": overall,
            "years_remaining": years_remaining,
            "current_salary": current_salary,
        },
    )


def create_cut_recommendation_event(
    player_id: UUID,
    player_name: str,
    position: str,
    salary: int,
    dead_money: int,
    cap_savings: int,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create an event recommending a player be cut for cap savings."""
    return ManagementEvent(
        event_type="cut_recommendation",
        category=EventCategory.ROSTER,
        priority=EventPriority.NORMAL,
        title=f"Cut Candidate: {player_name}",
        description=f"Cutting {position} {player_name} saves ${cap_savings:,}K (${dead_money:,}K dead)",
        icon="cut",
        auto_pause=False,
        requires_attention=True,
        can_dismiss=True,
        can_delegate=True,
        team_id=team_id,
        player_ids=[player_id],
        payload={
            "player_name": player_name,
            "position": position,
            "salary": salary,
            "dead_money": dead_money,
            "cap_savings": cap_savings,
        },
    )


def create_scouting_event(
    event_name: str,
    scheduled_for: datetime,
    event_subtype: str,  # "combine", "pro_day", "workout", "interview"
    team_id: Optional[UUID] = None,
    prospect_ids: Optional[list[UUID]] = None,
) -> ManagementEvent:
    """Create a scouting event."""
    return ManagementEvent(
        event_type=f"scouting_{event_subtype}",
        category=EventCategory.SCOUTING,
        priority=EventPriority.NORMAL,
        title=event_name,
        description=f"Scouting opportunity: {event_subtype}",
        icon="scouting",
        scheduled_for=scheduled_for,
        auto_pause=event_subtype == "workout",  # Pause for private workouts
        requires_attention=True,
        can_dismiss=True,
        can_delegate=True,  # Scouts can attend
        team_id=team_id,
        player_ids=prospect_ids or [],
        payload={
            "subtype": event_subtype,
        },
    )


def create_deadline_event(
    deadline_name: str,
    deadline: datetime,
    description: str = "",
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """Create a deadline reminder event."""
    return ManagementEvent(
        event_type="deadline",
        category=EventCategory.DEADLINE,
        priority=EventPriority.HIGH,
        title=deadline_name,
        description=description or f"Deadline: {deadline_name}",
        icon="deadline",
        scheduled_for=deadline - timedelta(days=1),  # Remind 1 day before
        deadline=deadline,
        auto_pause=True,
        requires_attention=True,
        can_dismiss=False,
        team_id=team_id,
        payload={
            "deadline_name": deadline_name,
        },
    )


def create_scout_report_event(
    opponent_name: str,
    opponent_id: UUID,
    week: int,
    scheduled_week: int,
    scheduled_day: int,
    team_id: Optional[UUID] = None,
) -> ManagementEvent:
    """
    Create a scout report event for upcoming opponent.

    Generates procedural tendencies based on opponent_id seed.
    """
    import random

    # Seed random with opponent_id for consistent procedural generation
    seed = int(str(opponent_id).replace("-", "")[:8], 16)
    rng = random.Random(seed)

    # Generate procedural tendencies
    defenses = ["4-3 Under", "3-4 Over", "4-3 Even", "Nickel", "4-2-5"]
    coverages = ["Cover 2", "Cover 3", "Cover 1 Man", "Cover 4", "Cover 6"]
    blitz_rates = [f"{rng.randint(25, 55)}%"]
    red_zone_schemes = ["Man Heavy", "Zone Heavy", "Aggressive Blitz", "Conservative"]

    # Rankings (1-32)
    off_rank = rng.randint(1, 32)
    def_rank = rng.randint(1, 32)

    # Key threats by position
    threat_positions = ["DE", "LB", "CB", "S", "DT"]
    threats = []
    for pos in rng.sample(threat_positions, 2):
        stat_type = "sacks" if pos in ["DE", "DT", "LB"] else "INTs"
        stat_val = rng.randint(2, 8)
        threats.append({
            "position": pos,
            "stat_type": stat_type,
            "stat_value": stat_val,
        })

    # Attack vectors
    attack_vectors = [
        ("Slot CB", "Weak vs quick routes"),
        ("LB Coverage", "Middle open"),
        ("DE Crash", "Bootleg opportunity"),
        ("Safety Help", "Post routes viable"),
        ("Nickel Back", "Struggles vs size"),
        ("Run Fits", "Outside zone effective"),
    ]
    selected_vectors = rng.sample(attack_vectors, 3)

    return ManagementEvent(
        event_type="scout_report",
        category=EventCategory.SCOUTING,
        priority=EventPriority.HIGH,
        title=f"Scout Report: {opponent_name}",
        description=f"Review defensive tendencies for Week {week} opponent",
        icon="scout",
        display_mode=DisplayMode.PANE,
        scheduled_week=scheduled_week,
        scheduled_day=scheduled_day,
        auto_pause=False,
        requires_attention=True,
        can_dismiss=True,
        team_id=team_id,
        payload={
            "opponent_name": opponent_name,
            "opponent_id": str(opponent_id),
            "week": week,
            "rankings": {
                "offense": off_rank,
                "defense": def_rank,
            },
            "tendencies": {
                "base_defense": rng.choice(defenses),
                "third_down": rng.choice(coverages),
                "red_zone": rng.choice(red_zone_schemes),
                "blitz_rate": blitz_rates[0],
            },
            "key_threats": threats,
            "attack_vectors": [
                {"area": v[0], "note": v[1]} for v in selected_vectors
            ],
        },
    )


@dataclass
class EventQueue:
    """
    Manages the queue of management events.

    Events are stored in a priority queue ordered by:
    1. Priority (critical first)
    2. Deadline (sooner first)
    3. Scheduled time (sooner first)

    The queue handles event lifecycle transitions based on current time.
    """

    _events: dict[UUID, ManagementEvent] = field(default_factory=dict)

    # Callbacks for queue-level events
    _on_event_activated: list[Callable[[ManagementEvent], None]] = field(default_factory=list)
    _on_event_expired: list[Callable[[ManagementEvent], None]] = field(default_factory=list)

    def add(self, event: ManagementEvent) -> None:
        """Add an event to the queue."""
        self._events[event.id] = event

    def remove(self, event_id: UUID) -> Optional[ManagementEvent]:
        """Remove an event from the queue."""
        return self._events.pop(event_id, None)

    def get(self, event_id: UUID) -> Optional[ManagementEvent]:
        """Get an event by ID."""
        return self._events.get(event_id)

    def update(self, current_time: datetime) -> list[ManagementEvent]:
        """
        Update event statuses based on current time.

        Returns list of events that were just activated (for auto-pause checking).
        """
        newly_activated = []

        for event in self._events.values():
            # Check for activation
            if event.should_activate(current_time):
                event.activate()
                newly_activated.append(event)
                for callback in self._on_event_activated:
                    callback(event)

            # Check for expiration
            elif event.status == EventStatus.PENDING and event.is_expired(current_time):
                event.expire()
                for callback in self._on_event_expired:
                    callback(event)

        return newly_activated

    def get_pending(self) -> list[ManagementEvent]:
        """Get all pending events, sorted by priority and deadline."""
        pending = [
            e for e in self._events.values()
            if e.status == EventStatus.PENDING
        ]
        return sorted(pending, key=lambda e: (e.priority.value, e.deadline or datetime.max))

    def get_by_category(self, category: EventCategory) -> list[ManagementEvent]:
        """Get all events in a category."""
        return [e for e in self._events.values() if e.category == category]

    def get_by_status(self, status: EventStatus) -> list[ManagementEvent]:
        """Get all events with a specific status."""
        return [e for e in self._events.values() if e.status == status]

    def get_upcoming(self, within_hours: int = 24) -> list[ManagementEvent]:
        """Get events scheduled within the next N hours."""
        cutoff = datetime.now() + timedelta(hours=within_hours)
        upcoming = [
            e for e in self._events.values()
            if e.status == EventStatus.SCHEDULED
            and e.scheduled_for
            and e.scheduled_for <= cutoff
        ]
        return sorted(upcoming, key=lambda e: e.scheduled_for or datetime.max)

    def get_urgent(self) -> list[ManagementEvent]:
        """Get all urgent events."""
        return [e for e in self._events.values() if e.is_urgent and e.status == EventStatus.PENDING]

    def get_events_for_day(self, week: int, day: int) -> list[ManagementEvent]:
        """
        Get all events scheduled for a specific day.

        Args:
            week: Week number (1-17+)
            day: Day of week (0=Mon, 6=Sun)

        Returns:
            List of events for that day, sorted by priority
        """
        day_events = [
            e for e in self._events.values()
            if e.scheduled_week == week
            and e.scheduled_day == day
            and e.status in {EventStatus.SCHEDULED, EventStatus.PENDING}
        ]
        # Sort by priority (critical first)
        priority_order = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        return sorted(day_events, key=lambda e: priority_order.get(e.priority, 2))

    def activate_day_events(self, week: int, day: int) -> list[ManagementEvent]:
        """
        Activate all events scheduled for a specific day.

        Moves events from SCHEDULED to PENDING and triggers callbacks.
        Returns the activated events.
        """
        activated = []
        for event in self.get_events_for_day(week, day):
            if event.status == EventStatus.SCHEDULED:
                event.status = EventStatus.PENDING
                activated.append(event)
                for callback in self._on_event_activated:
                    callback(event)
        return activated

    def process_triggers(self, event: ManagementEvent, condition: "TriggerCondition") -> list[ManagementEvent]:
        """
        Process event triggers when an event completes/dismisses/expires.

        Spawns follow-up events based on the trigger condition.
        Returns list of newly spawned events.
        """
        spawned = []
        for trigger in event.triggers:
            if trigger.condition == condition:
                # Check probability
                import random
                if random.random() > trigger.probability:
                    continue

                # Create the follow-up event
                from huddle.management.generators import create_triggered_event
                new_event = create_triggered_event(trigger, event)
                if new_event:
                    self.add(new_event)
                    spawned.append(new_event)

        return spawned

    def get_auto_pause_events(self) -> list[ManagementEvent]:
        """Get pending events that should trigger auto-pause."""
        return [
            e for e in self._events.values()
            if e.auto_pause and e.status == EventStatus.PENDING
        ]

    def clear_completed(self) -> int:
        """Remove all completed/expired/dismissed events. Returns count removed."""
        terminal_statuses = {
            EventStatus.ATTENDED,
            EventStatus.EXPIRED,
            EventStatus.DISMISSED,
            EventStatus.AUTO_RESOLVED,
        }
        to_remove = [
            eid for eid, e in self._events.items()
            if e.status in terminal_statuses
        ]
        for eid in to_remove:
            del self._events[eid]
        return len(to_remove)

    def on_event_activated(self, callback: Callable[[ManagementEvent], None]) -> None:
        """Register callback for when events activate."""
        self._on_event_activated.append(callback)

    def on_event_expired(self, callback: Callable[[ManagementEvent], None]) -> None:
        """Register callback for when events expire."""
        self._on_event_expired.append(callback)

    @property
    def count(self) -> int:
        """Total number of events in queue."""
        return len(self._events)

    @property
    def pending_count(self) -> int:
        """Number of pending events."""
        return len(self.get_pending())

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "events": [e.to_dict() for e in self._events.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventQueue":
        """Create from dictionary."""
        queue = cls()
        for event_data in data.get("events", []):
            event = ManagementEvent.from_dict(event_data)
            queue.add(event)
        return queue
