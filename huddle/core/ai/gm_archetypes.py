"""
GM Archetype System.

Defines different AI GM personalities that affect player valuation,
draft strategy, and team-building philosophy.

Based on research findings from Calvetti (2023) and Mulholland-Jensen (2019):
- Market has systematic inefficiencies (LT overvalued, Guards undervalued)
- Rookie contracts provide ~2x value vs veterans
- Age is underweighted in salary prediction
- Position interactions affect optimal allocation

Integrates with allocation_tables.py for research-backed decision-making.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List
import random

# Import research-backed lookup tables
from huddle.core.ai.allocation_tables import (
    get_effective_salary,
    get_optimal_allocation,
    get_allocation_gap,
    get_position_priority,
    get_rookie_premium,
    OPTIMAL_ALLOCATION,
    ROOKIE_PREMIUM,
)


class GMArchetype(Enum):
    """Types of GM decision-making philosophies."""
    ANALYTICS = "analytics"       # Follows optimal allocation closely
    OLD_SCHOOL = "old_school"     # Traditional premiums, ignores analytics
    CAP_WIZARD = "cap_wizard"     # Maximizes effective salary arbitrage
    WIN_NOW = "win_now"           # Short-term optimization, trades future
    BALANCED = "balanced"         # Mix of approaches (default)


# Human-readable descriptions of each archetype
GM_DESCRIPTIONS = {
    "analytics": "Data-driven GM who follows research-backed allocation. Values interior OL, devalues premium positions like LT. Maximizes value per dollar.",
    "old_school": "Traditional GM who trusts the eye test. Pays premium for 'franchise' positions like LT and QB. Skeptical of analytics.",
    "cap_wizard": "Cap specialist who exploits rookie contract arbitrage. Builds through the draft, avoids big FA splashes. Always cap-healthy.",
    "win_now": "Aggressive GM willing to mortgage the future. Pays premium for proven veterans. Trades draft picks for immediate help.",
    "balanced": "Balanced approach mixing analytics with traditional scouting. Moderate spending, builds through both draft and FA.",
}


@dataclass
class GMProfile:
    """
    A GM's decision-making profile.

    Affects how they value players, approach free agency,
    and build their roster.
    """
    archetype: GMArchetype

    # Core traits (0-1 scale)
    analytics_weight: float = 0.5      # How much they trust analytics
    veteran_preference: float = 0.5    # Preference for veterans vs youth
    risk_tolerance: float = 0.5        # Willingness to take chances
    patience: float = 0.5              # Long-term vs short-term thinking

    # Position valuation adjustments (multipliers vs market)
    # >1 = values more than market, <1 = values less
    position_adjustments: dict = None

    # Draft/FA preferences
    rookie_premium: float = 1.0        # How much they value rookie contracts
    draft_pick_value: float = 1.0      # How they value future picks

    def __post_init__(self):
        if self.position_adjustments is None:
            self.position_adjustments = {}


# Pre-defined GM profiles based on research archetypes

ANALYTICS_GM = GMProfile(
    archetype=GMArchetype.ANALYTICS,
    analytics_weight=0.95,
    veteran_preference=0.3,    # Prefers youth (rookie surplus)
    risk_tolerance=0.6,
    patience=0.8,              # Long-term thinker
    position_adjustments={
        # Research-backed: correct market inefficiencies
        "LT": 0.75,    # Market overvalues (blind side myth)
        "RB": 0.70,    # Highly replaceable (0.8% optimal)
        "LG": 1.25,    # Market undervalues (12.4% optimal vs 5.8% actual)
        "RG": 1.25,
        "RT": 1.20,    # Undervalued (7.8% optimal vs 3.5% actual)
        "ILB": 1.20,   # Undervalued (10% optimal)
        "OLB": 1.15,   # Undervalued (15.2% optimal)
        "DT": 1.15,    # Interior D undervalued
        "DE": 1.10,
        "C": 1.10,     # Undervalued
        "QB": 0.90,    # High variance (R²=0.06) - risky investment
    },
    rookie_premium=1.5,        # Strongly values rookie contracts (2x surplus)
    draft_pick_value=1.3,      # Values picks highly
)

OLD_SCHOOL_GM = GMProfile(
    archetype=GMArchetype.OLD_SCHOOL,
    analytics_weight=0.2,
    veteran_preference=0.8,    # "Proven" players
    risk_tolerance=0.3,        # Conservative
    patience=0.4,              # Wants results now
    position_adjustments={
        # Traditional premiums - falls for market inefficiencies
        "LT": 1.20,    # Blind side premium myth
        "QB": 1.15,    # Any QB is valuable
        "RB": 1.15,    # Bell cow RB philosophy
        "CB": 1.10,    # "Shutdown corner" premium
        "LG": 0.85,    # Undervalues guards
        "RG": 0.85,
        "ILB": 0.80,   # "Just a linebacker"
    },
    rookie_premium=0.8,        # Prefers veterans
    draft_pick_value=0.85,     # Willing to trade picks for "sure things"
)

CAP_WIZARD_GM = GMProfile(
    archetype=GMArchetype.CAP_WIZARD,
    analytics_weight=0.75,
    veteran_preference=0.25,   # Strongly prefers cheap young players
    risk_tolerance=0.7,
    patience=0.9,              # Very long-term focused
    position_adjustments={
        # Focuses on value positions - where cap efficiency is highest
        "LG": 1.30,    # High value per dollar
        "RG": 1.30,
        "ILB": 1.25,
        "RT": 1.20,
        "C": 1.15,
        "DT": 1.15,
        # Avoids premium positions
        "QB": 0.85,    # Too expensive, low R²
        "LT": 0.80,    # Overpaid
        "WR": 0.90,    # Can find value later
        "RB": 0.65,    # Never pay a RB
    },
    rookie_premium=2.0,        # HEAVILY values rookie contracts
    draft_pick_value=1.5,      # Draft picks are gold
)

WIN_NOW_GM = GMProfile(
    archetype=GMArchetype.WIN_NOW,
    analytics_weight=0.4,
    veteran_preference=0.9,    # Veterans win now
    risk_tolerance=0.8,        # Will overpay for talent
    patience=0.1,              # No patience - championship window
    position_adjustments={
        # Pays premium for impact positions
        "QB": 1.25,    # Need a QB to win
        "DE": 1.20,    # Pass rush wins games
        "CB": 1.15,
        "WR": 1.15,    # Weapons for QB
        "LT": 1.15,    # Protect the QB
        # Still won't overpay for depth
        "ILB": 0.90,
        "RB": 0.95,    # Will pay a RB if they're a weapon
    },
    rookie_premium=0.6,        # Rookies need time to develop
    draft_pick_value=0.5,      # Will trade picks for talent
)

BALANCED_GM = GMProfile(
    archetype=GMArchetype.BALANCED,
    analytics_weight=0.5,
    veteran_preference=0.5,
    risk_tolerance=0.5,
    patience=0.5,
    position_adjustments={},   # Uses market rates
    rookie_premium=1.0,
    draft_pick_value=1.0,
)


# Mapping for easy lookup
GM_PROFILES = {
    GMArchetype.ANALYTICS: ANALYTICS_GM,
    GMArchetype.OLD_SCHOOL: OLD_SCHOOL_GM,
    GMArchetype.CAP_WIZARD: CAP_WIZARD_GM,
    GMArchetype.WIN_NOW: WIN_NOW_GM,
    GMArchetype.BALANCED: BALANCED_GM,
}


def get_gm_profile(archetype: GMArchetype) -> GMProfile:
    """Get the profile for a GM archetype."""
    return GM_PROFILES.get(archetype, BALANCED_GM)


def random_gm_archetype(
    team_status: str = "AVERAGE",
    weighted: bool = True,
) -> GMArchetype:
    """
    Assign a random GM archetype, optionally weighted by team status.

    Contending teams more likely to have Win Now GMs.
    Rebuilding teams more likely to have Cap Wizard or Analytics GMs.
    """
    if not weighted:
        return random.choice(list(GMArchetype))

    # Weight by team status
    if team_status in ("CONTENDING", "DYNASTY", "WINDOW_CLOSING"):
        weights = {
            GMArchetype.WIN_NOW: 0.35,
            GMArchetype.BALANCED: 0.25,
            GMArchetype.ANALYTICS: 0.20,
            GMArchetype.OLD_SCHOOL: 0.15,
            GMArchetype.CAP_WIZARD: 0.05,
        }
    elif team_status in ("REBUILDING", "EMERGING"):
        weights = {
            GMArchetype.CAP_WIZARD: 0.30,
            GMArchetype.ANALYTICS: 0.30,
            GMArchetype.BALANCED: 0.20,
            GMArchetype.OLD_SCHOOL: 0.15,
            GMArchetype.WIN_NOW: 0.05,
        }
    else:  # AVERAGE, MISMANAGED
        weights = {
            GMArchetype.BALANCED: 0.30,
            GMArchetype.OLD_SCHOOL: 0.25,
            GMArchetype.ANALYTICS: 0.20,
            GMArchetype.CAP_WIZARD: 0.15,
            GMArchetype.WIN_NOW: 0.10,
        }

    archetypes = list(weights.keys())
    probs = list(weights.values())
    return random.choices(archetypes, weights=probs, k=1)[0]


def calculate_position_value_adjustment(
    profile: GMProfile,
    position: str,
) -> float:
    """
    Get the position value adjustment for a GM profile.

    Returns multiplier (1.0 = market rate, >1 = values more, <1 = values less)
    """
    return profile.position_adjustments.get(position, 1.0)


def calculate_player_value_for_gm(
    market_value: int,
    position: str,
    age: int,
    is_rookie_contract: bool,
    profile: GMProfile,
) -> int:
    """
    Calculate what a player is worth to a specific GM.

    Adjusts market value based on GM's philosophy.
    """
    value = float(market_value)

    # Position adjustment
    pos_mult = calculate_position_value_adjustment(profile, position)
    value *= pos_mult

    # Rookie contract premium
    if is_rookie_contract:
        value *= profile.rookie_premium

    # Age adjustment (analytics GMs discount older players more)
    if age >= 30:
        age_penalty = (age - 29) * 0.05 * profile.analytics_weight
        value *= (1.0 - age_penalty)

    # Veteran preference (old school GMs prefer experience)
    if age >= 26 and age <= 30:
        value *= (1.0 + (profile.veteran_preference - 0.5) * 0.1)

    return int(value)


def gm_should_pursue_player(
    profile: GMProfile,
    player_age: int,
    player_overall: int,
    is_free_agent: bool,
    position_need: float,
) -> tuple[bool, float]:
    """
    Determine if a GM should pursue a player and how aggressively.

    Returns (should_pursue, aggression_factor)
    aggression_factor: 0-1, how much above market they'd pay
    """
    # Base interest from position need
    interest = position_need

    # Age preferences
    if player_age >= 30:
        # Older players
        if profile.veteran_preference > 0.7:
            interest *= 1.1  # Old school likes vets
        elif profile.analytics_weight > 0.7:
            interest *= 0.7  # Analytics avoids aging players
    elif player_age <= 25:
        # Young players
        if profile.analytics_weight > 0.7 or profile.rookie_premium > 1.2:
            interest *= 1.2  # Analytics/Cap Wizard love youth
        elif profile.veteran_preference > 0.7:
            interest *= 0.8  # Old school skeptical of youth

    # Quality threshold
    if player_overall < 75:
        interest *= 0.5  # Low interest in depth players
    elif player_overall >= 90:
        interest *= 1.3  # High interest in elite players

    # Win Now GMs more aggressive in FA
    if is_free_agent and profile.archetype == GMArchetype.WIN_NOW:
        interest *= 1.2

    # Calculate aggression (how much above market they'd pay)
    aggression = profile.risk_tolerance * 0.3  # Base aggression from risk tolerance

    if profile.archetype == GMArchetype.WIN_NOW:
        aggression += 0.15
    elif profile.archetype == GMArchetype.CAP_WIZARD:
        aggression -= 0.1

    should_pursue = interest >= 0.3

    return should_pursue, min(1.0, max(0.0, aggression))


# =============================================================================
# Integration with Research Lookup Tables
# =============================================================================

def get_gm_draft_priorities(profile: GMProfile) -> List[str]:
    """
    Get prioritized list of positions to draft based on GM archetype.

    Uses research-backed rookie premium data adjusted by GM philosophy.
    """
    # Get base draft priorities from research
    offense_premiums = ROOKIE_PREMIUM.get('offense', {})
    defense_premiums = ROOKIE_PREMIUM.get('defense', {})

    # Combine and sort by value multiplier
    all_positions = []
    for pos, data in offense_premiums.items():
        mult = data.get('value_multiplier', 1.0)
        # Adjust by GM archetype
        if profile.archetype == GMArchetype.CAP_WIZARD:
            mult *= 1.3  # Cap wizards love high-value rookies
        elif profile.archetype == GMArchetype.OLD_SCHOOL:
            mult *= 0.8  # Old school less focused on rookie value
        all_positions.append((pos, mult, 'offense'))

    for pos, data in defense_premiums.items():
        mult = data.get('value_multiplier', 1.0)
        if profile.archetype == GMArchetype.CAP_WIZARD:
            mult *= 1.3
        elif profile.archetype == GMArchetype.OLD_SCHOOL:
            mult *= 0.8
        all_positions.append((pos, mult, 'defense'))

    # Sort by adjusted multiplier (highest first)
    all_positions.sort(key=lambda x: -x[1])

    return [pos for pos, mult, side in all_positions]


def get_gm_allocation_targets(
    profile: GMProfile,
    current_allocation: Dict[str, float],
) -> Dict[str, float]:
    """
    Get target allocation adjustments for a GM based on archetype.

    Returns dict of position -> target_cap_pct adjusted for GM philosophy.
    """
    targets = {}

    for side in ['offense', 'defense']:
        gaps = get_allocation_gap(current_allocation, side)

        for pos, gap in gaps.items():
            opt = get_optimal_allocation(pos, side)
            base_target = opt.get('target', 5.0)

            # Adjust target by archetype
            if profile.archetype == GMArchetype.ANALYTICS:
                # Follow optimal closely
                targets[pos] = base_target
            elif profile.archetype == GMArchetype.OLD_SCHOOL:
                # Traditional premiums
                if pos in ('QB', 'LT', 'CB'):
                    targets[pos] = base_target * 1.2
                elif pos in ('LG', 'RG', 'ILB'):
                    targets[pos] = base_target * 0.8
                else:
                    targets[pos] = base_target
            elif profile.archetype == GMArchetype.CAP_WIZARD:
                # Minimize spending on overvalued, maximize on undervalued
                if pos in ('RB', 'LT'):
                    targets[pos] = base_target * 0.6
                elif pos in ('OL', 'LB', 'EDGE'):
                    targets[pos] = base_target * 1.1
                else:
                    targets[pos] = base_target * 0.9
            elif profile.archetype == GMArchetype.WIN_NOW:
                # Spend more on premium positions now
                if pos in ('QB', 'WR', 'EDGE', 'CB'):
                    targets[pos] = base_target * 1.3
                else:
                    targets[pos] = base_target
            else:
                targets[pos] = base_target

    return targets


def gm_evaluate_rookie_value(
    profile: GMProfile,
    position: str,
    rookie_cap_pct: float,
    side: str = 'offense',
) -> float:
    """
    Evaluate how a GM perceives rookie contract value.

    Analytics/Cap Wizard GMs properly value the rookie surplus.
    Old School GMs undervalue it.
    """
    # Get true effective salary from research
    true_effective = get_effective_salary(position, rookie_cap_pct, side)

    # Adjust perception by archetype
    if profile.archetype in (GMArchetype.ANALYTICS, GMArchetype.CAP_WIZARD):
        # Understands full value
        perceived = true_effective
    elif profile.archetype == GMArchetype.OLD_SCHOOL:
        # Undervalues rookie contracts
        perceived = (true_effective + rookie_cap_pct) / 2  # Average with actual
    elif profile.archetype == GMArchetype.WIN_NOW:
        # Slightly discounts because rookies need time
        perceived = true_effective * 0.85
    else:
        # Balanced - somewhat understands
        perceived = true_effective * 0.9

    return perceived


def gm_get_position_priorities(
    profile: GMProfile,
    strong_positions: List[str],
    weak_positions: List[str],
    side: str = 'offense',
) -> List[str]:
    """
    Get GM-adjusted position priorities considering roster state.

    Uses the Calvetti interaction model (position synergies).
    """
    # Get research-based priorities
    base_priorities = get_position_priority(strong_positions, weak_positions, side)

    # Adjust by archetype
    if profile.archetype == GMArchetype.ANALYTICS:
        # Uses interaction model properly
        return base_priorities
    elif profile.archetype == GMArchetype.OLD_SCHOOL:
        # Ignores interaction model, uses traditional order
        if side == 'offense':
            return ['QB', 'LT', 'WR', 'RB', 'TE', 'OL']
        else:
            return ['CB', 'EDGE', 'LB', 'DL', 'S']
    elif profile.archetype == GMArchetype.WIN_NOW:
        # Prioritizes impact positions regardless of synergies
        if side == 'offense':
            return ['QB', 'WR', 'OL', 'TE', 'RB']
        else:
            return ['EDGE', 'CB', 'DL', 'LB', 'S']
    else:
        return base_priorities
