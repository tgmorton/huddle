"""
Defensive Attribute Projection Model

Maps DB/LB defensive attributes to NFL performance data:
- man_coverage: Completion % allowed in man coverage
- zone_coverage: Completion % allowed in zone coverage
- tackle: Tackle efficiency / missed tackle rate
- play_recognition: Implicit in coverage success

Uses team-level PBP data for coverage analysis.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_data():
    """Load play-by-play data."""
    data_dir = Path(__file__).parent.parent / "data" / "cached"
    pbp = pd.read_parquet(data_dir / "pbp_2019_2024.parquet")
    return pbp


def convert_to_native(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(i) for i in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def tier_defenses_by_epa(pbp):
    """Tier defenses by EPA allowed per play."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['defteam'].notna()) &
        (pbp['epa'].notna())
    ].copy()

    # Get defensive EPA per season
    def_seasons = pass_plays.groupby(['season', 'defteam']).agg({
        'epa': ['mean', 'count']
    }).reset_index()
    def_seasons.columns = ['season', 'team', 'epa_allowed', 'plays']

    # Filter to enough plays
    def_seasons = def_seasons[def_seasons['plays'] >= 200]

    # Tier by EPA (lower = better defense)
    def_seasons['tier'] = pd.qcut(
        def_seasons['epa_allowed'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Elite', 'Above Avg', 'Below Avg', 'Bad']  # Low EPA allowed = Elite
    )

    return def_seasons


def analyze_coverage_by_tier(pbp, def_tiers):
    """Analyze coverage success by defensive tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['defteam'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    # Merge tiers
    pass_plays = pass_plays.merge(
        def_tiers[['season', 'team', 'tier']],
        left_on=['season', 'defteam'],
        right_on=['season', 'team'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        if len(tier_plays) >= 500:
            results[tier] = {
                'completion_allowed': round(tier_plays['complete_pass'].mean(), 4),
                'int_rate': round(tier_plays['interception'].mean() if 'interception' in tier_plays.columns else 0, 4),
                'sample': len(tier_plays)
            }

    return results


def analyze_coverage_by_depth(pbp, def_tiers):
    """Analyze coverage by pass depth for each tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['defteam'].notna()) &
        (pbp['complete_pass'].notna()) &
        (pbp['air_yards'].notna())
    ].copy()

    def get_depth(air_yards):
        if air_yards < 10:
            return 'short'
        elif air_yards < 20:
            return 'medium'
        else:
            return 'deep'

    pass_plays['depth'] = pass_plays['air_yards'].apply(get_depth)

    # Merge tiers
    pass_plays = pass_plays.merge(
        def_tiers[['season', 'team', 'tier']],
        left_on=['season', 'defteam'],
        right_on=['season', 'team'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]
        results[tier] = {}

        for depth in ['short', 'medium', 'deep']:
            depth_plays = tier_plays[tier_plays['depth'] == depth]
            if len(depth_plays) >= 200:
                results[tier][depth] = {
                    'completion_allowed': round(depth_plays['complete_pass'].mean(), 4),
                    'sample': len(depth_plays)
                }

    return results


def analyze_run_defense(pbp, def_tiers):
    """Analyze run defense (tackling proxy) by tier."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['defteam'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Merge tiers
    run_plays = run_plays.merge(
        def_tiers[['season', 'team', 'tier']],
        left_on=['season', 'defteam'],
        right_on=['season', 'team'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = run_plays[run_plays['tier'] == tier]

        if len(tier_plays) >= 200:
            # Stuff rate (0 or negative yards)
            stuff_rate = (tier_plays['rushing_yards'] <= 0).mean()

            # Explosive allowed (10+ yards)
            explosive_rate = (tier_plays['rushing_yards'] >= 10).mean()

            results[tier] = {
                'ypc_allowed': round(tier_plays['rushing_yards'].mean(), 2),
                'stuff_rate': round(stuff_rate, 4),
                'explosive_allowed': round(explosive_rate, 4),
                'sample': len(tier_plays)
            }

    return results


def analyze_big_play_prevention(pbp, def_tiers):
    """Analyze big play prevention (20+ yard passes allowed)."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['defteam'].notna()) &
        (pbp['yards_gained'].notna())
    ].copy()

    # Big play = 20+ yards gained
    pass_plays['big_play'] = pass_plays['yards_gained'] >= 20

    # Merge tiers
    pass_plays = pass_plays.merge(
        def_tiers[['season', 'team', 'tier']],
        left_on=['season', 'defteam'],
        right_on=['season', 'team'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        if len(tier_plays) >= 500:
            big_play_rate = tier_plays['big_play'].mean()
            results[tier] = {
                'big_play_rate': round(big_play_rate, 4),
                'sample': len(tier_plays)
            }

    return results


def build_defense_calibration(coverage_data, depth_data, run_data, big_play_data):
    """Build calibration tables for defensive attributes."""

    calibration = {}

    # COVERAGE (completion allowed)
    if coverage_data:
        calibration['coverage'] = {
            'nfl_metric': 'completion_rate_allowed',
            'tier_data': {
                tier: data.get('completion_allowed')
                for tier, data in coverage_data.items()
            }
        }

        elite = coverage_data.get('Elite', {}).get('completion_allowed')
        bad = coverage_data.get('Bad', {}).get('completion_allowed')
        if elite and bad:
            spread = bad - elite  # Bad allows more completions
            calibration['coverage']['spread_elite_to_bad'] = round(spread, 4)
            calibration['coverage']['effect_per_10_points'] = round(-spread / 55 * 10, 4)

    # DEEP COVERAGE (deep ball allowed)
    if depth_data:
        calibration['deep_coverage'] = {
            'nfl_metric': 'deep_completion_allowed',
            'tier_data': {}
        }

        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in depth_data and 'deep' in depth_data[tier]:
                calibration['deep_coverage']['tier_data'][tier] = depth_data[tier]['deep']['completion_allowed']

        elite = calibration['deep_coverage']['tier_data'].get('Elite')
        bad = calibration['deep_coverage']['tier_data'].get('Bad')
        if elite and bad:
            spread = bad - elite
            calibration['deep_coverage']['spread_elite_to_bad'] = round(spread, 4)
            calibration['deep_coverage']['effect_per_10_points'] = round(-spread / 55 * 10, 4)

    # TACKLE (run defense proxy)
    if run_data:
        calibration['tackle'] = {
            'nfl_metric': 'run_ypc_allowed_and_stuff_rate',
            'tier_data': {
                tier: {
                    'ypc_allowed': data.get('ypc_allowed'),
                    'stuff_rate': data.get('stuff_rate')
                }
                for tier, data in run_data.items()
            }
        }

        elite_ypc = run_data.get('Elite', {}).get('ypc_allowed')
        bad_ypc = run_data.get('Bad', {}).get('ypc_allowed')
        if elite_ypc and bad_ypc:
            spread = bad_ypc - elite_ypc
            calibration['tackle']['ypc_spread'] = round(spread, 2)
            calibration['tackle']['effect_per_10_points'] = round(-spread / 55 * 10, 3)

    # PLAY RECOGNITION (big play prevention)
    if big_play_data:
        calibration['play_recognition'] = {
            'nfl_metric': 'big_play_rate_allowed',
            'tier_data': {
                tier: data.get('big_play_rate')
                for tier, data in big_play_data.items()
            }
        }

        elite = big_play_data.get('Elite', {}).get('big_play_rate')
        bad = big_play_data.get('Bad', {}).get('big_play_rate')
        if elite is not None and bad is not None:
            spread = bad - elite
            calibration['play_recognition']['spread_elite_to_bad'] = round(spread, 4)
            calibration['play_recognition']['effect_per_10_points'] = round(-spread / 55 * 10, 4)

    return calibration


def run_defense_projection():
    """Run the defensive attribute projection analysis."""

    print("Loading data...")
    pbp = load_data()
    print(f"Loaded {len(pbp)} plays")

    print("\nTiering defenses by EPA allowed...")
    def_tiers = tier_defenses_by_epa(pbp)
    print(f"Tiered {len(def_tiers)} team-seasons")

    print("\nAnalyzing coverage success...")
    coverage_data = analyze_coverage_by_tier(pbp, def_tiers)

    print("Analyzing coverage by depth...")
    depth_data = analyze_coverage_by_depth(pbp, def_tiers)

    print("Analyzing run defense (tackling)...")
    run_data = analyze_run_defense(pbp, def_tiers)

    print("Analyzing big play prevention...")
    big_play_data = analyze_big_play_prevention(pbp, def_tiers)

    print("Building calibration tables...")
    calibration = build_defense_calibration(coverage_data, depth_data, run_data, big_play_data)

    # Build final model
    model = {
        'model_name': 'defense_attribute_projection',
        'description': 'Maps DB/LB defensive attributes to NFL performance metrics',
        'data_source': 'NFL PBP 2019-2024 (team-level)',
        'coverage_by_tier': coverage_data,
        'coverage_by_depth': depth_data,
        'run_defense': run_data,
        'big_play_prevention': big_play_data,
        'attribute_calibration': calibration,
        'attributes_covered': [
            'coverage',
            'deep_coverage',
            'tackle',
            'play_recognition'
        ]
    }

    # Convert and export
    model = convert_to_native(model)

    export_path = Path(__file__).parent.parent / "exports" / "defense_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("DEFENSIVE ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    print("\nCOVERAGE (Completion Allowed):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in coverage_data:
            comp = coverage_data[tier].get('completion_allowed', 0)
            int_rate = coverage_data[tier].get('int_rate', 0)
            print(f"  {tier}: {comp*100:.1f}% comp, {int_rate*100:.2f}% INT")

    if depth_data:
        print("\nDEEP COVERAGE (20+ Air Yards):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in depth_data and 'deep' in depth_data[tier]:
                comp = depth_data[tier]['deep'].get('completion_allowed', 0)
                print(f"  {tier}: {comp*100:.1f}% deep completion allowed")

    print("\nRUN DEFENSE (Tackling Proxy):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in run_data:
            ypc = run_data[tier].get('ypc_allowed', 0)
            stuff = run_data[tier].get('stuff_rate', 0)
            print(f"  {tier}: {ypc:.2f} YPC allowed, {stuff*100:.1f}% stuff rate")

    print("\nBIG PLAY PREVENTION (Play Recognition):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in big_play_data:
            rate = big_play_data[tier].get('big_play_rate', 0)
            print(f"  {tier}: {rate*100:.1f}% big plays allowed")

    print("\nATTRIBUTE EFFECTS:")
    for attr in ['coverage', 'deep_coverage', 'tackle', 'play_recognition']:
        if attr in calibration and 'effect_per_10_points' in calibration[attr]:
            effect = calibration[attr]['effect_per_10_points']
            if attr == 'tackle':
                print(f"  {attr}: +10 rating = {effect:.3f} YPC prevented")
            else:
                print(f"  {attr}: +10 rating = {effect*100:.2f}% improvement")

    return model


if __name__ == "__main__":
    model = run_defense_projection()
