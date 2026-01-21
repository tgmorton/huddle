#!/usr/bin/env python3
"""
Trade Value Analysis

Creates a framework for player↔pick value conversion based on:
1. Draft pick expected value curves
2. Player remaining career value (from development curves)
3. Position value weights (from salary allocation)
4. Contract surplus value

Output: research/exports/trade_value_analysis.json
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# =============================================================================
# Configuration
# =============================================================================

EXPORT_DIR = Path("research/exports")

# From our draft value analysis - pick value relative to #1 = 100
PICK_VALUES = {
    1: 100.0, 2: 95.0, 3: 90.0, 4: 85.0, 5: 80.0,
    6: 76.0, 7: 73.0, 8: 70.0, 9: 67.0, 10: 64.0,
    11: 55.0, 12: 53.0, 13: 51.0, 14: 49.0, 15: 47.0,
    16: 42.0, 17: 41.0, 18: 40.0, 19: 39.0, 20: 38.0,
    21: 46.0, 22: 45.0, 23: 44.0, 24: 43.0, 25: 42.0,
    26: 41.0, 27: 40.0, 28: 39.0, 29: 38.0, 30: 37.0,
    31: 36.0, 32: 35.0,
}

# Round-based values for later picks
ROUND_VALUES = {
    2: 25.0,  # Average 2nd round pick
    3: 15.0,  # Average 3rd round pick
    4: 8.0,   # Average 4th round pick
    5: 4.0,   # Average 5th round pick
    6: 2.0,   # Average 6th round pick
    7: 1.0,   # Average 7th round pick
}

# From development curves - peak ages and decline rates
PEAK_AGES = {
    'QB': 29, 'RB': 26, 'WR': 27, 'TE': 28, 'OL': 28,
    'CB': 27, 'S': 28, 'LB': 27, 'EDGE': 27, 'DL': 28,
}

DECLINE_RATES = {
    'QB': 0.04, 'RB': 0.12, 'WR': 0.06, 'TE': 0.05, 'OL': 0.04,
    'CB': 0.10, 'S': 0.06, 'LB': 0.07, 'EDGE': 0.08, 'DL': 0.05,
}

# From salary allocation - position value weights (relative importance)
POSITION_WEIGHTS = {
    'QB': 2.0,    # Most valuable
    'EDGE': 1.5,  # Premium pass rusher
    'OL': 1.3,    # Premium blocker
    'WR': 1.2,    # Skill position
    'CB': 1.1,    # Coverage
    'DL': 1.0,    # Interior
    'TE': 0.9,    # Hybrid
    'LB': 0.8,    # Linebacker
    'S': 0.7,     # Safety
    'RB': 0.5,    # Replaceable
}


# =============================================================================
# Trade Value Model
# =============================================================================

def compute_remaining_career_value(
    position: str,
    age: int,
    current_rating: float,
    years_horizon: int = 5
) -> float:
    """
    Compute expected remaining career value over the next N years.

    Uses development curves to project performance and sum total value.
    """
    peak_age = PEAK_AGES.get(position, 27)
    decline_rate = DECLINE_RATES.get(position, 0.06)

    total_value = 0.0

    for year in range(years_horizon):
        player_age = age + year

        if player_age < peak_age:
            # Still growing - assume linear growth to peak
            years_to_peak = peak_age - player_age
            growth_per_year = (100 - current_rating) / max(years_to_peak, 1) * 0.3
            year_rating = min(current_rating + growth_per_year * year, 99)
        else:
            # Past peak - apply decline
            years_past_peak = player_age - peak_age
            year_rating = current_rating * ((1 - decline_rate) ** years_past_peak)

        # Discount future years (time value)
        discount = 0.9 ** year
        total_value += year_rating * discount

    return total_value


def compute_player_trade_value(
    position: str,
    age: int,
    rating: float,
    years_remaining: int = 3,
    cap_hit_pct: float = 0.02
) -> Dict:
    """
    Compute a player's trade value in terms of draft pick equivalents.

    Returns pick equivalent and analysis breakdown.

    Value scale: 0-100 to match pick values (pick 1 = 100)
    """
    peak_age = PEAK_AGES.get(position, 27)
    decline_rate = DECLINE_RATES.get(position, 0.06)
    pos_weight = POSITION_WEIGHTS.get(position, 1.0)

    # 1. Base value from rating (normalized to 0-50 scale)
    # 60 rating = 0, 90 rating = 30
    rating_value = max(0, (rating - 60)) * 1.0

    # 2. Age factor: pre-peak = bonus, post-peak = penalty
    if age < peak_age:
        # Pre-peak: bonus for upside (max +20)
        years_to_peak = peak_age - age
        age_factor = min(years_to_peak * 4, 20)
    elif age == peak_age:
        age_factor = 0
    else:
        # Post-peak: penalty based on expected decline
        years_past = age - peak_age
        # Steeper penalty for fast-declining positions
        age_factor = -years_past * (decline_rate * 100 + 2)

    # 3. Position value multiplier (QB = 1.5x, RB = 0.6x)
    position_mult = 0.5 + (pos_weight * 0.5)

    # 4. Contract value: years of control + surplus
    # Cheap contracts on good players are very valuable
    expected_market = rating / 100 * pos_weight * 5  # Expected cap %
    surplus = max(0, expected_market - cap_hit_pct * 100) * 0.5
    years_value = min(years_remaining, 4) * 3

    # 5. Combine
    raw_value = (rating_value + age_factor) * position_mult + surplus + years_value

    # 6. Scale to pick value range (0-100)
    # Elite young QB on rookie deal = ~100 (pick 1)
    # Average starter = ~35-40 (late 1st)
    # Replacement level = ~10-15 (3rd round)
    scaled_value = max(0, min(100, raw_value))

    # 7. Convert to pick
    pick_equivalent = value_to_pick(scaled_value)

    return {
        'total_value': round(scaled_value, 1),
        'rating_value': round(rating_value, 1),
        'age_factor': round(age_factor, 1),
        'position_mult': round(position_mult, 2),
        'contract_value': round(surplus + years_value, 1),
        'pick_equivalent': pick_equivalent,
        'pick_value': round(get_pick_value(pick_equivalent), 1),
    }


def get_pick_value(pick: int) -> float:
    """Get value for a draft pick."""
    if pick <= 32:
        return PICK_VALUES.get(pick, 35.0)

    round_num = (pick - 1) // 32 + 1
    return ROUND_VALUES.get(round_num, 1.0)


def value_to_pick(value: float) -> int:
    """Convert trade value to equivalent draft pick."""
    # Find the pick with closest value
    for pick in range(1, 33):
        if PICK_VALUES.get(pick, 0) <= value:
            return pick

    # Check later rounds
    if value >= ROUND_VALUES[2]:
        return 40  # Mid 2nd
    elif value >= ROUND_VALUES[3]:
        return 70  # Mid 3rd
    elif value >= ROUND_VALUES[4]:
        return 110  # Mid 4th
    elif value >= ROUND_VALUES[5]:
        return 150  # Mid 5th
    elif value >= ROUND_VALUES[6]:
        return 190  # Mid 6th
    else:
        return 220  # 7th round


def compute_pick_package_value(picks: List[int]) -> float:
    """Compute total value of a package of picks."""
    return sum(get_pick_value(p) for p in picks)


def find_equivalent_package(target_value: float, available_rounds: List[int] = [1,2,3,4]) -> List[int]:
    """Find a package of picks that approximates target value."""
    # Greedy approach: start with highest value picks
    package = []
    remaining = target_value

    for round_num in sorted(available_rounds):
        pick = round_num * 32 - 16  # Mid-round pick
        pick_val = get_pick_value(pick)

        while remaining >= pick_val and len(package) < 4:
            package.append(pick)
            remaining -= pick_val

    return package


# =============================================================================
# Analysis
# =============================================================================

def analyze_trade_scenarios() -> Dict:
    """Generate trade value examples for common scenarios."""

    scenarios = []

    # Scenario matrix: position × age × rating
    test_cases = [
        # Elite young players
        ('QB', 25, 88, 4, 0.01, "Elite young QB on rookie deal"),
        ('EDGE', 24, 85, 3, 0.02, "Elite young pass rusher"),
        ('WR', 25, 86, 2, 0.03, "Elite young WR"),

        # Prime veterans
        ('QB', 30, 90, 2, 0.10, "Prime veteran QB, expensive"),
        ('RB', 27, 85, 2, 0.03, "Prime RB, starting decline"),
        ('CB', 28, 82, 3, 0.04, "Prime CB"),

        # Aging stars
        ('QB', 35, 85, 2, 0.08, "Aging QB, still productive"),
        ('RB', 29, 80, 1, 0.02, "Aging RB, cheap but declining fast"),
        ('WR', 31, 78, 2, 0.05, "Aging WR"),

        # Young developing players
        ('QB', 23, 72, 3, 0.01, "Young QB with upside"),
        ('OL', 24, 75, 3, 0.01, "Young OL on rookie deal"),
        ('LB', 25, 74, 2, 0.02, "Solid young LB"),
    ]

    for pos, age, rating, years, cap, desc in test_cases:
        result = compute_player_trade_value(pos, age, rating, years, cap)
        scenarios.append({
            'description': desc,
            'position': pos,
            'age': age,
            'rating': rating,
            'years_remaining': years,
            'cap_hit_pct': cap,
            **result
        })

    return scenarios


def compute_position_value_by_age() -> Dict:
    """Compute trade value curves by position and age."""

    results = {}

    for position in POSITION_WEIGHTS.keys():
        position_data = {}

        for age in range(22, 36):
            # Assume a "good starter" (80 rating) with 3 years left, market deal
            result = compute_player_trade_value(
                position=position,
                age=age,
                rating=80,
                years_remaining=3,
                cap_hit_pct=0.03
            )
            position_data[age] = {
                'value': result['total_value'],
                'pick_equivalent': result['pick_equivalent'],
            }

        results[position] = position_data

    return results


def compute_pick_trade_chart() -> Dict:
    """
    Create pick-for-pick trade value chart.

    Based on our empirical pick value curve.
    """
    chart = {}

    for pick in range(1, 257):
        value = get_pick_value(pick)

        # Find equivalent combinations
        # Single pick trades
        chart[str(pick)] = {
            'value': round(value, 1),
            'round': (pick - 1) // 32 + 1,
        }

    # Common trade patterns
    patterns = {
        'move_up_5_spots_r1': {
            'from': 10,
            'to': 5,
            'cost': round(get_pick_value(5) - get_pick_value(10), 1),
            'typical_package': [10, 42],  # Original pick + 2nd rounder
        },
        'move_up_10_spots_r1': {
            'from': 15,
            'to': 5,
            'cost': round(get_pick_value(5) - get_pick_value(15), 1),
            'typical_package': [15, 47, 80],  # Original + 2nd + 3rd
        },
        'move_into_r1_from_r2': {
            'from': 35,
            'to': 28,
            'cost': round(get_pick_value(28) - get_pick_value(35), 1),
            'typical_package': [35, 100],  # 2nd + 3rd/4th
        },
    }

    return {
        'pick_values': chart,
        'trade_patterns': patterns,
    }


def generate_recommendations() -> Dict:
    """Generate strategic recommendations for management."""

    return {
        'player_acquisition': {
            'high_value_targets': [
                "Young QBs on rookie deals (pick 1-5 equivalent)",
                "Pre-peak EDGE rushers with 3+ years control",
                "Young OL on cheap deals (9.56x rookie premium)",
            ],
            'avoid': [
                "RBs over 27 (12% annual decline)",
                "CBs over 29 (10% annual decline, speed-dependent)",
                "Any player on massive deal past peak age",
            ],
            'buy_low': [
                "Post-hype QBs age 25-27 (still pre-peak)",
                "WRs coming off injury (if young)",
                "LBs from run-heavy teams (undervalued)",
            ],
        },
        'player_trading': {
            'sell_high': [
                "RBs at age 25-26 (peak value, decline imminent)",
                "Any player entering contract year if not extending",
                "Players outperforming their draft position",
            ],
            'hold': [
                "QBs pre-peak on any deal (longest prime)",
                "Young OL (slow developers, technique ages well)",
                "EDGE on rookie deals (high value, high demand)",
            ],
        },
        'pick_valuation': {
            'key_insight': "Pick value drops 50% from #1 to #15, then flattens",
            'trade_up_math': "Moving up 5 spots in R1 costs ~1 second rounder",
            'trade_down_value': "Accumulating mid-round picks often better than reaching",
            'position_specific': {
                'QB': "Worth overpaying in R1 only - R3+ is 0% star rate",
                'RB': "Never trade up for RB - R2-3 hit rates are fine",
                'OL': "Trade up in R2 - better hit rates than R1, still get premium",
            },
        },
        'contract_vs_trade': {
            'extend_if': [
                "Player is pre-peak and top-10 at position",
                "Position has slow decline (QB, OL)",
                "Replacement cost via draft is high (QB, EDGE)",
            ],
            'trade_if': [
                "Player is 2+ years past peak",
                "Position has fast decline (RB, CB)",
                "Can get R1-R2 pick equivalent value",
            ],
        },
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Trade Value Analysis")
    print("=" * 60)
    print()

    # Run analyses
    print("Computing trade scenarios...")
    scenarios = analyze_trade_scenarios()

    print("Computing position value by age...")
    position_curves = compute_position_value_by_age()

    print("Building pick trade chart...")
    pick_chart = compute_pick_trade_chart()

    print("Generating recommendations...")
    recommendations = generate_recommendations()

    # Compile results
    results = {
        'meta': {
            'description': 'Trade value analysis for player and pick valuation',
            'methodology': 'Combines development curves, salary allocation, and draft value',
        },
        'trade_scenarios': scenarios,
        'position_value_curves': position_curves,
        'pick_chart': pick_chart,
        'recommendations': recommendations,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / "trade_value_analysis.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExported to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Trade Scenario Examples")
    print("=" * 60)

    for s in scenarios:
        print(f"\n{s['description']}")
        print(f"  {s['position']} age {s['age']}, {s['rating']} rating, {s['years_remaining']}yr/${s['cap_hit_pct']:.1%} cap")
        print(f"  → Value: {s['total_value']:.0f} = Pick #{s['pick_equivalent']}")

    print("\n" + "=" * 60)
    print("Position Value Decay (80-rated starter)")
    print("=" * 60)

    for pos in ['QB', 'RB', 'EDGE', 'OL']:
        curve = position_curves[pos]
        ages = [24, 27, 30, 33]
        values = [f"age {a}: #{curve[a]['pick_equivalent']}" for a in ages]
        print(f"  {pos:4}: {', '.join(values)}")


if __name__ == '__main__':
    main()
