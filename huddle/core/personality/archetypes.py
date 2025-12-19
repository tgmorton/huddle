"""
Personality Archetypes.

Defines the 12 personality archetypes - predefined trait combinations
that create recognizable personality types.

Inspired by NFL Head Coach 09's 17 archetypes, simplified to 12 core types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple

from huddle.core.personality.traits import Trait


class ArchetypeType(Enum):
    """
    The 12 personality archetypes.

    Each archetype defines default trait values and behavioral tendencies
    that affect negotiations, morale, and compatibility.
    """

    # Leadership types
    COMMANDER = "commander"
    """Driven leader who demands respect and values structure. (HC09: Mike Shanahan)"""

    CAPTAIN = "captain"
    """Team-first leader, loyal, cooperative. (HC09: Mike McCarthy)"""

    # Star types
    SUPERSTAR = "superstar"
    """Ambitious, materialistic, dramatic - wants money and spotlight. (HC09: Herman Edwards)"""

    VIRTUOSO = "virtuoso"
    """Talented, flexible, sensitive - artistic temperament. (HC09: N/A)"""

    # Steady types
    TRADITIONALIST = "traditionalist"
    """Values tradition, loyal, structured - respects the game. (HC09: Rod Marinelli)"""

    STOIC = "stoic"
    """Patient, calm, conservative - unflappable presence. (HC09: Andy Reid)"""

    ANCHOR = "anchor"
    """Reliable, passive, patient - steady rock. (HC09: Tony Dungy)"""

    # Aggressive types
    TITAN = "titan"
    """Aggressive, competitive, reckless - force of nature. (HC09: Marvin Lewis)"""

    HEADLINER = "headliner"
    """Dramatic, impulsive, expressive - loves the spotlight. (HC09: Jon Gruden)"""

    # Analytical types
    ANALYST = "analyst"
    """Calculating, perfectionist, structured - data-driven. (HC09: Lane Kiffin)"""

    GURU = "guru"
    """Reserved, conservative, trusting - quiet wisdom. (HC09: Norv Turner)"""

    # Social types
    AMBASSADOR = "ambassador"
    """Cooperative, expressive, trusting - diplomatic presence. (HC09: Dick Jauron)"""


@dataclass
class Archetype:
    """
    Defines trait distributions and behavioral modifiers for an archetype.

    Attributes:
        archetype_type: The archetype enum value
        description: Human-readable description
        trait_weights: Maps Trait -> (base_value, variance)
                      When generating, actual = base +/- variance
        opening_demand_modifier: Multiplier on initial contract ask (1.0 = market)
        patience_modifier: How patient in negotiations (1.0 = normal, >1 = more patient)
        walkaway_threshold: % of market value before walking away (0.60 = 60%)
        loyalty_modifier: How much they value team/relationships (-0.1 to +0.1)
        prefers_praise: Responds well to positive feedback
        prefers_criticism: Responds well to tough love / constructive criticism
    """

    archetype_type: ArchetypeType
    description: str
    trait_weights: Dict[Trait, Tuple[float, float]] = field(default_factory=dict)

    # Negotiation behavior modifiers
    opening_demand_modifier: float = 1.0
    patience_modifier: float = 1.0
    walkaway_threshold: float = 0.60

    # Relationship modifiers
    loyalty_modifier: float = 0.0

    # Feedback preferences (for future morale system)
    prefers_praise: bool = True
    prefers_criticism: bool = False


# =============================================================================
# Archetype Definitions
# =============================================================================

ARCHETYPE_DEFINITIONS: Dict[ArchetypeType, Archetype] = {
    # =========================================================================
    # COMMANDER - Driven leader, structured, demands respect
    # =========================================================================
    ArchetypeType.COMMANDER: Archetype(
        archetype_type=ArchetypeType.COMMANDER,
        description="Driven leader who demands respect and values structure",
        trait_weights={
            Trait.DRIVEN: (0.85, 0.10),
            Trait.COMPETITIVE: (0.80, 0.10),
            Trait.LOYAL: (0.70, 0.15),
            Trait.STRUCTURED: (0.80, 0.10),
            Trait.PATIENT: (0.65, 0.15),
            Trait.CALCULATING: (0.75, 0.10),
            Trait.RESERVED: (0.60, 0.15),
            Trait.LEVEL_HEADED: (0.70, 0.15),
        },
        opening_demand_modifier=1.05,  # Fair but firm
        patience_modifier=1.2,  # Patient negotiator
        walkaway_threshold=0.55,  # Hard to offend
        loyalty_modifier=0.05,
        prefers_praise=False,
        prefers_criticism=True,
    ),
    # =========================================================================
    # CAPTAIN - Team-first leader, loyal, cooperative
    # =========================================================================
    ArchetypeType.CAPTAIN: Archetype(
        archetype_type=ArchetypeType.CAPTAIN,
        description="Team-first leader who values loyalty and cooperation",
        trait_weights={
            Trait.LOYAL: (0.90, 0.05),
            Trait.TEAM_PLAYER: (0.90, 0.05),
            Trait.COOPERATIVE: (0.80, 0.10),
            Trait.COMPETITIVE: (0.75, 0.10),
            Trait.PATIENT: (0.70, 0.15),
            Trait.SENSITIVE: (0.55, 0.15),
            Trait.STRUCTURED: (0.65, 0.15),
        },
        opening_demand_modifier=0.95,  # Willing to take less for right team
        patience_modifier=1.1,
        walkaway_threshold=0.50,  # Very hard to offend
        loyalty_modifier=0.10,  # Strong loyalty bonus
        prefers_praise=True,
        prefers_criticism=True,
    ),
    # =========================================================================
    # SUPERSTAR - Ambitious, materialistic, dramatic
    # =========================================================================
    ArchetypeType.SUPERSTAR: Archetype(
        archetype_type=ArchetypeType.SUPERSTAR,
        description="Ambitious talent who wants money, fame, and the spotlight",
        trait_weights={
            Trait.DRIVEN: (0.90, 0.05),
            Trait.AMBITIOUS: (0.90, 0.05),
            Trait.MATERIALISTIC: (0.85, 0.10),
            Trait.DRAMATIC: (0.75, 0.15),
            Trait.COMPETITIVE: (0.80, 0.10),
            Trait.PERFECTIONIST: (0.70, 0.15),
            Trait.FLEXIBLE: (0.60, 0.15),
            Trait.EXPRESSIVE: (0.70, 0.15),
        },
        opening_demand_modifier=1.20,  # Wants top dollar
        patience_modifier=0.75,  # Impatient
        walkaway_threshold=0.70,  # Will walk for lowballs
        loyalty_modifier=-0.05,  # Less loyal, follows the money
        prefers_praise=True,
        prefers_criticism=False,
    ),
    # =========================================================================
    # VIRTUOSO - Talented, flexible, sensitive
    # =========================================================================
    ArchetypeType.VIRTUOSO: Archetype(
        archetype_type=ArchetypeType.VIRTUOSO,
        description="Talented player with artistic temperament, flexible but sensitive",
        trait_weights={
            Trait.FLEXIBLE: (0.85, 0.10),
            Trait.SENSITIVE: (0.80, 0.10),
            Trait.DRIVEN: (0.70, 0.15),
            Trait.DRAMATIC: (0.65, 0.15),
            Trait.IMPULSIVE: (0.60, 0.15),
            Trait.EXPRESSIVE: (0.65, 0.15),
            Trait.PERFECTIONIST: (0.60, 0.20),
        },
        opening_demand_modifier=1.05,  # Fair market
        patience_modifier=0.9,
        walkaway_threshold=0.65,  # Easily offended
        loyalty_modifier=0.0,
        prefers_praise=True,
        prefers_criticism=False,
    ),
    # =========================================================================
    # TRADITIONALIST - Values tradition, loyal, structured
    # =========================================================================
    ArchetypeType.TRADITIONALIST: Archetype(
        archetype_type=ArchetypeType.TRADITIONALIST,
        description="Respects the game's traditions, loyal, values structure",
        trait_weights={
            Trait.VALUES_TRADITION: (0.90, 0.05),
            Trait.LOYAL: (0.85, 0.10),
            Trait.STRUCTURED: (0.80, 0.10),
            Trait.TEAM_PLAYER: (0.75, 0.10),
            Trait.COMPETITIVE: (0.70, 0.15),
            Trait.THRIFTY: (0.65, 0.15),
            Trait.LEVEL_HEADED: (0.65, 0.15),
        },
        opening_demand_modifier=0.98,  # Slightly below market, values team
        patience_modifier=1.15,
        walkaway_threshold=0.52,  # Very patient
        loyalty_modifier=0.08,
        prefers_praise=False,
        prefers_criticism=True,
    ),
    # =========================================================================
    # STOIC - Patient, calm, conservative
    # =========================================================================
    ArchetypeType.STOIC: Archetype(
        archetype_type=ArchetypeType.STOIC,
        description="Patient, calm professional who values substance over flash",
        trait_weights={
            Trait.PATIENT: (0.90, 0.05),
            Trait.LEVEL_HEADED: (0.90, 0.05),
            Trait.CONSERVATIVE: (0.75, 0.15),
            Trait.RESERVED: (0.80, 0.10),
            Trait.CALCULATING: (0.70, 0.15),
            Trait.THRIFTY: (0.60, 0.20),
            Trait.STRUCTURED: (0.65, 0.15),
        },
        opening_demand_modifier=1.0,  # Exactly market value
        patience_modifier=1.4,  # Very patient
        walkaway_threshold=0.48,  # Almost impossible to offend
        loyalty_modifier=0.02,
        prefers_praise=False,
        prefers_criticism=False,  # Doesn't need external validation
    ),
    # =========================================================================
    # ANCHOR - Reliable, passive, patient
    # =========================================================================
    ArchetypeType.ANCHOR: Archetype(
        archetype_type=ArchetypeType.ANCHOR,
        description="Reliable, steady presence - the rock of the team",
        trait_weights={
            Trait.PATIENT: (0.85, 0.10),
            Trait.RESERVED: (0.75, 0.15),
            Trait.LEVEL_HEADED: (0.80, 0.10),
            Trait.VALUES_TRADITION: (0.70, 0.15),
            Trait.CONSERVATIVE: (0.70, 0.15),
            Trait.LOYAL: (0.65, 0.15),
            Trait.TEAM_PLAYER: (0.65, 0.15),
        },
        opening_demand_modifier=0.97,  # Accepts fair offers quickly
        patience_modifier=1.3,
        walkaway_threshold=0.50,
        loyalty_modifier=0.05,
        prefers_praise=False,
        prefers_criticism=False,
    ),
    # =========================================================================
    # TITAN - Aggressive, competitive, reckless
    # =========================================================================
    ArchetypeType.TITAN: Archetype(
        archetype_type=ArchetypeType.TITAN,
        description="Aggressive force of nature - competitive and intense",
        trait_weights={
            Trait.AGGRESSIVE: (0.90, 0.05),
            Trait.COMPETITIVE: (0.90, 0.05),
            Trait.RECKLESS: (0.75, 0.15),
            Trait.DRIVEN: (0.80, 0.10),
            Trait.AMBITIOUS: (0.70, 0.15),
            Trait.TEAM_PLAYER: (0.60, 0.20),
            Trait.IMPULSIVE: (0.65, 0.15),
        },
        opening_demand_modifier=1.15,  # Demands premium
        patience_modifier=0.7,  # Very impatient
        walkaway_threshold=0.68,  # Will walk
        loyalty_modifier=-0.02,
        prefers_praise=True,
        prefers_criticism=True,  # Responds to challenge
    ),
    # =========================================================================
    # HEADLINER - Dramatic, impulsive, expressive
    # =========================================================================
    ArchetypeType.HEADLINER: Archetype(
        archetype_type=ArchetypeType.HEADLINER,
        description="Loves the spotlight, dramatic and unpredictable",
        trait_weights={
            Trait.DRAMATIC: (0.90, 0.05),
            Trait.EXPRESSIVE: (0.85, 0.10),
            Trait.IMPULSIVE: (0.80, 0.10),
            Trait.AMBITIOUS: (0.75, 0.15),
            Trait.FLEXIBLE: (0.70, 0.15),
            Trait.RECKLESS: (0.60, 0.20),
            Trait.SENSITIVE: (0.55, 0.20),
        },
        opening_demand_modifier=1.12,  # Wants recognition
        patience_modifier=0.65,  # Very impatient
        walkaway_threshold=0.65,
        loyalty_modifier=-0.03,
        prefers_praise=True,
        prefers_criticism=False,
    ),
    # =========================================================================
    # ANALYST - Calculating, perfectionist, structured
    # =========================================================================
    ArchetypeType.ANALYST: Archetype(
        archetype_type=ArchetypeType.ANALYST,
        description="Data-driven perfectionist who values fairness and logic",
        trait_weights={
            Trait.CALCULATING: (0.90, 0.05),
            Trait.PERFECTIONIST: (0.85, 0.10),
            Trait.STRUCTURED: (0.80, 0.10),
            Trait.PATIENT: (0.70, 0.15),
            Trait.RESERVED: (0.65, 0.15),
            Trait.CONSERVATIVE: (0.60, 0.20),
            Trait.LEVEL_HEADED: (0.70, 0.15),
        },
        opening_demand_modifier=1.02,  # Respects market data
        patience_modifier=1.1,
        walkaway_threshold=0.58,
        loyalty_modifier=0.0,
        prefers_praise=False,
        prefers_criticism=True,  # Values honest feedback
    ),
    # =========================================================================
    # GURU - Reserved, conservative, trusting
    # =========================================================================
    ArchetypeType.GURU: Archetype(
        archetype_type=ArchetypeType.GURU,
        description="Quiet wisdom, reserved presence with deep trust",
        trait_weights={
            Trait.RESERVED: (0.85, 0.10),
            Trait.CONSERVATIVE: (0.75, 0.15),
            Trait.TRUSTING: (0.80, 0.10),
            Trait.PATIENT: (0.75, 0.15),
            Trait.LEVEL_HEADED: (0.70, 0.15),
            Trait.VALUES_TRADITION: (0.60, 0.20),
            Trait.TEAM_PLAYER: (0.65, 0.15),
        },
        opening_demand_modifier=0.98,  # Fair and quiet
        patience_modifier=1.2,
        walkaway_threshold=0.52,
        loyalty_modifier=0.04,
        prefers_praise=False,
        prefers_criticism=False,
    ),
    # =========================================================================
    # AMBASSADOR - Cooperative, expressive, trusting
    # =========================================================================
    ArchetypeType.AMBASSADOR: Archetype(
        archetype_type=ArchetypeType.AMBASSADOR,
        description="Diplomatic presence who builds bridges and values cooperation",
        trait_weights={
            Trait.COOPERATIVE: (0.90, 0.05),
            Trait.EXPRESSIVE: (0.80, 0.10),
            Trait.TRUSTING: (0.80, 0.10),
            Trait.TEAM_PLAYER: (0.75, 0.10),
            Trait.LOYAL: (0.70, 0.15),
            Trait.FLEXIBLE: (0.70, 0.15),
            Trait.LEVEL_HEADED: (0.65, 0.15),
        },
        opening_demand_modifier=0.98,  # Easy to negotiate with
        patience_modifier=1.15,
        walkaway_threshold=0.52,
        loyalty_modifier=0.06,
        prefers_praise=True,
        prefers_criticism=True,
    ),
}


def get_archetype(archetype_type: ArchetypeType) -> Archetype:
    """Get the archetype definition for a given type."""
    return ARCHETYPE_DEFINITIONS[archetype_type]


def get_archetype_description(archetype_type: ArchetypeType) -> str:
    """Get a human-readable description of an archetype."""
    return ARCHETYPE_DEFINITIONS[archetype_type].description
