"""
Personality Profile.

The PersonalityProfile is the actual personality instance attached to a player.
It contains their archetype and individual trait values.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from huddle.core.personality.traits import Trait
from huddle.core.personality.archetypes import (
    ArchetypeType,
    Archetype,
    ARCHETYPE_DEFINITIONS,
)


@dataclass
class PersonalityProfile:
    """
    A specific person's personality profile.

    Contains their archetype and individual trait values.
    Trait values can deviate from archetype defaults, making each
    person unique even within the same archetype.

    Provides helper methods for:
    - Querying trait values
    - Calculating negotiation modifiers
    - Serialization/deserialization
    """

    archetype: ArchetypeType
    traits: Dict[Trait, float] = field(default_factory=dict)

    @property
    def archetype_definition(self) -> Archetype:
        """Get the full archetype definition."""
        return ARCHETYPE_DEFINITIONS[self.archetype]

    def get_trait(self, trait: Trait, default: float = 0.5) -> float:
        """
        Get a trait value (0.0-1.0).

        Args:
            trait: The trait to query
            default: Value to return if trait not set (default 0.5 = neutral)

        Returns:
            Trait value between 0.0 and 1.0
        """
        return self.traits.get(trait, default)

    def is_trait_strong(self, trait: Trait, threshold: float = 0.7) -> bool:
        """
        Check if a trait is above a threshold.

        Args:
            trait: The trait to check
            threshold: Minimum value to be considered "strong" (default 0.7)

        Returns:
            True if trait value >= threshold
        """
        return self.get_trait(trait) >= threshold

    def is_trait_weak(self, trait: Trait, threshold: float = 0.3) -> bool:
        """
        Check if a trait is below a threshold.

        Args:
            trait: The trait to check
            threshold: Maximum value to be considered "weak" (default 0.3)

        Returns:
            True if trait value <= threshold
        """
        return self.get_trait(trait) <= threshold

    # =========================================================================
    # Negotiation Modifiers
    # =========================================================================

    def get_opening_demand_modifier(self) -> float:
        """
        Calculate the opening demand multiplier for contract negotiations.

        Base comes from archetype, modified by individual traits.

        Returns:
            Multiplier for opening contract demand (e.g., 1.15 = +15%)
        """
        base = self.archetype_definition.opening_demand_modifier

        # Materialistic players want more money
        if self.is_trait_strong(Trait.MATERIALISTIC):
            base *= 1.08

        # Loyal/team players are more flexible
        if self.is_trait_strong(Trait.LOYAL):
            base *= 0.96
        if self.is_trait_strong(Trait.TEAM_PLAYER):
            base *= 0.97

        # Ambitious players push harder
        if self.is_trait_strong(Trait.AMBITIOUS):
            base *= 1.05

        # Thrifty players are actually content with less (surprising but true)
        if self.is_trait_strong(Trait.THRIFTY):
            base *= 0.98

        return base

    def get_patience_modifier(self) -> float:
        """
        Calculate patience modifier for negotiations.

        Higher = more patient, lower = more likely to walk.

        Returns:
            Patience multiplier (1.0 = normal, 1.3 = very patient, 0.7 = impatient)
        """
        base = self.archetype_definition.patience_modifier

        # Patient trait directly affects patience
        if self.is_trait_strong(Trait.PATIENT):
            base *= 1.15
        elif self.is_trait_weak(Trait.PATIENT):
            base *= 0.85

        # Impulsive reduces patience
        if self.is_trait_strong(Trait.IMPULSIVE):
            base *= 0.85

        # Level-headed increases patience
        if self.is_trait_strong(Trait.LEVEL_HEADED):
            base *= 1.08

        # Aggressive reduces patience
        if self.is_trait_strong(Trait.AGGRESSIVE):
            base *= 0.90

        return base

    def get_walkaway_threshold(self) -> float:
        """
        Get the percentage of market value below which player may walk away.

        Returns:
            Threshold as decimal (0.60 = 60% of market value)
        """
        base = self.archetype_definition.walkaway_threshold

        # Sensitive players walk away faster
        if self.is_trait_strong(Trait.SENSITIVE):
            base += 0.05

        # Reckless players may walk impulsively
        if self.is_trait_strong(Trait.RECKLESS):
            base += 0.03

        # Patient players tolerate more
        if self.is_trait_strong(Trait.PATIENT):
            base -= 0.04

        # Calculating players are pragmatic
        if self.is_trait_strong(Trait.CALCULATING):
            base -= 0.03

        # Loyal players give benefit of the doubt
        if self.is_trait_strong(Trait.LOYAL):
            base -= 0.03

        return max(0.40, min(0.80, base))  # Clamp to reasonable range

    def get_loyalty_modifier(self) -> float:
        """
        Get loyalty modifier for current team discounts.

        Positive = willing to take less to stay, negative = follows money.

        Returns:
            Loyalty modifier (-0.1 to +0.1 range typically)
        """
        base = self.archetype_definition.loyalty_modifier

        # Loyal trait directly affects
        if self.is_trait_strong(Trait.LOYAL):
            base += 0.04
        elif self.is_trait_weak(Trait.LOYAL):
            base -= 0.02

        # Team players value staying
        if self.is_trait_strong(Trait.TEAM_PLAYER):
            base += 0.03

        # Materialistic players follow money
        if self.is_trait_strong(Trait.MATERIALISTIC):
            base -= 0.04

        # Values tradition players want to build legacy
        if self.is_trait_strong(Trait.VALUES_TRADITION):
            base += 0.02

        return base

    def get_counter_offer_aggressiveness(self) -> float:
        """
        How aggressively player counters in negotiations.

        Higher = smaller concessions per round.

        Returns:
            Aggressiveness factor (0.3-0.7 typical range)
        """
        # Base: concede 40-60% of gap per round
        base = 0.50

        # Aggressive players concede less
        if self.is_trait_strong(Trait.AGGRESSIVE):
            base -= 0.10

        # Calculating players are strategic
        if self.is_trait_strong(Trait.CALCULATING):
            base -= 0.05

        # Cooperative players concede more
        if self.is_trait_strong(Trait.COOPERATIVE):
            base += 0.10

        # Trusting players are more flexible
        if self.is_trait_strong(Trait.TRUSTING):
            base += 0.05

        return max(0.25, min(0.75, base))

    # =========================================================================
    # Future: Morale & Event Reactions
    # =========================================================================

    def get_morale_sensitivity(self) -> float:
        """
        How strongly this person reacts to morale-affecting events.

        Returns:
            Sensitivity multiplier (1.0 = normal, 1.5 = very sensitive)
        """
        base = 1.0

        if self.is_trait_strong(Trait.SENSITIVE):
            base *= 1.4

        if self.is_trait_strong(Trait.DRAMATIC):
            base *= 1.2

        if self.is_trait_strong(Trait.LEVEL_HEADED):
            base *= 0.8

        if self.is_trait_strong(Trait.STOIC if hasattr(Trait, "STOIC") else Trait.RESERVED):
            base *= 0.85

        return base

    def prefers_praise(self) -> bool:
        """Whether this person responds well to praise and positive feedback."""
        return self.archetype_definition.prefers_praise

    def prefers_criticism(self) -> bool:
        """Whether this person responds well to tough love / constructive criticism."""
        return self.archetype_definition.prefers_criticism

    # =========================================================================
    # Inner Weather: Mental State Properties
    # =========================================================================

    def get_confidence_volatility(self) -> float:
        """
        How much confidence swings during a game.

        Higher volatility = bigger swings (both up and down).
        LEVEL_HEADED types have smaller swings, DRAMATIC types have larger.

        Returns:
            Volatility multiplier (0.6 = steady, 1.0 = normal, 1.4 = volatile)
        """
        base = 1.0

        # Dramatic personalities have larger swings
        if self.is_trait_strong(Trait.DRAMATIC):
            base *= 1.35

        # Impulsive personalities react more strongly
        if self.is_trait_strong(Trait.IMPULSIVE):
            base *= 1.15

        # Sensitive personalities feel everything more
        if self.is_trait_strong(Trait.SENSITIVE):
            base *= 1.1

        # Level-headed personalities stay steady
        if self.is_trait_strong(Trait.LEVEL_HEADED):
            base *= 0.7

        # Patient personalities don't overreact
        if self.is_trait_strong(Trait.PATIENT):
            base *= 0.85

        # Reserved personalities keep emotions in check
        if self.is_trait_strong(Trait.RESERVED):
            base *= 0.9

        return max(0.4, min(1.6, base))  # Clamp to reasonable range

    def get_pressure_response(self) -> float:
        """
        How the player responds to pressure situations.

        Positive = rises to the occasion, negative = wilts under pressure.

        Returns:
            Pressure response (-0.3 to +0.3 typical range)
        """
        base = 0.0

        # Competitive personalities rise to challenges
        if self.is_trait_strong(Trait.COMPETITIVE):
            base += 0.15

        # Driven personalities push through
        if self.is_trait_strong(Trait.DRIVEN):
            base += 0.1

        # Aggressive personalities feed off pressure
        if self.is_trait_strong(Trait.AGGRESSIVE):
            base += 0.08

        # Sensitive personalities struggle under scrutiny
        if self.is_trait_strong(Trait.SENSITIVE):
            base -= 0.12

        # Conservative personalities play it safe (neither rises nor wilts)
        if self.is_trait_strong(Trait.CONSERVATIVE):
            base -= 0.05

        # Reckless personalities can crack either way
        if self.is_trait_strong(Trait.RECKLESS):
            base += 0.05  # Slight positive - they don't feel the weight

        return max(-0.4, min(0.4, base))

    def get_baseline_confidence_modifier(self) -> float:
        """
        Personality-based modifier to starting confidence.

        Some personalities naturally start games more confident.

        Returns:
            Confidence modifier (-10 to +10 range)
        """
        base = 0.0

        # Driven personalities have natural self-belief
        if self.is_trait_strong(Trait.DRIVEN):
            base += 5.0

        # Competitive personalities back themselves
        if self.is_trait_strong(Trait.COMPETITIVE):
            base += 4.0

        # Ambitious personalities expect to succeed
        if self.is_trait_strong(Trait.AMBITIOUS):
            base += 3.0

        # Sensitive personalities have more self-doubt
        if self.is_trait_strong(Trait.SENSITIVE):
            base -= 4.0

        # Conservative personalities don't overrate themselves
        if self.is_trait_strong(Trait.CONSERVATIVE):
            base -= 2.0

        return max(-15.0, min(15.0, base))

    def get_confidence_recovery_rate(self) -> float:
        """
        How quickly confidence recovers after negative events.

        Higher = bounces back faster.

        Returns:
            Recovery rate multiplier (0.6 = slow, 1.0 = normal, 1.4 = fast)
        """
        base = 1.0

        # Level-headed personalities don't dwell
        if self.is_trait_strong(Trait.LEVEL_HEADED):
            base *= 1.3

        # Patient personalities let things go
        if self.is_trait_strong(Trait.PATIENT):
            base *= 1.15

        # Driven personalities move on quickly
        if self.is_trait_strong(Trait.DRIVEN):
            base *= 1.1

        # Sensitive personalities hold onto mistakes
        if self.is_trait_strong(Trait.SENSITIVE):
            base *= 0.7

        # Dramatic personalities relive bad moments
        if self.is_trait_strong(Trait.DRAMATIC):
            base *= 0.8

        return max(0.5, min(1.5, base))

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "archetype": self.archetype.value,
            "traits": {t.value: v for t, v in self.traits.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersonalityProfile":
        """Create from dictionary."""
        archetype = ArchetypeType(data.get("archetype", "stoic"))
        traits = {}
        for trait_str, value in data.get("traits", {}).items():
            try:
                trait = Trait(trait_str)
                traits[trait] = value
            except ValueError:
                pass  # Skip unknown traits for forward compatibility
        return cls(archetype=archetype, traits=traits)

    def __str__(self) -> str:
        return f"{self.archetype.value.title()}"

    def __repr__(self) -> str:
        return f"PersonalityProfile(archetype={self.archetype.value})"
