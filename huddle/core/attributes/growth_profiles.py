"""Growth category definitions and ceiling ranges for per-attribute potential.

Physical attributes (speed, strength, etc.) have genetics-limited ceilings,
while mental and technique attributes can be trained more significantly.
"""

from enum import Enum


class GrowthCategory(Enum):
    """Categories that determine how much an attribute can grow."""

    PHYSICAL = "physical"  # Genetics-limited: +2-8 ceiling
    MENTAL = "mental"  # Highly trainable: +5-18 ceiling
    TECHNIQUE = "technique"  # Trainable: +4-15 ceiling
    SPECIAL = "special"  # Position-specific: +3-12 ceiling


# Map each attribute to its growth category
ATTRIBUTE_GROWTH_CATEGORIES: dict[str, GrowthCategory] = {
    # Physical (genetics-limited)
    "speed": GrowthCategory.PHYSICAL,
    "acceleration": GrowthCategory.PHYSICAL,
    "agility": GrowthCategory.PHYSICAL,
    "strength": GrowthCategory.PHYSICAL,
    "jumping": GrowthCategory.PHYSICAL,
    "stamina": GrowthCategory.PHYSICAL,
    # Mental (highly trainable)
    "awareness": GrowthCategory.MENTAL,
    "play_recognition": GrowthCategory.MENTAL,
    "zone_coverage": GrowthCategory.MENTAL,
    "man_coverage": GrowthCategory.MENTAL,
    "press": GrowthCategory.MENTAL,
    "ball_carrier_vision": GrowthCategory.MENTAL,
    # Technique (trainable)
    "throw_power": GrowthCategory.TECHNIQUE,
    "throw_accuracy_short": GrowthCategory.TECHNIQUE,
    "throw_accuracy_med": GrowthCategory.TECHNIQUE,
    "throw_accuracy_deep": GrowthCategory.TECHNIQUE,
    "throw_on_run": GrowthCategory.TECHNIQUE,
    "play_action": GrowthCategory.TECHNIQUE,
    "carrying": GrowthCategory.TECHNIQUE,
    "break_tackle": GrowthCategory.TECHNIQUE,
    "trucking": GrowthCategory.TECHNIQUE,
    "elusiveness": GrowthCategory.TECHNIQUE,
    "stiff_arm": GrowthCategory.TECHNIQUE,
    "spin_move": GrowthCategory.TECHNIQUE,
    "juke_move": GrowthCategory.TECHNIQUE,
    "catching": GrowthCategory.TECHNIQUE,
    "catch_in_traffic": GrowthCategory.TECHNIQUE,
    "spectacular_catch": GrowthCategory.TECHNIQUE,
    "release": GrowthCategory.TECHNIQUE,
    "route_running": GrowthCategory.TECHNIQUE,
    "run_block": GrowthCategory.TECHNIQUE,
    "pass_block": GrowthCategory.TECHNIQUE,
    "impact_blocking": GrowthCategory.TECHNIQUE,
    "block_shedding": GrowthCategory.TECHNIQUE,
    "tackle": GrowthCategory.TECHNIQUE,
    "hit_power": GrowthCategory.TECHNIQUE,
    "pursuit": GrowthCategory.TECHNIQUE,
    "power_moves": GrowthCategory.TECHNIQUE,
    "finesse_moves": GrowthCategory.TECHNIQUE,
    # Special (position-specific, moderate growth)
    "kick_power": GrowthCategory.SPECIAL,
    "kick_accuracy": GrowthCategory.SPECIAL,
    "kick_return": GrowthCategory.SPECIAL,
    "injury": GrowthCategory.SPECIAL,
    "toughness": GrowthCategory.SPECIAL,
    "learning": GrowthCategory.SPECIAL,
}

# Growth ceiling ranges by category (min_growth, max_growth)
GROWTH_CEILING_RANGES: dict[GrowthCategory, tuple[int, int]] = {
    GrowthCategory.PHYSICAL: (1, 6),  # Lowered - genetics are limiting
    GrowthCategory.MENTAL: (5, 18),
    GrowthCategory.TECHNIQUE: (4, 15),
    GrowthCategory.SPECIAL: (3, 12),
}

# Attribute-specific overrides for growth ranges
# Speed is the most genetics-limited - you either have it or you don't
ATTRIBUTE_GROWTH_OVERRIDES: dict[str, tuple[int, int]] = {
    "speed": (0, 5),  # Speed limited but raw athletes exist
    "acceleration": (0, 6),  # Slightly more trainable than top speed
    "jumping": (0, 5),  # Vertical is largely genetic
}

# Draft tier modifiers affect ceiling ranges
# Elite prospects have higher ceilings, UDFAs have lower ceilings
TIER_CEILING_MODIFIERS: dict[str, float] = {
    "elite": 1.3,
    "day1": 1.15,
    "day2": 1.0,
    "day3_early": 0.9,
    "day3_late": 0.75,
    "udfa": 0.6,
}
