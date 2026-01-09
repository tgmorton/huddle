"""
Player Development Curves

Auto-generated from NFL data analysis.
Provides age-based performance curves for player potential and regression.

Usage:
    from huddle.core.ai.development_curves import (
        get_position_group,
        get_peak_age,
        get_prime_years,
        get_growth_rate,
        get_decline_rate,
        get_regression_factor,
        project_performance,
        get_potential_tier,
        apply_offseason_development,
    )
"""

from typing import Dict, List, Tuple, Optional


# =============================================================================
# Position Group Mapping
# =============================================================================
# Maps specific positions to development curve groups

POSITION_TO_GROUP = {
    # Quarterback
    'QB': 'QB',
    # Running backs
    'RB': 'RB',
    'FB': 'RB',
    # Receivers
    'WR': 'WR',
    'TE': 'TE',
    # Offensive line (all use same curve)
    'LT': 'OL',
    'LG': 'OL',
    'C': 'OL',
    'RG': 'OL',
    'RT': 'OL',
    'OL': 'OL',
    'OT': 'OL',
    'OG': 'OL',
    # Defensive line
    'DE': 'EDGE',
    'DT': 'DL',
    'NT': 'DL',
    'DL': 'DL',
    # Linebackers
    'OLB': 'EDGE',  # Pass rushers use EDGE curve
    'ILB': 'LB',
    'MLB': 'LB',
    'LB': 'LB',
    # Secondary
    'CB': 'CB',
    'FS': 'S',
    'SS': 'S',
    'S': 'S',
    'DB': 'CB',
    # Special teams (use QB curve - long careers, slow decline)
    'K': 'QB',
    'P': 'QB',
}


def get_position_group(position: str) -> str:
    """
    Map a specific position to its development curve group.

    Args:
        position: Specific position like 'LT', 'CB', 'OLB'

    Returns:
        Position group for development curves like 'OL', 'CB', 'EDGE'
    """
    return POSITION_TO_GROUP.get(position, 'LB')  # Default to LB (medium curves)


# =============================================================================
# Peak Ages and Prime Years
# =============================================================================
# Data-derived with literature-informed corrections for survivorship bias
# Sources: Our analysis + Mulholland/Jensen, established aging curves

PEAK_AGES = {
    # Offense
    'QB': 29,    # Data: 28, Literature: 28-32, longer careers
    'RB': 26,    # Data: 28 (survivorship), Literature: 25-26, early peak
    'WR': 27,    # Data: 33 (survivorship), Literature: 26-28
    'TE': 28,    # Data: 32 (survivorship), Literature: 27-29
    'OL': 28,    # Insufficient data, Literature: 27-29
    # Defense
    'CB': 27,    # Data: 31 (survivorship), Literature: 26-28, speed position
    'S': 28,     # Data: 29, reasonable
    'LB': 27,    # Data: 27, matches well
    'EDGE': 27,  # Data: 32 (survivorship), Literature: 26-28
    'DL': 28,    # Data: 33 (survivorship), Literature: 27-29
}

PRIME_YEARS = {
    # Offense (years within 90% of peak)
    'QB': (27, 33),   # Long prime window
    'RB': (24, 28),   # Short prime, early peak
    'WR': (25, 30),   # Medium prime
    'TE': (26, 31),   # Medium-long prime
    'OL': (26, 32),   # Long prime
    # Defense
    'CB': (25, 29),   # Speed-dependent, shorter prime
    'S': (26, 30),    # Medium prime
    'LB': (25, 30),   # Medium prime
    'EDGE': (25, 30), # Medium prime
    'DL': (26, 31),   # Medium-long prime
}


# =============================================================================
# Growth and Decline Rates (% of peak per year)
# =============================================================================
# Adjusted for realism - decline rates were often 0 due to survivorship

GROWTH_RATES = {
    # Offense - how fast they develop toward peak
    'QB': 8.0,    # Slow development, need experience
    'RB': 15.0,   # Fast development, physical maturity early
    'WR': 12.0,   # Medium, route running takes time
    'TE': 10.0,   # Medium, blocking + receiving skills
    'OL': 8.0,    # Slow, technique-heavy
    # Defense
    'CB': 12.0,   # Fast, physical prime matters
    'S': 10.0,    # Medium
    'LB': 12.0,   # Fast, physical position
    'EDGE': 10.0, # Medium, technique + athleticism
    'DL': 8.0,    # Slow, technique-heavy
}

DECLINE_RATES = {
    # Offense - how fast they decline after peak
    'QB': 4.0,    # Slow decline, experience compensates
    'RB': 12.0,   # Fast decline, contact + speed loss
    'WR': 6.0,    # Medium, speed loss matters
    'TE': 5.0,    # Slow-medium, less speed-dependent
    'OL': 4.0,    # Slow, technique compensates
    # Defense
    'CB': 10.0,   # Fast decline, speed-critical
    'S': 6.0,     # Medium decline
    'LB': 7.0,    # Medium decline
    'EDGE': 8.0,  # Medium-fast, explosiveness matters
    'DL': 5.0,    # Slow-medium, power > speed
}


# =============================================================================
# Decline Schedules (% of peak remaining by years past peak)
# =============================================================================
# Generated from DECLINE_RATES: remaining = 100 * (1 - rate/100)^years

def _generate_decline_schedule(rate: float, years: int = 8) -> dict:
    """Generate decline schedule from annual rate."""
    return {y: round(100 * ((1 - rate/100) ** y), 1) for y in range(1, years + 1)}

DECLINE_SCHEDULES = {
    # Offense
    'QB': _generate_decline_schedule(4.0),     # 96, 92, 88, 85, 82, 78, 75, 72
    'RB': _generate_decline_schedule(12.0),    # 88, 77, 68, 60, 53, 46, 41, 36
    'WR': _generate_decline_schedule(6.0),     # 94, 88, 83, 78, 73, 69, 65, 61
    'TE': _generate_decline_schedule(5.0),     # 95, 90, 86, 81, 77, 74, 70, 66
    'OL': _generate_decline_schedule(4.0),     # 96, 92, 88, 85, 82, 78, 75, 72
    # Defense
    'CB': _generate_decline_schedule(10.0),    # 90, 81, 73, 66, 59, 53, 48, 43
    'S': _generate_decline_schedule(6.0),      # 94, 88, 83, 78, 73, 69, 65, 61
    'LB': _generate_decline_schedule(7.0),     # 93, 86, 80, 75, 70, 65, 60, 56
    'EDGE': _generate_decline_schedule(8.0),   # 92, 85, 78, 72, 66, 61, 56, 51
    'DL': _generate_decline_schedule(5.0),     # 95, 90, 86, 81, 77, 74, 70, 66
}


# =============================================================================
# API Functions
# =============================================================================

def get_peak_age(position: str) -> int:
    """Get the typical peak age for a position."""
    group = get_position_group(position)
    return PEAK_AGES.get(group, 27)


def get_prime_years(position: str) -> Tuple[int, int]:
    """Get the prime years range for a position."""
    group = get_position_group(position)
    return PRIME_YEARS.get(group, (26, 28))


def get_growth_rate(position: str) -> float:
    """Get annual growth rate (% of peak) during development phase."""
    group = get_position_group(position)
    return GROWTH_RATES.get(group, 10.0)


def get_decline_rate(position: str) -> float:
    """Get annual decline rate (% of peak) after prime years."""
    group = get_position_group(position)
    return DECLINE_RATES.get(group, 6.0)


def get_years_to_peak(position: str, current_age: int) -> int:
    """Get years until peak age for a position."""
    peak = get_peak_age(position)
    return max(0, peak - current_age)


def get_years_past_peak(position: str, current_age: int) -> int:
    """Get years past peak age for a position."""
    peak = get_peak_age(position)
    return max(0, current_age - peak)


def is_in_prime(position: str, age: int) -> bool:
    """Check if player is in their prime years."""
    prime_start, prime_end = get_prime_years(position)
    return prime_start <= age <= prime_end


def project_performance(
    position: str,
    current_age: int,
    current_rating: float,
    target_age: int
) -> float:
    """
    Project a player's performance at a future age.

    Args:
        position: Specific position (e.g., 'LT', 'CB') or position group
        current_age: Current age
        current_rating: Current overall rating (0-100 scale)
        target_age: Age to project to

    Returns:
        Projected rating at target age
    """
    group = get_position_group(position)
    peak_age = PEAK_AGES.get(group, 27)

    if target_age == current_age:
        return current_rating

    growth_rate = GROWTH_RATES.get(group, 10.0) / 100
    decline_rate = DECLINE_RATES.get(group, 6.0) / 100

    # If moving toward peak, apply growth
    if current_age < peak_age and target_age <= peak_age:
        years = target_age - current_age
        return current_rating * (1 + growth_rate) ** years

    # If moving past peak, apply decline
    if current_age >= peak_age or target_age > peak_age:
        # First, grow to peak if needed
        if current_age < peak_age:
            years_to_peak = peak_age - current_age
            peak_rating = current_rating * (1 + growth_rate) ** years_to_peak
            years_decline = target_age - peak_age
        else:
            peak_rating = current_rating
            years_decline = target_age - current_age

        # Then apply decline
        return peak_rating * (1 - decline_rate) ** years_decline

    return current_rating


def get_potential_tier(
    position: str,
    age: int,
    current_rating: float,
    league_avg_rating: float = 70.0
) -> str:
    """
    Estimate a young player's potential tier based on current performance.

    Args:
        position: Position group
        age: Current age
        current_rating: Current overall rating
        league_avg_rating: Average rating in the league

    Returns:
        Potential tier: 'elite', 'star', 'starter', 'backup', or 'depth'
    """
    # Only applies to young players
    if age > 26:
        return 'established'

    # Project to peak
    projected_peak = project_performance(position, age, current_rating, get_peak_age(position))

    # Compare to thresholds (relative to league average)
    if projected_peak >= league_avg_rating * 1.3:
        return 'elite'
    elif projected_peak >= league_avg_rating * 1.15:
        return 'star'
    elif projected_peak >= league_avg_rating:
        return 'starter'
    elif projected_peak >= league_avg_rating * 0.85:
        return 'backup'
    else:
        return 'depth'


def get_regression_factor(position: str, age: int) -> float:
    """
    Get the expected performance multiplier for a player's age.

    Returns a value between 0 and 1 indicating expected performance
    relative to peak. Use to apply age-based regression.

    Args:
        position: Specific position (e.g., 'LT', 'CB') or position group
        age: Current age

    Returns:
        Multiplier (1.0 = peak performance)
    """
    group = get_position_group(position)
    peak_age = PEAK_AGES.get(group, 27)

    if age < peak_age:
        # Pre-peak: growing toward 1.0
        years_to_peak = peak_age - age
        growth_rate = GROWTH_RATES.get(group, 10.0) / 100
        # Work backwards: current = peak / (1 + growth)^years
        return 1.0 / ((1 + growth_rate) ** years_to_peak)
    else:
        # Post-peak: declining from 1.0
        years_past_peak = age - peak_age

        # Use schedule if available
        schedule = DECLINE_SCHEDULES.get(group, {})
        if years_past_peak in schedule:
            return schedule[years_past_peak] / 100

        # Otherwise use rate
        decline_rate = DECLINE_RATES.get(group, 6.0) / 100
        return (1 - decline_rate) ** years_past_peak


def apply_offseason_development(
    player,
    season: int,
    variance: float = 0.03,
) -> dict:
    """
    Apply one year of development to a player and return history snapshot.

    This function:
    1. Records a "before" snapshot of the player
    2. Ages the player by 1 year
    3. Applies growth (pre-peak) or decline (post-peak) to attributes
    4. Uses growth categories for differentiated development rates
    5. Returns a development history entry

    Growth/Decline by category:
    - PHYSICAL (speed, strength): Low growth (0.5x), fast decline (1.5x)
    - MENTAL (awareness, vision): High growth (1.5x), slow decline (0.5x)
    - TECHNIQUE (throwing, blocking): Normal growth (1.0x), normal decline (1.0x)
    - SPECIAL (kicking, toughness): Low growth (0.7x), slow decline (0.7x)

    Args:
        player: Player object with age, position, attributes
        season: The season this development applies to
        variance: Random variance in development (default 3%)

    Returns:
        Development history entry with before/after snapshots
    """
    import random
    from huddle.core.attributes import AttributeRegistry
    from huddle.core.attributes.growth_profiles import (
        ATTRIBUTE_GROWTH_CATEGORIES,
        GrowthCategory,
    )

    position = player.position.value
    group = get_position_group(position)
    peak_age = PEAK_AGES.get(group, 27)
    prime_start, prime_end = PRIME_YEARS.get(group, (26, 28))

    # Category multipliers for growth and decline
    CATEGORY_GROWTH_MULTIPLIERS = {
        GrowthCategory.PHYSICAL: 0.5,   # Genetics-limited, hard to improve
        GrowthCategory.MENTAL: 1.5,     # Highly trainable
        GrowthCategory.TECHNIQUE: 1.0,  # Normal training
        GrowthCategory.SPECIAL: 0.7,    # Moderate
    }
    CATEGORY_DECLINE_MULTIPLIERS = {
        GrowthCategory.PHYSICAL: 1.5,   # Speed/athleticism goes first
        GrowthCategory.MENTAL: 0.5,     # Experience compensates
        GrowthCategory.TECHNIQUE: 1.0,  # Normal decline
        GrowthCategory.SPECIAL: 0.7,    # Moderate
    }

    # Record before state
    age_before = player.age
    overall_before = player.overall

    # Get player's learning attribute (affects development speed)
    # learning=50 is baseline (1.0x), learning=75 is 1.5x, learning=25 is 0.5x
    learning = player.attributes.get("learning", 50)
    learning_multiplier = learning / 50.0

    # Increment age
    player.age += 1
    player.experience_years = getattr(player, 'experience_years', 0) + 1
    age_after = player.age

    # Determine development phase
    if age_after < prime_start:
        phase = "growth"
        base_rate = GROWTH_RATES.get(group, 10.0) / 100
        direction = 1  # Positive growth
    elif age_after <= prime_end:
        phase = "prime"
        base_rate = 0.02  # Small random changes in prime
        direction = random.choice([-1, 0, 0, 1])  # Mostly stable
    else:
        phase = "decline"
        base_rate = DECLINE_RATES.get(group, 6.0) / 100
        direction = -1  # Negative decline

    # Get relevant attributes for this position
    relevant_attrs = AttributeRegistry.get_for_position(position)

    # Apply development to each relevant attribute
    for attr_def in relevant_attrs:
        attr_name = attr_def.name
        current_value = player.attributes.get(attr_name, 50)

        # Get growth category for this attribute
        growth_category = ATTRIBUTE_GROWTH_CATEGORIES.get(attr_name, GrowthCategory.TECHNIQUE)

        # Apply category-specific multiplier
        if phase == "growth":
            category_mult = CATEGORY_GROWTH_MULTIPLIERS.get(growth_category, 1.0)
        elif phase == "decline":
            category_mult = CATEGORY_DECLINE_MULTIPLIERS.get(growth_category, 1.0)
        else:
            category_mult = 1.0  # Prime phase - equal chance for all

        # Apply variance to the rate
        # Learning attribute affects growth (high learning = faster development)
        # but doesn't affect decline (can't learn your way out of aging)
        if phase == "growth":
            actual_rate = base_rate * category_mult * learning_multiplier * (1 + random.uniform(-variance, variance))
        else:
            actual_rate = base_rate * category_mult * (1 + random.uniform(-variance, variance))

        # Calculate change
        change = current_value * actual_rate * direction

        # For growth, respect potential ceiling if set
        if direction > 0:
            potential = player.attributes.get_potential(attr_name)
            if potential is not None:
                max_change = potential - current_value
                change = min(change, max_change)

        # Apply change
        new_value = current_value + change
        new_value = max(1, min(99, int(new_value)))

        player.attributes.set(attr_name, new_value)

    # Record after state
    overall_after = player.overall

    return {
        "season": season,
        "age_before": age_before,
        "age_after": age_after,
        "overall_before": overall_before,
        "overall_after": overall_after,
        "phase": phase,
        "change": overall_after - overall_before,
    }
