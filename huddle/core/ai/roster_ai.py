"""
Roster Management AI System.

Autonomous roster decision-making for AI-controlled teams.

Handles:
- Roster cuts to meet limits (90 -> 85 -> 53)
- Practice squad decisions
- IR management
- Waiver claims
"""

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.models.team_identity import TeamStatus, TeamStatusState

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.contracts.contract import Contract


# Roster limits at different points
ROSTER_LIMIT_90 = 90
ROSTER_LIMIT_85 = 85
ROSTER_LIMIT_53 = 53
PRACTICE_SQUAD_LIMIT = 16


# Position priorities for roster (higher = more protected)
POSITION_ROSTER_PRIORITY = {
    "QB": 100,  # Always protect QBs
    "LT": 85,
    "CB": 82,
    "EDGE": 80,
    "WR": 78,
    "RB": 70,
    "S": 68,
    "DT": 65,
    "TE": 62,
    "LB": 60,
    "RT": 58,
    "LG": 55,
    "RG": 55,
    "C": 55,
    "FB": 30,
    "K": 40,
    "P": 40,
}


@dataclass
class RosterEvaluation:
    """Evaluation of a player for roster decisions."""
    player_id: str
    player_name: str
    position: str
    age: int
    overall: int
    experience: int  # Years in league

    # Scores
    performance_score: float    # Current ability contribution
    development_score: float    # Future value potential
    contract_score: float       # Cap efficiency
    depth_score: float          # Position depth consideration

    # Composite
    roster_value: float = 0.0

    # Flags
    is_starter: bool = False
    is_protected: bool = False  # Can't be cut (guaranteed money, etc.)
    practice_squad_eligible: bool = False
    is_injured: bool = False

    def __post_init__(self):
        if self.roster_value == 0:
            self._calculate_roster_value()

    def _calculate_roster_value(self):
        """Calculate composite roster value."""
        # Weight components
        self.roster_value = (
            self.performance_score * 0.45 +
            self.development_score * 0.20 +
            self.contract_score * 0.20 +
            self.depth_score * 0.15
        )

        # Adjustments
        if self.is_starter:
            self.roster_value *= 1.3
        if self.is_protected:
            self.roster_value = 999  # Can't cut
        if self.is_injured:
            self.roster_value *= 0.7  # Injured players valued less for cuts


@dataclass
class CutDecision:
    """Result of a roster cut decision."""
    player_id: str
    player_name: str
    position: str
    action: str  # "cut", "ir", "practice_squad", "keep"
    reason: str
    dead_money: int = 0
    cap_savings: int = 0


class RosterAI:
    """
    AI system for roster management decisions.

    Handles cuts, IR, practice squad, and waiver decisions.
    """

    def __init__(
        self,
        team_id: str,
        team_status: TeamStatusState,
        salary_cap: int,
        current_cap_used: int,
    ):
        self.team_id = team_id
        self.status = team_status
        self.salary_cap = salary_cap
        self.current_cap_used = current_cap_used

    def evaluate_roster(
        self,
        roster: list["Player"],
        contracts: dict[str, "Contract"],
        starters: set[str] = None,
        injured: set[str] = None,
    ) -> list[RosterEvaluation]:
        """
        Evaluate all players on roster for cut decisions.

        Args:
            roster: All players on roster
            contracts: Map of player_id -> Contract
            starters: Set of starter player IDs
            injured: Set of injured player IDs

        Returns:
            List of evaluations sorted by roster value (lowest first)
        """
        starters = starters or set()
        injured = injured or set()

        evaluations = []

        for player in roster:
            player_id = str(player.id)
            contract = contracts.get(player_id)

            eval = self._evaluate_player(
                player,
                contract,
                is_starter=player_id in starters,
                is_injured=player_id in injured,
            )
            evaluations.append(eval)

        # Sort by roster value, lowest first (cut candidates at front)
        evaluations.sort(key=lambda e: e.roster_value)

        return evaluations

    def _evaluate_player(
        self,
        player: "Player",
        contract: Optional["Contract"],
        is_starter: bool,
        is_injured: bool,
    ) -> RosterEvaluation:
        """Evaluate a single player for roster decisions."""
        player_id = str(player.id)

        # Performance score from overall rating
        performance_score = player.overall / 100

        # Position priority bonus
        position_bonus = POSITION_ROSTER_PRIORITY.get(player.position.value, 50) / 100
        performance_score = performance_score * 0.7 + position_bonus * 0.3

        # Development score based on age and potential
        if player.age <= 24:
            development_score = 0.8 + (24 - player.age) * 0.05
        elif player.age <= 28:
            development_score = 0.5
        else:
            development_score = max(0.1, 0.5 - (player.age - 28) * 0.1)

        # Contract score (cap efficiency)
        contract_score = 0.5  # Default
        is_protected = False

        if contract:
            cap_hit = contract.cap_hit()
            dead_money = contract.dead_money_if_cut()

            # Check if protected by guaranteed money
            if dead_money >= cap_hit:
                is_protected = True
                contract_score = 1.0  # Can't cut anyway

            else:
                # Value per cap dollar
                expected_cap = player.overall * 100  # Rough: 80 OVR = $8M expected
                if cap_hit > 0:
                    cap_efficiency = expected_cap / cap_hit
                    contract_score = min(1.0, cap_efficiency / 2)
                else:
                    contract_score = 1.0  # Minimum salary

        # Depth score - need backup at position
        depth_score = 0.5  # Would be calculated from roster composition

        # Practice squad eligibility (simplified)
        experience = player.age - 22  # Rough approximation
        practice_squad_eligible = experience <= 3 and player.overall < 70

        return RosterEvaluation(
            player_id=player_id,
            player_name=player.full_name,
            position=player.position.value,
            age=player.age,
            overall=player.overall,
            experience=max(0, experience),
            performance_score=performance_score,
            development_score=development_score,
            contract_score=contract_score,
            depth_score=depth_score,
            is_starter=is_starter,
            is_protected=is_protected,
            practice_squad_eligible=practice_squad_eligible,
            is_injured=is_injured,
        )

    def make_cuts(
        self,
        roster: list["Player"],
        contracts: dict[str, "Contract"],
        target_size: int,
        starters: set[str] = None,
        injured: set[str] = None,
    ) -> list[CutDecision]:
        """
        Decide which players to cut to reach roster limit.

        Args:
            roster: Current roster
            contracts: Player contracts
            target_size: Target roster size (90, 85, or 53)
            starters: Starter player IDs
            injured: Injured player IDs

        Returns:
            List of cut decisions
        """
        current_size = len(roster)
        if current_size <= target_size:
            return []  # Already at limit

        cuts_needed = current_size - target_size

        evaluations = self.evaluate_roster(roster, contracts, starters, injured)

        decisions = []
        cuts_made = 0

        for eval in evaluations:
            if cuts_made >= cuts_needed:
                break

            if eval.is_protected:
                continue  # Can't cut

            contract = contracts.get(eval.player_id)
            dead_money = 0
            cap_savings = 0

            if contract:
                dead_money = contract.dead_money_if_cut()
                cap_savings = contract.cap_savings_if_cut()

            # Determine action
            if eval.is_injured and target_size == 53:
                # Consider IR for injured players at 53-man cutdown
                action = "ir"
                reason = f"Placed on IR ({eval.player_name} injured)"
            elif eval.practice_squad_eligible and target_size == 53:
                # Try to keep on practice squad
                action = "practice_squad"
                reason = f"Moved to practice squad (development)"
            else:
                action = "cut"
                reason = self._get_cut_reason(eval, contract)

            decisions.append(CutDecision(
                player_id=eval.player_id,
                player_name=eval.player_name,
                position=eval.position,
                action=action,
                reason=reason,
                dead_money=dead_money,
                cap_savings=cap_savings,
            ))

            if action != "ir":  # IR doesn't count toward roster limit
                cuts_made += 1

        return decisions

    def _get_cut_reason(
        self,
        eval: RosterEvaluation,
        contract: Optional["Contract"],
    ) -> str:
        """Generate reason for cutting a player."""
        reasons = []

        if eval.overall < 60:
            reasons.append("insufficient talent")
        if eval.age >= 32:
            reasons.append("age")
        if contract and contract.cap_hit() > eval.overall * 150:
            reasons.append("cap efficiency")
        if eval.depth_score < 0.3:
            reasons.append("roster depth")

        if reasons:
            return f"Released due to {', '.join(reasons)}"
        return "Released (roster move)"

    def evaluate_ir_candidates(
        self,
        roster: list["Player"],
        injured_players: dict[str, int],  # player_id -> weeks injured
    ) -> list[tuple[str, bool]]:
        """
        Evaluate which injured players should go on IR.

        Args:
            roster: Current roster
            injured_players: Map of player ID to weeks expected out

        Returns:
            List of (player_id, should_ir) tuples
        """
        decisions = []

        for player in roster:
            player_id = str(player.id)
            if player_id not in injured_players:
                continue

            weeks_out = injured_players[player_id]

            # IR if out 4+ weeks (IR-designated return eligible after 4)
            should_ir = weeks_out >= 4

            # Star players might be kept on active roster if borderline
            if player.overall >= 85 and weeks_out <= 4:
                should_ir = False

            decisions.append((player_id, should_ir))

        return decisions

    def evaluate_waiver_claims(
        self,
        waiver_players: list["Player"],
        current_roster: list["Player"],
        needs: dict[str, float],
        waiver_priority: int,  # 1 = first, 32 = last
    ) -> list[tuple[str, float]]:
        """
        Evaluate which waiver players to claim.

        Args:
            waiver_players: Available players on waivers
            current_roster: Current roster
            needs: Position needs (from DraftAI)
            waiver_priority: Waiver order position

        Returns:
            List of (player_id, interest_level) sorted by interest
        """
        claims = []

        for player in waiver_players:
            # Base interest from overall
            interest = player.overall / 100

            # Position need multiplier
            need = needs.get(player.position.value, 0.3)
            interest *= (1 + need)

            # Age consideration
            if player.age > 30:
                interest *= 0.8
            elif player.age < 26:
                interest *= 1.1

            # Worth claiming if high interest
            if interest > 0.5:
                claims.append((str(player.id), interest))

        # Sort by interest, highest first
        claims.sort(key=lambda x: x[1], reverse=True)

        return claims

    def build_practice_squad(
        self,
        available_players: list["Player"],
        current_roster: list["Player"],
        current_ps: list["Player"],
        needs: dict[str, float],
    ) -> list[str]:
        """
        Select players for practice squad.

        Args:
            available_players: Cut players eligible for PS
            current_roster: Active roster
            current_ps: Current practice squad
            needs: Position needs

        Returns:
            List of player IDs to sign to practice squad
        """
        ps_spots = PRACTICE_SQUAD_LIMIT - len(current_ps)
        if ps_spots <= 0:
            return []

        # Score candidates
        candidates = []
        for player in available_players:
            # Check eligibility (simplified)
            experience = player.age - 22
            if experience > 3:
                continue

            # Score based on development potential
            score = 0.5

            # Young players score higher
            if player.age <= 24:
                score += 0.2

            # High potential scores higher
            if player.overall >= 65:
                score += 0.2

            # Need at position
            need = needs.get(player.position.value, 0.3)
            score += need * 0.3

            candidates.append((str(player.id), score))

        # Sort and take top candidates
        candidates.sort(key=lambda x: x[1], reverse=True)

        return [pid for pid, _ in candidates[:ps_spots]]


def select_starters(
    roster: list["Player"],
    scheme: str = "base",
) -> dict[str, list[str]]:
    """
    Select starters from roster.

    Returns depth chart with starters first.
    """
    depth_chart: dict[str, list[str]] = {}

    # Group by position
    by_position: dict[str, list["Player"]] = {}
    for player in roster:
        pos = player.position.value
        if pos not in by_position:
            by_position[pos] = []
        by_position[pos].append(player)

    # Sort each position by overall
    for pos, players in by_position.items():
        players.sort(key=lambda p: p.overall, reverse=True)
        depth_chart[pos] = [str(p.id) for p in players]

    return depth_chart


def get_starter_ids(depth_chart: dict[str, list[str]]) -> set[str]:
    """Get set of starter player IDs from depth chart."""
    starters = set()
    for pos, players in depth_chart.items():
        if players:
            starters.add(players[0])
    return starters
