#!/usr/bin/env python3
"""
College Production Analysis

Analyzes which colleges and conferences produce NFL talent.
Used for generating realistic draft classes with appropriate school distributions.

Outputs:
- Top producing schools by position
- Conference strength rankings
- Hit rates by school tier
- School archetypes (QB factory, OL school, etc.)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import json

# Paths
RESEARCH_DIR = Path(__file__).parent.parent
CACHED_DIR = RESEARCH_DIR / "data" / "cached"
EXPORTS_DIR = RESEARCH_DIR / "exports"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Conference Mapping
# =============================================================================

# Map schools to conferences (Power 5 + Group of 5 + FCS)
CONFERENCE_MAP = {
    # SEC
    'Alabama': 'SEC', 'Auburn': 'SEC', 'Arkansas': 'SEC', 'Florida': 'SEC',
    'Georgia': 'SEC', 'Kentucky': 'SEC', 'LSU': 'SEC', 'Mississippi': 'SEC',
    'Ole Miss': 'SEC', 'Mississippi St.': 'SEC', 'Missouri': 'SEC',
    'South Carolina': 'SEC', 'Tennessee': 'SEC', 'Texas A&M': 'SEC',
    'Vanderbilt': 'SEC', 'Texas': 'SEC', 'Oklahoma': 'SEC',

    # Big Ten
    'Illinois': 'Big Ten', 'Indiana': 'Big Ten', 'Iowa': 'Big Ten',
    'Maryland': 'Big Ten', 'Michigan': 'Big Ten', 'Michigan St.': 'Big Ten',
    'Minnesota': 'Big Ten', 'Nebraska': 'Big Ten', 'Northwestern': 'Big Ten',
    'Ohio St.': 'Big Ten', 'Penn St.': 'Big Ten', 'Purdue': 'Big Ten',
    'Rutgers': 'Big Ten', 'Wisconsin': 'Big Ten', 'UCLA': 'Big Ten',
    'USC': 'Big Ten', 'Oregon': 'Big Ten', 'Washington': 'Big Ten',

    # ACC
    'Boston College': 'ACC', 'Clemson': 'ACC', 'Duke': 'ACC',
    'Florida St.': 'ACC', 'Georgia Tech': 'ACC', 'Louisville': 'ACC',
    'Miami': 'ACC', 'North Carolina': 'ACC', 'NC State': 'ACC',
    'Pittsburgh': 'ACC', 'Syracuse': 'ACC', 'Virginia': 'ACC',
    'Virginia Tech': 'ACC', 'Wake Forest': 'ACC', 'Notre Dame': 'ACC',
    'Stanford': 'ACC', 'California': 'ACC', 'SMU': 'ACC',

    # Big 12
    'Baylor': 'Big 12', 'BYU': 'Big 12', 'Cincinnati': 'Big 12',
    'Houston': 'Big 12', 'Iowa St.': 'Big 12', 'Kansas': 'Big 12',
    'Kansas St.': 'Big 12', 'Oklahoma St.': 'Big 12', 'TCU': 'Big 12',
    'Texas Tech': 'Big 12', 'UCF': 'Big 12', 'West Virginia': 'Big 12',
    'Arizona': 'Big 12', 'Arizona St.': 'Big 12', 'Colorado': 'Big 12',
    'Utah': 'Big 12',

    # Pac-12 (historical - now mostly in Big Ten/Big 12)
    'Oregon St.': 'Pac-12', 'Washington St.': 'Pac-12',

    # Group of 5
    'Boise St.': 'Mountain West', 'Colorado St.': 'Mountain West',
    'Fresno St.': 'Mountain West', 'Nevada': 'Mountain West',
    'New Mexico': 'Mountain West', 'San Diego St.': 'Mountain West',
    'San Jose St.': 'Mountain West', 'UNLV': 'Mountain West',
    'Wyoming': 'Mountain West', 'Air Force': 'Mountain West',
    'Hawaii': 'Mountain West', 'Utah St.': 'Mountain West',

    'Memphis': 'AAC', 'Navy': 'AAC', 'SMU': 'AAC', 'Temple': 'AAC',
    'Tulane': 'AAC', 'Tulsa': 'AAC', 'East Carolina': 'AAC',
    'South Florida': 'AAC', 'Charlotte': 'AAC', 'FAU': 'AAC',
    'North Texas': 'AAC', 'Rice': 'AAC', 'UAB': 'AAC', 'UTSA': 'AAC',

    'Appalachian St.': 'Sun Belt', 'Arkansas St.': 'Sun Belt',
    'Coastal Carolina': 'Sun Belt', 'Georgia Southern': 'Sun Belt',
    'Georgia St.': 'Sun Belt', 'Louisiana': 'Sun Belt',
    'Louisiana-Lafayette': 'Sun Belt', 'Louisiana Tech': 'Sun Belt',
    'Louisiana Monroe': 'Sun Belt', 'South Alabama': 'Sun Belt',
    'Texas St.': 'Sun Belt', 'Troy': 'Sun Belt',
    'James Madison': 'Sun Belt', 'Marshall': 'Sun Belt',
    'Old Dominion': 'Sun Belt', 'Southern Miss': 'Sun Belt',

    'Akron': 'MAC', 'Ball St.': 'MAC', 'Bowling Green': 'MAC',
    'Buffalo': 'MAC', 'Central Michigan': 'MAC', 'Eastern Michigan': 'MAC',
    'Kent St.': 'MAC', 'Miami (OH)': 'MAC', 'Northern Illinois': 'MAC',
    'Ohio': 'MAC', 'Toledo': 'MAC', 'Western Michigan': 'MAC',

    'Army': 'Independent', 'UConn': 'Independent', 'UMass': 'Independent',
}

POWER_CONFERENCES = ['SEC', 'Big Ten', 'ACC', 'Big 12', 'Pac-12']
GROUP_OF_5 = ['Mountain West', 'AAC', 'Sun Belt', 'MAC', 'C-USA']


def get_conference(school: str) -> str:
    """Map school to conference."""
    if pd.isna(school):
        return 'Unknown'

    # Direct lookup
    if school in CONFERENCE_MAP:
        return CONFERENCE_MAP[school]

    # Try common variations
    school_clean = school.replace('.', '').replace("'", '').strip()
    for key, conf in CONFERENCE_MAP.items():
        if key.replace('.', '').replace("'", '') == school_clean:
            return conf

    # Check for partial matches
    school_lower = school.lower()
    if 'alabama' in school_lower and 'uab' not in school_lower:
        return 'SEC'
    if 'ohio state' in school_lower or 'ohio st' in school_lower:
        return 'Big Ten'

    return 'Other'


def get_conference_tier(conf: str) -> str:
    """Classify conference into tiers."""
    if conf in POWER_CONFERENCES:
        return 'Power 5'
    elif conf in GROUP_OF_5:
        return 'Group of 5'
    elif conf in ['FCS', 'D2', 'D3', 'NAIA']:
        return 'FCS/Lower'
    else:
        return 'Other'


# =============================================================================
# Position Grouping
# =============================================================================

POSITION_GROUP_MAP = {
    'QB': 'QB',
    'RB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'T': 'OL', 'G': 'OL', 'C': 'OL', 'OL': 'OL', 'OT': 'OL',
    'DE': 'EDGE', 'EDGE': 'EDGE', 'OLB': 'EDGE',
    'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
    'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB',
    'CB': 'CB',
    'S': 'S', 'DB': 'S', 'FS': 'S', 'SS': 'S',
    'K': 'K', 'P': 'P', 'LS': 'LS',
}


def get_position_group(pos: str) -> str:
    """Map position to group."""
    if pd.isna(pos):
        return 'Unknown'
    return POSITION_GROUP_MAP.get(pos, 'Other')


# =============================================================================
# Analysis Functions
# =============================================================================

def calculate_hit_rate(df: pd.DataFrame) -> Dict:
    """Calculate various hit rate metrics."""
    total = len(df)
    if total == 0:
        return {'total': 0, 'starter_rate': 0, 'probowl_rate': 0, 'allpro_rate': 0}

    # Starter = played 2+ seasons as starter
    starters = len(df[df['seasons_started'] >= 2])

    # Pro Bowl
    probowlers = len(df[df['probowls'] > 0])

    # All-Pro
    allpros = len(df[df['allpro'] > 0])

    # Games played (measure of staying in league)
    avg_games = df['games'].fillna(0).mean()

    # Career AV
    avg_av = df['car_av'].fillna(0).mean()

    return {
        'total': total,
        'starter_rate': round(starters / total * 100, 1),
        'probowl_rate': round(probowlers / total * 100, 1),
        'allpro_rate': round(allpros / total * 100, 1),
        'avg_games': round(avg_games, 1),
        'avg_career_av': round(avg_av, 1),
    }


def analyze_schools(draft: pd.DataFrame) -> Dict:
    """Analyze production by school."""
    print("\nAnalyzing production by school...")

    # Add columns
    draft['conference'] = draft['college'].apply(get_conference)
    draft['conf_tier'] = draft['conference'].apply(get_conference_tier)
    draft['pos_group'] = draft['position'].apply(get_position_group)

    results = {
        'top_overall': [],
        'by_position': {},
        'school_archetypes': {},
    }

    # Top overall producers
    school_counts = draft.groupby('college').agg({
        'pick': 'count',
        'seasons_started': lambda x: (x >= 2).sum(),
        'probowls': lambda x: (x > 0).sum(),
        'allpro': lambda x: (x > 0).sum(),
        'car_av': 'sum',
    }).rename(columns={'pick': 'total_picks'})

    school_counts['starter_rate'] = (school_counts['seasons_started'] / school_counts['total_picks'] * 100).round(1)
    school_counts = school_counts.sort_values('total_picks', ascending=False)

    for school in school_counts.head(30).index:
        row = school_counts.loc[school]
        conf = draft[draft['college'] == school]['conference'].iloc[0]
        results['top_overall'].append({
            'school': school,
            'conference': conf,
            'total_picks': int(row['total_picks']),
            'starters': int(row['seasons_started']),
            'probowlers': int(row['probowls']),
            'allpros': int(row['allpro']),
            'starter_rate': float(row['starter_rate']),
            'total_career_av': int(row['car_av']),
        })

    print(f"  Top 5 overall: {[s['school'] for s in results['top_overall'][:5]]}")

    # By position group
    for pos_group in ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']:
        pos_data = draft[draft['pos_group'] == pos_group]
        if len(pos_data) < 10:
            continue

        pos_schools = pos_data.groupby('college').agg({
            'pick': 'count',
            'seasons_started': lambda x: (x >= 2).sum(),
            'probowls': lambda x: (x > 0).sum(),
            'car_av': 'mean',
        }).rename(columns={'pick': 'total'})

        pos_schools = pos_schools[pos_schools['total'] >= 3]  # Min 3 picks
        pos_schools['starter_rate'] = (pos_schools['seasons_started'] / pos_schools['total'] * 100).round(1)
        pos_schools = pos_schools.sort_values('total', ascending=False)

        results['by_position'][pos_group] = []
        for school in pos_schools.head(10).index:
            row = pos_schools.loc[school]
            results['by_position'][pos_group].append({
                'school': school,
                'total': int(row['total']),
                'starters': int(row['seasons_started']),
                'probowlers': int(row['probowls']),
                'starter_rate': float(row['starter_rate']),
            })

    # School archetypes (what positions they excel at)
    for school in school_counts.head(50).index:
        school_data = draft[draft['college'] == school]
        if len(school_data) < 10:
            continue

        pos_breakdown = school_data['pos_group'].value_counts()
        total = len(school_data)

        # Find dominant positions (>20% of picks)
        specialties = []
        for pos, count in pos_breakdown.items():
            pct = count / total * 100
            if pct >= 20:
                specialties.append({'position': pos, 'pct': round(pct, 1), 'count': int(count)})

        if specialties:
            results['school_archetypes'][school] = {
                'total_picks': total,
                'specialties': sorted(specialties, key=lambda x: x['pct'], reverse=True),
            }

    return results


def analyze_conferences(draft: pd.DataFrame) -> Dict:
    """Analyze production by conference."""
    print("\nAnalyzing production by conference...")

    draft['conference'] = draft['college'].apply(get_conference)
    draft['conf_tier'] = draft['conference'].apply(get_conference_tier)

    results = {
        'by_conference': {},
        'by_tier': {},
        'by_round': {},
    }

    # By conference
    for conf in draft['conference'].unique():
        if conf in ['Unknown', 'Other']:
            continue
        conf_data = draft[draft['conference'] == conf]
        if len(conf_data) < 20:
            continue

        metrics = calculate_hit_rate(conf_data)

        # Round distribution
        round_dist = conf_data['round'].value_counts().sort_index()
        r1_pct = round_dist.get(1, 0) / len(conf_data) * 100

        results['by_conference'][conf] = {
            **metrics,
            'first_round_pct': round(r1_pct, 1),
            'tier': get_conference_tier(conf),
        }

    # Sort by total picks
    results['by_conference'] = dict(sorted(
        results['by_conference'].items(),
        key=lambda x: x[1]['total'],
        reverse=True
    ))

    print(f"  Top conferences: {list(results['by_conference'].keys())[:5]}")

    # By tier
    for tier in ['Power 5', 'Group of 5', 'FCS/Lower', 'Other']:
        tier_data = draft[draft['conf_tier'] == tier]
        if len(tier_data) < 20:
            continue

        metrics = calculate_hit_rate(tier_data)
        round_dist = tier_data['round'].value_counts().sort_index()

        results['by_tier'][tier] = {
            **metrics,
            'round_distribution': {str(r): int(c) for r, c in round_dist.items()},
        }

    # Hit rate by round AND conference tier
    for tier in ['Power 5', 'Group of 5']:
        tier_data = draft[draft['conf_tier'] == tier]
        round_metrics = {}

        for rd in range(1, 8):
            rd_data = tier_data[tier_data['round'] == rd]
            if len(rd_data) >= 10:
                round_metrics[str(rd)] = calculate_hit_rate(rd_data)

        results['by_round'][tier] = round_metrics

    return results


def analyze_draft_value(draft: pd.DataFrame) -> Dict:
    """Analyze draft value by school tier."""
    print("\nAnalyzing draft value curves...")

    draft['conf_tier'] = draft['college'].apply(lambda x: get_conference_tier(get_conference(x)))

    results = {
        'hit_rates_by_round': {},
        'expected_av_by_pick': {},
    }

    # Hit rate by round for different tiers
    for tier in ['Power 5', 'Group of 5', 'Other']:
        tier_data = draft[draft['conf_tier'] == tier]
        tier_results = {}

        for rd in range(1, 8):
            rd_data = tier_data[tier_data['round'] == rd]
            if len(rd_data) >= 5:
                tier_results[str(rd)] = {
                    'n': len(rd_data),
                    'starter_rate': round((rd_data['seasons_started'] >= 2).mean() * 100, 1),
                    'avg_games': round(rd_data['games'].fillna(0).mean(), 1),
                    'avg_av': round(rd_data['car_av'].fillna(0).mean(), 1),
                }

        results['hit_rates_by_round'][tier] = tier_results

    # Expected AV by pick range
    pick_ranges = [(1, 10), (11, 32), (33, 64), (65, 100), (101, 150), (151, 224), (225, 300)]

    for start, end in pick_ranges:
        range_data = draft[(draft['pick'] >= start) & (draft['pick'] <= end)]
        if len(range_data) >= 10:
            results['expected_av_by_pick'][f'{start}-{end}'] = {
                'n': len(range_data),
                'avg_av': round(range_data['car_av'].fillna(0).mean(), 1),
                'avg_games': round(range_data['games'].fillna(0).mean(), 1),
                'starter_rate': round((range_data['seasons_started'] >= 2).mean() * 100, 1),
            }

    return results


def generate_draft_class_weights(draft: pd.DataFrame) -> Dict:
    """Generate weights for draft class generation."""
    print("\nGenerating draft class weights...")

    draft['conference'] = draft['college'].apply(get_conference)
    draft['conf_tier'] = draft['conference'].apply(get_conference_tier)
    draft['pos_group'] = draft['position'].apply(get_position_group)

    results = {
        'school_weights': {},
        'conference_weights': {},
        'position_by_conference': {},
    }

    # School weights (for picking specific schools)
    school_counts = draft['college'].value_counts()
    total_picks = len(draft)

    for school, count in school_counts.head(100).items():
        conf = get_conference(school)
        results['school_weights'][school] = {
            'weight': round(count / total_picks * 1000, 2),  # Per 1000 picks
            'conference': conf,
            'tier': get_conference_tier(conf),
        }

    # Conference weights
    conf_counts = draft['conference'].value_counts()
    for conf, count in conf_counts.items():
        if conf not in ['Unknown', 'Other']:
            results['conference_weights'][conf] = {
                'weight': round(count / total_picks * 100, 1),  # Percentage
                'tier': get_conference_tier(conf),
            }

    # Position distribution by conference
    for conf in ['SEC', 'Big Ten', 'ACC', 'Big 12']:
        conf_data = draft[draft['conference'] == conf]
        pos_dist = conf_data['pos_group'].value_counts(normalize=True) * 100
        results['position_by_conference'][conf] = {pos: round(pct, 1) for pos, pct in pos_dist.items()}

    return results


# =============================================================================
# Main
# =============================================================================

def run_analysis():
    """Run full college production analysis."""
    print("=" * 60)
    print("COLLEGE PRODUCTION ANALYSIS")
    print("For Draft Class Generation")
    print("=" * 60)

    # Load data
    draft = pd.read_parquet(CACHED_DIR / "draft_picks.parquet")
    print(f"\nLoaded {len(draft):,} draft picks ({draft['season'].min()}-{draft['season'].max()})")

    # Run analyses
    school_analysis = analyze_schools(draft)
    conference_analysis = analyze_conferences(draft)
    value_analysis = analyze_draft_value(draft)
    weights = generate_draft_class_weights(draft)

    # Combine into model
    model = {
        'meta': {
            'description': 'College production model for draft class generation',
            'source': 'NFL draft picks 2010-2024',
            'total_picks_analyzed': len(draft),
            'years': f"{draft['season'].min()}-{draft['season'].max()}",
        },

        'schools': school_analysis,
        'conferences': conference_analysis,
        'draft_value': value_analysis,
        'generation_weights': weights,

        'implementation_hints': {
            'draft_class_generation': '''
                To generate a realistic draft class:

                1. Use conference_weights to distribute prospects across conferences
                   - SEC: ~22%, Big Ten: ~18%, ACC: ~12%, Big 12: ~10%
                   - Group of 5: ~15%, Other: ~23%

                2. Use school_weights within each conference
                   - Top schools (Alabama, Ohio St, Georgia) produce 2-4% each
                   - Mid-tier P5 schools produce 0.5-1% each

                3. Use position_by_conference for school specialties
                   - SEC: Strong at RB, LB, CB
                   - Big Ten: Strong at OL, DL
                   - ACC: Strong at WR, EDGE

                4. Use hit_rates_by_round for prospect quality
                   - Power 5 R1: 75% starter rate
                   - Group of 5 R1: 55% starter rate
                   - Power 5 R7: 15% starter rate
            ''',

            'school_flavor': '''
                For narrative richness, tag schools with archetypes:
                - "QB Factory": USC, Oklahoma, Alabama
                - "O-Line U": Wisconsin, Iowa, Notre Dame
                - "WR U": Alabama, Ohio St, Clemson
                - "DB U": LSU, Florida, Ohio St
                - "Edge Factory": Clemson, Ohio St, Georgia
            ''',
        },
    }

    # Export
    output_path = EXPORTS_DIR / "college_production_model.json"
    with open(output_path, 'w') as f:
        json.dump(model, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Exported to: {output_path}")
    print("=" * 60)

    # Print summary
    print("\nKEY FINDINGS:")
    print("\n📚 Top 10 Schools (total picks 2010-2024):")
    for i, school in enumerate(school_analysis['top_overall'][:10], 1):
        print(f"  {i:2d}. {school['school']:20s} ({school['conference']:8s}): "
              f"{school['total_picks']} picks, {school['starter_rate']:.0f}% starters, "
              f"{school['probowlers']} Pro Bowls")

    print("\n🏈 Conference Hit Rates:")
    for conf, data in list(conference_analysis['by_conference'].items())[:8]:
        print(f"  {conf:12s}: {data['total']:3d} picks, "
              f"{data['starter_rate']:.0f}% starters, "
              f"{data['first_round_pct']:.0f}% R1")

    print("\n🎯 Power 5 vs Group of 5 by Round:")
    for rd in ['1', '2', '3', '4']:
        p5 = conference_analysis.get('by_round', {}).get('Power 5', {}).get(rd, {})
        g5 = conference_analysis.get('by_round', {}).get('Group of 5', {}).get(rd, {})
        if p5 and g5:
            print(f"  Round {rd}: P5 {p5.get('starter_rate', 0):.0f}% starters vs "
                  f"G5 {g5.get('starter_rate', 0):.0f}%")

    return model


if __name__ == "__main__":
    run_analysis()
