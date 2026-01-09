"""
Cap Manager AI - Financial Decision Making for Teams.

A shrewd financial AI that:
- Reasons about current and future cap implications
- Makes decisions about releasing players when needed
- Restructures contracts to create cap space
- Acts aggressively or conservatively based on team status
- Ensures every rostered player has a valid contract

Key principles:
1. Never go over the cap (release players if needed)
2. Maintain some cap cushion for in-season moves
3. Balance short-term competitiveness with long-term flexibility
4. Consider dead money implications before cuts
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, TYPE_CHECKING
from enum import Enum, auto
import random

from huddle.core.contracts.contract import (
    Contract,
    ContractType,
    ContractStatus,
    create_veteran_contract,
    create_minimum_contract,
)
from huddle.core.contracts.market_value import calculate_market_value

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team_identity import TeamStatusState, TeamStatus


class CapStrategy(Enum):
    """Team's cap management strategy."""
    AGGRESSIVE = auto()    # Spend to the cap, win now
    BALANCED = auto()      # Moderate spending, some flexibility
    CONSERVATIVE = auto()  # Maximize future flexibility
    REBUILDING = auto()    # Minimize long-term commitments


@dataclass
class CapSituation:
    """Snapshot of a team's cap situation."""
    salary_cap: int = 255_000  # In thousands

    # Current year
    total_salary: int = 0
    dead_money: int = 0

    # Projections
    committed_next_year: int = 0
    committed_year_after: int = 0

    # Derived
    @property
    def cap_space(self) -> int:
        return self.salary_cap - self.total_salary - self.dead_money

    @property
    def cap_used_pct(self) -> float:
        return (self.total_salary + self.dead_money) / self.salary_cap

    @property
    def is_over_cap(self) -> bool:
        return self.cap_space < 0

    @property
    def projected_space_next_year(self) -> int:
        """Rough projection of next year's cap space."""
        # Assume 5% cap increase
        next_cap = int(self.salary_cap * 1.05)
        return next_cap - self.committed_next_year


@dataclass
class CutCandidate:
    """A player being evaluated for release."""
    player: "Player"
    contract: Contract

    cap_savings: int = 0
    dead_money: int = 0
    replacement_cost: int = 0  # Cost to replace their production

    # Scores
    value_score: float = 0.0  # How much they contribute
    cut_score: float = 0.0    # How cuttable they are (higher = more cuttable)

    def calculate_scores(self, needs: dict[str, float] = None):
        """Calculate value and cut scores."""
        # Value based on overall and position need
        self.value_score = self.player.overall / 100
        if needs:
            need = needs.get(self.player.position.value, 0.3)
            self.value_score *= (1 + need * 0.3)

        # Cut score based on savings vs dead money ratio
        if self.cap_savings > 0:
            efficiency = self.cap_savings / (self.dead_money + 1)
        else:
            efficiency = 0  # No savings = don't cut

        # Age penalty - older players more cuttable
        age_factor = max(0.5, 1.0 + (self.player.age - 28) * 0.1)

        # Lower value = more cuttable
        self.cut_score = efficiency * age_factor / (self.value_score + 0.1)


@dataclass
class RestructureCandidate:
    """A player being evaluated for restructure."""
    player: "Player"
    contract: Contract

    convertible_amount: int = 0  # Max salary that can be converted
    cap_savings: int = 0         # Savings from restructure
    future_cap_hit: int = 0      # Added future dead money risk

    restructure_score: float = 0.0


class CapManager:
    """
    AI system for managing team salary cap.

    Makes decisions about:
    - Who to release to get under cap
    - Which contracts to restructure
    - How much to offer free agents
    - When to be aggressive vs conservative
    """

    def __init__(
        self,
        team_id: str,
        roster: list["Player"],
        contracts: dict[str, Contract],
        salary_cap: int = 255_000,
        team_status: "TeamStatusState" = None,
    ):
        self.team_id = team_id
        self.roster = roster
        self.contracts = contracts
        self.salary_cap = salary_cap
        self.team_status = team_status

        # Determine strategy based on team status
        self.strategy = self._determine_strategy()

        # Calculate current situation
        self.situation = self._calculate_situation()

    def _determine_strategy(self) -> CapStrategy:
        """Determine cap strategy based on team status."""
        if not self.team_status:
            return CapStrategy.BALANCED

        from huddle.core.models.team_identity import TeamStatus

        status = self.team_status.current_status

        if status == TeamStatus.DYNASTY:
            return CapStrategy.AGGRESSIVE
        elif status == TeamStatus.CONTENDING:
            return CapStrategy.AGGRESSIVE
        elif status == TeamStatus.WINDOW_CLOSING:
            return CapStrategy.AGGRESSIVE  # Go all-in
        elif status == TeamStatus.REBUILDING:
            return CapStrategy.REBUILDING
        elif status == TeamStatus.EMERGING:
            return CapStrategy.BALANCED
        else:
            return CapStrategy.CONSERVATIVE

    def _calculate_situation(self) -> CapSituation:
        """Calculate current cap situation."""
        total_salary = 0
        dead_money = 0
        committed_next = 0
        committed_after = 0

        for player_id, contract in self.contracts.items():
            if contract.status != ContractStatus.ACTIVE:
                continue

            # Current year
            total_salary += contract.cap_hit()

            # Future commitments
            if contract.years_remaining > 1:
                committed_next += contract.cap_hit(contract.current_year + 1)
            if contract.years_remaining > 2:
                committed_after += contract.cap_hit(contract.current_year + 2)

        return CapSituation(
            salary_cap=self.salary_cap,
            total_salary=total_salary,
            dead_money=dead_money,
            committed_next_year=committed_next,
            committed_year_after=committed_after,
        )

    def get_under_cap(self, target_cushion: int = 5_000) -> list[tuple["Player", int]]:
        """
        Get team under the salary cap.

        Returns list of (player, dead_money) for players to cut.

        Args:
            target_cushion: Target cap space after cuts (for flexibility)
        """
        cuts = []

        # How much do we need to clear?
        needed = -self.situation.cap_space + target_cushion

        if needed <= 0:
            return []  # Already under cap with cushion

        # Get cut candidates
        candidates = self._evaluate_cut_candidates()

        # Sort by cut score (most cuttable first)
        candidates.sort(key=lambda c: c.cut_score, reverse=True)

        # Cut until we have enough space
        cleared = 0
        for candidate in candidates:
            if cleared >= needed:
                break

            if candidate.cap_savings <= 0:
                continue  # No point cutting

            cuts.append((candidate.player, candidate.dead_money))
            cleared += candidate.cap_savings

        return cuts

    def _evaluate_cut_candidates(self) -> list[CutCandidate]:
        """Evaluate all players as potential cuts."""
        candidates = []

        # Calculate team needs first
        from huddle.core.ai import calculate_team_needs
        needs = calculate_team_needs(self.roster)
        needs_dict = {pos: needs.get_need(pos) for pos in
                     ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                      "DE", "DT", "OLB", "ILB", "MLB", "CB", "FS", "SS"]}

        for player in self.roster:
            player_id = str(player.id)
            contract = self.contracts.get(player_id)

            if not contract:
                continue  # Can't cut someone without a contract

            candidate = CutCandidate(
                player=player,
                contract=contract,
                cap_savings=contract.cap_savings_if_cut(),
                dead_money=contract.dead_money_if_cut(),
            )
            candidate.calculate_scores(needs_dict)
            candidates.append(candidate)

        return candidates

    def get_restructure_candidates(self, needed_savings: int) -> list[RestructureCandidate]:
        """
        Find players whose contracts can be restructured for cap relief.

        Restructuring converts salary to signing bonus, spreading the cap hit.
        """
        candidates = []

        for player in self.roster:
            player_id = str(player.id)
            contract = self.contracts.get(player_id)

            if not contract:
                continue

            # Need at least 2 years remaining to restructure
            if contract.years_remaining < 2:
                continue

            # Can only convert base salary
            current_year = contract.current_year_data()
            if not current_year:
                continue

            convertible = current_year.base_salary
            if convertible < 1000:  # Not worth restructuring small amounts
                continue

            # Calculate savings
            years_to_spread = min(5, contract.years_remaining)
            new_prorated = convertible // years_to_spread
            savings = convertible - new_prorated

            candidate = RestructureCandidate(
                player=player,
                contract=contract,
                convertible_amount=convertible,
                cap_savings=savings,
                future_cap_hit=convertible,  # All becomes dead money risk
            )

            # Score based on savings efficiency and player value
            value_factor = player.overall / 100
            candidate.restructure_score = savings / (contract.years_remaining + 1) * value_factor

            candidates.append(candidate)

        # Sort by restructure score
        candidates.sort(key=lambda c: c.restructure_score, reverse=True)

        return candidates

    def determine_offer(
        self,
        player: "Player",
        competing_offers: list[int] = None,
    ) -> Optional[dict]:
        """
        Determine what contract to offer a free agent.

        Returns dict with years, value, guaranteed, signing_bonus or None.
        """
        # Can we afford them?
        market = calculate_market_value(player)

        if market.cap_hit_year1 > self.situation.cap_space:
            return None  # Can't afford

        # Adjust based on strategy
        if self.strategy == CapStrategy.AGGRESSIVE:
            value_mult = 1.15  # Overpay to win
            years_pref = 1     # Longer deals
        elif self.strategy == CapStrategy.REBUILDING:
            value_mult = 0.85  # Only bargains
            years_pref = -1    # Short deals
        else:
            value_mult = 1.0
            years_pref = 0

        # Calculate offer
        base_value = int(market.total_value * value_mult)
        years = max(1, min(5, market.years + years_pref))

        # Age adjustment
        if player.age > 30:
            years = min(years, 2)

        # If there's competition, we might need to beat it
        if competing_offers:
            max_competing = max(competing_offers)
            if max_competing > base_value:
                if self.strategy == CapStrategy.AGGRESSIVE:
                    base_value = int(max_competing * 1.05)  # Beat by 5%
                else:
                    return None  # Don't overpay

        return {
            "years": years,
            "total_value": base_value,
            "guaranteed": int(base_value * 0.4),
            "signing_bonus": int(base_value * 0.2),
        }

    def handle_expiring_contracts(
        self,
        current_date: date,
    ) -> tuple[list["Player"], list["Player"]]:
        """
        Handle players with expiring contracts.

        Returns (players_to_resign, players_to_release).
        """
        to_resign = []
        to_release = []

        for player in self.roster:
            player_id = str(player.id)
            contract = self.contracts.get(player_id)

            if not contract or not contract.is_expiring():
                continue

            # Evaluate whether to re-sign
            should_resign = self._should_resign_player(player, contract)

            if should_resign:
                to_resign.append(player)
            else:
                to_release.append(player)

        return to_resign, to_release

    def _should_resign_player(self, player: "Player", contract: Contract) -> bool:
        """Decide if we should re-sign an expiring player."""
        # Always try to keep high performers
        if player.overall >= 88:
            return True

        # Don't re-sign old declining players
        if player.age >= 32 and player.overall < 80:
            return False

        # Re-sign young talent
        if player.age <= 26 and player.overall >= 75:
            return True

        # Strategy-based decision
        if self.strategy == CapStrategy.REBUILDING:
            # Only keep young players
            return player.age <= 27
        elif self.strategy == CapStrategy.AGGRESSIVE:
            # Keep anyone contributing
            return player.overall >= 72
        else:
            # Balanced - keep solid starters
            return player.overall >= 75

    def create_minimum_contract_for_player(
        self,
        player: "Player",
        current_date: date,
    ) -> Contract:
        """Create a minimum contract for a player (for roster filler)."""
        return create_minimum_contract(
            player_id=str(player.id),
            team_id=self.team_id,
            years=1,
            player_experience=player.experience_years,
            signed_date=current_date,
        )

    def ensure_all_players_have_contracts(
        self,
        current_date: date,
    ) -> list[Contract]:
        """
        Ensure every player on roster has a contract.

        Creates minimum contracts for any players without one.
        Returns list of new contracts created.
        """
        new_contracts = []

        for player in self.roster:
            player_id = str(player.id)

            if player_id not in self.contracts:
                # Create minimum contract
                contract = self.create_minimum_contract_for_player(player, current_date)
                self.contracts[player_id] = contract
                new_contracts.append(contract)

        return new_contracts


def get_under_cap_with_strategy(
    roster: list["Player"],
    contracts: dict[str, Contract],
    salary_cap: int = 255_000,
    target_cushion: int = 10_000,
    team_status: "TeamStatusState" = None,
) -> tuple[list["Player"], dict[str, Contract], int]:
    """
    Get a team under the cap using the CapManager.

    Returns (updated_roster, updated_contracts, dead_money_incurred).
    """
    manager = CapManager(
        team_id="temp",
        roster=list(roster),
        contracts=dict(contracts),
        salary_cap=salary_cap,
        team_status=team_status,
    )

    cuts = manager.get_under_cap(target_cushion)

    dead_money_total = 0
    updated_roster = list(roster)
    updated_contracts = dict(contracts)

    for player, dead_money in cuts:
        updated_roster = [p for p in updated_roster if p.id != player.id]
        if str(player.id) in updated_contracts:
            del updated_contracts[str(player.id)]
        dead_money_total += dead_money

    return updated_roster, updated_contracts, dead_money_total
