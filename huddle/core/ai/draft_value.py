"""
Draft Value System

Provides data-driven models for draft prospect generation with realistic
uncertainty and variance.

Usage:
    from huddle.core.ai.draft_value import (
        get_pick_value,
        get_hit_rates,
        generate_prospect_outcome,
        get_scouting_error,
        get_development_speed,
    )

Based on analysis of 2015-2021 NFL drafts with 2019-2024 performance data.
"""

import random
from typing import Dict, List, Optional, Tuple


# =============================================================================
# Pick Value Curve
# =============================================================================
# Expected career value by draft pick (normalized to pick 1 = 100)

PICK_VALUE_CURVE = {
    # Per-pick values for top 32 (relative to pick 1)
    1: 100.0, 2: 95.0, 3: 90.0, 4: 85.0, 5: 80.0,
    6: 76.0, 7: 73.0, 8: 70.0, 9: 67.0, 10: 64.0,
    11: 55.0, 12: 53.0, 13: 51.0, 14: 49.0, 15: 47.0,
    16: 42.0, 17: 41.0, 18: 40.0, 19: 39.0, 20: 38.0,
    21: 46.0, 22: 45.0, 23: 44.0, 24: 43.0, 25: 42.0,
    26: 41.0, 27: 40.0, 28: 39.0, 29: 38.0, 30: 37.0,
    31: 36.0, 32: 35.0,
}

# Bucket-based values for later rounds (mean value relative to pick 1)
PICK_VALUE_BUCKETS = {
    'round_2': 45.3,   # Picks 33-64
    'round_3': 33.8,   # Picks 65-100
    'round_4': 25.6,   # Picks 101-135
    'round_5': 20.0,   # Picks 136-176
    'round_6': 15.4,   # Picks 177-220
    'round_7': 10.0,   # Picks 221-256
}


# =============================================================================
# Hit Rates by Round and Position
# =============================================================================
# What % of picks become starters, stars, or busts by round and position

HIT_RATES = {
    # Round 1: High hit rates, position matters
    1: {
        'QB':   {'starter': 0.91, 'star': 0.30, 'bust': 0.04},
        'RB':   {'starter': 1.00, 'star': 0.50, 'bust': 0.00},
        'WR':   {'starter': 0.73, 'star': 0.35, 'bust': 0.04},
        'TE':   {'starter': 1.00, 'star': 0.57, 'bust': 0.00},
        'OL':   {'starter': 0.60, 'star': 0.20, 'bust': 0.20},
        'CB':   {'starter': 0.63, 'star': 0.30, 'bust': 0.07},
        'S':    {'starter': 0.88, 'star': 0.25, 'bust': 0.00},
        'LB':   {'starter': 0.78, 'star': 0.28, 'bust': 0.11},
        'EDGE': {'starter': 0.90, 'star': 0.38, 'bust': 0.00},
        'DL':   {'starter': 0.83, 'star': 0.50, 'bust': 0.04},
    },
    # Round 2: Good value, lower star rates
    2: {
        'QB':   {'starter': 0.50, 'star': 0.17, 'bust': 0.17},
        'RB':   {'starter': 0.79, 'star': 0.29, 'bust': 0.07},
        'WR':   {'starter': 0.78, 'star': 0.22, 'bust': 0.11},
        'TE':   {'starter': 0.75, 'star': 0.25, 'bust': 0.08},
        'OL':   {'starter': 0.75, 'star': 0.20, 'bust': 0.10},
        'CB':   {'starter': 0.68, 'star': 0.20, 'bust': 0.12},
        'S':    {'starter': 0.71, 'star': 0.21, 'bust': 0.14},
        'LB':   {'starter': 0.67, 'star': 0.22, 'bust': 0.17},
        'EDGE': {'starter': 0.65, 'star': 0.25, 'bust': 0.10},
        'DL':   {'starter': 0.70, 'star': 0.25, 'bust': 0.15},
    },
    # Round 3: Declining value, position differences emerge
    3: {
        'QB':   {'starter': 0.43, 'star': 0.00, 'bust': 0.43},  # Don't draft QBs here
        'RB':   {'starter': 0.68, 'star': 0.18, 'bust': 0.05},
        'WR':   {'starter': 0.71, 'star': 0.29, 'bust': 0.00},
        'TE':   {'starter': 0.47, 'star': 0.11, 'bust': 0.42},
        'OL':   {'starter': 0.65, 'star': 0.15, 'bust': 0.15},
        'CB':   {'starter': 0.67, 'star': 0.22, 'bust': 0.15},
        'S':    {'starter': 0.59, 'star': 0.18, 'bust': 0.18},
        'LB':   {'starter': 0.70, 'star': 0.30, 'bust': 0.13},  # LBs good value here
        'EDGE': {'starter': 0.33, 'star': 0.12, 'bust': 0.21},
        'DL':   {'starter': 0.72, 'star': 0.21, 'bust': 0.21},
    },
    # Rounds 4-5: Low-probability starters
    4: {
        'QB':   {'starter': 0.25, 'star': 0.08, 'bust': 0.50},
        'RB':   {'starter': 0.50, 'star': 0.10, 'bust': 0.20},
        'WR':   {'starter': 0.45, 'star': 0.10, 'bust': 0.25},
        'TE':   {'starter': 0.35, 'star': 0.05, 'bust': 0.40},
        'OL':   {'starter': 0.45, 'star': 0.08, 'bust': 0.25},
        'CB':   {'starter': 0.40, 'star': 0.08, 'bust': 0.30},
        'S':    {'starter': 0.42, 'star': 0.08, 'bust': 0.30},
        'LB':   {'starter': 0.45, 'star': 0.10, 'bust': 0.25},
        'EDGE': {'starter': 0.30, 'star': 0.05, 'bust': 0.35},
        'DL':   {'starter': 0.45, 'star': 0.10, 'bust': 0.25},
    },
    # Rounds 5-7: Mostly depth, occasional gem
    5: {
        'default': {'starter': 0.25, 'star': 0.03, 'bust': 0.50},
    },
    6: {
        'default': {'starter': 0.15, 'star': 0.02, 'bust': 0.60},
    },
    7: {
        'default': {'starter': 0.10, 'star': 0.01, 'bust': 0.70},
    },
}


# =============================================================================
# Position Variance
# =============================================================================
# Coefficient of variation by position - higher = more boom/bust

POSITION_VARIANCE = {
    # High variance (CV > 1.0) - more upside and downside
    'QB':   {'cv': 1.15, 'tier': 'high', 'boom_mult': 1.4, 'bust_mult': 1.3},
    'RB':   {'cv': 1.12, 'tier': 'high', 'boom_mult': 1.3, 'bust_mult': 1.2},
    'TE':   {'cv': 1.11, 'tier': 'high', 'boom_mult': 1.3, 'bust_mult': 1.3},
    'WR':   {'cv': 1.10, 'tier': 'high', 'boom_mult': 1.3, 'bust_mult': 1.2},

    # Medium variance (CV 0.9-1.0) - more predictable
    'DL':   {'cv': 0.98, 'tier': 'medium', 'boom_mult': 1.1, 'bust_mult': 1.1},
    'LB':   {'cv': 0.98, 'tier': 'medium', 'boom_mult': 1.1, 'bust_mult': 1.1},
    'EDGE': {'cv': 0.94, 'tier': 'medium', 'boom_mult': 1.1, 'bust_mult': 1.1},
    'CB':   {'cv': 0.93, 'tier': 'medium', 'boom_mult': 1.0, 'bust_mult': 1.0},

    # Low variance (CV < 0.9) - safest picks
    'S':    {'cv': 0.82, 'tier': 'low', 'boom_mult': 0.9, 'bust_mult': 0.9},
    'OL':   {'cv': 0.85, 'tier': 'low', 'boom_mult': 0.9, 'bust_mult': 0.9},
}


# =============================================================================
# Scouting Error
# =============================================================================
# How much true talent can differ from scouted grade

SCOUTING_ERROR = {
    # Hardest to scout (std ~1.0-1.2)
    'QB':   {'mean': 0.20, 'std': 1.10, 'range': (-1.0, 2.0)},
    'WR':   {'mean': 0.54, 'std': 1.17, 'range': (-0.8, 2.2)},
    'RB':   {'mean': 0.44, 'std': 1.04, 'range': (-0.9, 1.8)},
    'TE':   {'mean': 0.36, 'std': 1.10, 'range': (-0.9, 1.9)},

    # Easier to scout (std ~0.6-0.8)
    'CB':   {'mean': -0.25, 'std': 0.79, 'range': (-0.9, 0.9)},
    'S':    {'mean': -0.05, 'std': 0.80, 'range': (-0.9, 1.2)},
    'LB':   {'mean': -0.15, 'std': 0.78, 'range': (-0.9, 0.8)},
    'EDGE': {'mean': -0.11, 'std': 0.83, 'range': (-0.9, 1.0)},
    'DL':   {'mean': -0.38, 'std': 0.62, 'range': (-0.9, 0.4)},
    'OL':   {'mean': 0.00, 'std': 0.75, 'range': (-0.8, 0.8)},
}


# =============================================================================
# Development Speed
# =============================================================================
# How quickly players reach their peak

DEVELOPMENT_SPEED = {
    # Fast developers (peak year ~3.0-3.5)
    'RB':   {'speed': 'fast', 'mean_peak_year': 3.4, 'early_rate': 0.35},
    'WR':   {'speed': 'fast', 'mean_peak_year': 3.3, 'early_rate': 0.30},

    # Normal developers (peak year ~3.5-4.0)
    'QB':   {'speed': 'normal', 'mean_peak_year': 4.0, 'early_rate': 0.20},
    'CB':   {'speed': 'normal', 'mean_peak_year': 3.6, 'early_rate': 0.25},
    'TE':   {'speed': 'normal', 'mean_peak_year': 3.8, 'early_rate': 0.22},
    'S':    {'speed': 'normal', 'mean_peak_year': 3.8, 'early_rate': 0.23},
    'EDGE': {'speed': 'normal', 'mean_peak_year': 3.8, 'early_rate': 0.24},
    'LB':   {'speed': 'normal', 'mean_peak_year': 3.9, 'early_rate': 0.21},

    # Slow developers (peak year > 4.0)
    'OL':   {'speed': 'slow', 'mean_peak_year': 4.3, 'early_rate': 0.15},
    'DL':   {'speed': 'slow', 'mean_peak_year': 4.4, 'early_rate': 0.14},
}


# =============================================================================
# API Functions
# =============================================================================

def get_pick_value(pick: int) -> float:
    """
    Get expected value for a draft pick (relative to pick 1 = 100).

    Args:
        pick: Overall draft pick (1-256)

    Returns:
        Expected value (0-100 scale, pick 1 = 100)
    """
    if pick <= 32:
        return PICK_VALUE_CURVE.get(pick, 35.0)

    # Use bucket values for later rounds
    if pick <= 64:
        return PICK_VALUE_BUCKETS['round_2']
    elif pick <= 100:
        return PICK_VALUE_BUCKETS['round_3']
    elif pick <= 135:
        return PICK_VALUE_BUCKETS['round_4']
    elif pick <= 176:
        return PICK_VALUE_BUCKETS['round_5']
    elif pick <= 220:
        return PICK_VALUE_BUCKETS['round_6']
    else:
        return PICK_VALUE_BUCKETS['round_7']


def get_round(pick: int) -> int:
    """Convert overall pick to round number."""
    if pick <= 32:
        return 1
    elif pick <= 64:
        return 2
    elif pick <= 100:
        return 3
    elif pick <= 135:
        return 4
    elif pick <= 176:
        return 5
    elif pick <= 220:
        return 6
    else:
        return 7


def get_hit_rates(position: str, round_num: int) -> Dict[str, float]:
    """
    Get hit rates for a position at a given round.

    Args:
        position: Position group (QB, RB, WR, etc.)
        round_num: Draft round (1-7)

    Returns:
        Dict with 'starter', 'star', 'bust' probabilities
    """
    round_num = min(max(1, round_num), 7)
    round_data = HIT_RATES.get(round_num, {})

    if position in round_data:
        return round_data[position]
    elif 'default' in round_data:
        return round_data['default']
    else:
        # Fallback for unknown positions
        return {'starter': 0.50, 'star': 0.15, 'bust': 0.20}


def get_position_variance(position: str) -> Dict:
    """
    Get variance characteristics for a position.

    Returns:
        Dict with cv, tier, boom_mult, bust_mult
    """
    return POSITION_VARIANCE.get(position, {
        'cv': 1.0, 'tier': 'medium', 'boom_mult': 1.0, 'bust_mult': 1.0
    })


def get_scouting_error(position: str) -> Dict:
    """
    Get scouting error parameters for a position.

    Use to generate hidden talent that differs from scouted grade.

    Returns:
        Dict with mean, std, range for error distribution
    """
    return SCOUTING_ERROR.get(position, {
        'mean': 0.0, 'std': 0.80, 'range': (-0.9, 1.0)
    })


def get_development_speed(position: str) -> Dict:
    """
    Get development speed for a position.

    Returns:
        Dict with speed ('fast', 'normal', 'slow'),
        mean_peak_year, and early_rate
    """
    return DEVELOPMENT_SPEED.get(position, {
        'speed': 'normal', 'mean_peak_year': 3.8, 'early_rate': 0.20
    })


def generate_prospect_outcome(
    position: str,
    pick: int,
    scouted_grade: float = 70.0,
    random_seed: Optional[int] = None
) -> Dict:
    """
    Generate a realistic prospect outcome with hidden talent.

    This is the main function for prospect generation. It takes a scouted
    grade (what scouts see) and generates hidden attributes like true
    potential, development speed, and actual career outcome.

    Args:
        position: Position group
        pick: Overall draft pick
        scouted_grade: The visible scouted grade (0-100 scale)
        random_seed: Optional seed for reproducibility

    Returns:
        Dict with:
            - scouted_grade: What scouts see
            - true_potential: Hidden actual ceiling
            - development_speed: 'fast', 'normal', or 'slow'
            - expected_outcome: 'bust', 'depth', 'starter', or 'star'
            - boom_probability: Chance to exceed projections
            - bust_probability: Chance to underperform badly
    """
    if random_seed is not None:
        random.seed(random_seed)

    round_num = get_round(pick)
    hit_rates = get_hit_rates(position, round_num)
    variance = get_position_variance(position)
    scout_error = get_scouting_error(position)
    dev_speed = get_development_speed(position)

    # Generate true potential from scouted grade + error
    # Error is relative to scouted grade
    error = random.gauss(scout_error['mean'], scout_error['std'])
    error = max(scout_error['range'][0], min(scout_error['range'][1], error))

    # Apply error as multiplier (e.g., +0.2 means 20% better than scouted)
    true_potential = scouted_grade * (1 + error * 0.1)  # Scale down effect
    true_potential = max(40, min(99, true_potential))

    # Determine outcome based on hit rates
    roll = random.random()
    if roll < hit_rates['bust']:
        outcome = 'bust'
    elif roll < hit_rates['bust'] + (1 - hit_rates['starter']):
        outcome = 'depth'
    elif roll < 1 - hit_rates['star']:
        outcome = 'starter'
    else:
        outcome = 'star'

    # Adjust development speed based on position tendency
    dev_roll = random.random()
    if dev_roll < dev_speed['early_rate']:
        speed = 'fast'
    elif dev_roll < 0.80:
        speed = 'normal'
    else:
        speed = 'slow'

    # Calculate boom/bust probabilities based on variance
    base_boom = 0.10 * variance['boom_mult']
    base_bust = hit_rates['bust'] * variance['bust_mult']

    # Adjust based on scouted grade
    grade_factor = (scouted_grade - 70) / 30  # -1 to +1 around average
    boom_prob = max(0.02, min(0.30, base_boom + grade_factor * 0.05))
    bust_prob = max(0.05, min(0.50, base_bust - grade_factor * 0.05))

    return {
        'scouted_grade': round(scouted_grade, 1),
        'true_potential': round(true_potential, 1),
        'development_speed': speed,
        'expected_outcome': outcome,
        'boom_probability': round(boom_prob, 3),
        'bust_probability': round(bust_prob, 3),
        'pick_value': round(get_pick_value(pick), 1),
    }


def should_draft_position(position: str, round_num: int) -> Tuple[bool, str]:
    """
    Advise whether a position is good value at a given round.

    Args:
        position: Position group
        round_num: Draft round

    Returns:
        (is_good_value, reason)
    """
    hit_rates = get_hit_rates(position, round_num)
    variance = get_position_variance(position)

    # Bad value: high bust rate, low star rate
    if hit_rates['bust'] > 0.35:
        return False, f"High bust rate ({hit_rates['bust']:.0%})"

    # QB special case: avoid after round 2
    if position == 'QB' and round_num >= 3:
        return False, "QBs after round 2 have 0% star rate"

    # Good value: high starter rate, reasonable star upside
    if hit_rates['starter'] >= 0.65 and hit_rates['star'] >= 0.15:
        return True, f"Good hit rates (starter: {hit_rates['starter']:.0%})"

    # Position-specific value
    if position in ['LB', 'RB', 'WR'] and round_num == 3:
        return True, f"Good mid-round value for {position}"

    if position in ['OL', 'DL', 'S'] and variance['tier'] == 'low':
        return True, f"Low variance = safe pick"

    # Default: marginal value
    if hit_rates['starter'] >= 0.40:
        return True, "Reasonable upside"

    return False, "Low hit rates"


# =============================================================================
# Utility Functions
# =============================================================================

def get_draft_grade_range(pick: int) -> Tuple[float, float]:
    """
    Get typical scouted grade range for a draft pick.

    Higher picks have higher grades (that's why they're picked higher).

    Args:
        pick: Overall draft pick

    Returns:
        (min_grade, max_grade) tuple
    """
    round_num = get_round(pick)

    # Grade ranges by round
    ranges = {
        1: (75, 95),   # Elite prospects
        2: (68, 82),   # Very good prospects
        3: (62, 75),   # Good prospects
        4: (55, 70),   # Solid prospects
        5: (50, 65),   # Day 3 upside
        6: (45, 60),   # Projects
        7: (40, 55),   # Lottery tickets
    }

    return ranges.get(round_num, (40, 55))


def generate_draft_class(
    positions: List[str],
    num_prospects: int = 250,
    random_seed: Optional[int] = None
) -> List[Dict]:
    """
    Generate a full draft class of prospects.

    Args:
        positions: List of positions to include
        num_prospects: Total number of prospects
        random_seed: Optional seed

    Returns:
        List of prospect dicts sorted by scouted grade
    """
    if random_seed is not None:
        random.seed(random_seed)

    prospects = []

    for i in range(num_prospects):
        # Distribute positions roughly evenly
        position = positions[i % len(positions)]

        # Assign pick (for simulation - actual pick determined by grade)
        simulated_pick = i + 1
        round_num = get_round(simulated_pick)

        # Generate grade appropriate for pick range
        min_grade, max_grade = get_draft_grade_range(simulated_pick)
        scouted_grade = random.uniform(min_grade, max_grade)

        # Generate full prospect outcome
        outcome = generate_prospect_outcome(
            position=position,
            pick=simulated_pick,
            scouted_grade=scouted_grade,
        )
        outcome['position'] = position
        outcome['round'] = round_num

        prospects.append(outcome)

    # Sort by scouted grade (highest first)
    prospects.sort(key=lambda x: -x['scouted_grade'])

    return prospects
