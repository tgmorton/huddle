"""
Blocking Attribute Projection Model

Maps OL/DL blocking attributes to NFL performance data:
- pass_block: Pressure rate allowed
- run_block: Yards before contact / stuff rate
- block_shedding: Pressure rate generated (DL)
- pass_rush: Sack rate (DL)

Uses team-level PBP data since individual OL/DL stats aren't available.
Leverages the blocking_model_deep.json for calibration.
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


def analyze_team_pressure_rates(pbp):
    """Analyze pressure rates by team (OL vs DL performance)."""

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['posteam'].notna()) &
        (pbp['defteam'].notna())
    ].copy()

    # Calculate pressure indicators
    pass_plays['pressured'] = (
        (pass_plays.get('sack', 0) == 1) |
        (pass_plays.get('qb_hit', 0) == 1)
    )

    # Offensive line stats (pressure allowed)
    ol_stats = pass_plays.groupby(['season', 'posteam']).agg({
        'pressured': ['mean', 'count'],
        'sack': 'mean',
        'qb_hit': 'mean'
    }).reset_index()
    ol_stats.columns = ['season', 'team', 'pressure_allowed', 'dropbacks', 'sack_rate_allowed', 'hit_rate']

    # Tier OL by pressure allowed
    ol_stats['ol_tier'] = pd.qcut(
        ol_stats['pressure_allowed'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Elite', 'Above Avg', 'Below Avg', 'Bad']  # Low pressure = Elite
    )

    # Defensive line stats (pressure generated)
    dl_stats = pass_plays.groupby(['season', 'defteam']).agg({
        'pressured': ['mean', 'count'],
        'sack': 'mean',
        'qb_hit': 'mean'
    }).reset_index()
    dl_stats.columns = ['season', 'team', 'pressure_generated', 'dropbacks', 'sack_rate', 'hit_rate']

    # Tier DL by pressure generated
    dl_stats['dl_tier'] = pd.qcut(
        dl_stats['pressure_generated'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']  # High pressure = Elite
    )

    return ol_stats, dl_stats


def analyze_run_blocking(pbp):
    """Analyze run blocking efficiency by team."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['posteam'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Stuff rate (0 or negative yards)
    run_plays['stuffed'] = run_plays['rushing_yards'] <= 0

    # Explosive rate (10+ yards)
    run_plays['explosive'] = run_plays['rushing_yards'] >= 10

    # Team run blocking stats
    rb_stats = run_plays.groupby(['season', 'posteam']).agg({
        'rushing_yards': 'mean',
        'stuffed': 'mean',
        'explosive': 'mean'
    }).reset_index()
    rb_stats.columns = ['season', 'team', 'ypc', 'stuff_rate', 'explosive_rate']

    # Tier by YPC (proxy for run blocking)
    rb_stats['run_block_tier'] = pd.qcut(
        rb_stats['ypc'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']
    )

    return rb_stats


def analyze_run_defense(pbp):
    """Analyze run defense (DL block shedding) by team."""

    run_plays = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['defteam'].notna()) &
        (pbp['rushing_yards'].notna())
    ].copy()

    # Stuff rate (defense perspective - 0 or negative yards allowed)
    run_plays['stuffed'] = run_plays['rushing_yards'] <= 0

    # Team run defense stats
    rd_stats = run_plays.groupby(['season', 'defteam']).agg({
        'rushing_yards': 'mean',
        'stuffed': 'mean'
    }).reset_index()
    rd_stats.columns = ['season', 'team', 'ypc_allowed', 'stuff_rate_generated']

    # Tier by stuff rate (proxy for block shedding)
    rd_stats['block_shed_tier'] = pd.qcut(
        rd_stats['stuff_rate_generated'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Bad', 'Below Avg', 'Above Avg', 'Elite']
    )

    return rd_stats


def build_blocking_calibration(ol_stats, dl_stats, rb_stats, rd_stats):
    """Build calibration tables for blocking attributes."""

    calibration = {}

    # PASS BLOCKING (pressure allowed)
    pass_block_by_tier = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = ol_stats[ol_stats['ol_tier'] == tier]
        if len(tier_data) >= 5:
            pass_block_by_tier[tier] = {
                'pressure_allowed': round(tier_data['pressure_allowed'].mean(), 4),
                'sack_rate_allowed': round(tier_data['sack_rate_allowed'].mean(), 4),
                'sample': len(tier_data)
            }

    calibration['pass_block'] = {
        'nfl_metric': 'pressure_rate_allowed',
        'tier_data': pass_block_by_tier,
        'note': 'Lower pressure allowed = better pass blocking'
    }

    if 'Elite' in pass_block_by_tier and 'Bad' in pass_block_by_tier:
        elite_pressure = pass_block_by_tier['Elite']['pressure_allowed']
        bad_pressure = pass_block_by_tier['Bad']['pressure_allowed']
        spread = bad_pressure - elite_pressure  # Bad has more pressure
        calibration['pass_block']['spread_elite_to_bad'] = round(spread, 4)
        calibration['pass_block']['effect_per_10_points'] = round(-spread / 55 * 10, 4)

    # RUN BLOCKING (stuff rate, YPC)
    run_block_by_tier = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = rb_stats[rb_stats['run_block_tier'] == tier]
        if len(tier_data) >= 5:
            run_block_by_tier[tier] = {
                'ypc': round(tier_data['ypc'].mean(), 2),
                'stuff_rate': round(tier_data['stuff_rate'].mean(), 4),
                'explosive_rate': round(tier_data['explosive_rate'].mean(), 4),
                'sample': len(tier_data)
            }

    calibration['run_block'] = {
        'nfl_metric': 'yards_per_carry_and_stuff_rate',
        'tier_data': run_block_by_tier
    }

    if 'Elite' in run_block_by_tier and 'Bad' in run_block_by_tier:
        elite_ypc = run_block_by_tier['Elite']['ypc']
        bad_ypc = run_block_by_tier['Bad']['ypc']
        spread = elite_ypc - bad_ypc
        calibration['run_block']['ypc_spread'] = round(spread, 2)
        calibration['run_block']['effect_per_10_points'] = round(spread / 55 * 10, 3)

    # PASS RUSH (pressure generated)
    pass_rush_by_tier = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = dl_stats[dl_stats['dl_tier'] == tier]
        if len(tier_data) >= 5:
            pass_rush_by_tier[tier] = {
                'pressure_generated': round(tier_data['pressure_generated'].mean(), 4),
                'sack_rate': round(tier_data['sack_rate'].mean(), 4),
                'sample': len(tier_data)
            }

    calibration['pass_rush'] = {
        'nfl_metric': 'pressure_rate_generated',
        'tier_data': pass_rush_by_tier,
        'note': 'Higher pressure generated = better pass rush'
    }

    if 'Elite' in pass_rush_by_tier and 'Bad' in pass_rush_by_tier:
        elite_pressure = pass_rush_by_tier['Elite']['pressure_generated']
        bad_pressure = pass_rush_by_tier['Bad']['pressure_generated']
        spread = elite_pressure - bad_pressure
        calibration['pass_rush']['spread_elite_to_bad'] = round(spread, 4)
        calibration['pass_rush']['effect_per_10_points'] = round(spread / 55 * 10, 4)

    # BLOCK SHEDDING (stuff rate generated)
    block_shed_by_tier = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        tier_data = rd_stats[rd_stats['block_shed_tier'] == tier]
        if len(tier_data) >= 5:
            block_shed_by_tier[tier] = {
                'stuff_rate_generated': round(tier_data['stuff_rate_generated'].mean(), 4),
                'ypc_allowed': round(tier_data['ypc_allowed'].mean(), 2),
                'sample': len(tier_data)
            }

    calibration['block_shedding'] = {
        'nfl_metric': 'stuff_rate_generated',
        'tier_data': block_shed_by_tier
    }

    if 'Elite' in block_shed_by_tier and 'Bad' in block_shed_by_tier:
        elite_stuff = block_shed_by_tier['Elite']['stuff_rate_generated']
        bad_stuff = block_shed_by_tier['Bad']['stuff_rate_generated']
        spread = elite_stuff - bad_stuff
        calibration['block_shedding']['spread_elite_to_bad'] = round(spread, 4)
        calibration['block_shedding']['effect_per_10_points'] = round(spread / 55 * 10, 4)

    return calibration


def run_blocking_projection():
    """Run the blocking attribute projection analysis."""

    print("Loading data...")
    pbp = load_data()
    print(f"Loaded {len(pbp)} plays")

    print("\nAnalyzing team pressure rates...")
    ol_stats, dl_stats = analyze_team_pressure_rates(pbp)
    print(f"Analyzed {len(ol_stats)} team-seasons for OL, {len(dl_stats)} for DL")

    print("Analyzing run blocking...")
    rb_stats = analyze_run_blocking(pbp)

    print("Analyzing run defense (block shedding)...")
    rd_stats = analyze_run_defense(pbp)

    print("Building calibration tables...")
    calibration = build_blocking_calibration(ol_stats, dl_stats, rb_stats, rd_stats)

    # Build final model
    model = {
        'model_name': 'blocking_attribute_projection',
        'description': 'Maps OL/DL blocking attributes to NFL performance metrics',
        'data_source': 'NFL PBP 2019-2024 (team-level)',
        'note': 'Individual OL/DL stats not available in PBP; using team-level proxies',
        'ol_pass_block': {tier: data for tier, data in calibration['pass_block']['tier_data'].items()},
        'ol_run_block': {tier: data for tier, data in calibration['run_block']['tier_data'].items()},
        'dl_pass_rush': {tier: data for tier, data in calibration['pass_rush']['tier_data'].items()},
        'dl_block_shed': {tier: data for tier, data in calibration['block_shedding']['tier_data'].items()},
        'attribute_calibration': calibration,
        'attributes_covered': [
            'pass_block',
            'run_block',
            'pass_rush',
            'block_shedding'
        ]
    }

    # Convert and export
    model = convert_to_native(model)

    export_path = Path(__file__).parent.parent / "exports" / "blocking_projection.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(model, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*60)
    print("BLOCKING ATTRIBUTE PROJECTION SUMMARY")
    print("="*60)

    print("\nPASS BLOCKING (Pressure Allowed):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in calibration['pass_block']['tier_data']:
            data = calibration['pass_block']['tier_data'][tier]
            print(f"  {tier}: {data['pressure_allowed']*100:.1f}% pressure, {data['sack_rate_allowed']*100:.1f}% sack")

    print("\nRUN BLOCKING (YPC / Stuff Rate):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in calibration['run_block']['tier_data']:
            data = calibration['run_block']['tier_data'][tier]
            print(f"  {tier}: {data['ypc']:.2f} YPC, {data['stuff_rate']*100:.1f}% stuffed")

    print("\nPASS RUSH (Pressure Generated):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in calibration['pass_rush']['tier_data']:
            data = calibration['pass_rush']['tier_data'][tier]
            print(f"  {tier}: {data['pressure_generated']*100:.1f}% pressure, {data['sack_rate']*100:.1f}% sack")

    print("\nBLOCK SHEDDING (Stuff Rate Generated):")
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Bad']:
        if tier in calibration['block_shedding']['tier_data']:
            data = calibration['block_shedding']['tier_data'][tier]
            print(f"  {tier}: {data['stuff_rate_generated']*100:.1f}% stuff, {data['ypc_allowed']:.2f} YPC allowed")

    print("\nATTRIBUTE EFFECTS:")
    for attr in ['pass_block', 'run_block', 'pass_rush', 'block_shedding']:
        if 'effect_per_10_points' in calibration[attr]:
            effect = calibration[attr]['effect_per_10_points']
            if attr == 'run_block':
                print(f"  {attr}: +10 rating = +{effect:.3f} YPC")
            else:
                print(f"  {attr}: +10 rating = {effect*100:+.2f}% rate")

    return model


if __name__ == "__main__":
    model = run_blocking_projection()
