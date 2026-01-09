"""
Free agency management router.

Handles free agents, negotiations, and auctions:
- Free agent listing
- Contract negotiations
- Elite player auctions
"""

import random as auction_random
from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.core.contracts.market_value import MarketValue, calculate_market_value
from huddle.api.schemas.management import (
    FreeAgentInfo,
    FreeAgentsResponse,
    # Negotiation
    NegotiationResultSchema,
    NegotiationToneSchema,
    ContractOfferSchema,
    MarketValueSchema,
    StartNegotiationRequest,
    StartNegotiationResponse,
    SubmitOfferRequest,
    SubmitOfferResponse,
    ActiveNegotiationInfo,
    ActiveNegotiationsResponse,
    # Auction
    AuctionPhaseSchema,
    AuctionResultSchema,
    CompetingTeamBid,
    AuctionBidSchema,
    StartAuctionRequest,
    StartAuctionResponse,
    SubmitAuctionBidRequest,
    SubmitAuctionBidResponse,
    FinalizeAuctionResponse,
    ActiveAuctionInfo,
    ActiveAuctionsResponse,
)
from .deps import get_session

router = APIRouter(tags=["free-agency"])


# =============================================================================
# In-Memory State for Negotiations and Auctions
# Note: In a future refactor, this should move to ManagementService
# =============================================================================

# Store active negotiations per franchise (in-memory for now)
_active_negotiations: Dict[str, Dict[str, "NegotiationState"]] = {}


def _get_franchise_negotiations(franchise_id: str) -> dict:
    """Get or create negotiations dict for a franchise."""
    if franchise_id not in _active_negotiations:
        _active_negotiations[franchise_id] = {}
    return _active_negotiations[franchise_id]


def _contract_offer_to_schema(offer) -> ContractOfferSchema:
    """Convert ContractOffer to schema."""
    return ContractOfferSchema(
        years=offer.years,
        salary=offer.salary,
        signing_bonus=offer.signing_bonus,
        total_value=offer.total_value,
        guaranteed=offer.guaranteed,
    )


# =============================================================================
# Auction State Classes
# =============================================================================


@dataclass
class AuctionTeamBid:
    """A team's bid in the auction."""

    team_id: str
    team_name: str
    team_abbrev: str
    interest_level: str  # HIGH, MEDIUM, LOW
    years: int = 0
    salary: int = 0
    signing_bonus: int = 0

    @property
    def total_value(self) -> int:
        return self.years * self.salary + self.signing_bonus

    @property
    def guaranteed(self) -> int:
        return self.signing_bonus + (self.salary // 2)


@dataclass
class AuctionState:
    """State of an ongoing auction."""

    auction_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    player_age: int
    market_value: MarketValue

    # Auction progress
    phase: str = "BIDDING"  # BIDDING, FINAL_CALL, CLOSED
    round: int = 1
    max_rounds: int = 3

    # User's bid
    user_bid: Optional[AuctionTeamBid] = None

    # Competing teams and their bids
    competing_teams: List[AuctionTeamBid] = dataclass_field(default_factory=list)

    # Result
    is_complete: bool = False
    result: Optional[str] = None
    winning_team: Optional[str] = None
    winning_bid: Optional[AuctionTeamBid] = None


_active_auctions: Dict[str, Dict[str, AuctionState]] = {}


def _get_franchise_auctions(franchise_id: str) -> Dict[str, AuctionState]:
    """Get or create the auctions dict for a franchise."""
    if franchise_id not in _active_auctions:
        _active_auctions[franchise_id] = {}
    return _active_auctions[franchise_id]


def _generate_competing_teams(
    player_overall: int, market_value: MarketValue
) -> List[AuctionTeamBid]:
    """Generate AI teams interested in the player."""
    # Sample team names for demo
    TEAMS = [
        ("Dallas Cowboys", "DAL"),
        ("New England Patriots", "NE"),
        ("Green Bay Packers", "GB"),
        ("San Francisco 49ers", "SF"),
        ("Kansas City Chiefs", "KC"),
        ("Buffalo Bills", "BUF"),
        ("Miami Dolphins", "MIA"),
        ("Philadelphia Eagles", "PHI"),
        ("Los Angeles Rams", "LAR"),
        ("Baltimore Ravens", "BAL"),
    ]

    # Elite players attract more teams
    if player_overall >= 90:
        num_teams = auction_random.randint(4, 6)
    elif player_overall >= 85:
        num_teams = auction_random.randint(3, 5)
    else:
        num_teams = auction_random.randint(2, 4)

    selected = auction_random.sample(TEAMS, min(num_teams, len(TEAMS)))

    teams = []
    for team_name, abbrev in selected:
        # Determine interest level
        roll = auction_random.random()
        if roll > 0.7:
            interest = "HIGH"
        elif roll > 0.3:
            interest = "MEDIUM"
        else:
            interest = "LOW"

        teams.append(
            AuctionTeamBid(
                team_id=abbrev.lower(),
                team_name=team_name,
                team_abbrev=abbrev,
                interest_level=interest,
            )
        )

    return teams


def _ai_team_makes_bid(
    team: AuctionTeamBid,
    market_value: MarketValue,
    current_round: int,
    top_bid: Optional[AuctionTeamBid],
) -> bool:
    """Determine if an AI team makes a bid this round."""
    # Interest level affects bid probability
    base_prob = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}.get(team.interest_level, 0.5)

    # Later rounds = more pressure to bid
    round_bonus = (current_round - 1) * 0.1

    # If already has a bid and is top, less likely to raise
    if team.total_value > 0 and top_bid and team.team_id == top_bid.team_id:
        return False

    return auction_random.random() < (base_prob + round_bonus)


def _generate_ai_bid(
    team: AuctionTeamBid,
    market_value: MarketValue,
    current_round: int,
    top_bid: Optional[AuctionTeamBid],
) -> None:
    """Generate an AI team's bid."""
    # Base bid around market value
    interest_mult = {"HIGH": 1.15, "MEDIUM": 1.05, "LOW": 0.95}.get(team.interest_level, 1.0)

    # Add some variance
    variance = auction_random.uniform(0.95, 1.10)

    # If there's a top bid, need to beat it
    if top_bid and top_bid.total_value > 0:
        min_salary = int(top_bid.salary * 1.02)  # At least 2% more
        target_salary = int(market_value.base_salary * interest_mult * variance)
        team.salary = max(min_salary, target_salary)
    else:
        team.salary = int(market_value.base_salary * interest_mult * variance)

    team.years = market_value.years
    team.signing_bonus = int(market_value.signing_bonus * interest_mult * variance)


def _get_top_bid(state: AuctionState) -> Optional[AuctionTeamBid]:
    """Get the current top bid in the auction."""
    all_bids = [t for t in state.competing_teams if t.total_value > 0]
    if state.user_bid and state.user_bid.total_value > 0:
        all_bids.append(state.user_bid)

    if not all_bids:
        return None

    return max(all_bids, key=lambda b: b.total_value)


def _bid_to_range(bid: AuctionTeamBid) -> str:
    """Convert a bid to a range string (obscure exact amount)."""
    if bid.salary == 0:
        return "No bid"

    # Round to nearest $500K and add variance
    low = (bid.salary // 500) * 500
    high = low + 2000  # $2M range

    if low >= 1000:
        return f"${low / 1000:.1f}M-${high / 1000:.1f}M/yr"
    else:
        return f"${low}K-${high}K/yr"


def _auction_bid_to_schema(bid: Optional[AuctionTeamBid]) -> Optional[AuctionBidSchema]:
    """Convert auction bid to schema."""
    if not bid or bid.total_value == 0:
        return None
    return AuctionBidSchema(
        years=bid.years,
        salary=bid.salary,
        signing_bonus=bid.signing_bonus,
        total_value=bid.total_value,
        guaranteed=bid.guaranteed,
    )


# =============================================================================
# Free Agent Endpoints
# =============================================================================


@router.get("/franchise/{franchise_id}/free-agents", response_model=FreeAgentsResponse)
async def get_free_agents(franchise_id: UUID) -> FreeAgentsResponse:
    """Get available free agents with market evaluation."""
    session = get_session(franchise_id)
    league = session.service.league
    agents = []

    for player in league.free_agents:
        # Calculate market value
        mv = calculate_market_value(player)

        # Determine tier based on overall
        overall = player.overall or 0
        if overall >= 88:
            tier = "ELITE"
        elif overall >= 78:
            tier = "STARTER"
        elif overall >= 68:
            tier = "DEPTH"
        else:
            tier = "MINIMUM"

        agents.append(
            FreeAgentInfo(
                player_id=str(player.id),
                name=f"{player.first_name} {player.last_name}",
                position=player.position.value if player.position else "UNK",
                overall=overall,
                age=player.age or 0,
                tier=tier,
                market_value=mv.base_salary,
            )
        )

    # Sort by overall descending
    agents.sort(key=lambda a: a.overall, reverse=True)

    return FreeAgentsResponse(count=len(agents), free_agents=agents)


# =============================================================================
# Negotiation Endpoints
# =============================================================================


@router.post(
    "/franchise/{franchise_id}/negotiations/start", response_model=StartNegotiationResponse
)
async def start_negotiation(
    franchise_id: UUID,
    request: StartNegotiationRequest,
) -> StartNegotiationResponse:
    """Start a contract negotiation with a free agent."""
    from huddle.core.contracts.negotiation import start_negotiation as begin_negotiation

    session = get_session(franchise_id)
    league = session.service.league

    # Find the player in free agents
    player = None
    for fa in league.free_agents:
        if str(fa.id) == request.player_id:
            player = fa
            break

    if not player:
        raise HTTPException(status_code=404, detail="Player not found in free agents")

    # Check if already negotiating with this player
    negotiations = _get_franchise_negotiations(str(franchise_id))
    if request.player_id in negotiations:
        raise HTTPException(status_code=400, detail="Already negotiating with this player")

    # Start the negotiation
    state = begin_negotiation(player)
    negotiations[request.player_id] = state

    # Calculate market value for response
    mv = calculate_market_value(player)

    # Determine tier
    overall = player.overall or 0
    if overall >= 85:
        tier = "ELITE"
    elif overall >= 75:
        tier = "STARTER"
    elif overall >= 68:
        tier = "DEPTH"
    else:
        tier = "MINIMUM"

    return StartNegotiationResponse(
        negotiation_id=f"{franchise_id}-{request.player_id}",
        player_id=request.player_id,
        player_name=player.full_name,
        player_position=player.position.value if player.position else "UNK",
        player_overall=player.overall or 0,
        player_age=player.age or 0,
        market_value=MarketValueSchema(
            base_salary=mv.base_salary,
            signing_bonus=mv.signing_bonus,
            years=mv.years,
            total_value=mv.total_value,
            tier=tier,
        ),
        opening_demand=_contract_offer_to_schema(state.current_demand),
        message=f"{player.full_name}'s agent is ready to negotiate. They're looking for around ${state.current_demand.salary:,}K per year.",
    )


@router.post(
    "/franchise/{franchise_id}/negotiations/{player_id}/offer", response_model=SubmitOfferResponse
)
async def submit_offer(
    franchise_id: UUID,
    player_id: str,
    request: SubmitOfferRequest,
) -> SubmitOfferResponse:
    """Submit a contract offer in an active negotiation."""
    from uuid import UUID as UUIDType
    from huddle.core.contracts.negotiation import evaluate_offer, ContractOffer, NegotiationResult

    session = get_session(franchise_id)
    league = session.service.league
    team = session.team

    if not team:
        raise HTTPException(status_code=400, detail="No team connected to this franchise")

    # Get active negotiation
    negotiations = _get_franchise_negotiations(str(franchise_id))
    state = negotiations.get(player_id)
    if not state:
        raise HTTPException(status_code=404, detail="No active negotiation with this player")

    if state.is_complete:
        raise HTTPException(status_code=400, detail="Negotiation is already complete")

    # Find the player for personality-aware evaluation
    player = None
    for fa in league.free_agents:
        if str(fa.id) == player_id:
            player = fa
            break

    if not player:
        raise HTTPException(status_code=404, detail="Player not found in free agents")

    # Cap validation: check if team can afford the offer before evaluating
    if not team.can_afford(request.salary):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot afford ${request.salary:,}K salary. Cap room: ${team.cap_room:,}K"
        )

    # Create the offer
    offer = ContractOffer(
        years=request.years,
        salary=request.salary,
        signing_bonus=request.signing_bonus,
    )

    # Evaluate the offer
    response = evaluate_offer(state, offer, player)

    # Track signing result for response
    signing_message = None

    # If accepted, complete the signing
    if response.result == NegotiationResult.ACCEPTED:
        # Remove from negotiations
        del negotiations[player_id]

        # Get the agreed contract terms
        agreed = state.agreed_contract
        if agreed:
            # Sign the player: creates contract, adds to roster, removes from FA, updates cap
            success, sign_msg = league.sign_free_agent(
                player_id=UUIDType(player_id),
                team_abbr=team.abbreviation,
                salary=agreed.salary,
                years=agreed.years,
                signing_bonus=agreed.signing_bonus,
                enforce_cap=True,  # Should pass since we checked above
            )

            if success:
                signing_message = sign_msg
            else:
                # Signing failed (shouldn't happen since we pre-checked cap)
                raise HTTPException(status_code=400, detail=f"Signing failed: {sign_msg}")

    # If walked away, remove negotiation
    elif response.result == NegotiationResult.WALK_AWAY:
        del negotiations[player_id]

    # Build response message
    final_message = response.message
    if signing_message:
        final_message = f"{response.message} {signing_message}"

    return SubmitOfferResponse(
        result=NegotiationResultSchema(response.result.name),
        tone=NegotiationToneSchema(response.tone.name),
        message=final_message,
        offer_pct_of_market=response.offer_pct_of_market,
        walk_away_chance=response.walk_away_chance,
        counter_offer=_contract_offer_to_schema(response.counter_offer)
        if response.counter_offer
        else None,
        agreed_contract=_contract_offer_to_schema(state.agreed_contract)
        if state.agreed_contract
        else None,
        rounds=state.rounds,
        patience=state.patience,
    )


@router.get(
    "/franchise/{franchise_id}/negotiations/active", response_model=ActiveNegotiationsResponse
)
async def get_active_negotiations(franchise_id: UUID) -> ActiveNegotiationsResponse:
    """Get list of active negotiations for a franchise."""
    session = get_session(franchise_id)

    negotiations = _get_franchise_negotiations(str(franchise_id))

    result = []
    for player_id, state in negotiations.items():
        if not state.is_complete:
            result.append(
                ActiveNegotiationInfo(
                    negotiation_id=f"{franchise_id}-{player_id}",
                    player_id=player_id,
                    player_name=state.player_name,
                    player_position=state.player_position,
                    player_overall=state.player_overall,
                    rounds=state.rounds,
                    last_offer=_contract_offer_to_schema(state.offers_made[-1])
                    if state.offers_made
                    else None,
                    current_demand=_contract_offer_to_schema(state.current_demand)
                    if state.current_demand
                    else None,
                    patience=state.patience,
                )
            )

    return ActiveNegotiationsResponse(
        negotiations=result,
        count=len(result),
    )


@router.delete("/franchise/{franchise_id}/negotiations/{player_id}")
async def cancel_negotiation(franchise_id: UUID, player_id: str) -> dict:
    """Cancel/abandon an active negotiation."""
    session = get_session(franchise_id)

    negotiations = _get_franchise_negotiations(str(franchise_id))

    if player_id not in negotiations:
        raise HTTPException(status_code=404, detail="No active negotiation with this player")

    del negotiations[player_id]

    return {"success": True, "message": "Negotiation cancelled"}


# =============================================================================
# Auction Endpoints
# =============================================================================


@router.post(
    "/franchise/{franchise_id}/free-agency/auction/start", response_model=StartAuctionResponse
)
async def start_auction(franchise_id: UUID, request: StartAuctionRequest) -> StartAuctionResponse:
    """Start an auction for an elite free agent."""
    from huddle.api.routers.admin import get_active_league

    session = get_session(franchise_id)

    league = get_active_league()
    if not league:
        raise HTTPException(status_code=404, detail="No active league")

    # Find the player in free agents
    player = None
    for fa in league.free_agents:
        if str(fa.id) == request.player_id:
            player = fa
            break

    if not player:
        raise HTTPException(status_code=404, detail="Player not found in free agents")

    # Check if already in an auction
    auctions = _get_franchise_auctions(str(franchise_id))
    if request.player_id in auctions:
        raise HTTPException(status_code=400, detail="Already in an auction with this player")

    # Calculate market value
    market = calculate_market_value(player)

    # Only elite players go to auction
    if market.tier not in ("ELITE", "STARTER"):
        raise HTTPException(
            status_code=400,
            detail=f"Only ELITE and STARTER tier players go to auction. This player is {market.tier}.",
        )

    # Generate competing teams
    competing_teams = _generate_competing_teams(player.overall, market)

    # Some teams may make opening bids
    for team in competing_teams:
        if _ai_team_makes_bid(team, market, 1, None):
            _generate_ai_bid(team, market, 1, None)

    # Create auction state
    auction_id = f"{franchise_id}-auction-{request.player_id}"
    state = AuctionState(
        auction_id=auction_id,
        player_id=request.player_id,
        player_name=player.full_name,
        player_position=player.position.value,
        player_overall=player.overall,
        player_age=player.age,
        market_value=market,
        competing_teams=competing_teams,
    )

    auctions[request.player_id] = state

    # Floor bid is 80% of market value
    floor_bid = AuctionBidSchema(
        years=market.years,
        salary=int(market.base_salary * 0.80),
        signing_bonus=int(market.signing_bonus * 0.80),
        total_value=int(market.total_value * 0.80),
        guaranteed=int((market.signing_bonus + market.base_salary // 2) * 0.80),
    )

    # Convert competing teams to response format
    top_bid = _get_top_bid(state)
    competing_response = [
        CompetingTeamBid(
            team_id=t.team_id,
            team_name=t.team_name,
            team_abbrev=t.team_abbrev,
            interest_level=t.interest_level,
            has_bid=t.total_value > 0,
            is_top_bid=top_bid is not None and t.team_id == top_bid.team_id,
            bid_range=_bid_to_range(t) if t.total_value > 0 else None,
        )
        for t in competing_teams
    ]

    return StartAuctionResponse(
        auction_id=auction_id,
        player_id=request.player_id,
        player_name=player.full_name,
        player_position=player.position.value,
        player_overall=player.overall,
        player_age=player.age,
        market_value=MarketValueSchema(
            base_salary=market.base_salary,
            signing_bonus=market.signing_bonus,
            years=market.years,
            total_value=market.total_value,
            tier=market.tier,
        ),
        phase=AuctionPhaseSchema.BIDDING,
        round=1,
        max_rounds=3,
        competing_teams=competing_response,
        floor_bid=floor_bid,
        message=f"Auction opened for {player.full_name}. {len(competing_teams)} teams are interested.",
    )


@router.post(
    "/franchise/{franchise_id}/free-agency/auction/{player_id}/bid",
    response_model=SubmitAuctionBidResponse,
)
async def submit_auction_bid(
    franchise_id: UUID,
    player_id: str,
    request: SubmitAuctionBidRequest,
) -> SubmitAuctionBidResponse:
    """Submit a bid in an active auction."""
    session = get_session(franchise_id)

    auctions = _get_franchise_auctions(str(franchise_id))
    state = auctions.get(player_id)

    if not state:
        raise HTTPException(status_code=404, detail="No active auction for this player")

    if state.is_complete:
        raise HTTPException(status_code=400, detail="Auction is already complete")

    if state.phase == "CLOSED":
        raise HTTPException(status_code=400, detail="Auction is closed")

    # Create user bid
    user_bid = AuctionTeamBid(
        team_id="user",
        team_name="Your Team",
        team_abbrev="YOU",
        interest_level="HIGH",
        years=request.years,
        salary=request.salary,
        signing_bonus=request.signing_bonus,
    )
    state.user_bid = user_bid

    # AI teams may respond
    top_bid = _get_top_bid(state)
    for team in state.competing_teams:
        # If team was outbid, they might raise
        if top_bid and team.total_value < top_bid.total_value:
            if _ai_team_makes_bid(team, state.market_value, state.round, top_bid):
                _generate_ai_bid(team, state.market_value, state.round, top_bid)

    # Check if user is now top bid
    new_top = _get_top_bid(state)
    is_top_bid = new_top is not None and new_top.team_id == "user"

    # Convert to response
    competing_response = [
        CompetingTeamBid(
            team_id=t.team_id,
            team_name=t.team_name,
            team_abbrev=t.team_abbrev,
            interest_level=t.interest_level,
            has_bid=t.total_value > 0,
            is_top_bid=new_top is not None and t.team_id == new_top.team_id,
            bid_range=_bid_to_range(t) if t.total_value > 0 else None,
        )
        for t in state.competing_teams
    ]

    # Determine message
    if is_top_bid:
        message = "Your bid is currently the highest!"
    else:
        message = f"You've been outbid. {new_top.team_abbrev if new_top else 'Another team'} has the top bid."

    return SubmitAuctionBidResponse(
        success=True,
        message=message,
        phase=AuctionPhaseSchema(state.phase),
        round=state.round,
        your_bid=_auction_bid_to_schema(user_bid),
        is_top_bid=is_top_bid,
        competing_teams=competing_response,
        top_bid_range=_bid_to_range(new_top) if new_top and not is_top_bid else None,
    )


@router.post(
    "/franchise/{franchise_id}/free-agency/auction/{player_id}/advance",
    response_model=SubmitAuctionBidResponse,
)
async def advance_auction_round(franchise_id: UUID, player_id: str) -> SubmitAuctionBidResponse:
    """Advance the auction to the next round."""
    session = get_session(franchise_id)

    auctions = _get_franchise_auctions(str(franchise_id))
    state = auctions.get(player_id)

    if not state:
        raise HTTPException(status_code=404, detail="No active auction for this player")

    if state.is_complete:
        raise HTTPException(status_code=400, detail="Auction is already complete")

    # Advance round
    state.round += 1

    # Update phase
    if state.round >= state.max_rounds:
        state.phase = "FINAL_CALL"
    elif state.round > state.max_rounds:
        state.phase = "CLOSED"

    # AI teams may make new bids
    top_bid = _get_top_bid(state)
    for team in state.competing_teams:
        if _ai_team_makes_bid(team, state.market_value, state.round, top_bid):
            _generate_ai_bid(team, state.market_value, state.round, top_bid)

    # Check user's position
    new_top = _get_top_bid(state)
    is_top_bid = state.user_bid is not None and new_top is not None and new_top.team_id == "user"

    # Convert to response
    competing_response = [
        CompetingTeamBid(
            team_id=t.team_id,
            team_name=t.team_name,
            team_abbrev=t.team_abbrev,
            interest_level=t.interest_level,
            has_bid=t.total_value > 0,
            is_top_bid=new_top is not None and t.team_id == new_top.team_id,
            bid_range=_bid_to_range(t) if t.total_value > 0 else None,
        )
        for t in state.competing_teams
    ]

    phase_msg = (
        "Final call!"
        if state.phase == "FINAL_CALL"
        else f"Round {state.round} of {state.max_rounds}"
    )

    return SubmitAuctionBidResponse(
        success=True,
        message=f"{phase_msg} {'You have the top bid.' if is_top_bid else 'You are not the top bidder.'}",
        phase=AuctionPhaseSchema(state.phase),
        round=state.round,
        your_bid=_auction_bid_to_schema(state.user_bid),
        is_top_bid=is_top_bid,
        competing_teams=competing_response,
        top_bid_range=_bid_to_range(new_top) if new_top and not is_top_bid else None,
    )


@router.post(
    "/franchise/{franchise_id}/free-agency/auction/{player_id}/finalize",
    response_model=FinalizeAuctionResponse,
)
async def finalize_auction(franchise_id: UUID, player_id: str) -> FinalizeAuctionResponse:
    """Finalize the auction and determine winner."""
    from uuid import UUID as UUIDType

    session = get_session(franchise_id)
    league = session.service.league
    team = session.team

    auctions = _get_franchise_auctions(str(franchise_id))
    state = auctions.get(player_id)

    if not state:
        raise HTTPException(status_code=404, detail="No active auction for this player")

    if state.is_complete:
        raise HTTPException(status_code=400, detail="Auction is already complete")

    # Mark complete
    state.is_complete = True
    state.phase = "CLOSED"

    # Determine winner
    top_bid = _get_top_bid(state)

    if not top_bid:
        # No bids - player stays in free agency
        state.result = "NO_BID"
        del auctions[player_id]
        return FinalizeAuctionResponse(
            result=AuctionResultSchema.NO_BID,
            message=f"No acceptable bids were received. {state.player_name} remains a free agent.",
        )

    if top_bid.team_id == "user":
        # User won! Complete the signing
        state.result = "WON"
        state.winning_bid = top_bid
        del auctions[player_id]

        # Sign the player to user's team
        if team:
            success, sign_msg = league.sign_free_agent(
                player_id=UUIDType(player_id),
                team_abbr=team.abbreviation,
                salary=top_bid.salary,
                years=top_bid.years,
                signing_bonus=top_bid.signing_bonus,
                enforce_cap=True,
            )

            if not success:
                return FinalizeAuctionResponse(
                    result=AuctionResultSchema.NO_BID,
                    message=f"Signing failed: {sign_msg}. {state.player_name} remains a free agent.",
                )

            return FinalizeAuctionResponse(
                result=AuctionResultSchema.WON,
                message=f"Congratulations! {sign_msg}",
                winning_bid=_auction_bid_to_schema(top_bid),
            )
        else:
            return FinalizeAuctionResponse(
                result=AuctionResultSchema.WON,
                message=f"Congratulations! You've won the auction for {state.player_name}!",
                winning_bid=_auction_bid_to_schema(top_bid),
            )
    else:
        # AI team won - sign to that team
        state.result = "OUTBID"
        state.winning_team = top_bid.team_name
        state.winning_bid = top_bid
        del auctions[player_id]

        # Sign to AI team (remove from FA pool)
        league.sign_free_agent(
            player_id=UUIDType(player_id),
            team_abbr=top_bid.team_abbrev,
            salary=top_bid.salary,
            years=top_bid.years,
            signing_bonus=top_bid.signing_bonus,
            enforce_cap=False,  # AI teams don't have strict cap enforcement
        )

        return FinalizeAuctionResponse(
            result=AuctionResultSchema.OUTBID,
            message=f"{state.player_name} has signed with the {top_bid.team_name}.",
            winning_team=top_bid.team_name,
            winning_team_abbrev=top_bid.team_abbrev,
        )


@router.get(
    "/franchise/{franchise_id}/free-agency/auctions/active", response_model=ActiveAuctionsResponse
)
async def get_active_auctions(franchise_id: UUID) -> ActiveAuctionsResponse:
    """Get list of active auctions for a franchise."""
    session = get_session(franchise_id)

    auctions = _get_franchise_auctions(str(franchise_id))

    result = []
    for player_id, state in auctions.items():
        if not state.is_complete:
            top_bid = _get_top_bid(state)
            is_top = (
                state.user_bid is not None and top_bid is not None and top_bid.team_id == "user"
            )

            result.append(
                ActiveAuctionInfo(
                    auction_id=state.auction_id,
                    player_id=player_id,
                    player_name=state.player_name,
                    player_position=state.player_position,
                    player_overall=state.player_overall,
                    phase=AuctionPhaseSchema(state.phase),
                    round=state.round,
                    max_rounds=state.max_rounds,
                    your_bid=_auction_bid_to_schema(state.user_bid),
                    is_top_bid=is_top,
                    competing_teams_count=len(state.competing_teams),
                )
            )

    return ActiveAuctionsResponse(
        auctions=result,
        count=len(result),
    )


@router.delete("/franchise/{franchise_id}/free-agency/auction/{player_id}")
async def withdraw_from_auction(franchise_id: UUID, player_id: str) -> dict:
    """Withdraw from an active auction."""
    session = get_session(franchise_id)

    auctions = _get_franchise_auctions(str(franchise_id))

    if player_id not in auctions:
        raise HTTPException(status_code=404, detail="No active auction for this player")

    state = auctions[player_id]

    # Remove user's bid but keep auction going for AI teams
    state.user_bid = None

    # In a real implementation, the auction would continue for AI teams
    # For now, just remove the user's involvement
    del auctions[player_id]

    return {"success": True, "message": "Withdrawn from auction"}
