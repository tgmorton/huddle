#!/usr/bin/env python3
"""
Free Agency Valuation Analysis

Creates a framework for evaluating and scoring free agent targets:
- Value score based on production, age, and position
- Cost projection based on market rates
- Value vs. cost comparison
- Risk assessment

Based on:
- Salary allocation (market values, position weights)
- Development curves (age-based projections)
- Contract timing (optimal years, surplus value)

Output: research/exports/fa_valuation_analysis.json
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
DATA_DIR = Path("research/data/cached")

# From salary allocation - market value by tier (% of cap)
MARKET_VALUES = {
    'QB':   {'elite': 4.08, 'starter': 0.84, 'backup': 0.27},
    'RB':   {'elite': 1.34, 'starter': 0.75, 'backup': 0.24},
    'WR':   {'elite': 1.26, 'starter': 0.75, 'backup': 0.23},
    'TE':   {'elite': 1.34, 'starter': 0.76, 'backup': 0.23},
    'OL':   {'elite': 2.58, 'starter': 0.80, 'backup': 0.23},
    'CB':   {'elite': 1.37, 'starter': 0.76, 'backup': 0.23},
    'S':    {'elite': 1.90, 'starter': 0.81, 'backup': 0.25},
    'LB':   {'elite': 1.65, 'starter': 0.80, 'backup': 0.26},
    'EDGE': {'elite': 2.00, 'starter': 0.85, 'backup': 0.25},
    'DL':   {'elite': 1.80, 'starter': 0.82, 'backup': 0.24},
}

# From development curves
PEAK_AGES = {
    'QB': 29, 'RB': 26, 'WR': 27, 'TE': 28, 'OL': 28,
    'CB': 27, 'S': 28, 'LB': 27, 'EDGE': 27, 'DL': 28,
}

PRIME_YEARS = {
    'QB': (27, 33), 'RB': (24, 28), 'WR': (25, 30), 'TE': (26, 31), 'OL': (26, 32),
    'CB': (25, 29), 'S': (26, 30), 'LB': (25, 30), 'EDGE': (25, 30), 'DL': (26, 31),
}

DECLINE_RATES = {
    'QB': 0.04, 'RB': 0.12, 'WR': 0.06, 'TE': 0.05, 'OL': 0.04,
    'CB': 0.10, 'S': 0.06, 'LB': 0.07, 'EDGE': 0.08, 'DL': 0.05,
}

# FA value indicators - prefer signing these positions in FA vs draft
FA_PREFERENCE = {
    'RB': 1.5,    # 0.39x rookie premium = sign veterans
    'CB': 1.3,    # 0.58x rookie premium = sign veterans
    'LB': 1.1,    # 1.16x = slight FA preference
    'TE': 1.0,    # Neutral
    'S': 0.9,     # Slight draft preference
    'WR': 0.8,    # Draft preference
    'DL': 0.7,    # Draft preference
    'EDGE': 0.6,  # Strong draft preference
    'OL': 0.5,    # Strong draft preference
    'QB': 0.4,    # Very strong draft preference
}


# =============================================================================
# Valuation Functions
# =============================================================================

def compute_player_tier(rating: float) -> str:
    """Classify player into tier based on rating."""
    if rating >= 85:
        return 'elite'
    elif rating >= 70:
        return 'starter'
    else:
        return 'backup'


def project_production(position: str, age: int, current_rating: float, years_ahead: int = 3) -> float:
    """Project average production over next N years."""
    peak = PEAK_AGES[position]
    decline = DECLINE_RATES[position]

    total = 0
    for year in range(years_ahead):
        player_age = age + year
        if player_age <= peak:
            # Still at or before peak
            year_rating = current_rating
        else:
            years_past = player_age - peak
            year_rating = current_rating * ((1 - decline) ** years_past)
        total += year_rating

    return total / years_ahead


def compute_fa_value_score(
    position: str,
    age: int,
    rating: float,
    injury_history: str = 'clean',  # 'clean', 'minor', 'major'
) -> Dict:
    """
    Compute a value score for a free agent (0-100 scale).

    Factors:
    - Production (rating)
    - Age relative to prime
    - Position FA preference
    - Injury risk
    """
    peak = PEAK_AGES[position]
    prime_start, prime_end = PRIME_YEARS[position]
    decline = DECLINE_RATES[position]
    fa_pref = FA_PREFERENCE[position]

    # 1. Base value from rating (40-100 → 0-60)
    base_value = max(0, (rating - 40)) * 1.0

    # 2. Age factor
    if age < prime_start:
        # Pre-prime: small bonus (upside)
        age_factor = 10
    elif age <= prime_end:
        # In prime: full value
        age_factor = 5
    else:
        # Past prime: penalty based on decline rate
        years_past = age - prime_end
        age_factor = -years_past * (decline * 50 + 5)

    # 3. Position FA preference multiplier
    position_factor = fa_pref

    # 4. Injury adjustment
    injury_adjustments = {
        'clean': 1.0,
        'minor': 0.9,
        'major': 0.7,
    }
    injury_mult = injury_adjustments.get(injury_history, 0.8)

    # 5. Compute score
    raw_score = (base_value + age_factor) * position_factor * injury_mult
    score = max(0, min(100, raw_score))

    # 6. Project future production
    projected = project_production(position, age, rating, 3)

    return {
        'value_score': round(score, 1),
        'base_value': round(base_value, 1),
        'age_factor': round(age_factor, 1),
        'position_mult': round(position_factor, 2),
        'injury_mult': round(injury_mult, 2),
        'projected_avg_rating': round(projected, 1),
        'years_of_prime_left': max(0, prime_end - age),
    }


def compute_expected_cost(position: str, rating: float, age: int) -> Dict:
    """
    Estimate expected contract cost for a free agent.

    Based on market rates with age adjustments.
    """
    tier = compute_player_tier(rating)
    market = MARKET_VALUES.get(position, {})
    base_cost = market.get(tier, 0.50)

    peak = PEAK_AGES[position]
    prime_end = PRIME_YEARS[position][1]

    # Age adjustments to cost
    if age < peak:
        # Pre-peak: premium for upside
        cost_mult = 1.1
    elif age <= peak + 1:
        # At peak: full price
        cost_mult = 1.0
    elif age <= prime_end:
        # Late prime: slight discount
        cost_mult = 0.9
    else:
        # Past prime: bigger discount
        years_past = age - prime_end
        cost_mult = max(0.5, 0.85 - years_past * 0.1)

    expected_cost = base_cost * cost_mult

    # Contract years expectation
    if age >= prime_end:
        expected_years = 1
    elif age >= peak:
        expected_years = 2
    else:
        expected_years = min(4, prime_end - age + 1)

    return {
        'tier': tier,
        'base_market_rate': round(base_cost, 3),
        'age_multiplier': round(cost_mult, 2),
        'expected_apy_cap_pct': round(expected_cost, 3),
        'expected_years': expected_years,
        'total_cap_commitment': round(expected_cost * expected_years, 3),
    }


def compute_value_vs_cost(value_score: float, cost: Dict) -> Dict:
    """Compare value score to expected cost."""

    # Normalize cost to 0-100 scale (0% cap = 0, 4% cap = 100)
    cost_normalized = cost['expected_apy_cap_pct'] / 4.0 * 100

    # Value/cost ratio
    if cost_normalized > 0:
        ratio = value_score / cost_normalized
    else:
        ratio = 10.0  # Very cheap

    # Classification
    if ratio >= 1.5:
        classification = 'STRONG BUY'
    elif ratio >= 1.2:
        classification = 'BUY'
    elif ratio >= 0.9:
        classification = 'FAIR VALUE'
    elif ratio >= 0.7:
        classification = 'OVERPRICED'
    else:
        classification = 'AVOID'

    return {
        'value_score': round(value_score, 1),
        'cost_score': round(cost_normalized, 1),
        'value_cost_ratio': round(ratio, 2),
        'classification': classification,
    }


def score_fa_target(
    position: str,
    age: int,
    rating: float,
    injury_history: str = 'clean',
) -> Dict:
    """
    Complete FA target evaluation.

    Returns value score, expected cost, and recommendation.
    """
    value = compute_fa_value_score(position, age, rating, injury_history)
    cost = compute_expected_cost(position, rating, age)
    comparison = compute_value_vs_cost(value['value_score'], cost)

    return {
        'player': {
            'position': position,
            'age': age,
            'rating': rating,
            'injury_history': injury_history,
        },
        'value': value,
        'cost': cost,
        'evaluation': comparison,
    }


# =============================================================================
# Analysis
# =============================================================================

def analyze_fa_archetypes() -> List[Dict]:
    """Evaluate common FA archetypes."""

    archetypes = [
        # High-value targets
        ('QB', 27, 88, 'clean', "Elite young QB entering prime"),
        ('RB', 25, 82, 'clean', "Peak-age RB, good production"),
        ('WR', 26, 85, 'clean', "Prime WR1"),
        ('EDGE', 26, 84, 'clean', "Prime pass rusher"),

        # Value plays
        ('RB', 28, 78, 'clean', "Post-peak RB, cheaper"),
        ('CB', 27, 76, 'minor', "Solid CB, minor injury"),
        ('LB', 28, 75, 'clean', "Solid starter LB"),
        ('TE', 29, 74, 'clean', "Veteran TE"),

        # Risky targets
        ('RB', 30, 80, 'clean', "Aging RB, still productive"),
        ('CB', 31, 78, 'clean', "Aging CB"),
        ('WR', 32, 75, 'minor', "Aging WR with injury"),

        # Bargain bin
        ('QB', 34, 72, 'clean', "Veteran backup QB"),
        ('RB', 29, 70, 'major', "Post-injury RB"),
        ('LB', 30, 72, 'clean', "Depth LB"),
    ]

    results = []
    for pos, age, rating, injury, desc in archetypes:
        eval_result = score_fa_target(pos, age, rating, injury)
        eval_result['description'] = desc
        results.append(eval_result)

    return results


def compute_position_fa_tiers() -> Dict:
    """
    Identify which positions are best addressed via FA.

    Based on rookie premium (inverse) and market efficiency.
    """

    tiers = {
        'strong_fa_preference': {
            'positions': ['RB', 'CB'],
            'reasoning': 'Very low rookie premium (0.39x, 0.58x) - veterans more efficient',
            'strategy': 'Sign proven veterans at market rate, avoid drafting early',
        },
        'moderate_fa_preference': {
            'positions': ['LB', 'TE'],
            'reasoning': 'Low-moderate rookie premium (1.16x, 1.72x) - FA is fine',
            'strategy': 'Either draft mid-rounds or sign FA depending on value',
        },
        'draft_preference': {
            'positions': ['WR', 'S', 'DL'],
            'reasoning': 'Moderate rookie premium (2.0-2.3x) - draft provides edge',
            'strategy': 'Prefer draft, use FA only for proven elite players',
        },
        'strong_draft_preference': {
            'positions': ['QB', 'OL', 'EDGE'],
            'reasoning': 'High rookie premium (3.2-9.6x) - draft is much better value',
            'strategy': 'Only sign elite FA if desperate, otherwise draft',
        },
    }

    return tiers


def generate_fa_recommendations() -> Dict:
    """Generate strategic FA recommendations."""

    return {
        'spending_priorities': {
            'spend_heavily': [
                "Elite RBs age 25-27 (peak production, easier to evaluate)",
                "Proven CBs age 26-28 (rookies underperform)",
                "LBs from any system (deep position, translatable skills)",
            ],
            'spend_moderately': [
                "WR2/WR3 types (save WR1 money for draft picks)",
                "Rotational DL (depth matters)",
                "Solid TEs (blocking helps immediately)",
            ],
            'spend_sparingly': [
                "QBs (only backups unless elite franchise QB available)",
                "OL (prefer draft, development matters)",
                "EDGE (premium in draft, expensive in FA)",
            ],
        },
        'value_traps': [
            "RBs over 28 - decline imminent despite current production",
            "CBs over 29 - speed loss accelerates",
            "Any player with major injury in speed-dependent position",
            "Paying elite money for good-not-great production",
        ],
        'hidden_value': [
            "Post-hype players age 26-28 who underperformed on bad teams",
            "Players coming off injury at technique positions (OL, TE)",
            "LBs from run-heavy defenses (tackle stats inflate value)",
            "Slot CBs (undervalued vs outside corners)",
        ],
        'negotiation_leverage': {
            'high_leverage': [
                "RB market - many options, short careers",
                "LB market - deep position, interchangeable",
                "Backup QB market - many available",
            ],
            'low_leverage': [
                "Elite QB market - almost never available",
                "Elite EDGE market - highest demand",
                "Young elite WR market - rare to hit FA",
            ],
        },
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Free Agency Valuation Analysis")
    print("=" * 60)
    print()

    # Run analyses
    print("Evaluating FA archetypes...")
    archetypes = analyze_fa_archetypes()

    print("Computing position FA tiers...")
    position_tiers = compute_position_fa_tiers()

    print("Generating recommendations...")
    recommendations = generate_fa_recommendations()

    # Compile results
    results = {
        'meta': {
            'description': 'Free agency valuation framework',
            'methodology': 'Combines market values, development curves, and rookie premiums',
        },
        'archetype_evaluations': archetypes,
        'position_tiers': position_tiers,
        'recommendations': recommendations,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / "fa_valuation_analysis.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExported to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("FA Target Evaluations")
    print("=" * 60)

    for arch in archetypes:
        player = arch['player']
        eval_res = arch['evaluation']
        cost = arch['cost']
        print(f"\n{arch['description']}")
        print(f"  {player['position']} age {player['age']}, {player['rating']} rating")
        print(f"  Value: {eval_res['value_score']:.0f} | Cost: {cost['expected_apy_cap_pct']:.2f}% cap")
        print(f"  → {eval_res['classification']} (ratio: {eval_res['value_cost_ratio']:.2f})")

    print("\n" + "=" * 60)
    print("Position FA Preference Tiers")
    print("=" * 60)
    for tier, data in position_tiers.items():
        print(f"\n{tier.upper().replace('_', ' ')}: {data['positions']}")
        print(f"  {data['reasoning']}")


if __name__ == '__main__':
    main()
