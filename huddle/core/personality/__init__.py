"""
Personality System.

HC09-style personality archetypes that govern player behavior in:
- Contract negotiations
- Event reactions (future)
- Morale and chemistry (future)
- Staff compatibility (future)

The system is built on two layers:
1. Traits - Individual personality characteristics (LOYAL, AGGRESSIVE, etc.)
2. Archetypes - Predefined trait combinations (COMMANDER, SUPERSTAR, etc.)

Each player has a PersonalityProfile containing their archetype and
individual trait values (which can vary within the archetype).

Example usage:
    from huddle.core.personality import (
        generate_personality,
        ArchetypeType,
        Trait,
    )

    # Generate personality based on position
    personality = generate_personality(position="QB")

    # Check specific traits
    if personality.is_trait_strong(Trait.LOYAL):
        print("This player values loyalty")

    # Get negotiation modifiers
    demand_modifier = personality.get_opening_demand_modifier()
"""

from huddle.core.personality.traits import (
    Trait,
    MOTIVATION_TRAITS,
    INTERPERSONAL_TRAITS,
    TEMPERAMENT_TRAITS,
    WORK_STYLE_TRAITS,
    RISK_TRAITS,
    SOCIAL_TRAITS,
    VALUE_TRAITS,
    ALL_TRAITS,
)

from huddle.core.personality.archetypes import (
    ArchetypeType,
    Archetype,
    ARCHETYPE_DEFINITIONS,
    get_archetype,
    get_archetype_description,
)

from huddle.core.personality.profile import PersonalityProfile

from huddle.core.personality.generation import (
    generate_personality,
    assign_personality_to_player,
    get_archetype_distribution,
    get_common_archetypes,
)


__all__ = [
    # Traits
    "Trait",
    "MOTIVATION_TRAITS",
    "INTERPERSONAL_TRAITS",
    "TEMPERAMENT_TRAITS",
    "WORK_STYLE_TRAITS",
    "RISK_TRAITS",
    "SOCIAL_TRAITS",
    "VALUE_TRAITS",
    "ALL_TRAITS",
    # Archetypes
    "ArchetypeType",
    "Archetype",
    "ARCHETYPE_DEFINITIONS",
    "get_archetype",
    "get_archetype_description",
    # Profile
    "PersonalityProfile",
    # Generation
    "generate_personality",
    "assign_personality_to_player",
    "get_archetype_distribution",
    "get_common_archetypes",
]
