"""
Player Development System.

HC09-style development where practice drives attribute growth.
Young players improve toward their potential ceiling based on
age, learning attribute, and room to grow.
"""

from typing import TYPE_CHECKING, Dict, List, Optional
import random

if TYPE_CHECKING:
    from huddle.core.models.player import Player


# =============================================================================
# Constants
# =============================================================================

# Base attribute points gained per development rep
BASE_DEV_RATE = 0.1

# Age thresholds for development speed
AGE_PEAK = 24           # Fastest development (1.2x)
AGE_NORMAL = 26         # Normal development (1.0x)
AGE_DECLINE_START = 28  # Slowing development (0.6x)
AGE_SLOW = 30           # Near-zero development (0.3x)
AGE_CUTOFF = 31         # Minimal development (0.1x)


# =============================================================================
# Developable Attributes by Position
# =============================================================================

# Position-specific attributes that can be improved through practice
# Not all 53 attributes should develop - focus on trainable skills
DEVELOPABLE_ATTRIBUTES: Dict[str, List[str]] = {
    # Physical attributes (all positions, but develop slowly)
    "physical": ["speed", "acceleration", "agility", "strength"],

    # Quarterback
    "QB": [
        "throw_accuracy_short", "throw_accuracy_mid", "throw_accuracy_deep",
        "throw_on_run", "play_action", "awareness",
    ],

    # Running back
    "RB": [
        "carrying", "elusiveness", "break_tackle", "bcv", "catching",
    ],

    # Fullback (same as RB + blocking)
    "FB": [
        "carrying", "elusiveness", "break_tackle", "run_block", "pass_block",
    ],

    # Wide receiver
    "WR": [
        "route_running", "catching", "catch_in_traffic", "release", "awareness",
    ],

    # Tight end (receiving + blocking)
    "TE": [
        "route_running", "catching", "run_block", "pass_block", "awareness",
    ],

    # Offensive line (all OL positions share these)
    "OL": [
        "pass_block", "run_block", "impact_block", "awareness",
    ],

    # Defensive line (DE, DT, NT)
    "DL": [
        "power_moves", "finesse_moves", "block_shedding", "pursuit", "tackle",
    ],

    # Linebackers (MLB, OLB, ILB)
    "LB": [
        "tackle", "pursuit", "play_recognition", "zone_coverage", "block_shedding",
    ],

    # Defensive backs (CB, FS, SS)
    "DB": [
        "man_coverage", "zone_coverage", "press", "play_recognition", "tackle",
    ],
}

# Map specific positions to their development category
POSITION_TO_CATEGORY: Dict[str, str] = {
    "QB": "QB",
    "RB": "RB",
    "FB": "FB",
    "WR": "WR",
    "TE": "TE",
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "DE": "DL", "DT": "DL", "NT": "DL",
    "MLB": "LB", "OLB": "LB", "ILB": "LB",
    "CB": "DB", "FS": "DB", "SS": "DB",
    # Special teams don't really develop through practice
    "K": None, "P": None, "LS": None,
}


# =============================================================================
# Development Rate Calculation
# =============================================================================

def get_age_factor(age: int) -> float:
    """
    Get development rate multiplier based on player age.

    Younger players develop faster, veterans barely improve.

    Args:
        age: Player's current age

    Returns:
        Multiplier for development rate (0.1 to 1.2)
    """
    if age <= AGE_PEAK:
        return 1.2  # Peak development years
    elif age <= AGE_NORMAL:
        return 1.0  # Normal development
    elif age <= AGE_DECLINE_START:
        return 0.6  # Starting to slow
    elif age <= AGE_SLOW:
        return 0.3  # Significant slowdown
    else:
        return 0.1  # Veterans barely improve


def get_learning_factor(player: "Player") -> float:
    """
    Get development rate multiplier based on Learning attribute.

    Smart players (high Learning) develop faster.

    Args:
        player: The player

    Returns:
        Multiplier for development rate (0.6 to 1.8 typical range)
    """
    learning = player.attributes.get("learning", 50)
    return learning / 50.0


def get_potential_gap_factor(player: "Player") -> float:
    """
    Get development rate multiplier based on room to grow.

    Players far from their ceiling develop faster than those
    who are already near their potential.

    Args:
        player: The player

    Returns:
        Multiplier for development rate (0.0 to 1.3)
    """
    gap = player.potential - player.overall

    if gap <= 0:
        return 0.0  # At or above potential, no growth
    elif gap <= 5:
        return 0.5  # Close to ceiling, slow growth
    elif gap <= 10:
        return 1.0  # Normal growth
    else:
        return 1.3  # Lots of room, accelerated growth


def calculate_development_rate(player: "Player") -> float:
    """
    Calculate the base development rate for a player.

    Combines age, learning, and potential gap factors.

    Args:
        player: The player to calculate rate for

    Returns:
        Attribute points gained per development rep
    """
    age_factor = get_age_factor(player.age)
    learning_factor = get_learning_factor(player)
    gap_factor = get_potential_gap_factor(player)

    return BASE_DEV_RATE * age_factor * learning_factor * gap_factor


# =============================================================================
# Attribute Development
# =============================================================================

def get_developable_attrs(position: str) -> List[str]:
    """
    Get list of attributes that can develop for a position.

    Combines physical attributes with position-specific skills.

    Args:
        position: Player's position (e.g., "QB", "WR", "CB")

    Returns:
        List of attribute names that can be improved
    """
    category = POSITION_TO_CATEGORY.get(position)
    if category is None:
        return []  # Special teams don't develop

    # Physical attributes apply to everyone
    attrs = DEVELOPABLE_ATTRIBUTES.get("physical", []).copy()

    # Add position-specific attributes
    pos_attrs = DEVELOPABLE_ATTRIBUTES.get(category, [])
    attrs.extend(pos_attrs)

    return attrs


def apply_development(
    player: "Player",
    attribute: str,
    reps: int,
    potential_buffer: int = 5,
) -> float:
    """
    Apply development reps to improve a specific attribute.

    Args:
        player: The player to develop
        attribute: The attribute to improve
        reps: Number of development reps
        potential_buffer: Individual attributes can exceed OVR potential by this much

    Returns:
        Actual points gained (may be less than calculated if hitting ceiling)
    """
    rate = calculate_development_rate(player)
    if rate <= 0:
        return 0.0

    current_value = player.attributes.get(attribute, 50)

    # Individual attribute ceiling is potential + buffer
    # This allows specific skills to exceed overall potential slightly
    ceiling = player.potential + potential_buffer

    # Calculate raw gain
    raw_gain = rate * reps

    # Apply ceiling
    new_value = min(current_value + raw_gain, ceiling)
    actual_gain = new_value - current_value

    if actual_gain > 0:
        # Use integer for attribute storage
        player.attributes.set(attribute, int(new_value))

    return actual_gain


def develop_player(
    player: "Player",
    reps: int,
    attrs_per_session: int = 3,
) -> Dict[str, float]:
    """
    Apply development to a player, improving random attributes.

    Simulates a development-focused practice session by picking
    random position-relevant attributes to train.

    Args:
        player: The player to develop
        reps: Total development reps
        attrs_per_session: Number of attributes to train (default 3)

    Returns:
        Dict mapping attribute name to points gained
    """
    developable = get_developable_attrs(player.position.value)
    if not developable:
        return {}

    # Pick random attributes to develop this session
    # This simulates varied drills
    attrs_to_train = random.sample(
        developable,
        min(attrs_per_session, len(developable))
    )

    # Split reps among selected attributes
    reps_per_attr = max(1, reps // len(attrs_to_train))

    gains: Dict[str, float] = {}
    for attr in attrs_to_train:
        gain = apply_development(player, attr, reps_per_attr)
        if gain > 0:
            gains[attr] = gain

    return gains


def can_develop(player: "Player") -> bool:
    """
    Check if a player can benefit from development practice.

    Args:
        player: The player to check

    Returns:
        True if player has room to grow and isn't too old
    """
    if player.age > AGE_CUTOFF + 5:
        return False  # Too old

    if player.overall >= player.potential:
        return False  # At ceiling

    if POSITION_TO_CATEGORY.get(player.position.value) is None:
        return False  # Special teams

    return True


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BASE_DEV_RATE",
    "AGE_PEAK",
    "AGE_DECLINE_START",
    "AGE_CUTOFF",
    "DEVELOPABLE_ATTRIBUTES",
    "POSITION_TO_CATEGORY",
    "get_age_factor",
    "get_learning_factor",
    "get_potential_gap_factor",
    "calculate_development_rate",
    "get_developable_attrs",
    "apply_development",
    "develop_player",
    "can_develop",
]
