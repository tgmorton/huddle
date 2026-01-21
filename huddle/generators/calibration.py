"""Calibrated player generation using NFL combine and contract data.

Loads research models and provides calibrated generation functions.
Research source: research/exports/active/
"""

import json
import math
import random
from pathlib import Path
from typing import Optional

# =============================================================================
# Load Research Models
# =============================================================================

_RESEARCH_DIR = Path(__file__).parent.parent.parent / "research" / "exports" / "active"


def _load_model(filename: str) -> dict:
    """Load a model JSON file from research exports."""
    path = _RESEARCH_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


# Load models at module import
PHYSICAL_MODEL = _load_model("physical_profile_model.json")
CONTRACT_MODEL = _load_model("contract_model.json")
DRAFT_MODEL = _load_model("draft_model.json")
POSITION_VALUE_MODEL = _load_model("position_value_model.json")


# =============================================================================
# Physical Generation (Calibrated)
# =============================================================================

# Position mapping for physical stats
POSITION_MAPPING = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",  # Use RB profile
    "WR": "WR",
    "TE": "TE",
    "OT": "OL",
    "OG": "OL",
    "C": "OL",
    "OL": "OL",
    "DE": "EDGE",
    "DT": "DL",
    "NT": "DL",
    "DL": "DL",
    "EDGE": "EDGE",
    "MLB": "LB",
    "ILB": "LB",
    "OLB": "EDGE",  # OLBs are often edge rushers
    "LB": "LB",
    "CB": "CB",
    "FS": "S",
    "SS": "S",
    "S": "S",
    "K": "K",
    "P": "P",
}


def get_physical_stats(position: str) -> dict:
    """Get calibrated physical stats for a position."""
    pos_stats = PHYSICAL_MODEL.get("position_stats", {})
    mapped_pos = POSITION_MAPPING.get(position, "WR")  # Default to WR
    return pos_stats.get(mapped_pos, {})


def generate_weight(position: str) -> int:
    """Generate calibrated weight for a position."""
    stats = get_physical_stats(position)
    wt_stats = stats.get("wt", {"mean": 220, "std": 20})

    weight = int(random.gauss(wt_stats["mean"], wt_stats["std"]))

    # Clamp to reasonable range
    min_wt = wt_stats.get("min", 160)
    max_wt = wt_stats.get("max", 350)
    return max(min_wt, min(max_wt, weight))


def generate_forty_time(position: str) -> float:
    """Generate calibrated 40-yard dash time for a position."""
    stats = get_physical_stats(position)
    forty_stats = stats.get("forty", {"mean": 4.70, "std": 0.15})

    forty = random.gauss(forty_stats["mean"], forty_stats["std"])

    # Clamp to reasonable range
    min_forty = forty_stats.get("min", 4.20)
    max_forty = forty_stats.get("max", 5.50)
    return round(max(min_forty, min(max_forty, forty)), 2)


def generate_vertical(position: str) -> float:
    """Generate calibrated vertical jump for a position."""
    stats = get_physical_stats(position)
    vert_stats = stats.get("vertical", {"mean": 33, "std": 3.5})

    vert = random.gauss(vert_stats["mean"], vert_stats["std"])

    # Clamp to reasonable range
    min_vert = vert_stats.get("min", 24)
    max_vert = vert_stats.get("max", 46)
    return round(max(min_vert, min(max_vert, vert)), 1)


def generate_broad_jump(position: str) -> int:
    """Generate calibrated broad jump for a position."""
    stats = get_physical_stats(position)
    broad_stats = stats.get("broad_jump", {"mean": 115, "std": 7})

    broad = random.gauss(broad_stats["mean"], broad_stats["std"])

    # Clamp to reasonable range
    min_broad = broad_stats.get("min", 90)
    max_broad = broad_stats.get("max", 140)
    return int(max(min_broad, min(max_broad, broad)))


def generate_bench_reps(position: str) -> int:
    """Generate calibrated bench press reps for a position."""
    stats = get_physical_stats(position)
    bench_stats = stats.get("bench", {"mean": 20, "std": 5})

    bench = random.gauss(bench_stats["mean"], bench_stats["std"])

    # Clamp to reasonable range (0-40 reps)
    return max(0, min(40, int(bench)))


def generate_cone_drill(position: str) -> float:
    """Generate calibrated 3-cone drill time for a position."""
    stats = get_physical_stats(position)
    cone_stats = stats.get("cone", {"mean": 7.10, "std": 0.20})

    cone = random.gauss(cone_stats["mean"], cone_stats["std"])

    # Clamp to reasonable range
    min_cone = cone_stats.get("min", 6.40)
    max_cone = cone_stats.get("max", 8.00)
    return round(max(min_cone, min(max_cone, cone)), 2)


def generate_shuttle(position: str) -> float:
    """Generate calibrated shuttle time for a position."""
    stats = get_physical_stats(position)
    shuttle_stats = stats.get("shuttle", {"mean": 4.30, "std": 0.15})

    shuttle = random.gauss(shuttle_stats["mean"], shuttle_stats["std"])

    # Clamp to reasonable range
    min_shuttle = shuttle_stats.get("min", 3.90)
    max_shuttle = shuttle_stats.get("max", 5.00)
    return round(max(min_shuttle, min(max_shuttle, shuttle)), 2)


# =============================================================================
# Attribute Conversion Functions
# =============================================================================

def forty_to_speed(forty_time: float) -> int:
    """
    Convert 40-yard dash time to speed rating.

    Elite (4.25s) = 99
    Slow (5.30s) = 50
    """
    # Linear interpolation
    speed = int(99 - (forty_time - 4.25) * 46.67)
    return max(40, min(99, speed))


def bench_to_strength(reps: int) -> int:
    """
    Convert bench press reps to strength rating.

    Elite (35+ reps) = 99
    Low (10 reps) = 60
    """
    strength = int(60 + (reps - 10) * 1.56)
    return max(40, min(99, strength))


def cone_to_agility(cone_time: float) -> int:
    """
    Convert 3-cone drill time to agility rating.

    Elite (6.50s) = 99
    Slow (8.00s) = 55
    """
    agility = int(99 - (cone_time - 6.50) * 29.33)
    return max(40, min(99, agility))


def vertical_to_jumping(vertical_inches: float) -> int:
    """
    Convert vertical jump to jumping rating.

    Elite (45 in) = 99
    Low (28 in) = 60
    """
    jumping = int(60 + (vertical_inches - 28) * 2.29)
    return max(40, min(99, jumping))


def weight_to_strength_bonus(weight: int, position: str) -> int:
    """
    Calculate strength bonus from weight (heavier = stronger baseline).

    Returns a bonus to add to base strength.
    """
    # Position expected weights
    expected = {
        "QB": 220, "RB": 213, "WR": 201, "TE": 250,
        "OL": 312, "DL": 290, "EDGE": 248, "LB": 236,
        "CB": 193, "S": 205,
    }
    pos = POSITION_MAPPING.get(position, "WR")
    exp_weight = expected.get(pos, 220)

    # Bonus/penalty based on weight vs expected
    diff = weight - exp_weight
    return int(diff * 0.15)  # +1.5 strength per 10 lbs over


# =============================================================================
# Contract Value Functions
# =============================================================================

def get_position_contract_tiers(position: str) -> dict:
    """Get contract tier values (in millions) for a position."""
    tiers = CONTRACT_MODEL.get("position_tiers_millions", {})

    # Map to contract positions
    pos_map = {
        "QB": "QB", "RB": "RB", "FB": "RB",
        "WR": "WR", "TE": "TE",
        "OT": "OT", "OG": "OG", "C": "C",
        "DE": "EDGE", "DT": "DL", "NT": "DL",
        "MLB": "LB", "ILB": "LB", "OLB": "LB",
        "CB": "CB", "FS": "S", "SS": "S",
        "K": "K", "P": "P",
    }
    mapped = pos_map.get(position, "WR")
    return tiers.get(mapped, tiers.get("WR", {}))


def calculate_contract_value(position: str, overall: int, age: int = 26) -> dict:
    """
    Calculate market contract value for a player.

    Args:
        position: Player position
        overall: Overall rating (40-99)
        age: Player age

    Returns:
        Dict with apy, years, guaranteed_pct
    """
    tiers = get_position_contract_tiers(position)

    # Map overall to tier
    if overall >= 95:
        tier = "top_1"
    elif overall >= 90:
        tier = "top_5"
    elif overall >= 85:
        tier = "top_10"
    elif overall >= 80:
        tier = "top_20"
    elif overall >= 75:
        tier = "average"
    elif overall >= 70:
        tier = "depth"
    else:
        tier = "minimum"

    base_apy = tiers.get(tier, 1.0)

    # Age adjustments
    # Peak value age is 26-28
    if age < 25:
        # Young player premium (potential)
        age_mod = 1.0
    elif age <= 28:
        # Peak years
        age_mod = 1.0
    elif age <= 30:
        # Start of decline
        age_mod = 0.85
    elif age <= 32:
        # Significant decline
        age_mod = 0.70
    else:
        # Veteran minimum territory
        age_mod = 0.50

    apy = base_apy * age_mod

    # Contract length by position and age
    base_years = {
        "QB": 4, "OL": 3.5, "WR": 3, "DL": 3, "EDGE": 3,
        "LB": 3, "CB": 3, "S": 3, "RB": 2.5, "TE": 2.5,
    }.get(POSITION_MAPPING.get(position, "WR"), 3)

    # Reduce years for older players
    if age >= 30:
        years = max(1, int(base_years - 1))
    elif age >= 28:
        years = int(base_years)
    else:
        years = int(base_years + 0.5)

    # Guaranteed percentage by tier
    gtd_by_tier = {
        "top_1": 0.60,
        "top_5": 0.50,
        "top_10": 0.40,
        "top_20": 0.30,
        "average": 0.25,
        "depth": 0.20,
        "minimum": 0.10,
    }
    gtd_pct = gtd_by_tier.get(tier, 0.25)

    return {
        "apy_millions": round(apy, 2),
        "years": years,
        "guaranteed_pct": gtd_pct,
        "total_millions": round(apy * years, 2),
        "guaranteed_millions": round(apy * years * gtd_pct, 2),
        "tier": tier,
    }


# =============================================================================
# Draft Value Functions
# =============================================================================

def get_pick_expected_value(pick_number: int) -> float:
    """
    Get expected career value for a draft pick.

    Uses: E[value] = exp(5.117 - 0.613 * ln(pick))
    """
    formula = DRAFT_MODEL.get("pick_value_formula", {})
    intercept = formula.get("intercept", 5.117)
    slope = formula.get("slope", -0.613)

    return math.exp(intercept + slope * math.log(pick_number))


def get_round_success_rates(round_num: int) -> dict:
    """Get success/bust rates for a draft round."""
    by_round = DRAFT_MODEL.get("by_round", {})
    return by_round.get(str(round_num), {
        "bust_rate": 0.30,
        "starter_rate": 0.30,
        "star_rate": 0.10,
        "elite_rate": 0.03,
    })


def generate_prospect_tier(pick_number: int) -> str:
    """
    Generate prospect tier based on pick number.

    Returns: "elite", "star", "starter", "rotation", "bust"
    """
    if pick_number <= 10:
        weights = [0.30, 0.40, 0.20, 0.08, 0.02]
    elif pick_number <= 32:
        weights = [0.10, 0.30, 0.35, 0.20, 0.05]
    elif pick_number <= 64:
        weights = [0.05, 0.15, 0.35, 0.30, 0.15]
    elif pick_number <= 128:
        weights = [0.02, 0.08, 0.25, 0.35, 0.30]
    else:
        weights = [0.01, 0.04, 0.15, 0.35, 0.45]

    tiers = ["elite", "star", "starter", "rotation", "bust"]
    return random.choices(tiers, weights=weights, k=1)[0]


def tier_to_overall_range(tier: str) -> tuple[int, int]:
    """Convert prospect tier to overall rating range."""
    ranges = {
        "elite": (88, 95),
        "star": (82, 89),
        "starter": (75, 83),
        "rotation": (68, 76),
        "bust": (58, 70),
    }
    return ranges.get(tier, (70, 80))


def tier_to_potential_range(tier: str) -> tuple[int, int]:
    """Convert prospect tier to potential rating range."""
    ranges = {
        "elite": (94, 99),
        "star": (88, 95),
        "starter": (80, 90),
        "rotation": (72, 82),
        "bust": (62, 74),
    }
    return ranges.get(tier, (75, 85))


def generate_prospect_ratings(pick_number: int) -> dict:
    """
    Generate prospect current/potential ratings based on pick.

    Returns:
        Dict with tier, current_overall, potential
    """
    tier = generate_prospect_tier(pick_number)

    current_range = tier_to_overall_range(tier)
    potential_range = tier_to_potential_range(tier)

    # Higher picks have higher means within range
    pick_factor = max(0.0, 1.0 - (pick_number / 256))

    current = int(
        current_range[0] + (current_range[1] - current_range[0]) * (0.3 + 0.7 * pick_factor)
        + random.gauss(0, 2)
    )
    current = max(current_range[0], min(current_range[1], current))

    potential = int(
        potential_range[0] + (potential_range[1] - potential_range[0]) * (0.3 + 0.7 * pick_factor)
        + random.gauss(0, 2)
    )
    potential = max(potential_range[0], min(potential_range[1], potential))

    # Ensure potential >= current
    potential = max(potential, current)

    return {
        "tier": tier,
        "current_overall": current,
        "potential": potential,
        "expected_value": get_pick_expected_value(pick_number),
    }


# =============================================================================
# Position Value Functions (WAR & Market Efficiency)
# =============================================================================

# Default multipliers if model not loaded
_DEFAULT_MULTIPLIERS = {
    "QB": 5.0, "DE": 2.5, "CB": 2.0, "WR": 2.2, "LT": 1.5, "RT": 1.5,
    "LG": 1.3, "RG": 1.3, "C": 1.2, "TE": 1.3, "DT": 1.6, "OLB": 1.5,
    "MLB": 1.0, "ILB": 1.0, "FS": 1.2, "SS": 1.1, "RB": 0.6, "FB": 0.4,
    "NT": 0.8, "K": 0.4, "P": 0.3, "LS": 0.2,
}


def get_position_multiplier(position: str) -> float:
    """
    Get position value multiplier for roster/contract decisions.

    Higher = more valuable position (invest in draft/development).
    Lower = less valuable (avoid big contracts, find cheap replacements).

    Based on WAR analysis and market efficiency research.
    """
    hints = POSITION_VALUE_MODEL.get("implementation_hints", {})
    multipliers = hints.get("recommended_multipliers", _DEFAULT_MULTIPLIERS)
    return multipliers.get(position, 1.0)


def get_position_war(position: str) -> dict:
    """
    Get WAR (Wins Above Replacement) estimates for a position.

    Returns:
        Dict with elite_war, median_war, war_range, market_efficiency
    """
    war_data = POSITION_VALUE_MODEL.get("pff_war_estimates", {})
    positions = war_data.get("positions", {})
    return positions.get(position, {
        "elite_war": 0.5,
        "median_war": 0.2,
        "war_range": 0.6,
        "market_efficiency": 0.2,
    })


def get_position_win_contribution(position: str) -> dict:
    """
    Get win contribution data for a position group.

    Positive win_correlation = investing more correlates with wins.
    Negative = overspending hurts (market inefficiency).

    Returns:
        Dict with win_correlation, avg_cap_share_pct, high_vs_low_win_diff
    """
    win_data = POSITION_VALUE_MODEL.get("win_contribution", {})
    by_group = win_data.get("by_position_group", {})

    # Map specific positions to groups
    pos_to_group = {
        "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
        "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
        "DE": "DL", "DT": "DL", "NT": "DL", "EDGE": "DL",
        "MLB": "LB", "ILB": "LB", "OLB": "LB",
        "CB": "CB", "FS": "S", "SS": "S",
        "K": "K", "P": "P", "LS": "LS",
    }
    group = pos_to_group.get(position, position)

    return by_group.get(group, {
        "win_correlation": 0.0,
        "avg_cap_share_pct": 5.0,
        "high_vs_low_win_diff": 0.0,
    })


def is_market_inefficient(position: str) -> bool:
    """
    Check if a position is market inefficient (overpaid relative to value).

    True = avoid big FA contracts, draft/develop instead.
    """
    war = get_position_war(position)
    return war.get("market_efficiency", 0.2) < 0.15


def get_replacement_level_cost(position: str) -> int:
    """
    Get replacement-level salary (in thousands) for a position.

    This is roughly the 10th percentile salary - league minimum territory.
    """
    replacement = POSITION_VALUE_MODEL.get("replacement_value", {})
    by_position = replacement.get("by_position", {})
    pos_data = by_position.get(position, {})
    return int(pos_data.get("replacement_salary_k", 0))


def get_elite_salary(position: str) -> int:
    """
    Get elite salary (in thousands) for a position.

    This is roughly the 90th percentile - top of market.
    """
    replacement = POSITION_VALUE_MODEL.get("replacement_value", {})
    by_position = replacement.get("by_position", {})
    pos_data = by_position.get(position, {})
    return int(pos_data.get("elite_salary_k", 10) * 1000)  # Convert to thousands
