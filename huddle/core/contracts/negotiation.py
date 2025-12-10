"""
Contract Negotiation System.

Provides HC09-style negotiation mechanics:
- Offer evaluation based on market value
- Counter-offers with explanation
- Walk-away risk for lowball offers
- Player personality affects negotiation
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.contracts.market_value import calculate_market_value, MarketValue

if TYPE_CHECKING:
    from huddle.core.models.player import Player


class NegotiationResult(Enum):
    """Outcome of a contract negotiation round."""
    ACCEPTED = auto()      # Player accepts the offer
    COUNTER_OFFER = auto() # Player counters with different terms
    REJECTED = auto()      # Player rejects but willing to keep talking
    WALK_AWAY = auto()     # Player ends negotiations entirely


class NegotiationTone(Enum):
    """How the player/agent responds (affects message flavor)."""
    ENTHUSIASTIC = auto()  # Loves the team, willing to take less
    PROFESSIONAL = auto()  # Business-like, fair negotiations
    DEMANDING = auto()     # Wants top dollar, aggressive counters
    INSULTED = auto()      # Lowballed, may walk away


@dataclass
class ContractOffer:
    """
    A contract offer in negotiation.

    All monetary values in thousands (e.g., 15000 = $15M).
    """
    years: int
    salary: int           # Annual salary
    signing_bonus: int    # Total signing bonus

    @property
    def total_value(self) -> int:
        """Total contract value."""
        return self.salary * self.years + self.signing_bonus

    @property
    def guaranteed(self) -> int:
        """Guaranteed money (bonus + portion of salary)."""
        return self.signing_bonus + (self.salary // 2)

    @property
    def cap_hit_year1(self) -> int:
        """First year cap impact."""
        return self.salary + (self.signing_bonus // self.years)

    def to_dict(self) -> dict:
        return {
            "years": self.years,
            "salary": self.salary,
            "signing_bonus": self.signing_bonus,
            "total_value": self.total_value,
            "guaranteed": self.guaranteed,
        }


@dataclass
class NegotiationResponse:
    """
    Response from a negotiation round.

    Contains the result, any counter-offer, and flavor text.
    """
    result: NegotiationResult
    tone: NegotiationTone
    message: str
    counter_offer: Optional[ContractOffer] = None

    # Tracking
    offer_pct_of_market: float = 0.0  # How the offer compared to market
    walk_away_chance: float = 0.0     # Probability of walk-away if rejected


@dataclass
class NegotiationState:
    """
    Tracks the state of an ongoing negotiation.
    """
    player_id: str
    player_name: str
    player_position: str
    player_overall: int

    market_value: MarketValue

    # History
    rounds: int = 0
    offers_made: list[ContractOffer] = None
    best_offer: Optional[ContractOffer] = None

    # Player stance
    current_demand: Optional[ContractOffer] = None
    patience: float = 1.0  # Decreases with lowball offers

    # Outcome
    is_complete: bool = False
    final_result: Optional[NegotiationResult] = None
    agreed_contract: Optional[ContractOffer] = None

    def __post_init__(self):
        if self.offers_made is None:
            self.offers_made = []


def start_negotiation(player: "Player") -> NegotiationState:
    """
    Start a new contract negotiation with a player.

    Returns the initial negotiation state including player's
    market value and opening demands.
    """
    market = calculate_market_value(player)

    # Player's opening demand is slightly above market (agents inflate)
    demand_multiplier = random.uniform(1.05, 1.20)  # 5-20% above market

    opening_demand = ContractOffer(
        years=market.years,
        salary=int(market.base_salary * demand_multiplier),
        signing_bonus=int(market.signing_bonus * demand_multiplier),
    )

    return NegotiationState(
        player_id=str(player.id),
        player_name=player.full_name,
        player_position=player.position.value,
        player_overall=player.overall,
        market_value=market,
        current_demand=opening_demand,
        patience=1.0,
    )


def evaluate_offer(
    state: NegotiationState,
    offer: ContractOffer,
) -> NegotiationResponse:
    """
    Evaluate a contract offer and return the player's response.

    The response depends on:
    - How offer compares to market value
    - Number of negotiation rounds
    - Player's remaining patience
    """
    state.rounds += 1
    state.offers_made.append(offer)

    # Track best offer
    if state.best_offer is None or offer.total_value > state.best_offer.total_value:
        state.best_offer = offer

    market = state.market_value

    # Calculate offer as percentage of market value
    offer_pct = offer.total_value / market.total_value if market.total_value > 0 else 1.0

    # Thresholds for different responses
    # These create the HC09-style negotiation feel
    ACCEPT_THRESHOLD = 0.95      # 95%+ of market = likely accept
    COUNTER_LOW = 0.80          # 80-95% = counter offer
    REJECT_LOW = 0.70           # 70-80% = reject but continue
    WALKAWAY_THRESHOLD = 0.60   # <60% = risk walking away

    # Adjust thresholds based on rounds (player gets more flexible)
    flexibility_bonus = min(0.10, state.rounds * 0.02)  # Up to 10% more flexible

    accept_threshold = ACCEPT_THRESHOLD - flexibility_bonus

    # Determine response
    if offer_pct >= accept_threshold:
        return _accept_offer(state, offer, offer_pct)

    elif offer_pct >= COUNTER_LOW:
        return _counter_offer(state, offer, offer_pct)

    elif offer_pct >= REJECT_LOW:
        return _reject_offer(state, offer, offer_pct)

    else:
        return _maybe_walk_away(state, offer, offer_pct)


def _accept_offer(
    state: NegotiationState,
    offer: ContractOffer,
    offer_pct: float,
) -> NegotiationResponse:
    """Player accepts the offer."""
    state.is_complete = True
    state.final_result = NegotiationResult.ACCEPTED
    state.agreed_contract = offer

    # Generate acceptance message
    if offer_pct >= 1.05:
        tone = NegotiationTone.ENTHUSIASTIC
        messages = [
            f"{state.player_name} is thrilled with this offer and accepts immediately!",
            f"{state.player_name}'s agent: 'We have a deal! {state.player_name} is excited to be here.'",
            f"{state.player_name} accepts! This is exactly what we were looking for.",
        ]
    elif offer_pct >= 0.98:
        tone = NegotiationTone.ENTHUSIASTIC
        messages = [
            f"{state.player_name} accepts the offer. 'This feels like the right fit.'",
            f"{state.player_name}'s agent: 'We're happy with these terms. Deal.'",
            f"{state.player_name} is pleased to accept and join the team.",
        ]
    else:
        tone = NegotiationTone.PROFESSIONAL
        messages = [
            f"{state.player_name} accepts after careful consideration.",
            f"{state.player_name}'s agent: 'We can work with this. You have a deal.'",
            f"After {state.rounds} round(s), {state.player_name} agrees to terms.",
        ]

    return NegotiationResponse(
        result=NegotiationResult.ACCEPTED,
        tone=tone,
        message=random.choice(messages),
        offer_pct_of_market=offer_pct,
    )


def _counter_offer(
    state: NegotiationState,
    offer: ContractOffer,
    offer_pct: float,
) -> NegotiationResponse:
    """Player makes a counter-offer."""
    market = state.market_value

    # Counter-offer is between their demand and market value
    # The closer the offer is to market, the more they'll come down
    gap = 1.0 - offer_pct

    # Player comes down by 30-60% of the gap
    concession = gap * random.uniform(0.30, 0.60)
    counter_pct = max(offer_pct + concession, 0.95)  # Won't go below 95% of market

    counter = ContractOffer(
        years=offer.years,  # Usually match years
        salary=int(market.base_salary * counter_pct),
        signing_bonus=int(market.signing_bonus * counter_pct),
    )

    state.current_demand = counter

    # Generate counter message
    if offer_pct >= 0.90:
        tone = NegotiationTone.PROFESSIONAL
        messages = [
            f"{state.player_name}'s agent: 'We're close. Can you get to ${counter.salary:,}K per year?'",
            f"Agent: 'Good offer, but {state.player_name} is looking for ${counter.total_value:,}K total.'",
            f"'We appreciate the offer. Meet us at ${counter.salary:,}K and we have a deal.'",
        ]
    else:
        tone = NegotiationTone.DEMANDING
        messages = [
            f"{state.player_name}'s agent counters: {counter.years}yr/${counter.total_value:,}K.",
            f"Agent: '{state.player_name} knows his worth. We need ${counter.salary:,}K per year.'",
            f"'That's below market. We're looking at ${counter.salary:,}K minimum.'",
        ]

    return NegotiationResponse(
        result=NegotiationResult.COUNTER_OFFER,
        tone=tone,
        message=random.choice(messages),
        counter_offer=counter,
        offer_pct_of_market=offer_pct,
    )


def _reject_offer(
    state: NegotiationState,
    offer: ContractOffer,
    offer_pct: float,
) -> NegotiationResponse:
    """Player rejects but is willing to continue negotiating."""
    market = state.market_value

    # Decrease patience
    state.patience -= 0.15

    # Tell them what they need to come up to
    target = ContractOffer(
        years=offer.years,
        salary=market.base_salary,
        signing_bonus=market.signing_bonus,
    )

    tone = NegotiationTone.DEMANDING
    messages = [
        f"{state.player_name}'s agent: 'We're too far apart. Need to see ${target.salary:,}K per year.'",
        f"Agent: 'Not even close. {state.player_name} won't consider anything under ${target.total_value:,}K total.'",
        f"'That offer is insulting. Come back when you're serious - we need ${target.salary:,}K.'",
    ]

    return NegotiationResponse(
        result=NegotiationResult.REJECTED,
        tone=tone,
        message=random.choice(messages),
        counter_offer=target,  # Show them what to aim for
        offer_pct_of_market=offer_pct,
    )


def _maybe_walk_away(
    state: NegotiationState,
    offer: ContractOffer,
    offer_pct: float,
) -> NegotiationResponse:
    """Player might walk away from a lowball offer."""
    # Calculate walk-away chance
    # Very low offers have high chance, especially with low patience
    base_walkaway = (0.60 - offer_pct) * 2  # 0-60% becomes 0-120% base
    patience_factor = 1.0 - state.patience  # Low patience = more likely to walk

    walkaway_chance = min(0.80, base_walkaway + patience_factor * 0.3)

    # Roll for walk-away
    if random.random() < walkaway_chance:
        state.is_complete = True
        state.final_result = NegotiationResult.WALK_AWAY

        tone = NegotiationTone.INSULTED
        messages = [
            f"{state.player_name}'s agent: 'This is a waste of time. We're done here.'",
            f"Agent hangs up: '{state.player_name} will not be disrespected like this.'",
            f"'That offer is an insult. {state.player_name} is no longer interested.'",
            f"Negotiations have broken down. {state.player_name} will explore other options.",
        ]

        return NegotiationResponse(
            result=NegotiationResult.WALK_AWAY,
            tone=tone,
            message=random.choice(messages),
            offer_pct_of_market=offer_pct,
            walk_away_chance=walkaway_chance,
        )

    # Didn't walk away, but very upset - reject harshly
    state.patience -= 0.25  # Big patience hit

    market = state.market_value
    target = ContractOffer(
        years=offer.years,
        salary=int(market.base_salary * 1.05),  # Demand MORE after lowball
        signing_bonus=int(market.signing_bonus * 1.05),
    )

    tone = NegotiationTone.INSULTED
    messages = [
        f"{state.player_name}'s agent is furious: 'That's insulting. We need ${target.salary:,}K or we walk.'",
        f"Agent: 'Are you serious? {state.player_name} is worth ${target.total_value:,}K minimum.'",
        f"'Don't waste our time. Come back with a real offer or we're done.'",
    ]

    return NegotiationResponse(
        result=NegotiationResult.REJECTED,
        tone=tone,
        message=random.choice(messages),
        counter_offer=target,
        offer_pct_of_market=offer_pct,
        walk_away_chance=walkaway_chance,
    )


def quick_negotiate(
    player: "Player",
    offer: ContractOffer,
) -> NegotiationResponse:
    """
    One-shot negotiation for simple cases.

    Evaluates a single offer without tracking state.
    Good for AI team decisions or quick checks.
    """
    state = start_negotiation(player)
    return evaluate_offer(state, offer)
