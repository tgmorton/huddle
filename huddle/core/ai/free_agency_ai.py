"""
Free Agency AI System.

Autonomous free agent decision-making for AI-controlled teams.

Handles:
- Free agent prioritization
- Contract offer generation
- Re-signing own players
- Market value assessment
- Research-backed position priority (Calvetti framework)
- GM archetype personality integration
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    FreeAgencyPhilosophy,
)
from huddle.core.contracts.market_value import calculate_market_value
from huddle.core.ai.allocation_tables import (
    get_position_priority,
    should_draft_position,
    get_allocation_gap,
    get_rookie_premium,
)
from huddle.core.ai.gm_archetypes import (
    GMArchetype,
    GMProfile,
    get_gm_profile,
)

# Map specific positions to research position groups
POSITION_TO_GROUP = {
    # Offense
    "QB": ("QB", "offense"),
    "RB": ("RB", "offense"),
    "FB": ("RB", "offense"),
    "WR": ("WR", "offense"),
    "TE": ("TE", "offense"),
    "LT": ("OL", "offense"),
    "LG": ("OL", "offense"),
    "C": ("OL", "offense"),
    "RG": ("OL", "offense"),
    "RT": ("OL", "offense"),
    # Defense
    "DE": ("EDGE", "defense"),
    "EDGE": ("EDGE", "defense"),
    "DT": ("DL", "defense"),
    "NT": ("DL", "defense"),
    "OLB": ("LB", "defense"),
    "ILB": ("LB", "defense"),
    "MLB": ("LB", "defense"),
    "LB": ("LB", "defense"),
    "CB": ("CB", "defense"),
    "FS": ("S", "defense"),
    "SS": ("S", "defense"),
    "S": ("S", "defense"),
}

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team_identity import TeamIdentity
    from huddle.core.contracts.contract import Contract


@dataclass
class FreeAgentEvaluation:
    """Evaluation of a free agent."""
    player_id: str
    player_name: str
    position: str
    age: int
    overall: int

    # Evaluation scores
    talent_score: float       # Raw ability
    fit_score: float          # Team scheme fit
    need_score: float         # Position need
    value_score: float        # Contract value

    # Market info
    market_value: int         # Expected contract value
    max_offer: int            # Max this team would offer

    # Priority
    priority: float = 0.0     # Overall priority for signing

    def __post_init__(self):
        if self.priority == 0:
            self._calculate_priority()

    def _calculate_priority(self):
        """Calculate signing priority."""
        self.priority = (
            self.talent_score * 0.35 +
            self.fit_score * 0.15 +
            self.need_score * 0.30 +
            self.value_score * 0.20
        )


@dataclass
class ContractOfferResult:
    """Result of generating a contract offer."""
    player_id: str
    years: int
    total_value: int
    guaranteed: int
    signing_bonus: int
    offer_type: str  # "market", "premium", "discount", "max"


class FreeAgencyAI:
    """
    AI system for free agency decisions.

    Integrates with team identity, status, and needs to make
    contextually appropriate signing decisions.

    Now includes:
    - Research-backed position priority (Calvetti framework)
    - GM archetype personality modifiers
    - FA premium for positions that should be signed in FA (not drafted)
    """

    def __init__(
        self,
        team_id: str,
        team_identity: "TeamIdentity",
        team_status: TeamStatusState,
        cap_space: int,
        team_needs: dict[str, float],
        gm_archetype: GMArchetype = None,
    ):
        self.team_id = team_id
        self.identity = team_identity
        self.status = team_status
        self.cap_space = cap_space
        self.needs = team_needs

        # GM archetype for personality-based adjustments
        self.gm_archetype = gm_archetype or GMArchetype.BALANCED
        self.gm_profile = get_gm_profile(self.gm_archetype)

        # Configure based on team philosophy
        self._configure_behavior()

        # Apply GM archetype modifiers
        self._apply_gm_modifiers()

    def _apply_gm_modifiers(self):
        """Adjust behavior based on GM archetype."""
        # GM rookie preference inversely affects FA spending
        # Cap Wizard (2.0 rookie pref) spends less in FA
        # Win Now (0.6 rookie pref) spends more in FA
        if self.gm_profile.rookie_premium < 0.8:
            # Low rookie preference = more aggressive in FA
            self.spending_multiplier *= 1.15
        elif self.gm_profile.rookie_premium > 1.2:
            # High rookie preference = conservative in FA
            self.spending_multiplier *= 0.90

    def _configure_behavior(self):
        """Set behavior parameters based on team identity."""
        self.spending_multiplier = 1.0
        self.years_preference = 0  # Positive = longer, negative = shorter

        # Handle None identity (use defaults)
        if self.identity is None:
            return

        # Free agency philosophy
        if self.identity.free_agency_philosophy == FreeAgencyPhilosophy.BIG_SPENDER:
            self.spending_multiplier = 1.2
            self.years_preference = 1
        elif self.identity.free_agency_philosophy == FreeAgencyPhilosophy.BARGAIN_HUNTER:
            self.spending_multiplier = 0.8
            self.years_preference = -1

        # Team status adjustments
        status = self.status.current_status

        if status == TeamStatus.DYNASTY:
            self.spending_multiplier *= 1.1
            self.years_preference += 1
        elif status == TeamStatus.CONTENDING:
            self.spending_multiplier *= 1.15
        elif status == TeamStatus.WINDOW_CLOSING:
            self.spending_multiplier *= 1.25  # Desperate
            self.years_preference -= 1  # Short deals
        elif status == TeamStatus.REBUILDING:
            self.spending_multiplier *= 0.7
            self.years_preference -= 2  # Short deals only
        elif status == TeamStatus.MISMANAGED:
            self.spending_multiplier *= 0.6  # Cap constraints

    def evaluate_free_agent(
        self,
        player: "Player",
    ) -> FreeAgentEvaluation:
        """
        Evaluate a free agent for potential signing.

        Args:
            player: The free agent

        Returns:
            FreeAgentEvaluation with all scores
        """
        # Talent score from overall
        talent_score = player.overall / 100

        # Fit score from scheme
        fit_score = self._calculate_fit(player)

        # Need score from position needs
        need_score = self.needs.get(player.position.value, 0.3)

        # Get market value
        market = calculate_market_value(player)
        market_value = market.total_value

        # Value score - compare talent to cost
        expected_cost_per_point = market_value / max(1, player.overall - 50)
        value_score = max(0.2, 1.0 - (expected_cost_per_point / 500))

        # Max offer based on cap space and need
        max_offer = self._calculate_max_offer(player, market_value)

        return FreeAgentEvaluation(
            player_id=str(player.id),
            player_name=player.full_name,
            position=player.position.value,
            age=player.age,
            overall=player.overall,
            talent_score=talent_score,
            fit_score=fit_score,
            need_score=need_score,
            value_score=value_score,
            market_value=market_value,
            max_offer=max_offer,
        )

    def _calculate_fit(self, player: "Player") -> float:
        """Calculate scheme fit for a player."""
        # Handle None identity
        if self.identity is None:
            return 0.5

        # Get attribute emphasis from team identity
        emphasis = self.identity.get_attribute_emphasis(player.position.value)

        if not emphasis:
            return 0.5

        fit_score = 0.5
        for attr, mult in emphasis.items():
            attr_value = player.attributes.get(attr, 50)
            if mult > 1.0 and attr_value >= 75:
                fit_score += 0.1
            elif mult > 1.0 and attr_value < 60:
                fit_score -= 0.1

        return max(0.0, min(1.0, fit_score))

    def _calculate_max_offer(
        self,
        player: "Player",
        market_value: int,
    ) -> int:
        """
        Calculate maximum offer for a player.

        Includes research-backed FA premium for positions that should
        be signed in FA rather than drafted (RB, CB).
        """
        position = player.position.value

        # Base: market value adjusted by spending multiplier
        base_max = int(market_value * self.spending_multiplier)

        # Cap by available space (can use up to 50% of space on one player)
        cap_max = self.cap_space // 2

        # Premium for high need
        need = self.needs.get(position, 0.3)
        if need > 0.7:
            base_max = int(base_max * 1.15)

        # Research-backed FA premium
        # Positions where rookies underperform (RB, CB) should be signed in FA
        group, side = POSITION_TO_GROUP.get(position, (position, "offense"))
        if not should_draft_position(group, side):
            # Research says this position is better to sign in FA
            # Pay up to 15% more for RB, CB in free agency
            base_max = int(base_max * 1.15)

        # GM archetype position adjustment
        gm_position_adj = self.gm_profile.position_adjustments.get(position, 1.0)
        base_max = int(base_max * gm_position_adj)

        # Penalty for older players
        if player.age > 30:
            base_max = int(base_max * 0.85)

        return min(base_max, cap_max)

    def rank_free_agents(
        self,
        free_agents: list["Player"],
    ) -> list[FreeAgentEvaluation]:
        """
        Rank free agents by priority for signing.

        Returns sorted list of evaluations, highest priority first.
        """
        evaluations = [
            self.evaluate_free_agent(p) for p in free_agents
        ]

        # Filter out unaffordable players
        evaluations = [e for e in evaluations if e.max_offer >= e.market_value * 0.7]

        # Sort by priority
        evaluations.sort(key=lambda e: e.priority, reverse=True)

        return evaluations

    def generate_offer(
        self,
        player: "Player",
        competing_offers: list[int] = None,
    ) -> Optional[ContractOfferResult]:
        """
        Generate a contract offer for a free agent.

        Args:
            player: The free agent
            competing_offers: Total values of competing offers

        Returns:
            ContractOfferResult or None if not interested
        """
        eval = self.evaluate_free_agent(player)

        # Not interested if priority too low
        if eval.priority < 0.3:
            return None

        # Can't afford
        if eval.max_offer < eval.market_value * 0.7:
            return None

        market = calculate_market_value(player)

        # Determine offer type
        if competing_offers and max(competing_offers) > eval.market_value:
            # Need to beat competition
            offer_type = "premium"
            total_value = min(eval.max_offer, int(max(competing_offers) * 1.05))
        elif eval.need_score > 0.7:
            # High need, pay up
            offer_type = "premium"
            total_value = int(eval.market_value * 1.1 * self.spending_multiplier)
        elif eval.priority > 0.7:
            # Really want this player
            offer_type = "market"
            total_value = int(eval.market_value * self.spending_multiplier)
        else:
            # Try to get a discount
            offer_type = "discount"
            total_value = int(eval.market_value * 0.85 * self.spending_multiplier)

        # Cap at max offer
        total_value = min(total_value, eval.max_offer)

        # Determine years
        base_years = market.years + self.years_preference
        years = max(1, min(5, base_years))

        # Adjust for age
        if player.age > 30:
            years = min(years, 3)
        if player.age > 33:
            years = min(years, 2)

        # Structure the deal
        signing_bonus = int(total_value * 0.25)
        guaranteed = int(total_value * 0.50)

        return ContractOfferResult(
            player_id=str(player.id),
            years=years,
            total_value=total_value,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
            offer_type=offer_type,
        )

    def should_resign_player(
        self,
        player: "Player",
        current_contract: "Contract",
    ) -> tuple[bool, Optional[ContractOfferResult]]:
        """
        Decide whether to re-sign an expiring player.

        Args:
            player: Player with expiring contract
            current_contract: Their current contract

        Returns:
            (should_resign, offer) tuple
        """
        eval = self.evaluate_free_agent(player)

        # Always try to keep high performers
        if player.overall >= 85:
            return True, self.generate_offer(player)

        # Keep if good value and need
        if eval.priority > 0.5 and eval.value_score > 0.5:
            return True, self.generate_offer(player)

        # Keep young players with potential
        if player.age <= 26 and player.overall >= 72:
            return True, self.generate_offer(player)

        # Status affects retention
        if self.status.current_status == TeamStatus.REBUILDING:
            # Only keep young guys
            if player.age > 27:
                return False, None

        return False, None

    def prioritize_positions(self) -> list[str]:
        """
        Get positions in priority order for FA spending.

        Uses research-backed position priority based on:
        - Current roster strengths and weaknesses
        - Position synergies (strong QB → invest in OL)
        - FA vs draft recommendations

        Returns list of positions from highest to lowest priority.
        """
        # Identify strong and weak positions from needs
        strong_positions = [pos for pos, need in self.needs.items() if need < 0.3]
        weak_positions = [pos for pos, need in self.needs.items() if need > 0.7]

        # Map to research position groups
        strong_groups = []
        weak_groups = []
        for pos in strong_positions:
            group, side = POSITION_TO_GROUP.get(pos, (pos, "offense"))
            if group not in strong_groups:
                strong_groups.append(group)
        for pos in weak_positions:
            group, side = POSITION_TO_GROUP.get(pos, (pos, "offense"))
            if group not in weak_groups:
                weak_groups.append(group)

        # Get research-backed priority for offense and defense
        offense_priority = get_position_priority(
            [g for g in strong_groups if POSITION_TO_GROUP.get(g, (g, "offense"))[1] == "offense"],
            [g for g in weak_groups if POSITION_TO_GROUP.get(g, (g, "offense"))[1] == "offense"],
            "offense"
        )
        defense_priority = get_position_priority(
            [g for g in strong_groups if POSITION_TO_GROUP.get(g, (g, "defense"))[1] == "defense"],
            [g for g in weak_groups if POSITION_TO_GROUP.get(g, (g, "defense"))[1] == "defense"],
            "defense"
        )

        # Combine into specific positions, prioritizing high-need
        all_positions = list(self.needs.keys())

        def priority(pos):
            need = self.needs.get(pos, 0.3)
            group, side = POSITION_TO_GROUP.get(pos, (pos, "offense"))

            # Base priority from research
            priority_list = offense_priority if side == "offense" else defense_priority
            if group in priority_list:
                research_rank = len(priority_list) - priority_list.index(group)
            else:
                research_rank = 0

            # Boost for positions better to sign in FA (not draft)
            fa_boost = 0.1 if not should_draft_position(group, side) else 0

            # GM archetype adjustment
            gm_adj = self.gm_profile.position_adjustments.get(pos, 1.0) - 1.0

            # Combined score
            return need + (research_rank * 0.05) + fa_boost + (gm_adj * 0.1)

        all_positions.sort(key=priority, reverse=True)
        return all_positions


def simulate_free_agency_market(
    free_agents: list["Player"],
    teams_with_ai: list[tuple[str, FreeAgencyAI]],
    num_days: int = 14,
) -> dict[str, str]:
    """
    Simulate free agency market with multiple teams bidding.

    Args:
        free_agents: Available free agents
        teams_with_ai: List of (team_id, FreeAgencyAI) tuples
        num_days: Days of free agency to simulate

    Returns:
        Dict mapping player_id -> team_id that signed them
    """
    signings: dict[str, str] = {}
    remaining_fas = list(free_agents)

    for day in range(num_days):
        if not remaining_fas:
            break

        # Each team makes offers
        daily_offers: dict[str, list[tuple[str, ContractOfferResult]]] = {}

        for team_id, ai in teams_with_ai:
            # Update AI cap space (simplified)
            rankings = ai.rank_free_agents(remaining_fas)

            # Make offer to top target
            for eval in rankings[:3]:  # Top 3 targets
                player = next(
                    (p for p in remaining_fas if str(p.id) == eval.player_id),
                    None
                )
                if not player:
                    continue

                offer = ai.generate_offer(player)
                if offer:
                    if eval.player_id not in daily_offers:
                        daily_offers[eval.player_id] = []
                    daily_offers[eval.player_id].append((team_id, offer))

        # Players choose best offers
        for player_id, offers in daily_offers.items():
            if not offers:
                continue

            # Best offer by total value
            offers.sort(key=lambda x: x[1].total_value, reverse=True)
            winning_team, winning_offer = offers[0]

            # Player accepts (simplified - would use negotiation system)
            if random.random() < 0.7:  # 70% acceptance rate
                signings[player_id] = winning_team
                remaining_fas = [p for p in remaining_fas if str(p.id) != player_id]

    return signings
