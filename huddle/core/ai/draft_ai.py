"""
Draft AI System.

Autonomous draft decision-making for AI-controlled teams.

Handles:
- Player evaluation and ranking
- Best player available vs team needs
- Trade up/down decisions
- Team philosophy integration
- Research-backed position valuations (Calvetti framework)
- GM archetype personality integration
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple
from uuid import UUID
import random

from huddle.core.draft.picks import DraftPick, DraftPickInventory, get_pick_value
from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    DraftPhilosophy,
    PersonnelPreference,
    OffensiveScheme,
    DefensiveScheme,
)
from huddle.core.philosophy.evaluation import (
    calculate_scheme_fit_overall,
    get_scheme_fit_bonus,
)
from huddle.core.ai.allocation_tables import (
    get_rookie_premium,
    should_draft_position,
)
from huddle.core.ai.gm_archetypes import (
    GMArchetype,
    GMProfile,
    get_gm_profile,
)

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team_identity import TeamIdentity
    from huddle.core.ai.position_planner import PositionPlan, AcquisitionPath


# Legacy position value tiers (kept for fallback)
POSITION_VALUE_TIERS = {
    # Tier 1: Premium positions
    "QB": 1.0,
    "LT": 0.95,
    "EDGE": 0.92,
    "CB": 0.90,
    # Tier 2: High value
    "WR": 0.85,
    "DT": 0.82,
    "S": 0.80,
    "RT": 0.78,
    # Tier 3: Solid value
    "TE": 0.75,
    "LB": 0.73,
    "RB": 0.70,
    "LG": 0.68,
    "RG": 0.68,
    "C": 0.65,
    # Tier 4: Specialists
    "FB": 0.40,
    "K": 0.35,
    "P": 0.30,
}

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
    # Special teams
    "K": ("K", "offense"),
    "P": ("P", "offense"),
}


def get_research_position_value(position: str) -> float:
    """
    Get research-backed draft value for a position.

    Uses CONSTRAINED values from DRAFT_AI_CONSTRAINTS.md to prevent
    runaway optimization (e.g., drafting only OL).

    Raw research: OL=9.56x vs RB=0.39x (24x difference - too extreme!)
    Constrained:  OL=1.8  vs RB=0.7  (2.5x difference - realistic)

    The research tells us relative value (OL > RB), but the constraint
    ensures we don't make any position undraftable.
    """
    # Constrained position values from DRAFT_AI_CONSTRAINTS.md
    # Uses compressed scale: 0.7 (floor) to 1.8 (ceiling)
    CONSTRAINED_POSITION_VALUES = {
        # Position groups mapped to constrained values
        "OL": 1.8,  # Was 9.56x - capped
        "QB": 1.6,  # High but not dominant
        "EDGE": 1.5,
        "DL": 1.4,
        "S": 1.1,
        "WR": 1.1,
        "TE": 1.0,
        "LB": 0.9,
        "CB": 0.8,  # Floor
        "RB": 0.7,  # Floor - don't make them undraftable
        # Special teams (use legacy values)
        "K": 0.35,
        "P": 0.30,
    }

    group, side = POSITION_TO_GROUP.get(position, (position, "offense"))

    # Look up constrained value
    if group in CONSTRAINED_POSITION_VALUES:
        return CONSTRAINED_POSITION_VALUES[group]

    # Fallback to legacy tiers for positions not in research
    return POSITION_VALUE_TIERS.get(position, 1.0)


def is_draft_priority_position(position: str) -> bool:
    """
    Check if research recommends drafting this position (vs signing in FA).

    High draft priority: QB, WR, OL, DL, EDGE, S
    Low draft priority (sign in FA): RB, CB
    """
    group, side = POSITION_TO_GROUP.get(position, (position, "offense"))
    return should_draft_position(group, side)


@dataclass
class ProspectEvaluation:
    """AI evaluation of a draft prospect."""

    player_id: str
    player_name: str
    position: str
    overall: int

    # Evaluation scores
    raw_grade: float  # 0-100, pure talent evaluation
    scheme_fit: float  # 0-1, how well they fit team scheme
    need_score: float  # 0-1, how much team needs this position
    upside_score: float  # 0-1, development potential
    floor_score: float  # 0-1, guaranteed production

    # Composite
    draft_value: float = 0.0  # Combined score for draft ranking

    # Risk factors
    injury_risk: float = 0.0  # 0-1, durability concerns
    character_risk: float = 0.0  # 0-1, off-field concerns

    def __post_init__(self):
        if self.draft_value == 0:
            self._calculate_draft_value()

    def _calculate_draft_value(self):
        """Calculate composite draft value."""
        # Base: raw grade adjusted by position value
        position_mult = POSITION_VALUE_TIERS.get(self.position, 0.60)
        base_value = self.raw_grade * position_mult

        # Modifiers
        scheme_bonus = (self.scheme_fit - 0.5) * 10  # -5 to +5
        need_bonus = (self.need_score - 0.5) * 15  # -7.5 to +7.5
        upside_bonus = (self.upside_score - 0.5) * 5  # -2.5 to +2.5

        # Penalties
        injury_penalty = self.injury_risk * 10
        character_penalty = self.character_risk * 8

        self.draft_value = max(
            0,
            (
                base_value
                + scheme_bonus
                + need_bonus
                + upside_bonus
                - injury_penalty
                - character_penalty
            ),
        )


@dataclass
class TeamNeeds:
    """Current team needs by position."""

    needs: dict[str, float] = field(default_factory=dict)  # position -> 0-1 need level

    def get_need(self, position: str) -> float:
        """Get need level for a position (0 = no need, 1 = desperate)."""
        return self.needs.get(position, 0.3)  # Default moderate need

    def set_need(self, position: str, level: float) -> None:
        """Set need level for a position."""
        self.needs[position] = max(0.0, min(1.0, level))

    def decrease_need(self, position: str, amount: float = 0.3) -> None:
        """Decrease need after filling it."""
        current = self.needs.get(position, 0.3)
        self.needs[position] = max(0.0, current - amount)


@dataclass
class DraftAIConfig:
    """Configuration for draft AI behavior."""

    # Weights for evaluation components
    raw_talent_weight: float = 0.40
    scheme_fit_weight: float = 0.15
    need_weight: float = 0.25
    upside_weight: float = 0.10
    floor_weight: float = 0.10

    # Behavioral modifiers
    reach_tolerance: int = 10  # How many picks will AI reach for "their guy"
    value_threshold: float = 0.8  # Minimum value % to take a player
    trade_down_threshold: float = 0.6  # If best available is below this, consider trade down

    # Risk tolerance
    injury_risk_tolerance: float = 0.3
    character_risk_tolerance: float = 0.2


class DraftAI:
    """
    AI system for making draft decisions.

    Integrates with team identity, status, and needs to make
    contextually appropriate draft choices.

    Now includes:
    - Research-backed position valuations (Calvetti framework)
    - GM archetype personality modifiers
    - Scarcity penalty for over-drafting same position
    """

    def __init__(
        self,
        team_id: str,
        team_identity: "TeamIdentity",
        team_status: TeamStatusState,
        team_needs: TeamNeeds,
        config: DraftAIConfig = None,
        gm_archetype: GMArchetype = None,
    ):
        self.team_id = team_id
        self.identity = team_identity
        self.status = team_status
        self.needs = team_needs
        self.config = config or DraftAIConfig()

        # GM archetype for personality-based adjustments
        self.gm_archetype = gm_archetype or GMArchetype.BALANCED
        self.gm_profile = get_gm_profile(self.gm_archetype)

        # Track positions drafted this draft (for scarcity penalty)
        self._positions_drafted: dict[str, int] = {}

        # Apply team status modifiers
        self._apply_status_modifiers()

        # Apply GM archetype modifiers
        self._apply_gm_modifiers()

    def _apply_gm_modifiers(self):
        """Adjust config based on GM archetype."""
        # GM rookie preference affects how much we value draft picks
        # Cap Wizard (2.0) loves rookies, Win Now (0.6) prefers veterans
        if self.gm_profile.rookie_premium > 1.2:
            # High rookie preference = more willing to reach for needs
            self.config.reach_tolerance += 5
            self.config.need_weight *= 1.1
        elif self.gm_profile.rookie_premium < 0.8:
            # Low rookie preference = stick to BPA
            self.config.reach_tolerance -= 3
            self.config.raw_talent_weight += 0.05

    def _apply_status_modifiers(self):
        """Adjust config based on team status."""
        status = self.status.current_status

        if status == TeamStatus.DYNASTY:
            # Dynasties can take risks on upside
            self.config.upside_weight = 0.15
            self.config.need_weight = 0.15  # Less need-driven
            self.config.reach_tolerance = 5  # Less likely to reach

        elif status == TeamStatus.CONTENDING:
            # Contenders need contributors now
            self.config.floor_weight = 0.15
            self.config.upside_weight = 0.05
            self.config.need_weight = 0.30

        elif status == TeamStatus.REBUILDING:
            # Rebuilders swing for fences
            self.config.upside_weight = 0.25
            self.config.floor_weight = 0.05
            self.config.need_weight = 0.15
            self.config.reach_tolerance = 15

        elif status == TeamStatus.WINDOW_CLOSING:
            # All-in on immediate contributors
            self.config.floor_weight = 0.20
            self.config.upside_weight = 0.0
            self.config.need_weight = 0.35

        elif status == TeamStatus.EMERGING:
            # Balance upside with building blocks
            self.config.upside_weight = 0.15
            self.config.need_weight = 0.25

        # Apply draft philosophy (skip if no identity)
        if self.identity is None:
            return

        if self.identity.draft_philosophy == DraftPhilosophy.BEST_AVAILABLE:
            self.config.need_weight *= 0.5
            self.config.raw_talent_weight += 0.15

        elif self.identity.draft_philosophy == DraftPhilosophy.DRAFT_FOR_NEED:
            self.config.need_weight *= 1.5
            self.config.raw_talent_weight -= 0.10

    def evaluate_prospect(
        self,
        player: "Player",
        pick_number: int,
    ) -> ProspectEvaluation:
        """
        Evaluate a prospect for draft consideration.

        Uses research-backed position valuations and GM archetype modifiers.

        Args:
            player: The prospect to evaluate
            pick_number: Current draft position (affects value assessment)

        Returns:
            ProspectEvaluation with all scores
        """
        position = player.position.value

        # Raw grade from player's archetype-based OVR (HC09-style)
        # This uses the player's archetype weights, not generic position weights
        raw_grade = player.archetype_overall

        # Scheme fit based on team identity (HC09-style archetype fit)
        scheme_fit = self._calculate_scheme_fit(player)

        # Need score based on roster
        need_score = self.needs.get_need(position)

        # Upside/floor from potential vs current
        upside_score = self._calculate_upside(player)
        floor_score = self._calculate_floor(player)

        # Risk factors
        injury_risk = self._assess_injury_risk(player)
        character_risk = 0.0  # Would come from personality system

        # Create base evaluation
        eval = ProspectEvaluation(
            player_id=str(player.id),
            player_name=player.full_name,
            position=position,
            overall=player.overall,
            raw_grade=raw_grade,
            scheme_fit=scheme_fit,
            need_score=need_score,
            upside_score=upside_score,
            floor_score=floor_score,
            injury_risk=injury_risk,
            character_risk=character_risk,
        )

        # Apply research-backed and GM archetype adjustments
        eval.draft_value = self._calculate_adjusted_draft_value(eval, position)

        return eval

    def _calculate_adjusted_draft_value(
        self,
        eval: ProspectEvaluation,
        position: str,
    ) -> float:
        """
        Calculate draft value with research and GM adjustments.

        FORMULA (from DRAFT_AI_CONSTRAINTS.md):
        - Talent is the foundation (same for all positions)
        - Position adds a BONUS, not a multiplier (prevents runaway OL drafting)
        - Need can swing decisions (25+ points)
        - Scarcity penalty for over-drafting same position
        """
        # Get research-backed position draft value (0.7 to 1.8 scale)
        research_value = get_research_position_value(position)

        # Get GM archetype position adjustment
        gm_position_adj = self.gm_profile.position_adjustments.get(position, 1.0)

        # GM rookie preference (Cap Wizard=2.0, Win Now=0.6)
        gm_rookie_pref = self.gm_profile.rookie_premium

        # === NEW BALANCED FORMULA ===

        # 1. Base talent score (SAME for all positions)
        #    90 OVR = 45 points, regardless of position
        talent_score = eval.raw_grade * 0.5

        # 2. Position bonus (ADDITIVE, not multiplicative)
        #    OL (1.8): +8 points, RB (0.7): -3 points
        #    This is the research signal, but capped to prevent domination
        position_bonus = (research_value - 1.0) * 10 * gm_position_adj

        # 3. Need bonus (STRONG - can swing a pick)
        #    Team that needs RB gets +25 for RB, team that doesn't gets +0
        need_bonus = eval.need_score * 25 * gm_rookie_pref

        # 4. Scheme fit bonus
        scheme_bonus = eval.scheme_fit * 8

        # 5. Upside bonus (young players with potential)
        upside_bonus = eval.upside_score * 5

        # 6. Risk penalties
        risk_penalty = eval.injury_risk * 10 + eval.character_risk * 8

        # 7. FA penalty for positions better signed than drafted
        fa_penalty = 0
        if not is_draft_priority_position(position):
            fa_penalty = 5  # Small penalty for RB, CB (sign in FA)

        # 8. Scarcity penalty for over-drafting same position
        # Prevents AI from drafting 4 OL in a row just because OL has high value
        scarcity_penalty = self._get_scarcity_penalty(position)

        # Combine all factors
        adjusted_value = (
            talent_score
            + position_bonus
            + need_bonus
            + scheme_bonus
            + upside_bonus
            - risk_penalty
            - fa_penalty
            - scarcity_penalty
        )

        return max(0, adjusted_value)

    def _get_scarcity_penalty(self, position: str) -> float:
        """
        Calculate penalty for over-drafting a position.

        Penalizes drafting the same position multiple times to ensure
        roster diversity. Based on DRAFT_AI_CONSTRAINTS.md:
        - 1st pick at position: 1.0x (no penalty)
        - 2nd pick at position: 0.7x
        - 3rd pick at position: 0.5x
        - 4th+ pick at position: 0.2x

        We convert these to penalties: 0, 8, 15, 25 points.
        """
        # Map specific position to position group for scarcity
        # (e.g., LT, LG, C, RG, RT all count as OL)
        group, _ = POSITION_TO_GROUP.get(position, (position, "offense"))

        times_drafted = self._positions_drafted.get(group, 0)

        # Scarcity penalty curve
        if times_drafted == 0:
            return 0  # First pick - no penalty
        elif times_drafted == 1:
            return 8  # Second pick - small penalty
        elif times_drafted == 2:
            return 15  # Third pick - moderate penalty
        else:
            return 25  # Fourth+ pick - heavy penalty

    def _record_draft_pick(self, position: str) -> None:
        """Record that we drafted a position (for scarcity tracking)."""
        group, _ = POSITION_TO_GROUP.get(position, (position, "offense"))
        self._positions_drafted[group] = self._positions_drafted.get(group, 0) + 1

    def reset_draft_tracking(self) -> None:
        """Reset position tracking for a new draft."""
        self._positions_drafted = {}

    def _calculate_scheme_fit(self, player: "Player") -> float:
        """
        Calculate how well player fits team scheme (HC09-style).

        Uses the player's archetype and the team's offensive/defensive scheme
        to determine scheme fit. A Power RB fits a Power Run team, etc.

        Returns:
            0.0-1.0 scheme fit score
        """
        if self.identity is None:
            return 0.5  # Neutral if no identity

        # Get team's offensive and defensive schemes
        offensive_scheme = getattr(self.identity, 'offensive_scheme', None)
        defensive_scheme = getattr(self.identity, 'defensive_scheme', None)

        # Use HC09-style archetype scheme fit calculation
        scheme_bonus = get_scheme_fit_bonus(
            player,
            offensive_scheme=offensive_scheme,
            defensive_scheme=defensive_scheme,
        )

        # Convert bonus (-3 to +5) to 0-1 scale
        # -3 = 0.2, 0 = 0.5, +5 = 1.0
        fit_score = 0.5 + (scheme_bonus / 10.0)
        return max(0.0, min(1.0, fit_score))

    def _calculate_upside(self, player: "Player") -> float:
        """Calculate development upside."""
        # Young players with gap between overall and potential have upside
        # This is simplified - would use potential system

        # Age factor (younger = more upside)
        age_factor = max(0, (24 - player.age) / 6)  # Peak upside at 21, none at 27

        # Physical attributes matter for upside
        speed = player.attributes.get("speed", 50)
        athleticism_factor = (speed - 50) / 50

        upside = 0.3 + (age_factor * 0.4) + (athleticism_factor * 0.3)
        return max(0.0, min(1.0, upside))

    def _calculate_floor(self, player: "Player") -> float:
        """Calculate safe floor/guaranteed production."""
        # High overall = high floor
        overall_factor = (player.overall - 50) / 50

        # Mental attributes indicate floor
        awareness = player.attributes.get("awareness", 50)
        mental_factor = (awareness - 50) / 50

        # Older prospects have more known floor
        age_factor = min(1.0, (player.age - 20) / 4)

        floor = 0.3 + (overall_factor * 0.4) + (mental_factor * 0.15) + (age_factor * 0.15)
        return max(0.0, min(1.0, floor))

    def _assess_injury_risk(self, player: "Player") -> float:
        """Assess injury/durability risk."""
        # Check durability attributes
        avg_durability = 0
        durability_attrs = [
            "head_durability",
            "torso_durability",
            "left_leg_durability",
            "right_leg_durability",
            "left_arm_durability",
            "right_arm_durability",
        ]

        count = 0
        for attr in durability_attrs:
            if attr in player.attributes:
                avg_durability += player.attributes[attr]
                count += 1

        if count > 0:
            avg_durability /= count
        else:
            avg_durability = 75  # Default

        # Lower durability = higher risk
        risk = (100 - avg_durability) / 100

        # Check injury history
        if hasattr(player, "injury_history") and player.injury_history:
            risk += len(player.injury_history) * 0.1

        return max(0.0, min(1.0, risk))

    def rank_prospects(
        self,
        prospects: list["Player"],
        pick_number: int,
    ) -> list[ProspectEvaluation]:
        """
        Rank available prospects by draft value.

        Returns sorted list of evaluations, best first.
        """
        evaluations = [self.evaluate_prospect(p, pick_number) for p in prospects]

        # Sort by draft value, descending
        evaluations.sort(key=lambda e: e.draft_value, reverse=True)

        return evaluations

    def select_player(
        self,
        available: list["Player"],
        pick_number: int,
    ) -> Optional["Player"]:
        """
        Select the best player from available prospects.

        Args:
            available: List of undrafted players
            pick_number: Current pick number

        Returns:
            Player to select, or None if should trade out
        """
        if not available:
            return None

        rankings = self.rank_prospects(available, pick_number)

        if not rankings:
            return None

        best = rankings[0]

        # Check if value is sufficient
        pick_value = get_pick_value(pick_number)
        expected_grade = self._pick_to_expected_grade(pick_number)

        # If best available is significantly below expectations, might pass
        if best.raw_grade < expected_grade * self.config.value_threshold:
            # Could consider trade down here
            # For now, still pick best available
            pass

        # Filter by risk tolerance
        if best.injury_risk > self.config.injury_risk_tolerance:
            # Look for safer option
            for eval in rankings[1:5]:
                if eval.injury_risk <= self.config.injury_risk_tolerance:
                    best = eval
                    break

        # Find the actual player
        for player in available:
            if str(player.id) == best.player_id:
                # Update needs
                self.needs.decrease_need(player.position.value)
                # Track position for scarcity penalty
                self._record_draft_pick(player.position.value)
                return player

        # Fallback to first available
        if available:
            self._record_draft_pick(available[0].position.value)
        return available[0] if available else None

    def _pick_to_expected_grade(self, pick_number: int) -> float:
        """Get expected player grade for a pick position."""
        # Roughly: Pick 1 expects ~85 OVR, Pick 32 expects ~72, Pick 224 expects ~55
        if pick_number <= 32:
            return 85 - (pick_number - 1) * 0.4
        elif pick_number <= 100:
            return 72 - (pick_number - 32) * 0.15
        else:
            return max(50, 60 - (pick_number - 100) * 0.05)

    def should_trade_up(
        self,
        target_pick: int,
        current_pick: int,
        target_player: "Player",
        inventory: DraftPickInventory,
        position_plan: Optional["PositionPlan"] = None,
    ) -> bool:
        """
        Evaluate if team should trade up for a player.

        Args:
            target_pick: Pick number to acquire
            current_pick: Team's current pick
            target_player: Player they want
            inventory: Team's draft pick inventory
            position_plan: Team's position acquisition plan (for commitment awareness)
        """
        # Evaluate player
        evaluation = self.evaluate_prospect(target_player, target_pick)

        # Base threshold for trading up
        base_threshold = 80

        # Commitment-aware threshold adjustment
        if position_plan:
            # Import here to avoid circular imports
            from huddle.core.ai.position_planner import AcquisitionPath

            need = position_plan.needs.get(target_player.position.value)
            if need and need.acquisition_path == AcquisitionPath.DRAFT_EARLY:
                # Team PLANNED to draft this position early - lower threshold
                base_threshold = 75

                # If this is their specific target, even more willing
                if need.target_player_id and str(need.target_player_id) == str(target_player.id):
                    base_threshold = 70
            elif need and need.acquisition_path in {AcquisitionPath.FREE_AGENCY, AcquisitionPath.KEEP_CURRENT}:
                # Team didn't plan to draft this position - higher threshold
                base_threshold = 90

        # Is player worth it?
        if evaluation.draft_value < base_threshold:
            return False  # Not worth trading up for

        # Can we afford it?
        current_value = get_pick_value(current_pick)
        target_value = get_pick_value(target_pick)

        value_needed = target_value - current_value

        # Check available assets
        available_value = sum(
            p.estimated_value
            for p in inventory.picks
            if p.current_team_id == self.team_id and p.pick_number != current_pick
        )

        if available_value < value_needed * 0.8:  # Need 80% of value
            return False

        # Status affects willingness
        if self.status.current_status in {TeamStatus.DYNASTY, TeamStatus.CONTENDING}:
            # More willing to trade picks
            return True
        elif self.status.current_status == TeamStatus.REBUILDING:
            # Protect assets unless it's a generational talent
            return evaluation.draft_value >= 95

        return evaluation.draft_value >= 85

    def should_trade_down(
        self,
        current_pick: int,
        best_available: ProspectEvaluation,
        position_plan: Optional["PositionPlan"] = None,
        available_prospects: list = None,
    ) -> bool:
        """
        Evaluate if team should trade down from current pick.

        Args:
            current_pick: Team's current pick
            best_available: Best player evaluation at this spot
            position_plan: Team's position acquisition plan (for commitment awareness)
            available_prospects: List of available prospects (for checking plan targets)
        """
        expected = self._pick_to_expected_grade(current_pick)

        # Commitment-aware check: if planned position is available, DON'T trade down
        if position_plan:
            from huddle.core.ai.position_planner import AcquisitionPath

            # Check if best available matches a DRAFT_EARLY/MID position
            best_pos = getattr(best_available, 'position', None)
            if best_pos:
                need = position_plan.needs.get(best_pos)
                if need and need.acquisition_path in {AcquisitionPath.DRAFT_EARLY, AcquisitionPath.DRAFT_MID}:
                    # This is a planned position - DON'T trade down
                    return False

            # If NO planned positions are available at this pick, MORE willing to trade down
            if available_prospects:
                has_planned_target = any(
                    p for p in position_plan.draft_board
                    if any(ap.player_id == p.player_id for ap in available_prospects)
                    and p.grade >= expected * 0.8  # Available and good enough
                )
                if not has_planned_target:
                    # No good targets from our board - strongly prefer trading down
                    if self.status.current_status not in {TeamStatus.DYNASTY, TeamStatus.CONTENDING}:
                        return True

        # If best available is below threshold, consider trading down
        if best_available.raw_grade < expected * self.config.trade_down_threshold:
            # Status affects decision
            if self.status.current_status == TeamStatus.REBUILDING:
                return True  # Rebuilding teams love extra picks
            elif self.status.current_status in {TeamStatus.DYNASTY, TeamStatus.CONTENDING}:
                return False  # Contenders need talent now

            return random.random() < 0.5  # 50/50 for neutral teams

        return False

    def wants_to_trade_up_here(
        self,
        current_pick: int,
        my_pick: int,
        mock: "MockDraft",
        available: List["Player"],
        position_plan: Optional["PositionPlan"] = None,
        fall_probability: float = 0.20,
    ) -> Optional["Player"]:
        """
        Determine if this team needs to trade up to the current pick.

        Returns the player we want to trade up for, or None if no urgency.

        Logic:
        1. Get our top draft target from position plan (or BPA if no plan)
        2. Check if they're still available
        3. Check if consensus says they'll be gone before our pick
        4. Factor in noise (20% chance they fall)
        5. If urgent, return the target player

        Args:
            current_pick: The pick currently on the clock
            my_pick: Our next pick number
            mock: MockDraft consensus
            available: Currently available players
            position_plan: Team's position acquisition plan
            fall_probability: Chance the player falls past projection

        Returns:
            Player to trade up for, or None
        """
        if my_pick <= current_pick:
            return None  # We pick before or at this spot

        # Find our top target
        target_player = None
        target_priority = 0.0

        if position_plan:
            # Check position plan for DRAFT_EARLY targets
            from huddle.core.ai.position_planner import AcquisitionPath

            for pos, need in position_plan.needs.items():
                if need.acquisition_path == AcquisitionPath.DRAFT_EARLY:
                    # Find best available at this position
                    for player in available:
                        if player.position.value == pos:
                            # Check if this is our guy
                            if target_player is None or player.overall > target_player.overall:
                                target_player = player
                                target_priority = 0.9  # High priority for planned position
                            break

                    # Check for specific target
                    if need.target_player_id:
                        for player in available:
                            if str(player.id) == str(need.target_player_id):
                                target_player = player
                                target_priority = 1.0  # Max priority for specific target
                                break

        # Fallback to BPA if no plan or no plan target found
        if target_player is None:
            # Use our ranking to find top target
            rankings = self.rank_prospects(available[:20], current_pick)  # Top 20 for speed
            if rankings and rankings[0].draft_value >= 80:
                for player in available:
                    if str(player.id) == rankings[0].player_id:
                        target_player = player
                        target_priority = 0.7  # Lower priority for BPA
                        break

        if target_player is None:
            return None

        # Check consensus: will this player be gone before our pick?
        consensus_pick = mock.get_consensus_pick(str(target_player.id))

        picks_until_mine = my_pick - current_pick
        picks_until_target_gone = consensus_pick - current_pick

        if picks_until_target_gone >= picks_until_mine:
            # Consensus says he'll still be there
            return None

        # Target is projected to go before our pick!
        # But add noise - maybe he falls
        if random.random() < fall_probability:
            # We think he might fall, don't trade up
            return None

        # Check if we should actually trade up (use existing method)
        evaluation = self.evaluate_prospect(target_player, current_pick)

        # Adjust threshold based on priority
        base_threshold = 80
        if target_priority >= 1.0:
            base_threshold = 70  # Specific target - very willing
        elif target_priority >= 0.9:
            base_threshold = 75  # Planned position - willing

        if evaluation.draft_value < base_threshold:
            return None  # Not worth it

        # Status check
        if self.status.current_status == TeamStatus.REBUILDING:
            # Rebuilding - only trade up for elite talent
            if evaluation.draft_value < 92:
                return None
        elif self.status.current_status == TeamStatus.WINDOW_CLOSING:
            # Window closing - more willing to trade up for immediate help
            if evaluation.floor_score < 0.5:
                return None  # Need safe floor

        return target_player

    def generate_trade_up_package(
        self,
        target_pick: int,
        my_pick: int,
        inventory: DraftPickInventory,
        value_threshold: float = 0.85,
    ) -> Optional[List[DraftPick]]:
        """
        Build a package of picks to trade up.

        Uses pick value chart to determine fair value, then builds a package
        from available picks.

        Args:
            target_pick: Pick number we want to acquire
            my_pick: Our current pick number
            inventory: Our draft pick inventory
            value_threshold: Minimum value ratio to consider a package (0.85 = 85% of target value)

        Returns:
            List of DraftPick objects to offer, or None if can't afford
        """
        target_value = get_pick_value(target_pick)
        my_pick_value = get_pick_value(my_pick)

        # We always include our pick in the package
        # Additional picks make up the difference
        value_needed = target_value - my_pick_value

        if value_needed <= 0:
            # Our pick is worth more - weird but just offer our pick
            return None  # Should use different trade logic

        # Collect available picks (exclude our current pick - it's the trade centerpiece)
        available_picks = []
        for pick in inventory.picks:
            if pick.current_team_id == self.team_id:
                if pick.pick_number != my_pick and not pick.is_compensatory:
                    available_picks.append(pick)

        # Sort by value (prefer using later picks first to preserve capital)
        available_picks.sort(key=lambda p: p.estimated_value)

        # Build package
        package_value = 0
        package_picks = []

        for pick in available_picks:
            if package_value >= value_needed * value_threshold:
                break  # Have enough

            # Check if this pick is committed in position plan
            # (We don't want to trade a pick we planned to use for a specific position)
            commitment = 1.0
            # Skip highly committed picks
            if commitment > 1.3:
                continue

            package_picks.append(pick)
            package_value += pick.estimated_value

        # Check if we have enough
        if package_value < value_needed * value_threshold:
            return None  # Can't afford

        # Return our pick + the package
        # (The actual my_pick will be added by the caller)
        return package_picks

    def evaluate_trade_down_offer(
        self,
        offered_picks: List[DraftPick],
        current_pick_value: int,
        best_available: ProspectEvaluation,
        position_plan: Optional["PositionPlan"] = None,
        mock: Optional["MockDraft"] = None,
    ) -> Tuple[bool, str]:
        """
        Evaluate if a trade-down offer is acceptable.

        Args:
            offered_picks: Picks being offered for our pick
            current_pick_value: Value of our current pick
            best_available: Best player available at our spot
            position_plan: Our position acquisition plan
            mock: Mock draft for projections

        Returns:
            (accept: bool, reason: str)
        """
        offered_value = sum(p.estimated_value for p in offered_picks)
        value_ratio = offered_value / max(1, current_pick_value)

        # Check if we want to trade down in the first place
        if position_plan:
            from huddle.core.ai.position_planner import AcquisitionPath

            # Check if best available matches a planned position
            best_pos = getattr(best_available, 'position', None)
            if best_pos:
                need = position_plan.needs.get(best_pos)
                if need and need.acquisition_path in {AcquisitionPath.DRAFT_EARLY, AcquisitionPath.DRAFT_MID}:
                    # This is our guy - don't trade down unless GREAT value
                    if value_ratio < 1.20:  # Need 20% premium
                        return False, f"Want to draft {best_pos}, offered value too low ({value_ratio:.0%})"

        # Status affects willingness
        min_ratio = 0.90  # Default

        if self.status.current_status == TeamStatus.REBUILDING:
            min_ratio = 0.80  # Love extra picks, accept less
        elif self.status.current_status in {TeamStatus.DYNASTY, TeamStatus.CONTENDING}:
            min_ratio = 1.00  # Need full value or more
        elif self.status.current_status == TeamStatus.WINDOW_CLOSING:
            min_ratio = 1.05  # Premium required - need talent NOW

        if value_ratio < min_ratio:
            return False, f"Value ratio {value_ratio:.0%} below threshold {min_ratio:.0%}"

        # Check if there's talent worth keeping
        expected_grade = self._pick_to_expected_grade(offered_picks[0].pick_number if offered_picks else 32)
        if best_available.raw_grade >= expected_grade + 10:
            # Elite talent available - less willing to move
            if value_ratio < 1.15:
                return False, f"Elite talent available ({best_available.raw_grade}), need premium"

        # Check upcoming picks - is there a run on positions we don't need?
        if mock and position_plan:
            upcoming = mock.get_next_n_projected(offered_picks[0].pick_number if offered_picks else 32, 5, set())
            positions_i_need = [
                p for p in upcoming
                if position_plan.needs.get(p.position) and
                position_plan.needs[p.position].acquisition_path in {
                    AcquisitionPath.DRAFT_EARLY,
                    AcquisitionPath.DRAFT_MID,
                }
            ]
            if len(positions_i_need) == 0:
                # None of the next picks help us - more willing to trade down
                min_ratio -= 0.10
                if value_ratio >= min_ratio:
                    return True, "No targets in range, accepting trade down"

        if value_ratio >= min_ratio:
            return True, f"Good value ({value_ratio:.0%})"

        return False, f"Value ratio {value_ratio:.0%} below adjusted threshold"


def calculate_team_needs(
    roster: list["Player"],
    depth_chart: dict[str, list[str]] = None,
) -> TeamNeeds:
    """
    Calculate team needs based on current roster.

    Args:
        roster: Current team roster
        depth_chart: Optional depth chart for position importance

    Returns:
        TeamNeeds with calculated need levels
    """
    needs = TeamNeeds()

    # Count players by position
    position_counts: dict[str, int] = {}
    position_quality: dict[str, int] = {}  # Sum of overalls

    for player in roster:
        pos = player.position.value
        position_counts[pos] = position_counts.get(pos, 0) + 1
        position_quality[pos] = position_quality.get(pos, 0) + player.overall

    # Ideal roster composition
    IDEAL_COUNTS = {
        "QB": 3,
        "RB": 4,
        "WR": 6,
        "TE": 3,
        "FB": 1,
        "LT": 2,
        "LG": 2,
        "C": 2,
        "RG": 2,
        "RT": 2,
        "DE": 4,
        "DT": 3,
        "NT": 1,
        "OLB": 4,
        "ILB": 3,
        "MLB": 2,
        "CB": 5,
        "FS": 2,
        "SS": 2,
        "S": 2,
        "K": 1,
        "P": 1,
    }

    for pos, ideal in IDEAL_COUNTS.items():
        current = position_counts.get(pos, 0)

        if current == 0:
            # Desperate need
            needs.set_need(pos, 1.0)
        elif current < ideal:
            # Some need
            shortage = (ideal - current) / ideal
            needs.set_need(pos, min(0.9, 0.3 + shortage * 0.5))
        else:
            # Have enough, check quality
            avg_quality = position_quality.get(pos, 0) / current if current > 0 else 50
            if avg_quality < 65:
                # Low quality, still need upgrade
                needs.set_need(pos, 0.4)
            elif avg_quality < 75:
                needs.set_need(pos, 0.2)
            else:
                needs.set_need(pos, 0.1)  # Well stocked

    # QB is always important if you don't have a good one
    qb_quality = position_quality.get("QB", 0) / max(1, position_counts.get("QB", 1))
    if qb_quality < 75:
        needs.set_need("QB", max(needs.get_need("QB"), 0.7))

    return needs


# =============================================================================
# Mock Draft System - Consensus Projections for Draft Day Trades
# =============================================================================


@dataclass
class MockDraftEntry:
    """A single entry in the mock draft consensus."""
    player_id: str
    player_name: str
    position: str
    grade: float
    consensus_pick: int  # Where consensus says this player goes

    def __hash__(self):
        return hash(self.player_id)


@dataclass
class MockDraft:
    """
    League-wide draft consensus projection with per-team noise.

    Before the draft, generate a consensus mock draft that all teams reference
    (with noise). This drives trade-up urgency - teams trade up because
    "my guy will be gone before my pick."
    """
    season: int
    consensus: List[MockDraftEntry]  # Sorted by consensus_pick
    team_views: Dict[str, List[MockDraftEntry]]  # Team-specific boards (with noise)

    def get_consensus_pick(self, player_id: str) -> int:
        """Where does consensus say this player goes?"""
        for entry in self.consensus:
            if entry.player_id == player_id:
                return entry.consensus_pick
        return 999  # Not found = very late

    def get_team_view_pick(self, team_id: str, player_id: str) -> int:
        """Where does THIS team think the player goes?"""
        team_board = self.team_views.get(team_id, self.consensus)
        for idx, entry in enumerate(team_board):
            if entry.player_id == player_id:
                return idx + 1  # 1-indexed pick number
        return 999

    def get_available_at_pick(self, pick_number: int, already_drafted: set) -> List[MockDraftEntry]:
        """Get players consensus projects as available at this pick."""
        return [
            e for e in self.consensus
            if e.player_id not in already_drafted and e.consensus_pick >= pick_number
        ]

    def get_next_n_projected(self, current_pick: int, n: int, already_drafted: set) -> List[MockDraftEntry]:
        """Get the next N projected picks from consensus."""
        available = [
            e for e in self.consensus
            if e.player_id not in already_drafted
        ]
        # Sort by consensus pick
        available.sort(key=lambda e: e.consensus_pick)
        return available[:n]


def generate_mock_draft(
    prospects: List["Player"],
    teams: Dict[str, "TeamState"],
    noise_factor: float = 0.15,
) -> MockDraft:
    """
    Generate a mock draft consensus with per-team noise.

    1. Sort prospects by grade → consensus order
    2. For each team, shuffle based on:
       - Scheme fit preferences
       - GM archetype (analytics vs old school)
       - Random noise (±5 spots)

    Args:
        prospects: List of Player objects in the draft class
        teams: Dict of team_id -> TeamState
        noise_factor: How much teams disagree on rankings (0.0-0.3)

    Returns:
        MockDraft with consensus and team-specific views
    """
    # Build consensus order (sorted by player grade/overall)
    sorted_prospects = sorted(prospects, key=lambda p: p.overall, reverse=True)

    consensus = []
    for idx, player in enumerate(sorted_prospects):
        consensus.append(MockDraftEntry(
            player_id=str(player.id),
            player_name=player.full_name,
            position=player.position.value,
            grade=player.overall,
            consensus_pick=idx + 1,  # 1-indexed
        ))

    # Generate team-specific views with noise
    team_views = {}

    for team_id, team_state in teams.items():
        team_board = []

        for entry in consensus:
            # Apply noise to consensus pick
            # Teams can see a player ±5 picks from consensus
            noise_range = int(len(consensus) * noise_factor)
            noise = random.randint(-noise_range, noise_range)

            # GM archetype affects how much noise
            # Analytics GMs are closer to consensus
            # Old school GMs have more variance
            if team_state.gm_archetype:
                from huddle.core.ai.gm_archetypes import GMArchetype
                if team_state.gm_archetype == GMArchetype.ANALYTICS:
                    noise = int(noise * 0.6)  # Less noise
                elif team_state.gm_archetype == GMArchetype.OLD_SCHOOL:
                    noise = int(noise * 1.4)  # More noise

            # Position preferences based on team needs
            position = entry.position
            needs = calculate_team_needs(team_state.roster) if team_state.roster else TeamNeeds()
            need_level = needs.get_need(position)

            # High need = rank player higher (negative noise)
            if need_level > 0.7:
                noise -= 3
            elif need_level > 0.5:
                noise -= 1
            elif need_level < 0.2:
                noise += 2  # Don't need, rank lower

            team_board.append(MockDraftEntry(
                player_id=entry.player_id,
                player_name=entry.player_name,
                position=entry.position,
                grade=entry.grade,
                consensus_pick=max(1, entry.consensus_pick + noise),
            ))

        # Sort by adjusted consensus pick
        team_board.sort(key=lambda e: e.consensus_pick)
        team_views[team_id] = team_board

    # Get season from first team
    season = 2024
    for team_state in teams.values():
        if hasattr(team_state, 'current_season'):
            season = team_state.current_season
            break

    return MockDraft(
        season=season,
        consensus=consensus,
        team_views=team_views,
    )
