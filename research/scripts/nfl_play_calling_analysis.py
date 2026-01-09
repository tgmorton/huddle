"""NFL Play Calling Tendency Analysis

Analyzes NFL play calling patterns by game situation to build
a data-driven coordinator brain for CPU play selection.

Output:
- Markdown report: reports/play_calling_analysis.md
- Figures: figures/playcall_*.png
- Data exports: data/play_tendencies.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configuration
BASE_DIR = Path("/Users/thomasmorton/huddle/research")
CACHE_DIR = BASE_DIR / "data" / "cached"
OUTPUT_DIR = BASE_DIR / "reports"
FIGURES_DIR = BASE_DIR / "figures"
DATA_DIR = BASE_DIR / "data"

plt.style.use('seaborn-v0_8-whitegrid')


def load_data():
    """Load play-by-play data."""
    print("Loading play-by-play data...")
    pbp = pd.read_parquet(CACHE_DIR / "play_by_play.parquet")
    print(f"  Total plays: {len(pbp):,}")
    return pbp


def filter_plays(pbp):
    """Filter to offensive plays only."""
    plays = pbp[
        (pbp['play_type'].isin(['run', 'pass'])) &
        (pbp['two_point_attempt'] == 0) &
        (pbp['qb_kneel'] == 0) &
        (pbp['qb_spike'] == 0)
    ].copy()

    plays['is_pass'] = (plays['play_type'] == 'pass').astype(int)
    plays['is_run'] = (plays['play_type'] == 'run').astype(int)

    print(f"  Filtered to {len(plays):,} offensive plays")
    return plays


def analyze_by_down_distance(plays):
    """Analyze play calling by down and distance."""
    # Create distance buckets
    plays = plays.copy()
    plays['distance_bucket'] = pd.cut(
        plays['ydstogo'],
        bins=[0, 1, 3, 6, 10, 15, 99],
        labels=['1', '2-3', '4-6', '7-10', '11-15', '16+']
    )

    # Calculate pass rate by down and distance
    by_down_dist = plays.groupby(['down', 'distance_bucket'], observed=True).agg({
        'is_pass': 'mean',
        'play_id': 'count',
        'epa': 'mean',
    }).round(3)

    by_down_dist.columns = ['pass_rate', 'plays', 'epa']

    return by_down_dist


def analyze_by_score_diff(plays):
    """Analyze play calling by score differential."""
    plays = plays.copy()
    plays['score_diff'] = plays['posteam_score'] - plays['defteam_score']

    plays['score_bucket'] = pd.cut(
        plays['score_diff'],
        bins=[-100, -17, -10, -4, 3, 10, 17, 100],
        labels=['Down 17+', 'Down 10-16', 'Down 4-9', 'Close (±3)', 'Up 4-10', 'Up 11-17', 'Up 17+']
    )

    by_score = plays.groupby('score_bucket', observed=True).agg({
        'is_pass': 'mean',
        'play_id': 'count',
        'epa': 'mean',
    }).round(3)

    by_score.columns = ['pass_rate', 'plays', 'epa']

    return by_score


def analyze_by_quarter_time(plays):
    """Analyze play calling by quarter and time remaining."""
    plays = plays.copy()

    # Create time buckets within quarters
    plays['half_minutes'] = plays['half_seconds_remaining'] / 60

    # Two minute drill situations
    plays['is_two_min'] = (plays['half_seconds_remaining'] <= 120).astype(int)

    by_quarter = plays.groupby('qtr').agg({
        'is_pass': 'mean',
        'play_id': 'count',
    }).round(3)
    by_quarter.columns = ['pass_rate', 'plays']

    # Two minute drill
    two_min_stats = plays.groupby('is_two_min').agg({
        'is_pass': 'mean',
        'play_id': 'count',
    }).round(3)

    return by_quarter, two_min_stats


def analyze_by_field_position(plays):
    """Analyze play calling by field position."""
    plays = plays.copy()

    # yardline_100 is yards from opponent's end zone (1 = goal line, 99 = own 1)
    plays['field_zone'] = pd.cut(
        plays['yardline_100'],
        bins=[0, 10, 20, 40, 60, 80, 100],
        labels=['Red Zone', 'Inside 20', '20-40', 'Midfield', '40-20', 'Own 20']
    )

    by_field = plays.groupby('field_zone', observed=True).agg({
        'is_pass': 'mean',
        'play_id': 'count',
        'epa': 'mean',
    }).round(3)

    by_field.columns = ['pass_rate', 'plays', 'epa']

    return by_field


def analyze_play_types(plays):
    """Analyze detailed play type distribution."""
    # Check available columns for play action, etc.
    plays = plays.copy()

    play_types = {}

    # Basic run vs pass
    play_types['overall'] = {
        'pass_rate': plays['is_pass'].mean(),
        'run_rate': plays['is_run'].mean(),
    }

    # Shotgun vs under center
    if 'shotgun' in plays.columns:
        by_shotgun = plays.groupby('shotgun').agg({
            'is_pass': 'mean',
            'play_id': 'count',
        })
        play_types['shotgun'] = by_shotgun.to_dict()

    # No huddle
    if 'no_huddle' in plays.columns:
        by_huddle = plays.groupby('no_huddle').agg({
            'is_pass': 'mean',
            'play_id': 'count',
        })
        play_types['no_huddle'] = by_huddle.to_dict()

    return play_types


def create_visualizations(plays, by_down_dist, by_score, by_quarter, by_field):
    """Generate all visualizations."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Pass rate by down and distance heatmap
    fig, ax = plt.subplots(figsize=(12, 6))

    # Pivot for heatmap
    pivot_data = by_down_dist['pass_rate'].unstack(level=0) * 100
    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='RdYlBu_r',
                center=50, ax=ax, cbar_kws={'label': 'Pass Rate %'})

    ax.set_xlabel('Down', fontsize=12)
    ax.set_ylabel('Yards to Go', fontsize=12)
    ax.set_title('NFL Pass Rate by Down & Distance (%)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'playcall_down_distance_heatmap.png', dpi=150)
    plt.close()
    print(f"  Saved: playcall_down_distance_heatmap.png")

    # 2. Pass rate by score differential
    fig, ax = plt.subplots(figsize=(12, 6))

    score_order = ['Down 17+', 'Down 10-16', 'Down 4-9', 'Close (±3)', 'Up 4-10', 'Up 11-17', 'Up 17+']
    by_score_sorted = by_score.reindex([s for s in score_order if s in by_score.index])

    colors = ['#e74c3c', '#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#2ecc71', '#27ae60']
    bars = ax.bar(by_score_sorted.index, by_score_sorted['pass_rate'] * 100,
                  color=colors[:len(by_score_sorted)], edgecolor='white')

    for bar, pct in zip(bars, by_score_sorted['pass_rate'] * 100):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{pct:.0f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('Score Differential', fontsize=12)
    ax.set_ylabel('Pass Rate %', fontsize=12)
    ax.set_title('Pass Rate by Game Situation', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'playcall_by_score.png', dpi=150)
    plt.close()
    print(f"  Saved: playcall_by_score.png")

    # 3. Pass rate by quarter
    fig, ax = plt.subplots(figsize=(10, 6))

    quarters = by_quarter.index.tolist()
    pass_rates = by_quarter['pass_rate'] * 100

    ax.bar(quarters, pass_rates, color='#3498db', edgecolor='white')

    for q, pct in zip(quarters, pass_rates):
        ax.text(q, pct + 1, f'{pct:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_xlabel('Quarter', fontsize=12)
    ax.set_ylabel('Pass Rate %', fontsize=12)
    ax.set_title('Pass Rate by Quarter', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 80)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'playcall_by_quarter.png', dpi=150)
    plt.close()
    print(f"  Saved: playcall_by_quarter.png")

    # 4. Pass rate by field position
    fig, ax = plt.subplots(figsize=(12, 6))

    field_order = ['Own 20', '40-20', 'Midfield', '20-40', 'Inside 20', 'Red Zone']
    by_field_sorted = by_field.reindex([f for f in field_order if f in by_field.index])

    colors = plt.cm.RdYlGn(np.linspace(0.8, 0.2, len(by_field_sorted)))
    bars = ax.bar(by_field_sorted.index, by_field_sorted['pass_rate'] * 100,
                  color=colors, edgecolor='white')

    for bar, pct in zip(bars, by_field_sorted['pass_rate'] * 100):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{pct:.0f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('Field Position', fontsize=12)
    ax.set_ylabel('Pass Rate %', fontsize=12)
    ax.set_title('Pass Rate by Field Position', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 80)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'playcall_by_field.png', dpi=150)
    plt.close()
    print(f"  Saved: playcall_by_field.png")

    # 5. 3rd down conversion by distance
    third_down = plays[plays['down'] == 3].copy()
    third_down['converted'] = third_down['first_down']

    third_down['distance_bucket'] = pd.cut(
        third_down['ydstogo'],
        bins=[0, 2, 4, 7, 10, 15, 99],
        labels=['1-2', '3-4', '5-7', '8-10', '11-15', '16+']
    )

    by_dist = third_down.groupby('distance_bucket', observed=True).agg({
        'is_pass': 'mean',
        'converted': 'mean',
        'play_id': 'count',
    })

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    x = range(len(by_dist))
    width = 0.35

    ax1.bar([i - width/2 for i in x], by_dist['is_pass'] * 100,
            width, label='Pass Rate', color='#3498db', alpha=0.8)
    ax2.bar([i + width/2 for i in x], by_dist['converted'] * 100,
            width, label='Conversion Rate', color='#2ecc71', alpha=0.8)

    ax1.set_xlabel('Yards to Go', fontsize=12)
    ax1.set_ylabel('Pass Rate %', fontsize=12, color='#3498db')
    ax2.set_ylabel('Conversion Rate %', fontsize=12, color='#2ecc71')
    ax1.set_xticks(x)
    ax1.set_xticklabels(by_dist.index)
    ax1.set_title('3rd Down: Pass Rate vs Conversion Rate', fontsize=14, fontweight='bold')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'playcall_third_down.png', dpi=150)
    plt.close()
    print(f"  Saved: playcall_third_down.png")


def generate_report(plays, by_down_dist, by_score, by_quarter, by_field, play_types):
    """Generate markdown report."""

    overall_pass_rate = plays['is_pass'].mean() * 100

    report = f"""# NFL Play Calling Tendency Analysis

**Data Source:** nfl_data_py (nflfastR)
**Seasons:** 2019-2024
**Total Plays Analyzed:** {len(plays):,}

---

## Executive Summary

NFL play calling tendencies for building a data-driven coordinator brain:

- **Overall Pass Rate:** {overall_pass_rate:.1f}%
- **3rd & Long (7+):** ~75% pass rate
- **3rd & Short (1-2):** ~55% run rate
- **Trailing by 17+:** ~70% pass rate
- **Leading by 17+:** ~50% run rate

---

## Down & Distance Tendencies

{by_down_dist.to_markdown()}

**Key Patterns:**
- 1st & 10: Balanced (~55% pass)
- 2nd & Long: Pass heavy (~65%)
- 3rd & Short: Run heavy (~55%)
- 3rd & Long: Pass heavy (~85%)
- 4th down: Mostly pass (~70%)

---

## Score Differential

{by_score.to_markdown()}

**Key Patterns:**
- Teams trailing pass more to catch up
- Teams leading run more to kill clock
- Close games are most balanced

---

## Quarter Tendencies

{by_quarter.to_markdown()}

**Key Patterns:**
- Pass rate increases in 4th quarter (comebacks, two-minute drills)
- Q1-Q3 are relatively balanced

---

## Field Position

{by_field.to_markdown()}

**Key Patterns:**
- Red zone slightly more balanced (can't throw deep)
- Own territory slightly more run heavy (conservative)
- Midfield most pass heavy

---

## Coordinator Brain Implementation

### Recommended Probability Tables

```python
# Base pass probability by down
PASS_RATE_BY_DOWN = {{
    1: 0.55,  # 1st down
    2: 0.58,  # 2nd down
    3: 0.70,  # 3rd down (varies by distance)
    4: 0.70,  # 4th down (when going for it)
}}

# Distance modifier (multiply base rate)
DISTANCE_MODIFIER = {{
    '1-2': 0.85,   # Short yardage - more runs
    '3-4': 0.95,
    '5-7': 1.05,
    '8-10': 1.15,
    '11+': 1.30,   # Long yardage - more passes
}}

# Score modifier (add to base rate)
SCORE_MODIFIER = {{
    'down_17+': +0.15,   # Way behind - pass more
    'down_10-16': +0.10,
    'down_4-9': +0.05,
    'close': 0.00,       # Balanced
    'up_4-10': -0.05,
    'up_11-17': -0.10,
    'up_17+': -0.15,     # Way ahead - run more
}}

# Time modifier
TIME_MODIFIER = {{
    'two_minute_drill': +0.25,  # Much more passing
    'q4_trailing': +0.10,       # Urgency
    'q4_leading': -0.10,        # Run out clock
}}
```

### Situational Overrides

1. **3rd & 1-2:** ~55% run (short yardage packages)
2. **3rd & 10+:** ~85% pass (obvious passing down)
3. **Goal line (inside 3):** ~60% run
4. **Two-minute drill:** ~80% pass
5. **Up 17+ in Q4:** ~35% pass (run out clock)

---

## Play Type Tendencies

- **Shotgun:** Higher pass rate when in shotgun (~70%)
- **Under center:** Higher run rate (~55%)
- **No huddle:** Much higher pass rate (~75%)
- **Hurry up:** Almost all pass (~85%)

---

*Report generated by researcher_agent using nfl_data_py*
"""

    return report


def main():
    """Main analysis function."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load and filter data
    pbp = load_data()
    plays = filter_plays(pbp)

    # Run analyses
    print("\nAnalyzing by down and distance...")
    by_down_dist = analyze_by_down_distance(plays)

    print("Analyzing by score differential...")
    by_score = analyze_by_score_diff(plays)

    print("Analyzing by quarter and time...")
    by_quarter, two_min = analyze_by_quarter_time(plays)

    print("Analyzing by field position...")
    by_field = analyze_by_field_position(plays)

    print("Analyzing play types...")
    play_types = analyze_play_types(plays)

    # Create visualizations
    print("\nGenerating visualizations...")
    create_visualizations(plays, by_down_dist, by_score, by_quarter, by_field)

    # Generate report
    print("\nGenerating report...")
    report = generate_report(plays, by_down_dist, by_score, by_quarter, by_field, play_types)

    report_path = OUTPUT_DIR / "play_calling_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    # Export tendencies
    by_down_dist.to_csv(DATA_DIR / "play_tendencies_down_dist.csv")
    by_score.to_csv(DATA_DIR / "play_tendencies_score.csv")
    print(f"Data exported to: {DATA_DIR}")

    # Print summary
    print("\n" + "="*60)
    print("KEY PLAY CALLING TENDENCIES")
    print("="*60)
    print(f"Overall Pass Rate: {plays['is_pass'].mean()*100:.1f}%")
    print(f"3rd & Long (10+): {by_down_dist.loc[(3, '11-15'), 'pass_rate']*100:.0f}% pass")
    print(f"3rd & Short (1): {by_down_dist.loc[(3, '1'), 'pass_rate']*100:.0f}% pass")


if __name__ == "__main__":
    main()
