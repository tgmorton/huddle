"""
Clipboard State Management.

The clipboard is the primary UI element on the right side of the screen.
It contains tabs for different views (Events, Roster, Depth Chart, etc.)
and controls what appears in the active panel on the left.

This module manages the clipboard state and panel routing.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional
from uuid import UUID


class ClipboardTab(Enum):
    """
    Available tabs on the clipboard.

    Each tab represents a different view/function the player can access.
    """

    # Primary tabs
    EVENTS = auto()  # Event queue - always first
    ROSTER = auto()  # Team roster
    DEPTH_CHART = auto()  # Position depth chart
    SCHEDULE = auto()  # Season schedule

    # Personnel tabs
    FREE_AGENTS = auto()  # Available free agents
    TRADE_BLOCK = auto()  # Players available for trade
    DRAFT_BOARD = auto()  # Draft prospects (when in season)

    # Staff tabs
    COACHING_STAFF = auto()  # Coaches and their skills
    FRONT_OFFICE = auto()  # GM, scouts

    # Team tabs
    PLAYBOOK = auto()  # Offensive/defensive playbook
    GAMEPLAN = auto()  # Weekly gameplan setup
    FINANCES = auto()  # Salary cap, contracts

    # League tabs
    STANDINGS = auto()  # League standings
    LEAGUE_LEADERS = auto()  # Statistical leaders
    TRANSACTIONS = auto()  # Recent league transactions

    @property
    def display_name(self) -> str:
        """Get display name for tab."""
        names = {
            ClipboardTab.EVENTS: "Events",
            ClipboardTab.ROSTER: "Roster",
            ClipboardTab.DEPTH_CHART: "Depth Chart",
            ClipboardTab.SCHEDULE: "Schedule",
            ClipboardTab.FREE_AGENTS: "Free Agents",
            ClipboardTab.TRADE_BLOCK: "Trade Block",
            ClipboardTab.DRAFT_BOARD: "Draft Board",
            ClipboardTab.COACHING_STAFF: "Coaches",
            ClipboardTab.FRONT_OFFICE: "Front Office",
            ClipboardTab.PLAYBOOK: "Playbook",
            ClipboardTab.GAMEPLAN: "Gameplan",
            ClipboardTab.FINANCES: "Finances",
            ClipboardTab.STANDINGS: "Standings",
            ClipboardTab.LEAGUE_LEADERS: "Leaders",
            ClipboardTab.TRANSACTIONS: "Transactions",
        }
        return names.get(self, self.name.replace("_", " ").title())

    @property
    def icon(self) -> str:
        """Get icon identifier for tab."""
        icons = {
            ClipboardTab.EVENTS: "clipboard",
            ClipboardTab.ROSTER: "users",
            ClipboardTab.DEPTH_CHART: "list",
            ClipboardTab.SCHEDULE: "calendar",
            ClipboardTab.FREE_AGENTS: "user-plus",
            ClipboardTab.TRADE_BLOCK: "exchange",
            ClipboardTab.DRAFT_BOARD: "graduation-cap",
            ClipboardTab.COACHING_STAFF: "whistle",
            ClipboardTab.FRONT_OFFICE: "briefcase",
            ClipboardTab.PLAYBOOK: "book",
            ClipboardTab.GAMEPLAN: "strategy",
            ClipboardTab.FINANCES: "dollar",
            ClipboardTab.STANDINGS: "trophy",
            ClipboardTab.LEAGUE_LEADERS: "star",
            ClipboardTab.TRANSACTIONS: "newspaper",
        }
        return icons.get(self, "file")


class PanelType(Enum):
    """
    Types of panels that can appear in the active panel area.

    This determines what component/view is rendered on the left side.
    """

    # Event-related panels
    EVENT_LIST = auto()  # List of events (default for Events tab)
    EVENT_DETAIL = auto()  # Single event detail view

    # Roster panels
    ROSTER_LIST = auto()  # Full roster list
    PLAYER_CARD = auto()  # Individual player detail
    PLAYER_COMPARISON = auto()  # Compare two players

    # Depth chart panels
    DEPTH_CHART_VIEW = auto()  # Visual depth chart
    POSITION_GROUP = auto()  # Single position group detail

    # Schedule panels
    SCHEDULE_VIEW = auto()  # Season schedule
    GAME_PREVIEW = auto()  # Upcoming game preview
    GAME_RESULT = auto()  # Past game result

    # Free agency panels
    FREE_AGENT_LIST = auto()  # Available FAs
    FREE_AGENT_DETAIL = auto()  # Single FA detail
    CONTRACT_NEGOTIATION = auto()  # Active negotiation

    # Trade panels
    TRADE_BLOCK_VIEW = auto()  # Your trade block
    TRADE_PROPOSAL = auto()  # Incoming/outgoing trade
    TRADE_FINDER = auto()  # Search for trades

    # Draft panels
    DRAFT_BOARD_VIEW = auto()  # Big board
    PROSPECT_CARD = auto()  # Prospect detail
    SCOUTING_REPORT = auto()  # Scouting info

    # Staff panels
    STAFF_LIST = auto()  # Staff roster
    STAFF_DETAIL = auto()  # Individual staff member
    STAFF_HIRING = auto()  # Hiring interface

    # Playbook panels
    PLAYBOOK_VIEW = auto()  # Playbook overview
    PLAY_DETAIL = auto()  # Single play diagram
    PLAY_PRACTICE = auto()  # Practice play setup

    # Gameplan panels
    GAMEPLAN_SETUP = auto()  # Weekly gameplan
    OPPONENT_TENDENCIES = auto()  # Opponent analysis

    # Finance panels
    CAP_OVERVIEW = auto()  # Salary cap status
    CONTRACT_LIST = auto()  # All contracts
    CONTRACT_DETAIL = auto()  # Single contract

    # League panels
    STANDINGS_VIEW = auto()  # League standings
    LEADERS_VIEW = auto()  # Stat leaders
    TRANSACTIONS_VIEW = auto()  # Recent transactions

    # Game panels
    GAME_LIVE = auto()  # Live game view
    GAME_SIMULATION = auto()  # Game sim controls

    # Special panels
    EMPTY = auto()  # No content
    LOADING = auto()  # Loading state


@dataclass
class PanelContext:
    """
    Context for what's displayed in the active panel.

    Contains the panel type and any associated data needed to render it.
    """

    panel_type: PanelType = PanelType.EMPTY

    # Entity references (what is this panel showing?)
    event_id: Optional[UUID] = None
    player_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    game_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    prospect_id: Optional[UUID] = None

    # Additional context data
    context_data: dict[str, Any] = field(default_factory=dict)

    # Navigation history tracking
    previous_panel: Optional["PanelContext"] = field(default=None, repr=False)

    def with_player(self, player_id: UUID) -> "PanelContext":
        """Create new context focused on a player."""
        return PanelContext(
            panel_type=PanelType.PLAYER_CARD,
            player_id=player_id,
            previous_panel=self,
        )

    def with_event(self, event_id: UUID) -> "PanelContext":
        """Create new context focused on an event."""
        return PanelContext(
            panel_type=PanelType.EVENT_DETAIL,
            event_id=event_id,
            previous_panel=self,
        )

    def with_game(self, game_id: UUID) -> "PanelContext":
        """Create new context focused on a game."""
        return PanelContext(
            panel_type=PanelType.GAME_PREVIEW,
            game_id=game_id,
            previous_panel=self,
        )

    @property
    def can_go_back(self) -> bool:
        """Check if there's a previous panel to return to."""
        return self.previous_panel is not None

    def go_back(self) -> "PanelContext":
        """Return to previous panel context."""
        return self.previous_panel if self.previous_panel else self

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "panel_type": self.panel_type.name,
            "event_id": str(self.event_id) if self.event_id else None,
            "player_id": str(self.player_id) if self.player_id else None,
            "team_id": str(self.team_id) if self.team_id else None,
            "game_id": str(self.game_id) if self.game_id else None,
            "staff_id": str(self.staff_id) if self.staff_id else None,
            "prospect_id": str(self.prospect_id) if self.prospect_id else None,
            "context_data": self.context_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelContext":
        """Create from dictionary."""
        return cls(
            panel_type=PanelType[data.get("panel_type", "EMPTY")],
            event_id=UUID(data["event_id"]) if data.get("event_id") else None,
            player_id=UUID(data["player_id"]) if data.get("player_id") else None,
            team_id=UUID(data["team_id"]) if data.get("team_id") else None,
            game_id=UUID(data["game_id"]) if data.get("game_id") else None,
            staff_id=UUID(data["staff_id"]) if data.get("staff_id") else None,
            prospect_id=UUID(data["prospect_id"]) if data.get("prospect_id") else None,
            context_data=data.get("context_data", {}),
        )


@dataclass
class ClipboardState:
    """
    Complete state of the clipboard UI.

    Tracks which tab is selected, what's in the active panel,
    and any clipboard-level state like search filters.
    """

    # Current tab selection
    active_tab: ClipboardTab = ClipboardTab.EVENTS

    # Active panel context
    panel: PanelContext = field(default_factory=PanelContext)

    # Available tabs (some may be hidden based on season phase)
    available_tabs: list[ClipboardTab] = field(default_factory=lambda: [
        ClipboardTab.EVENTS,
        ClipboardTab.ROSTER,
        ClipboardTab.DEPTH_CHART,
        ClipboardTab.SCHEDULE,
        ClipboardTab.COACHING_STAFF,
        ClipboardTab.PLAYBOOK,
        ClipboardTab.FINANCES,
        ClipboardTab.STANDINGS,
    ])

    # Tab-specific state
    roster_filter: Optional[str] = None  # Position filter for roster
    roster_sort: str = "overall"  # Sort field for roster

    free_agent_filter: Optional[str] = None
    free_agent_sort: str = "overall"

    draft_board_filter: Optional[str] = None
    draft_board_sort: str = "rank"

    # Search state
    search_query: str = ""
    search_active: bool = False

    # Notification badges (count of items needing attention)
    tab_badges: dict[ClipboardTab, int] = field(default_factory=dict)

    def select_tab(self, tab: ClipboardTab) -> None:
        """
        Select a clipboard tab.

        This also sets the default panel for that tab.
        """
        if tab not in self.available_tabs:
            return

        self.active_tab = tab
        self.panel = self._default_panel_for_tab(tab)
        self.search_active = False
        self.search_query = ""

    def _default_panel_for_tab(self, tab: ClipboardTab) -> PanelContext:
        """Get default panel context for a tab."""
        defaults = {
            ClipboardTab.EVENTS: PanelType.EVENT_LIST,
            ClipboardTab.ROSTER: PanelType.ROSTER_LIST,
            ClipboardTab.DEPTH_CHART: PanelType.DEPTH_CHART_VIEW,
            ClipboardTab.SCHEDULE: PanelType.SCHEDULE_VIEW,
            ClipboardTab.FREE_AGENTS: PanelType.FREE_AGENT_LIST,
            ClipboardTab.TRADE_BLOCK: PanelType.TRADE_BLOCK_VIEW,
            ClipboardTab.DRAFT_BOARD: PanelType.DRAFT_BOARD_VIEW,
            ClipboardTab.COACHING_STAFF: PanelType.STAFF_LIST,
            ClipboardTab.FRONT_OFFICE: PanelType.STAFF_LIST,
            ClipboardTab.PLAYBOOK: PanelType.PLAYBOOK_VIEW,
            ClipboardTab.GAMEPLAN: PanelType.GAMEPLAN_SETUP,
            ClipboardTab.FINANCES: PanelType.CAP_OVERVIEW,
            ClipboardTab.STANDINGS: PanelType.STANDINGS_VIEW,
            ClipboardTab.LEAGUE_LEADERS: PanelType.LEADERS_VIEW,
            ClipboardTab.TRANSACTIONS: PanelType.TRANSACTIONS_VIEW,
        }
        panel_type = defaults.get(tab, PanelType.EMPTY)
        return PanelContext(panel_type=panel_type)

    def set_panel(self, panel: PanelContext) -> None:
        """Set the active panel directly."""
        self.panel = panel

    def navigate_to_player(self, player_id: UUID) -> None:
        """Navigate to a player's detail view."""
        self.panel = self.panel.with_player(player_id)

    def navigate_to_event(self, event_id: UUID) -> None:
        """Navigate to an event's detail view."""
        self.panel = self.panel.with_event(event_id)

    def navigate_to_game(self, game_id: UUID) -> None:
        """Navigate to a game view."""
        self.panel = self.panel.with_game(game_id)

    def go_back(self) -> bool:
        """
        Navigate back to previous panel.

        Returns True if navigation occurred, False if at root.
        """
        if self.panel.can_go_back:
            self.panel = self.panel.go_back()
            return True
        return False

    def set_badge(self, tab: ClipboardTab, count: int) -> None:
        """Set notification badge count for a tab."""
        if count > 0:
            self.tab_badges[tab] = count
        elif tab in self.tab_badges:
            del self.tab_badges[tab]

    def get_badge(self, tab: ClipboardTab) -> int:
        """Get notification badge count for a tab."""
        return self.tab_badges.get(tab, 0)

    def update_available_tabs(self, is_draft_season: bool = False, is_free_agency: bool = False) -> None:
        """Update which tabs are available based on season phase."""
        base_tabs = [
            ClipboardTab.EVENTS,
            ClipboardTab.ROSTER,
            ClipboardTab.DEPTH_CHART,
            ClipboardTab.SCHEDULE,
            ClipboardTab.COACHING_STAFF,
            ClipboardTab.PLAYBOOK,
            ClipboardTab.FINANCES,
            ClipboardTab.STANDINGS,
        ]

        if is_draft_season:
            base_tabs.insert(4, ClipboardTab.DRAFT_BOARD)

        if is_free_agency:
            base_tabs.insert(4, ClipboardTab.FREE_AGENTS)

        # Trade block available most of the time
        if ClipboardTab.TRADE_BLOCK not in base_tabs:
            base_tabs.insert(5, ClipboardTab.TRADE_BLOCK)

        self.available_tabs = base_tabs

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "active_tab": self.active_tab.name,
            "panel": self.panel.to_dict(),
            "available_tabs": [t.name for t in self.available_tabs],
            "roster_filter": self.roster_filter,
            "roster_sort": self.roster_sort,
            "free_agent_filter": self.free_agent_filter,
            "free_agent_sort": self.free_agent_sort,
            "draft_board_filter": self.draft_board_filter,
            "draft_board_sort": self.draft_board_sort,
            "search_query": self.search_query,
            "search_active": self.search_active,
            "tab_badges": {t.name: c for t, c in self.tab_badges.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClipboardState":
        """Create from dictionary."""
        state = cls(
            active_tab=ClipboardTab[data.get("active_tab", "EVENTS")],
            panel=PanelContext.from_dict(data.get("panel", {})),
            available_tabs=[ClipboardTab[t] for t in data.get("available_tabs", ["EVENTS"])],
            roster_filter=data.get("roster_filter"),
            roster_sort=data.get("roster_sort", "overall"),
            free_agent_filter=data.get("free_agent_filter"),
            free_agent_sort=data.get("free_agent_sort", "overall"),
            draft_board_filter=data.get("draft_board_filter"),
            draft_board_sort=data.get("draft_board_sort", "rank"),
            search_query=data.get("search_query", ""),
            search_active=data.get("search_active", False),
        )
        # Restore badges
        for tab_name, count in data.get("tab_badges", {}).items():
            state.tab_badges[ClipboardTab[tab_name]] = count
        return state
