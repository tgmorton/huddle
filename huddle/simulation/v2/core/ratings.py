"""Continuous Rating Impact System.

Converts player ratings (0-99) into gameplay modifiers using smooth
interpolation between calibrated checkpoints. No hard tier boundaries -
every point of rating matters.

Checkpoint calibration is based on research data:
- 99 (Elite ceiling): +15% standalone, +20% vs average
- 88 (Elite floor): +10% standalone, +15% vs average
- 75 (Average): 0% baseline
- 50 (Below-avg floor): -8% standalone, -15% vs average

Usage:
    from .ratings import get_rating_modifier, get_matchup_modifier

    # Single rating modifier (for standalone effects)
    speed_mod = get_rating_modifier(player.attributes.speed)

    # Matchup modifier (attacker vs defender)
    tackle_advantage = get_matchup_modifier(
        defender.attributes.tackling,
        ballcarrier.attributes.elusiveness,
    )

    # For composite attributes (blocking), use weighted composite first
    ol_composite = get_composite_rating(ol.attributes, PASS_BLOCK_WEIGHTS)
    dl_composite = get_composite_rating(dl.attributes, PASS_RUSH_WEIGHTS)
    block_advantage = get_matchup_modifier(ol_composite, dl_composite)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Union


# =============================================================================
# Calibration Checkpoints
# =============================================================================
# These are research-calibrated values that define the curve shape.
# Format: (rating, modifier) - sorted descending by rating
# Modifiers represent the standalone bonus/penalty for that rating level.

RATING_CHECKPOINTS: List[Tuple[int, float]] = [
    (99, 0.15),   # Elite ceiling - dominant
    (88, 0.10),   # Elite floor - clearly above average
    (76, 0.03),   # Above-average floor - slight edge
    (75, 0.00),   # Average - baseline
    (63, -0.03),  # Below-average ceiling - slight liability
    (50, -0.08),  # Below-average floor - significant liability
]

# Raw rating difference scaling
# How much the raw difference between ratings affects matchups
# (in addition to the checkpoint-based modifiers)
RAW_DIFF_SCALE = 0.10  # +/-10% for full 0-99 range difference


# =============================================================================
# Core Functions
# =============================================================================

def get_rating_modifier(rating: int) -> float:
    """Get the continuous modifier for a single rating.

    Smoothly interpolates between calibration checkpoints.
    Every point of rating matters - no hard tier boundaries.

    Args:
        rating: Player attribute value (0-99)

    Returns:
        Modifier as a float (e.g., 0.12 = +12%, -0.05 = -5%)

    Examples:
        >>> get_rating_modifier(99)   # Elite ceiling
        0.15
        >>> get_rating_modifier(88)   # Elite floor
        0.10
        >>> get_rating_modifier(93)   # Between 88-99
        ~0.125  # Interpolated
        >>> get_rating_modifier(75)   # Average
        0.0
        >>> get_rating_modifier(50)   # Below-average floor
        -0.08
    """
    # Handle edge cases
    if rating >= RATING_CHECKPOINTS[0][0]:
        return RATING_CHECKPOINTS[0][1]
    if rating <= RATING_CHECKPOINTS[-1][0]:
        return RATING_CHECKPOINTS[-1][1]

    # Find the two checkpoints we're between and interpolate
    for i in range(len(RATING_CHECKPOINTS) - 1):
        upper_rating, upper_mod = RATING_CHECKPOINTS[i]
        lower_rating, lower_mod = RATING_CHECKPOINTS[i + 1]

        if rating >= lower_rating:
            # Linear interpolation between these two checkpoints
            t = (rating - lower_rating) / (upper_rating - lower_rating)
            return lower_mod + t * (upper_mod - lower_mod)

    # Fallback (shouldn't reach here)
    return 0.0


def get_matchup_modifier(
    attacker_rating: int,
    defender_rating: int,
) -> float:
    """Get the matchup modifier for attacker vs defender.

    Combines:
    1. Attacker's standalone modifier (from their rating)
    2. Defender's standalone modifier (subtracted - higher defender = harder)
    3. Raw rating difference (scaled contribution)

    Args:
        attacker_rating: The attacking player's relevant attribute (0-99)
        defender_rating: The defending player's relevant attribute (0-99)

    Returns:
        Modifier for attacker's success probability
        Positive = attacker favored, Negative = defender favored

    Examples:
        >>> get_matchup_modifier(95, 55)   # Elite vs Below-Avg
        ~0.22  # Strong attacker advantage
        >>> get_matchup_modifier(88, 75)   # Elite vs Average
        ~0.11  # Moderate attacker advantage
        >>> get_matchup_modifier(75, 75)   # Even matchup
        0.0
        >>> get_matchup_modifier(60, 90)   # Below-Avg vs Elite
        ~-0.17  # Defender advantage
    """
    # Get individual modifiers
    att_mod = get_rating_modifier(attacker_rating)
    def_mod = get_rating_modifier(defender_rating)

    # Raw difference contribution
    raw_diff = (attacker_rating - defender_rating) / 100.0 * RAW_DIFF_SCALE

    # Combine: attacker's bonus - defender's bonus + raw difference
    return att_mod - def_mod + raw_diff


def get_composite_rating(
    attributes: Union[Dict[str, Any], Any],
    weights: Dict[str, float],
) -> int:
    """Calculate a weighted composite rating from multiple attributes.

    Use this for multi-attribute matchups like blocking (block_power + strength + ...).

    Args:
        attributes: Dict of attribute values OR object with attributes
        weights: Dict mapping attribute names to weights (should sum to ~1.0)

    Returns:
        Weighted composite rating as int (0-99)

    Example:
        >>> get_composite_rating(
        ...     {"block_power": 85, "strength": 80, "awareness": 75},
        ...     {"block_power": 0.5, "strength": 0.35, "awareness": 0.15},
        ... )
        82  # Weighted average
    """
    total = 0.0
    total_weight = 0.0

    for attr_name, weight in weights.items():
        # Support both dict and object access
        if isinstance(attributes, dict):
            value = attributes.get(attr_name, 75)
        else:
            value = getattr(attributes, attr_name, 75)

        total += value * weight
        total_weight += weight

    if total_weight > 0:
        return int(total / total_weight)

    return 75  # Default to average


# =============================================================================
# Convenience Functions
# =============================================================================

def get_tier_label(rating: int) -> str:
    """Get a human-readable tier label for a rating.

    These are just labels for display/logging - not used in calculations.

    Args:
        rating: Player attribute value (0-99)

    Returns:
        String label like "Elite", "Above-Average", etc.
    """
    if rating >= 88:
        return "Elite"
    elif rating >= 76:
        return "Above-Average"
    elif rating >= 63:
        return "Average"
    else:
        return "Below-Average"


def describe_matchup(attacker_rating: int, defender_rating: int) -> str:
    """Get a human-readable description of a matchup.

    Useful for debugging and logging.

    Args:
        attacker_rating: Attacker's attribute (0-99)
        defender_rating: Defender's attribute (0-99)

    Returns:
        Description string like "Elite (92) vs Average (70): +15.4% advantage"
    """
    att_label = get_tier_label(attacker_rating)
    def_label = get_tier_label(defender_rating)
    mod = get_matchup_modifier(attacker_rating, defender_rating)
    sign = "+" if mod >= 0 else ""
    return f"{att_label} ({attacker_rating}) vs {def_label} ({defender_rating}): {sign}{mod*100:.1f}% advantage"


# =============================================================================
# Dataclass for Weighted Ratings (backwards compatibility)
# =============================================================================

@dataclass
class WeightedRating:
    """Result of combining multiple attributes with weights.

    Kept for backwards compatibility with existing code.
    """
    composite_rating: int
    modifier: float
    tier_label: str

    @classmethod
    def from_attributes(
        cls,
        attributes: Union[Dict[str, Any], Any],
        weights: Dict[str, float],
    ) -> "WeightedRating":
        """Create from attribute dict/object and weight dict."""
        composite = get_composite_rating(attributes, weights)

        return cls(
            composite_rating=composite,
            modifier=get_rating_modifier(composite),
            tier_label=get_tier_label(composite),
        )
