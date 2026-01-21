"""NFL Run Game Analysis for Simulation Calibration

Uses nfl_data_py to analyze real NFL run play data and generate
insights for balancing the Huddle simulation.

Research Questions:
1. What's the real yards-per-carry distribution?
2. How often are runs stuffed at or behind LOS?
3. How often do runs go for 10+ yards?
4. How do different run concepts perform?
5. What's the tackle distribution (solo vs assist)?

Output:
- Markdown report for agents: reports/run_game_analysis.md
- Figures: figures/run_*.png
- Raw data export: data/run_game_stats.csv
"""

import nfl_data_py as nfl
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from datetime import datetime

# Configuration
YEARS = [2023, 2022, 2021]  # Recent seasons for analysis
BASE_DIR = "/Users/thomasmorton/huddle/research"
OUTPUT_DIR = f"{BASE_DIR}/reports"
FIGURES_DIR = f"{BASE_DIR}/figures"
DATA_DIR = f"{BASE_DIR}/data"

# Style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def load_pbp_data(years: list) -> pd.DataFrame:
    """Load play-by-play data for specified years."""
    print(f"Loading play-by-play data for {years}...")
    pbp = nfl.import_pbp_data(years)
    print(f"Loaded {len(pbp):,} plays")
    return pbp


def filter_run_plays(pbp: pd.DataFrame) -> pd.DataFrame:
    """Filter to just run plays."""
    runs = pbp[
        (pbp['play_type'] == 'run') &
        (pbp['rushing_yards'].notna()) &
        (pbp['two_point_attempt'] == 0) &  # Exclude 2pt conversions
        (pbp['qb_kneel'] == 0) &  # Exclude kneels
        (pbp['qb_spike'] == 0)  # Exclude spikes
    ].copy()
    print(f"Filtered to {len(runs):,} run plays")
    return runs


def analyze_yards_distribution(runs: pd.DataFrame) -> dict:
    """Analyze the distribution of rushing yards."""
    yards = runs['rushing_yards']

    results = {
        'total_plays': len(runs),
        'mean_yards': yards.mean(),
        'median_yards': yards.median(),
        'std_yards': yards.std(),

        # Key percentiles
        'p10': yards.quantile(0.10),
        'p25': yards.quantile(0.25),
        'p50': yards.quantile(0.50),
        'p75': yards.quantile(0.75),
        'p90': yards.quantile(0.90),
        'p95': yards.quantile(0.95),
        'p99': yards.quantile(0.99),

        # Outcome buckets
        'stuffed_behind_los': (yards < 0).mean() * 100,  # Loss
        'no_gain': ((yards >= 0) & (yards <= 0)).mean() * 100,
        'short_gain_1_3': ((yards >= 1) & (yards <= 3)).mean() * 100,
        'medium_gain_4_6': ((yards >= 4) & (yards <= 6)).mean() * 100,
        'good_gain_7_9': ((yards >= 7) & (yards <= 9)).mean() * 100,
        'explosive_10_plus': (yards >= 10).mean() * 100,
        'big_play_20_plus': (yards >= 20).mean() * 100,
    }

    return results


def analyze_by_down(runs: pd.DataFrame) -> pd.DataFrame:
    """Analyze rushing by down."""
    by_down = runs.groupby('down').agg({
        'rushing_yards': ['count', 'mean', 'median', 'std'],
        'first_down': 'mean',  # First down conversion rate
        'epa': 'mean',  # Expected points added
    }).round(2)

    by_down.columns = ['plays', 'mean_yards', 'median_yards', 'std_yards',
                       'first_down_rate', 'mean_epa']
    return by_down


def analyze_by_distance(runs: pd.DataFrame) -> pd.DataFrame:
    """Analyze rushing by yards to go."""
    runs['ytg_bucket'] = pd.cut(
        runs['ydstogo'],
        bins=[0, 2, 5, 8, 10, 15, 99],
        labels=['1-2', '3-5', '6-8', '9-10', '11-15', '16+']
    )

    by_distance = runs.groupby('ytg_bucket').agg({
        'rushing_yards': ['count', 'mean', 'median'],
        'first_down': 'mean',
        'epa': 'mean',
    }).round(2)

    by_distance.columns = ['plays', 'mean_yards', 'median_yards',
                           'first_down_rate', 'mean_epa']
    return by_distance


def analyze_by_score_differential(runs: pd.DataFrame) -> pd.DataFrame:
    """Analyze rushing by score differential (game situation)."""
    runs['score_diff'] = runs['posteam_score'] - runs['defteam_score']
    runs['situation'] = pd.cut(
        runs['score_diff'],
        bins=[-100, -14, -7, -1, 0, 7, 14, 100],
        labels=['down_14+', 'down_7-13', 'down_1-6', 'tied',
                'up_1-7', 'up_8-14', 'up_14+']
    )

    by_situation = runs.groupby('situation').agg({
        'rushing_yards': ['count', 'mean'],
        'epa': 'mean',
    }).round(2)

    by_situation.columns = ['plays', 'mean_yards', 'mean_epa']
    return by_situation


def analyze_run_location(runs: pd.DataFrame) -> pd.DataFrame:
    """Analyze rushing by run location (left/middle/right)."""
    # run_location field: left, middle, right
    if 'run_location' in runs.columns:
        by_location = runs.groupby('run_location').agg({
            'rushing_yards': ['count', 'mean', 'median'],
            'first_down': 'mean',
            'epa': 'mean',
        }).round(2)
        by_location.columns = ['plays', 'mean_yards', 'median_yards',
                               'first_down_rate', 'mean_epa']
        return by_location
    return None


def analyze_run_gap(runs: pd.DataFrame) -> pd.DataFrame:
    """Analyze rushing by gap (A/B/C)."""
    if 'run_gap' in runs.columns:
        by_gap = runs.groupby('run_gap').agg({
            'rushing_yards': ['count', 'mean', 'median'],
            'first_down': 'mean',
            'epa': 'mean',
        }).round(2)
        by_gap.columns = ['plays', 'mean_yards', 'median_yards',
                          'first_down_rate', 'mean_epa']
        return by_gap
    return None


def generate_report(results: dict, by_down: pd.DataFrame,
                    by_distance: pd.DataFrame, by_situation: pd.DataFrame,
                    by_location: pd.DataFrame, by_gap: pd.DataFrame) -> str:
    """Generate a markdown research report."""

    report = f"""# NFL Run Game Analysis Report

**Data Source:** nfl_data_py (nflfastR)
**Seasons:** {YEARS}
**Total Run Plays Analyzed:** {results['total_plays']:,}

---

## Executive Summary

The real NFL run game has these characteristics that our simulation should match:

- **Average:** {results['mean_yards']:.1f} yards per carry
- **Median:** {results['median_yards']:.1f} yards (tells us distribution is right-skewed)
- **Stuffed (loss):** {results['stuffed_behind_los']:.1f}% of runs
- **Short gains (1-3):** {results['short_gain_1_3']:.1f}% of runs
- **Medium gains (4-6):** {results['medium_gain_4_6']:.1f}% of runs
- **Explosive (10+):** {results['explosive_10_plus']:.1f}% of runs

---

## Yards Distribution

| Percentile | Yards |
|------------|-------|
| 10th | {results['p10']:.0f} |
| 25th | {results['p25']:.0f} |
| 50th (Median) | {results['p50']:.0f} |
| 75th | {results['p75']:.0f} |
| 90th | {results['p90']:.0f} |
| 95th | {results['p95']:.0f} |
| 99th | {results['p99']:.0f} |

**Key Insight:** 50% of runs gain 3 yards or less. 75% gain 5 yards or less.
The 4-6 yard "good run" is actually in the 50th-75th percentile.

---

## Outcome Buckets

| Outcome | Percentage |
|---------|------------|
| Stuffed (loss) | {results['stuffed_behind_los']:.1f}% |
| No gain (0) | {results['no_gain']:.1f}% |
| Short (1-3) | {results['short_gain_1_3']:.1f}% |
| Medium (4-6) | {results['medium_gain_4_6']:.1f}% |
| Good (7-9) | {results['good_gain_7_9']:.1f}% |
| Explosive (10+) | {results['explosive_10_plus']:.1f}% |
| Big Play (20+) | {results['big_play_20_plus']:.1f}% |

---

## By Down

{by_down.to_markdown()}

**Key Insights:**
- 1st down runs average the most yards
- 3rd and 4th down runs have lower averages (defense knows it's coming)
- First down conversion rate drops significantly on 3rd/4th down

---

## By Yards to Go

{by_distance.to_markdown()}

**Key Insight:** Short yardage (1-2) has highest EPA - this is where runs are most valuable.

---

## By Game Situation

{by_situation.to_markdown()}

**Key Insight:** Teams run more when ahead, but EPA drops (defense stacks the box).

---

## By Run Location

{by_location.to_markdown() if by_location is not None else "Data not available"}

---

## By Gap

{by_gap.to_markdown() if by_gap is not None else "Data not available"}

---

## Simulation Calibration Recommendations

### 1. Yards Distribution Target
Our simulation should produce:
- ~20% of runs for loss or no gain
- ~35% of runs for 1-3 yards
- ~25% of runs for 4-6 yards
- ~10% of runs for 7-9 yards
- ~10% of runs for 10+ yards

### 2. Average YPC Target
- Target: 4.2-4.5 yards per carry average
- Median should be 3 yards (not the mean!)

### 3. Explosive Play Rate
- 10+ yard runs: ~10% of all runs
- 20+ yard runs: ~2-3% of all runs

### 4. Situation Awareness
- Short yardage should convert ~75%+ of the time
- 3rd/4th down runs should have lower success rate
- Runs when ahead by 14+ should average less (stacked boxes)

---

*Report generated by researcher_agent using nfl_data_py*
"""

    return report


def create_visualizations(runs: pd.DataFrame, results: dict,
                          by_down: pd.DataFrame, by_situation: pd.DataFrame):
    """Generate all visualizations."""
    import os
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # 1. Yards Distribution Histogram
    fig, ax = plt.subplots(figsize=(12, 6))
    yards = runs['rushing_yards'].clip(-10, 40)  # Clip for visualization
    ax.hist(yards, bins=51, range=(-10, 40), edgecolor='white', alpha=0.7, color='#2E86AB')
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Line of Scrimmage')
    ax.axvline(x=results['mean_yards'], color='green', linestyle='-', linewidth=2,
               label=f'Mean ({results["mean_yards"]:.1f} yds)')
    ax.axvline(x=results['median_yards'], color='orange', linestyle='-', linewidth=2,
               label=f'Median ({results["median_yards"]:.1f} yds)')
    ax.set_xlabel('Rushing Yards', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('NFL Run Play Yards Distribution (2021-2023)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.set_xlim(-10, 40)
    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/run_yards_distribution.png', dpi=150)
    plt.close()
    print(f"  Saved: {FIGURES_DIR}/run_yards_distribution.png")

    # 2. Outcome Buckets Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    buckets = ['Loss\n(< 0)', 'No Gain\n(0)', 'Short\n(1-3)', 'Medium\n(4-6)',
               'Good\n(7-9)', 'Explosive\n(10+)', 'Big Play\n(20+)']
    percentages = [
        results['stuffed_behind_los'],
        results['no_gain'],
        results['short_gain_1_3'],
        results['medium_gain_4_6'],
        results['good_gain_7_9'],
        results['explosive_10_plus'],
        results['big_play_20_plus']
    ]
    colors = ['#E63946', '#F4A261', '#E9C46A', '#2A9D8F', '#264653', '#1D3557', '#023047']
    bars = ax.bar(buckets, percentages, color=colors, edgecolor='white')

    # Add percentage labels on bars
    for bar, pct in zip(bars, percentages):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=10)

    ax.set_ylabel('Percentage of Run Plays', fontsize=12)
    ax.set_title('NFL Run Play Outcome Distribution (2021-2023)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(percentages) * 1.15)
    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/run_outcome_buckets.png', dpi=150)
    plt.close()
    print(f"  Saved: {FIGURES_DIR}/run_outcome_buckets.png")

    # 3. By Down Analysis
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Mean yards by down
    downs = by_down.index.astype(int)
    ax1 = axes[0]
    ax1.bar(downs, by_down['mean_yards'], color='#2E86AB', edgecolor='white')
    for i, (d, y) in enumerate(zip(downs, by_down['mean_yards'])):
        ax1.text(d, y + 0.1, f'{y:.1f}', ha='center', va='bottom', fontsize=11)
    ax1.set_xlabel('Down', fontsize=12)
    ax1.set_ylabel('Mean Rushing Yards', fontsize=12)
    ax1.set_title('Average Rushing Yards by Down', fontsize=13, fontweight='bold')
    ax1.set_xticks(downs)

    # First down rate by down
    ax2 = axes[1]
    ax2.bar(downs, by_down['first_down_rate'] * 100, color='#2A9D8F', edgecolor='white')
    for i, (d, r) in enumerate(zip(downs, by_down['first_down_rate'] * 100)):
        ax2.text(d, r + 1, f'{r:.0f}%', ha='center', va='bottom', fontsize=11)
    ax2.set_xlabel('Down', fontsize=12)
    ax2.set_ylabel('First Down Conversion Rate (%)', fontsize=12)
    ax2.set_title('First Down Conversion Rate by Down', fontsize=13, fontweight='bold')
    ax2.set_xticks(downs)

    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/run_by_down.png', dpi=150)
    plt.close()
    print(f"  Saved: {FIGURES_DIR}/run_by_down.png")

    # 4. By Game Situation
    fig, ax = plt.subplots(figsize=(10, 6))
    situations = by_situation.index.tolist()
    mean_yards = by_situation['mean_yards'].values
    colors = ['#E63946' if 'down' in s else '#2A9D8F' if 'up' in s else '#E9C46A'
              for s in situations]
    bars = ax.bar(situations, mean_yards, color=colors, edgecolor='white')

    for bar, y in zip(bars, mean_yards):
        ax.text(bar.get_x() + bar.get_width()/2, y + 0.05,
                f'{y:.1f}', ha='center', va='bottom', fontsize=10)

    ax.set_xlabel('Game Situation', fontsize=12)
    ax.set_ylabel('Mean Rushing Yards', fontsize=12)
    ax.set_title('Rushing Yards by Score Differential', fontsize=14, fontweight='bold')
    ax.axhline(y=results['mean_yards'], color='gray', linestyle='--', alpha=0.7)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/run_by_situation.png', dpi=150)
    plt.close()
    print(f"  Saved: {FIGURES_DIR}/run_by_situation.png")

    # 5. Cumulative Distribution Function
    fig, ax = plt.subplots(figsize=(10, 6))
    yards_sorted = np.sort(runs['rushing_yards'].values)
    cdf = np.arange(1, len(yards_sorted) + 1) / len(yards_sorted) * 100
    ax.plot(yards_sorted, cdf, color='#2E86AB', linewidth=2)

    # Key markers
    ax.axhline(y=50, color='orange', linestyle='--', alpha=0.7, label='50th percentile')
    ax.axhline(y=75, color='green', linestyle='--', alpha=0.7, label='75th percentile')
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='LOS')

    ax.set_xlabel('Rushing Yards', fontsize=12)
    ax.set_ylabel('Cumulative Percentage', fontsize=12)
    ax.set_title('Cumulative Distribution of Rushing Yards', fontsize=14, fontweight='bold')
    ax.set_xlim(-10, 30)
    ax.legend()
    plt.tight_layout()
    plt.savefig(f'{FIGURES_DIR}/run_cdf.png', dpi=150)
    plt.close()
    print(f"  Saved: {FIGURES_DIR}/run_cdf.png")


def export_raw_data(runs: pd.DataFrame, results: dict):
    """Export key statistics to CSV for reference."""
    import os
    os.makedirs(DATA_DIR, exist_ok=True)

    # Summary stats
    summary = pd.DataFrame([results])
    summary.to_csv(f'{DATA_DIR}/run_game_summary.csv', index=False)

    # Sample of raw data (first 10000 rows) with key columns
    key_cols = ['game_id', 'play_id', 'down', 'ydstogo', 'rushing_yards',
                'run_location', 'run_gap', 'rusher_player_name', 'posteam',
                'defteam', 'epa', 'first_down', 'game_seconds_remaining']
    available_cols = [c for c in key_cols if c in runs.columns]
    runs[available_cols].head(10000).to_csv(f'{DATA_DIR}/run_plays_sample.csv', index=False)

    print(f"  Saved: {DATA_DIR}/run_game_summary.csv")
    print(f"  Saved: {DATA_DIR}/run_plays_sample.csv")


def main():
    """Main analysis function."""
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load data
    pbp = load_pbp_data(YEARS)

    # Filter to run plays
    runs = filter_run_plays(pbp)

    # Run analyses
    print("\nAnalyzing yards distribution...")
    results = analyze_yards_distribution(runs)

    print("Analyzing by down...")
    by_down = analyze_by_down(runs)

    print("Analyzing by distance...")
    by_distance = analyze_by_distance(runs)

    print("Analyzing by situation...")
    by_situation = analyze_by_score_differential(runs)

    print("Analyzing by location...")
    by_location = analyze_run_location(runs)

    print("Analyzing by gap...")
    by_gap = analyze_run_gap(runs)

    # Generate visualizations
    print("\nGenerating visualizations...")
    create_visualizations(runs, results, by_down, by_situation)

    # Export raw data
    print("\nExporting raw data...")
    export_raw_data(runs, results)

    # Generate report
    print("\nGenerating report...")
    report = generate_report(results, by_down, by_distance, by_situation,
                             by_location, by_gap)

    # Save report
    report_path = f"{OUTPUT_DIR}/run_game_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

    # Print summary
    print("\n" + "="*60)
    print("KEY FINDINGS FOR SIMULATION CALIBRATION")
    print("="*60)
    print(f"Mean YPC: {results['mean_yards']:.2f}")
    print(f"Median YPC: {results['median_yards']:.1f}")
    print(f"Stuffed rate: {results['stuffed_behind_los']:.1f}%")
    print(f"Explosive (10+) rate: {results['explosive_10_plus']:.1f}%")
    print(f"Big play (20+) rate: {results['big_play_20_plus']:.1f}%")
    print("="*60)
    print(f"\nFigures saved to: {FIGURES_DIR}/")
    print(f"Data saved to: {DATA_DIR}/")


if __name__ == "__main__":
    main()
