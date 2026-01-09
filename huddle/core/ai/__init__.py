"""
AI Systems for Autonomous Team Management.

Provides AI decision-making for:
- Draft selections (DraftAI)
- Roster management (RosterAI)
- Free agency (FreeAgencyAI)
- Trades (TradeAI)
"""

from huddle.core.ai.draft_ai import (
    DraftAI,
    DraftAIConfig,
    ProspectEvaluation,
    TeamNeeds,
    calculate_team_needs,
)

from huddle.core.ai.roster_ai import (
    RosterAI,
    RosterEvaluation,
    CutDecision,
    select_starters,
    get_starter_ids,
)

from huddle.core.ai.free_agency_ai import (
    FreeAgencyAI,
    FreeAgentEvaluation,
    ContractOfferResult,
    simulate_free_agency_market,
)

from huddle.core.ai.trade_ai import (
    TradeAI,
    TradeAsset,
    TradeProposal,
    TradeEvaluation,
    player_trade_value,
)

__all__ = [
    # Draft
    "DraftAI",
    "DraftAIConfig",
    "ProspectEvaluation",
    "TeamNeeds",
    "calculate_team_needs",
    # Roster
    "RosterAI",
    "RosterEvaluation",
    "CutDecision",
    "select_starters",
    "get_starter_ids",
    # Free Agency
    "FreeAgencyAI",
    "FreeAgentEvaluation",
    "ContractOfferResult",
    "simulate_free_agency_market",
    # Trade
    "TradeAI",
    "TradeAsset",
    "TradeProposal",
    "TradeEvaluation",
    "player_trade_value",
]
