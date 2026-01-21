#!/usr/bin/env python3
"""
Draft Value Analysis

Analyzes NFL draft data to create models for:
1. Expected value curves by draft pick
2. Hit rates and variance by position/round
3. Scouting error distributions
4. Development timelines
5. Prospect generation lookup tables

Data sources:
- contracts.parquet: Draft position, player info
- seasonal_stats.parquet: Offensive performance (fantasy points)
- defensive_value.parquet: Defensive performance (DV metric)

Output: research/exports/draft_value_analysis.json
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path("research/data/cached")
EXPORT_DIR = Path("research/exports")

# Position groupings
OFFENSE_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OL', 'T', 'G', 'C']
DEFENSE_POSITIONS = ['CB', 'S', 'LB', 'EDGE', 'DL', 'DE', 'DT', 'NT', 'ILB', 'OLB', 'FS', 'SS']

# Map granular positions to groups
POSITION_GROUPS = {
    # Offense
    'QB': 'QB', 'RB': 'RB', 'FB': 'RB',
    'WR': 'WR', 'TE': 'TE',
    'T': 'OL', 'OT': 'OL', 'LT': 'OL', 'RT': 'OL',
    'G': 'OL', 'OG': 'OL', 'LG': 'OL', 'RG': 'OL',
    'C': 'OL', 'OL': 'OL',
    # Defense
    'CB': 'CB', 'DB': 'CB',
    'S': 'S', 'FS': 'S', 'SS': 'S', 'SAF': 'S',
    'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB', 'OLB': 'LB',
    'EDGE': 'EDGE', 'DE': 'EDGE', 'ED': 'EDGE',  # ED is OTC format
    'DL': 'DL', 'DT': 'DL', 'NT': 'DL', 'IDL': 'DL',  # IDL is OTC format
}

# Years of data we have performance for
PERFORMANCE_YEARS = range(2019, 2025)

# Fantasy point weights for offense
FANTASY_WEIGHTS = {
    'passing_yards': 0.04,
    'passing_tds': 4,
    'interceptions': -2,
    'rushing_yards': 0.1,
    'rushing_tds': 6,
    'receiving_yards': 0.1,
    'receiving_tds': 6,
    'receptions': 1,  # PPR
}


# =============================================================================
# Data Loading
# =============================================================================

def load_contracts() -> pd.DataFrame:
    """Load and clean contracts data."""
    df = pd.read_parquet(DATA_DIR / "contracts.parquet")

    # Filter to drafted players
    df = df.dropna(subset=['draft_year', 'draft_round', 'draft_overall'])

    # Clean up position groups
    df['position_group'] = df['position'].map(POSITION_GROUPS).fillna(df['position'])

    # Convert types
    df['draft_year'] = df['draft_year'].astype(int)
    df['draft_round'] = df['draft_round'].astype(int)
    df['draft_overall'] = df['draft_overall'].astype(int)

    return df


def load_offensive_performance() -> pd.DataFrame:
    """Load offensive stats and compute fantasy points."""
    df = pd.read_parquet(DATA_DIR / "seasonal_stats.parquet")

    # Filter to regular season
    df = df[df['season_type'] == 'REG']

    # Compute fantasy points
    fantasy_points = 0
    for col, weight in FANTASY_WEIGHTS.items():
        if col in df.columns:
            fantasy_points += df[col].fillna(0) * weight

    df['fantasy_points'] = fantasy_points

    # Aggregate by player and season
    result = df.groupby(['player_id', 'season']).agg({
        'fantasy_points': 'sum',
        'attempts': 'sum',  # passing attempts
        'rushing_yards': 'sum',
        'receiving_yards': 'sum',
    }).reset_index()

    return result


def load_defensive_performance() -> pd.DataFrame:
    """Load defensive value data."""
    df = pd.read_parquet(DATA_DIR / "defensive_value.parquet")
    return df[['player_id', 'season', 'defensive_value', 'position_group']]


def join_draft_with_performance(
    contracts: pd.DataFrame,
    offensive: pd.DataFrame,
    defensive: pd.DataFrame
) -> pd.DataFrame:
    """Join draft info with career performance."""

    # Create player-level summary from contracts
    players = contracts.groupby('gsis_id').agg({
        'player': 'first',
        'position': 'first',
        'position_group': 'first',
        'draft_year': 'first',
        'draft_round': 'first',
        'draft_overall': 'first',
    }).reset_index()

    # Join with offensive performance
    off_perf = offensive.groupby('player_id').agg({
        'fantasy_points': ['sum', 'max', 'mean', 'count'],
    }).reset_index()
    off_perf.columns = ['player_id', 'career_fp', 'peak_fp', 'avg_fp', 'seasons_played']

    players = players.merge(
        off_perf,
        left_on='gsis_id',
        right_on='player_id',
        how='left'
    )

    # Join with defensive performance
    def_perf = defensive.groupby('player_id').agg({
        'defensive_value': ['sum', 'max', 'mean', 'count'],
    }).reset_index()
    def_perf.columns = ['player_id', 'career_dv', 'peak_dv', 'avg_dv', 'def_seasons']

    players = players.merge(
        def_perf,
        left_on='gsis_id',
        right_on='player_id',
        how='left',
        suffixes=('', '_def')
    )

    # Use appropriate performance metric based on side of ball
    def get_performance(row):
        pos = row['position_group']
        if pos in ['QB', 'RB', 'WR', 'TE', 'OL']:
            return row['career_fp'] if pd.notna(row['career_fp']) else 0
        else:
            return row['career_dv'] if pd.notna(row['career_dv']) else 0

    def get_peak(row):
        pos = row['position_group']
        if pos in ['QB', 'RB', 'WR', 'TE', 'OL']:
            return row['peak_fp'] if pd.notna(row['peak_fp']) else 0
        else:
            return row['peak_dv'] if pd.notna(row['peak_dv']) else 0

    players['career_value'] = players.apply(get_performance, axis=1)
    players['peak_value'] = players.apply(get_peak, axis=1)

    # Get seasons played (use max of offense/defense)
    players['seasons'] = players[['seasons_played', 'def_seasons']].max(axis=1).fillna(0)

    return players


# =============================================================================
# Analysis Functions
# =============================================================================

def compute_pick_value_curve(players: pd.DataFrame) -> Dict:
    """
    Compute expected career value by draft pick.

    Returns value curve with uncertainty bands.
    """
    # Filter to recent drafts with enough time to evaluate
    # Only include 2015-2021 drafts (at least 3 years of data possible)
    recent = players[
        (players['draft_year'] >= 2015) &
        (players['draft_year'] <= 2021) &
        (players['draft_overall'] <= 256)
    ].copy()

    print(f"Analyzing {len(recent)} players from 2015-2021 drafts")

    # Group by pick ranges for smoothing
    pick_buckets = [
        (1, 5, "Top 5"),
        (6, 10, "6-10"),
        (11, 15, "11-15"),
        (16, 20, "16-20"),
        (21, 32, "Late 1st"),
        (33, 64, "2nd Round"),
        (65, 100, "3rd Round"),
        (101, 150, "4th-5th"),
        (151, 200, "5th-6th"),
        (201, 256, "7th Round"),
    ]

    curve = {}
    for start, end, label in pick_buckets:
        bucket = recent[(recent['draft_overall'] >= start) & (recent['draft_overall'] <= end)]
        if len(bucket) > 5:
            values = bucket['career_value'].values
            curve[label] = {
                'pick_range': [start, end],
                'n_players': len(bucket),
                'mean_value': float(np.mean(values)),
                'median_value': float(np.median(values)),
                'std_value': float(np.std(values)),
                'p25': float(np.percentile(values, 25)),
                'p75': float(np.percentile(values, 75)),
                'p90': float(np.percentile(values, 90)),
            }

    # Also compute per-pick values for top 50
    per_pick = {}
    for pick in range(1, 51):
        bucket = recent[recent['draft_overall'] == pick]
        if len(bucket) >= 3:
            values = bucket['career_value'].values
            per_pick[str(pick)] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'n': len(bucket),
            }

    return {
        'by_bucket': curve,
        'by_pick': per_pick,
    }


def compute_hit_rates(players: pd.DataFrame) -> Dict:
    """
    Compute hit rates by round and position.

    "Hit" = starter-level performance or better.
    "Star" = top-tier performance.
    "Bust" = minimal career value.
    """
    recent = players[
        (players['draft_year'] >= 2015) &
        (players['draft_year'] <= 2021)
    ].copy()

    # Define thresholds by position (based on distribution)
    position_thresholds = {}
    for pos in recent['position_group'].unique():
        pos_data = recent[recent['position_group'] == pos]['career_value']
        if len(pos_data) >= 10:
            position_thresholds[pos] = {
                'bust': float(np.percentile(pos_data, 25)),
                'starter': float(np.percentile(pos_data, 50)),
                'star': float(np.percentile(pos_data, 85)),
            }

    # Compute hit rates by round and position
    results = {}
    for round_num in range(1, 8):
        round_data = recent[recent['draft_round'] == round_num]

        round_results = {
            'total_picks': len(round_data),
            'by_position': {},
        }

        for pos in round_data['position_group'].unique():
            if pos not in position_thresholds:
                continue

            pos_round = round_data[round_data['position_group'] == pos]
            if len(pos_round) < 5:
                continue

            thresholds = position_thresholds[pos]
            values = pos_round['career_value'].values

            # Calculate rates
            n = len(values)
            busts = sum(values <= thresholds['bust']) / n
            starters = sum(values >= thresholds['starter']) / n
            stars = sum(values >= thresholds['star']) / n

            round_results['by_position'][pos] = {
                'n': n,
                'bust_rate': round(busts, 3),
                'starter_rate': round(starters, 3),
                'star_rate': round(stars, 3),
            }

        results[f'round_{round_num}'] = round_results

    return {
        'thresholds': position_thresholds,
        'rates': results,
    }


def compute_position_variance(players: pd.DataFrame) -> Dict:
    """
    Compute outcome variance by position.

    Higher variance = more boom/bust potential.
    """
    recent = players[
        (players['draft_year'] >= 2015) &
        (players['draft_year'] <= 2021)
    ].copy()

    results = {}
    for pos in recent['position_group'].unique():
        pos_data = recent[recent['position_group'] == pos]
        if len(pos_data) < 20:
            continue

        values = pos_data['career_value'].values
        peaks = pos_data['peak_value'].values

        # Coefficient of variation (normalized variance)
        cv = np.std(values) / (np.mean(values) + 1e-6)

        # Skewness (positive = more upside outliers)
        skew = float(stats.skew(values))

        # Boom rate (top 10% performers)
        boom_threshold = np.percentile(values, 90)
        boom_rate = sum(values >= boom_threshold) / len(values)

        # Bust rate (bottom 25%)
        bust_threshold = np.percentile(values, 25)
        bust_rate = sum(values <= bust_threshold) / len(values)

        results[pos] = {
            'n': len(pos_data),
            'mean_value': float(np.mean(values)),
            'std_value': float(np.std(values)),
            'cv': float(cv),
            'skewness': skew,
            'boom_rate': round(boom_rate, 3),
            'bust_rate': round(bust_rate, 3),
            'peak_mean': float(np.mean(peaks)),
            'peak_std': float(np.std(peaks)),
        }

    # Rank positions by variance
    sorted_by_cv = sorted(results.items(), key=lambda x: x[1]['cv'], reverse=True)

    return {
        'by_position': results,
        'variance_ranking': [pos for pos, _ in sorted_by_cv],
    }


def compute_scouting_error(players: pd.DataFrame) -> Dict:
    """
    Model scouting error: difference between draft position and actual value.

    This helps us generate realistic uncertainty in prospect evaluations.
    """
    recent = players[
        (players['draft_year'] >= 2015) &
        (players['draft_year'] <= 2021) &
        (players['draft_overall'] <= 256) &
        (players['career_value'] > 0)
    ].copy()

    # Compute expected value by pick (from actual performance)
    pick_value = recent.groupby('draft_overall')['career_value'].mean()

    # For each player, compute residual (actual - expected)
    recent['expected_value'] = recent['draft_overall'].map(pick_value)
    recent['residual'] = recent['career_value'] - recent['expected_value']
    recent['relative_error'] = recent['residual'] / (recent['expected_value'] + 1e-6)

    # Analyze error distribution by round
    results = {
        'by_round': {},
        'by_position': {},
    }

    for round_num in range(1, 8):
        round_data = recent[recent['draft_round'] == round_num]
        if len(round_data) < 10:
            continue

        residuals = round_data['residual'].values
        rel_errors = round_data['relative_error'].values

        results['by_round'][f'round_{round_num}'] = {
            'n': len(round_data),
            'mean_residual': float(np.mean(residuals)),
            'std_residual': float(np.std(residuals)),
            'mean_relative_error': float(np.mean(rel_errors)),
            'std_relative_error': float(np.std(rel_errors)),
            'p10_error': float(np.percentile(rel_errors, 10)),
            'p90_error': float(np.percentile(rel_errors, 90)),
        }

    # By position
    for pos in recent['position_group'].unique():
        pos_data = recent[recent['position_group'] == pos]
        if len(pos_data) < 20:
            continue

        rel_errors = pos_data['relative_error'].values

        results['by_position'][pos] = {
            'n': len(pos_data),
            'mean_error': float(np.mean(rel_errors)),
            'std_error': float(np.std(rel_errors)),
            'p10': float(np.percentile(rel_errors, 10)),
            'p90': float(np.percentile(rel_errors, 90)),
        }

    return results


def compute_development_timeline(players: pd.DataFrame, offensive: pd.DataFrame, defensive: pd.DataFrame) -> Dict:
    """
    Compute time-to-impact by position and round.

    How many seasons until a player reaches their peak?
    """
    # Get per-season data for each player
    contracts = players[['gsis_id', 'position_group', 'draft_year', 'draft_round', 'draft_overall']].copy()

    # Combine offensive and defensive per-season data
    off_seasons = offensive.copy()
    off_seasons['value'] = off_seasons['fantasy_points']
    off_seasons = off_seasons[['player_id', 'season', 'value']]

    def_seasons = defensive.copy()
    def_seasons['value'] = def_seasons['defensive_value']
    def_seasons = def_seasons[['player_id', 'season', 'value']]

    all_seasons = pd.concat([off_seasons, def_seasons], ignore_index=True)

    # Join with draft info
    seasons = all_seasons.merge(
        contracts,
        left_on='player_id',
        right_on='gsis_id',
        how='inner'
    )

    # Compute career year
    seasons['career_year'] = seasons['season'] - seasons['draft_year'] + 1

    # Filter to reasonable career years
    seasons = seasons[(seasons['career_year'] >= 1) & (seasons['career_year'] <= 10)]

    # Find peak year for each player
    player_peaks = seasons.groupby('player_id').agg({
        'value': 'max',
        'position_group': 'first',
        'draft_round': 'first',
    }).reset_index()

    # For each player, find when they hit peak
    def find_peak_year(group):
        peak_val = group['value'].max()
        peak_rows = group[group['value'] == peak_val]
        return peak_rows['career_year'].min()

    peak_years = seasons.groupby('player_id').apply(find_peak_year).reset_index()
    peak_years.columns = ['player_id', 'peak_career_year']

    # Join back
    player_peaks = player_peaks.merge(peak_years, on='player_id')

    # Analyze by position and round
    results = {
        'by_position': {},
        'by_round': {},
    }

    for pos in player_peaks['position_group'].unique():
        pos_data = player_peaks[player_peaks['position_group'] == pos]
        if len(pos_data) < 10:
            continue

        peak_years = pos_data['peak_career_year'].values
        results['by_position'][pos] = {
            'n': len(pos_data),
            'mean_peak_year': float(np.mean(peak_years)),
            'median_peak_year': float(np.median(peak_years)),
            'std_peak_year': float(np.std(peak_years)),
            'early_peak_rate': float(sum(peak_years <= 2) / len(peak_years)),  # Peaks in first 2 years
            'late_peak_rate': float(sum(peak_years >= 4) / len(peak_years)),   # Peaks after year 4
        }

    for round_num in range(1, 8):
        round_data = player_peaks[player_peaks['draft_round'] == round_num]
        if len(round_data) < 10:
            continue

        peak_years = round_data['peak_career_year'].values
        results['by_round'][f'round_{round_num}'] = {
            'n': len(round_data),
            'mean_peak_year': float(np.mean(peak_years)),
            'median_peak_year': float(np.median(peak_years)),
        }

    return results


def generate_prospect_tables(
    hit_rates: Dict,
    variance: Dict,
    scouting_error: Dict,
    timeline: Dict
) -> Dict:
    """
    Generate lookup tables for prospect generation.

    These tables can be used directly in the game to generate
    realistic draft prospects with appropriate uncertainty.
    """

    # Outcome probabilities by round and position
    outcomes = {}
    for round_key, round_data in hit_rates['rates'].items():
        outcomes[round_key] = {}
        for pos, pos_data in round_data.get('by_position', {}).items():
            outcomes[round_key][pos] = {
                'bust': pos_data['bust_rate'],
                'role_player': round(1 - pos_data['bust_rate'] - pos_data['starter_rate'], 3),
                'starter': round(pos_data['starter_rate'] - pos_data['star_rate'], 3),
                'star': pos_data['star_rate'],
            }

    # Variance descriptors
    variance_tiers = {
        'high': [],   # CV > 1.5
        'medium': [], # CV 1.0-1.5
        'low': [],    # CV < 1.0
    }
    for pos, data in variance['by_position'].items():
        cv = data['cv']
        if cv > 1.5:
            variance_tiers['high'].append(pos)
        elif cv > 1.0:
            variance_tiers['medium'].append(pos)
        else:
            variance_tiers['low'].append(pos)

    # Scouting error parameters for generating hidden talent
    error_params = {}
    for pos, data in scouting_error['by_position'].items():
        error_params[pos] = {
            'mean': data['mean_error'],
            'std': data['std_error'],
            'range': [data['p10'], data['p90']],
        }

    # Development speed by position
    development = {}
    for pos, data in timeline.get('by_position', {}).items():
        mean_peak = data['mean_peak_year']
        # Based on actual data: most players peak around year 3-4
        # "fast" = above average early contribution
        # "slow" = below average early contribution
        if mean_peak <= 3.0:
            speed = 'fast'
        elif mean_peak <= 4.0:
            speed = 'normal'
        else:
            speed = 'slow'

        development[pos] = {
            'speed': speed,
            'mean_peak_year': mean_peak,
            'early_contributor_rate': data.get('early_peak_rate', 0),
        }

    return {
        'outcome_probabilities': outcomes,
        'variance_tiers': variance_tiers,
        'scouting_error': error_params,
        'development_speed': development,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Draft Value Analysis")
    print("=" * 60)
    print()

    # Load data
    print("Loading data...")
    contracts = load_contracts()
    print(f"  Contracts: {len(contracts)} drafted players")

    offensive = load_offensive_performance()
    print(f"  Offensive: {len(offensive)} player-seasons")

    defensive = load_defensive_performance()
    print(f"  Defensive: {len(defensive)} player-seasons")
    print()

    # Join data
    print("Joining draft with performance...")
    players = join_draft_with_performance(contracts, offensive, defensive)
    players_with_perf = players[players['career_value'] > 0]
    print(f"  Players with performance data: {len(players_with_perf)}")
    print()

    # Run analyses
    print("Computing pick value curve...")
    pick_curve = compute_pick_value_curve(players_with_perf)
    print(f"  Analyzed {len(pick_curve['by_bucket'])} pick buckets")

    print("Computing hit rates...")
    hit_rates = compute_hit_rates(players_with_perf)
    print(f"  Analyzed {len(hit_rates['rates'])} rounds")

    print("Computing position variance...")
    variance = compute_position_variance(players_with_perf)
    print(f"  High variance positions: {variance['variance_ranking'][:3]}")

    print("Computing scouting error...")
    scouting_error = compute_scouting_error(players_with_perf)
    print(f"  Analyzed {len(scouting_error['by_position'])} positions")

    print("Computing development timeline...")
    timeline = compute_development_timeline(players, offensive, defensive)
    print(f"  Analyzed {len(timeline['by_position'])} positions")
    print()

    # Generate lookup tables
    print("Generating prospect tables...")
    prospect_tables = generate_prospect_tables(hit_rates, variance, scouting_error, timeline)

    # Compile results
    results = {
        'meta': {
            'description': 'Draft value analysis for prospect generation',
            'data_years': '2015-2021 drafts with 2019-2024 performance',
            'n_players': len(players_with_perf),
        },
        'pick_value_curve': pick_curve,
        'hit_rates': hit_rates,
        'position_variance': variance,
        'scouting_error': scouting_error,
        'development_timeline': timeline,
        'prospect_tables': prospect_tables,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / "draft_value_analysis.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Exported to {output_path}")
    print()

    # Print summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()

    print("Pick Value by Bucket:")
    for bucket, data in pick_curve['by_bucket'].items():
        print(f"  {bucket}: mean={data['mean_value']:.1f}, std={data['std_value']:.1f}")
    print()

    print("High Variance Positions (boom/bust):")
    for pos in variance['variance_ranking'][:5]:
        data = variance['by_position'][pos]
        print(f"  {pos}: CV={data['cv']:.2f}, boom={data['boom_rate']:.1%}, bust={data['bust_rate']:.1%}")
    print()

    print("Development Speed:")
    for pos, data in prospect_tables['development_speed'].items():
        print(f"  {pos}: {data['speed']} (peak year {data['mean_peak_year']:.1f})")


if __name__ == '__main__':
    main()
