"""
Personality Generation.

Functions for generating personalities for players based on position,
experience, and other factors.
"""

import random
from typing import Dict, List, Optional, TYPE_CHECKING

from huddle.core.personality.traits import Trait
from huddle.core.personality.archetypes import (
    ArchetypeType,
    ARCHETYPE_DEFINITIONS,
)
from huddle.core.personality.profile import PersonalityProfile

if TYPE_CHECKING:
    from huddle.core.enums import Position


# =============================================================================
# Position-Based Archetype Weights
# =============================================================================
# Different positions tend toward different archetypes.
# This creates realistic personality distributions.

# Default weights (used for positions not specifically defined)
DEFAULT_ARCHETYPE_WEIGHTS: Dict[ArchetypeType, float] = {
    ArchetypeType.COMMANDER: 1.0,
    ArchetypeType.CAPTAIN: 1.0,
    ArchetypeType.SUPERSTAR: 1.0,
    ArchetypeType.VIRTUOSO: 1.0,
    ArchetypeType.TRADITIONALIST: 1.0,
    ArchetypeType.STOIC: 1.0,
    ArchetypeType.ANCHOR: 1.0,
    ArchetypeType.TITAN: 1.0,
    ArchetypeType.HEADLINER: 1.0,
    ArchetypeType.ANALYST: 1.0,
    ArchetypeType.GURU: 1.0,
    ArchetypeType.AMBASSADOR: 1.0,
}

# Position-specific archetype tendencies
POSITION_ARCHETYPE_WEIGHTS: Dict[str, Dict[ArchetypeType, float]] = {
    # Quarterbacks - Leaders and analysts
    "QB": {
        ArchetypeType.COMMANDER: 2.5,
        ArchetypeType.CAPTAIN: 2.0,
        ArchetypeType.ANALYST: 2.0,
        ArchetypeType.SUPERSTAR: 1.5,
        ArchetypeType.STOIC: 1.5,
        ArchetypeType.GURU: 1.2,
        ArchetypeType.HEADLINER: 1.0,
        ArchetypeType.AMBASSADOR: 1.0,
        ArchetypeType.TRADITIONALIST: 0.8,
        ArchetypeType.VIRTUOSO: 0.7,
        ArchetypeType.ANCHOR: 0.5,
        ArchetypeType.TITAN: 0.5,
    },
    # Wide Receivers - Stars and headliners
    "WR": {
        ArchetypeType.SUPERSTAR: 2.5,
        ArchetypeType.HEADLINER: 2.0,
        ArchetypeType.VIRTUOSO: 1.8,
        ArchetypeType.TITAN: 1.5,
        ArchetypeType.AMBASSADOR: 1.2,
        ArchetypeType.CAPTAIN: 1.0,
        ArchetypeType.COMMANDER: 0.8,
        ArchetypeType.ANALYST: 0.7,
        ArchetypeType.STOIC: 0.6,
        ArchetypeType.TRADITIONALIST: 0.6,
        ArchetypeType.ANCHOR: 0.5,
        ArchetypeType.GURU: 0.5,
    },
    # Running Backs - Mix of stars and workhorses
    "RB": {
        ArchetypeType.TITAN: 2.0,
        ArchetypeType.SUPERSTAR: 1.8,
        ArchetypeType.CAPTAIN: 1.5,
        ArchetypeType.ANCHOR: 1.5,
        ArchetypeType.VIRTUOSO: 1.3,
        ArchetypeType.HEADLINER: 1.2,
        ArchetypeType.TRADITIONALIST: 1.0,
        ArchetypeType.STOIC: 0.8,
        ArchetypeType.COMMANDER: 0.7,
        ArchetypeType.ANALYST: 0.6,
        ArchetypeType.AMBASSADOR: 0.6,
        ArchetypeType.GURU: 0.5,
    },
    # Tight Ends - Team players and anchors
    "TE": {
        ArchetypeType.ANCHOR: 2.0,
        ArchetypeType.CAPTAIN: 1.8,
        ArchetypeType.TRADITIONALIST: 1.5,
        ArchetypeType.TITAN: 1.3,
        ArchetypeType.STOIC: 1.2,
        ArchetypeType.SUPERSTAR: 1.0,
        ArchetypeType.AMBASSADOR: 1.0,
        ArchetypeType.GURU: 0.8,
        ArchetypeType.ANALYST: 0.7,
        ArchetypeType.VIRTUOSO: 0.7,
        ArchetypeType.COMMANDER: 0.6,
        ArchetypeType.HEADLINER: 0.5,
    },
    # Offensive Linemen - Anchors and traditionalists
    "OL": {
        ArchetypeType.ANCHOR: 2.5,
        ArchetypeType.TRADITIONALIST: 2.0,
        ArchetypeType.CAPTAIN: 1.8,
        ArchetypeType.STOIC: 1.5,
        ArchetypeType.GURU: 1.2,
        ArchetypeType.TITAN: 1.0,
        ArchetypeType.AMBASSADOR: 0.8,
        ArchetypeType.ANALYST: 0.7,
        ArchetypeType.COMMANDER: 0.6,
        ArchetypeType.VIRTUOSO: 0.4,
        ArchetypeType.SUPERSTAR: 0.3,
        ArchetypeType.HEADLINER: 0.2,
    },
    # Defensive Linemen - Titans and commanders
    "DL": {
        ArchetypeType.TITAN: 2.5,
        ArchetypeType.ANCHOR: 1.8,
        ArchetypeType.COMMANDER: 1.5,
        ArchetypeType.STOIC: 1.3,
        ArchetypeType.TRADITIONALIST: 1.2,
        ArchetypeType.CAPTAIN: 1.0,
        ArchetypeType.SUPERSTAR: 0.8,
        ArchetypeType.HEADLINER: 0.7,
        ArchetypeType.ANALYST: 0.6,
        ArchetypeType.GURU: 0.5,
        ArchetypeType.VIRTUOSO: 0.4,
        ArchetypeType.AMBASSADOR: 0.4,
    },
    # Linebackers - Leaders and titans
    "LB": {
        ArchetypeType.COMMANDER: 2.0,
        ArchetypeType.TITAN: 2.0,
        ArchetypeType.CAPTAIN: 1.8,
        ArchetypeType.TRADITIONALIST: 1.5,
        ArchetypeType.STOIC: 1.2,
        ArchetypeType.ANCHOR: 1.0,
        ArchetypeType.ANALYST: 0.9,
        ArchetypeType.SUPERSTAR: 0.8,
        ArchetypeType.HEADLINER: 0.7,
        ArchetypeType.GURU: 0.6,
        ArchetypeType.AMBASSADOR: 0.5,
        ArchetypeType.VIRTUOSO: 0.4,
    },
    # Cornerbacks - Stars and virtuosos
    "CB": {
        ArchetypeType.SUPERSTAR: 2.0,
        ArchetypeType.VIRTUOSO: 1.8,
        ArchetypeType.HEADLINER: 1.5,
        ArchetypeType.TITAN: 1.3,
        ArchetypeType.CAPTAIN: 1.0,
        ArchetypeType.STOIC: 1.0,
        ArchetypeType.COMMANDER: 0.9,
        ArchetypeType.ANALYST: 0.8,
        ArchetypeType.TRADITIONALIST: 0.7,
        ArchetypeType.ANCHOR: 0.6,
        ArchetypeType.AMBASSADOR: 0.5,
        ArchetypeType.GURU: 0.4,
    },
    # Safeties - Mix of leaders and analysts
    "S": {
        ArchetypeType.CAPTAIN: 1.8,
        ArchetypeType.COMMANDER: 1.5,
        ArchetypeType.ANALYST: 1.5,
        ArchetypeType.STOIC: 1.3,
        ArchetypeType.TITAN: 1.2,
        ArchetypeType.ANCHOR: 1.0,
        ArchetypeType.TRADITIONALIST: 1.0,
        ArchetypeType.SUPERSTAR: 0.8,
        ArchetypeType.GURU: 0.8,
        ArchetypeType.AMBASSADOR: 0.7,
        ArchetypeType.VIRTUOSO: 0.6,
        ArchetypeType.HEADLINER: 0.5,
    },
    # Kickers/Punters - Stoics and analysts
    "K": {
        ArchetypeType.STOIC: 2.5,
        ArchetypeType.ANALYST: 2.0,
        ArchetypeType.ANCHOR: 1.5,
        ArchetypeType.GURU: 1.3,
        ArchetypeType.TRADITIONALIST: 1.0,
        ArchetypeType.VIRTUOSO: 0.8,
        ArchetypeType.CAPTAIN: 0.6,
        ArchetypeType.AMBASSADOR: 0.5,
        ArchetypeType.COMMANDER: 0.3,
        ArchetypeType.SUPERSTAR: 0.2,
        ArchetypeType.TITAN: 0.2,
        ArchetypeType.HEADLINER: 0.2,
    },
}

# Map specific positions to general categories for weight lookup
POSITION_CATEGORY_MAP: Dict[str, str] = {
    # Offensive Line
    "LT": "OL",
    "LG": "OL",
    "C": "OL",
    "RG": "OL",
    "RT": "OL",
    # Defensive Line
    "DE": "DL",
    "DT": "DL",
    "NT": "DL",
    # Linebackers
    "MLB": "LB",
    "OLB": "LB",
    "ILB": "LB",
    # Safeties
    "FS": "S",
    "SS": "S",
    # Special Teams
    "P": "K",
    "LS": "OL",  # Long snappers are like OL personality-wise
    # Fullbacks similar to RB
    "FB": "RB",
}


def _get_archetype_weights(position: Optional[str]) -> Dict[ArchetypeType, float]:
    """Get archetype weights for a position."""
    if position is None:
        return DEFAULT_ARCHETYPE_WEIGHTS

    # Map specific position to category
    pos_key = POSITION_CATEGORY_MAP.get(position, position)

    return POSITION_ARCHETYPE_WEIGHTS.get(pos_key, DEFAULT_ARCHETYPE_WEIGHTS)


def _select_archetype(position: Optional[str]) -> ArchetypeType:
    """Select an archetype based on position tendencies."""
    weights = _get_archetype_weights(position)

    archetypes = list(weights.keys())
    probabilities = list(weights.values())

    # Normalize probabilities
    total = sum(probabilities)
    probabilities = [p / total for p in probabilities]

    return random.choices(archetypes, probabilities)[0]


def _generate_traits(archetype: ArchetypeType) -> Dict[Trait, float]:
    """
    Generate trait values for an archetype.

    Uses archetype definition's base values with variance.
    """
    definition = ARCHETYPE_DEFINITIONS[archetype]
    traits = {}

    for trait, (base, variance) in definition.trait_weights.items():
        # Generate value with variance
        value = base + random.uniform(-variance, variance)
        # Clamp to 0.0-1.0
        traits[trait] = max(0.0, min(1.0, value))

    return traits


def generate_personality(
    archetype: Optional[ArchetypeType] = None,
    position: Optional[str] = None,
) -> PersonalityProfile:
    """
    Generate a personality profile for a player.

    Args:
        archetype: Specific archetype to use. If None, selects based on position.
        position: Player's position (e.g., "QB", "WR"). Used for archetype selection
                  if archetype not specified.

    Returns:
        A new PersonalityProfile with generated trait values.
    """
    if archetype is None:
        archetype = _select_archetype(position)

    traits = _generate_traits(archetype)

    return PersonalityProfile(
        archetype=archetype,
        traits=traits,
    )


def assign_personality_to_player(player: "Player") -> None:
    """
    Assign a personality to a player in-place.

    Uses the player's position to select an appropriate archetype.

    Args:
        player: Player to assign personality to. Modified in-place.
    """
    from huddle.core.models.player import Player

    position_str = player.position.value if player.position else None
    player.personality = generate_personality(position=position_str)


def get_archetype_distribution(position: Optional[str] = None) -> Dict[ArchetypeType, float]:
    """
    Get the probability distribution of archetypes for a position.

    Useful for debugging or displaying to users.

    Args:
        position: Position to get distribution for (None for default)

    Returns:
        Dict mapping archetype to probability (0.0-1.0, sums to 1.0)
    """
    weights = _get_archetype_weights(position)
    total = sum(weights.values())
    return {at: w / total for at, w in weights.items()}


def get_common_archetypes(position: str, top_n: int = 3) -> List[ArchetypeType]:
    """
    Get the most common archetypes for a position.

    Args:
        position: Position to query
        top_n: Number of archetypes to return

    Returns:
        List of most common archetypes, ordered by frequency
    """
    weights = _get_archetype_weights(position)
    sorted_archetypes = sorted(weights.keys(), key=lambda a: weights[a], reverse=True)
    return sorted_archetypes[:top_n]
