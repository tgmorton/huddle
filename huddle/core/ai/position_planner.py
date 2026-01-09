"""
Position Planner - HC09-Style Holistic Team Building.

GMs don't evaluate FA/Draft in isolation. They create a unified plan:
1. Assess current roster needs
2. Scout draft class for each position
3. Evaluate FA market for each position
4. Decide BEST PATH to fill each need (draft, FA, or keep current)

This creates realistic behaviors:
- Team with #1 pick + elite QB prospect sits out QB FA
- Team with no draft options at CB goes aggressive in CB FA
- Team decides "I'll get my guard in round 3, chase EDGE in FA"

Based on HC09 approach where GMs rank all players across markets.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import random

from huddle.core.ai.gm_archetypes import GMProfile, GMArchetype


class AcquisitionPath(Enum):
    """How the GM plans to fill a position."""
    KEEP_CURRENT = "keep_current"       # Current player is good enough
    FREE_AGENCY = "free_agency"         # Target FA market
    DRAFT_EARLY = "draft_early"         # Use early pick (rounds 1-2)
    DRAFT_MID = "draft_mid"             # Use mid pick (rounds 3-4)
    DRAFT_LATE = "draft_late"           # Use late pick (rounds 5-7)
    TRADE = "trade"                     # Pursue trade
    UNDECIDED = "undecided"             # Still evaluating


@dataclass
class PositionNeed:
    """Assessment of need at a position."""
    position: str

    # Current roster state (0-100)
    current_starter_overall: int = 0
    current_depth_count: int = 0

    # Need level (0-1, higher = more urgent)
    need_score: float = 0.0

    # Best options by market
    best_fa_option: Optional[dict] = None      # {player_id, name, overall, asking_price}
    best_draft_option: Optional[dict] = None   # {player_id, name, projected_round, grade}

    # GM's chosen path
    acquisition_path: AcquisitionPath = AcquisitionPath.UNDECIDED
    target_player_id: Optional[UUID] = None

    # Budget allocated (cap % for FA, pick value for draft)
    budget_allocated: float = 0.0


@dataclass
class DraftProspect:
    """A prospect in the upcoming draft."""
    player_id: UUID
    name: str
    position: str
    grade: float              # Scout grade (0-100)
    projected_round: int      # 1-7
    projected_pick: int       # 1-256

    # Team-specific evaluation
    scheme_fit: float = 0.5   # 0-1
    character_grade: float = 0.5

    def __repr__(self):
        return f"{self.name} ({self.position}) - Rd{self.projected_round}, Grade {self.grade:.0f}"


@dataclass
class PositionPlan:
    """
    A GM's complete plan for filling roster needs.

    Created at start of offseason, updated as FA/Draft progresses.
    """
    team_id: UUID
    gm_profile: GMProfile
    draft_position: int        # 1-32
    cap_room: int             # Available cap space

    # Position assessments
    needs: Dict[str, PositionNeed] = field(default_factory=dict)

    # Draft board (team's ranked prospects)
    draft_board: List[DraftProspect] = field(default_factory=list)

    # FA targets (ranked by priority)
    fa_targets: List[dict] = field(default_factory=list)

    # Decisions made
    fa_acquisitions: List[dict] = field(default_factory=list)
    draft_picks_used: List[dict] = field(default_factory=list)


def assess_position_need(
    position: str,
    current_starter_overall: int,
    current_depth: int,
    gm_profile: GMProfile,
) -> float:
    """
    Calculate how much a team needs help at a position.

    Returns 0-1 score (higher = more urgent need).
    """
    # Base need from starter quality
    if current_starter_overall >= 90:
        base_need = 0.0  # Elite, no need
    elif current_starter_overall >= 85:
        base_need = 0.1  # Very good
    elif current_starter_overall >= 80:
        base_need = 0.3  # Solid starter
    elif current_starter_overall >= 75:
        base_need = 0.5  # Average
    elif current_starter_overall >= 70:
        base_need = 0.7  # Below average
    else:
        base_need = 0.9  # Major need

    # Depth factor (lack of depth increases need)
    if current_depth <= 1:
        base_need = min(1.0, base_need + 0.2)

    # GM archetype adjustments
    if gm_profile.archetype == GMArchetype.WIN_NOW:
        # Win now GMs more sensitive to needs
        base_need = min(1.0, base_need * 1.2)
    elif gm_profile.archetype == GMArchetype.CAP_WIZARD:
        # Cap wizards tolerate lower quality if cheap
        base_need *= 0.9

    return base_need


def evaluate_draft_path(
    need: PositionNeed,
    draft_position: int,
    draft_prospects: List[DraftProspect],
    gm_profile: GMProfile,
) -> Tuple[AcquisitionPath, Optional[DraftProspect], float]:
    """
    Evaluate if draft is the best path to fill a need.

    Returns (path, target_prospect, confidence)
    """
    position = need.position

    # Find best prospects at this position
    position_prospects = [p for p in draft_prospects if p.position == position]
    position_prospects.sort(key=lambda p: -p.grade)

    if not position_prospects:
        return AcquisitionPath.UNDECIDED, None, 0.0

    best_prospect = position_prospects[0]

    # Can we realistically get them?
    pick_buffer = 5  # How many picks before our selection

    if best_prospect.projected_pick <= draft_position + pick_buffer:
        # High confidence we can get them
        if best_prospect.projected_round <= 2:
            path = AcquisitionPath.DRAFT_EARLY
        elif best_prospect.projected_round <= 4:
            path = AcquisitionPath.DRAFT_MID
        else:
            path = AcquisitionPath.DRAFT_LATE

        # Confidence based on how far ahead of projection we pick
        margin = best_prospect.projected_pick - draft_position
        if margin > 10:
            confidence = 0.95  # Very likely to get them
        elif margin > 0:
            confidence = 0.80
        elif margin > -5:
            confidence = 0.50  # Might get them
        else:
            confidence = 0.20  # Risky

        # GM archetype adjustment
        if gm_profile.archetype == GMArchetype.ANALYTICS:
            # Analytics GMs love draft value
            confidence *= 1.1
        elif gm_profile.archetype == GMArchetype.OLD_SCHOOL:
            # Old school may prefer "proven" FA
            confidence *= 0.9

        return path, best_prospect, min(1.0, confidence)

    # Look for later round options
    for prospect in position_prospects[1:]:
        if prospect.projected_pick >= draft_position:
            if prospect.projected_round <= 4:
                path = AcquisitionPath.DRAFT_MID
            else:
                path = AcquisitionPath.DRAFT_LATE
            return path, prospect, 0.6

    return AcquisitionPath.UNDECIDED, None, 0.0


def evaluate_fa_path(
    need: PositionNeed,
    fa_options: List[dict],
    cap_room: int,
    gm_profile: GMProfile,
) -> Tuple[AcquisitionPath, Optional[dict], float]:
    """
    Evaluate if FA is the best path to fill a need.

    Returns (path, target_fa, confidence)
    """
    position = need.position

    # Find FAs at this position
    position_fas = [fa for fa in fa_options if fa.get('position') == position]

    if not position_fas:
        return AcquisitionPath.UNDECIDED, None, 0.0

    # Sort by value (overall / asking_price ratio)
    for fa in position_fas:
        asking = fa.get('asking_price', 1)
        overall = fa.get('overall', 70)
        fa['value_ratio'] = overall / max(1, asking / 1000)  # Normalize

    position_fas.sort(key=lambda fa: -fa['value_ratio'])

    best_fa = position_fas[0]

    # Can we afford them?
    if best_fa.get('asking_price', 0) > cap_room:
        # Look for cheaper options
        affordable = [fa for fa in position_fas if fa.get('asking_price', 0) <= cap_room]
        if not affordable:
            return AcquisitionPath.UNDECIDED, None, 0.0
        best_fa = affordable[0]

    # Is this FA better than current starter?
    fa_overall = best_fa.get('overall', 70)
    current_overall = need.current_starter_overall

    if fa_overall <= current_overall:
        # FA isn't an upgrade
        return AcquisitionPath.KEEP_CURRENT, None, 0.8

    upgrade = fa_overall - current_overall

    # Confidence based on upgrade size
    if upgrade >= 10:
        confidence = 0.95  # Clear upgrade
    elif upgrade >= 5:
        confidence = 0.75
    else:
        confidence = 0.50  # Marginal upgrade

    # GM archetype adjustments
    if gm_profile.archetype == GMArchetype.WIN_NOW:
        confidence *= 1.15  # Win now loves proven FA
    elif gm_profile.archetype == GMArchetype.CAP_WIZARD:
        # Cap wizard skeptical of FA prices
        confidence *= 0.85

    return AcquisitionPath.FREE_AGENCY, best_fa, min(1.0, confidence)


def create_position_plan(
    team_id: UUID,
    gm_profile: GMProfile,
    draft_position: int,
    cap_room: int,
    roster: Dict[str, dict],       # {position: {starter_overall, depth_count}}
    draft_prospects: List[DraftProspect],
    fa_options: List[dict],
) -> PositionPlan:
    """
    Create a complete offseason plan for a team.

    This is the HC09-style holistic planning where the GM decides
    BEFORE free agency which positions to target in FA vs draft.
    """
    plan = PositionPlan(
        team_id=team_id,
        gm_profile=gm_profile,
        draft_position=draft_position,
        cap_room=cap_room,
    )

    # Assess each position
    positions = ['QB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT',
                 'DE', 'DT', 'OLB', 'ILB', 'CB', 'FS', 'SS']

    for pos in positions:
        roster_info = roster.get(pos, {'starter_overall': 65, 'depth_count': 1})

        need = PositionNeed(
            position=pos,
            current_starter_overall=roster_info.get('starter_overall', 65),
            current_depth_count=roster_info.get('depth_count', 1),
        )

        # Calculate need score
        need.need_score = assess_position_need(
            pos,
            need.current_starter_overall,
            need.current_depth_count,
            gm_profile,
        )

        # Skip positions with no need
        if need.need_score < 0.2:
            need.acquisition_path = AcquisitionPath.KEEP_CURRENT
            plan.needs[pos] = need
            continue

        # Evaluate both paths
        draft_path, draft_target, draft_confidence = evaluate_draft_path(
            need, draft_position, draft_prospects, gm_profile
        )

        fa_path, fa_target, fa_confidence = evaluate_fa_path(
            need, fa_options, cap_room, gm_profile
        )

        # Store best options
        if draft_target:
            need.best_draft_option = {
                'player_id': draft_target.player_id,
                'name': draft_target.name,
                'projected_round': draft_target.projected_round,
                'grade': draft_target.grade,
            }

        if fa_target:
            need.best_fa_option = fa_target

        # Choose best path
        # Key insight: Compare PLAYER QUALITY and COST EFFICIENCY
        #
        # Draft advantages:
        # - Cheap contracts (rookie scale)
        # - Control for 4-5 years
        # - Higher upside if high grade
        #
        # FA advantages:
        # - Immediate impact (no development)
        # - Known quantity

        draft_grade = draft_target.grade if draft_target else 0
        fa_overall = fa_target.get('overall', 0) if fa_target else 0

        # Calculate effective value
        # Draft: grade * confidence * rookie_premium (cheap contracts are valuable!)
        # FA: overall * confidence * cost_penalty (expensive contracts hurt)
        rookie_value_mult = 1.5  # Rookie contracts provide ~1.5x value
        fa_cost_penalty = 0.85   # FA costs more

        draft_value = draft_confidence * (draft_grade / 100) * rookie_value_mult
        fa_value = fa_confidence * (fa_overall / 100) * fa_cost_penalty

        # Adjust for GM archetype preferences
        if gm_profile.archetype == GMArchetype.CAP_WIZARD:
            draft_value *= 1.4  # Loves draft value (rookie contracts)
            fa_value *= 0.8    # Skeptical of FA prices
        elif gm_profile.archetype == GMArchetype.WIN_NOW:
            draft_value *= 0.85  # Rookies need time
            fa_value *= 1.3      # Prefers immediate help
        elif gm_profile.archetype == GMArchetype.ANALYTICS:
            draft_value *= 1.2   # Understands rookie surplus
        elif gm_profile.archetype == GMArchetype.OLD_SCHOOL:
            fa_value *= 1.1      # Prefers "proven" players

        # Tiebreaker: If draft prospect is significantly better, prefer draft
        if draft_grade > fa_overall + 5:
            draft_value *= 1.2  # Quality bonus

        if draft_value > fa_value and draft_confidence >= 0.4:
            need.acquisition_path = draft_path
            if draft_target:
                need.target_player_id = draft_target.player_id
        elif fa_value > 0 and fa_confidence >= 0.4:
            need.acquisition_path = fa_path
            if fa_target:
                need.target_player_id = fa_target.get('player_id')
        else:
            need.acquisition_path = AcquisitionPath.UNDECIDED

        plan.needs[pos] = need

    # Build FA target list (positions where FA is the path)
    for pos, need in plan.needs.items():
        if need.acquisition_path == AcquisitionPath.FREE_AGENCY and need.best_fa_option:
            plan.fa_targets.append({
                'position': pos,
                'need_score': need.need_score,
                'target': need.best_fa_option,
            })

    # Sort FA targets by priority
    plan.fa_targets.sort(key=lambda x: -x['need_score'])

    # Build draft board (prospects for positions where draft is the path)
    draft_target_positions = {
        pos for pos, need in plan.needs.items()
        if need.acquisition_path in (AcquisitionPath.DRAFT_EARLY,
                                     AcquisitionPath.DRAFT_MID,
                                     AcquisitionPath.DRAFT_LATE)
    }

    # Add prospects for target positions to board
    for prospect in draft_prospects:
        if prospect.position in draft_target_positions:
            plan.draft_board.append(prospect)

    # Sort by grade
    plan.draft_board.sort(key=lambda p: -p.grade)

    return plan


def should_pursue_fa(
    plan: PositionPlan,
    fa_player: dict,
) -> Tuple[bool, float]:
    """
    Determine if a team should pursue a specific FA based on their plan.

    Returns (should_pursue, aggression)
    """
    position = fa_player.get('position')
    need = plan.needs.get(position)

    if not need:
        return False, 0.0

    # Check if FA is our planned path
    if need.acquisition_path == AcquisitionPath.FREE_AGENCY:
        # This is our target position!
        if need.target_player_id == fa_player.get('player_id'):
            # This is THE target
            return True, 0.9
        else:
            # Alternate option
            return True, 0.5

    elif need.acquisition_path in (AcquisitionPath.DRAFT_EARLY,
                                   AcquisitionPath.DRAFT_MID,
                                   AcquisitionPath.DRAFT_LATE):
        # We're planning to draft here - only pursue if FA is significantly better
        draft_grade = need.best_draft_option.get('grade', 0) if need.best_draft_option else 0
        fa_overall = fa_player.get('overall', 0)

        if fa_overall > draft_grade + 5:
            # FA is notably better - might pivot
            return True, 0.3
        else:
            # Stick to draft plan
            return False, 0.0

    elif need.acquisition_path == AcquisitionPath.KEEP_CURRENT:
        # No need here
        return False, 0.0

    # Undecided - moderate interest
    return True, 0.4


def update_plan_after_fa(
    plan: PositionPlan,
    signed_player: dict,
) -> None:
    """
    Update the plan after signing an FA.

    May change draft priorities.
    """
    position = signed_player.get('position')
    need = plan.needs.get(position)

    if need:
        # Position filled!
        need.acquisition_path = AcquisitionPath.KEEP_CURRENT
        need.need_score = 0.0

        # Remove from FA targets
        plan.fa_targets = [t for t in plan.fa_targets if t['position'] != position]

        # Remove from draft board
        plan.draft_board = [p for p in plan.draft_board if p.position != position]

        # Record acquisition
        plan.fa_acquisitions.append(signed_player)


def get_draft_target(
    plan: PositionPlan,
    available_prospects: List[DraftProspect],
) -> Optional[DraftProspect]:
    """
    Get the best available prospect based on team's plan.

    Prioritizes positions where draft was the chosen path.
    """
    # Filter to available
    available_ids = {p.player_id for p in available_prospects}
    board = [p for p in plan.draft_board if p.player_id in available_ids]

    if not board:
        # Fall back to BPA from available
        available_prospects.sort(key=lambda p: -p.grade)
        return available_prospects[0] if available_prospects else None

    # Get highest graded player from our board
    board.sort(key=lambda p: -p.grade)
    return board[0]
