#!/usr/bin/env python3
"""
Compute Defensive Value (DV) from Play-by-Play Data

Creates a performance metric for defensive players similar to AV,
using play-by-play events:
- Sacks (weighted heavily)
- Interceptions (weighted heavily)
- Tackles for loss
- Pass defenses / PBUs
- QB hits
- Forced fumbles
- Solo/assist tackles

The weights are calibrated to roughly match Pro Football Reference's
Approximate Value scale.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RESEARCH_DIR = Path(__file__).parent.parent
CACHED_DIR = RESEARCH_DIR / "data" / "cached"
EXPORTS_DIR = RESEARCH_DIR / "exports"


# =============================================================================
# Defensive Value Weights
# =============================================================================
# Calibrated to approximate PFR's AV scale
# A star defensive player gets ~10-15 AV per season
# Elite plays (sacks, INTs) are worth more than volume plays (tackles)

DV_WEIGHTS = {
    'sack': 4.0,           # Full sack
    'half_sack': 2.0,      # Half sack
    'interception': 5.0,   # Interception
    'fumble_forced': 3.0,  # Forced fumble
    'fumble_recovery': 2.0,# Fumble recovery
    'pass_defense': 1.5,   # Pass breakup
    'qb_hit': 0.5,         # QB hit (no sack)
    'tackle_for_loss': 1.0,# TFL
    'solo_tackle': 0.3,    # Solo tackle
    'assist_tackle': 0.15, # Assist tackle
}


def compute_defensive_value():
    """Compute DV for all defensive players from PBP data."""
    print("Loading play-by-play data...")
    pbp = pd.read_parquet(CACHED_DIR / "pbp_2019_2024.parquet")

    print(f"  {len(pbp):,} plays loaded")
    print(f"  Seasons: {sorted(pbp['season'].unique())}")

    # Initialize player stats dictionary
    # Key: (player_id, season), Value: dict of stats
    player_stats = {}

    print("\nAggregating defensive plays...")

    # =========================================================================
    # Sacks
    # =========================================================================
    sacks = pbp[pbp['sack'] == 1].copy()
    print(f"  Processing {len(sacks):,} sacks...")

    for _, play in sacks.iterrows():
        season = play['season']

        # Full sack
        if pd.notna(play.get('sack_player_id')):
            key = (play['sack_player_id'], season)
            if key not in player_stats:
                player_stats[key] = {'player_name': play.get('sack_player_name'), 'season': season}
            player_stats[key]['sacks'] = player_stats[key].get('sacks', 0) + 1

        # Half sacks
        for i in [1, 2]:
            col = f'half_sack_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'half_sack_{i}_player_name'), 'season': season}
                player_stats[key]['half_sacks'] = player_stats[key].get('half_sacks', 0) + 1

    # =========================================================================
    # Interceptions
    # =========================================================================
    ints = pbp[pbp['interception'] == 1].copy()
    print(f"  Processing {len(ints):,} interceptions...")

    for _, play in ints.iterrows():
        season = play['season']
        if pd.notna(play.get('interception_player_id')):
            key = (play['interception_player_id'], season)
            if key not in player_stats:
                player_stats[key] = {'player_name': play.get('interception_player_name'), 'season': season}
            player_stats[key]['interceptions'] = player_stats[key].get('interceptions', 0) + 1

    # =========================================================================
    # Forced Fumbles
    # =========================================================================
    ff = pbp[pbp['fumble_forced'] == 1].copy()
    print(f"  Processing {len(ff):,} forced fumbles...")

    for _, play in ff.iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'forced_fumble_player_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'forced_fumble_player_{i}_player_name'), 'season': season}
                player_stats[key]['forced_fumbles'] = player_stats[key].get('forced_fumbles', 0) + 1

    # =========================================================================
    # Fumble Recoveries
    # =========================================================================
    for _, play in pbp[pbp['fumble'] == 1].iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'fumble_recovery_{i}_player_id'
            if pd.notna(play.get(col)):
                # Only count if recovered by defense
                recovery_team = play.get(f'fumble_recovery_{i}_team')
                if recovery_team and recovery_team == play.get('defteam'):
                    key = (play[col], season)
                    if key not in player_stats:
                        player_stats[key] = {'player_name': play.get(f'fumble_recovery_{i}_player_name'), 'season': season}
                    player_stats[key]['fumble_recoveries'] = player_stats[key].get('fumble_recoveries', 0) + 1

    # =========================================================================
    # Pass Defenses (PBUs)
    # =========================================================================
    pds = pbp[pbp['pass_defense_1_player_id'].notna()].copy()
    print(f"  Processing {len(pds):,} pass defenses...")

    for _, play in pds.iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'pass_defense_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'pass_defense_{i}_player_name'), 'season': season}
                player_stats[key]['pass_defenses'] = player_stats[key].get('pass_defenses', 0) + 1

    # =========================================================================
    # QB Hits (non-sack)
    # =========================================================================
    hits = pbp[(pbp['qb_hit'] == 1) & (pbp['sack'] != 1)].copy()
    print(f"  Processing {len(hits):,} QB hits...")

    for _, play in hits.iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'qb_hit_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'qb_hit_{i}_player_name'), 'season': season}
                player_stats[key]['qb_hits'] = player_stats[key].get('qb_hits', 0) + 1

    # =========================================================================
    # Tackles for Loss
    # =========================================================================
    tfls = pbp[pbp['tackled_for_loss'] == 1].copy()
    print(f"  Processing {len(tfls):,} tackles for loss...")

    for _, play in tfls.iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'tackle_for_loss_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'tackle_for_loss_{i}_player_name'), 'season': season}
                player_stats[key]['tackles_for_loss'] = player_stats[key].get('tackles_for_loss', 0) + 1

    # =========================================================================
    # Solo Tackles
    # =========================================================================
    solos = pbp[pbp['solo_tackle'] == 1].copy()
    print(f"  Processing {len(solos):,} solo tackles...")

    for _, play in solos.iterrows():
        season = play['season']
        for i in [1, 2]:
            col = f'solo_tackle_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'solo_tackle_{i}_player_name'), 'season': season}
                player_stats[key]['solo_tackles'] = player_stats[key].get('solo_tackles', 0) + 1

    # =========================================================================
    # Assist Tackles
    # =========================================================================
    assists = pbp[pbp['assist_tackle'] == 1].copy()
    print(f"  Processing {len(assists):,} assist tackles...")

    for _, play in assists.iterrows():
        season = play['season']
        for i in [1, 2, 3, 4]:
            col = f'assist_tackle_{i}_player_id'
            if pd.notna(play.get(col)):
                key = (play[col], season)
                if key not in player_stats:
                    player_stats[key] = {'player_name': play.get(f'assist_tackle_{i}_player_name'), 'season': season}
                player_stats[key]['assist_tackles'] = player_stats[key].get('assist_tackles', 0) + 1

    # =========================================================================
    # Compute DV Score
    # =========================================================================
    print("\nComputing Defensive Value scores...")

    rows = []
    for (player_id, season), stats in player_stats.items():
        dv = 0
        dv += stats.get('sacks', 0) * DV_WEIGHTS['sack']
        dv += stats.get('half_sacks', 0) * DV_WEIGHTS['half_sack']
        dv += stats.get('interceptions', 0) * DV_WEIGHTS['interception']
        dv += stats.get('forced_fumbles', 0) * DV_WEIGHTS['fumble_forced']
        dv += stats.get('fumble_recoveries', 0) * DV_WEIGHTS['fumble_recovery']
        dv += stats.get('pass_defenses', 0) * DV_WEIGHTS['pass_defense']
        dv += stats.get('qb_hits', 0) * DV_WEIGHTS['qb_hit']
        dv += stats.get('tackles_for_loss', 0) * DV_WEIGHTS['tackle_for_loss']
        dv += stats.get('solo_tackles', 0) * DV_WEIGHTS['solo_tackle']
        dv += stats.get('assist_tackles', 0) * DV_WEIGHTS['assist_tackle']

        rows.append({
            'player_id': player_id,
            'player_name': stats.get('player_name'),
            'season': season,
            'sacks': stats.get('sacks', 0),
            'half_sacks': stats.get('half_sacks', 0),
            'interceptions': stats.get('interceptions', 0),
            'forced_fumbles': stats.get('forced_fumbles', 0),
            'fumble_recoveries': stats.get('fumble_recoveries', 0),
            'pass_defenses': stats.get('pass_defenses', 0),
            'qb_hits': stats.get('qb_hits', 0),
            'tackles_for_loss': stats.get('tackles_for_loss', 0),
            'solo_tackles': stats.get('solo_tackles', 0),
            'assist_tackles': stats.get('assist_tackles', 0),
            'defensive_value': round(dv, 2),
        })

    df = pd.DataFrame(rows)

    # Filter to players with meaningful DV (played defense)
    df = df[df['defensive_value'] > 0]

    print(f"\n  Total defensive player-seasons: {len(df):,}")

    # =========================================================================
    # Add Position from Contracts (via gsis_id)
    # =========================================================================
    print("\nAdding positions from contracts...")
    contracts = pd.read_parquet(CACHED_DIR / "contracts.parquet")

    # Get position by gsis_id
    player_positions = contracts[['gsis_id', 'position', 'player', 'team']].dropna(subset=['gsis_id']).drop_duplicates('gsis_id')

    # Merge by player_id (which is gsis_id)
    df = df.merge(
        player_positions.rename(columns={
            'gsis_id': 'player_id',
            'player': 'full_name',
            'position': 'position',
            'team': 'contract_team',
        }),
        on='player_id',
        how='left'
    )

    # Map positions to groups
    POSITION_MAP = {
        'CB': 'CB',
        'DB': 'CB',
        'S': 'S', 'FS': 'S', 'SS': 'S',
        'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB', 'OLB': 'LB',
        'DE': 'EDGE', 'ED': 'EDGE', 'EDGE': 'EDGE',
        'DT': 'DL', 'NT': 'DL', 'DL': 'DL', 'IDL': 'DL',
    }

    df['position_group'] = df['position'].map(POSITION_MAP)

    # =========================================================================
    # Summary Stats
    # =========================================================================
    print("\n" + "=" * 60)
    print("DEFENSIVE VALUE SUMMARY")
    print("=" * 60)

    print("\nTop 20 DV Seasons (all time):")
    top = df.nlargest(20, 'defensive_value')[['player_name', 'season', 'position', 'defensive_value', 'sacks', 'interceptions']]
    print(top.to_string(index=False))

    print("\nAverage DV by Position Group:")
    pos_avg = df.groupby('position_group')['defensive_value'].agg(['mean', 'median', 'max', 'count'])
    print(pos_avg.round(2).to_string())

    print("\nDV Distribution:")
    print(f"  Min: {df['defensive_value'].min():.1f}")
    print(f"  25%: {df['defensive_value'].quantile(0.25):.1f}")
    print(f"  50%: {df['defensive_value'].quantile(0.50):.1f}")
    print(f"  75%: {df['defensive_value'].quantile(0.75):.1f}")
    print(f"  90%: {df['defensive_value'].quantile(0.90):.1f}")
    print(f"  Max: {df['defensive_value'].max():.1f}")

    # =========================================================================
    # Save Results
    # =========================================================================
    output_path = CACHED_DIR / "defensive_value.parquet"
    df.to_parquet(output_path, index=False)
    print(f"\nSaved to: {output_path}")

    # Also save as CSV for easy inspection
    csv_path = RESEARCH_DIR / "data" / "defensive_value.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved to: {csv_path}")

    return df


if __name__ == "__main__":
    df = compute_defensive_value()
