"""Per-attribute potential generation for draft prospects.

Generates realistic potential ceilings based on:
- Growth category (physical vs mental vs technique)
- Draft tier (elite prospects have higher ceilings)
- Individual player variance (late bloomers vs early peaks)
- Scouting accuracy (perceived vs actual potential)
"""

import random
from typing import Optional

from huddle.core.attributes.growth_profiles import (
    GrowthCategory,
    ATTRIBUTE_GROWTH_CATEGORIES,
    ATTRIBUTE_GROWTH_OVERRIDES,
    GROWTH_CEILING_RANGES,
    TIER_CEILING_MODIFIERS,
)


def generate_attribute_potential(
    attr_name: str,
    current_value: int,
    tier: str = "day2",
    player_ceiling_modifier: float = 1.0,
) -> int:
    """
    Generate potential ceiling for a single attribute.

    Args:
        attr_name: Attribute name (e.g., "speed", "awareness")
        current_value: Current attribute value
        tier: Draft tier (elite, day1, day2, day3_early, day3_late, udfa)
        player_ceiling_modifier: Individual player variance (0.85-1.15)

    Returns:
        Potential ceiling (capped at 99)
    """
    # Check for attribute-specific overrides first (e.g., speed has lower growth)
    if attr_name in ATTRIBUTE_GROWTH_OVERRIDES:
        base_min, base_max = ATTRIBUTE_GROWTH_OVERRIDES[attr_name]
    else:
        category = ATTRIBUTE_GROWTH_CATEGORIES.get(attr_name, GrowthCategory.TECHNIQUE)
        base_min, base_max = GROWTH_CEILING_RANGES[category]

    # ==========================================================================
    # Peaked vs Raw Player Mechanic
    # High-rated attributes may already be near ceiling (polished)
    # Low-rated attributes may have big upside (raw/developmental)
    # ==========================================================================

    # HIGH-RATED: More likely to be peaked
    if current_value >= 90:
        peaked_roll = random.random()
        if peaked_roll < 0.25:  # 25% already at ceiling
            return current_value
        elif peaked_roll < 0.50:  # 25% minimal growth
            return min(99, current_value + random.randint(1, 2))
        # else: 50% normal growth (continues below)
    elif current_value >= 85:
        peaked_roll = random.random()
        if peaked_roll < 0.10:  # 10% already at ceiling
            return current_value
        elif peaked_roll < 0.25:  # 15% minimal growth
            return min(99, current_value + random.randint(1, 2))
        # else: 75% normal growth

    # LOW-RATED: Chance to be "raw" with big upside
    elif current_value <= 75:
        raw_roll = random.random()
        if raw_roll < 0.12:  # 12% are raw athletes with big upside
            # Raw prospect: 1.5-2x normal growth
            raw_multiplier = random.uniform(1.5, 2.0)
            growth = int(base_max * raw_multiplier)
            return min(99, current_value + growth)

    # Apply tier modifier
    tier_mod = TIER_CEILING_MODIFIERS.get(tier, 1.0)

    # Calculate ceiling range
    min_growth = int(base_min * tier_mod * player_ceiling_modifier)
    max_growth = int(base_max * tier_mod * player_ceiling_modifier)

    # Allow 0 growth for physical attributes (already peaked scenarios)
    if base_min == 0:
        min_growth = 0
    else:
        min_growth = max(1, min_growth)
    max_growth = max(min_growth + 1, max_growth)

    # Generate ceiling with slight bias toward middle (triangular distribution)
    growth = int(random.triangular(min_growth, max_growth, (min_growth + max_growth) / 2))

    potential = current_value + growth
    return min(99, potential)


def generate_perceived_potential(
    actual_potential: int,
    scouted_percentage: int,
    is_bust: bool = False,
    is_gem: bool = False,
) -> int:
    """
    Generate media/scout perceived potential that may differ from actual.

    More scouting = more accurate perception.
    Busts have inflated perceived potential.
    Gems have deflated perceived potential.

    Args:
        actual_potential: True potential ceiling
        scouted_percentage: How much scouting done (0-100)
        is_bust: If True, perceived is inflated
        is_gem: If True, perceived is deflated

    Returns:
        Perceived potential ceiling
    """
    # Base error decreases with scouting
    max_error = int(15 * (1 - scouted_percentage / 100))

    if is_bust:
        # Overrated: perceived higher than actual
        inflation = random.randint(5, 15)
        error = random.randint(0, max_error)
        return min(99, actual_potential + inflation + error)
    elif is_gem:
        # Underrated: perceived lower than actual
        deflation = random.randint(5, 15)
        error = random.randint(-max_error, 0)
        return max(40, actual_potential - deflation + error)
    else:
        # Normal variance
        error = random.randint(-max_error, max_error)
        return max(40, min(99, actual_potential + error))


def generate_all_potentials(
    attributes: dict[str, int],
    tier: str = "day2",
    is_bust: bool = False,
    is_gem: bool = False,
    scouted_percentage: int = 0,
) -> tuple[dict[str, int], dict[str, int]]:
    """
    Generate all attribute potentials for a player.

    Args:
        attributes: Dict of current attribute values
        tier: Draft tier
        is_bust: Media overrates this player
        is_gem: Media underrates this player
        scouted_percentage: Scouting progress

    Returns:
        Tuple of (actual_potentials, perceived_potentials)
        Keys are formatted as "{attr_name}_potential"
    """
    # Individual player variance (some players are late bloomers, some peak early)
    player_ceiling_mod = random.uniform(0.85, 1.15)

    actual_potentials: dict[str, int] = {}
    perceived_potentials: dict[str, int] = {}

    for attr_name, current_value in attributes.items():
        # Skip non-trainable attributes and potential keys
        if attr_name.endswith("_potential"):
            continue
        if attr_name not in ATTRIBUTE_GROWTH_CATEGORIES:
            continue

        # Generate actual potential
        actual = generate_attribute_potential(
            attr_name, current_value, tier, player_ceiling_mod
        )
        actual_potentials[f"{attr_name}_potential"] = actual

        # Generate perceived potential
        perceived = generate_perceived_potential(
            actual, scouted_percentage, is_bust, is_gem
        )
        perceived_potentials[f"{attr_name}_potential"] = perceived

    return actual_potentials, perceived_potentials


def calculate_overall_potential(
    potentials: dict[str, int],
    position: str,
) -> int:
    """
    Calculate an aggregate potential rating for display purposes.

    This mirrors the overall calculation but uses potential values.

    Args:
        potentials: Dict of {attr_name}_potential values
        position: Player position for weighting

    Returns:
        Aggregate potential rating
    """
    from huddle.core.attributes.registry import AttributeRegistry

    relevant_attrs = AttributeRegistry.get_for_position(position)
    if not relevant_attrs:
        if potentials:
            return int(sum(potentials.values()) / len(potentials))
        return 50

    total_weight = 0.0
    weighted_sum = 0.0

    for attr_def in relevant_attrs:
        weight = attr_def.position_weights.get(position, 0.0)
        potential_key = f"{attr_def.name}_potential"
        if potential_key in potentials:
            weighted_sum += potentials[potential_key] * weight
            total_weight += weight

    if total_weight == 0:
        return 50

    return int(weighted_sum / total_weight)


# =============================================================================
# Durability Scouting System
# =============================================================================

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from huddle.core.models.player import Player


# Body parts that can be scouted for durability
DURABILITY_BODY_PARTS = [
    "head",
    "torso",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
]

# Injury types that might appear in college history
COLLEGE_INJURY_TYPES = [
    ("knee", "left_leg"),
    ("knee", "right_leg"),
    ("ankle", "left_leg"),
    ("ankle", "right_leg"),
    ("hamstring", "left_leg"),
    ("hamstring", "right_leg"),
    ("shoulder", "left_arm"),
    ("shoulder", "right_arm"),
    ("concussion", "head"),
    ("back", "torso"),
]


@dataclass
class DurabilityScoutReport:
    """Scout's estimate of prospect durability for a body part."""

    body_part: str
    estimated_rating: int  # Scout's guess (may be wrong)
    confidence: str  # "low", "medium", "high"
    red_flag: bool  # History suggests concern
    notes: str  # e.g., "Missed 4 games junior year with knee injury"


@dataclass
class ProspectDurabilityReport:
    """Complete durability scouting report for a prospect."""

    reports: list[DurabilityScoutReport] = field(default_factory=list)
    overall_concern: str = "none"  # "none", "minor", "moderate", "major"
    college_injury_history: list[dict] = field(default_factory=list)
    physical_completed: bool = False

    def get_body_part_report(self, body_part: str) -> Optional[DurabilityScoutReport]:
        """Get report for a specific body part."""
        for report in self.reports:
            if report.body_part == body_part:
                return report
        return None


def generate_college_injury_history(
    actual_durability: dict[str, int],
    position: str,
) -> list[dict]:
    """
    Generate simulated college injury history based on durability.

    Lower durability = more likely to have had college injuries.

    Args:
        actual_durability: True durability ratings by body part
        position: Player position (affects injury likelihood)

    Returns:
        List of injury history entries
    """
    history = []

    # Position injury modifiers (some positions get hurt more)
    pos_modifier = {
        "RB": 1.3, "WR": 1.2, "TE": 1.1, "LB": 1.2, "CB": 1.1,
        "DL": 1.2, "OL": 1.0, "QB": 0.8, "S": 1.0,
    }.get(position, 1.0)

    for injury_type, body_part in COLLEGE_INJURY_TYPES:
        durability = actual_durability.get(body_part, 75)

        # Lower durability = higher chance of having had this injury
        # 40 durability = 40% chance, 75 = 15% chance, 99 = 1% chance
        base_chance = max(0.01, (100 - durability) / 150)
        injury_chance = base_chance * pos_modifier

        if random.random() < injury_chance:
            # Determine severity
            if random.random() < 0.15:  # 15% season-ending
                games_missed = random.randint(8, 12)
                severity = "season-ending"
                year = random.choice(["freshman", "sophomore", "junior"])
            elif random.random() < 0.40:  # Multi-game
                games_missed = random.randint(2, 6)
                severity = "moderate"
                year = random.choice(["freshman", "sophomore", "junior", "senior"])
            else:  # Minor
                games_missed = random.randint(1, 2)
                severity = "minor"
                year = random.choice(["sophomore", "junior", "senior"])

            history.append({
                "injury_type": injury_type,
                "body_part": body_part,
                "year": year,
                "games_missed": games_missed,
                "severity": severity,
            })

    return history


def generate_prospect_durability_report(
    player: "Player",
    scout_accuracy: float = 0.7,
) -> ProspectDurabilityReport:
    """
    Generate scout estimates for prospect durability.

    Estimates have error based on:
    - Scout accuracy rating (0.5 = poor scout, 1.0 = elite scout)
    - Whether player has injury history (more data = better estimate)
    - Random variance

    Red flags based on simulated college injury history.

    Args:
        player: The prospect being scouted
        scout_accuracy: Scout's ability (0.5-1.0)

    Returns:
        ProspectDurabilityReport with estimates and flags
    """
    # Get actual durability values
    actual_durability = {
        "head": player.attributes.get("head_durability", 75),
        "torso": player.attributes.get("torso_durability", 75),
        "left_arm": player.attributes.get("left_arm_durability", 75),
        "right_arm": player.attributes.get("right_arm_durability", 75),
        "left_leg": player.attributes.get("left_leg_durability", 75),
        "right_leg": player.attributes.get("right_leg_durability", 75),
    }

    # Generate college injury history (if not already present)
    if not player.injury_history:
        college_history = generate_college_injury_history(
            actual_durability, player.position.value
        )
    else:
        college_history = player.injury_history

    # Track which body parts have injury history
    injured_parts = set()
    for entry in college_history:
        injured_parts.add(entry.get("body_part", ""))

    reports = []
    concern_count = 0

    for body_part in DURABILITY_BODY_PARTS:
        actual = actual_durability[body_part]

        # Base error based on scout accuracy
        # Good scout: ±5 error, Poor scout: ±15 error
        max_error = int(20 * (1 - scout_accuracy))

        # Injury history improves accuracy for that body part
        if body_part in injured_parts:
            max_error = max(3, max_error - 5)
            has_history = True
        else:
            has_history = False

        # Generate estimate with error
        error = random.randint(-max_error, max_error)
        estimated = max(40, min(99, actual + error))

        # Determine confidence
        if has_history or scout_accuracy >= 0.85:
            confidence = "high"
        elif scout_accuracy >= 0.7:
            confidence = "medium"
        else:
            confidence = "low"

        # Red flag if actual is low OR if there's significant injury history
        red_flag = False
        notes = ""

        if has_history:
            # Find relevant injuries
            relevant = [e for e in college_history if e.get("body_part") == body_part]
            if relevant:
                total_games = sum(e.get("games_missed", 0) for e in relevant)
                most_recent = relevant[-1]

                if total_games >= 6 or any(e.get("severity") == "season-ending" for e in relevant):
                    red_flag = True
                    concern_count += 1

                injury_name = most_recent.get("injury_type", "injury")
                year = most_recent.get("year", "")
                notes = f"Missed {total_games} games with {injury_name} issues"
                if any(e.get("severity") == "season-ending" for e in relevant):
                    notes += " (season-ending)"

        # Also flag if estimated is very low
        if estimated <= 55 and not red_flag:
            red_flag = True
            concern_count += 1
            if not notes:
                notes = "Scouts concerned about long-term durability"

        reports.append(DurabilityScoutReport(
            body_part=body_part,
            estimated_rating=estimated,
            confidence=confidence,
            red_flag=red_flag,
            notes=notes,
        ))

    # Determine overall concern level
    if concern_count >= 3:
        overall = "major"
    elif concern_count == 2:
        overall = "moderate"
    elif concern_count == 1:
        overall = "minor"
    else:
        overall = "none"

    return ProspectDurabilityReport(
        reports=reports,
        overall_concern=overall,
        college_injury_history=college_history,
        physical_completed=False,
    )


def perform_physical_exam(player: "Player") -> dict[str, int]:
    """
    Full physical exam reveals true durability values.

    This is a management action that costs resources but provides
    accurate information for decision-making.

    Args:
        player: The prospect being examined

    Returns:
        Dict mapping body part to true durability rating
    """
    return {
        "head": player.attributes.get("head_durability", 75),
        "torso": player.attributes.get("torso_durability", 75),
        "left_arm": player.attributes.get("left_arm_durability", 75),
        "right_arm": player.attributes.get("right_arm_durability", 75),
        "left_leg": player.attributes.get("left_leg_durability", 75),
        "right_leg": player.attributes.get("right_leg_durability", 75),
        "toughness": player.attributes.get("toughness", 75),
    }
