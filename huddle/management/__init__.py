"""Management systems for the franchise/career mode game loop."""

from huddle.management.calendar import (
    LeagueCalendar,
    SeasonPhase,
    NFLWeek,
    TimeSpeed,
)
from huddle.management.events import (
    ManagementEvent,
    EventCategory,
    EventPriority,
    EventStatus,
    EventQueue,
    create_free_agent_event,
    create_practice_event,
    create_game_event,
    create_trade_offer_event,
    create_contract_event,
    create_scouting_event,
    create_deadline_event,
)
from huddle.management.clipboard import (
    ClipboardTab,
    ClipboardState,
    PanelType,
    PanelContext,
)
from huddle.management.ticker import (
    TickerItem,
    TickerCategory,
    TickerFeed,
    ticker_signing,
    ticker_release,
    ticker_trade,
    ticker_score,
    ticker_injury,
    ticker_draft_pick,
    ticker_rumor,
    ticker_deadline,
)
from huddle.management.league import LeagueState
from huddle.management.generators import (
    EventGenerator,
    EventGeneratorConfig,
    ScheduledGame,
    FreeAgentInfo,
)

__all__ = [
    # Calendar
    "LeagueCalendar",
    "SeasonPhase",
    "NFLWeek",
    "TimeSpeed",
    # Events
    "ManagementEvent",
    "EventCategory",
    "EventPriority",
    "EventStatus",
    "EventQueue",
    "create_free_agent_event",
    "create_practice_event",
    "create_game_event",
    "create_trade_offer_event",
    "create_contract_event",
    "create_scouting_event",
    "create_deadline_event",
    # Clipboard
    "ClipboardTab",
    "ClipboardState",
    "PanelType",
    "PanelContext",
    # Ticker
    "TickerItem",
    "TickerCategory",
    "TickerFeed",
    "ticker_signing",
    "ticker_release",
    "ticker_trade",
    "ticker_score",
    "ticker_injury",
    "ticker_draft_pick",
    "ticker_rumor",
    "ticker_deadline",
    # League State
    "LeagueState",
    # Generators
    "EventGenerator",
    "EventGeneratorConfig",
    "ScheduledGame",
    "FreeAgentInfo",
]
