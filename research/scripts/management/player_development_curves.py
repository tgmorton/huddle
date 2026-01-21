#!/usr/bin/env python3
"""
Player Development Curves Analysis

Analyzes performance vs age by position to model:
1. Peak age by position
2. Growth curves (pre-peak) with percentile bands
3. Decline curves (post-peak) with percentile bands
4. Lookup tables for player potential and regression

Output is used for:
- Player potential system (projecting young players)
- Player regression system (aging/decline)
- Contract timing decisions
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
import json
import warnings
warnings.filterwarnings('ignore')

# Optional imports
try:
    from scipy.optimize import curve_fit
    from scipy.stats import percentileofscore
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

RESEARCH_DIR = Path(__file__).parent.parent
CACHED_DIR = RESEARCH_DIR / "data" / "cached"
EXPORTS_DIR = RESEARCH_DIR / "exports"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Position Groups
# =============================================================================

OFFENSIVE_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OL']
DEFENSIVE_POSITIONS = ['CB', 'S', 'LB', 'EDGE', 'DL']

POSITION_MAP = {
    'QB': 'QB',
    'RB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'LT': 'OL', 'RT': 'OL', 'LG': 'OL', 'RG': 'OL', 'C': 'OL', 'OT': 'OL', 'G': 'OL', 'T': 'OL',
    'CB': 'CB', 'DB': 'CB',
    'S': 'S', 'FS': 'S', 'SS': 'S',
    'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB', 'OLB': 'LB',
    'ED': 'EDGE', 'EDGE': 'EDGE', 'DE': 'EDGE',
    'IDL': 'DL', 'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
}


# =============================================================================
# Data Loading
# =============================================================================

def load_player_ages() -> pd.DataFrame:
    """Load player birth dates and draft info from contracts."""
    print("Loading player age data...")

    contracts = pd.read_parquet(CACHED_DIR / "contracts.parquet")

    # Extract relevant fields
    players = contracts[[
        'player', 'position', 'gsis_id', 'date_of_birth',
        'draft_year', 'draft_round', 'draft_overall'
    ]].copy()

    # Parse birth dates
    players['dob'] = pd.to_datetime(players['date_of_birth'], errors='coerce')

    # Map to position groups
    players['position_group'] = players['position'].map(POSITION_MAP)

    # Drop duplicates (keep first entry per player)
    players = players.dropna(subset=['gsis_id']).drop_duplicates('gsis_id')

    print(f"  Loaded {len(players):,} players with age data")
    print(f"  DOB available: {players['dob'].notna().sum():,}")

    return players


def load_offensive_performance() -> pd.DataFrame:
    """Load offensive player performance (fantasy points)."""
    print("Loading offensive performance...")

    stats = pd.read_parquet(CACHED_DIR / "seasonal_stats.parquet")
    stats = stats.rename(columns={'season': 'year', 'player_id': 'gsis_id'})
    stats['performance'] = stats['fantasy_points'].fillna(0)

    print(f"  Loaded {len(stats):,} offensive player-seasons")

    return stats[['gsis_id', 'year', 'performance']]


def load_defensive_performance() -> pd.DataFrame:
    """Load defensive player performance (DV)."""
    print("Loading defensive performance...")

    dv_path = CACHED_DIR / "defensive_value.parquet"
    if not dv_path.exists():
        print("  Warning: defensive_value.parquet not found")
        return pd.DataFrame(columns=['gsis_id', 'year', 'performance'])

    stats = pd.read_parquet(dv_path)
    stats = stats.rename(columns={'season': 'year', 'player_id': 'gsis_id'})
    stats['performance'] = stats['defensive_value'].fillna(0)

    print(f"  Loaded {len(stats):,} defensive player-seasons")

    return stats[['gsis_id', 'year', 'performance']]


def compute_player_ages(players: pd.DataFrame, performance: pd.DataFrame) -> pd.DataFrame:
    """Join performance with player ages."""

    # Merge performance with player info
    merged = performance.merge(
        players[['gsis_id', 'position_group', 'dob', 'draft_year']],
        on='gsis_id',
        how='inner'
    )

    # Compute age at season
    # Season typically runs Sep-Feb, use Sep 1 as reference
    merged['season_start'] = pd.to_datetime(merged['year'].astype(str) + '-09-01')
    merged['age'] = (merged['season_start'] - merged['dob']).dt.days / 365.25

    # Also compute experience (years since draft)
    merged['experience'] = merged['year'] - merged['draft_year']

    # Filter to valid ages (21-40) and experience (0-20)
    merged = merged[
        (merged['age'] >= 21) &
        (merged['age'] <= 40) &
        (merged['experience'] >= 0) &
        (merged['experience'] <= 20)
    ]

    # Round age to nearest integer for grouping
    merged['age_bucket'] = merged['age'].round().astype(int)

    return merged


# =============================================================================
# Curve Fitting
# =============================================================================

def fit_career_curve(data: pd.DataFrame, position: str) -> Dict:
    """
    Fit a career curve for a position.

    Uses a piecewise model:
    - Pre-peak: linear or exponential growth
    - Post-peak: linear or exponential decline

    Returns peak age, growth rate, decline rate, and percentile bands.
    """
    pos_data = data[data['position_group'] == position].copy()

    if len(pos_data) < 50:
        print(f"  {position}: Insufficient data ({len(pos_data)} samples)")
        return None

    # Group by age bucket and compute percentiles
    age_stats = pos_data.groupby('age_bucket')['performance'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('std', 'std'),
        ('p10', lambda x: x.quantile(0.10)),
        ('p25', lambda x: x.quantile(0.25)),
        ('p50', lambda x: x.quantile(0.50)),
        ('p75', lambda x: x.quantile(0.75)),
        ('p90', lambda x: x.quantile(0.90)),
    ]).reset_index()

    # Filter to ages with enough samples
    age_stats = age_stats[age_stats['count'] >= 10]

    if len(age_stats) < 5:
        print(f"  {position}: Not enough age buckets with sufficient data")
        return None

    # Find peak age (age with highest mean performance)
    peak_idx = age_stats['mean'].idxmax()
    peak_age = age_stats.loc[peak_idx, 'age_bucket']
    peak_performance = age_stats.loc[peak_idx, 'mean']

    # Split into pre-peak and post-peak
    pre_peak = age_stats[age_stats['age_bucket'] <= peak_age]
    post_peak = age_stats[age_stats['age_bucket'] >= peak_age]

    # Compute growth rate (pre-peak)
    if len(pre_peak) >= 2:
        # Simple linear: performance change per year
        first_age = pre_peak['age_bucket'].min()
        first_perf = pre_peak[pre_peak['age_bucket'] == first_age]['mean'].values[0]
        years_to_peak = peak_age - first_age
        if years_to_peak > 0:
            growth_rate = (peak_performance - first_perf) / years_to_peak
            growth_pct = growth_rate / peak_performance * 100  # As % of peak
        else:
            growth_rate = 0
            growth_pct = 0
    else:
        growth_rate = 0
        growth_pct = 0

    # Compute decline rate (post-peak)
    if len(post_peak) >= 2:
        last_age = post_peak['age_bucket'].max()
        last_perf = post_peak[post_peak['age_bucket'] == last_age]['mean'].values[0]
        years_from_peak = last_age - peak_age
        if years_from_peak > 0:
            decline_rate = (peak_performance - last_perf) / years_from_peak
            decline_pct = decline_rate / peak_performance * 100  # As % of peak
        else:
            decline_rate = 0
            decline_pct = 0
    else:
        decline_rate = 0
        decline_pct = 0

    # Build percentile curves
    percentile_curves = {}
    for pct in ['p10', 'p25', 'p50', 'p75', 'p90']:
        curve = {}
        for _, row in age_stats.iterrows():
            curve[int(row['age_bucket'])] = round(row[pct], 2)
        percentile_curves[pct] = curve

    # Compute "prime years" (within 90% of peak)
    prime_threshold = peak_performance * 0.9
    prime_ages = age_stats[age_stats['mean'] >= prime_threshold]['age_bucket'].tolist()
    prime_start = min(prime_ages) if prime_ages else peak_age
    prime_end = max(prime_ages) if prime_ages else peak_age

    result = {
        'position': position,
        'sample_size': len(pos_data),
        'peak_age': int(peak_age),
        'peak_performance': round(peak_performance, 2),
        'prime_years': [int(prime_start), int(prime_end)],
        'growth_rate_per_year': round(growth_rate, 2),
        'growth_pct_per_year': round(growth_pct, 2),
        'decline_rate_per_year': round(decline_rate, 2),
        'decline_pct_per_year': round(decline_pct, 2),
        'age_range': [int(age_stats['age_bucket'].min()), int(age_stats['age_bucket'].max())],
        'percentile_curves': percentile_curves,
        'age_stats': age_stats.to_dict('records'),
    }

    print(f"  {position}: Peak={peak_age}, Prime={prime_start}-{prime_end}, "
          f"Growth={growth_pct:.1f}%/yr, Decline={decline_pct:.1f}%/yr "
          f"(n={len(pos_data):,})")

    return result


# =============================================================================
# Potential Tiers
# =============================================================================

def compute_potential_tiers(data: pd.DataFrame, position: str, curve: Dict) -> Dict:
    """
    Compute potential tier thresholds based on early career performance.

    For players age 21-24, how does their performance predict their peak?
    """
    pos_data = data[data['position_group'] == position].copy()

    if len(pos_data) < 100:
        return None

    # Get early career performance (age 21-24)
    early_career = pos_data[pos_data['age_bucket'].between(21, 24)]

    # Get peak-age performance (within 1 year of peak)
    peak_age = curve['peak_age']
    peak_performance = pos_data[pos_data['age_bucket'].between(peak_age - 1, peak_age + 1)]

    # For players who appear in both, compute correlation
    early_by_player = early_career.groupby('gsis_id')['performance'].mean()
    peak_by_player = peak_performance.groupby('gsis_id')['performance'].mean()

    # Find players in both
    common_players = set(early_by_player.index) & set(peak_by_player.index)

    if len(common_players) < 20:
        return None

    early_vals = [early_by_player[p] for p in common_players]
    peak_vals = [peak_by_player[p] for p in common_players]

    # Compute correlation
    correlation = np.corrcoef(early_vals, peak_vals)[0, 1]

    # Compute percentile thresholds for early career performance
    early_all = early_career['performance']
    thresholds = {
        'elite': float(early_all.quantile(0.90)),      # Top 10%
        'star': float(early_all.quantile(0.75)),       # Top 25%
        'starter': float(early_all.quantile(0.50)),    # Top 50%
        'backup': float(early_all.quantile(0.25)),     # Top 75%
    }

    return {
        'early_peak_correlation': round(correlation, 3),
        'sample_size': len(common_players),
        'early_career_thresholds': thresholds,
    }


# =============================================================================
# Regression Model
# =============================================================================

def compute_decline_model(data: pd.DataFrame, position: str, curve: Dict) -> Dict:
    """
    Model performance decline after peak.

    Fits: Performance = Peak_Performance × (1 - decline_rate)^(age - peak_age)
    """
    pos_data = data[data['position_group'] == position].copy()
    peak_age = curve['peak_age']

    # Get post-peak data
    post_peak = pos_data[pos_data['age_bucket'] > peak_age]

    if len(post_peak) < 50:
        return None

    # Group by years past peak
    post_peak['years_past_peak'] = post_peak['age_bucket'] - peak_age

    decline_by_year = post_peak.groupby('years_past_peak')['performance'].agg([
        'mean', 'std', 'count'
    ]).reset_index()

    decline_by_year = decline_by_year[decline_by_year['count'] >= 10]

    if len(decline_by_year) < 3:
        return None

    # Compute year-over-year decline
    peak_perf = curve['peak_performance']

    decline_schedule = {}
    for _, row in decline_by_year.iterrows():
        years = int(row['years_past_peak'])
        remaining_pct = row['mean'] / peak_perf * 100 if peak_perf > 0 else 100
        decline_schedule[years] = round(remaining_pct, 1)

    # Compute average annual decline rate
    if len(decline_schedule) >= 2:
        years = list(decline_schedule.keys())
        pcts = list(decline_schedule.values())

        # Fit exponential: pct = 100 * (1 - r)^years
        # log(pct/100) = years * log(1 - r)
        # Solve for r
        if pcts[-1] > 0:
            avg_decline_rate = 1 - (pcts[-1] / 100) ** (1 / years[-1])
        else:
            avg_decline_rate = 0.15  # Default 15% per year
    else:
        avg_decline_rate = 0.10

    return {
        'years_past_peak_schedule': decline_schedule,
        'avg_annual_decline_rate': round(avg_decline_rate, 3),
    }


# =============================================================================
# Main Analysis
# =============================================================================

def run_development_analysis():
    """Run full development curve analysis."""
    print("=" * 60)
    print("PLAYER DEVELOPMENT CURVES ANALYSIS")
    print("=" * 60)

    # Load data
    players = load_player_ages()
    offense_perf = load_offensive_performance()
    defense_perf = load_defensive_performance()

    # Compute ages
    print("\nComputing player ages...")
    offense_data = compute_player_ages(players, offense_perf)
    defense_data = compute_player_ages(players, defense_perf)

    print(f"  Offense: {len(offense_data):,} player-seasons with age")
    print(f"  Defense: {len(defense_data):,} player-seasons with age")

    results = {
        'offense': {},
        'defense': {},
        'meta': {
            'description': 'Player development curves by position',
            'performance_metric': {
                'offense': 'fantasy_points',
                'defense': 'defensive_value',
            }
        }
    }

    # ==========================================================================
    # OFFENSE CURVES
    # ==========================================================================
    print("\n" + "=" * 60)
    print("OFFENSIVE DEVELOPMENT CURVES")
    print("=" * 60)

    for pos in OFFENSIVE_POSITIONS:
        curve = fit_career_curve(offense_data, pos)
        if curve:
            # Add potential tier analysis
            potential = compute_potential_tiers(offense_data, pos, curve)
            if potential:
                curve['potential_tiers'] = potential

            # Add decline model
            decline = compute_decline_model(offense_data, pos, curve)
            if decline:
                curve['decline_model'] = decline

            results['offense'][pos] = curve

    # ==========================================================================
    # DEFENSE CURVES
    # ==========================================================================
    print("\n" + "=" * 60)
    print("DEFENSIVE DEVELOPMENT CURVES")
    print("=" * 60)

    for pos in DEFENSIVE_POSITIONS:
        curve = fit_career_curve(defense_data, pos)
        if curve:
            # Add potential tier analysis
            potential = compute_potential_tiers(defense_data, pos, curve)
            if potential:
                curve['potential_tiers'] = potential

            # Add decline model
            decline = compute_decline_model(defense_data, pos, curve)
            if decline:
                curve['decline_model'] = decline

            results['defense'][pos] = curve

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print("\nPeak Ages by Position:")
    print("-" * 40)
    for side in ['offense', 'defense']:
        print(f"\n  {side.upper()}:")
        for pos, data in results[side].items():
            prime = data.get('prime_years', [0, 0])
            print(f"    {pos:6s}: Peak={data['peak_age']}, Prime={prime[0]}-{prime[1]}")

    print("\nGrowth & Decline Rates:")
    print("-" * 40)
    for side in ['offense', 'defense']:
        print(f"\n  {side.upper()}:")
        for pos, data in results[side].items():
            growth = data.get('growth_pct_per_year', 0)
            decline = data.get('decline_pct_per_year', 0)
            print(f"    {pos:6s}: +{growth:.1f}%/yr growth, -{decline:.1f}%/yr decline")

    # ==========================================================================
    # EXPORT
    # ==========================================================================
    print("\n" + "=" * 60)
    print("EXPORTING RESULTS")
    print("=" * 60)

    # Clean up for JSON serialization
    def clean_for_json(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(v) for v in obj]
        return obj

    results_clean = clean_for_json(results)

    # Remove verbose age_stats from export (keep percentile curves)
    for side in ['offense', 'defense']:
        for pos in results_clean[side]:
            if 'age_stats' in results_clean[side][pos]:
                del results_clean[side][pos]['age_stats']

    output_path = EXPORTS_DIR / "player_development_curves.json"
    with open(output_path, 'w') as f:
        json.dump(results_clean, f, indent=2)

    print(f"  Saved to: {output_path}")

    # Generate Python module
    generate_python_module(results_clean)

    return results


def generate_python_module(results: Dict):
    """Generate Python module for game integration."""

    output = '''"""
Player Development Curves

Auto-generated from NFL data analysis.
Provides age-based performance curves for player potential and regression.

Usage:
    from huddle.core.ai.development_curves import (
        get_peak_age,
        get_prime_years,
        get_growth_rate,
        get_decline_rate,
        project_performance,
        get_potential_tier,
    )
"""

from typing import Dict, List, Tuple, Optional


# =============================================================================
# Peak Ages and Prime Years
# =============================================================================

PEAK_AGES = {
'''

    for side in ['offense', 'defense']:
        output += f"    # {side.title()}\n"
        for pos, data in results[side].items():
            output += f"    '{pos}': {data['peak_age']},\n"

    output += '''}

PRIME_YEARS = {
'''

    for side in ['offense', 'defense']:
        output += f"    # {side.title()}\n"
        for pos, data in results[side].items():
            prime = data.get('prime_years', [data['peak_age'], data['peak_age']])
            output += f"    '{pos}': ({prime[0]}, {prime[1]}),\n"

    output += '''}


# =============================================================================
# Growth and Decline Rates (% of peak per year)
# =============================================================================

GROWTH_RATES = {
'''

    for side in ['offense', 'defense']:
        output += f"    # {side.title()}\n"
        for pos, data in results[side].items():
            rate = data.get('growth_pct_per_year', 0)
            output += f"    '{pos}': {rate},\n"

    output += '''}

DECLINE_RATES = {
'''

    for side in ['offense', 'defense']:
        output += f"    # {side.title()}\n"
        for pos, data in results[side].items():
            rate = data.get('decline_pct_per_year', 0)
            output += f"    '{pos}': {rate},\n"

    output += '''}


# =============================================================================
# Decline Schedules (% of peak remaining by years past peak)
# =============================================================================

DECLINE_SCHEDULES = {
'''

    for side in ['offense', 'defense']:
        output += f"    # {side.title()}\n"
        for pos, data in results[side].items():
            if 'decline_model' in data:
                schedule = data['decline_model'].get('years_past_peak_schedule', {})
                output += f"    '{pos}': {schedule},\n"
            else:
                output += f"    '{pos}': {{}},\n"

    output += '''}


# =============================================================================
# API Functions
# =============================================================================

def get_peak_age(position: str) -> int:
    """Get the typical peak age for a position."""
    return PEAK_AGES.get(position, 27)


def get_prime_years(position: str) -> Tuple[int, int]:
    """Get the prime years range for a position."""
    return PRIME_YEARS.get(position, (26, 28))


def get_growth_rate(position: str) -> float:
    """Get annual growth rate (% of peak) during development phase."""
    return GROWTH_RATES.get(position, 5.0)


def get_decline_rate(position: str) -> float:
    """Get annual decline rate (% of peak) after prime years."""
    return DECLINE_RATES.get(position, 5.0)


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
        position: Position group
        current_age: Current age
        current_rating: Current overall rating (0-100 scale)
        target_age: Age to project to

    Returns:
        Projected rating at target age
    """
    peak_age = get_peak_age(position)

    if target_age == current_age:
        return current_rating

    # If moving toward peak, apply growth
    if current_age < peak_age and target_age <= peak_age:
        years = target_age - current_age
        growth_rate = get_growth_rate(position) / 100
        return current_rating * (1 + growth_rate) ** years

    # If moving past peak, apply decline
    if current_age >= peak_age or target_age > peak_age:
        # First, grow to peak if needed
        if current_age < peak_age:
            years_to_peak = peak_age - current_age
            growth_rate = get_growth_rate(position) / 100
            peak_rating = current_rating * (1 + growth_rate) ** years_to_peak
            years_decline = target_age - peak_age
        else:
            peak_rating = current_rating
            years_decline = target_age - current_age

        # Then apply decline
        decline_rate = get_decline_rate(position) / 100
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
        position: Position group
        age: Current age

    Returns:
        Multiplier (1.0 = peak performance)
    """
    peak_age = get_peak_age(position)

    if age < peak_age:
        # Pre-peak: growing toward 1.0
        years_to_peak = peak_age - age
        growth_rate = get_growth_rate(position) / 100
        # Work backwards: current = peak / (1 + growth)^years
        return 1.0 / ((1 + growth_rate) ** years_to_peak)
    else:
        # Post-peak: declining from 1.0
        years_past_peak = age - peak_age

        # Use schedule if available
        schedule = DECLINE_SCHEDULES.get(position, {})
        if years_past_peak in schedule:
            return schedule[years_past_peak] / 100

        # Otherwise use rate
        decline_rate = get_decline_rate(position) / 100
        return (1 - decline_rate) ** years_past_peak
'''

    module_path = Path(__file__).parent.parent.parent / "huddle" / "core" / "ai" / "development_curves.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)

    with open(module_path, 'w') as f:
        f.write(output)

    print(f"  Saved Python module to: {module_path}")


if __name__ == "__main__":
    run_development_analysis()
