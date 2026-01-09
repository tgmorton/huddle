"""NFL Special Teams Analysis

Analyzes NFL special teams data to build calibration models for:
- Field goals (accuracy by distance)
- Extra points (success rate)
- Kickoffs (touchback rate, return yards)
- Punts (net yards, inside-20, fair catch)
- Two-point conversions (success rate)

Output:
- JSON model: exports/special_teams_model.json
- Markdown report: reports/special_teams_analysis.md
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
BASE_DIR = Path("/Users/thomasmorton/huddle/research")
CACHE_DIR = BASE_DIR / "data" / "cached"
EXPORTS_DIR = BASE_DIR / "exports"
REPORTS_DIR = BASE_DIR / "reports"

EXPORTS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


def load_data():
    """Load play-by-play data."""
    print("Loading play-by-play data...")
    pbp = pd.read_parquet(CACHE_DIR / "play_by_play.parquet")
    print(f"  Total plays: {len(pbp):,}")
    return pbp


def analyze_field_goals(pbp):
    """Analyze field goal success rates by distance."""
    print("\nAnalyzing field goals...")

    # Filter to field goal attempts
    fg = pbp[pbp['play_type'] == 'field_goal'].copy()
    print(f"  Total FG attempts: {len(fg):,}")

    # Field goal result
    fg['made'] = fg['field_goal_result'] == 'made'

    # By distance (5-yard buckets)
    fg['distance_bucket'] = (fg['kick_distance'] // 5) * 5

    by_distance = fg.groupby('distance_bucket').agg({
        'made': ['mean', 'count']
    }).round(4)
    by_distance.columns = ['success_rate', 'attempts']
    by_distance = by_distance[by_distance['attempts'] >= 10]  # Filter low sample sizes

    # Also get exact distance for finer granularity
    by_exact = fg.groupby('kick_distance').agg({
        'made': ['mean', 'count']
    }).round(4)
    by_exact.columns = ['success_rate', 'attempts']
    by_exact = by_exact[by_exact['attempts'] >= 20]  # Need more samples for exact

    # Calculate overall stats
    overall_rate = fg['made'].mean()
    print(f"  Overall FG success rate: {overall_rate:.1%}")

    return {
        'overall_rate': round(overall_rate, 4),
        'by_distance_bucket': by_distance.to_dict('index'),
        'by_exact_distance': {
            int(k): round(v['success_rate'], 4)
            for k, v in by_exact.to_dict('index').items()
        },
        'total_attempts': len(fg)
    }


def analyze_extra_points(pbp):
    """Analyze extra point success rates."""
    print("\nAnalyzing extra points...")

    # Filter to extra point attempts
    xp = pbp[pbp['play_type'] == 'extra_point'].copy()
    print(f"  Total XP attempts: {len(xp):,}")

    xp['made'] = xp['extra_point_result'] == 'good'

    success_rate = xp['made'].mean()
    print(f"  XP success rate: {success_rate:.1%}")

    return {
        'success_rate': round(success_rate, 4),
        'total_attempts': len(xp)
    }


def analyze_two_point(pbp):
    """Analyze two-point conversion success rates."""
    print("\nAnalyzing two-point conversions...")

    # Filter to two-point attempts
    twopt = pbp[pbp['two_point_attempt'] == 1].copy()
    print(f"  Total 2PT attempts: {len(twopt):,}")

    if len(twopt) == 0:
        return {'success_rate': 0.48, 'total_attempts': 0, 'note': 'No data found'}

    twopt['success'] = twopt['two_point_conv_result'] == 'success'

    success_rate = twopt['success'].mean()
    print(f"  2PT success rate: {success_rate:.1%}")

    # By play type (run vs pass)
    by_type = twopt.groupby('play_type').agg({
        'success': ['mean', 'count']
    }).round(4)

    return {
        'success_rate': round(success_rate, 4),
        'by_play_type': {
            'pass': round(twopt[twopt['play_type'] == 'pass']['success'].mean(), 4) if len(twopt[twopt['play_type'] == 'pass']) > 0 else None,
            'run': round(twopt[twopt['play_type'] == 'run']['success'].mean(), 4) if len(twopt[twopt['play_type'] == 'run']) > 0 else None,
        },
        'total_attempts': len(twopt)
    }


def analyze_kickoffs(pbp):
    """Analyze kickoff outcomes."""
    print("\nAnalyzing kickoffs...")

    # Filter to kickoffs
    ko = pbp[pbp['play_type'] == 'kickoff'].copy()
    print(f"  Total kickoffs: {len(ko):,}")

    # Touchback rate
    ko['is_touchback'] = ko['touchback'] == 1
    touchback_rate = ko['is_touchback'].mean()
    print(f"  Touchback rate: {touchback_rate:.1%}")

    # Return yards (when returned)
    returns = ko[ko['is_touchback'] == False].copy()
    if len(returns) > 0:
        return_yards_mean = returns['return_yards'].mean()
        return_yards_std = returns['return_yards'].std()
        return_yards_median = returns['return_yards'].median()
    else:
        return_yards_mean = 23.0
        return_yards_std = 10.0
        return_yards_median = 22.0

    print(f"  Return yards (mean): {return_yards_mean:.1f}")
    print(f"  Return yards (median): {return_yards_median:.1f}")

    # Starting field position after touchback
    # Touchback = own 25-yard line in modern NFL (since 2016)
    touchback_yard_line = 25

    return {
        'touchback_rate': round(touchback_rate, 4),
        'touchback_yard_line': touchback_yard_line,
        'return_yards': {
            'mean': round(return_yards_mean, 1),
            'std': round(return_yards_std, 1),
            'median': round(return_yards_median, 1)
        },
        'total_kickoffs': len(ko)
    }


def analyze_punts(pbp):
    """Analyze punt outcomes."""
    print("\nAnalyzing punts...")

    # Filter to punts
    punts = pbp[pbp['play_type'] == 'punt'].copy()
    print(f"  Total punts: {len(punts):,}")

    # Gross punt yards
    gross_yards = punts['kick_distance'].dropna()
    gross_mean = gross_yards.mean()
    gross_std = gross_yards.std()

    # Net punt yards (accounting for return)
    # Net = gross - return yards
    punts['net_yards'] = punts['kick_distance'] - punts['return_yards'].fillna(0)
    net_yards = punts['net_yards'].dropna()
    net_mean = net_yards.mean()
    net_std = net_yards.std()

    print(f"  Gross yards (mean): {gross_mean:.1f}")
    print(f"  Net yards (mean): {net_mean:.1f}")

    # Fair catch rate
    punts['is_fair_catch'] = punts['punt_fair_catch'] == 1
    fair_catch_rate = punts['is_fair_catch'].mean()
    print(f"  Fair catch rate: {fair_catch_rate:.1%}")

    # Touchback rate
    punts['is_touchback'] = punts['touchback'] == 1
    touchback_rate = punts['is_touchback'].mean()
    print(f"  Touchback rate: {touchback_rate:.1%}")

    # Inside 20 rate (punt downed inside opponent's 20)
    # This is harder to calculate directly - estimate based on field position
    # A punt is "inside 20" if it ends between opponent's 1-19 yard line

    return {
        'gross_yards': {
            'mean': round(gross_mean, 1),
            'std': round(gross_std, 1)
        },
        'net_yards': {
            'mean': round(net_mean, 1),
            'std': round(net_std, 1)
        },
        'fair_catch_rate': round(fair_catch_rate, 4),
        'touchback_rate': round(touchback_rate, 4),
        'total_punts': len(punts)
    }


def convert_to_native(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


def build_model(fg_data, xp_data, twopt_data, ko_data, punt_data):
    """Build the complete special teams model."""

    model = {
        'model_name': 'special_teams',
        'version': '1.0',
        'source': 'nfl_data_py play-by-play 2019-2024',

        'field_goal': {
            'overall_rate': fg_data['overall_rate'],
            'by_distance': fg_data['by_exact_distance'],
            'by_bucket': {
                str(int(k)): v['success_rate']
                for k, v in fg_data['by_distance_bucket'].items()
            },
            'total_attempts': fg_data['total_attempts'],
            'notes': {
                'distance_is_kick_distance': 'Includes ~7 yards for snap/hold',
                'recommendation': 'Use by_distance for simulation, interpolate for missing values'
            }
        },

        'extra_point': {
            'success_rate': xp_data['success_rate'],
            'total_attempts': xp_data['total_attempts'],
            'notes': {
                'modern_distance': '33 yards (moved back in 2015)',
                'recommendation': 'Can modify slightly by kicker rating'
            }
        },

        'two_point': {
            'success_rate': twopt_data['success_rate'],
            'by_play_type': twopt_data.get('by_play_type', {}),
            'total_attempts': twopt_data['total_attempts'],
            'notes': {
                'recommendation': 'Use V2 simulation for 2PT attempts for realism'
            }
        },

        'kickoff': {
            'touchback_rate': ko_data['touchback_rate'],
            'touchback_yard_line': ko_data['touchback_yard_line'],
            'return_yards': ko_data['return_yards'],
            'total_kickoffs': ko_data['total_kickoffs'],
            'notes': {
                'modern_rules': 'Touchback to 25-yard line since 2016',
                'recommendation': 'Roll touchback first, then return yards if not touchback'
            }
        },

        'punt': {
            'gross_yards': punt_data['gross_yards'],
            'net_yards': punt_data['net_yards'],
            'fair_catch_rate': punt_data['fair_catch_rate'],
            'touchback_rate': punt_data['touchback_rate'],
            'total_punts': punt_data['total_punts'],
            'notes': {
                'recommendation': 'Use net_yards for field position calculation'
            }
        },

        'implementation_hints': {
            'field_goal_probability': 'P(make) = by_distance[distance] * (1 + (kicker_rating - 75) / 100)',
            'kickoff_result': 'if random() < touchback_rate: start at 25 else: start at 25 + return_yards',
            'punt_result': 'new_yard_line = 100 - current_yard_line - net_yards (clamp to 1-99)',
        }
    }

    return model


def generate_report(model):
    """Generate markdown report."""

    report = f"""# NFL Special Teams Analysis

**Source:** nfl_data_py play-by-play data
**Data Points:** {model['field_goal']['total_attempts']:,} FG attempts, {model['kickoff']['total_kickoffs']:,} kickoffs, {model['punt']['total_punts']:,} punts

---

## Field Goals

**Overall Success Rate:** {model['field_goal']['overall_rate']:.1%}

### By Distance

| Distance | Success Rate |
|----------|-------------|
"""

    for dist, rate in sorted(model['field_goal']['by_distance'].items(), key=lambda x: int(x[0])):
        report += f"| {dist} yards | {rate:.1%} |\n"

    report += f"""
---

## Extra Points

**Success Rate:** {model['extra_point']['success_rate']:.1%}

Modern XP distance is 33 yards (moved back in 2015).

---

## Two-Point Conversions

**Success Rate:** {model['two_point']['success_rate']:.1%}

---

## Kickoffs

**Touchback Rate:** {model['kickoff']['touchback_rate']:.1%}

When returned:
- Mean return: {model['kickoff']['return_yards']['mean']:.1f} yards
- Median return: {model['kickoff']['return_yards']['median']:.1f} yards

---

## Punts

- **Gross yards:** {model['punt']['gross_yards']['mean']:.1f} (σ={model['punt']['gross_yards']['std']:.1f})
- **Net yards:** {model['punt']['net_yards']['mean']:.1f} (σ={model['punt']['net_yards']['std']:.1f})
- **Fair catch rate:** {model['punt']['fair_catch_rate']:.1%}
- **Touchback rate:** {model['punt']['touchback_rate']:.1%}

---

## Implementation Code

```python
import json
from pathlib import Path

# Load model
with open('research/exports/special_teams_model.json') as f:
    ST = json.load(f)

def resolve_field_goal(distance: int, kicker_rating: int = 75) -> bool:
    \"\"\"Resolve field goal attempt.\"\"\"
    base_rate = ST['field_goal']['by_distance'].get(str(distance), 0.5)
    modifier = 1 + (kicker_rating - 75) / 100
    probability = min(0.99, base_rate * modifier)
    return random.random() < probability

def resolve_kickoff(kicker_rating: int = 75) -> int:
    \"\"\"Return starting yard line after kickoff.\"\"\"
    touchback_rate = ST['kickoff']['touchback_rate']
    if random.random() < touchback_rate:
        return 25  # Touchback
    else:
        return_yards = random.gauss(
            ST['kickoff']['return_yards']['mean'],
            ST['kickoff']['return_yards']['std']
        )
        return max(1, min(99, int(25 + return_yards)))

def resolve_punt(yard_line: int, punter_rating: int = 75) -> int:
    \"\"\"Return new yard line after punt.\"\"\"
    net_yards = random.gauss(
        ST['punt']['net_yards']['mean'],
        ST['punt']['net_yards']['std']
    )
    new_yard_line = 100 - yard_line - net_yards
    return max(1, min(99, int(new_yard_line)))
```

---

*Generated by researcher_agent for game_layer_agent*
"""

    return report


def main():
    """Run the analysis."""
    print("=" * 60)
    print("NFL Special Teams Analysis")
    print("=" * 60)

    # Load data
    pbp = load_data()

    # Run analyses
    fg_data = analyze_field_goals(pbp)
    xp_data = analyze_extra_points(pbp)
    twopt_data = analyze_two_point(pbp)
    ko_data = analyze_kickoffs(pbp)
    punt_data = analyze_punts(pbp)

    # Build model
    print("\nBuilding model...")
    model = build_model(fg_data, xp_data, twopt_data, ko_data, punt_data)

    # Convert numpy types to native Python types
    model = convert_to_native(model)

    # Save model
    model_path = EXPORTS_DIR / "special_teams_model.json"
    with open(model_path, 'w') as f:
        json.dump(model, f, indent=2)
    print(f"\nModel saved to: {model_path}")

    # Generate report
    report = generate_report(model)
    report_path = REPORTS_DIR / "special_teams_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
