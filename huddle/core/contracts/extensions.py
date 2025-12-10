"""
Contract Extension System.

Allows teams to re-sign players before they hit free agency:
- Players in final 2 years can be extended
- Extension offers get a "security premium" discount vs FA market
- Player loyalty/tenure affects acceptance
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.contracts.market_value import calculate_market_value, MarketValue
from huddle.core.contracts.negotiation import ContractOffer

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team import Team


class ExtensionEligibility(Enum):
    """Whether a player is eligible for extension."""
    ELIGIBLE = auto()         # Final 2 years of contract
    TOO_EARLY = auto()        # More than 2 years remaining
    EXPIRING = auto()         # Final year - can extend but less discount
    NO_CONTRACT = auto()      # Not under contract (free agent)


class ExtensionResult(Enum):
    """Outcome of an extension offer."""
    ACCEPTED = auto()
    REJECTED = auto()
    COUNTER_OFFER = auto()


@dataclass
class ExtensionOffer:
    """
    Contract extension offer.

    Extensions add years to existing contract.
    """
    additional_years: int     # Years to add
    new_salary: int          # New annual salary
    new_signing_bonus: int   # New bonus (prorated over new years)
    new_total_value: int     # Total value of extension

    @property
    def cap_hit_year1(self) -> int:
        """First year cap impact of new deal."""
        return self.new_salary + (self.new_signing_bonus // self.additional_years)


@dataclass
class ExtensionResponse:
    """
    Player's response to an extension offer.
    """
    result: ExtensionResult
    message: str
    counter_offer: Optional[ExtensionOffer] = None
    acceptance_probability: float = 0.0


def check_extension_eligibility(player: "Player") -> ExtensionEligibility:
    """
    Check if a player is eligible for contract extension.

    Players must be in their final 2 years to extend.
    """
    if player.contract_year_remaining is None:
        return ExtensionEligibility.NO_CONTRACT

    if player.contract_year_remaining <= 1:
        return ExtensionEligibility.EXPIRING
    elif player.contract_year_remaining <= 2:
        return ExtensionEligibility.ELIGIBLE
    else:
        return ExtensionEligibility.TOO_EARLY


def calculate_extension_value(
    player: "Player",
    additional_years: int = 3,
) -> tuple[MarketValue, float]:
    """
    Calculate market value for an extension and the "hometown discount".

    Returns (market_value, discount_factor).

    The discount factor represents the reduction a player might accept
    for the security of an extension vs hitting free agency.
    """
    market = calculate_market_value(player)

    # Base discount for security (avoiding FA uncertainty)
    base_discount = 0.95  # 5% discount for extension security

    # Adjust based on player age - older players value security more
    if player.age >= 32:
        age_discount = 0.92  # 8% discount - really values security
    elif player.age >= 29:
        age_discount = 0.94  # 6% discount
    else:
        age_discount = 0.97  # 3% discount - younger players chase FA money

    # Tenure discount - players with more time on team more loyal
    years_on_team = player.years_on_team or 0
    if years_on_team >= 5:
        tenure_discount = 0.94  # Long-tenured players give discount
    elif years_on_team >= 3:
        tenure_discount = 0.96
    else:
        tenure_discount = 0.98

    # Combined discount (multiply factors)
    discount_factor = base_discount * (age_discount / 0.95) * (tenure_discount / 0.95)
    discount_factor = max(0.85, min(0.98, discount_factor))  # Cap at 85-98%

    return (market, discount_factor)


def evaluate_extension_offer(
    player: "Player",
    offer: ExtensionOffer,
    team: "Team" = None,
) -> ExtensionResponse:
    """
    Evaluate an extension offer from the player's perspective.

    Considers:
    - Offer vs market value
    - Player's loyalty/tenure
    - Team's competitiveness
    """
    market, discount = calculate_extension_value(player, offer.additional_years)

    # What player expects (market value adjusted by discount)
    expected_salary = int(market.base_salary * discount)
    expected_total = expected_salary * offer.additional_years + int(market.signing_bonus * discount)

    offer_pct = offer.new_total_value / expected_total if expected_total > 0 else 1.0

    # Acceptance thresholds
    if offer_pct >= 1.0:
        # Meeting or exceeding expectations
        result = ExtensionResult.ACCEPTED
        message = f"{player.full_name} is thrilled to stay and accepts the extension!"
        acceptance_prob = 1.0

    elif offer_pct >= 0.92:
        # Close enough - high chance of accepting
        acceptance_prob = 0.70 + (offer_pct - 0.92) * 3.75  # 70-100% chance

        if random.random() < acceptance_prob:
            result = ExtensionResult.ACCEPTED
            message = f"{player.full_name} accepts the extension offer."
        else:
            # Counter at expected value
            counter = ExtensionOffer(
                additional_years=offer.additional_years,
                new_salary=expected_salary,
                new_signing_bonus=int(market.signing_bonus * discount),
                new_total_value=expected_total,
            )
            result = ExtensionResult.COUNTER_OFFER
            message = f"{player.full_name}'s agent: 'We need ${expected_salary:,}K per year to get this done.'"
            return ExtensionResponse(
                result=result,
                message=message,
                counter_offer=counter,
                acceptance_probability=acceptance_prob,
            )

    elif offer_pct >= 0.85:
        # Below expectations but negotiable
        acceptance_prob = 0.20 + (offer_pct - 0.85) * 7.14  # 20-70% chance

        # Counter between offer and expected
        counter_salary = int((offer.new_salary + expected_salary) / 2)
        counter_total = counter_salary * offer.additional_years + int(market.signing_bonus * discount)

        counter = ExtensionOffer(
            additional_years=offer.additional_years,
            new_salary=counter_salary,
            new_signing_bonus=int(market.signing_bonus * discount),
            new_total_value=counter_total,
        )
        result = ExtensionResult.COUNTER_OFFER
        message = f"{player.full_name}'s agent: 'That's below market. We're looking for ${counter_salary:,}K.'"

        return ExtensionResponse(
            result=result,
            message=message,
            counter_offer=counter,
            acceptance_probability=acceptance_prob,
        )

    else:
        # Too low - rejection
        result = ExtensionResult.REJECTED
        message = f"{player.full_name}'s agent: 'That offer is insulting. We'll test free agency.'"
        acceptance_prob = 0.0

    return ExtensionResponse(
        result=result,
        message=message,
        acceptance_probability=acceptance_prob,
    )


def apply_extension(
    player: "Player",
    team: "Team",
    offer: ExtensionOffer,
) -> None:
    """
    Apply an accepted extension to the player's contract.

    Updates player contract fields and team financials.
    """
    # Calculate new contract values
    # Extension adds years and replaces salary/bonus
    new_total_years = (player.contract_year_remaining or 0) + offer.additional_years

    # Old salary comes off, new salary goes on
    old_salary = player.salary or 0
    team.financials.total_salary -= old_salary
    team.financials.total_salary += offer.new_salary

    # Update player contract
    player.contract_years = new_total_years
    player.contract_year_remaining = new_total_years
    player.salary = offer.new_salary
    player.signing_bonus = offer.new_signing_bonus
    player.signing_bonus_remaining = offer.new_signing_bonus


def generate_extension_offer(
    player: "Player",
    additional_years: int = 3,
    offer_pct: float = 0.95,
) -> ExtensionOffer:
    """
    Generate an extension offer at a percentage of market value.

    Args:
        player: The player to extend
        additional_years: Years to add to contract
        offer_pct: Percentage of market value to offer (0.0-1.0+)

    Returns:
        ExtensionOffer ready to present to player
    """
    market, discount = calculate_extension_value(player, additional_years)

    # Calculate offer values
    new_salary = int(market.base_salary * discount * offer_pct)
    new_bonus = int(market.signing_bonus * discount * offer_pct)
    new_total = new_salary * additional_years + new_bonus

    return ExtensionOffer(
        additional_years=additional_years,
        new_salary=new_salary,
        new_signing_bonus=new_bonus,
        new_total_value=new_total,
    )


def get_extension_candidates(team: "Team") -> list[tuple["Player", ExtensionEligibility]]:
    """
    Get all players on a team eligible for extension.

    Returns list of (player, eligibility) sorted by overall rating.
    """
    candidates = []

    for player in team.roster.players.values():
        eligibility = check_extension_eligibility(player)
        if eligibility in (ExtensionEligibility.ELIGIBLE, ExtensionEligibility.EXPIRING):
            candidates.append((player, eligibility))

    # Sort by overall (best players first)
    candidates.sort(key=lambda x: x[0].overall, reverse=True)

    return candidates
