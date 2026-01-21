"""
Passing Attribute Projection Model

Maps QB attributes to NFL performance data:
- throw_power: Deep completion rate, avg air yards
- throw_accuracy_short: Completion % on <10 air yards
- throw_accuracy_med: Completion % on 10-20 air yards
- throw_accuracy_deep: Completion % on 20+ air yards
- throw_on_run: Scramble completion rate
- play_action: Play action completion boost

Uses PBP and NGS data to calibrate attribute effects.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_data():
    """Load play-by-play and NGS passing data."""
    data_dir = Path(__file__).parent.parent / "data" / "cached"

    pbp = pd.read_parquet(data_dir / "pbp_2019_2024.parquet")
    ngs = pd.read_parquet(data_dir / "ngs_passing.parquet")

    return pbp, ngs


def tier_qbs_by_epa(pbp):
    """Tier QBs into quartiles by EPA/play for each season."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_player_name'].notna()) &
        (pbp['epa'].notna())
    ].copy()

    # Get seasonal EPA
    qb_seasons = pass_plays.groupby(['season', 'passer_player_name']).agg({
        'epa': ['mean', 'count']
    }).reset_index()
    qb_seasons.columns = ['season', 'passer', 'epa_per_play', 'attempts']

    # Filter to 100+ attempts
    qb_seasons = qb_seasons[qb_seasons['attempts'] >= 100]

    # Quartile tiers
    qb_seasons['tier'] = pd.qcut(
        qb_seasons['epa_per_play'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']
    )

    return qb_seasons


def analyze_accuracy_by_depth(pbp, qb_tiers):
    """Analyze completion rates by air yards depth for each tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['air_yards'].notna()) &
        (pbp['complete_pass'].notna()) &
        (pbp['passer_player_name'].notna())
    ].copy()

    # Merge tiers
    pass_plays = pass_plays.merge(
        qb_tiers[['season', 'passer', 'tier']],
        left_on=['season', 'passer_player_name'],
        right_on=['season', 'passer'],
        how='inner'
    )

    # Define depth buckets
    def get_depth_bucket(air_yards):
        if air_yards < 0:
            return 'behind_los'
        elif air_yards < 10:
            return 'short'
        elif air_yards < 20:
            return 'medium'
        else:
            return 'deep'

    pass_plays['depth'] = pass_plays['air_yards'].apply(get_depth_bucket)

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]
        results[tier] = {}

        for depth in ['behind_los', 'short', 'medium', 'deep']:
            depth_plays = tier_plays[tier_plays['depth'] == depth]
            if len(depth_plays) >= 100:
                results[tier][depth] = {
                    'completion_rate': round(depth_plays['complete_pass'].mean(), 4),
                    'int_rate': round(depth_plays['interception'].mean() if 'interception' in depth_plays.columns else 0, 4),
                    'sample': len(depth_plays),
                    'avg_air_yards': round(depth_plays['air_yards'].mean(), 1)
                }

    return results


def analyze_pressure_performance(pbp, qb_tiers):
    """Analyze completion rates under pressure vs clean pocket."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['complete_pass'].notna()) &
        (pbp['passer_player_name'].notna())
    ].copy()

    # Determine pressure (sack, qb_hit, or was_pressure if available)
    if 'was_pressure' in pass_plays.columns:
        pass_plays['under_pressure'] = pass_plays['was_pressure'] == 1
    else:
        pass_plays['under_pressure'] = (pass_plays['sack'] == 1) | (pass_plays['qb_hit'] == 1)

    # Merge tiers
    pass_plays = pass_plays.merge(
        qb_tiers[['season', 'passer', 'tier']],
        left_on=['season', 'passer_player_name'],
        right_on=['season', 'passer'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        clean = tier_plays[~tier_plays['under_pressure']]
        pressure = tier_plays[tier_plays['under_pressure']]

        clean_comp = clean['complete_pass'].mean() if len(clean) > 100 else None
        pressure_comp = pressure['complete_pass'].mean() if len(pressure) > 100 else None

        results[tier] = {
            'clean_pocket': round(clean_comp, 4) if clean_comp else None,
            'under_pressure': round(pressure_comp, 4) if pressure_comp else None,
            'pressure_penalty': round(clean_comp - pressure_comp, 4) if (clean_comp and pressure_comp) else None,
            'clean_sample': len(clean),
            'pressure_sample': len(pressure)
        }

    return results


def analyze_play_action(pbp, qb_tiers):
    """Analyze play action boost by tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['complete_pass'].notna()) &
        (pbp['passer_player_name'].notna())
    ].copy()

    # Check for play action field
    if 'play_action' not in pass_plays.columns:
        return {}

    # Merge tiers
    pass_plays = pass_plays.merge(
        qb_tiers[['season', 'passer', 'tier']],
        left_on=['season', 'passer_player_name'],
        right_on=['season', 'passer'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        pa = tier_plays[tier_plays['play_action'] == True]
        no_pa = tier_plays[tier_plays['play_action'] != True]

        pa_comp = pa['complete_pass'].mean() if len(pa) > 100 else None
        no_pa_comp = no_pa['complete_pass'].mean() if len(no_pa) > 100 else None

        results[tier] = {
            'with_play_action': round(pa_comp, 4) if pa_comp else None,
            'without_play_action': round(no_pa_comp, 4) if no_pa_comp else None,
            'play_action_boost': round(pa_comp - no_pa_comp, 4) if (pa_comp and no_pa_comp) else None,
            'pa_sample': len(pa),
            'no_pa_sample': len(no_pa)
        }

    return results


def analyze_scramble_passing(pbp, qb_tiers):
    """Analyze passing while scrambling/on the run."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['complete_pass'].notna()) &
        (pbp['passer_player_name'].notna())
    ].copy()

    # Check for scramble field
    has_scramble = 'qb_scramble' in pass_plays.columns

    if not has_scramble:
        # Try to derive from pass_location or other fields
        return {}

    # Merge tiers
    pass_plays = pass_plays.merge(
        qb_tiers[['season', 'passer', 'tier']],
        left_on=['season', 'passer_player_name'],
        right_on=['season', 'passer'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        # qb_scramble typically means the QB ran, not passed
        # Look at 'pass_location' for outside pocket throws
        in_pocket = tier_plays[tier_plays['pass_location'].isin(['left', 'middle', 'right'])]

        results[tier] = {
            'in_pocket_completion': round(in_pocket['complete_pass'].mean(), 4) if len(in_pocket) > 100 else None,
            'sample': len(in_pocket)
        }

    return results


def analyze_throw_power_proxy(pbp, qb_tiers):
    """Analyze deep ball ability as proxy for throw power."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['air_yards'].notna()) &
        (pbp['air_yards'] >= 20) &
        (pbp['complete_pass'].notna()) &
        (pbp['passer_player_name'].notna())
    ].copy()

    # Merge tiers
    pass_plays = pass_plays.merge(
        qb_tiers[['season', 'passer', 'tier']],
        left_on=['season', 'passer_player_name'],
        right_on=['season', 'passer'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        if len(tier_plays) >= 100:
            results[tier] = {
                'deep_completion': round(tier_plays['complete_pass'].mean(), 4),
                'avg_deep_air_yards': round(tier_plays['air_yards'].mean(), 1),
                'max_air_yards_p90': round(tier_plays['air_yards'].quantile(0.90), 1),
                'int_rate': round(tier_plays['interception'].mean() if 'interception' in tier_plays.columns else 0, 4),
                'sample': len(tier_plays)
            }

    return results


def build_attribute_calibration(depth_data, pressure_data, power_data):
    """Build calibration tables for passing attributes."""

    calibration = {}

    # THROW ACCURACY SHORT (<10 yards)
    if depth_data:
        calibration['throw_accuracy_short'] = {
            'nfl_metric': 'completion_rate_under_10_yards',
            'tier_data': {
                tier: data.get('short', {}).get('completion_rate')
                for tier, data in depth_data.items()
            },
            'effect_per_10_points': None,  # Will calculate below
            'rating_formula': 'completion = base + (rating - 50) / 50 * spread'
        }

        # Calculate effect
        elite = depth_data.get('Elite', {}).get('short', {}).get('completion_rate')
        bad = depth_data.get('Bad', {}).get('short', {}).get('completion_rate')
        if elite and bad:
            spread = elite - bad
            calibration['throw_accuracy_short']['spread_elite_to_bad'] = round(spread, 4)
            calibration['throw_accuracy_short']['effect_per_10_points'] = round(spread / 5.5 * 10, 4)  # 55 point spread

    # THROW ACCURACY MEDIUM (10-20 yards)
    if depth_data:
        calibration['throw_accuracy_medium'] = {
            'nfl_metric': 'completion_rate_10_to_20_yards',
            'tier_data': {
                tier: data.get('medium', {}).get('completion_rate')
                for tier, data in depth_data.items()
            }
        }

        elite = depth_data.get('Elite', {}).get('medium', {}).get('completion_rate')
        bad = depth_data.get('Bad', {}).get('medium', {}).get('completion_rate')
        if elite and bad:
            spread = elite - bad
            calibration['throw_accuracy_medium']['spread_elite_to_bad'] = round(spread, 4)
            calibration['throw_accuracy_medium']['effect_per_10_points'] = round(spread / 5.5 * 10, 4)

    # THROW ACCURACY DEEP (20+ yards)
    if depth_data:
        calibration['throw_accuracy_deep'] = {
            'nfl_metric': 'completion_rate_over_20_yards',
            'tier_data': {
                tier: data.get('deep', {}).get('completion_rate')
                for tier, data in depth_data.items()
            }
        }

        elite = depth_data.get('Elite', {}).get('deep', {}).get('completion_rate')
        bad = depth_data.get('Bad', {}).get('deep', {}).get('completion_rate')
        if elite and bad:
            spread = elite - bad
            calibration['throw_accuracy_deep']['spread_elite_to_bad'] = round(spread, 4)
            calibration['throw_accuracy_deep']['effect_per_10_points'] = round(spread / 5.5 * 10, 4)

    # THROW POWER (deep ball proxy)
    if power_data:
        calibration['throw_power'] = {
            'nfl_metric': 'deep_ball_completion_and_air_yards',
            'tier_data': {
                tier: {
                    'deep_completion': data.get('deep_completion'),
                    'avg_deep_air_yards': data.get('avg_deep_air_yards'),
                    'max_air_yards_p90': data.get('max_air_yards_p90')
                }
                for tier, data in power_data.items()
            }
        }

    # POISE / THROW UNDER PRESSURE
    if pressure_data:
        calibration['poise'] = {
            'nfl_metric': 'completion_under_pressure_penalty',
            'tier_data': {
                tier: {
                    'clean_pocket': data.get('clean_pocket'),
                    'under_pressure': data.get('under_pressure'),
                    'pressure_penalty': data.get('pressure_penalty')
                }
                for tier, data in pressure_data.items()
            },
            'effect_description': 'Higher poise = smaller completion drop under pressure'
        }

        elite_penalty = pressure_data.get('Elite', {}).get('pressure_penalty')
        bad_penalty = pressure_data.get('Bad', {}).get('pressure_penalty')
        if elite_penalty and bad_penalty:
            calibration['poise']['penalty_spread'] = round(bad_penalty - elite_penalty, 4)

    return calibration


def run_passing_projection():
    """Run the passing attribute projection analysis."""

    print("Loading data...")
    pbp, ngs = load_data()
    print(f"Loaded {len(pbp)} plays, {len(ngs)} NGS passing records")

    print("\nTiering QBs by EPA...")
    qb_tiers = tier_qbs_by_epa(pbp)
    print(f"Tiered {len(qb_tiers)} QB seasons")

    print("\nAnalyzing accuracy by depth...")
    depth_data = analyze_accuracy_by_depth(pbp, qb_tiers)

    print("Analyzing pressure performance...")
    pressure_data = analyze_pressure_performance(pbp, qb_tiers)

    print("Analyzing play action...")
    pa_data = analyze_play_action(pbp, qb_tiers)

    print("Analyzing throw power (deep ball)...")
    power_data = analyze_throw_power_proxy(pbp, qb_tiers)

    print("Building calibration tables...")
    calibration = build_attribute_calibration(depth_data, pressure_data, power_data)

    # Build final model
    model = {
        'model_name': 'passing_attribute_projection',
        'description': 'Maps QB passing attributes to NFL performance metrics',
        'data_source': 'NFL PBP 2019-2024',
        'accuracy_by_depth': depth_data,
        'pressure_performance': pressure_data,
        'play_action': pa_data,
        'throw_power_proxy': power_data,
        'attribute_calibration': calibration,
        'attributes_covered': [
            'throw_accuracy_short',
            'throw_accuracy_medium',
            'throw_accuracy_deep',
            'throw_power',
            'poise',
            'play_action'
        ]
    }

    # Export
    export_path = Path(__file__).parent.parent / "exports" / "passing_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert numpy types to native Python for JSON serialization
    def convert_to_native(obj):
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

    model = convert_to_native(model)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("PASSING ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    print("\nCOMPLETION BY DEPTH:")
    print(f"{'Tier':<12} {'Short':<10} {'Medium':<10} {'Deep':<10}")
    print("-" * 42)
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in depth_data:
            short = depth_data[tier].get('short', {}).get('completion_rate', 0)
            med = depth_data[tier].get('medium', {}).get('completion_rate', 0)
            deep = depth_data[tier].get('deep', {}).get('completion_rate', 0)
            print(f"{tier:<12} {short*100:>7.1f}%   {med*100:>7.1f}%   {deep*100:>7.1f}%")

    print("\nPRESSURE PERFORMANCE:")
    print(f"{'Tier':<12} {'Clean':<10} {'Pressure':<10} {'Penalty':<10}")
    print("-" * 42)
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in pressure_data:
            clean = pressure_data[tier].get('clean_pocket', 0)
            press = pressure_data[tier].get('under_pressure', 0)
            penalty = pressure_data[tier].get('pressure_penalty', 0)
            print(f"{tier:<12} {clean*100:>7.1f}%   {press*100:>7.1f}%   {penalty*100:>7.1f}%")

    print("\nATTRIBUTE CALIBRATION:")
    for attr, data in calibration.items():
        if 'effect_per_10_points' in data and data['effect_per_10_points']:
            print(f"  {attr}: +10 rating = +{data['effect_per_10_points']*100:.1f}% completion")
        elif 'spread_elite_to_bad' in data:
            print(f"  {attr}: Elite to Bad spread = {data['spread_elite_to_bad']*100:.1f}%")

    return model


if __name__ == "__main__":
    model = run_passing_projection()
