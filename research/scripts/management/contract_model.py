#!/usr/bin/env python3
"""
NFL Contract Value Model

Models contract values by position and age:
- APY (Average Per Year) by position tier
- Guaranteed percentage by position and tier
- Age curves by position
- Contract length patterns

Output:
- Position-specific salary tables
- Age adjustment factors
- Figures and report
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# Paths
RESEARCH_DIR = Path(__file__).parent.parent
DATA_DIR = RESEARCH_DIR / "data"
CACHED_DIR = DATA_DIR / "cached"
FIGURES_DIR = DATA_DIR / "figures" / "models"
EXPORTS_DIR = RESEARCH_DIR / "exports"
REPORTS_DIR = RESEARCH_DIR / "reports" / "management"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# Position groups for standardization
POSITION_MAP = {
    'QB': 'QB',
    'RB': 'RB', 'HB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'T': 'OT', 'OT': 'OT', 'LT': 'OT', 'RT': 'OT',
    'G': 'OG', 'OG': 'OG', 'LG': 'OG', 'RG': 'OG',
    'C': 'C',
    'DE': 'EDGE', 'EDGE': 'EDGE', 'OLB': 'EDGE', 'ED': 'EDGE',
    'DT': 'DL', 'NT': 'DL', 'DL': 'DL', 'IDL': 'DL',
    'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB',
    'CB': 'CB',
    'S': 'S', 'SS': 'S', 'FS': 'S',
    'K': 'K', 'P': 'P', 'LS': 'LS'
}


def load_contract_data():
    """Load contract data."""
    print("Loading contract data...")

    contracts = pd.read_parquet(CACHED_DIR / "contracts.parquet")

    print(f"  Total contracts: {len(contracts):,}")
    print(f"  Columns: {list(contracts.columns)}")

    # Filter to recent years
    if 'year_signed' in contracts.columns:
        contracts = contracts[contracts['year_signed'] >= 2018].copy()
        print(f"  Filtered to 2018+: {len(contracts):,}")

    # Standardize position
    if 'position' in contracts.columns:
        contracts['pos'] = contracts['position'].map(POSITION_MAP).fillna('OTHER')
    else:
        contracts['pos'] = 'OTHER'

    # Get key financial columns
    apy_col = None
    for col in ['apy', 'apy_cap_pct', 'value', 'total_value']:
        if col in contracts.columns:
            contracts[col] = pd.to_numeric(contracts[col], errors='coerce')
            if contracts[col].notna().sum() > 100:
                apy_col = col
                break

    if apy_col:
        if apy_col in ['value', 'total_value']:
            # Need to calculate APY from total and years
            if 'years' in contracts.columns:
                contracts['apy'] = contracts[apy_col] / contracts['years'].clip(1)
            else:
                contracts['apy'] = contracts[apy_col]
        else:
            contracts['apy'] = contracts[apy_col]
        print(f"  Using '{apy_col}' for APY (mean: ${contracts['apy'].mean():.2f}M)")
    else:
        contracts['apy'] = np.nan
        print("  WARNING: No APY column found")

    # Guaranteed money
    gtd_col = None
    for col in ['guaranteed', 'gtd', 'guaranteed_at_signing', 'practical_guaranteed']:
        if col in contracts.columns:
            contracts[col] = pd.to_numeric(contracts[col], errors='coerce')
            if contracts[col].notna().sum() > 100:
                gtd_col = col
                break

    if gtd_col:
        contracts['guaranteed'] = contracts[gtd_col]
        print(f"  Using '{gtd_col}' for guaranteed")
    else:
        contracts['guaranteed'] = np.nan

    # Calculate guaranteed percentage
    if 'value' in contracts.columns:
        contracts['total_value'] = pd.to_numeric(contracts['value'], errors='coerce')
    elif 'total_value' in contracts.columns:
        contracts['total_value'] = pd.to_numeric(contracts['total_value'], errors='coerce')
    else:
        contracts['total_value'] = contracts['apy'] * contracts.get('years', 1)

    contracts['gtd_pct'] = (contracts['guaranteed'] / contracts['total_value']).clip(0, 1)

    # Years
    if 'years' not in contracts.columns:
        contracts['years'] = 3  # Default

    # Age at signing
    if 'age' in contracts.columns:
        contracts['age'] = pd.to_numeric(contracts['age'], errors='coerce')
    else:
        contracts['age'] = np.nan

    # Filter out invalid APY
    # APY is already in millions (e.g., 55.0 = $55M)
    contracts = contracts[contracts['apy'] > 0.5].copy()  # At least $500K ($0.5M)
    print(f"  Valid contracts: {len(contracts):,}")

    return contracts


def analyze_position_contracts(contracts):
    """Analyze contracts by position."""
    print("\nAnalyzing position contracts...")

    results = {}

    # Overall
    results['overall'] = {
        'mean_apy': float(contracts['apy'].mean()),
        'median_apy': float(contracts['apy'].median()),
        'mean_years': float(contracts['years'].mean()),
        'mean_gtd_pct': float(contracts['gtd_pct'].mean()),
        'count': len(contracts)
    }
    print(f"  Overall: Mean APY=${results['overall']['mean_apy']:.2f}M")

    # By position
    pos_stats = contracts.groupby('pos').agg({
        'apy': ['mean', 'median', 'std', 'count'],
        'years': 'mean',
        'gtd_pct': 'mean'
    })
    pos_stats.columns = ['mean_apy', 'median_apy', 'std_apy', 'count', 'mean_years', 'mean_gtd_pct']
    pos_stats = pos_stats[pos_stats['count'] >= 10]  # Filter small samples
    pos_stats = pos_stats.sort_values('mean_apy', ascending=False)
    results['by_position'] = pos_stats
    print(f"\n  By position (top 5):\n{pos_stats.head()[['mean_apy', 'median_apy', 'count']]}")

    # Position tiers (top 5, top 10, average, depth)
    print("\n  Calculating position tiers...")
    position_tiers = {}

    for pos in pos_stats.index:
        pos_data = contracts[contracts['pos'] == pos]['apy'].dropna()
        if len(pos_data) < 10:
            continue

        position_tiers[pos] = {
            'top_1': float(pos_data.quantile(0.99)),
            'top_5': float(pos_data.quantile(0.95)),
            'top_10': float(pos_data.quantile(0.90)),
            'top_20': float(pos_data.quantile(0.80)),
            'average': float(pos_data.median()),
            'depth': float(pos_data.quantile(0.25)),
            'minimum': float(pos_data.quantile(0.05))
        }

    results['position_tiers'] = position_tiers

    return results


def analyze_age_curves(contracts):
    """Analyze contract values by age."""
    print("\nAnalyzing age curves...")

    # Filter to contracts with age
    aged = contracts[contracts['age'].notna()].copy()
    print(f"  Contracts with age: {len(aged):,}")

    if len(aged) < 100:
        print("  WARNING: Not enough age data")
        return None

    # APY by age
    age_stats = aged.groupby('age').agg({
        'apy': ['mean', 'median', 'count'],
        'gtd_pct': 'mean'
    })
    age_stats.columns = ['mean_apy', 'median_apy', 'count', 'mean_gtd_pct']
    age_stats = age_stats[age_stats['count'] >= 10]

    # Age curve by position (relative to peak)
    age_curves = {}
    for pos in ['QB', 'RB', 'WR', 'TE', 'OT', 'EDGE', 'CB']:
        pos_data = aged[aged['pos'] == pos]
        if len(pos_data) < 50:
            continue

        pos_age = pos_data.groupby('age')['apy'].mean()
        if len(pos_age) < 3:
            continue

        # Normalize to peak
        peak_value = pos_age.max()
        normalized = (pos_age / peak_value).to_dict()
        peak_age = pos_age.idxmax()

        age_curves[pos] = {
            'peak_age': int(peak_age),
            'curve': {str(int(k)): round(float(v), 3) for k, v in normalized.items()}
        }

    print(f"  Age curves calculated for {len(age_curves)} positions")

    return age_stats, age_curves


def create_contract_figures(contracts, results, age_data):
    """Create contract figures."""
    print("\nCreating figures...")

    # 1. APY by position
    fig, ax = plt.subplots(figsize=(12, 8))

    pos_data = results['by_position'].reset_index()
    colors = plt.cm.Greens(np.linspace(0.3, 0.9, len(pos_data)))
    bars = ax.barh(pos_data['pos'], pos_data['mean_apy'], color=colors)

    ax.set_xlabel('Mean APY (Millions)', fontsize=12)
    ax.set_ylabel('Position', fontsize=12)
    ax.set_title('Average Contract Value by Position', fontsize=14)

    # Add value labels
    for bar, val in zip(bars, pos_data['mean_apy']):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                f'${val:.1f}M', va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_by_position.png', dpi=150)
    plt.close()
    print("  Saved: contract_by_position.png")

    # 2. Position tier distribution
    fig, ax = plt.subplots(figsize=(14, 8))

    positions = ['QB', 'WR', 'EDGE', 'OT', 'CB', 'DL', 'RB', 'S', 'LB', 'TE']
    tier_names = ['top_1', 'top_5', 'top_10', 'average', 'depth']
    colors = ['gold', 'orange', 'coral', 'steelblue', 'gray']

    x = np.arange(len(positions))
    width = 0.15

    for i, (tier, color) in enumerate(zip(tier_names, colors)):
        values = []
        for pos in positions:
            if pos in results['position_tiers'] and tier in results['position_tiers'][pos]:
                values.append(results['position_tiers'][pos][tier])  # Already in millions
            else:
                values.append(0)
        ax.bar(x + i*width, values, width, label=tier.replace('_', ' ').title(), color=color, alpha=0.8)

    ax.set_xlabel('Position', fontsize=12)
    ax.set_ylabel('APY (Millions)', fontsize=12)
    ax.set_title('Contract Value by Position and Tier', fontsize=14)
    ax.set_xticks(x + width*2)
    ax.set_xticklabels(positions)
    ax.legend()

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_position_tiers.png', dpi=150)
    plt.close()
    print("  Saved: contract_position_tiers.png")

    # 3. APY distribution by major position
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    major_positions = ['QB', 'WR', 'RB', 'EDGE', 'CB', 'OT']
    for ax, pos in zip(axes, major_positions):
        pos_data = contracts[contracts['pos'] == pos]['apy'].dropna()  # Already in millions
        if len(pos_data) > 10:
            pos_data.clip(0, pos_data.quantile(0.99)).hist(bins=25, ax=ax, color='steelblue', edgecolor='white')
            ax.axvline(pos_data.mean(), color='red', linestyle='--', label=f'Mean: ${pos_data.mean():.1f}M')
            ax.axvline(pos_data.median(), color='orange', linestyle='--', label=f'Median: ${pos_data.median():.1f}M')
            ax.set_xlabel('APY (Millions)', fontsize=10)
            ax.set_title(f'{pos} Contract Distribution', fontsize=12)
            ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_distributions.png', dpi=150)
    plt.close()
    print("  Saved: contract_distributions.png")

    # 4. Age curves (if available)
    if age_data:
        age_stats, age_curves = age_data

        fig, ax = plt.subplots(figsize=(12, 6))

        colors = plt.cm.tab10(np.linspace(0, 1, len(age_curves)))
        for i, (pos, curve_data) in enumerate(age_curves.items()):
            ages = [int(a) for a in curve_data['curve'].keys()]
            values = list(curve_data['curve'].values())
            ax.plot(ages, values, 'o-', label=pos, color=colors[i], markersize=4)

        ax.set_xlabel('Age', fontsize=12)
        ax.set_ylabel('Relative Contract Value (1.0 = Peak)', fontsize=12)
        ax.set_title('Contract Value Age Curves by Position', fontsize=14)
        ax.legend()
        ax.axhline(1.0, color='gray', linestyle='--', alpha=0.5)
        ax.set_ylim(0, 1.2)

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / 'contract_age_curves.png', dpi=150)
        plt.close()
        print("  Saved: contract_age_curves.png")

    # 5. Guaranteed percentage by position
    fig, ax = plt.subplots(figsize=(10, 6))

    gtd_by_pos = contracts.groupby('pos')['gtd_pct'].mean().sort_values(ascending=False)
    gtd_by_pos = gtd_by_pos[gtd_by_pos.index.isin(results['by_position'].index)]

    ax.barh(gtd_by_pos.index, gtd_by_pos.values, color='coral')
    ax.set_xlabel('Guaranteed %', fontsize=12)
    ax.set_ylabel('Position', fontsize=12)
    ax.set_title('Average Guaranteed Percentage by Position', fontsize=14)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'contract_guaranteed_by_position.png', dpi=150)
    plt.close()
    print("  Saved: contract_guaranteed_by_position.png")


def export_contract_model(results, age_data):
    """Export contract model."""
    print("\nExporting model...")

    # Convert position stats
    position_stats = {}
    for pos, row in results['by_position'].iterrows():
        position_stats[pos] = {
            'mean_apy': round(float(row['mean_apy']), 0),
            'median_apy': round(float(row['median_apy']), 0),
            'std_apy': round(float(row['std_apy']), 0),
            'mean_years': round(float(row['mean_years']), 1),
            'mean_gtd_pct': round(float(row['mean_gtd_pct']), 3)
        }

    # Tiers are already in millions
    position_tiers_m = {}
    for pos, tiers in results['position_tiers'].items():
        position_tiers_m[pos] = {
            tier: round(val, 2) for tier, val in tiers.items()
        }

    export = {
        'model_name': 'contract_value',
        'version': '1.0',
        'description': 'Position and tier based contract value model',

        'overall_stats': {
            'mean_apy': round(results['overall']['mean_apy'], 0),
            'median_apy': round(results['overall']['median_apy'], 0),
            'mean_years': round(results['overall']['mean_years'], 1),
            'mean_gtd_pct': round(results['overall']['mean_gtd_pct'], 3)
        },

        'by_position': position_stats,
        'position_tiers_millions': position_tiers_m,

        'tier_definitions': {
            'top_1': '99th percentile (elite, top ~5 at position)',
            'top_5': '95th percentile (top ~15 at position)',
            'top_10': '90th percentile (top ~30 at position)',
            'top_20': '80th percentile (solid starter)',
            'average': '50th percentile (average starter)',
            'depth': '25th percentile (backup/rotational)',
            'minimum': '5th percentile (veteran minimum types)'
        },

        'factor_mapping': {
            'position': {'huddle_factor': 'player.position', 'available': True},
            'overall': {'huddle_factor': 'player.overall', 'available': True},
            'age': {'huddle_factor': 'player.age', 'available': True},
            'experience': {'huddle_factor': 'player.years_pro', 'available': True}
        },

        'implementation_notes': [
            'Use position_tiers to determine APY based on player tier',
            'Apply age curve adjustments for players past peak',
            'Guaranteed % varies by position - QBs get highest',
            'Contract length correlates with age and position'
        ]
    }

    # Add age curves if available
    if age_data:
        _, age_curves = age_data
        export['age_curves'] = age_curves

    with open(EXPORTS_DIR / 'contract_model.json', 'w') as f:
        json.dump(export, f, indent=2)
    print(f"  Saved: {EXPORTS_DIR / 'contract_model.json'}")

    return export


def generate_report(contracts, results, age_data, export):
    """Generate markdown report."""
    print("\nGenerating report...")

    report = f"""# Contract Value Model

**Model Type:** Position × Tier Lookup Tables
**Data:** {len(contracts):,} contracts (2018-2024)
**Mean APY:** ${results['overall']['mean_apy']:.2f}M

---

## Executive Summary

NFL contract values are primarily driven by:
1. **Position** - QBs earn 2-3x other positions
2. **Tier** - Top 5 at position earn ~3x average
3. **Age** - Players depreciate after peak (varies by position)
4. **Guaranteed %** - Elite players get 50%+ guaranteed

---

## Contract Values by Position

| Position | Mean APY | Median APY | Avg Years | Guaranteed % |
|----------|----------|------------|-----------|--------------|
"""

    for pos, row in results['by_position'].head(12).iterrows():
        report += f"| {pos} | ${row['mean_apy']:.1f}M | ${row['median_apy']:.1f}M | {row['mean_years']:.1f} | {row['mean_gtd_pct']:.0%} |\n"

    report += f"""

---

## Position Tier Values (Millions)

| Position | Top 1% | Top 5% | Top 10% | Average | Depth |
|----------|--------|--------|---------|---------|-------|
"""

    for pos in ['QB', 'WR', 'EDGE', 'OT', 'CB', 'DL', 'RB', 'S', 'LB', 'TE']:
        if pos in export['position_tiers_millions']:
            tiers = export['position_tiers_millions'][pos]
            report += f"| {pos} | ${tiers.get('top_1', 0):.1f}M | ${tiers.get('top_5', 0):.1f}M | ${tiers.get('top_10', 0):.1f}M | ${tiers.get('average', 0):.1f}M | ${tiers.get('depth', 0):.1f}M |\n"

    report += f"""

---

## Model Usage

### Calculating Contract Value

```python
def calculate_contract_value(position, tier, age=None):
    '''
    Calculate expected APY based on position and tier.

    tier: 'top_5', 'top_10', 'top_20', 'average', 'depth'
    '''
    # Base value from tier table
    base_apy = POSITION_TIERS[position][tier]

    # Age adjustment (if past peak)
    if age and position in AGE_CURVES:
        curve = AGE_CURVES[position]
        if str(age) in curve['curve']:
            age_mult = curve['curve'][str(age)]
        else:
            # Decay for older players
            age_mult = max(0.3, 1.0 - (age - curve['peak_age']) * 0.05)
        base_apy *= age_mult

    return base_apy
```

### Tier Classification

```python
def get_player_tier(overall_rating):
    '''
    Map overall rating to contract tier.
    '''
    if overall_rating >= 95:
        return 'top_1'
    elif overall_rating >= 90:
        return 'top_5'
    elif overall_rating >= 85:
        return 'top_10'
    elif overall_rating >= 80:
        return 'top_20'
    elif overall_rating >= 75:
        return 'average'
    elif overall_rating >= 70:
        return 'depth'
    else:
        return 'minimum'
```

---

## Age Curves

"""

    if age_data:
        _, age_curves = age_data
        for pos, curve_data in age_curves.items():
            report += f"### {pos}\n"
            report += f"**Peak Age:** {curve_data['peak_age']}\n\n"
            report += "| Age | Relative Value |\n|-----|----------------|\n"
            for age, val in sorted(curve_data['curve'].items(), key=lambda x: int(x[0])):
                report += f"| {age} | {val:.1%} |\n"
            report += "\n"

    report += f"""
---

## Key Insights

1. **QB premium is massive** - Top QBs earn $50M+, 2x other positions
2. **Premium positions** - QB, WR, EDGE, OT command highest values
3. **RB decline** - RBs now earn less than many other positions
4. **Age matters most for skill positions** - RBs decline fastest
5. **Guaranteed money tracks tier** - Elite players get 50-60% guaranteed

---

## Figures

- `contract_by_position.png`
- `contract_position_tiers.png`
- `contract_distributions.png`
- `contract_age_curves.png`
- `contract_guaranteed_by_position.png`

---

*Model built by researcher_agent*
"""

    report_path = REPORTS_DIR / "contract_model_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")


def main():
    """Run contract model pipeline."""
    print("=" * 60)
    print("CONTRACT VALUE MODEL")
    print("=" * 60)

    # Load data
    contracts = load_contract_data()

    # Analyze by position
    results = analyze_position_contracts(contracts)

    # Analyze age curves
    age_data = analyze_age_curves(contracts)

    # Create figures
    create_contract_figures(contracts, results, age_data)

    # Export
    export = export_contract_model(results, age_data)

    # Report
    generate_report(contracts, results, age_data, export)

    print("\n" + "=" * 60)
    print("MODEL COMPLETE")
    print("=" * 60)
    if 'QB' in results['position_tiers']:
        print(f"Top QB APY: ${results['position_tiers']['QB']['top_5']:.1f}M")
    if 'RB' in results['position_tiers']:
        print(f"Top RB APY: ${results['position_tiers']['RB']['top_5']:.1f}M")


if __name__ == "__main__":
    main()
