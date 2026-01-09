#!/usr/bin/env python3
"""
Contract Timing Analysis

Determines optimal contract timing decisions:
- When to extend vs. let walk
- Optimal extension windows by position
- Contract length recommendations by age
- Surplus value windows

Based on:
- Development curves (peak ages, decline rates)
- Salary allocation (position value, market rates)

Output: research/exports/contract_timing_analysis.json
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

GROWTH_RATES = {
    'QB': 0.08, 'RB': 0.15, 'WR': 0.12, 'TE': 0.10, 'OL': 0.08,
    'CB': 0.12, 'S': 0.10, 'LB': 0.12, 'EDGE': 0.10, 'DL': 0.08,
}

# From salary allocation - draft priority indicates replacement difficulty
REPLACEMENT_DIFFICULTY = {
    'QB': 'very_hard',   # 4.32x rookie premium, hard to find
    'EDGE': 'hard',      # 3.24x, premium position
    'OL': 'hard',        # 9.56x premium but slow development
    'WR': 'medium',      # 2.27x, reasonable FA market
    'DL': 'medium',      # 3.83x but deep position
    'S': 'medium',       # 2.23x, decent FA options
    'TE': 'easy',        # 1.72x, replaceable
    'LB': 'easy',        # 1.16x, deep position
    'CB': 'easy',        # 0.58x, better to sign FA
    'RB': 'very_easy',   # 0.39x, easily replaceable
}


# =============================================================================
# Analysis Functions
# =============================================================================

def compute_extension_windows() -> Dict:
    """
    Compute optimal extension timing windows by position.

    Key insight: Extend BEFORE peak to lock in prime years at pre-prime price.
    """
    results = {}

    for position in PEAK_AGES.keys():
        peak = PEAK_AGES[position]
        prime_start, prime_end = PRIME_YEARS[position]
        decline = DECLINE_RATES[position]
        replacement = REPLACEMENT_DIFFICULTY[position]

        # Optimal extension window: 1-3 years before peak
        # This locks in prime years at a discount
        optimal_start = peak - 3
        optimal_end = peak - 1

        # Last chance window: at peak (paying full price but still getting value)
        last_chance = peak

        # Danger zone: past peak (paying for decline)
        danger_start = peak + 1

        # Years of prime remaining at each extension point
        prime_at_optimal = prime_end - optimal_start
        prime_at_last_chance = prime_end - last_chance
        prime_at_danger = max(0, prime_end - danger_start)

        results[position] = {
            'peak_age': peak,
            'prime_years': list(PRIME_YEARS[position]),
            'decline_rate': f"{decline:.0%}/year",
            'replacement_difficulty': replacement,
            'extension_windows': {
                'optimal': {
                    'ages': [optimal_start, optimal_end],
                    'description': f"Extend at age {optimal_start}-{optimal_end}",
                    'prime_years_captured': prime_at_optimal,
                    'recommendation': 'EXTEND - best value',
                },
                'acceptable': {
                    'ages': [last_chance, last_chance],
                    'description': f"Extend at age {last_chance}",
                    'prime_years_captured': prime_at_last_chance,
                    'recommendation': 'EXTEND - if elite player',
                },
                'risky': {
                    'ages': [danger_start, danger_start + 2],
                    'description': f"Extend at age {danger_start}+",
                    'prime_years_captured': prime_at_danger,
                    'recommendation': 'CAUTION - declining production',
                },
            },
        }

    return results


def compute_contract_length_guidance() -> Dict:
    """
    Recommend contract lengths based on position and age.

    Principle: Contract should end near or before prime ends.
    """
    results = {}

    for position in PEAK_AGES.keys():
        peak = PEAK_AGES[position]
        prime_start, prime_end = PRIME_YEARS[position]
        decline = DECLINE_RATES[position]

        position_guidance = {}

        for age in range(21, 35):
            years_to_prime_end = max(0, prime_end - age)
            years_past_peak = max(0, age - peak)

            if age < prime_start - 2:
                # Very young: long deal OK, captures development + prime
                max_years = 5
                ideal_years = 4
                rationale = "Captures development and prime years"
            elif age < peak:
                # Pre-peak: extend through prime
                max_years = min(5, years_to_prime_end + 1)
                ideal_years = min(4, years_to_prime_end)
                rationale = f"Locks in {years_to_prime_end} prime years"
            elif age <= prime_end:
                # In prime: shorter deal, will decline soon
                max_years = min(3, years_to_prime_end + 1)
                ideal_years = min(2, years_to_prime_end)
                rationale = f"Only {years_to_prime_end} prime years left"
            else:
                # Past prime: very short or don't extend
                if decline >= 0.10:  # Fast declining position
                    max_years = 1
                    ideal_years = 1
                    rationale = f"Past prime, {decline:.0%}/year decline"
                else:
                    max_years = 2
                    ideal_years = 1
                    rationale = f"Past prime but slow decline ({decline:.0%}/year)"

            position_guidance[age] = {
                'ideal_years': ideal_years,
                'max_years': max_years,
                'rationale': rationale,
                'years_to_prime_end': years_to_prime_end,
            }

        results[position] = position_guidance

    return results


def compute_extend_vs_replace() -> Dict:
    """
    Framework for extend vs. let walk decision.

    Factors:
    - Player quality (rating)
    - Age relative to peak
    - Position replacement difficulty
    - Expected contract cost
    """

    decision_matrix = {}

    for position in PEAK_AGES.keys():
        peak = PEAK_AGES[position]
        decline = DECLINE_RATES[position]
        replacement = REPLACEMENT_DIFFICULTY[position]

        # Build decision rules
        rules = []

        # Rule 1: Elite players at hard-to-replace positions
        if replacement in ['very_hard', 'hard']:
            rules.append({
                'condition': 'Elite (top 5 at position) AND pre-peak',
                'decision': 'EXTEND',
                'max_cost': 'Top of market',
                'rationale': f'{position} is hard to replace via draft/FA',
            })
            rules.append({
                'condition': 'Elite AND at peak',
                'decision': 'EXTEND',
                'max_cost': 'Market rate',
                'rationale': 'Still valuable, worth paying',
            })
            rules.append({
                'condition': 'Elite AND 1-2 years past peak',
                'decision': 'EXTEND with caution',
                'max_cost': 'Below market',
                'rationale': f'{decline:.0%}/year decline expected',
            })

        # Rule 2: Good starters
        rules.append({
            'condition': 'Good starter AND pre-peak',
            'decision': 'EXTEND' if replacement != 'very_easy' else 'CONSIDER',
            'max_cost': 'Market rate',
            'rationale': 'Growth potential justifies investment',
        })
        rules.append({
            'condition': 'Good starter AND past peak',
            'decision': 'REPLACE' if decline >= 0.08 else 'SHORT DEAL',
            'max_cost': 'Below market' if decline >= 0.08 else 'Market rate',
            'rationale': f'{decline:.0%}/year decline',
        })

        # Rule 3: Easily replaceable positions
        if replacement in ['easy', 'very_easy']:
            rules.append({
                'condition': 'Any quality AND age 28+',
                'decision': 'REPLACE via draft/FA',
                'max_cost': 'Veteran minimum',
                'rationale': f'{position} easily replaced, save cap',
            })

        decision_matrix[position] = {
            'replacement_difficulty': replacement,
            'peak_age': peak,
            'decline_rate': f"{decline:.0%}",
            'rules': rules,
        }

    return decision_matrix


def compute_surplus_value_windows() -> Dict:
    """
    Identify when players provide surplus value (production > cost).

    Rookie deals provide the most surplus; post-prime provides least.
    """

    results = {}

    for position in PEAK_AGES.keys():
        peak = PEAK_AGES[position]
        prime_start, prime_end = PRIME_YEARS[position]
        growth = GROWTH_RATES[position]
        decline = DECLINE_RATES[position]

        # Surplus phases
        phases = []

        # Phase 1: Rookie deal (years 1-4)
        # High surplus because cheap + developing
        phases.append({
            'phase': 'Rookie Contract',
            'typical_ages': [21, 24],
            'surplus_level': 'VERY HIGH',
            'explanation': 'Cheap contract, player developing toward peak',
            'strategy': 'Maximize playing time, evaluate for extension',
        })

        # Phase 2: Second contract pre-peak
        # Good surplus if extended early
        phases.append({
            'phase': 'Second Contract (Pre-Peak)',
            'typical_ages': [25, peak - 1],
            'surplus_level': 'HIGH' if growth >= 0.10 else 'MEDIUM',
            'explanation': f'Still improving ({growth:.0%}/year), prime years ahead',
            'strategy': 'Extend before FA if above-average player',
        })

        # Phase 3: Prime years
        # Fair value - paying market rate for production
        phases.append({
            'phase': 'Prime Years',
            'typical_ages': [prime_start, prime_end],
            'surplus_level': 'NEUTRAL',
            'explanation': 'Paying market rate for peak production',
            'strategy': 'Only extend if elite; otherwise let FA determine value',
        })

        # Phase 4: Post-prime
        # Negative surplus - paying for past performance
        if decline >= 0.10:
            surplus = 'NEGATIVE'
            strategy = 'Do not extend; replace via draft'
        elif decline >= 0.06:
            surplus = 'LOW'
            strategy = 'Short deal only if no replacement ready'
        else:
            surplus = 'MEDIUM'
            strategy = 'Can extend technique-based veterans'

        phases.append({
            'phase': 'Post-Prime',
            'typical_ages': [prime_end + 1, 35],
            'surplus_level': surplus,
            'explanation': f'Declining {decline:.0%}/year, paying for past',
            'strategy': strategy,
        })

        results[position] = phases

    return results


def analyze_contract_data() -> Dict:
    """Analyze actual contract patterns from data."""

    try:
        contracts = pd.read_parquet(DATA_DIR / "contracts.parquet")

        # Filter to relevant contracts
        contracts = contracts.dropna(subset=['apy_cap_pct', 'years'])
        contracts = contracts[contracts['years'] >= 1]

        # Analyze by position
        position_stats = {}

        for position in ['QB', 'RB', 'WR', 'TE', 'CB', 'S', 'LB']:
            pos_data = contracts[contracts['position'] == position]
            if len(pos_data) < 10:
                continue

            position_stats[position] = {
                'avg_years': round(pos_data['years'].mean(), 1),
                'avg_apy_cap_pct': round(pos_data['apy_cap_pct'].mean() * 100, 2),
                'median_apy_cap_pct': round(pos_data['apy_cap_pct'].median() * 100, 2),
                'max_apy_cap_pct': round(pos_data['apy_cap_pct'].max() * 100, 2),
                'n_contracts': len(pos_data),
            }

        return position_stats

    except Exception as e:
        return {'error': str(e)}


def generate_recommendations() -> Dict:
    """Generate strategic recommendations for contract timing."""

    return {
        'general_principles': [
            "Extend players BEFORE peak to capture prime at pre-prime cost",
            "Shorter deals for fast-declining positions (RB, CB)",
            "Longer deals OK for slow-declining positions (QB, OL)",
            "Replacement difficulty should influence willingness to pay",
        ],
        'by_position_tier': {
            'extend_aggressively': {
                'positions': ['QB', 'EDGE', 'OL'],
                'reason': 'Hard to replace via draft/FA, slow decline',
                'timing': '2-3 years before peak',
                'max_years': '4-5 years',
            },
            'extend_selectively': {
                'positions': ['WR', 'DL', 'S', 'TE'],
                'reason': 'Moderate replacement difficulty',
                'timing': '1-2 years before peak',
                'max_years': '3-4 years',
            },
            'avoid_extensions': {
                'positions': ['RB', 'CB', 'LB'],
                'reason': 'Easy to replace, fast decline (RB/CB) or deep position (LB)',
                'timing': 'Only extend elite players',
                'max_years': '2-3 years, prefer 1-year deals',
            },
        },
        'red_flags': [
            "Never give long deals to RBs over 26 (12%/year decline)",
            "CBs over 29 are risky (speed-dependent, 10%/year decline)",
            "Avoid guaranteeing years past prime end for any position",
            "Don't pay market rate for players 2+ years past peak",
        ],
        'best_practices': [
            "Use franchise tag to bridge extension negotiations at peak",
            "Structure deals with declining cap hits (front-load)",
            "Include performance incentives for aging players",
            "Plan replacement 2 years before expected decline",
        ],
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Contract Timing Analysis")
    print("=" * 60)
    print()

    # Run analyses
    print("Computing extension windows...")
    extension_windows = compute_extension_windows()

    print("Computing contract length guidance...")
    length_guidance = compute_contract_length_guidance()

    print("Computing extend vs replace framework...")
    extend_replace = compute_extend_vs_replace()

    print("Computing surplus value windows...")
    surplus_windows = compute_surplus_value_windows()

    print("Analyzing contract data...")
    contract_stats = analyze_contract_data()

    print("Generating recommendations...")
    recommendations = generate_recommendations()

    # Compile results
    results = {
        'meta': {
            'description': 'Contract timing analysis for extension decisions',
            'methodology': 'Based on development curves and salary allocation data',
        },
        'extension_windows': extension_windows,
        'contract_length_guidance': length_guidance,
        'extend_vs_replace': extend_replace,
        'surplus_value_windows': surplus_windows,
        'market_data': contract_stats,
        'recommendations': recommendations,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / "contract_timing_analysis.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExported to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Extension Windows by Position")
    print("=" * 60)

    for pos in ['QB', 'RB', 'EDGE', 'CB', 'OL']:
        data = extension_windows[pos]
        opt = data['extension_windows']['optimal']
        print(f"\n{pos} (peak: {data['peak_age']}, decline: {data['decline_rate']})")
        print(f"  Optimal: ages {opt['ages'][0]}-{opt['ages'][1]} → {opt['prime_years_captured']} prime years")
        print(f"  Replacement: {data['replacement_difficulty']}")

    print("\n" + "=" * 60)
    print("Surplus Value Phases (Example: RB)")
    print("=" * 60)
    for phase in surplus_windows['RB']:
        print(f"\n{phase['phase']} (ages {phase['typical_ages']})")
        print(f"  Surplus: {phase['surplus_level']}")
        print(f"  Strategy: {phase['strategy']}")


if __name__ == '__main__':
    main()
