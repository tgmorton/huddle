"""
AI Contract Decision Making.

Provides AI logic for CPU teams to make contract decisions:
- Evaluate whether to pursue a free agent
- Generate offers based on team tendencies
- Respond to counter-offers
- Determine when to walk away
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.contracts.market_value import calculate_market_value, MarketValue
from huddle.core.contracts.negotiation import (
    ContractOffer,
    NegotiationState,
    NegotiationResponse,
    NegotiationResult,
    evaluate_offer,
    start_negotiation,
)
from huddle.core.models.tendencies import NegotiationTone, CapManagement

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team import Team


@dataclass
class AIEvaluation:
    """
    AI team's evaluation of a player for signing.

    Contains the decision and reasoning.
    """
    interested: bool
    interest_score: float   # 0.0 to 1.0, how much they want this player
    max_offer_pct: float    # Max % of market they'll pay
    opening_offer_pct: float  # Starting offer % of market
    reason: str


@dataclass
class AIOfferDecision:
    """
    AI team's decision about what offer to make.
    """
    will_offer: bool
    offer: Optional[ContractOffer]
    reason: str


def evaluate_free_agent(
    team: "Team",
    player: "Player",
    position_need: float = 0.5,  # 0.0 = don't need, 1.0 = desperate need
) -> AIEvaluation:
    """
    Evaluate whether an AI team should pursue a free agent.

    Considers:
    - Team's cap situation
    - Team's negotiation tendencies
    - Position need
    - Player quality
    """
    tendencies = team.tendencies
    cap_room = team.cap_room
    market = calculate_market_value(player)

    # Check if team can afford at all
    if cap_room < market.base_salary * 0.7:  # Can't even afford 70% of market
        return AIEvaluation(
            interested=False,
            interest_score=0.0,
            max_offer_pct=0.0,
            opening_offer_pct=0.0,
            reason="Insufficient cap space",
        )

    # Calculate base interest from player quality and need
    quality_score = player.overall / 100.0
    interest_score = (quality_score * 0.6) + (position_need * 0.4)

    # Adjust based on cap management style
    if tendencies.cap_management == CapManagement.THRIFTY:
        # Thrifty teams are less interested unless great value
        interest_score *= 0.7
        max_offer_pct = 0.85  # Won't go above 85% of market
        if player.overall < 80:
            opening_offer_pct = 0.65
        else:
            opening_offer_pct = 0.75
    elif tendencies.cap_management == CapManagement.SPEND_TO_CAP:
        # Aggressive spenders pursue anyone they need
        interest_score *= 1.2
        max_offer_pct = 1.15  # Will overpay 15% for targets
        opening_offer_pct = 0.95
    else:  # MODERATE
        max_offer_pct = 1.0  # Up to market value
        opening_offer_pct = 0.85

    # Adjust based on negotiation tone
    if tendencies.negotiation_tone == NegotiationTone.LOWBALL:
        opening_offer_pct *= 0.85  # Start even lower
        max_offer_pct *= 0.90  # Cap at 90% of normal max
    elif tendencies.negotiation_tone == NegotiationTone.OVERPAY:
        opening_offer_pct *= 1.10  # Start higher
        max_offer_pct *= 1.10  # Go 10% higher
    elif tendencies.negotiation_tone == NegotiationTone.FAIR:
        opening_offer_pct = max(opening_offer_pct, 0.90)  # At least 90%

    # Position value adjustment (research-backed)
    # Low-value positions (RB, FB) should get lower offers
    # High-value positions (QB, EDGE) can command higher offers
    # Lazy import to avoid circular dependency
    from huddle.generators.calibration import get_position_multiplier, is_market_inefficient

    position = player.position.value
    pos_mult = get_position_multiplier(position)

    # Map position multiplier (0.2-5.0) to offer adjustment (0.85-1.10)
    # This prevents overpaying for low-value positions
    if pos_mult < 1.0:
        # Low-value positions: reduce max offer
        # RB (0.6) -> 0.92x, FB (0.4) -> 0.88x
        pos_offer_adj = 0.85 + (pos_mult * 0.15)
    elif pos_mult > 2.0:
        # High-value positions: slightly increase max offer
        # QB (5.0) -> 1.08x, DE (2.5) -> 1.03x
        pos_offer_adj = 1.0 + min(0.10, (pos_mult - 2.0) * 0.03)
    else:
        pos_offer_adj = 1.0

    max_offer_pct *= pos_offer_adj

    # Market inefficiency warning - be cautious about FA spending
    if is_market_inefficient(position) and max_offer_pct > 1.0:
        # Don't overpay for positions where FA spending doesn't predict wins
        max_offer_pct = min(max_offer_pct, 1.0)

    # Interest threshold
    interested = interest_score >= 0.4

    # Generate reason
    if not interested:
        if position_need < 0.3:
            reason = "Position not a priority"
        elif quality_score < 0.7:
            reason = "Player quality below standards"
        else:
            reason = "Other priorities"
    else:
        if position_need > 0.7:
            reason = f"High priority target for {player.position.value}"
        elif quality_score > 0.85:
            reason = f"Elite talent at {player.position.value}"
        else:
            reason = f"Quality depth option at {player.position.value}"

    return AIEvaluation(
        interested=interested,
        interest_score=min(1.0, interest_score),
        max_offer_pct=max_offer_pct,
        opening_offer_pct=opening_offer_pct,
        reason=reason,
    )


def generate_opening_offer(
    team: "Team",
    player: "Player",
    evaluation: AIEvaluation,
) -> AIOfferDecision:
    """
    Generate the AI team's opening contract offer.
    """
    if not evaluation.interested:
        return AIOfferDecision(
            will_offer=False,
            offer=None,
            reason=evaluation.reason,
        )

    market = calculate_market_value(player)

    # Check cap room
    min_salary = int(market.base_salary * evaluation.opening_offer_pct)
    if not team.can_afford(min_salary):
        return AIOfferDecision(
            will_offer=False,
            offer=None,
            reason="Cannot afford minimum offer",
        )

    # Generate offer
    offer = ContractOffer(
        years=market.years,
        salary=int(market.base_salary * evaluation.opening_offer_pct),
        signing_bonus=int(market.signing_bonus * evaluation.opening_offer_pct),
    )

    return AIOfferDecision(
        will_offer=True,
        offer=offer,
        reason=f"Offering {evaluation.opening_offer_pct*100:.0f}% of market value",
    )


def respond_to_counter(
    team: "Team",
    player: "Player",
    evaluation: AIEvaluation,
    counter: ContractOffer,
    current_offer: ContractOffer,
    round_num: int,
) -> AIOfferDecision:
    """
    AI decides how to respond to a player's counter-offer.

    May:
    - Accept the counter
    - Make a higher offer
    - Walk away
    """
    market = calculate_market_value(player)
    tendencies = team.tendencies

    counter_pct = counter.total_value / market.total_value if market.total_value > 0 else 1.0
    current_pct = current_offer.total_value / market.total_value if market.total_value > 0 else 0.0

    # Calculate max we'll go based on evaluation
    max_pct = evaluation.max_offer_pct

    # Check if counter is within our max
    if counter_pct <= max_pct:
        # We can afford to match or close to their counter
        if not team.can_afford(counter.salary):
            return AIOfferDecision(
                will_offer=False,
                offer=None,
                reason="Counter exceeds available cap",
            )

        # Decide whether to accept or counter
        # The closer to our max, the more likely to just accept
        accept_probability = (counter_pct / max_pct) ** 2  # Quadratic - more likely near max

        if random.random() < accept_probability or round_num >= 4:
            # Accept their counter
            return AIOfferDecision(
                will_offer=True,
                offer=counter,
                reason="Accepting player's counter-offer",
            )
        else:
            # Make a counter between our current and their demand
            new_pct = (current_pct + counter_pct) / 2
            new_pct = min(new_pct, max_pct)  # Don't exceed our max

            new_offer = ContractOffer(
                years=market.years,
                salary=int(market.base_salary * new_pct),
                signing_bonus=int(market.signing_bonus * new_pct),
            )

            return AIOfferDecision(
                will_offer=True,
                offer=new_offer,
                reason=f"Counter-offering at {new_pct*100:.0f}% of market",
            )

    else:
        # Counter exceeds our max - need to decide if we walk or make final offer

        # Calculate how much over our max they're asking
        over_max = counter_pct - max_pct

        # Walk away probability increases with how much over max
        walk_probability = min(0.8, over_max * 4)  # 25% over = 100% walk

        # Adjust for negotiation tone
        if tendencies.negotiation_tone == NegotiationTone.LOWBALL:
            walk_probability += 0.2  # More likely to walk
        elif tendencies.negotiation_tone == NegotiationTone.OVERPAY:
            walk_probability -= 0.3  # Less likely to walk

        walk_probability = max(0.1, min(0.9, walk_probability))

        if random.random() < walk_probability:
            return AIOfferDecision(
                will_offer=False,
                offer=None,
                reason=f"Player's demands ({counter_pct*100:.0f}%) exceed maximum ({max_pct*100:.0f}%)",
            )
        else:
            # Make final offer at our max
            final_offer = ContractOffer(
                years=market.years,
                salary=int(market.base_salary * max_pct),
                signing_bonus=int(market.signing_bonus * max_pct),
            )

            if not team.can_afford(final_offer.salary):
                return AIOfferDecision(
                    will_offer=False,
                    offer=None,
                    reason="Cannot afford to match counter",
                )

            return AIOfferDecision(
                will_offer=True,
                offer=final_offer,
                reason=f"Final offer at maximum ({max_pct*100:.0f}%)",
            )


def run_ai_negotiation(
    team: "Team",
    player: "Player",
    position_need: float = 0.5,
    max_rounds: int = 5,
) -> tuple[bool, Optional[ContractOffer], list[str]]:
    """
    Run a complete AI-driven negotiation with a player.

    Returns:
        (success, final_contract, negotiation_log)
    """
    log = []

    # Evaluate interest
    evaluation = evaluate_free_agent(team, player, position_need)
    log.append(f"AI evaluation: {evaluation.reason}")

    if not evaluation.interested:
        log.append("AI not interested in pursuing")
        return (False, None, log)

    # Start negotiation
    state = start_negotiation(player)
    log.append(f"Player demands: ${state.current_demand.total_value:,}K total")

    # Generate opening offer
    decision = generate_opening_offer(team, player, evaluation)
    if not decision.will_offer:
        log.append(f"AI won't offer: {decision.reason}")
        return (False, None, log)

    current_offer = decision.offer
    log.append(f"AI opening offer: ${current_offer.total_value:,}K")

    # Negotiation rounds
    round_num = 0
    while round_num < max_rounds and not state.is_complete:
        round_num += 1

        # Player evaluates offer
        response = evaluate_offer(state, current_offer)
        log.append(f"Round {round_num}: {response.result.name} - {response.message}")

        if response.result == NegotiationResult.ACCEPTED:
            log.append(f"Contract agreed: ${current_offer.total_value:,}K")
            return (True, current_offer, log)

        elif response.result == NegotiationResult.WALK_AWAY:
            log.append("Player walked away from negotiations")
            return (False, None, log)

        elif response.result in (NegotiationResult.COUNTER_OFFER, NegotiationResult.REJECTED):
            if response.counter_offer:
                # AI decides response
                ai_decision = respond_to_counter(
                    team, player, evaluation,
                    response.counter_offer, current_offer, round_num
                )

                if not ai_decision.will_offer:
                    log.append(f"AI walks away: {ai_decision.reason}")
                    return (False, None, log)

                current_offer = ai_decision.offer
                log.append(f"AI counter: ${current_offer.total_value:,}K ({ai_decision.reason})")

    # Ran out of rounds
    log.append("Negotiations stalled - no agreement reached")
    return (False, None, log)


def calculate_team_position_need(team: "Team", position: str) -> float:
    """
    Calculate how much a team needs a specific position.

    Returns 0.0 (don't need) to 1.0 (desperate need).
    """
    from huddle.core.enums import Position

    # Get current players at position
    try:
        pos_enum = Position(position)
    except ValueError:
        return 0.5  # Unknown position, assume moderate need

    players_at_pos = team.roster.get_players_by_position(pos_enum)

    if not players_at_pos:
        return 1.0  # No players = desperate need

    # Calculate need based on quantity and quality
    best_overall = max(p.overall for p in players_at_pos)
    num_players = len(players_at_pos)

    # Starter quality thresholds
    ELITE_THRESHOLD = 90
    STARTER_THRESHOLD = 80
    BACKUP_THRESHOLD = 70

    if best_overall >= ELITE_THRESHOLD:
        # Have an elite player, low need
        need = 0.2
    elif best_overall >= STARTER_THRESHOLD:
        # Have a starter, moderate need for depth/upgrade
        need = 0.4
    elif best_overall >= BACKUP_THRESHOLD:
        # Only have backup quality, higher need
        need = 0.7
    else:
        # Below backup quality, high need
        need = 0.9

    # Adjust for depth
    if num_players <= 1:
        need += 0.2  # Need depth
    elif num_players >= 3:
        need -= 0.1  # Good depth

    return max(0.0, min(1.0, need))
