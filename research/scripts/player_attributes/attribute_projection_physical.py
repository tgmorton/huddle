"""
Physical Attribute Projection Model

Maps NFL Combine measurables to game attribute ratings:
- speed: 40-yard dash
- acceleration: 10-yard split (derived from forty)
- agility: 3-cone drill
- strength: Bench press
- jumping: Vertical jump

Uses combine data to build conversion formulas and position-specific ranges.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_combine_data():
    """Load combine data."""
    combine_path = Path(__file__).parent.parent / "data" / "cached" / "combine.parquet"
    return pd.read_parquet(combine_path)


def normalize_position(pos):
    """Normalize position to game-compatible position group."""
    pos_map = {
        'QB': 'QB',
        'RB': 'RB', 'FB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'T': 'OL', 'OT': 'OL', 'G': 'OL', 'OG': 'OL', 'C': 'OL', 'OL': 'OL',
        'DE': 'EDGE', 'EDGE': 'EDGE', 'OLB': 'EDGE',
        'DT': 'DL', 'DL': 'DL', 'NT': 'DL',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'CB',
        'S': 'S', 'FS': 'S', 'SS': 'S', 'DB': 'CB',
        'K': 'K', 'P': 'P', 'LS': 'LS'
    }
    return pos_map.get(pos, pos)


def forty_to_speed(forty_time):
    """
    Convert 40-yard dash time to speed rating.

    Elite: 4.22 (100) → Slowest: 5.60 (40)
    Linear interpolation based on combine ranges.
    """
    if pd.isna(forty_time):
        return None

    # Anchor points from combine data:
    # - Fastest ever: ~4.22 (John Ross) = 99
    # - Slowest OL: ~5.60 = 40
    fastest = 4.22
    slowest = 5.60

    # Linear mapping
    rating = 99 - (forty_time - fastest) / (slowest - fastest) * 59
    return max(40, min(99, rating))


def cone_to_agility(cone_time):
    """
    Convert 3-cone drill time to agility rating.

    Elite: 6.28 (99) → Slowest: 8.82 (40)
    """
    if pd.isna(cone_time):
        return None

    fastest = 6.28
    slowest = 8.82

    rating = 99 - (cone_time - fastest) / (slowest - fastest) * 59
    return max(40, min(99, rating))


def bench_to_strength(bench_reps):
    """
    Convert bench press reps to strength rating.

    Max: 49 reps (99) → Min: 4 reps (40)
    """
    if pd.isna(bench_reps):
        return None

    min_reps = 4
    max_reps = 49

    rating = 40 + (bench_reps - min_reps) / (max_reps - min_reps) * 59
    return max(40, min(99, rating))


def vertical_to_jumping(vertical_inches):
    """
    Convert vertical jump to jumping rating.

    Max: 46.5" (99) → Min: 17.5" (40)
    """
    if pd.isna(vertical_inches):
        return None

    min_vert = 17.5
    max_vert = 46.5

    rating = 40 + (vertical_inches - min_vert) / (max_vert - min_vert) * 59
    return max(40, min(99, rating))


def shuttle_to_quickness(shuttle_time):
    """
    Convert shuttle time to quickness/COD rating.

    Fastest: 3.82 (99) → Slowest: 5.38 (40)
    """
    if pd.isna(shuttle_time):
        return None

    fastest = 3.82
    slowest = 5.38

    rating = 99 - (shuttle_time - fastest) / (slowest - fastest) * 59
    return max(40, min(99, rating))


def derive_acceleration(forty_time):
    """
    Derive acceleration rating from 40-time.

    Acceleration correlates strongly with 10-split, which correlates with forty.
    Elite accelerators have faster first 10 yards relative to total time.

    Approximation: acceleration = speed + adjustment based on player size
    For raw derivation, use 85% of speed + 15 point variance
    """
    if pd.isna(forty_time):
        return None

    speed = forty_to_speed(forty_time)
    # Acceleration is typically close to speed with some variance
    # Heavier players tend to have lower acceleration relative to speed
    return speed


def build_conversion_formulas(combine_df):
    """Build and validate conversion formulas against combine data."""

    formulas = {}

    # Speed from forty
    forty_data = combine_df[combine_df['forty'].notna()]['forty']
    formulas['speed'] = {
        'source': 'forty',
        'formula': 'rating = 99 - (forty - 4.22) / (5.60 - 4.22) * 59',
        'description': 'Linear scaling: 4.22s = 99, 5.60s = 40',
        'combine_stats': {
            'min': float(forty_data.min()),
            'max': float(forty_data.max()),
            'mean': float(forty_data.mean()),
            'std': float(forty_data.std()),
            'p10': float(forty_data.quantile(0.10)),
            'p90': float(forty_data.quantile(0.90))
        },
        'rating_stats': {
            'min': forty_to_speed(forty_data.max()),
            'max': forty_to_speed(forty_data.min()),
            'mean': forty_to_speed(forty_data.mean()),
            'p10': forty_to_speed(forty_data.quantile(0.90)),  # Inverted
            'p90': forty_to_speed(forty_data.quantile(0.10))
        }
    }

    # Agility from 3-cone
    cone_data = combine_df[combine_df['cone'].notna()]['cone']
    formulas['agility'] = {
        'source': 'cone',
        'formula': 'rating = 99 - (cone - 6.28) / (8.82 - 6.28) * 59',
        'description': 'Linear scaling: 6.28s = 99, 8.82s = 40',
        'combine_stats': {
            'min': float(cone_data.min()),
            'max': float(cone_data.max()),
            'mean': float(cone_data.mean()),
            'std': float(cone_data.std()),
            'p10': float(cone_data.quantile(0.10)),
            'p90': float(cone_data.quantile(0.90))
        },
        'rating_stats': {
            'min': cone_to_agility(cone_data.max()),
            'max': cone_to_agility(cone_data.min()),
            'mean': cone_to_agility(cone_data.mean()),
            'p10': cone_to_agility(cone_data.quantile(0.90)),
            'p90': cone_to_agility(cone_data.quantile(0.10))
        }
    }

    # Strength from bench
    bench_data = combine_df[combine_df['bench'].notna()]['bench']
    formulas['strength'] = {
        'source': 'bench',
        'formula': 'rating = 40 + (reps - 4) / (49 - 4) * 59',
        'description': 'Linear scaling: 4 reps = 40, 49 reps = 99',
        'combine_stats': {
            'min': float(bench_data.min()),
            'max': float(bench_data.max()),
            'mean': float(bench_data.mean()),
            'std': float(bench_data.std()),
            'p10': float(bench_data.quantile(0.10)),
            'p90': float(bench_data.quantile(0.90))
        },
        'rating_stats': {
            'min': bench_to_strength(bench_data.min()),
            'max': bench_to_strength(bench_data.max()),
            'mean': bench_to_strength(bench_data.mean()),
            'p10': bench_to_strength(bench_data.quantile(0.10)),
            'p90': bench_to_strength(bench_data.quantile(0.90))
        }
    }

    # Jumping from vertical
    vert_data = combine_df[combine_df['vertical'].notna()]['vertical']
    formulas['jumping'] = {
        'source': 'vertical',
        'formula': 'rating = 40 + (vertical - 17.5) / (46.5 - 17.5) * 59',
        'description': 'Linear scaling: 17.5" = 40, 46.5" = 99',
        'combine_stats': {
            'min': float(vert_data.min()),
            'max': float(vert_data.max()),
            'mean': float(vert_data.mean()),
            'std': float(vert_data.std()),
            'p10': float(vert_data.quantile(0.10)),
            'p90': float(vert_data.quantile(0.90))
        },
        'rating_stats': {
            'min': vertical_to_jumping(vert_data.min()),
            'max': vertical_to_jumping(vert_data.max()),
            'mean': vertical_to_jumping(vert_data.mean()),
            'p10': vertical_to_jumping(vert_data.quantile(0.10)),
            'p90': vertical_to_jumping(vert_data.quantile(0.90))
        }
    }

    # Acceleration derived from forty
    formulas['acceleration'] = {
        'source': 'forty (derived)',
        'formula': 'rating = speed_rating (derived from forty)',
        'description': 'Derived from 40-time, correlates with 10-split',
        'note': 'No direct measurement; approximated from 40-time'
    }

    # Quickness from shuttle
    shuttle_data = combine_df[combine_df['shuttle'].notna()]['shuttle']
    formulas['change_of_direction'] = {
        'source': 'shuttle',
        'formula': 'rating = 99 - (shuttle - 3.82) / (5.38 - 3.82) * 59',
        'description': 'Linear scaling: 3.82s = 99, 5.38s = 40',
        'combine_stats': {
            'min': float(shuttle_data.min()),
            'max': float(shuttle_data.max()),
            'mean': float(shuttle_data.mean()),
            'std': float(shuttle_data.std()),
            'p10': float(shuttle_data.quantile(0.10)),
            'p90': float(shuttle_data.quantile(0.90))
        },
        'rating_stats': {
            'min': shuttle_to_quickness(shuttle_data.max()),
            'max': shuttle_to_quickness(shuttle_data.min()),
            'mean': shuttle_to_quickness(shuttle_data.mean()),
            'p10': shuttle_to_quickness(shuttle_data.quantile(0.90)),
            'p90': shuttle_to_quickness(shuttle_data.quantile(0.10))
        }
    }

    return formulas


def build_position_ranges(combine_df):
    """Build position-specific attribute ranges."""

    combine_df['pos_group'] = combine_df['pos'].apply(normalize_position)

    position_ranges = {}

    for pos in ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'CB', 'S']:
        pos_data = combine_df[combine_df['pos_group'] == pos]

        if len(pos_data) < 10:
            continue

        pos_ranges = {}

        # Speed from forty
        if pos_data['forty'].notna().sum() >= 10:
            forty = pos_data['forty']
            pos_ranges['speed'] = {
                'min': round(forty_to_speed(forty.quantile(0.90)), 0),  # Slowest -> lowest rating
                'avg': round(forty_to_speed(forty.median()), 0),
                'max': round(forty_to_speed(forty.quantile(0.10)), 0),  # Fastest -> highest rating
                'std': round(forty_to_speed(forty.mean()) - forty_to_speed(forty.mean() + forty.std()), 1)
            }

        # Agility from cone
        if pos_data['cone'].notna().sum() >= 10:
            cone = pos_data['cone']
            pos_ranges['agility'] = {
                'min': round(cone_to_agility(cone.quantile(0.90)), 0),
                'avg': round(cone_to_agility(cone.median()), 0),
                'max': round(cone_to_agility(cone.quantile(0.10)), 0),
                'std': round(cone_to_agility(cone.mean()) - cone_to_agility(cone.mean() + cone.std()), 1)
            }

        # Strength from bench
        if pos_data['bench'].notna().sum() >= 10:
            bench = pos_data['bench']
            pos_ranges['strength'] = {
                'min': round(bench_to_strength(bench.quantile(0.10)), 0),
                'avg': round(bench_to_strength(bench.median()), 0),
                'max': round(bench_to_strength(bench.quantile(0.90)), 0),
                'std': round(bench_to_strength(bench.mean() + bench.std()) - bench_to_strength(bench.mean()), 1)
            }

        # Jumping from vertical
        if pos_data['vertical'].notna().sum() >= 10:
            vert = pos_data['vertical']
            pos_ranges['jumping'] = {
                'min': round(vertical_to_jumping(vert.quantile(0.10)), 0),
                'avg': round(vertical_to_jumping(vert.median()), 0),
                'max': round(vertical_to_jumping(vert.quantile(0.90)), 0),
                'std': round(vertical_to_jumping(vert.mean() + vert.std()) - vertical_to_jumping(vert.mean()), 1)
            }

        # Change of direction from shuttle
        if pos_data['shuttle'].notna().sum() >= 10:
            shuttle = pos_data['shuttle']
            pos_ranges['change_of_direction'] = {
                'min': round(shuttle_to_quickness(shuttle.quantile(0.90)), 0),
                'avg': round(shuttle_to_quickness(shuttle.median()), 0),
                'max': round(shuttle_to_quickness(shuttle.quantile(0.10)), 0),
                'std': round(shuttle_to_quickness(shuttle.mean()) - shuttle_to_quickness(shuttle.mean() + shuttle.std()), 1)
            }

        position_ranges[pos] = pos_ranges

    return position_ranges


def build_correlation_matrix(combine_df):
    """Build correlation matrix between physical measurables."""

    measurables = ['forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle']

    # Filter to rows with at least 3 measurables
    valid_data = combine_df[measurables].dropna(thresh=3)

    correlations = {}

    for m1 in measurables:
        correlations[m1] = {}
        for m2 in measurables:
            if m1 == m2:
                correlations[m1][m2] = 1.0
            else:
                # Get valid pairs
                valid_pairs = combine_df[[m1, m2]].dropna()
                if len(valid_pairs) >= 30:
                    correlations[m1][m2] = round(valid_pairs[m1].corr(valid_pairs[m2]), 3)
                else:
                    correlations[m1][m2] = None

    return correlations


def build_effect_per_rating(combine_df):
    """Calculate effect of each 10 rating points on performance."""

    effects = {}

    # Speed effect
    # 10 rating points ≈ 0.14s forty difference
    # 0.14s faster ≈ 0.2 yards/sec faster
    effects['speed'] = {
        'per_10_points': {
            'forty_time': -0.14,  # seconds
            'top_speed': 0.3,    # yards/sec (estimated)
        },
        'effect_description': '+10 speed = -0.14s forty = +0.3 yds/sec top speed'
    }

    # Agility effect
    effects['agility'] = {
        'per_10_points': {
            'cone_time': -0.22,
        },
        'effect_description': '+10 agility = -0.22s 3-cone'
    }

    # Strength effect
    effects['strength'] = {
        'per_10_points': {
            'bench_reps': 7.6,
        },
        'effect_description': '+10 strength = +7.6 bench reps'
    }

    # Jumping effect
    effects['jumping'] = {
        'per_10_points': {
            'vertical_inches': 4.9,
        },
        'effect_description': '+10 jumping = +4.9 inches vertical'
    }

    return effects


def run_physical_projection():
    """Run the physical attribute projection analysis."""

    print("Loading combine data...")
    combine_df = load_combine_data()
    print(f"Loaded {len(combine_df)} combine entries")

    print("\nBuilding conversion formulas...")
    formulas = build_conversion_formulas(combine_df)

    print("Building position-specific ranges...")
    position_ranges = build_position_ranges(combine_df)

    print("Building correlation matrix...")
    correlations = build_correlation_matrix(combine_df)

    print("Calculating rating effects...")
    effects = build_effect_per_rating(combine_df)

    # Build final model
    model = {
        'model_name': 'physical_attribute_projection',
        'description': 'Maps NFL Combine measurables to game attribute ratings',
        'data_source': 'NFL Combine data',
        'conversion_formulas': formulas,
        'position_ranges': position_ranges,
        'measurable_correlations': correlations,
        'rating_effects': effects,
        'attributes_covered': [
            'speed',
            'acceleration',
            'agility',
            'strength',
            'jumping',
            'change_of_direction'
        ]
    }

    # Export
    export_path = Path(__file__).parent.parent / "exports" / "physical_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("PHYSICAL ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    print("\nCONVERSION FORMULAS:")
    for attr, data in formulas.items():
        print(f"\n{attr.upper()}:")
        print(f"  Source: {data['source']}")
        print(f"  {data['description']}")
        if 'rating_stats' in data:
            stats = data['rating_stats']
            print(f"  Rating range: {stats['min']:.0f} - {stats['max']:.0f} (mean: {stats['mean']:.0f})")

    print("\n" + "-"*60)
    print("POSITION-SPECIFIC RANGES:")
    for pos in ['WR', 'RB', 'OL', 'CB']:
        if pos in position_ranges:
            print(f"\n{pos}:")
            for attr, ranges in position_ranges[pos].items():
                print(f"  {attr}: {ranges['min']:.0f} - {ranges['max']:.0f} (avg: {ranges['avg']:.0f})")

    print("\n" + "-"*60)
    print("KEY CORRELATIONS:")
    print(f"  forty ↔ vertical: {correlations['forty']['vertical']}")
    print(f"  forty ↔ broad_jump: {correlations['forty']['broad_jump']}")
    print(f"  bench ↔ forty: {correlations['bench']['forty']}")
    print(f"  cone ↔ shuttle: {correlations['cone']['shuttle']}")

    return model


if __name__ == "__main__":
    model = run_physical_projection()
