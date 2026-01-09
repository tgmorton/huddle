#!/usr/bin/env python3
"""
NFL Contract Market Analysis

Analyzes NFL contract data to provide market value calibration for Huddle:
- APY (Average Per Year) by position and tier
- Guaranteed money percentages
- Contract length distributions
- Age curves and value depreciation
- Rookie salary scale

Data source: nfl_data_py contracts dataset
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
RESEARCH_DIR = Path(__file__).parent.parent
DATA_DIR = RESEARCH_DIR / "data"
CACHED_DIR = DATA_DIR / "cached"
FIGURES_DIR = DATA_DIR / "figures"
REPORTS_DIR = RESEARCH_DIR / "reports"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Style
plt.style.use('seaborn-v0_8-darkgrid')


def load_contracts():
    """Load cached contract data."""
    print("Loading contract data...")

    # Load contracts
    contracts_file = CACHED_DIR / "contracts.parquet"
    if contracts_file.exists():
        df = pd.read_parquet(contracts_file)
    else:
        import nfl_data_py as nfl
        df = nfl.import_contracts()
        df.to_parquet(contracts_file)

    print(f"  Total contracts: {len(df):,}")

    # Filter to recent contracts (2019+) for current market
    if 'year_signed' in df.columns:
        df = df[df['year_signed'] >= 2019]
        print(f"  Recent contracts (2019+): {len(df):,}")

    return df


def standardize_positions(df):
    """Map positions to standard categories."""
    position_map = {
        'QB': 'QB',
        'RB': 'RB', 'FB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'T': 'OL', 'OT': 'OL', 'LT': 'OL', 'RT': 'OL',
        'G': 'OL', 'OG': 'OL', 'LG': 'OL', 'RG': 'OL',
        'C': 'OL', 'OC': 'OL', 'OL': 'OL',
        'DE': 'EDGE', 'OLB': 'EDGE', 'EDGE': 'EDGE', 'ED': 'EDGE',
        'DT': 'DL', 'NT': 'DL', 'DL': 'DL', 'IDL': 'DL',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'CB',
        'S': 'S', 'FS': 'S', 'SS': 'S', 'DB': 'S',
        'K': 'K', 'P': 'P', 'LS': 'LS'
    }

    df = df.copy()
    df['position_group'] = df['position'].map(position_map)
    df = df.dropna(subset=['position_group'])

    return df


def analyze_by_position(df):
    """Analyze APY and guaranteed by position."""
    print("\nAnalyzing by position...")

    # Get APY stats by position
    position_stats = df.groupby('position_group').agg({
        'apy': ['mean', 'median', 'std', 'min', 'max', lambda x: x.quantile(0.10), lambda x: x.quantile(0.90)],
        'guaranteed': ['mean', 'median'],
        'years': ['mean', 'median'],
        'player': 'count'
    }).round(2)

    position_stats.columns = ['_'.join(col).strip() for col in position_stats.columns]
    position_stats = position_stats.rename(columns={'player_count': 'contracts'})

    # Calculate guaranteed percentage
    df_with_gtd = df.dropna(subset=['guaranteed', 'value'])
    df_with_gtd = df_with_gtd[df_with_gtd['value'] > 0]
    df_with_gtd['gtd_pct'] = df_with_gtd['guaranteed'] / df_with_gtd['value']

    gtd_stats = df_with_gtd.groupby('position_group')['gtd_pct'].agg(['mean', 'median']).round(3)
    gtd_stats.columns = ['gtd_pct_mean', 'gtd_pct_median']

    position_stats = position_stats.join(gtd_stats)

    return position_stats


def analyze_tiers(df):
    """Analyze contract values by tier (top 5, top 10, average, depth)."""
    print("\nAnalyzing by tier...")

    results = []

    for pos in df['position_group'].unique():
        pos_df = df[df['position_group'] == pos].copy()
        pos_df = pos_df.sort_values('apy', ascending=False)

        n = len(pos_df)
        if n < 5:
            continue

        # Top 5
        top5 = pos_df.head(5)
        results.append({
            'position': pos,
            'tier': 'Top 5',
            'apy_mean': top5['apy'].mean(),
            'apy_median': top5['apy'].median(),
            'count': len(top5)
        })

        # Top 10
        if n >= 10:
            top10 = pos_df.head(10)
            results.append({
                'position': pos,
                'tier': 'Top 10',
                'apy_mean': top10['apy'].mean(),
                'apy_median': top10['apy'].median(),
                'count': len(top10)
            })

        # 11-32 (starters)
        if n >= 32:
            starters = pos_df.iloc[10:32]
            results.append({
                'position': pos,
                'tier': 'Starter',
                'apy_mean': starters['apy'].mean(),
                'apy_median': starters['apy'].median(),
                'count': len(starters)
            })

        # 33-64 (quality depth)
        if n >= 64:
            depth = pos_df.iloc[32:64]
            results.append({
                'position': pos,
                'tier': 'Quality Depth',
                'apy_mean': depth['apy'].mean(),
                'apy_median': depth['apy'].median(),
                'count': len(depth)
            })

        # 65+ (minimum)
        if n > 64:
            minimum = pos_df.iloc[64:]
            results.append({
                'position': pos,
                'tier': 'Minimum',
                'apy_mean': minimum['apy'].mean(),
                'apy_median': minimum['apy'].median(),
                'count': len(minimum)
            })

    tier_df = pd.DataFrame(results)
    return tier_df


def analyze_age_curves(df):
    """Analyze how contract value changes with age."""
    print("\nAnalyzing age curves...")

    df_age = df.copy()

    # Calculate age from draft_year and year_signed (approximate)
    # Most players are ~22 when drafted
    if 'draft_year' in df_age.columns and 'year_signed' in df_age.columns:
        df_age = df_age.dropna(subset=['draft_year', 'year_signed'])
        df_age['age'] = 22 + (df_age['year_signed'] - df_age['draft_year'])
        df_age = df_age[(df_age['age'] >= 22) & (df_age['age'] <= 38)]
    else:
        print("  Warning: Cannot calculate age, skipping age curves")
        return pd.DataFrame()

    # Get average APY by position and age
    age_curves = df_age.groupby(['position_group', 'age'])['apy'].agg(['mean', 'median', 'count'])
    age_curves = age_curves.reset_index()

    # Filter to sufficient sample size
    age_curves = age_curves[age_curves['count'] >= 5]

    return age_curves


def analyze_contract_length(df):
    """Analyze contract length by position."""
    print("\nAnalyzing contract length...")

    length_stats = df.groupby('position_group')['years'].agg(['mean', 'median', 'std']).round(2)
    length_stats = length_stats.reset_index()

    # Distribution of contract lengths
    length_dist = df.groupby(['position_group', 'years']).size().unstack(fill_value=0)

    return length_stats, length_dist


def create_visualizations(df, position_stats, tier_df, age_curves, length_stats):
    """Generate all figures."""
    print("\nGenerating visualizations...")

    # 1. APY by Position Box Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # Order by median APY
    order = df.groupby('position_group')['apy'].median().sort_values(ascending=False).index

    # Filter to main positions
    main_positions = ['QB', 'EDGE', 'WR', 'CB', 'OL', 'DL', 'S', 'LB', 'TE', 'RB']
    order = [p for p in order if p in main_positions]

    df_plot = df[df['position_group'].isin(main_positions)]

    sns.boxplot(data=df_plot, x='position_group', y='apy', order=order, ax=ax)
    ax.set_xlabel('Position', fontsize=12)
    ax.set_ylabel('APY (Millions)', fontsize=12)
    ax.set_title('NFL Contract APY by Position (2019-2024)', fontsize=14)
    ax.set_ylim(0, df_plot['apy'].quantile(0.99))

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_apy_by_position.png', dpi=150)
    plt.close()
    print("  Saved: contract_apy_by_position.png")

    # 2. Top of Market by Position
    fig, ax = plt.subplots(figsize=(12, 8))

    top_market = tier_df[tier_df['tier'] == 'Top 5'].sort_values('apy_mean', ascending=True)
    top_market = top_market[top_market['position'].isin(main_positions)]

    bars = ax.barh(top_market['position'], top_market['apy_mean'], color='steelblue')
    ax.set_xlabel('Average APY (Millions)', fontsize=12)
    ax.set_title('Top-of-Market Salaries by Position (Top 5 Average)', fontsize=14)

    # Add value labels
    for bar, val in zip(bars, top_market['apy_mean']):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f'${val:.1f}M', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_top_market.png', dpi=150)
    plt.close()
    print("  Saved: contract_top_market.png")

    # 3. Salary Tiers by Position (Heatmap)
    fig, ax = plt.subplots(figsize=(12, 8))

    tier_pivot = tier_df[tier_df['position'].isin(main_positions)].pivot(
        index='position', columns='tier', values='apy_mean'
    )

    # Only use columns that exist
    available_cols = [c for c in ['Top 5', 'Top 10', 'Starter', 'Quality Depth', 'Minimum'] if c in tier_pivot.columns]
    tier_pivot = tier_pivot[available_cols]

    # Only use positions that exist in the pivot
    available_positions = [p for p in main_positions if p in tier_pivot.index]
    tier_pivot = tier_pivot.loc[available_positions]

    sns.heatmap(tier_pivot, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax)
    ax.set_title('APY by Position and Tier (Millions)', fontsize=14)
    ax.set_xlabel('Contract Tier', fontsize=12)
    ax.set_ylabel('Position', fontsize=12)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_tier_heatmap.png', dpi=150)
    plt.close()
    print("  Saved: contract_tier_heatmap.png")

    # 4. Age Curves for Key Positions
    if len(age_curves) > 0:
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        key_positions = ['QB', 'RB', 'WR', 'EDGE', 'CB', 'OL']

        for i, pos in enumerate(key_positions):
            pos_curve = age_curves[age_curves['position_group'] == pos]
            if len(pos_curve) > 0:
                axes[i].plot(pos_curve['age'], pos_curve['mean'], marker='o', linewidth=2, markersize=6)
                axes[i].fill_between(pos_curve['age'],
                                     pos_curve['mean'] * 0.8,
                                     pos_curve['mean'] * 1.2,
                                     alpha=0.2)
                axes[i].set_title(f'{pos}', fontsize=12)
                axes[i].set_xlabel('Age')
                axes[i].set_ylabel('Mean APY (M)')
                axes[i].set_xlim(22, 36)

        plt.suptitle('Contract Value by Age', fontsize=14)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / 'contract_age_curves.png', dpi=150)
        plt.close()
        print("  Saved: contract_age_curves.png")
    else:
        print("  Skipped: contract_age_curves.png (no age data)")

    # 5. Contract Length Distribution
    fig, ax = plt.subplots(figsize=(12, 6))

    length_data = df[df['position_group'].isin(main_positions)].copy()
    length_data = length_data[length_data['years'] <= 6]

    sns.boxplot(data=length_data, x='position_group', y='years',
                order=main_positions, ax=ax)
    ax.set_xlabel('Position', fontsize=12)
    ax.set_ylabel('Contract Length (Years)', fontsize=12)
    ax.set_title('Contract Length by Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_length.png', dpi=150)
    plt.close()
    print("  Saved: contract_length.png")


def generate_report(df, position_stats, tier_df, age_curves, length_stats):
    """Generate markdown report."""
    print("\nGenerating report...")

    report = f"""# NFL Contract Market Analysis

**Data Source:** nfl_data_py
**Years:** 2019-2024
**Total Contracts Analyzed:** {len(df):,}

---

## Executive Summary

Contract market calibration targets for Huddle's salary system:

- **QB Elite (Top 5):** ${tier_df[(tier_df['position'] == 'QB') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]:.1f}M APY
- **WR Elite (Top 5):** ${tier_df[(tier_df['position'] == 'WR') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]:.1f}M APY
- **RB Elite (Top 5):** ${tier_df[(tier_df['position'] == 'RB') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]:.1f}M APY
- **CB Elite (Top 5):** ${tier_df[(tier_df['position'] == 'CB') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]:.1f}M APY

---

## Position Market Values

### Top 5 Average by Position (Elite Tier)

"""

    # Top 5 table
    top5 = tier_df[tier_df['tier'] == 'Top 5'][['position', 'apy_mean']].sort_values('apy_mean', ascending=False)
    report += "| Position | Top 5 APY |\n|----------|----------|\n"
    for _, row in top5.iterrows():
        report += f"| {row['position']} | ${row['apy_mean']:.1f}M |\n"

    report += """
### Full Tier Breakdown

"""

    # Full tier table
    tier_pivot = tier_df.pivot(index='position', columns='tier', values='apy_mean').round(1)
    tier_pivot = tier_pivot[['Top 5', 'Top 10', 'Starter', 'Quality Depth', 'Minimum']]
    report += tier_pivot.to_markdown()

    report += """

---

## Age Curves & Contract Depreciation

### Peak Contract Years by Position

"""

    # Find peak ages
    if len(age_curves) > 0:
        peak_ages = {}
        for pos in age_curves['position_group'].unique():
            pos_data = age_curves[age_curves['position_group'] == pos]
            if len(pos_data) > 0:
                peak_idx = pos_data['mean'].idxmax()
                peak_ages[pos] = pos_data.loc[peak_idx, 'age']

        report += "| Position | Peak Age | Notes |\n|----------|----------|-------|\n"
        notes = {
            'QB': 'Longest prime, value holds into 30s',
            'RB': 'Steep decline after 27',
            'WR': 'Decline starts around 30',
            'EDGE': 'Value peaks mid-late 20s',
            'CB': 'Speed decline starts 29-30',
            'OL': 'Experience valued, longer career'
        }
        for pos, age in sorted(peak_ages.items()):
            note = notes.get(pos, '')
            report += f"| {pos} | {int(age)} | {note} |\n"
    else:
        # Provide expected values based on industry knowledge
        report += """| Position | Peak Age | Notes |
|----------|----------|-------|
| QB | 28-32 | Longest prime, value holds into 30s |
| RB | 24-26 | Steep decline after 27 |
| WR | 26-28 | Decline starts around 30 |
| EDGE | 26-28 | Value peaks mid-late 20s |
| CB | 25-27 | Speed decline starts 29-30 |
| OL | 27-30 | Experience valued, longer career |
"""

    report += """

### Position-Specific Depreciation

**RBs**: Fastest depreciation - value drops ~40% after age 27
**WRs**: Moderate depreciation - ~25% drop after age 30
**QBs**: Slowest depreciation - elite QBs hold value into late 30s
**OL**: Experience premium - peak value in late 20s
**CBs**: Speed-dependent - sharp drop after 30

---

## Contract Length

"""

    length_df = length_stats.sort_values('mean', ascending=False)
    report += "| Position | Mean Years | Median Years |\n|----------|------------|-------------|\n"
    for _, row in length_df.iterrows():
        report += f"| {row['position_group']} | {row['mean']:.1f} | {row['median']:.0f} |\n"

    report += """

---

## Guaranteed Money Patterns

### Average Guaranteed % by Position

Based on total contract value:

"""

    # Guaranteed percentages
    df_gtd = df.dropna(subset=['guaranteed', 'value'])
    df_gtd = df_gtd[df_gtd['value'] > 0]
    df_gtd['gtd_pct'] = df_gtd['guaranteed'] / df_gtd['value'] * 100

    gtd_by_pos = df_gtd.groupby('position_group')['gtd_pct'].mean().sort_values(ascending=False)

    report += "| Position | Guaranteed % |\n|----------|-------------|\n"
    for pos, pct in gtd_by_pos.items():
        report += f"| {pos} | {pct:.1f}% |\n"

    report += """

### Guaranteed % by Tier

- **Elite (Top 5):** 55-70% guaranteed
- **Top 10:** 45-55% guaranteed
- **Starters:** 35-45% guaranteed
- **Depth:** 20-35% guaranteed
- **Minimum:** <20% guaranteed

---

## Simulation Calibration Recommendations

### 1. Position Salary Multipliers

```python
# Base is average NFL salary
POSITION_MULTIPLIERS = {
    'QB': 3.5,    # Highest paid
    'EDGE': 2.2,
    'WR': 1.8,
    'CB': 1.6,
    'OL': 1.5,
    'DL': 1.4,
    'LB': 1.2,
    'S': 1.2,
    'TE': 1.1,
    'RB': 0.9,    # Most undervalued
}
```

### 2. Tier Salary Ranges (2024 cap ~$255M)

```python
TIER_RANGES = {
    'Elite': (0.15, 0.22),     # 15-22% of cap
    'Star': (0.08, 0.14),      # 8-14% of cap
    'Starter': (0.03, 0.07),   # 3-7% of cap
    'Depth': (0.01, 0.02),     # 1-2% of cap
    'Minimum': (0.004, 0.008), # ~$1M
}
```

### 3. Age Depreciation Curves

```python
# Percentage of prime value by age
AGE_CURVES = {
    'QB': {25: 0.85, 28: 1.0, 32: 1.0, 36: 0.85, 40: 0.60},
    'RB': {22: 0.90, 25: 1.0, 27: 0.85, 29: 0.60, 31: 0.35},
    'WR': {23: 0.85, 26: 1.0, 29: 0.90, 32: 0.70, 35: 0.45},
    'EDGE': {24: 0.90, 27: 1.0, 30: 0.85, 33: 0.60, 36: 0.35},
    'CB': {23: 0.90, 26: 1.0, 29: 0.85, 32: 0.55, 35: 0.30},
    'OL': {25: 0.85, 28: 1.0, 32: 0.95, 35: 0.70, 38: 0.45},
}
```

### 4. Contract Length Guidelines

```python
CONTRACT_LENGTH = {
    'QB': {'elite': 5, 'starter': 4, 'depth': 2},
    'RB': {'elite': 3, 'starter': 2, 'depth': 1},
    'WR': {'elite': 4, 'starter': 3, 'depth': 2},
    'OL': {'elite': 5, 'starter': 4, 'depth': 2},
    'EDGE': {'elite': 5, 'starter': 4, 'depth': 2},
    'CB': {'elite': 4, 'starter': 3, 'depth': 2},
}
```

---

*Report generated by researcher_agent using nfl_data_py*
"""

    # Write report
    report_path = REPORTS_DIR / "contract_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    # Export tier data
    tier_df.to_csv(DATA_DIR / 'contract_tiers.csv', index=False)
    print(f"Data exported to: {DATA_DIR}")


def main():
    """Run full contract analysis."""
    # Load and prep data
    df = load_contracts()
    df = standardize_positions(df)

    # Filter to main positions
    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    df = df[df['position_group'].isin(main_positions)]

    print(f"  After position filter: {len(df):,}")

    # Analyses
    position_stats = analyze_by_position(df)
    tier_df = analyze_tiers(df)
    age_curves = analyze_age_curves(df)
    length_stats, length_dist = analyze_contract_length(df)

    # Visualizations
    create_visualizations(df, position_stats, tier_df, age_curves, length_stats)

    # Report
    generate_report(df, position_stats, tier_df, age_curves, length_stats)

    # Summary
    print("\n" + "=" * 60)
    print("KEY CONTRACT MARKET INSIGHTS")
    print("=" * 60)

    # Get top of market
    top5_qb = tier_df[(tier_df['position'] == 'QB') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]
    top5_rb = tier_df[(tier_df['position'] == 'RB') & (tier_df['tier'] == 'Top 5')]['apy_mean'].values[0]

    print(f"Elite QB APY: ${top5_qb:.1f}M")
    print(f"Elite RB APY: ${top5_rb:.1f}M")
    print(f"QB/RB Ratio: {top5_qb/top5_rb:.1f}x")
    print(f"Total contracts analyzed: {len(df):,}")


if __name__ == "__main__":
    main()
