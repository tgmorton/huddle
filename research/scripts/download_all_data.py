"""Download and Cache All NFL Data

Downloads all available NFL datasets from nfl_data_py and saves them
as parquet files for fast loading in analysis scripts.

Run once to populate research/data/cached/

Usage:
    python research/scripts/download_all_data.py
"""

import os
import nfl_data_py as nfl
import pandas as pd
from datetime import datetime

# Configuration
CACHE_DIR = "/Users/thomasmorton/huddle/research/data/cached"
YEARS = list(range(2019, 2025))  # 2019-2024 (6 years of data)
COMBINE_YEARS = list(range(2015, 2025))  # More years for combine
DRAFT_YEARS = list(range(2010, 2025))  # More history for draft outcomes

def ensure_dir(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def download_with_progress(name, download_func, *args, **kwargs):
    """Download data with progress output."""
    print(f"\n{'='*60}")
    print(f"Downloading: {name}")
    print(f"{'='*60}")
    try:
        data = download_func(*args, **kwargs)
        print(f"  Rows: {len(data):,}")
        print(f"  Columns: {len(data.columns)}")
        return data
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def main():
    ensure_dir(CACHE_DIR)

    print("="*60)
    print("NFL DATA DOWNLOAD SCRIPT")
    print(f"Cache directory: {CACHE_DIR}")
    print(f"Started: {datetime.now()}")
    print("="*60)

    # 1. Play-by-play data (largest dataset)
    print("\n[1/12] Play-by-Play Data")
    pbp = download_with_progress("Play-by-Play", nfl.import_pbp_data, YEARS)
    if pbp is not None:
        pbp.to_parquet(f"{CACHE_DIR}/play_by_play.parquet")
        print(f"  Saved: play_by_play.parquet")

    # 2. Weekly player stats
    print("\n[2/12] Weekly Player Stats")
    weekly = download_with_progress("Weekly Stats", nfl.import_weekly_data, YEARS)
    if weekly is not None:
        weekly.to_parquet(f"{CACHE_DIR}/weekly_stats.parquet")
        print(f"  Saved: weekly_stats.parquet")

    # 3. Seasonal player stats
    print("\n[3/12] Seasonal Player Stats")
    seasonal = download_with_progress("Seasonal Stats", nfl.import_seasonal_data, YEARS)
    if seasonal is not None:
        seasonal.to_parquet(f"{CACHE_DIR}/seasonal_stats.parquet")
        print(f"  Saved: seasonal_stats.parquet")

    # 4. NGS Passing
    print("\n[4/12] Next Gen Stats - Passing")
    ngs_pass = download_with_progress("NGS Passing", nfl.import_ngs_data, 'passing', YEARS)
    if ngs_pass is not None:
        ngs_pass.to_parquet(f"{CACHE_DIR}/ngs_passing.parquet")
        print(f"  Saved: ngs_passing.parquet")

    # 5. NGS Rushing
    print("\n[5/12] Next Gen Stats - Rushing")
    ngs_rush = download_with_progress("NGS Rushing", nfl.import_ngs_data, 'rushing', YEARS)
    if ngs_rush is not None:
        ngs_rush.to_parquet(f"{CACHE_DIR}/ngs_rushing.parquet")
        print(f"  Saved: ngs_rushing.parquet")

    # 6. NGS Receiving
    print("\n[6/12] Next Gen Stats - Receiving")
    ngs_rec = download_with_progress("NGS Receiving", nfl.import_ngs_data, 'receiving', YEARS)
    if ngs_rec is not None:
        ngs_rec.to_parquet(f"{CACHE_DIR}/ngs_receiving.parquet")
        print(f"  Saved: ngs_receiving.parquet")

    # 7. Combine data
    print("\n[7/12] Combine Data")
    combine = download_with_progress("Combine", nfl.import_combine_data, COMBINE_YEARS)
    if combine is not None:
        combine.to_parquet(f"{CACHE_DIR}/combine.parquet")
        print(f"  Saved: combine.parquet")

    # 8. Draft picks
    print("\n[8/12] Draft Picks")
    draft = download_with_progress("Draft Picks", nfl.import_draft_picks, DRAFT_YEARS)
    if draft is not None:
        draft.to_parquet(f"{CACHE_DIR}/draft_picks.parquet")
        print(f"  Saved: draft_picks.parquet")

    # 9. Contracts
    print("\n[9/12] Contracts")
    contracts = download_with_progress("Contracts", nfl.import_contracts)
    if contracts is not None:
        contracts.to_parquet(f"{CACHE_DIR}/contracts.parquet")
        print(f"  Saved: contracts.parquet")

    # 10. Injuries
    print("\n[10/12] Injuries")
    injuries = download_with_progress("Injuries", nfl.import_injuries, YEARS)
    if injuries is not None:
        injuries.to_parquet(f"{CACHE_DIR}/injuries.parquet")
        print(f"  Saved: injuries.parquet")

    # 11. Snap counts
    print("\n[11/12] Snap Counts")
    snaps = download_with_progress("Snap Counts", nfl.import_snap_counts, YEARS)
    if snaps is not None:
        snaps.to_parquet(f"{CACHE_DIR}/snap_counts.parquet")
        print(f"  Saved: snap_counts.parquet")

    # 12. Depth charts
    print("\n[12/12] Depth Charts")
    depth = download_with_progress("Depth Charts", nfl.import_depth_charts, YEARS)
    if depth is not None:
        depth.to_parquet(f"{CACHE_DIR}/depth_charts.parquet")
        print(f"  Saved: depth_charts.parquet")

    # Summary
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)

    # List all cached files
    files = os.listdir(CACHE_DIR)
    total_size = 0
    for f in sorted(files):
        path = os.path.join(CACHE_DIR, f)
        size = os.path.getsize(path) / (1024 * 1024)  # MB
        total_size += size
        print(f"  {f}: {size:.1f} MB")

    print(f"\nTotal cache size: {total_size:.1f} MB")
    print(f"Finished: {datetime.now()}")

if __name__ == "__main__":
    main()
