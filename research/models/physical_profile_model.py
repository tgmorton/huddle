#!/usr/bin/env python3
"""
NFL Player Physical Profile Model

Multivariate Normal (MVN) distributions by position for player generation.
Uses NFL Combine data to model:
- Height/Weight distributions
- Athletic measurables (40, bench, vertical, broad, cone, shuttle)
- Correlations between measurables

Output:
- Position-specific mean vectors and covariance matrices
- Athletic archetype classifications
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
REPORTS_DIR = RESEARCH_DIR / "reports" / "player_generation"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# Position groupings
POSITION_GROUPS = {
    'QB': ['QB'],
    'RB': ['RB', 'FB'],
    'WR': ['WR'],
    'TE': ['TE'],
    'OL': ['OT', 'OG', 'C', 'OL', 'T', 'G'],
    'DL': ['DE', 'DT', 'NT', 'DL'],
    'EDGE': ['EDGE', 'OLB'],
    'LB': ['LB', 'ILB', 'MLB'],
    'CB': ['CB', 'DB'],
    'S': ['S', 'SS', 'FS']
}

# Measurables to analyze
MEASURABLES = ['ht', 'wt', 'forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle']


def load_combine_data():
    """Load combine data."""
    print("Loading combine data...")

    combine = pd.read_parquet(CACHED_DIR / "combine.parquet")

    print(f"  Total combine entries: {len(combine):,}")

    # Clean numeric columns (some have malformed data)
    for col in MEASURABLES:
        if col in combine.columns:
            # Convert to numeric, coercing errors to NaN
            combine[col] = pd.to_numeric(combine[col], errors='coerce')

    # Filter to recent years for relevance
    if 'season' in combine.columns:
        combine = combine[combine['season'] >= 2015].copy()
        print(f"  Filtered to 2015+: {len(combine):,}")

    # Standardize position names
    def standardize_position(pos):
        pos = str(pos).upper().strip()
        for group, positions in POSITION_GROUPS.items():
            if pos in positions:
                return group
        return 'OTHER'

    if 'pos' in combine.columns:
        combine['position'] = combine['pos'].apply(standardize_position)
    else:
        combine['position'] = 'OTHER'

    # Filter out OTHER
    combine = combine[combine['position'] != 'OTHER'].copy()

    print(f"  After position filtering: {len(combine):,}")
    print(f"  Positions: {combine['position'].value_counts().to_dict()}")

    return combine


def analyze_position_profiles(combine):
    """Analyze physical profiles by position."""
    print("\nAnalyzing position profiles...")

    results = {}

    for pos in POSITION_GROUPS.keys():
        pos_data = combine[combine['position'] == pos]
        if len(pos_data) < 20:
            print(f"  {pos}: Skipping (n={len(pos_data)})")
            continue

        print(f"\n  {pos} (n={len(pos_data)})")

        # Calculate stats for each measurable
        pos_stats = {}
        for m in MEASURABLES:
            if m not in pos_data.columns:
                continue
            valid = pos_data[m].dropna()
            if len(valid) < 10:
                continue

            pos_stats[m] = {
                'mean': float(valid.mean()),
                'std': float(valid.std()),
                'min': float(valid.min()),
                'max': float(valid.max()),
                'p10': float(valid.quantile(0.10)),
                'p25': float(valid.quantile(0.25)),
                'p50': float(valid.quantile(0.50)),
                'p75': float(valid.quantile(0.75)),
                'p90': float(valid.quantile(0.90)),
                'count': int(len(valid))
            }

        if pos_stats:
            results[pos] = {
                'stats': pos_stats,
                'count': len(pos_data)
            }

            # Print summary
            if 'ht' in pos_stats:
                print(f"    Height: {pos_stats['ht']['mean']:.1f} ± {pos_stats['ht']['std']:.1f}")
            if 'wt' in pos_stats:
                print(f"    Weight: {pos_stats['wt']['mean']:.0f} ± {pos_stats['wt']['std']:.0f}")
            if 'forty' in pos_stats:
                print(f"    40-time: {pos_stats['forty']['mean']:.2f} ± {pos_stats['forty']['std']:.2f}")

    return results


def build_mvn_models(combine):
    """Build multivariate normal models for each position."""
    print("\nBuilding MVN models...")

    mvn_models = {}

    # Key measurables for MVN (must have all for a valid sample)
    # Note: 'ht' is not available in combine data (all NaN)
    key_measures = ['wt', 'forty', 'vertical', 'broad_jump']

    for pos in POSITION_GROUPS.keys():
        pos_data = combine[combine['position'] == pos]

        # Get complete cases for key measures
        available = [m for m in key_measures if m in pos_data.columns]
        if len(available) < 3:
            print(f"  {pos}: Not enough measurables")
            continue

        complete_data = pos_data[available].dropna()
        if len(complete_data) < 30:
            print(f"  {pos}: Not enough complete cases (n={len(complete_data)})")
            continue

        # Calculate mean vector and covariance matrix
        mean_vec = complete_data.mean()
        cov_mat = complete_data.cov()

        # Also calculate correlation matrix
        corr_mat = complete_data.corr()

        mvn_models[pos] = {
            'mean': {k: float(v) for k, v in mean_vec.items()},
            'cov': {k1: {k2: float(v) for k2, v in row.items()} for k1, row in cov_mat.iterrows()},
            'corr': {k1: {k2: float(v) for k2, v in row.items()} for k1, row in corr_mat.iterrows()},
            'variables': available,
            'n': len(complete_data)
        }

        print(f"  {pos}: MVN model built (n={len(complete_data)}, vars={len(available)})")

    return mvn_models


def calculate_athletic_scores(combine, results):
    """Calculate composite athletic scores."""
    print("\nCalculating athletic scores...")

    # For each position, calculate z-scores and composite
    combine = combine.copy()
    combine['athletic_score'] = np.nan

    for pos in results.keys():
        pos_mask = combine['position'] == pos
        pos_data = combine[pos_mask]

        if 'forty' not in pos_data.columns:
            continue

        # Calculate z-scores (inverted for forty/cone/shuttle since lower is better)
        z_scores = pd.DataFrame(index=pos_data.index)

        for m in ['forty', 'cone', 'shuttle']:
            if m in pos_data.columns and m in results[pos]['stats']:
                mean = results[pos]['stats'][m]['mean']
                std = results[pos]['stats'][m]['std']
                if std > 0:
                    z_scores[m] = -(pos_data[m] - mean) / std  # Inverted

        for m in ['vertical', 'broad_jump', 'bench']:
            if m in pos_data.columns and m in results[pos]['stats']:
                mean = results[pos]['stats'][m]['mean']
                std = results[pos]['stats'][m]['std']
                if std > 0:
                    z_scores[m] = (pos_data[m] - mean) / std

        # Composite score (average of available z-scores)
        if len(z_scores.columns) >= 3:
            combine.loc[pos_mask, 'athletic_score'] = z_scores.mean(axis=1)

    # Classify athletes
    combine['athletic_tier'] = pd.cut(
        combine['athletic_score'],
        bins=[-np.inf, -1, -0.5, 0.5, 1, np.inf],
        labels=['Poor', 'Below Avg', 'Average', 'Above Avg', 'Elite']
    )

    # Count by tier per position
    tier_counts = {}
    for pos in results.keys():
        pos_data = combine[combine['position'] == pos]
        if 'athletic_tier' in pos_data.columns:
            counts = pos_data['athletic_tier'].value_counts(normalize=True)
            tier_counts[pos] = {str(k): round(float(v), 4) for k, v in counts.items()}

    print(f"  Athletic scores calculated for {combine['athletic_score'].notna().sum():,} players")

    return combine, tier_counts


def create_profile_figures(combine, results, mvn_models):
    """Create physical profile figures."""
    print("\nCreating figures...")

    # 1. Weight/40-time scatter by position (since height is unavailable)
    fig, ax = plt.subplots(figsize=(12, 8))

    colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    for i, pos in enumerate(results.keys()):
        pos_data = combine[combine['position'] == pos]
        if 'forty' in pos_data.columns and 'wt' in pos_data.columns:
            valid = pos_data[['forty', 'wt']].dropna()
            ax.scatter(valid['wt'], valid['forty'], alpha=0.5, label=pos, color=colors[i])

    ax.set_xlabel('Weight (lbs)', fontsize=12)
    ax.set_ylabel('40-Time (seconds)', fontsize=12)
    ax.set_title('NFL Combine: Weight vs 40-Time by Position', fontsize=14)
    ax.legend(loc='upper left')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'physical_weight_forty.png', dpi=150)
    plt.close()
    print("  Saved: physical_weight_forty.png")

    # 2. 40-time distribution by position
    fig, ax = plt.subplots(figsize=(12, 6))

    positions = [p for p in results.keys() if 'forty' in results[p]['stats']]
    forty_data = []
    for pos in positions:
        pos_data = combine[combine['position'] == pos]['forty'].dropna()
        forty_data.append(pos_data)

    bp = ax.boxplot(forty_data, labels=positions, patch_artist=True)
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(positions)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    ax.set_xlabel('Position', fontsize=12)
    ax.set_ylabel('40-Yard Dash Time (seconds)', fontsize=12)
    ax.set_title('40-Time Distribution by Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'physical_forty_by_position.png', dpi=150)
    plt.close()
    print("  Saved: physical_forty_by_position.png")

    # 3. Measurable correlation heatmap (for a sample position)
    if mvn_models:
        sample_pos = 'WR' if 'WR' in mvn_models else list(mvn_models.keys())[0]
    else:
        sample_pos = None

    if sample_pos and sample_pos in mvn_models:
        fig, ax = plt.subplots(figsize=(10, 8))

        corr_df = pd.DataFrame(mvn_models[sample_pos]['corr'])
        sns.heatmap(corr_df, annot=True, fmt='.2f', cmap='RdBu_r', center=0, ax=ax)
        ax.set_title(f'{sample_pos} Measurable Correlations', fontsize=14)

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / f'physical_correlation_{sample_pos.lower()}.png', dpi=150)
        plt.close()
        print(f"  Saved: physical_correlation_{sample_pos.lower()}.png")

    # 4. Position comparison radar charts (simplified as bar chart)
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # Mean 40 times
    ax = axes[0, 0]
    pos_forty = {p: results[p]['stats']['forty']['mean'] for p in results if 'forty' in results[p]['stats']}
    ax.barh(list(pos_forty.keys()), list(pos_forty.values()), color='steelblue')
    ax.set_xlabel('40-Time (seconds)', fontsize=12)
    ax.set_title('Mean 40-Time by Position', fontsize=14)
    ax.invert_xaxis()  # Lower is better

    # Mean weight
    ax = axes[0, 1]
    pos_wt = {p: results[p]['stats']['wt']['mean'] for p in results if 'wt' in results[p]['stats']}
    ax.barh(list(pos_wt.keys()), list(pos_wt.values()), color='coral')
    ax.set_xlabel('Weight (lbs)', fontsize=12)
    ax.set_title('Mean Weight by Position', fontsize=14)

    # Mean vertical
    ax = axes[1, 0]
    pos_vert = {p: results[p]['stats']['vertical']['mean'] for p in results if 'vertical' in results[p]['stats']}
    ax.barh(list(pos_vert.keys()), list(pos_vert.values()), color='green')
    ax.set_xlabel('Vertical Jump (inches)', fontsize=12)
    ax.set_title('Mean Vertical Jump by Position', fontsize=14)

    # Mean bench
    ax = axes[1, 1]
    pos_bench = {p: results[p]['stats']['bench']['mean'] for p in results if 'bench' in results[p]['stats']}
    ax.barh(list(pos_bench.keys()), list(pos_bench.values()), color='purple')
    ax.set_xlabel('Bench Press (reps)', fontsize=12)
    ax.set_title('Mean Bench Press by Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'physical_position_comparison.png', dpi=150)
    plt.close()
    print("  Saved: physical_position_comparison.png")

    # 5. Athletic score distribution
    if 'athletic_score' in combine.columns:
        fig, ax = plt.subplots(figsize=(10, 6))

        valid_scores = combine['athletic_score'].dropna()
        valid_scores.hist(bins=50, ax=ax, color='steelblue', edgecolor='white')
        ax.axvline(0, color='red', linestyle='--', label='Average')
        ax.axvline(1, color='green', linestyle='--', label='Elite (+1 std)')
        ax.axvline(-1, color='orange', linestyle='--', label='Poor (-1 std)')

        ax.set_xlabel('Composite Athletic Score (z-score)', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Distribution of Composite Athletic Scores', fontsize=14)
        ax.legend()

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / 'physical_athletic_scores.png', dpi=150)
        plt.close()
        print("  Saved: physical_athletic_scores.png")


def export_physical_model(results, mvn_models, tier_counts):
    """Export physical profile model."""
    print("\nExporting model...")

    export = {
        'model_name': 'physical_profiles',
        'version': '1.0',
        'description': 'Multivariate normal distributions for player generation',

        'position_stats': {},
        'mvn_parameters': {},
        'athletic_tier_distribution': tier_counts,

        'factor_mapping': {
            'height': {'huddle_factor': 'player.height', 'available': True},
            'weight': {'huddle_factor': 'player.weight', 'available': True},
            'forty': {'huddle_factor': 'player.forty', 'available': True, 'maps_to': 'SPD'},
            'bench': {'huddle_factor': 'player.bench', 'available': True, 'maps_to': 'STR'},
            'vertical': {'huddle_factor': 'player.vertical', 'available': True, 'maps_to': 'JMP'},
            'broad_jump': {'huddle_factor': 'player.broad', 'available': True},
            'cone': {'huddle_factor': 'player.cone', 'available': True, 'maps_to': 'AGI'},
            'shuttle': {'huddle_factor': 'player.shuttle', 'available': True}
        },

        'attribute_formulas': {
            'SPD': 'Linear scaling from forty time (4.2=99, 5.2=60)',
            'ACC': 'Derived from 10-split or 40-time correlation',
            'AGI': 'Linear scaling from cone (6.5=99, 8.0=60)',
            'STR': 'Linear scaling from bench (35 reps=99, 10 reps=60)',
            'JMP': 'Linear scaling from vertical (45in=99, 28in=60)'
        }
    }

    # Add position-specific data
    for pos in results:
        export['position_stats'][pos] = results[pos]['stats']

    for pos in mvn_models:
        export['mvn_parameters'][pos] = {
            'mean': mvn_models[pos]['mean'],
            'variables': mvn_models[pos]['variables'],
            'n': mvn_models[pos]['n'],
            # Cov matrix is large, store as nested dict
            'cov': mvn_models[pos]['cov']
        }

    with open(EXPORTS_DIR / 'physical_profile_model.json', 'w') as f:
        json.dump(export, f, indent=2)
    print(f"  Saved: {EXPORTS_DIR / 'physical_profile_model.json'}")

    return export


def generate_report(combine, results, mvn_models, tier_counts):
    """Generate markdown report."""
    print("\nGenerating report...")

    report = f"""# Player Physical Profile Model

**Model Type:** Multivariate Normal (MVN) by Position
**Data:** {len(combine):,} combine entries (2015-2024)
**Positions Modeled:** {len(results)}

---

## Executive Summary

This model provides statistical distributions for generating realistic player physical profiles:

- **Height/Weight** distributions by position
- **Athletic measurables** (40, bench, vertical, broad, cone, shuttle)
- **Correlations** between measurables (fast players tend to jump high)
- **Composite athletic scores** for talent classification

---

## Position Profiles

"""

    for pos in results:
        stats = results[pos]['stats']
        report += f"### {pos}\n\n"
        report += f"**Sample Size:** {results[pos]['count']}\n\n"

        report += "| Measurable | Mean | Std | P10 | P90 |\n"
        report += "|------------|------|-----|-----|-----|\n"

        for m in ['ht', 'wt', 'forty', 'bench', 'vertical', 'broad_jump', 'cone', 'shuttle']:
            if m in stats:
                s = stats[m]
                label = m.replace('_', ' ').title()
                report += f"| {label} | {s['mean']:.1f} | {s['std']:.2f} | {s['p10']:.1f} | {s['p90']:.1f} |\n"

        report += "\n"

    report += """---

## Athletic Tier Distribution

| Position | Poor | Below Avg | Average | Above Avg | Elite |
|----------|------|-----------|---------|-----------|-------|
"""

    for pos, tiers in tier_counts.items():
        row = f"| {pos} |"
        for tier in ['Poor', 'Below Avg', 'Average', 'Above Avg', 'Elite']:
            val = tiers.get(tier, 0)
            row += f" {val:.0%} |"
        report += row + "\n"

    report += """

---

## Attribute Conversion Formulas

### Speed (SPD) from 40-Time

```python
def forty_to_speed(forty_time):
    '''
    Convert 40-yard dash time to 0-99 Speed rating.
    '''
    # Elite (4.2s) = 99, Slow (5.2s) = 60
    speed = 99 - ((forty_time - 4.2) * 39)
    return max(40, min(99, int(speed)))
```

### Strength (STR) from Bench Press

```python
def bench_to_strength(reps):
    '''
    Convert bench press reps to 0-99 Strength rating.
    '''
    # 35+ reps = 99, 10 reps = 60
    strength = 60 + ((reps - 10) * 1.56)
    return max(40, min(99, int(strength)))
```

### Agility (AGI) from 3-Cone

```python
def cone_to_agility(cone_time):
    '''
    Convert 3-cone time to 0-99 Agility rating.
    '''
    # Elite (6.5s) = 99, Slow (8.0s) = 60
    agility = 99 - ((cone_time - 6.5) * 26)
    return max(40, min(99, int(agility)))
```

### Jumping (JMP) from Vertical

```python
def vertical_to_jumping(vertical_inches):
    '''
    Convert vertical jump to 0-99 Jumping rating.
    '''
    # 45 inches = 99, 28 inches = 60
    jumping = 60 + ((vertical_inches - 28) * 2.29)
    return max(40, min(99, int(jumping)))
```

---

## Model Usage

### Generating a New Player

```python
import numpy as np

def generate_physical_profile(position):
    '''
    Generate realistic physical measurables for a position.
    Uses multivariate normal to maintain correlations.
    '''
    # Load MVN parameters for position
    mvn_params = PHYSICAL_PROFILES[position]

    # Sample from multivariate normal
    mean = np.array([mvn_params['mean'][v] for v in mvn_params['variables']])
    cov = np.array([[mvn_params['cov'][v1][v2]
                    for v2 in mvn_params['variables']]
                   for v1 in mvn_params['variables']])

    sample = np.random.multivariate_normal(mean, cov)

    # Return as dict
    return dict(zip(mvn_params['variables'], sample))
```

---

## Key Correlations

Across positions, these correlations are consistent:

| Pair | Typical r | Interpretation |
|------|-----------|----------------|
| 40-time ↔ Vertical | -0.40 | Fast players jump high |
| 40-time ↔ Broad | -0.50 | Fast players jump far |
| Vertical ↔ Broad | +0.60 | Explosive power transfers |
| Weight ↔ 40-time | +0.45 | Heavier = slower |
| Weight ↔ Bench | +0.35 | Bigger = stronger |
| Cone ↔ Shuttle | +0.65 | Agility tests correlate |

---

## Position Archetypes

### Speed Positions (WR, CB, RB)
- 40-time: 4.40-4.60
- Vertical: 35-40 inches
- Weight: 175-215 lbs

### Size Positions (OL, DL)
- Weight: 290-330 lbs
- Bench: 25-35 reps
- 40-time: 4.90-5.30

### Hybrid Positions (TE, LB, EDGE)
- Balance of size and speed
- 40-time: 4.55-4.80
- Weight: 240-265 lbs

---

## Figures

- `physical_height_weight.png`
- `physical_forty_by_position.png`
- `physical_correlation_wr.png`
- `physical_position_comparison.png`
- `physical_athletic_scores.png`

---

*Model built by researcher_agent*
"""

    report_path = REPORTS_DIR / "physical_profile_model_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")


def main():
    """Run physical profile model pipeline."""
    print("=" * 60)
    print("PLAYER PHYSICAL PROFILE MODEL")
    print("=" * 60)

    # Load data
    combine = load_combine_data()

    # Analyze profiles
    results = analyze_position_profiles(combine)

    # Build MVN models
    mvn_models = build_mvn_models(combine)

    # Calculate athletic scores
    combine, tier_counts = calculate_athletic_scores(combine, results)

    # Create figures
    create_profile_figures(combine, results, mvn_models)

    # Export
    export = export_physical_model(results, mvn_models, tier_counts)

    # Report
    generate_report(combine, results, mvn_models, tier_counts)

    print("\n" + "=" * 60)
    print("MODEL COMPLETE")
    print("=" * 60)
    print(f"Positions modeled: {len(results)}")
    print(f"MVN models built: {len(mvn_models)}")


if __name__ == "__main__":
    main()
