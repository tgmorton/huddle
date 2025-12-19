"""
Personality Traits.

Individual traits that combine into personality archetypes.
Each trait is measured 0.0 (not present) to 1.0 (very strong).

Inspired by NFL Head Coach 09's personality system.
"""

from enum import Enum


class Trait(Enum):
    """
    Individual personality traits.

    Traits are the atomic building blocks of personality. Each archetype
    is defined by a combination of traits with specific weights.

    Traits can be queried individually for nuanced behavior, or archetypes
    can be used for broad behavioral categories.
    """

    # =========================================================================
    # Motivation & Drive
    # =========================================================================
    DRIVEN = "driven"
    """Ambitious, wants to win, pushes hard for success."""

    COMPETITIVE = "competitive"
    """Loves competition, hates losing, rises to challenges."""

    AMBITIOUS = "ambitious"
    """Wants more - money, fame, status, records."""

    # =========================================================================
    # Interpersonal
    # =========================================================================
    LOYAL = "loyal"
    """Values team and relationships over money."""

    TEAM_PLAYER = "team_player"
    """Puts team success above personal glory."""

    TRUSTING = "trusting"
    """Gives benefit of the doubt, believes in good faith."""

    COOPERATIVE = "cooperative"
    """Works well with others, willing to compromise."""

    # =========================================================================
    # Temperament
    # =========================================================================
    PATIENT = "patient"
    """Willing to wait for results, doesn't rush decisions."""

    AGGRESSIVE = "aggressive"
    """Confrontational, direct, pushes back hard."""

    IMPULSIVE = "impulsive"
    """Acts without thinking, makes snap decisions."""

    LEVEL_HEADED = "level_headed"
    """Calm under pressure, doesn't get rattled."""

    SENSITIVE = "sensitive"
    """Easily offended or affected by criticism."""

    # =========================================================================
    # Work Style
    # =========================================================================
    STRUCTURED = "structured"
    """Prefers routine, rules, clear expectations."""

    FLEXIBLE = "flexible"
    """Adapts to change, comfortable with ambiguity."""

    PERFECTIONIST = "perfectionist"
    """High standards, attention to detail, hard on self."""

    # =========================================================================
    # Risk Profile
    # =========================================================================
    CONSERVATIVE = "conservative"
    """Risk-averse, prefers safe choices."""

    RECKLESS = "reckless"
    """Takes big risks, gambles on outcomes."""

    CALCULATING = "calculating"
    """Weighs options carefully, thinks strategically."""

    # =========================================================================
    # Social Style
    # =========================================================================
    EXPRESSIVE = "expressive"
    """Outgoing, vocal, shares feelings openly."""

    RESERVED = "reserved"
    """Keeps to self, private, measured responses."""

    DRAMATIC = "dramatic"
    """Makes things bigger than they are, loves spotlight."""

    # =========================================================================
    # Values
    # =========================================================================
    MATERIALISTIC = "materialistic"
    """Values money and possessions highly."""

    VALUES_TRADITION = "values_tradition"
    """Respects history, legacy, the old ways."""

    THRIFTY = "thrifty"
    """Careful with money, values financial security."""


# Trait categories for organized access
MOTIVATION_TRAITS = [Trait.DRIVEN, Trait.COMPETITIVE, Trait.AMBITIOUS]
INTERPERSONAL_TRAITS = [Trait.LOYAL, Trait.TEAM_PLAYER, Trait.TRUSTING, Trait.COOPERATIVE]
TEMPERAMENT_TRAITS = [Trait.PATIENT, Trait.AGGRESSIVE, Trait.IMPULSIVE, Trait.LEVEL_HEADED, Trait.SENSITIVE]
WORK_STYLE_TRAITS = [Trait.STRUCTURED, Trait.FLEXIBLE, Trait.PERFECTIONIST]
RISK_TRAITS = [Trait.CONSERVATIVE, Trait.RECKLESS, Trait.CALCULATING]
SOCIAL_TRAITS = [Trait.EXPRESSIVE, Trait.RESERVED, Trait.DRAMATIC]
VALUE_TRAITS = [Trait.MATERIALISTIC, Trait.VALUES_TRADITION, Trait.THRIFTY]

# All traits in one list
ALL_TRAITS = (
    MOTIVATION_TRAITS
    + INTERPERSONAL_TRAITS
    + TEMPERAMENT_TRAITS
    + WORK_STYLE_TRAITS
    + RISK_TRAITS
    + SOCIAL_TRAITS
    + VALUE_TRAITS
)
