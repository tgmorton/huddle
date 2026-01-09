"""
Receiving Attribute Projection Model

Maps WR/receiver attributes to NFL performance data:
- catching: Catch rate
- catch_in_traffic: YAC / contested catching
- route_running: Separation at catch
- release: Cushion vs press coverage

Uses PBP and NGS receiving data to calibrate attribute effects.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_data():
    """Load play-by-play and NGS receiving data."""
    data_dir = Path(__file__).parent.parent / "data" / "cached"

    pbp = pd.read_parquet(data_dir / "pbp_2019_2024.parquet")
    ngs = pd.read_parquet(data_dir / "ngs_receiving.parquet")

    return pbp, ngs


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


def normalize_name(name):
    """Convert 'D.Cook' format to 'Dalvin Cook' compatible format for matching."""
    if pd.isna(name):
        return None
    # Extract last name for matching
    parts = name.split('.')
    if len(parts) >= 2:
        return parts[-1].strip()  # Return last name
    return name


def tier_receivers_by_yds_per_target(pbp):
    """Tier receivers into quartiles by yards/target for each season."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['receiver_player_name'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    # Get seasonal stats
    receiver_seasons = pass_plays.groupby(['season', 'receiver_player_name']).agg({
        'yards_gained': 'sum',
        'complete_pass': ['sum', 'count']
    }).reset_index()
    receiver_seasons.columns = ['season', 'receiver', 'yards', 'receptions', 'targets']

    # Filter to 30+ targets
    receiver_seasons = receiver_seasons[receiver_seasons['targets'] >= 30]

    # Yards per target
    receiver_seasons['yds_per_target'] = receiver_seasons['yards'] / receiver_seasons['targets']

    # Extract last name for matching with NGS
    receiver_seasons['last_name'] = receiver_seasons['receiver'].apply(normalize_name)

    # Quartile tiers
    receiver_seasons['tier'] = pd.qcut(
        receiver_seasons['yds_per_target'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']
    )

    return receiver_seasons


def analyze_separation(ngs, receiver_tiers):
    """Analyze separation by receiver tier (route running proxy)."""

    # Add last name to NGS for matching
    ngs = ngs.copy()
    ngs['last_name'] = ngs['player_last_name']

    # Merge NGS with tiers using last name
    ngs_merged = ngs.merge(
        receiver_tiers[['season', 'last_name', 'tier']],
        on=['season', 'last_name'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ngs_merged[ngs_merged['tier'] == tier]

        if len(tier_data) >= 10:
            sep = tier_data['avg_separation']
            results[tier] = {
                'avg_separation': round(sep.mean(), 3),
                'median': round(sep.median(), 3),
                'p25': round(sep.quantile(0.25), 3),
                'p75': round(sep.quantile(0.75), 3),
                'sample': len(tier_data)
            }

    return results


def analyze_cushion(ngs, receiver_tiers):
    """Analyze cushion by receiver tier (release ability proxy)."""

    # Add last name to NGS for matching
    ngs = ngs.copy()
    ngs['last_name'] = ngs['player_last_name']

    # Merge NGS with tiers using last name
    ngs_merged = ngs.merge(
        receiver_tiers[['season', 'last_name', 'tier']],
        on=['season', 'last_name'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ngs_merged[ngs_merged['tier'] == tier]

        if len(tier_data) >= 10:
            cushion = tier_data['avg_cushion']
            results[tier] = {
                'avg_cushion': round(cushion.mean(), 3),
                'median': round(cushion.median(), 3),
                'sample': len(tier_data)
            }

    return results


def analyze_yac(ngs, receiver_tiers):
    """Analyze YAC by receiver tier (catch in traffic proxy)."""

    # Add last name to NGS for matching
    ngs = ngs.copy()
    ngs['last_name'] = ngs['player_last_name']

    # Merge NGS with tiers using last name
    ngs_merged = ngs.merge(
        receiver_tiers[['season', 'last_name', 'tier']],
        on=['season', 'last_name'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ngs_merged[ngs_merged['tier'] == tier]

        if len(tier_data) >= 10:
            yac = tier_data['avg_yac']
            yac_above = tier_data['avg_yac_above_expectation']
            results[tier] = {
                'avg_yac': round(yac.mean(), 2),
                'avg_yac_above_expectation': round(yac_above.mean(), 2),
                'sample': len(tier_data)
            }

    return results


def analyze_catch_rate(pbp, receiver_tiers):
    """Analyze catch rate by receiver tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['receiver_player_name'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    # Merge tiers
    pass_plays = pass_plays.merge(
        receiver_tiers[['season', 'receiver', 'tier']],
        left_on=['season', 'receiver_player_name'],
        right_on=['season', 'receiver'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]

        if len(tier_plays) >= 100:
            catch_rate = tier_plays['complete_pass'].mean()
            results[tier] = {
                'catch_rate': round(catch_rate, 4),
                'sample': len(tier_plays)
            }

    return results


def analyze_catch_by_air_yards(pbp, receiver_tiers):
    """Analyze catch rate by air yards depth for each tier."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['receiver_player_name'].notna()) &
        (pbp['complete_pass'].notna()) &
        (pbp['air_yards'].notna())
    ].copy()

    def get_depth(air_yards):
        if air_yards < 0:
            return 'behind_los'
        elif air_yards < 10:
            return 'short'
        elif air_yards < 20:
            return 'medium'
        else:
            return 'deep'

    pass_plays['depth'] = pass_plays['air_yards'].apply(get_depth)

    # Merge tiers
    pass_plays = pass_plays.merge(
        receiver_tiers[['season', 'receiver', 'tier']],
        left_on=['season', 'receiver_player_name'],
        right_on=['season', 'receiver'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = pass_plays[pass_plays['tier'] == tier]
        results[tier] = {}

        for depth in ['short', 'medium', 'deep']:
            depth_plays = tier_plays[tier_plays['depth'] == depth]
            if len(depth_plays) >= 50:
                results[tier][depth] = {
                    'catch_rate': round(depth_plays['complete_pass'].mean(), 4),
                    'sample': len(depth_plays)
                }

    return results


def analyze_catch_by_separation(ngs, receiver_tiers):
    """Analyze catch rate by separation level."""

    # Add last name to NGS for matching
    ngs = ngs.copy()
    ngs['last_name'] = ngs['player_last_name']

    # Merge NGS with tiers using last name
    ngs_merged = ngs.merge(
        receiver_tiers[['season', 'last_name', 'tier']],
        on=['season', 'last_name'],
        how='inner'
    )

    if len(ngs_merged) == 0:
        print("  Warning: No matching records for separation analysis")
        return {}

    # Filter valid separation data
    valid_sep = ngs_merged[ngs_merged['avg_separation'].notna()].copy()

    if len(valid_sep) < 30:
        print(f"  Warning: Not enough valid separation data ({len(valid_sep)} records)")
        return {}

    # Tier separation levels
    try:
        valid_sep['sep_level'] = pd.qcut(
            valid_sep['avg_separation'],
            q=[0, 0.25, 0.75, 1.0],
            labels=['Tight', 'Normal', 'Wide'],
            duplicates='drop'
        )
    except ValueError as e:
        print(f"  Warning: Could not create separation tiers: {e}")
        return {}

    results = {}
    for sep_level in ['Tight', 'Normal', 'Wide']:
        sep_data = valid_sep[valid_sep['sep_level'] == sep_level]

        if len(sep_data) >= 30:
            results[sep_level] = {
                'avg_catch_pct': round(sep_data['catch_percentage'].mean(), 2),
                'avg_separation': round(sep_data['avg_separation'].mean(), 3),
                'sample': len(sep_data)
            }

    return results


def build_attribute_calibration(sep_data, cushion_data, yac_data, catch_data, depth_data, sep_catch_data):
    """Build calibration tables for receiving attributes."""

    calibration = {}

    # ROUTE RUNNING (separation)
    if sep_data:
        calibration['route_running'] = {
            'nfl_metric': 'avg_separation_yards',
            'tier_data': {
                tier: data.get('avg_separation')
                for tier, data in sep_data.items()
            }
        }

        elite = sep_data.get('Elite', {}).get('avg_separation')
        bad = sep_data.get('Bad', {}).get('avg_separation')
        if elite and bad:
            spread = elite - bad
            calibration['route_running']['spread_elite_to_bad'] = round(spread, 3)
            calibration['route_running']['effect_per_10_points'] = round(spread / 55 * 10, 3)

    # RELEASE (cushion)
    if cushion_data:
        calibration['release'] = {
            'nfl_metric': 'avg_cushion_yards',
            'tier_data': {
                tier: data.get('avg_cushion')
                for tier, data in cushion_data.items()
            },
            'note': 'Higher cushion may indicate respect for speed OR inability to beat press'
        }

    # CATCHING (catch rate)
    if catch_data:
        calibration['catching'] = {
            'nfl_metric': 'catch_rate',
            'tier_data': {
                tier: data.get('catch_rate')
                for tier, data in catch_data.items()
            }
        }

        elite = catch_data.get('Elite', {}).get('catch_rate')
        bad = catch_data.get('Bad', {}).get('catch_rate')
        if elite and bad:
            spread = elite - bad
            calibration['catching']['spread_elite_to_bad'] = round(spread, 4)
            calibration['catching']['effect_per_10_points'] = round(spread / 55 * 10, 4)

    # CATCH IN TRAFFIC (YAC above expectation)
    if yac_data:
        calibration['catch_in_traffic'] = {
            'nfl_metric': 'yac_above_expectation',
            'tier_data': {
                tier: data.get('avg_yac_above_expectation')
                for tier, data in yac_data.items()
            }
        }

        elite = yac_data.get('Elite', {}).get('avg_yac_above_expectation')
        bad = yac_data.get('Bad', {}).get('avg_yac_above_expectation')
        if elite is not None and bad is not None:
            spread = elite - bad
            calibration['catch_in_traffic']['spread_elite_to_bad'] = round(spread, 3)
            calibration['catch_in_traffic']['effect_per_10_points'] = round(spread / 55 * 10, 3)

    # Catch rate by separation correlation
    if sep_catch_data:
        calibration['separation_to_catch_correlation'] = {
            'description': 'How separation affects catch rate',
            'tight_separation': sep_catch_data.get('Tight', {}),
            'normal_separation': sep_catch_data.get('Normal', {}),
            'wide_separation': sep_catch_data.get('Wide', {})
        }

    return calibration


def run_receiving_projection():
    """Run the receiving attribute projection analysis."""

    print("Loading data...")
    pbp, ngs = load_data()
    print(f"Loaded {len(pbp)} plays, {len(ngs)} NGS receiving records")

    print("\nTiering receivers by yards/target...")
    receiver_tiers = tier_receivers_by_yds_per_target(pbp)
    print(f"Tiered {len(receiver_tiers)} receiver seasons")

    print("\nAnalyzing separation (route running)...")
    sep_data = analyze_separation(ngs, receiver_tiers)

    print("Analyzing cushion (release)...")
    cushion_data = analyze_cushion(ngs, receiver_tiers)

    print("Analyzing YAC (catch in traffic)...")
    yac_data = analyze_yac(ngs, receiver_tiers)

    print("Analyzing catch rate...")
    catch_data = analyze_catch_rate(pbp, receiver_tiers)

    print("Analyzing catch rate by depth...")
    depth_data = analyze_catch_by_air_yards(pbp, receiver_tiers)

    print("Analyzing separation to catch correlation...")
    sep_catch_data = analyze_catch_by_separation(ngs, receiver_tiers)

    print("Building calibration tables...")
    calibration = build_attribute_calibration(
        sep_data, cushion_data, yac_data, catch_data, depth_data, sep_catch_data
    )

    # Build final model
    model = {
        'model_name': 'receiving_attribute_projection',
        'description': 'Maps WR receiving attributes to NFL performance metrics',
        'data_source': 'NFL PBP and NGS 2019-2024',
        'separation': sep_data,
        'cushion': cushion_data,
        'yac': yac_data,
        'catch_rate': catch_data,
        'catch_by_depth': depth_data,
        'separation_to_catch': sep_catch_data,
        'attribute_calibration': calibration,
        'attributes_covered': [
            'route_running',
            'catching',
            'catch_in_traffic',
            'release'
        ]
    }

    # Convert and export
    model = convert_to_native(model)

    export_path = Path(__file__).parent.parent / "exports" / "receiving_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("RECEIVING ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    if sep_data:
        print("\nSEPARATION (Route Running):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in sep_data:
                sep = sep_data[tier].get('avg_separation', 0)
                print(f"  {tier}: {sep:.3f} yards")

    if yac_data:
        print("\nYAC ABOVE EXPECTATION (Catch in Traffic):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in yac_data:
                yac = yac_data[tier].get('avg_yac_above_expectation', 0)
                print(f"  {tier}: {yac:+.2f} yards")

    if catch_data:
        print("\nCATCH RATE:")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in catch_data:
                rate = catch_data[tier].get('catch_rate', 0)
                print(f"  {tier}: {rate*100:.1f}%")

    if sep_catch_data:
        print("\nSEPARATION → CATCH RATE:")
        for sep_level in ['Tight', 'Normal', 'Wide']:
            if sep_level in sep_catch_data:
                catch = sep_catch_data[sep_level].get('avg_catch_pct', 0)
                sep = sep_catch_data[sep_level].get('avg_separation', 0)
                print(f"  {sep_level} ({sep:.2f} yds): {catch:.1f}% catch")

    print("\nATTRIBUTE CALIBRATION:")
    for attr, data in calibration.items():
        if 'effect_per_10_points' in data and data['effect_per_10_points']:
            val = data['effect_per_10_points']
            if abs(val) < 1:
                print(f"  {attr}: +10 rating = +{val:.3f}")
            else:
                print(f"  {attr}: +10 rating = +{val:.1f}")

    return model


if __name__ == "__main__":
    model = run_receiving_projection()
