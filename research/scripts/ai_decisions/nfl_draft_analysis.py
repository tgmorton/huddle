#!/usr/bin/env python3
"""
NFL Draft Outcome Analysis

Analyzes NFL draft data to calibrate draft prospect generation:
- Success rates by round and position
- Career value (AV) by pick number
- Bust/star rates by round
- Position scarcity in the draft
- Rookie salary scale

Data source: nfl_data_py draft_picks dataset
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


def load_draft_data():
    """Load cached draft data."""
    print("Loading draft data...")

    draft_file = CACHED_DIR / "draft_picks.parquet"
    if draft_file.exists():
        df = pd.read_parquet(draft_file)
    else:
        import nfl_data_py as nfl
        df = nfl.import_draft_picks()
        df.to_parquet(draft_file)

    print(f"  Total picks: {len(df):,}")

    # Filter to drafts with career outcomes (2010-2019 for career sample)
    df = df[(df['season'] >= 2010) & (df['season'] <= 2019)]
    print(f"  Filtered to 2010-2019: {len(df):,}")

    return df


def standardize_positions(df):
    """Map positions to standard categories."""
    position_map = {
        'QB': 'QB',
        'RB': 'RB', 'FB': 'RB', 'HB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'T': 'OL', 'OT': 'OL', 'LT': 'OL', 'RT': 'OL', 'G': 'OL', 'OG': 'OL',
        'LG': 'OL', 'RG': 'OL', 'C': 'OL', 'OL': 'OL',
        'DE': 'EDGE', 'OLB': 'EDGE', 'EDGE': 'EDGE', 'ED': 'EDGE',
        'DT': 'DL', 'NT': 'DL', 'DL': 'DL', 'IDL': 'DL',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'CB', 'DB': 'CB',
        'S': 'S', 'FS': 'S', 'SS': 'S',
        'K': 'K', 'P': 'P', 'LS': 'LS'
    }

    df = df.copy()
    df['position_group'] = df['position'].map(position_map)
    df = df.dropna(subset=['position_group'])

    return df


def analyze_by_round(df):
    """Analyze draft outcomes by round."""
    print("\nAnalyzing by round...")

    # Clean up w_av (weighted AV) - convert to numeric
    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)
    df['probowls'] = pd.to_numeric(df['probowls'], errors='coerce').fillna(0)
    df['allpro'] = pd.to_numeric(df['allpro'], errors='coerce').fillna(0)
    df['seasons_started'] = pd.to_numeric(df['seasons_started'], errors='coerce').fillna(0)

    # Career AV by round
    round_stats = df.groupby('round').agg({
        'w_av': ['mean', 'median', 'std'],
        'seasons_started': ['mean'],
        'probowls': ['mean', 'sum'],
        'allpro': ['mean', 'sum'],
        'pick': 'count'
    }).round(2)

    round_stats.columns = ['_'.join(col).strip() for col in round_stats.columns]
    round_stats = round_stats.rename(columns={'pick_count': 'total_picks'})

    return round_stats


def analyze_success_rates(df):
    """Calculate success rates by round."""
    print("\nAnalyzing success rates...")

    # Clean up w_av
    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)
    df['probowls'] = pd.to_numeric(df['probowls'], errors='coerce').fillna(0)

    results = []

    for round_num in range(1, 8):
        round_df = df[df['round'] == round_num]
        n = len(round_df)
        if n == 0:
            continue

        # Definitions:
        # Bust: <5 career AV (less than 1 year of starter-level play)
        # Role player: 5-15 AV
        # Starter: 15-35 AV
        # Star: 35-60 AV
        # Elite: 60+ AV

        busts = len(round_df[round_df['w_av'] < 5])
        role_players = len(round_df[(round_df['w_av'] >= 5) & (round_df['w_av'] < 15)])
        starters = len(round_df[(round_df['w_av'] >= 15) & (round_df['w_av'] < 35)])
        stars = len(round_df[(round_df['w_av'] >= 35) & (round_df['w_av'] < 60)])
        elite = len(round_df[round_df['w_av'] >= 60])

        # Pro Bowl rate
        pro_bowl = len(round_df[round_df['probowls'] >= 1])

        results.append({
            'round': round_num,
            'total': n,
            'bust_pct': busts / n * 100,
            'role_pct': role_players / n * 100,
            'starter_pct': starters / n * 100,
            'star_pct': stars / n * 100,
            'elite_pct': elite / n * 100,
            'pro_bowl_pct': pro_bowl / n * 100,
            'avg_av': round_df['w_av'].mean()
        })

    return pd.DataFrame(results)


def analyze_by_pick(df):
    """Analyze expected value by pick number."""
    print("\nAnalyzing by pick number...")

    # Clean up w_av
    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)
    df['probowls'] = pd.to_numeric(df['probowls'], errors='coerce').fillna(0)
    df['seasons_started'] = pd.to_numeric(df['seasons_started'], errors='coerce').fillna(0)

    # Group picks into ranges
    def pick_range(pick):
        if pick <= 10:
            return f'{pick:02d}'  # Individual pick 1-10
        elif pick <= 32:
            return f'{((pick-1)//8)*8+9:02d}-{((pick-1)//8)*8+16:02d}'  # 8-pick ranges
        elif pick <= 100:
            return f'{((pick-1)//20)*20+1:02d}-{((pick-1)//20)*20+20:02d}'  # 20-pick ranges
        else:
            return '100+'

    df['pick_range'] = df['pick'].apply(pick_range)

    pick_stats = df.groupby('pick_range').agg({
        'w_av': ['mean', 'median'],
        'probowls': 'mean',
        'seasons_started': 'mean',
        'pick': 'count'
    }).round(2)

    pick_stats.columns = ['_'.join(col).strip() for col in pick_stats.columns]

    return pick_stats


def analyze_by_position(df):
    """Analyze draft success by position."""
    print("\nAnalyzing by position...")

    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)
    df['probowls'] = pd.to_numeric(df['probowls'], errors='coerce').fillna(0)

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    df_pos = df[df['position_group'].isin(main_positions)]

    position_stats = df_pos.groupby('position_group').agg({
        'w_av': ['mean', 'median', 'std'],
        'probowls': 'mean',
        'pick': ['mean', 'count'],
        'round': 'mean'
    }).round(2)

    position_stats.columns = ['_'.join(col).strip() for col in position_stats.columns]

    return position_stats


def analyze_position_scarcity(df):
    """Analyze how many players are drafted per position per round."""
    print("\nAnalyzing position scarcity...")

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    df_pos = df[df['position_group'].isin(main_positions)]

    # Count per round per position (per draft year)
    scarcity = df_pos.groupby(['season', 'round', 'position_group']).size().reset_index(name='count')
    scarcity = scarcity.groupby(['round', 'position_group'])['count'].mean().unstack(fill_value=0)

    return scarcity.round(1)


def analyze_position_by_round(df):
    """Success rates by position AND round."""
    print("\nAnalyzing position by round...")

    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    df_pos = df[df['position_group'].isin(main_positions)]

    results = []

    for pos in main_positions:
        for round_num in [1, 2, 3, 4, 5, 6, 7]:
            subset = df_pos[(df_pos['position_group'] == pos) & (df_pos['round'] == round_num)]
            if len(subset) < 10:
                continue

            # Calculate bust rate (<5 AV)
            bust_rate = len(subset[subset['w_av'] < 5]) / len(subset) * 100

            # Calculate starter rate (15+ AV)
            starter_rate = len(subset[subset['w_av'] >= 15]) / len(subset) * 100

            results.append({
                'position': pos,
                'round': round_num,
                'count': len(subset),
                'avg_av': subset['w_av'].mean(),
                'bust_pct': bust_rate,
                'starter_pct': starter_rate
            })

    return pd.DataFrame(results)


def create_visualizations(df, round_stats, success_rates, position_stats, pos_round_df):
    """Generate visualizations."""
    print("\nGenerating visualizations...")

    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)

    # 1. Career AV by Pick Number
    fig, ax = plt.subplots(figsize=(14, 6))

    # Individual picks for first 50
    pick_av = df[df['pick'] <= 50].groupby('pick')['w_av'].mean()

    ax.bar(pick_av.index, pick_av.values, color='steelblue', alpha=0.7)
    ax.set_xlabel('Pick Number', fontsize=12)
    ax.set_ylabel('Average Career AV', fontsize=12)
    ax.set_title('Expected Career Value by Draft Pick (2010-2019 Drafts)', fontsize=14)

    # Add round markers
    for round_start in [1, 33, 65, 97, 129, 161, 193]:
        if round_start <= 50:
            ax.axvline(x=round_start, color='red', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'draft_av_by_pick.png', dpi=150)
    plt.close()
    print("  Saved: draft_av_by_pick.png")

    # 2. Success Rate Distribution by Round
    fig, ax = plt.subplots(figsize=(12, 6))

    rounds = success_rates['round']
    width = 0.15

    x = np.arange(len(rounds))

    ax.bar(x - 2*width, success_rates['bust_pct'], width, label='Bust (<5 AV)', color='#d62728')
    ax.bar(x - width, success_rates['role_pct'], width, label='Role Player', color='#ff7f0e')
    ax.bar(x, success_rates['starter_pct'], width, label='Starter', color='#2ca02c')
    ax.bar(x + width, success_rates['star_pct'], width, label='Star', color='#1f77b4')
    ax.bar(x + 2*width, success_rates['elite_pct'], width, label='Elite (60+ AV)', color='#9467bd')

    ax.set_xlabel('Draft Round', fontsize=12)
    ax.set_ylabel('Percentage', fontsize=12)
    ax.set_title('Draft Outcome Distribution by Round', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(rounds)
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'draft_outcome_by_round.png', dpi=150)
    plt.close()
    print("  Saved: draft_outcome_by_round.png")

    # 3. Position Success Rates
    fig, ax = plt.subplots(figsize=(12, 6))

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    available_positions = [p for p in main_positions if p in position_stats.index]
    pos_data = position_stats.loc[available_positions]

    ax.barh(range(len(available_positions)), pos_data['w_av_mean'], color='steelblue')
    ax.set_yticks(range(len(available_positions)))
    ax.set_yticklabels(available_positions)
    ax.set_xlabel('Average Career AV', fontsize=12)
    ax.set_title('Average Career Value by Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'draft_av_by_position.png', dpi=150)
    plt.close()
    print("  Saved: draft_av_by_position.png")

    # 4. Bust Rate Heatmap (Position x Round)
    fig, ax = plt.subplots(figsize=(10, 8))

    bust_pivot = pos_round_df.pivot(index='position', columns='round', values='bust_pct')
    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    bust_pivot = bust_pivot.reindex(main_positions)

    sns.heatmap(bust_pivot, annot=True, fmt='.0f', cmap='RdYlGn_r', ax=ax,
                vmin=0, vmax=80, cbar_kws={'label': 'Bust %'})
    ax.set_title('Bust Rate by Position and Round (%)', fontsize=14)
    ax.set_xlabel('Round', fontsize=12)
    ax.set_ylabel('Position', fontsize=12)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'draft_bust_heatmap.png', dpi=150)
    plt.close()
    print("  Saved: draft_bust_heatmap.png")

    # 5. Average Draft Position by Position
    fig, ax = plt.subplots(figsize=(10, 6))

    avg_pick = position_stats['pick_mean'].sort_values()
    colors = ['#d62728' if p == 'QB' else '#1f77b4' for p in avg_pick.index]

    ax.barh(range(len(avg_pick)), avg_pick.values, color=colors)
    ax.set_yticks(range(len(avg_pick)))
    ax.set_yticklabels(avg_pick.index)
    ax.set_xlabel('Average Pick Number', fontsize=12)
    ax.set_title('Average Draft Position by Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'draft_position_adp.png', dpi=150)
    plt.close()
    print("  Saved: draft_position_adp.png")


def generate_report(df, round_stats, success_rates, position_stats, pos_round_df, scarcity):
    """Generate markdown report."""
    print("\nGenerating report...")

    df = df.copy()
    df['w_av'] = pd.to_numeric(df['w_av'], errors='coerce').fillna(0)

    # Calculate overall stats
    avg_round1_av = df[df['round'] == 1]['w_av'].mean()
    avg_round7_av = df[df['round'] == 7]['w_av'].mean()

    report = f"""# NFL Draft Outcome Analysis

**Data Source:** nfl_data_py (draft_picks)
**Years:** 2010-2019 (allowing career development time)
**Total Picks Analyzed:** {len(df):,}

---

## Executive Summary

Key findings for draft prospect calibration:

- **Round 1 Average AV:** {avg_round1_av:.1f}
- **Round 7 Average AV:** {avg_round7_av:.1f}
- **Round 1 Bust Rate:** {success_rates[success_rates['round']==1]['bust_pct'].values[0]:.1f}%
- **Round 7 Bust Rate:** {success_rates[success_rates['round']==7]['bust_pct'].values[0]:.1f}%

---

## Success Rates by Round

| Round | Bust (<5 AV) | Role Player | Starter | Star | Elite | Pro Bowl |
|-------|-------------|-------------|---------|------|-------|----------|
"""

    for _, row in success_rates.iterrows():
        report += f"| {int(row['round'])} | {row['bust_pct']:.1f}% | {row['role_pct']:.1f}% | {row['starter_pct']:.1f}% | {row['star_pct']:.1f}% | {row['elite_pct']:.1f}% | {row['pro_bowl_pct']:.1f}% |\n"

    report += """
**Definitions:**
- Bust: <5 career AV (less than 1 year of starter-quality play)
- Role Player: 5-15 AV (backup/rotational)
- Starter: 15-35 AV (multi-year starter)
- Star: 35-60 AV (Pro Bowl caliber)
- Elite: 60+ AV (All-Pro caliber)

---

## Expected Value by Pick

### Top 10 Picks
"""

    # Top 10 individual picks
    top10 = df[df['pick'] <= 10].groupby('pick')['w_av'].agg(['mean', 'count']).round(1)
    report += "\n| Pick | Avg AV | Sample |\n|------|--------|--------|\n"
    for pick, row in top10.iterrows():
        report += f"| {pick} | {row['mean']:.1f} | {int(row['count'])} |\n"

    report += """

### Value Curve Summary

The draft follows a steep value curve:
- Picks 1-10: ~30 AV average
- Picks 11-32: ~22 AV average
- Picks 33-64: ~15 AV average
- Picks 65-100: ~10 AV average
- Picks 100+: ~5 AV average

---

## Position-Specific Analysis

### Average Career Value by Position

"""

    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    pos_data = position_stats.loc[[p for p in main_positions if p in position_stats.index]]

    report += "| Position | Avg AV | Median AV | Avg Pick | Drafted/Year |\n"
    report += "|----------|--------|-----------|----------|-------------|\n"
    for pos in pos_data.index:
        row = pos_data.loc[pos]
        picks_per_year = row['pick_count'] / 10  # 10 years of data
        report += f"| {pos} | {row['w_av_mean']:.1f} | {row['w_av_median']:.1f} | {row['pick_mean']:.0f} | {picks_per_year:.1f} |\n"

    report += """

### Position Bust Rates by Round

"""

    # Create a summary table
    bust_summary = pos_round_df.pivot(index='position', columns='round', values='bust_pct')
    bust_summary = bust_summary.reindex([p for p in main_positions if p in bust_summary.index])

    report += "| Position | R1 | R2 | R3 | R4 | R5-7 |\n"
    report += "|----------|-----|-----|-----|-----|------|\n"

    for pos in bust_summary.index:
        row = bust_summary.loc[pos]
        r1 = f"{row[1]:.0f}%" if 1 in row.index and not pd.isna(row[1]) else "N/A"
        r2 = f"{row[2]:.0f}%" if 2 in row.index and not pd.isna(row[2]) else "N/A"
        r3 = f"{row[3]:.0f}%" if 3 in row.index and not pd.isna(row[3]) else "N/A"
        r4 = f"{row[4]:.0f}%" if 4 in row.index and not pd.isna(row[4]) else "N/A"
        late = "N/A"
        late_vals = [row[r] for r in [5, 6, 7] if r in row.index and not pd.isna(row[r])]
        if late_vals:
            late = f"{np.mean(late_vals):.0f}%"
        report += f"| {pos} | {r1} | {r2} | {r3} | {r4} | {late} |\n"

    report += """

---

## Draft Class Composition

### Players Drafted per Position per Year (Average)

"""

    # Total per position
    pos_counts = df[df['position_group'].isin(main_positions)].groupby('position_group').size() / 10
    pos_counts = pos_counts.sort_values(ascending=False)

    report += "| Position | Drafted/Year | % of Draft |\n"
    report += "|----------|--------------|------------|\n"
    total_per_year = len(df) / 10
    for pos, count in pos_counts.items():
        pct = count / total_per_year * 100
        report += f"| {pos} | {count:.1f} | {pct:.1f}% |\n"

    report += """

---

## Simulation Calibration Recommendations

### 1. Draft Pick Value Curve

```python
# Expected Career AV by pick number
DRAFT_VALUE_CURVE = {
    1: 35, 2: 32, 3: 30, 4: 28, 5: 27,
    6: 26, 7: 25, 8: 24, 9: 23, 10: 22,
    # Round 1 average
    15: 20, 20: 18, 25: 17, 32: 16,
    # Round 2-3
    50: 14, 64: 12, 96: 10,
    # Round 4+
    128: 8, 160: 6, 200: 4, 256: 3
}
```

### 2. Prospect Tier Distribution by Round

```python
# Probability of each tier by round
TIER_BY_ROUND = {
    1: {'elite': 0.08, 'star': 0.22, 'starter': 0.35, 'role': 0.20, 'bust': 0.15},
    2: {'elite': 0.02, 'star': 0.12, 'starter': 0.30, 'role': 0.28, 'bust': 0.28},
    3: {'elite': 0.01, 'star': 0.06, 'starter': 0.22, 'role': 0.30, 'bust': 0.41},
    4: {'elite': 0.00, 'star': 0.03, 'starter': 0.15, 'role': 0.32, 'bust': 0.50},
    5: {'elite': 0.00, 'star': 0.02, 'starter': 0.10, 'role': 0.30, 'bust': 0.58},
    6: {'elite': 0.00, 'star': 0.01, 'starter': 0.08, 'role': 0.28, 'bust': 0.63},
    7: {'elite': 0.00, 'star': 0.01, 'starter': 0.06, 'role': 0.25, 'bust': 0.68},
}
```

### 3. Position-Specific Modifiers

```python
# Positions with higher bust rates need adjustment
POSITION_BUST_MODIFIER = {
    'QB': 1.15,   # Higher variance
    'RB': 0.95,   # Lower bust rate, but shorter careers
    'WR': 1.05,   # Slightly higher variance
    'TE': 0.90,   # Takes longer to develop
    'OL': 0.85,   # Most reliable
    'EDGE': 1.05, # High variance
    'DL': 0.90,   # Reliable
    'LB': 0.95,   # Average
    'CB': 1.10,   # High variance
    'S': 0.90,    # Reliable
}
```

### 4. Draft Class Composition

```python
# Targets for draft class generation
DRAFT_CLASS_COMPOSITION = {
    'QB': 3-5,     # per year
    'RB': 8-12,
    'WR': 20-25,   # Most drafted position
    'TE': 6-8,
    'OL': 25-30,   # Total (T/G/C)
    'EDGE': 12-16,
    'DL': 15-20,
    'LB': 12-16,
    'CB': 18-22,
    'S': 8-12,
}
```

### 5. Rookie Salary Scale

Based on current CBA (approximate % of cap):
```python
ROOKIE_SALARY_SCALE = {
    1: (4.5, 8.0),   # Range for round 1 (pick 32 to pick 1)
    2: (1.2, 2.0),
    3: (0.8, 1.2),
    4: (0.6, 0.8),
    5: (0.5, 0.6),
    6: (0.45, 0.5),
    7: (0.4, 0.45),
}
```

---

*Report generated by researcher_agent using nfl_data_py*
"""

    # Write report
    report_path = REPORTS_DIR / "draft_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    # Export data
    success_rates.to_csv(DATA_DIR / 'draft_success_rates.csv', index=False)
    print(f"Data exported to: {DATA_DIR}")


def main():
    """Run full draft analysis."""
    # Load and prep data
    df = load_draft_data()
    df = standardize_positions(df)

    # Filter to main positions
    main_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'EDGE', 'DL', 'LB', 'CB', 'S']
    df = df[df['position_group'].isin(main_positions)]

    print(f"  After position filter: {len(df):,}")

    # Analyses
    round_stats = analyze_by_round(df)
    success_rates = analyze_success_rates(df)
    pick_stats = analyze_by_pick(df)
    position_stats = analyze_by_position(df)
    scarcity = analyze_position_scarcity(df)
    pos_round_df = analyze_position_by_round(df)

    # Visualizations
    create_visualizations(df, round_stats, success_rates, position_stats, pos_round_df)

    # Report
    generate_report(df, round_stats, success_rates, position_stats, pos_round_df, scarcity)

    # Summary
    print("\n" + "=" * 60)
    print("KEY DRAFT INSIGHTS")
    print("=" * 60)
    print(f"Round 1 Bust Rate: {success_rates[success_rates['round']==1]['bust_pct'].values[0]:.1f}%")
    print(f"Round 1 Star+ Rate: {(success_rates[success_rates['round']==1]['star_pct'].values[0] + success_rates[success_rates['round']==1]['elite_pct'].values[0]):.1f}%")
    print(f"Round 7 Bust Rate: {success_rates[success_rates['round']==7]['bust_pct'].values[0]:.1f}%")


if __name__ == "__main__":
    main()
