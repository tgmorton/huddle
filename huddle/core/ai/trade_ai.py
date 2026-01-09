"""
Trade AI System.

Autonomous trade decision-making for AI-controlled teams.

Handles:
- Trade proposal evaluation
- Trade generation (identifying targets and packages)
- Player valuation for trades
- Pick valuation adjustments based on team status
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.draft.picks import DraftPick, DraftPickInventory, get_pick_value
from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    TradePhilosophy,
)

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team_identity import TeamIdentity
    from huddle.core.contracts.contract import Contract


# Player value by overall rating (in draft pick value points)
def player_trade_value(overall: int, age: int, contract_years: int) -> int:
    """
    Calculate player trade value in draft pick value points.

    A 1st round pick is worth ~1000-3000 points on Jimmy Johnson chart.
    """
    # Base value from overall
    if overall >= 90:
        base = 2500 + (overall - 90) * 200  # Elite: 2500-4500
    elif overall >= 85:
        base = 1500 + (overall - 85) * 200  # Very good: 1500-2500
    elif overall >= 80:
        base = 800 + (overall - 80) * 140   # Good: 800-1500
    elif overall >= 75:
        base = 400 + (overall - 75) * 80    # Average: 400-800
    elif overall >= 70:
        base = 150 + (overall - 70) * 50    # Below average: 150-400
    else:
        base = max(0, (overall - 60) * 15)  # Replacement level

    # Age adjustment
    if age <= 25:
        age_mult = 1.2  # Young premium
    elif age <= 28:
        age_mult = 1.0  # Prime
    elif age <= 30:
        age_mult = 0.85  # Declining
    elif age <= 32:
        age_mult = 0.7   # Late career
    else:
        age_mult = 0.5   # End of career

    # Contract adjustment
    if contract_years >= 3:
        contract_mult = 1.1  # Team control premium
    elif contract_years == 2:
        contract_mult = 1.0
    elif contract_years == 1:
        contract_mult = 0.7  # Rental discount
    else:
        contract_mult = 0.4  # Expiring, may walk

    return int(base * age_mult * contract_mult)


@dataclass
class TradeAsset:
    """An asset in a trade package."""
    asset_type: str  # "player" or "pick"

    # Player info
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_overall: Optional[int] = None
    player_age: Optional[int] = None
    player_position: Optional[str] = None
    contract_years: Optional[int] = None

    # Pick info
    pick: Optional[DraftPick] = None

    # Value
    value: int = 0

    def __post_init__(self):
        if self.value == 0:
            self._calculate_value()

    def _calculate_value(self):
        if self.asset_type == "player" and self.player_overall:
            self.value = player_trade_value(
                self.player_overall,
                self.player_age or 25,
                self.contract_years or 2,
            )
        elif self.asset_type == "pick" and self.pick:
            self.value = self.pick.estimated_value

    def __repr__(self) -> str:
        if self.asset_type == "player":
            return f"{self.player_name} ({self.player_position}, {self.player_overall} OVR)"
        elif self.asset_type == "pick":
            return str(self.pick)
        return "Unknown asset"


@dataclass
class TradeProposal:
    """A proposed trade between two teams."""
    proposing_team_id: str
    receiving_team_id: str
    assets_offered: list[TradeAsset] = field(default_factory=list)
    assets_requested: list[TradeAsset] = field(default_factory=list)

    @property
    def offered_value(self) -> int:
        return sum(a.value for a in self.assets_offered)

    @property
    def requested_value(self) -> int:
        return sum(a.value for a in self.assets_requested)

    @property
    def value_difference(self) -> int:
        """Positive = proposer offering more."""
        return self.offered_value - self.requested_value

    def is_fair(self, tolerance: float = 0.15) -> bool:
        """Check if trade is roughly fair (within tolerance)."""
        if self.requested_value == 0:
            return False
        ratio = self.offered_value / self.requested_value
        return (1 - tolerance) <= ratio <= (1 + tolerance)


@dataclass
class TradeEvaluation:
    """AI evaluation of a trade proposal."""
    proposal: TradeProposal
    net_value: int           # Value gained/lost
    fills_need: bool         # Does it address a need?
    hurts_depth: bool        # Does it hurt roster depth?
    cap_impact: int          # Cap space change
    recommendation: str      # "accept", "counter", "reject"
    reasoning: str


class TradeAI:
    """
    AI system for trade decisions.

    Handles trade evaluation, generation, and negotiation.
    """

    def __init__(
        self,
        team_id: str,
        team_identity: "TeamIdentity",
        team_status: TeamStatusState,
        pick_inventory: DraftPickInventory,
        team_needs: dict[str, float],
    ):
        self.team_id = team_id
        self.identity = team_identity
        self.status = team_status
        self.picks = pick_inventory
        self.needs = team_needs

        # Configure based on team identity and status
        self._configure_behavior()

    def _configure_behavior(self):
        """Set trade behavior parameters."""
        # Base parameters
        self.trade_frequency = 0.5  # 0-1, likelihood to make trades
        self.pick_value_modifier = 1.0  # Adjusts pick valuation
        self.player_value_modifier = 1.0  # Adjusts player valuation
        self.minimum_profit = 0  # Minimum value profit to accept

        # Trade philosophy
        if self.identity.trade_philosophy == TradePhilosophy.HEAVY_TRADER:
            self.trade_frequency = 0.8
        elif self.identity.trade_philosophy == TradePhilosophy.LIGHT_TRADER:
            self.trade_frequency = 0.2

        # Team status adjustments
        status = self.status.current_status

        if status == TeamStatus.DYNASTY:
            self.pick_value_modifier = 0.8  # Picks less valuable to dynasties
            self.player_value_modifier = 1.1
            self.minimum_profit = -100  # Will overpay slightly

        elif status == TeamStatus.CONTENDING:
            self.pick_value_modifier = 0.85
            self.player_value_modifier = 1.05

        elif status == TeamStatus.WINDOW_CLOSING:
            self.pick_value_modifier = 0.7  # Desperate for players
            self.player_value_modifier = 1.15
            self.minimum_profit = -200  # Will overpay more

        elif status == TeamStatus.REBUILDING:
            self.pick_value_modifier = 1.4  # Hoard picks
            self.player_value_modifier = 0.8  # Players for picks
            self.minimum_profit = 100  # Only good deals
            self.trade_frequency = 0.7  # Active in trading

        elif status == TeamStatus.EMERGING:
            self.pick_value_modifier = 1.2
            self.player_value_modifier = 0.9

    def evaluate_trade(
        self,
        proposal: TradeProposal,
        my_roster: list["Player"] = None,
    ) -> TradeEvaluation:
        """
        Evaluate a trade proposal.

        Args:
            proposal: The trade to evaluate
            my_roster: Current roster for depth analysis

        Returns:
            TradeEvaluation with recommendation
        """
        # Calculate adjusted values based on our modifiers
        offered_adjusted = 0
        requested_adjusted = 0

        for asset in proposal.assets_offered:
            if asset.asset_type == "pick":
                offered_adjusted += int(asset.value * self.pick_value_modifier)
            else:
                offered_adjusted += int(asset.value * self.player_value_modifier)

        for asset in proposal.assets_requested:
            if asset.asset_type == "pick":
                requested_adjusted += int(asset.value * self.pick_value_modifier)
            else:
                requested_adjusted += int(asset.value * self.player_value_modifier)

        net_value = offered_adjusted - requested_adjusted

        # Check if fills need
        fills_need = False
        for asset in proposal.assets_offered:
            if asset.asset_type == "player":
                need = self.needs.get(asset.player_position, 0.3)
                if need > 0.5:
                    fills_need = True
                    net_value += 100  # Bonus for filling need

        # Check if hurts depth
        hurts_depth = False
        for asset in proposal.assets_requested:
            if asset.asset_type == "player":
                # Would need to check roster depth
                pass

        # Cap impact (simplified)
        cap_impact = 0

        # Make recommendation
        if net_value >= self.minimum_profit:
            if net_value >= 200:
                recommendation = "accept"
                reasoning = "Trade value significantly in our favor"
            elif fills_need:
                recommendation = "accept"
                reasoning = "Addresses team need at fair value"
            else:
                recommendation = "accept"
                reasoning = "Fair trade value"
        elif net_value >= self.minimum_profit - 100:
            recommendation = "counter"
            reasoning = "Close to acceptable, counter for better terms"
        else:
            recommendation = "reject"
            reasoning = f"Trade value not favorable (net: {net_value})"

        return TradeEvaluation(
            proposal=proposal,
            net_value=net_value,
            fills_need=fills_need,
            hurts_depth=hurts_depth,
            cap_impact=cap_impact,
            recommendation=recommendation,
            reasoning=reasoning,
        )

    def identify_trade_candidates(
        self,
        roster: list["Player"],
        contracts: dict[str, "Contract"],
    ) -> list[TradeAsset]:
        """
        Identify players that could be traded.

        Returns list of tradeable assets sorted by trade likelihood.
        """
        candidates = []

        for player in roster:
            player_id = str(player.id)
            contract = contracts.get(player_id)
            contract_years = contract.years_remaining if contract else 1

            # Skip players we absolutely need
            if player.overall >= 90:
                # Only trade superstars if rebuilding
                if self.status.current_status != TeamStatus.REBUILDING:
                    continue

            # Skip positions we need
            need = self.needs.get(player.position.value, 0.3)
            if need > 0.7:
                continue

            # Calculate trade likelihood
            trade_likelihood = 0.3

            # Older players more likely to be traded
            if player.age >= 30:
                trade_likelihood += 0.2

            # Players at stacked positions
            if need < 0.2:
                trade_likelihood += 0.2

            # Expiring contracts in contending window
            if contract_years == 1 and self.status.current_status == TeamStatus.REBUILDING:
                trade_likelihood += 0.3

            if trade_likelihood > 0.4:
                asset = TradeAsset(
                    asset_type="player",
                    player_id=player_id,
                    player_name=player.full_name,
                    player_overall=player.overall,
                    player_age=player.age,
                    player_position=player.position.value,
                    contract_years=contract_years,
                )
                candidates.append(asset)

        # Sort by trade likelihood (implicit in value - older, expiring = lower)
        candidates.sort(key=lambda a: a.value, reverse=True)

        return candidates

    def generate_trade_proposal(
        self,
        target_player: "Player",
        target_contract: "Contract",
        target_team_id: str,
    ) -> Optional[TradeProposal]:
        """
        Generate a trade proposal for a target player.

        Args:
            target_player: Player we want to acquire
            target_contract: Their contract
            target_team_id: Their current team

        Returns:
            TradeProposal or None if can't construct fair trade
        """
        target_value = player_trade_value(
            target_player.overall,
            target_player.age,
            target_contract.years_remaining if target_contract else 1,
        )

        # Adjust target value for our modifiers
        target_value_adjusted = int(target_value * self.player_value_modifier)

        # Build offer package
        offer_assets = []
        offer_value = 0

        # Try to use picks first
        available_picks = [
            p for p in self.picks.picks
            if p.current_team_id == self.team_id and not p.is_compensatory
        ]
        available_picks.sort(key=lambda p: p.estimated_value, reverse=True)

        for pick in available_picks:
            if offer_value >= target_value_adjusted:
                break

            pick_value = int(pick.estimated_value * self.pick_value_modifier)
            offer_assets.append(TradeAsset(
                asset_type="pick",
                pick=pick,
                value=pick.estimated_value,
            ))
            offer_value += pick_value

        # Check if we have enough
        if offer_value < target_value_adjusted * 0.85:
            return None  # Can't afford

        # Create proposal
        target_asset = TradeAsset(
            asset_type="player",
            player_id=str(target_player.id),
            player_name=target_player.full_name,
            player_overall=target_player.overall,
            player_age=target_player.age,
            player_position=target_player.position.value,
            contract_years=target_contract.years_remaining if target_contract else 1,
        )

        return TradeProposal(
            proposing_team_id=self.team_id,
            receiving_team_id=target_team_id,
            assets_offered=offer_assets,
            assets_requested=[target_asset],
        )

    def should_make_trade(self, proposal: TradeProposal) -> bool:
        """
        Final decision on whether to execute a trade.

        Incorporates randomness and trade frequency.
        """
        evaluation = self.evaluate_trade(proposal)

        if evaluation.recommendation == "reject":
            return False

        if evaluation.recommendation == "accept":
            return True

        # Counter - some probability
        return random.random() < self.trade_frequency


def find_trade_partners(
    trading_team: str,
    all_teams: dict[str, TradeAI],
    trade_candidates: list[TradeAsset],
) -> list[tuple[str, TradeProposal]]:
    """
    Find teams interested in trading for candidates.

    Returns list of (team_id, proposal) tuples.
    """
    matches = []

    for asset in trade_candidates:
        if asset.asset_type != "player":
            continue

        for team_id, ai in all_teams.items():
            if team_id == trading_team:
                continue

            # Check if team needs this position
            need = ai.needs.get(asset.player_position, 0.3)
            if need < 0.4:
                continue

            # Generate what they'd offer
            # This is simplified - would need their full AI context
            pick_value_needed = asset.value

            # Check if they have picks to offer
            available_value = sum(
                p.estimated_value for p in ai.picks.picks
                if p.current_team_id == team_id
            )

            if available_value >= pick_value_needed * 0.8:
                # They could potentially make a deal
                # In full implementation, would generate actual proposal
                matches.append((team_id, None))

    return matches
