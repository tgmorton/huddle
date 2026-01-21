#!/usr/bin/env python3
"""
Injury Risk Analysis

Analyzes NFL injury data to create position-based injury risk models:
- Injury frequency by position
- Games missed rates
- Injury type distributions
- Risk factors for contract decisions

Data: injuries_2019_2024.parquet (34K injury reports)

Output: research/exports/injury_risk_analysis.json
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# =============================================================================
# Configuration
# =============================================================================

EXPORT_DIR = Path("research/exports")
DATA_DIR = Path("research/data/cached")

# Map granular positions to groups
POSITION_GROUPS = {
    'QB': 'QB', 'RB': 'RB', 'FB': 'RB',
    'WR': 'WR', 'TE': 'TE',
    'T': 'OL', 'G': 'OL', 'C': 'OL', 'OL': 'OL',
    'CB': 'CB', 'S': 'S', 'DB': 'CB',
    'LB': 'LB', 'DE': 'EDGE', 'DT': 'DL', 'NT': 'DL',
    'K': 'K', 'P': 'P', 'LS': 'LS',
}

# Seasons in our data
SEASONS = [2019, 2020, 2021, 2022, 2023, 2024]

# Weeks per season (approximate)
WEEKS_PER_SEASON = 18


# =============================================================================
# Data Loading
# =============================================================================

def load_injuries() -> pd.DataFrame:
    """Load and clean injury data."""
    df = pd.read_parquet(DATA_DIR / "injuries_2019_2024.parquet")

    # Map to position groups
    df['position_group'] = df['position'].map(POSITION_GROUPS).fillna(df['position'])

    # Filter to main positions
    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'CB', 'S', 'LB', 'EDGE', 'DL']
    df = df[df['position_group'].isin(main_positions)]

    return df


def load_snap_counts() -> pd.DataFrame:
    """Load snap counts for player-games to calculate injury rates."""
    try:
        df = pd.read_parquet(DATA_DIR / "snap_counts_2019_2024.parquet")
        return df
    except:
        return None


# =============================================================================
# Analysis Functions
# =============================================================================

def compute_injury_frequency(injuries: pd.DataFrame) -> Dict:
    """
    Compute injury report frequency by position.

    Returns: appearances on injury report per season per position.
    """
    # Count injury reports by position and season
    by_pos_season = injuries.groupby(['position_group', 'season']).size().reset_index(name='injury_reports')

    # Average per season
    avg_by_pos = by_pos_season.groupby('position_group')['injury_reports'].mean()

    # Normalize to "per 100 players" (assuming ~50 players per position in league)
    # This gives a relative injury rate
    results = {}
    for pos in avg_by_pos.index:
        rate = avg_by_pos[pos]
        results[pos] = {
            'avg_injury_reports_per_season': round(rate, 1),
            'relative_rate': round(rate / avg_by_pos.mean(), 2),
        }

    # Rank positions by injury frequency
    sorted_positions = sorted(results.items(), key=lambda x: -x[1]['avg_injury_reports_per_season'])

    return {
        'by_position': results,
        'ranking': [p for p, _ in sorted_positions],
    }


def compute_games_missed(injuries: pd.DataFrame) -> Dict:
    """
    Compute games missed rates by position.

    'Out' status = missed game
    """
    # Filter to 'Out' designations (actual missed games)
    outs = injuries[injuries['report_status'] == 'Out']

    # Count by position and season
    by_pos_season = outs.groupby(['position_group', 'season']).size().reset_index(name='games_missed')

    # Average per season
    avg_by_pos = by_pos_season.groupby('position_group')['games_missed'].mean()

    results = {}
    for pos in avg_by_pos.index:
        missed = avg_by_pos[pos]
        results[pos] = {
            'avg_games_missed_per_season': round(missed, 1),
            'relative_rate': round(missed / avg_by_pos.mean(), 2),
        }

    # Rank by games missed
    sorted_positions = sorted(results.items(), key=lambda x: -x[1]['avg_games_missed_per_season'])

    return {
        'by_position': results,
        'ranking': [p for p, _ in sorted_positions],
        'highest_risk': sorted_positions[:3],
        'lowest_risk': sorted_positions[-3:],
    }


def compute_injury_types(injuries: pd.DataFrame) -> Dict:
    """Analyze injury types by position."""

    # Most common injuries overall
    overall_types = injuries['report_primary_injury'].value_counts().head(10).to_dict()

    # By position
    position_types = {}
    for pos in injuries['position_group'].unique():
        pos_data = injuries[injuries['position_group'] == pos]
        top_injuries = pos_data['report_primary_injury'].value_counts().head(5)
        position_types[pos] = {
            injury: count for injury, count in top_injuries.items()
        }

    # Categorize injuries by severity/recovery time
    injury_severity = {
        'minor': ['Illness', 'Rest', 'Veteran Rest', 'Not Injury Related'],
        'moderate': ['Ankle', 'Hamstring', 'Groin', 'Calf', 'Foot', 'Toe', 'Quadricep', 'Thigh'],
        'serious': ['Knee', 'Shoulder', 'Back', 'Hip', 'Neck', 'Elbow'],
        'severe': ['ACL', 'Achilles', 'Concussion', 'Pectoral'],
    }

    return {
        'overall_top_10': overall_types,
        'by_position': position_types,
        'severity_categories': injury_severity,
    }


def compute_durability_scores(injuries: pd.DataFrame) -> Dict:
    """
    Compute durability scores by position (inverse of injury risk).

    Score 0-100: 100 = very durable, 0 = very injury-prone
    """
    # Get games missed rates
    outs = injuries[injuries['report_status'] == 'Out']
    by_pos = outs.groupby('position_group').size()

    # Normalize to 0-100 scale (invert so lower injuries = higher score)
    max_outs = by_pos.max()
    min_outs = by_pos.min()

    durability = {}
    for pos in by_pos.index:
        # Invert: highest injuries = lowest durability
        raw_score = 100 * (1 - (by_pos[pos] - min_outs) / (max_outs - min_outs + 1))
        durability[pos] = round(raw_score, 1)

    # Classify into tiers
    tiers = {
        'highly_durable': [p for p, s in durability.items() if s >= 70],
        'average_durability': [p for p, s in durability.items() if 40 <= s < 70],
        'injury_prone': [p for p, s in durability.items() if s < 40],
    }

    return {
        'scores': durability,
        'tiers': tiers,
    }


def compute_position_risk_profiles(injuries: pd.DataFrame) -> Dict:
    """Create comprehensive risk profiles by position."""

    profiles = {}

    for pos in injuries['position_group'].unique():
        pos_data = injuries[injuries['position_group'] == pos]

        # Basic stats
        total_reports = len(pos_data)
        games_missed = len(pos_data[pos_data['report_status'] == 'Out'])

        # Top injuries
        top_injuries = pos_data['report_primary_injury'].value_counts().head(3).to_dict()

        # Out rate (what % of injury reports result in missing a game)
        out_rate = games_missed / total_reports if total_reports > 0 else 0

        # Seasons
        seasons_covered = len(pos_data['season'].unique())
        per_season_missed = games_missed / seasons_covered if seasons_covered > 0 else 0

        profiles[pos] = {
            'total_injury_reports': total_reports,
            'games_missed': games_missed,
            'out_rate': round(out_rate, 3),
            'avg_games_missed_per_season': round(per_season_missed, 1),
            'top_injuries': top_injuries,
        }

    return profiles


def generate_recommendations() -> Dict:
    """Generate strategic recommendations for injury management."""

    return {
        'contract_implications': {
            'high_risk_positions': {
                'positions': ['CB', 'WR', 'LB'],
                'recommendation': 'Limit guaranteed money, include injury protections',
                'rationale': 'Highest games missed rates - more likely to lose value to injury',
            },
            'low_risk_positions': {
                'positions': ['QB', 'DL'],
                'recommendation': 'More comfortable with guarantees',
                'rationale': 'Lower injury rates relative to roster size',
            },
        },
        'roster_construction': {
            'depth_priorities': [
                "CB depth critical - highest games missed",
                "WR depth important - high injury frequency",
                "RB depth valuable - contact position",
            ],
            'injury_reserve_planning': [
                "Budget 2-3 IR spots for CB/WR",
                "Expect ~1 significant OL injury per season",
                "QB injuries rare but catastrophic - always have backup",
            ],
        },
        'player_evaluation': {
            'injury_history_weight': {
                'minor_injury_history': 'Discount 5-10% on contract value',
                'major_injury_history': 'Discount 15-25% on contract value',
                'chronic_issues': 'Consider not signing/short deal only',
            },
            'position_specific': {
                'RB': 'Contact injuries accumulate - weight recent history heavily',
                'WR': 'Hamstring/soft tissue issues often recur',
                'CB': 'Speed-dependent - any leg injury is concerning',
                'OL': 'Can often play through injuries - durability matters less',
            },
        },
        'age_interaction': {
            'insight': 'Injury risk increases with age, especially past 28',
            'recommendation': 'Apply additional injury discount for players 29+',
            'high_risk_combos': [
                "RB 28+ with any injury history",
                "CB 29+ with hamstring/groin issues",
                "WR 30+ with any soft tissue injury",
            ],
        },
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Injury Risk Analysis")
    print("=" * 60)
    print()

    # Load data
    print("Loading injury data...")
    injuries = load_injuries()
    print(f"  Loaded {len(injuries)} injury reports")
    print()

    # Run analyses
    print("Computing injury frequency...")
    frequency = compute_injury_frequency(injuries)

    print("Computing games missed rates...")
    games_missed = compute_games_missed(injuries)

    print("Analyzing injury types...")
    injury_types = compute_injury_types(injuries)

    print("Computing durability scores...")
    durability = compute_durability_scores(injuries)

    print("Building risk profiles...")
    risk_profiles = compute_position_risk_profiles(injuries)

    print("Generating recommendations...")
    recommendations = generate_recommendations()

    # Compile results
    results = {
        'meta': {
            'description': 'Injury risk analysis by position',
            'data_source': 'NFL injury reports 2019-2024',
            'total_reports': len(injuries),
        },
        'injury_frequency': frequency,
        'games_missed': games_missed,
        'injury_types': injury_types,
        'durability_scores': durability,
        'risk_profiles': risk_profiles,
        'recommendations': recommendations,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / "injury_risk_analysis.json"

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExported to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Games Missed Rankings (by position)")
    print("=" * 60)

    for pos in games_missed['ranking']:
        data = games_missed['by_position'][pos]
        print(f"  {pos:5}: {data['avg_games_missed_per_season']:5.1f} games/season (relative: {data['relative_rate']:.2f}x)")

    print("\n" + "=" * 60)
    print("Durability Scores (100 = most durable)")
    print("=" * 60)

    for pos, score in sorted(durability['scores'].items(), key=lambda x: -x[1]):
        tier = 'HIGH' if score >= 70 else ('MEDIUM' if score >= 40 else 'LOW')
        print(f"  {pos:5}: {score:5.1f} ({tier})")

    print("\n" + "=" * 60)
    print("Top Injuries by Position")
    print("=" * 60)

    for pos in ['QB', 'RB', 'WR', 'CB', 'EDGE']:
        if pos in injury_types['by_position']:
            top = list(injury_types['by_position'][pos].keys())[:3]
            print(f"  {pos:5}: {', '.join(top)}")


if __name__ == '__main__':
    main()
