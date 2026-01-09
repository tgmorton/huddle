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
from typing import TYPE_CHECKING, Optional
import random

from huddle.core.draft.picks import DraftPick, DraftPickInventory, get_pick_value
from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    DraftPhilosophy,
    PersonnelPreference,
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

        # Raw grade from player attributes
        raw_grade = player.overall

        # Scheme fit based on team identity
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
        """Calculate how well player fits team scheme."""
        if self.identity is None:
            return 0.5  # Neutral if no identity

        # Get attribute emphasis from team identity
        emphasis = self.identity.get_attribute_emphasis(player.position.value)

        if not emphasis:
            return 0.5  # Neutral if no emphasis defined

        # Check how player's attributes align with emphasis
        fit_score = 0.5  # Start neutral
        for attr, mult in emphasis.items():
            attr_value = player.attributes.get(attr, 50)
            # High attribute + high emphasis = good fit
            if mult > 1.0 and attr_value >= 75:
                fit_score += 0.1
            elif mult > 1.0 and attr_value < 60:
                fit_score -= 0.1
            elif mult < 1.0 and attr_value >= 80:
                fit_score -= 0.05  # Overqualified in non-priority area

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
    ) -> bool:
        """
        Evaluate if team should trade up for a player.

        Args:
            target_pick: Pick number to acquire
            current_pick: Team's current pick
            target_player: Player they want
            inventory: Team's draft pick inventory
        """
        # Evaluate player
        evaluation = self.evaluate_prospect(target_player, target_pick)

        # Is player worth it?
        if evaluation.draft_value < 80:
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
    ) -> bool:
        """
        Evaluate if team should trade down from current pick.

        Args:
            current_pick: Team's current pick
            best_available: Best player evaluation at this spot
        """
        expected = self._pick_to_expected_grade(current_pick)

        # If best available is below threshold, consider trading down
        if best_available.raw_grade < expected * self.config.trade_down_threshold:
            # Status affects decision
            if self.status.current_status == TeamStatus.REBUILDING:
                return True  # Rebuilding teams love extra picks
            elif self.status.current_status in {TeamStatus.DYNASTY, TeamStatus.CONTENDING}:
                return False  # Contenders need talent now

            return random.random() < 0.5  # 50/50 for neutral teams

        return False


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
