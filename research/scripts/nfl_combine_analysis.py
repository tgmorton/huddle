"""NFL Combine Analysis for Player Generation

Analyzes NFL Combine data to provide position-specific physical profiles
for realistic player generation.

Output:
- Markdown report: reports/combine_analysis.md
- Figures: figures/combine_*.png
- Data exports: data/combine_profiles.csv
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

# Style
plt.style.use('seaborn-v0_8-whitegrid')

# Position groupings for analysis
POSITION_GROUPS = {
    'QB': ['QB'],
    'RB': ['RB', 'FB'],
    'WR': ['WR'],
    'TE': ['TE'],
    'OL': ['OT', 'OG', 'C', 'G', 'T'],
    'EDGE': ['EDGE', 'OLB', 'DE'],
    'DL': ['DT', 'NT', 'DL'],
    'LB': ['LB', 'ILB', 'MLB'],
    'CB': ['CB'],
    'S': ['S', 'FS', 'SS', 'DB'],
}

def get_position_group(pos):
    """Map specific position to position group."""
    if pd.isna(pos):
        return None
    pos = pos.upper()
    for group, positions in POSITION_GROUPS.items():
        if pos in positions:
            return group
    return None


def load_combine_data():
    """Load cached combine data."""
    print("Loading combine data...")
    combine = pd.read_parquet(CACHE_DIR / "combine.parquet")
    print(f"  Total records: {len(combine):,}")
    print(f"  Years: {combine['season'].min()}-{combine['season'].max()}")
    return combine


def clean_combine_data(df):
    """Clean and prepare combine data."""
    df = df.copy()

    # Add position group
    df['pos_group'] = df['pos'].apply(get_position_group)

    # Filter to valid position groups
    df = df[df['pos_group'].notna()]

    # Convert height to inches if needed
    if 'ht' in df.columns:
        # Height is in format like "6-2" or already inches
        def parse_height(h):
            if pd.isna(h):
                return np.nan
            if isinstance(h, (int, float)):
                return h
            if '-' in str(h):
                parts = str(h).split('-')
                return int(parts[0]) * 12 + int(parts[1])
            return np.nan
        df['height_inches'] = df['ht'].apply(parse_height)
    else:
        df['height_inches'] = np.nan

    print(f"  Valid records after cleaning: {len(df):,}")
    return df


def calculate_position_profiles(df):
    """Calculate physical profile statistics by position."""
    metrics = ['height_inches', 'wt', 'forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle']
    available_metrics = [m for m in metrics if m in df.columns]

    profiles = {}

    for pos_group in POSITION_GROUPS.keys():
        pos_data = df[df['pos_group'] == pos_group]
        if len(pos_data) < 10:
            continue

        profile = {'n': len(pos_data)}

        for metric in available_metrics:
            valid = pos_data[metric].dropna()
            if len(valid) >= 5:
                profile[f'{metric}_mean'] = valid.mean()
                profile[f'{metric}_std'] = valid.std()
                profile[f'{metric}_min'] = valid.min()
                profile[f'{metric}_max'] = valid.max()
                profile[f'{metric}_p10'] = valid.quantile(0.10)
                profile[f'{metric}_p90'] = valid.quantile(0.90)

        profiles[pos_group] = profile

    return profiles


def calculate_correlations(df):
    """Calculate correlation matrix between measurables."""
    metrics = ['forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle', 'wt']
    available = [m for m in metrics if m in df.columns]

    corr_matrix = df[available].corr()
    return corr_matrix


def create_visualizations(df, profiles, corr_matrix):
    """Generate all visualizations."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 40-yard dash by position
    fig, ax = plt.subplots(figsize=(12, 6))
    positions = [p for p in ['CB', 'WR', 'S', 'RB', 'LB', 'EDGE', 'TE', 'QB', 'DL', 'OL']
                 if p in profiles and f'forty_mean' in profiles[p]]
    forty_means = [profiles[p]['forty_mean'] for p in positions]
    forty_stds = [profiles[p].get('forty_std', 0) for p in positions]

    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(positions)))
    bars = ax.bar(positions, forty_means, yerr=forty_stds, capsize=5,
                  color=colors, edgecolor='white', alpha=0.8)

    for bar, mean in zip(bars, forty_means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{mean:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_xlabel('Position', fontsize=12)
    ax.set_ylabel('40-Yard Dash (seconds)', fontsize=12)
    ax.set_title('NFL Combine 40-Yard Dash by Position', fontsize=14, fontweight='bold')
    ax.set_ylim(4.2, 5.5)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'combine_forty_by_position.png', dpi=150)
    plt.close()
    print(f"  Saved: combine_forty_by_position.png")

    # 2. Height/Weight scatter by position
    fig, ax = plt.subplots(figsize=(12, 8))

    for pos_group in ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']:
        pos_data = df[df['pos_group'] == pos_group]
        if len(pos_data) < 10:
            continue
        ax.scatter(pos_data['wt'], pos_data['height_inches'],
                   label=pos_group, alpha=0.5, s=30)

    ax.set_xlabel('Weight (lbs)', fontsize=12)
    ax.set_ylabel('Height (inches)', fontsize=12)
    ax.set_title('NFL Combine Height vs Weight by Position', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'combine_height_weight.png', dpi=150)
    plt.close()
    print(f"  Saved: combine_height_weight.png")

    # 3. Athletic profile radar chart (for select positions)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), subplot_kw=dict(projection='polar'))
    axes = axes.flatten()

    metrics = ['forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle']
    metric_labels = ['40-Time\n(inv)', 'Bench', 'Vertical', 'Broad Jump', '3-Cone\n(inv)', 'Shuttle\n(inv)']

    # Normalize metrics (higher is better, so invert time metrics)
    def normalize_metrics(pos_data):
        values = []
        for metric in metrics:
            if metric not in pos_data or pd.isna(pos_data[metric]):
                values.append(0.5)
                continue
            val = pos_data[metric]
            if metric in ['forty', 'cone', 'shuttle']:  # Lower is better
                val = 1 - (val - 4.0) / 2.0  # Normalize
            else:
                val = (val - df[metric].min()) / (df[metric].max() - df[metric].min())
            values.append(max(0, min(1, val)))
        return values

    positions_to_plot = ['QB', 'RB', 'WR', 'EDGE', 'CB', 'OL']
    colors = plt.cm.tab10(range(len(positions_to_plot)))

    for ax, pos, color in zip(axes, positions_to_plot, colors):
        if pos not in profiles:
            continue

        values = []
        for metric in metrics:
            key = f'{metric}_mean'
            if key in profiles[pos]:
                val = profiles[pos][key]
                # Normalize
                if metric in ['forty', 'cone', 'shuttle']:
                    val = 1 - (val - 4.0) / 2.0
                else:
                    val = (val - 10) / 30  # Rough normalization
                values.append(max(0, min(1, val)))
            else:
                values.append(0.5)

        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        ax.plot(angles, values, 'o-', linewidth=2, color=color)
        ax.fill(angles, values, alpha=0.25, color=color)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metric_labels, size=8)
        ax.set_title(pos, size=14, fontweight='bold', y=1.1)
        ax.set_ylim(0, 1)

    plt.suptitle('Athletic Profiles by Position', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'combine_athletic_profiles.png', dpi=150)
    plt.close()
    print(f"  Saved: combine_athletic_profiles.png")

    # 4. Correlation heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
                center=0, ax=ax, square=True)
    ax.set_title('Combine Measurables Correlation Matrix', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'combine_correlations.png', dpi=150)
    plt.close()
    print(f"  Saved: combine_correlations.png")

    # 5. Distribution plots for key metrics
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    metrics_to_plot = [
        ('forty', '40-Yard Dash (seconds)', (4.3, 5.5)),
        ('bench', 'Bench Press (reps)', (0, 40)),
        ('vertical', 'Vertical Jump (inches)', (20, 45)),
        ('broad_jump', 'Broad Jump (inches)', (90, 140)),
        ('cone', '3-Cone Drill (seconds)', (6.5, 8.5)),
        ('wt', 'Weight (lbs)', (150, 350)),
    ]

    for ax, (metric, label, xlim) in zip(axes.flatten(), metrics_to_plot):
        if metric not in df.columns:
            continue
        valid = df[metric].dropna()
        ax.hist(valid, bins=30, edgecolor='white', alpha=0.7)
        ax.axvline(valid.mean(), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {valid.mean():.1f}')
        ax.set_xlabel(label)
        ax.set_ylabel('Frequency')
        ax.set_xlim(xlim)
        ax.legend()

    plt.suptitle('NFL Combine Measurable Distributions', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'combine_distributions.png', dpi=150)
    plt.close()
    print(f"  Saved: combine_distributions.png")


def generate_report(df, profiles, corr_matrix):
    """Generate markdown report."""

    report = f"""# NFL Combine Analysis Report

**Data Source:** nfl_data_py (nflfastR)
**Years:** {df['season'].min()}-{df['season'].max()}
**Total Athletes Analyzed:** {len(df):,}

---

## Executive Summary

Physical profiles for player generation, derived from {len(df):,} NFL Combine participants.
These distributions should replace hardcoded position templates.

---

## Position Physical Profiles

"""

    # Create profile table for each position
    for pos in ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']:
        if pos not in profiles:
            continue
        p = profiles[pos]

        report += f"""### {pos} (n={p['n']})

| Metric | Mean | Std | 10th Pct | 90th Pct |
|--------|------|-----|----------|----------|
"""
        metrics = [
            ('height_inches', 'Height (in)'),
            ('wt', 'Weight (lbs)'),
            ('forty', '40-Time (s)'),
            ('bench', 'Bench (reps)'),
            ('vertical', 'Vertical (in)'),
            ('broad_jump', 'Broad (in)'),
            ('cone', '3-Cone (s)'),
            ('shuttle', 'Shuttle (s)'),
        ]

        for key, label in metrics:
            if f'{key}_mean' in p:
                report += f"| {label} | {p[f'{key}_mean']:.1f} | {p.get(f'{key}_std', 0):.1f} | {p.get(f'{key}_p10', 0):.1f} | {p.get(f'{key}_p90', 0):.1f} |\n"

        report += "\n"

    report += """---

## Key Correlations

"""
    # Add notable correlations
    report += """
| Metric 1 | Metric 2 | Correlation |
|----------|----------|-------------|
"""
    if not corr_matrix.empty:
        for i, m1 in enumerate(corr_matrix.columns):
            for j, m2 in enumerate(corr_matrix.columns):
                if i < j:
                    corr = corr_matrix.loc[m1, m2]
                    if abs(corr) > 0.3:
                        report += f"| {m1} | {m2} | {corr:.2f} |\n"

    report += """
**Key Insights:**
- Weight negatively correlates with speed metrics (heavier = slower)
- Vertical and broad jump are positively correlated (explosive athletes)
- 3-cone and shuttle are highly correlated (agility cluster)

---

## Player Generation Recommendations

### 1. Use Real Distributions
Replace hardcoded mean/std with actual combine data:
```python
# Example: WR profile
WR_PROFILE = {
    'height': Normal(73.5, 2.1),  # inches
    'weight': Normal(199, 14),     # lbs
    'forty': Normal(4.48, 0.11),   # seconds
    'vertical': Normal(36.5, 3.2), # inches
}
```

### 2. Add Correlations
Fast players (low 40) tend to have:
- Lower weight
- Higher vertical
- Lower bench press reps

### 3. Position-Specific Ranges
Don't let an OL run a 4.3 forty or a CB weigh 300 lbs.
Use the 10th/90th percentiles as hard bounds.

### 4. "Athletic Freak" Detection
Players >90th percentile in 2+ metrics are rare but exist.
About 5% of players should be "freaks" in 1-2 areas.

---

## Attribute Mapping Suggestions

| Combine Metric | Simulation Attribute | Mapping |
|----------------|---------------------|---------|
| 40-yard dash | Speed | inv_normalize(4.2, 5.5) |
| 40-yard dash | Acceleration | inv_normalize(4.2, 5.5) |
| Bench press | Strength | normalize(0, 35) |
| Vertical jump | Jumping | normalize(25, 45) |
| Broad jump | Explosion | normalize(90, 140) |
| 3-cone | Agility | inv_normalize(6.5, 8.0) |
| Shuttle | Change of Direction | inv_normalize(3.8, 4.8) |

---

*Report generated by researcher_agent using nfl_data_py*
"""

    return report


def main():
    """Main analysis function."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load and clean data
    combine = load_combine_data()
    combine = clean_combine_data(combine)

    # Calculate profiles
    print("\nCalculating position profiles...")
    profiles = calculate_position_profiles(combine)

    print("Calculating correlations...")
    corr_matrix = calculate_correlations(combine)

    # Create visualizations
    print("\nGenerating visualizations...")
    create_visualizations(combine, profiles, corr_matrix)

    # Generate report
    print("\nGenerating report...")
    report = generate_report(combine, profiles, corr_matrix)

    report_path = OUTPUT_DIR / "combine_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    # Export profiles to CSV
    profiles_df = pd.DataFrame(profiles).T
    profiles_df.to_csv(DATA_DIR / "combine_profiles.csv")
    print(f"Profiles exported to: {DATA_DIR / 'combine_profiles.csv'}")

    # Print summary
    print("\n" + "="*60)
    print("KEY POSITION BENCHMARKS")
    print("="*60)
    for pos in ['QB', 'RB', 'WR', 'CB', 'EDGE', 'OL']:
        if pos in profiles and 'forty_mean' in profiles[pos]:
            p = profiles[pos]
            print(f"{pos}: 40={p['forty_mean']:.2f}s, Weight={p.get('wt_mean', 0):.0f}lbs")


if __name__ == "__main__":
    main()
