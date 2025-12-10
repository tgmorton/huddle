"""
Contracts module for salary cap and contract management.

This module provides:
- Market value calculation for players
- Contract negotiation mechanics
- AI contract decision making
- Free agency bidding system
- Contract extensions
"""

from huddle.core.contracts.market_value import (
    MarketValue,
    calculate_market_value,
    calculate_relative_value,
    assign_contract,
    generate_roster_contracts,
    POSITION_VALUE_MULTIPLIERS,
    AGE_VALUE_CURVE,
)

from huddle.core.contracts.negotiation import (
    NegotiationResult,
    NegotiationTone,
    ContractOffer,
    NegotiationResponse,
    NegotiationState,
    start_negotiation,
    evaluate_offer,
    quick_negotiate,
)

from huddle.core.contracts.ai_decisions import (
    AIEvaluation,
    AIOfferDecision,
    evaluate_free_agent,
    generate_opening_offer,
    respond_to_counter,
    run_ai_negotiation,
    calculate_team_position_need,
)

from huddle.core.contracts.free_agency import (
    FreeAgentTier,
    FreeAgentListing,
    TeamBid,
    BiddingResult,
    FreeAgencyPeriod,
    classify_free_agent,
    create_free_agent_listing,
    run_free_agency_period,
    get_top_free_agents,
    get_interested_teams,
)

from huddle.core.contracts.extensions import (
    ExtensionEligibility,
    ExtensionResult,
    ExtensionOffer,
    ExtensionResponse,
    check_extension_eligibility,
    calculate_extension_value,
    evaluate_extension_offer,
    apply_extension,
    generate_extension_offer,
    get_extension_candidates,
)

__all__ = [
    # Market value
    "MarketValue",
    "calculate_market_value",
    "calculate_relative_value",
    "assign_contract",
    "generate_roster_contracts",
    "POSITION_VALUE_MULTIPLIERS",
    "AGE_VALUE_CURVE",
    # Negotiation
    "NegotiationResult",
    "NegotiationTone",
    "ContractOffer",
    "NegotiationResponse",
    "NegotiationState",
    "start_negotiation",
    "evaluate_offer",
    "quick_negotiate",
    # AI decisions
    "AIEvaluation",
    "AIOfferDecision",
    "evaluate_free_agent",
    "generate_opening_offer",
    "respond_to_counter",
    "run_ai_negotiation",
    "calculate_team_position_need",
    # Free agency
    "FreeAgentTier",
    "FreeAgentListing",
    "TeamBid",
    "BiddingResult",
    "FreeAgencyPeriod",
    "classify_free_agent",
    "create_free_agent_listing",
    "run_free_agency_period",
    "get_top_free_agents",
    "get_interested_teams",
    # Extensions
    "ExtensionEligibility",
    "ExtensionResult",
    "ExtensionOffer",
    "ExtensionResponse",
    "check_extension_eligibility",
    "calculate_extension_value",
    "evaluate_extension_offer",
    "apply_extension",
    "generate_extension_offer",
    "get_extension_candidates",
]
