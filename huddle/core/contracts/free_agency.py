"""
Free Agency Bidding System.

Provides HC09-style competitive free agency:
- Top players enter "Bidding War" phase
- Teams submit bids based on need + cap
- Player picks based on: money, team fit, contender status
- Non-elite FAs: normal negotiation
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.contracts.market_value import calculate_market_value, MarketValue
from huddle.core.contracts.negotiation import ContractOffer
from huddle.core.contracts.ai_decisions import (
    evaluate_free_agent,
    calculate_team_position_need,
)

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team import Team
    from huddle.core.league.league import League


class FreeAgentTier(Enum):
    """Classification of free agent value."""
    ELITE = auto()      # Top 5-10 FAs, bidding wars
    STARTER = auto()    # Quality starters, competitive interest
    DEPTH = auto()      # Rotational players, normal market
    MINIMUM = auto()    # Camp bodies, league minimum


@dataclass
class FreeAgentListing:
    """
    A free agent with their market evaluation.
    """
    player_id: str
    player_name: str
    position: str
    overall: int
    age: int
    tier: FreeAgentTier
    market_value: MarketValue


@dataclass
class TeamBid:
    """
    A team's bid for a free agent.
    """
    team_abbr: str
    team_name: str
    offer: ContractOffer
    interest_level: float  # 0-1, how much they want this player
    is_user: bool = False


@dataclass
class BiddingResult:
    """
    Result of a bidding war for a free agent.
    """
    player_id: str
    player_name: str
    winning_team: Optional[str]  # None if unsigned
    winning_bid: Optional[ContractOffer]
    all_bids: list[TeamBid]
    reason: str  # Why the player chose this team


@dataclass
class FreeAgencyPeriod:
    """
    Manages the free agency period.

    Tracks available players, team cap situations,
    and runs the signing process.
    """
    listings: list[FreeAgentListing] = field(default_factory=list)
    completed_signings: list[BiddingResult] = field(default_factory=list)
    unsigned: list[str] = field(default_factory=list)  # Player IDs


def classify_free_agent(player: "Player") -> FreeAgentTier:
    """
    Classify a free agent into a tier based on quality.
    """
    overall = player.overall
    age = player.age

    # Age penalty - older players drop tiers faster
    age_penalty = max(0, (age - 29) * 2)  # 2 OVR penalty per year over 29
    effective_ovr = overall - age_penalty

    if effective_ovr >= 88:
        return FreeAgentTier.ELITE
    elif effective_ovr >= 78:
        return FreeAgentTier.STARTER
    elif effective_ovr >= 68:
        return FreeAgentTier.DEPTH
    else:
        return FreeAgentTier.MINIMUM


def create_free_agent_listing(player: "Player") -> FreeAgentListing:
    """
    Create a listing for a free agent with market evaluation.
    """
    market = calculate_market_value(player)
    tier = classify_free_agent(player)

    return FreeAgentListing(
        player_id=str(player.id),
        player_name=player.full_name,
        position=player.position.value,
        overall=player.overall,
        age=player.age,
        tier=tier,
        market_value=market,
    )


def generate_team_bid(
    team: "Team",
    listing: FreeAgentListing,
    player: "Player",
) -> Optional[TeamBid]:
    """
    Generate a team's bid for a free agent.

    Returns None if team won't bid.
    """
    # Calculate position need
    need = calculate_team_position_need(team, listing.position)

    # Evaluate interest
    evaluation = evaluate_free_agent(team, player, position_need=need)

    if not evaluation.interested:
        return None

    # Check if can afford
    market = listing.market_value
    min_salary = int(market.base_salary * evaluation.opening_offer_pct)

    if not team.can_afford(min_salary):
        return None

    # Generate bid based on tier
    if listing.tier == FreeAgentTier.ELITE:
        # Elite players get competitive bids near or above market
        bid_pct = evaluation.max_offer_pct * random.uniform(0.90, 1.0)
    elif listing.tier == FreeAgentTier.STARTER:
        # Starters get market-rate bids
        bid_pct = random.uniform(evaluation.opening_offer_pct, evaluation.max_offer_pct)
    else:
        # Lower tiers get lower bids
        bid_pct = evaluation.opening_offer_pct

    offer = ContractOffer(
        years=market.years,
        salary=int(market.base_salary * bid_pct),
        signing_bonus=int(market.signing_bonus * bid_pct),
    )

    # Final cap check
    if not team.can_afford(offer.salary):
        return None

    return TeamBid(
        team_abbr=team.abbreviation,
        team_name=team.full_name,
        offer=offer,
        interest_level=evaluation.interest_score,
    )


def player_choose_team(
    listing: FreeAgentListing,
    bids: list[TeamBid],
    team_records: dict[str, float] = None,  # abbr -> win_pct
) -> tuple[Optional[TeamBid], str]:
    """
    Player chooses between competing bids.

    Decision factors:
    - Money (60%): Total contract value
    - Team fit/contender (25%): Team's winning record
    - Role/interest (15%): How much team wants them

    Returns (chosen_bid, reason) or (None, reason) if unsigned.
    """
    if not bids:
        return (None, "No teams made offers")

    if len(bids) == 1:
        return (bids[0], f"Only offer from {bids[0].team_name}")

    # Default win percentages if not provided
    if team_records is None:
        team_records = {}

    # Score each bid
    scored_bids = []
    max_money = max(b.offer.total_value for b in bids)
    max_interest = max(b.interest_level for b in bids)

    for bid in bids:
        # Money score (0-100)
        money_score = (bid.offer.total_value / max_money) * 100 if max_money > 0 else 50

        # Contender score (0-100)
        win_pct = team_records.get(bid.team_abbr, 0.5)
        contender_score = win_pct * 100

        # Interest score (0-100)
        interest_score = (bid.interest_level / max_interest) * 100 if max_interest > 0 else 50

        # Weighted total
        # Elite players weight money more, depth players weight role more
        if listing.tier == FreeAgentTier.ELITE:
            total = (money_score * 0.55) + (contender_score * 0.35) + (interest_score * 0.10)
        elif listing.tier == FreeAgentTier.STARTER:
            total = (money_score * 0.50) + (contender_score * 0.30) + (interest_score * 0.20)
        else:
            total = (money_score * 0.40) + (contender_score * 0.25) + (interest_score * 0.35)

        # Add some randomness (player preferences/location)
        total += random.uniform(-10, 10)

        scored_bids.append((bid, total, money_score, contender_score))

    # Sort by score
    scored_bids.sort(key=lambda x: x[1], reverse=True)
    winner = scored_bids[0][0]

    # Generate reason
    if scored_bids[0][2] > scored_bids[1][2] + 10:  # Money was deciding factor
        reason = f"Chose {winner.team_name} - best financial package"
    elif scored_bids[0][3] > 60:  # Contender was factor
        reason = f"Chose {winner.team_name} - contender status"
    else:
        reason = f"Chose {winner.team_name} - best overall fit"

    return (winner, reason)


def run_free_agency_period(
    league: "League",
    user_team_abbr: str = None,
) -> FreeAgencyPeriod:
    """
    Run a complete free agency period.

    Returns the FreeAgencyPeriod with all signings.
    """
    period = FreeAgencyPeriod()

    # Create listings for all free agents
    for player in league.free_agents:
        listing = create_free_agent_listing(player)
        period.listings.append(listing)

    # Sort by tier then overall (best players first)
    period.listings.sort(key=lambda x: (-x.tier.value, -x.overall))

    # Get team win percentages for player decisions
    team_records = {}
    for abbr, standing in league.standings.items():
        team_records[abbr] = standing.win_pct

    # Process each free agent
    for listing in period.listings:
        # Find the actual player object
        player = None
        from uuid import UUID
        player_uuid = UUID(listing.player_id)
        for fa in league.free_agents:
            if fa.id == player_uuid:
                player = fa
                break

        if not player:
            continue

        # Collect bids from all teams
        bids = []
        for abbr, team in league.teams.items():
            # Skip user team - they bid manually
            if abbr == user_team_abbr:
                continue

            bid = generate_team_bid(team, listing, player)
            if bid:
                bids.append(bid)

        # Player chooses
        chosen, reason = player_choose_team(listing, bids, team_records)

        if chosen:
            # Execute the signing
            team = league.teams[chosen.team_abbr]

            # Remove from free agents and add to roster
            league.free_agents.remove(player)
            team.roster.add_player(player)

            # Assign contract
            player.contract_years = chosen.offer.years
            player.contract_year_remaining = chosen.offer.years
            player.salary = chosen.offer.salary
            player.signing_bonus = chosen.offer.signing_bonus
            player.signing_bonus_remaining = chosen.offer.signing_bonus

            # Update team financials
            team.financials.add_contract(chosen.offer.salary)

            result = BiddingResult(
                player_id=listing.player_id,
                player_name=listing.player_name,
                winning_team=chosen.team_abbr,
                winning_bid=chosen.offer,
                all_bids=bids,
                reason=reason,
            )
        else:
            result = BiddingResult(
                player_id=listing.player_id,
                player_name=listing.player_name,
                winning_team=None,
                winning_bid=None,
                all_bids=bids,
                reason=reason,
            )
            period.unsigned.append(listing.player_id)

        period.completed_signings.append(result)

    return period


def get_top_free_agents(
    league: "League",
    limit: int = 20,
) -> list[FreeAgentListing]:
    """
    Get the top free agents available for the user to view.
    """
    listings = []
    for player in league.free_agents:
        listing = create_free_agent_listing(player)
        listings.append(listing)

    # Sort by tier then overall
    listings.sort(key=lambda x: (-x.tier.value, -x.overall))

    return listings[:limit]


def get_interested_teams(
    league: "League",
    player: "Player",
) -> list[tuple[str, float]]:
    """
    Get list of teams interested in a player and their interest level.

    Returns list of (team_abbr, interest_score) sorted by interest.
    """
    listing = create_free_agent_listing(player)
    interested = []

    for abbr, team in league.teams.items():
        need = calculate_team_position_need(team, player.position.value)
        evaluation = evaluate_free_agent(team, player, position_need=need)

        if evaluation.interested:
            interested.append((abbr, evaluation.interest_score))

    # Sort by interest level
    interested.sort(key=lambda x: x[1], reverse=True)

    return interested
