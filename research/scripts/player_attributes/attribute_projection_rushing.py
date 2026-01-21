"""
Rushing Attribute Projection Model

Maps RB/ballcarrier attributes to NFL performance data:
- elusiveness: Yards after contact
- break_tackle: Broken tackle rate / YAC
- ball_carrier_vision: Yards before contact
- trucking: Short yardage success rate
- carrying: Fumble rate

Uses PBP and NGS rushing data to calibrate attribute effects.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def load_data():
    """Load play-by-play and NGS rushing data."""
    data_dir = Path(__file__).parent.parent / "data" / "cached"

    pbp = pd.read_parquet(data_dir / "pbp_2019_2024.parquet")
    ngs = pd.read_parquet(data_dir / "ngs_rushing.parquet")

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


def tier_rbs_by_ypc(pbp):
    """Tier RBs into quartiles by YPC for each season."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rusher_player_name'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Get seasonal YPC
    rb_seasons = run_plays.groupby(['season', 'rusher_player_name']).agg({
        'rushing_yards': ['mean', 'count', 'sum']
    }).reset_index()
    rb_seasons.columns = ['season', 'rusher', 'ypc', 'carries', 'total_yards']

    # Filter to 50+ carries
    rb_seasons = rb_seasons[rb_seasons['carries'] >= 50]

    # Quartile tiers
    rb_seasons['tier'] = pd.qcut(
        rb_seasons['ypc'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']
    )

    return rb_seasons


def analyze_yards_after_contact(ngs, pbp, rb_tiers):
    """Analyze yards after contact by RB tier (elusiveness proxy)."""

    # NGS has rushing stats with yards_after_contact
    if 'avg_yards_after_contact' not in ngs.columns:
        # Try alternative column names
        yac_col = None
        for col in ngs.columns:
            if 'after_contact' in col.lower():
                yac_col = col
                break

        if not yac_col:
            print("  Warning: No yards after contact column found in NGS data")
            return {}

        ngs = ngs.rename(columns={yac_col: 'avg_yards_after_contact'})

    # Merge NGS with tiers
    ngs_merged = ngs.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'player_display_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ngs_merged[ngs_merged['tier'] == tier]

        if len(tier_data) >= 10:
            yac = tier_data['avg_yards_after_contact']
            results[tier] = {
                'avg_yards_after_contact': round(yac.mean(), 2),
                'median': round(yac.median(), 2),
                'p25': round(yac.quantile(0.25), 2),
                'p75': round(yac.quantile(0.75), 2),
                'sample': len(tier_data)
            }

    return results


def analyze_yards_before_contact(ngs, rb_tiers):
    """Analyze yards before contact by RB tier (vision proxy)."""

    # Check for yards before contact column
    ybc_col = None
    for col in ngs.columns:
        if 'before_contact' in col.lower() or 'time_behind' in col.lower():
            ybc_col = col
            break

    if not ybc_col:
        # Alternative: derive from total yards - YAC if available
        if 'avg_rush_yards' in ngs.columns and 'avg_yards_after_contact' in ngs.columns:
            ngs['derived_ybc'] = ngs['avg_rush_yards'] - ngs['avg_yards_after_contact']
            ybc_col = 'derived_ybc'
        else:
            print("  Warning: No yards before contact data available")
            return {}

    # Merge NGS with tiers
    ngs_merged = ngs.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'player_display_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ngs_merged[ngs_merged['tier'] == tier]

        if len(tier_data) >= 10 and ybc_col in tier_data.columns:
            ybc = tier_data[ybc_col].dropna()
            if len(ybc) >= 5:
                results[tier] = {
                    'avg_yards_before_contact': round(ybc.mean(), 2),
                    'median': round(ybc.median(), 2),
                    'sample': len(ybc)
                }

    return results


def analyze_fumble_rate(pbp, rb_tiers):
    """Analyze fumble rate by RB tier (carrying proxy)."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rusher_player_name'].notna())
    ].copy()

    # Determine fumbles
    if 'fumble' in run_plays.columns:
        run_plays['had_fumble'] = run_plays['fumble'] == 1
    elif 'fumble_lost' in run_plays.columns:
        run_plays['had_fumble'] = run_plays['fumble_lost'] == 1
    else:
        print("  Warning: No fumble column found")
        return {}

    # Merge tiers
    run_plays = run_plays.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'rusher_player_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = run_plays[run_plays['tier'] == tier]

        if len(tier_plays) >= 100:
            fumble_rate = tier_plays['had_fumble'].mean()
            results[tier] = {
                'fumble_rate': round(fumble_rate, 5),
                'fumble_rate_per_100': round(fumble_rate * 100, 2),
                'sample': len(tier_plays)
            }

    return results


def analyze_short_yardage(pbp, rb_tiers):
    """Analyze short yardage success by RB tier (trucking proxy)."""

    # Short yardage: 3rd/4th down with 1-2 yards to go
    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rusher_player_name'].notna()) &
        (pbp['down'].isin([3, 4])) &
        (pbp['ydstogo'] <= 2)
    ].copy()

    # Success = got first down or TD
    run_plays['success'] = (
        (run_plays['first_down'] == 1) |
        (run_plays['rushing_yards'] >= run_plays['ydstogo']) |
        (run_plays['td_player_name'].notna())
    )

    # Merge tiers
    run_plays = run_plays.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'rusher_player_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = run_plays[run_plays['tier'] == tier]

        if len(tier_plays) >= 50:
            success_rate = tier_plays['success'].mean()
            avg_yards = tier_plays['rushing_yards'].mean()
            results[tier] = {
                'success_rate': round(success_rate, 4),
                'avg_yards': round(avg_yards, 2),
                'sample': len(tier_plays)
            }

    return results


def analyze_stuff_rate(pbp, rb_tiers):
    """Analyze stuff rate (TFL) by RB tier."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rusher_player_name'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Stuff = 0 or negative yards
    run_plays['stuffed'] = run_plays['rushing_yards'] <= 0

    # Merge tiers
    run_plays = run_plays.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'rusher_player_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = run_plays[run_plays['tier'] == tier]

        if len(tier_plays) >= 100:
            stuff_rate = tier_plays['stuffed'].mean()
            results[tier] = {
                'stuff_rate': round(stuff_rate, 4),
                'sample': len(tier_plays)
            }

    return results


def analyze_explosive_rate(pbp, rb_tiers):
    """Analyze explosive run rate (10+ yards) by RB tier."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rusher_player_name'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Explosive = 10+ yards
    run_plays['explosive'] = run_plays['rushing_yards'] >= 10

    # Merge tiers
    run_plays = run_plays.merge(
        rb_tiers[['season', 'rusher', 'tier']],
        left_on=['season', 'rusher_player_name'],
        right_on=['season', 'rusher'],
        how='inner'
    )

    results = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_plays = run_plays[run_plays['tier'] == tier]

        if len(tier_plays) >= 100:
            explosive_rate = tier_plays['explosive'].mean()
            results[tier] = {
                'explosive_rate': round(explosive_rate, 4),
                'sample': len(tier_plays)
            }

    return results


def build_attribute_calibration(yac_data, ybc_data, fumble_data, short_data, stuff_data, explosive_data):
    """Build calibration tables for rushing attributes."""

    calibration = {}

    # ELUSIVENESS (yards after contact)
    if yac_data:
        calibration['elusiveness'] = {
            'nfl_metric': 'yards_after_contact',
            'tier_data': {
                tier: data.get('avg_yards_after_contact')
                for tier, data in yac_data.items()
            }
        }

        elite = yac_data.get('Elite', {}).get('avg_yards_after_contact')
        bad = yac_data.get('Bad', {}).get('avg_yards_after_contact')
        if elite and bad:
            spread = elite - bad
            calibration['elusiveness']['spread_elite_to_bad'] = round(spread, 2)
            calibration['elusiveness']['effect_per_10_points'] = round(spread / 55 * 10, 3)

    # BALL CARRIER VISION (yards before contact)
    if ybc_data:
        calibration['ball_carrier_vision'] = {
            'nfl_metric': 'yards_before_contact',
            'tier_data': {
                tier: data.get('avg_yards_before_contact')
                for tier, data in ybc_data.items()
            }
        }

        elite = ybc_data.get('Elite', {}).get('avg_yards_before_contact')
        bad = ybc_data.get('Bad', {}).get('avg_yards_before_contact')
        if elite and bad:
            spread = elite - bad
            calibration['ball_carrier_vision']['spread_elite_to_bad'] = round(spread, 2)
            calibration['ball_carrier_vision']['effect_per_10_points'] = round(spread / 55 * 10, 3)

    # CARRYING (inverse fumble rate)
    if fumble_data:
        calibration['carrying'] = {
            'nfl_metric': 'fumble_rate_inverse',
            'tier_data': {
                tier: data.get('fumble_rate')
                for tier, data in fumble_data.items()
            },
            'note': 'Higher carrying = lower fumble rate'
        }

        elite = fumble_data.get('Elite', {}).get('fumble_rate')
        bad = fumble_data.get('Bad', {}).get('fumble_rate')
        if elite is not None and bad is not None:
            spread = bad - elite  # Inverted: bad has higher fumble rate
            calibration['carrying']['spread_elite_to_bad'] = round(spread, 5)
            calibration['carrying']['effect_per_10_points'] = round(-spread / 55 * 10, 5)

    # TRUCKING (short yardage success)
    if short_data:
        calibration['trucking'] = {
            'nfl_metric': 'short_yardage_success_rate',
            'tier_data': {
                tier: data.get('success_rate')
                for tier, data in short_data.items()
            }
        }

        elite = short_data.get('Elite', {}).get('success_rate')
        bad = short_data.get('Bad', {}).get('success_rate')
        if elite and bad:
            spread = elite - bad
            calibration['trucking']['spread_elite_to_bad'] = round(spread, 4)
            calibration['trucking']['effect_per_10_points'] = round(spread / 55 * 10, 4)

    # BREAK TACKLE (inverse stuff rate + explosive rate)
    if stuff_data and explosive_data:
        calibration['break_tackle'] = {
            'nfl_metric': 'stuff_rate_and_explosive_rate',
            'stuff_rate_by_tier': {
                tier: data.get('stuff_rate')
                for tier, data in stuff_data.items()
            },
            'explosive_rate_by_tier': {
                tier: data.get('explosive_rate')
                for tier, data in explosive_data.items()
            }
        }

        elite_stuff = stuff_data.get('Elite', {}).get('stuff_rate')
        bad_stuff = stuff_data.get('Bad', {}).get('stuff_rate')
        if elite_stuff is not None and bad_stuff is not None:
            calibration['break_tackle']['stuff_spread'] = round(bad_stuff - elite_stuff, 4)

        elite_exp = explosive_data.get('Elite', {}).get('explosive_rate')
        bad_exp = explosive_data.get('Bad', {}).get('explosive_rate')
        if elite_exp is not None and bad_exp is not None:
            calibration['break_tackle']['explosive_spread'] = round(elite_exp - bad_exp, 4)

    return calibration


def run_rushing_projection():
    """Run the rushing attribute projection analysis."""

    print("Loading data...")
    pbp, ngs = load_data()
    print(f"Loaded {len(pbp)} plays, {len(ngs)} NGS rushing records")

    print("\nTiering RBs by YPC...")
    rb_tiers = tier_rbs_by_ypc(pbp)
    print(f"Tiered {len(rb_tiers)} RB seasons")

    print("\nAnalyzing yards after contact (elusiveness)...")
    yac_data = analyze_yards_after_contact(ngs, pbp, rb_tiers)

    print("Analyzing yards before contact (vision)...")
    ybc_data = analyze_yards_before_contact(ngs, rb_tiers)

    print("Analyzing fumble rate (carrying)...")
    fumble_data = analyze_fumble_rate(pbp, rb_tiers)

    print("Analyzing short yardage (trucking)...")
    short_data = analyze_short_yardage(pbp, rb_tiers)

    print("Analyzing stuff rate...")
    stuff_data = analyze_stuff_rate(pbp, rb_tiers)

    print("Analyzing explosive rate...")
    explosive_data = analyze_explosive_rate(pbp, rb_tiers)

    print("Building calibration tables...")
    calibration = build_attribute_calibration(
        yac_data, ybc_data, fumble_data, short_data, stuff_data, explosive_data
    )

    # Build final model
    model = {
        'model_name': 'rushing_attribute_projection',
        'description': 'Maps RB rushing attributes to NFL performance metrics',
        'data_source': 'NFL PBP and NGS 2019-2024',
        'yards_after_contact': yac_data,
        'yards_before_contact': ybc_data,
        'fumble_rate': fumble_data,
        'short_yardage': short_data,
        'stuff_rate': stuff_data,
        'explosive_rate': explosive_data,
        'attribute_calibration': calibration,
        'attributes_covered': [
            'elusiveness',
            'ball_carrier_vision',
            'break_tackle',
            'trucking',
            'carrying'
        ]
    }

    # Convert and export
    model = convert_to_native(model)

    export_path = Path(__file__).parent.parent / "exports" / "rushing_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("RUSHING ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    if yac_data:
        print("\nYARDS AFTER CONTACT (Elusiveness):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in yac_data:
                yac = yac_data[tier].get('avg_yards_after_contact', 0)
                print(f"  {tier}: {yac:.2f} YAC")

    if fumble_data:
        print("\nFUMBLE RATE (Carrying):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in fumble_data:
                rate = fumble_data[tier].get('fumble_rate', 0)
                print(f"  {tier}: {rate*100:.2f}% per carry")

    if short_data:
        print("\nSHORT YARDAGE SUCCESS (Trucking):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            if tier in short_data:
                rate = short_data[tier].get('success_rate', 0)
                print(f"  {tier}: {rate*100:.1f}% success")

    if stuff_data and explosive_data:
        print("\nSTUFF vs EXPLOSIVE RATE (Break Tackle):")
        for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
            stuff = stuff_data.get(tier, {}).get('stuff_rate', 0)
            exp = explosive_data.get(tier, {}).get('explosive_rate', 0)
            print(f"  {tier}: {stuff*100:.1f}% stuffed, {exp*100:.1f}% explosive")

    print("\nATTRIBUTE CALIBRATION:")
    for attr, data in calibration.items():
        if 'effect_per_10_points' in data and data['effect_per_10_points']:
            print(f"  {attr}: +10 rating = +{data['effect_per_10_points']:.3f}")
        elif 'spread_elite_to_bad' in data:
            print(f"  {attr}: Elite to Bad spread = {data['spread_elite_to_bad']}")

    return model


if __name__ == "__main__":
    model = run_rushing_projection()
