"""Player attribute system."""

from huddle.core.attributes.base import AttributeCategory, AttributeDefinition
from huddle.core.attributes.growth_profiles import (
    GrowthCategory,
    ATTRIBUTE_GROWTH_CATEGORIES,
    ATTRIBUTE_GROWTH_OVERRIDES,
    GROWTH_CEILING_RANGES,
    TIER_CEILING_MODIFIERS,
)
from huddle.core.attributes.registry import AttributeRegistry, PlayerAttributes

__all__ = [
    "AttributeCategory",
    "AttributeDefinition",
    "AttributeRegistry",
    "PlayerAttributes",
    "GrowthCategory",
    "ATTRIBUTE_GROWTH_CATEGORIES",
    "ATTRIBUTE_GROWTH_OVERRIDES",
    "GROWTH_CEILING_RANGES",
    "TIER_CEILING_MODIFIERS",
]
