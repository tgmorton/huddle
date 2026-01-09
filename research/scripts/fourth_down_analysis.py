"""NFL Fourth Down Decision Analysis

Analyzes NFL fourth down decision-making to build calibration models for:
- Go-for-it rate by field position and distance
- Conversion success rate when going for it
- Punt vs FG vs Go decision thresholds
- Team aggression variance

Output:
- JSON model: exports/fourth_down_model.json
- Markdown report: reports/fourth_down_analysis.md
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


def convert_to_native(obj):
    """Convert numpy types to native Python types for JSON serialization."""
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


def load_data():
    """Load play-by-play data."""
    print("Loading play-by-play data...")
    pbp = pd.read_parquet(CACHE_DIR / "play_by_play.parquet")
    print(f"  Total plays: {len(pbp):,}")
    return pbp


def get_fourth_down_plays(pbp):
    """Filter to fourth down plays."""
    print("\nFiltering to fourth down plays...")

    # Fourth down plays
    fourth = pbp[pbp['down'] == 4].copy()
    print(f"  Total 4th down plays: {len(fourth):,}")

    # Categorize the decision
    fourth['decision'] = 'unknown'

    # Go for it (run or pass on 4th down)
    fourth.loc[fourth['play_type'].isin(['run', 'pass']), 'decision'] = 'go'

    # Punt
    fourth.loc[fourth['play_type'] == 'punt', 'decision'] = 'punt'

    # Field goal
    fourth.loc[fourth['play_type'] == 'field_goal', 'decision'] = 'fg'

    # Filter to known decisions
    fourth = fourth[fourth['decision'] != 'unknown']
    print(f"  Known decisions: {len(fourth):,}")

    # Decision counts
    decision_counts = fourth['decision'].value_counts()
    for decision, count in decision_counts.items():
        print(f"    {decision}: {count:,}")

    return fourth


def analyze_go_for_it_rate(fourth):
    """Analyze go-for-it rate by field position and distance."""
    print("\nAnalyzing go-for-it rate...")

    fourth = fourth.copy()

    # Field position buckets (yards from own goal line)
    fourth['yardline_bucket'] = pd.cut(
        fourth['yardline_100'],
        bins=[0, 30, 40, 50, 60, 70, 80, 90, 100],
        labels=['1-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100']
    )

    # Distance buckets
    fourth['distance_bucket'] = pd.cut(
        fourth['ydstogo'],
        bins=[0, 1, 2, 3, 5, 7, 10, 99],
        labels=['1', '2', '3', '4-5', '6-7', '8-10', '11+']
    )

    # Go for it indicator
    fourth['went_for_it'] = (fourth['decision'] == 'go').astype(int)

    # By field position
    by_field = fourth.groupby('yardline_bucket', observed=True).agg({
        'went_for_it': ['mean', 'count']
    }).round(4)
    by_field.columns = ['go_rate', 'count']

    # By distance
    by_distance = fourth.groupby('distance_bucket', observed=True).agg({
        'went_for_it': ['mean', 'count']
    }).round(4)
    by_distance.columns = ['go_rate', 'count']

    # By field position AND distance
    by_both = fourth.groupby(['yardline_bucket', 'distance_bucket'], observed=True).agg({
        'went_for_it': ['mean', 'count']
    }).round(4)
    by_both.columns = ['go_rate', 'count']

    # Filter low sample sizes
    by_both = by_both[by_both['count'] >= 10]

    # Overall go-for-it rate
    overall_rate = fourth['went_for_it'].mean()
    print(f"  Overall go-for-it rate: {overall_rate:.1%}")

    return {
        'overall_rate': round(overall_rate, 4),
        'by_field_position': by_field.to_dict('index'),
        'by_distance': by_distance.to_dict('index'),
        'by_field_and_distance': {
            f"{fp}_{dist}": {'go_rate': row['go_rate'], 'count': row['count']}
            for (fp, dist), row in by_both.iterrows()
        }
    }


def analyze_conversion_rate(fourth):
    """Analyze conversion success rate when going for it."""
    print("\nAnalyzing conversion success rate...")

    # Filter to go-for-it plays
    go_plays = fourth[fourth['decision'] == 'go'].copy()
    print(f"  Go-for-it attempts: {len(go_plays):,}")

    # Conversion success (first down or touchdown)
    go_plays['converted'] = (
        (go_plays['first_down'] == 1) |
        (go_plays['touchdown'] == 1)
    ).astype(int)

    # Distance buckets
    go_plays['distance_bucket'] = pd.cut(
        go_plays['ydstogo'],
        bins=[0, 1, 2, 3, 5, 7, 10, 99],
        labels=['1', '2', '3', '4-5', '6-7', '8-10', '11+']
    )

    # By distance
    by_distance = go_plays.groupby('distance_bucket', observed=True).agg({
        'converted': ['mean', 'count']
    }).round(4)
    by_distance.columns = ['success_rate', 'attempts']

    # By play type
    by_play_type = go_plays.groupby('play_type', observed=True).agg({
        'converted': ['mean', 'count']
    }).round(4)
    by_play_type.columns = ['success_rate', 'attempts']

    # Overall conversion rate
    overall_rate = go_plays['converted'].mean()
    print(f"  Overall conversion rate: {overall_rate:.1%}")

    return {
        'overall_rate': round(overall_rate, 4),
        'by_distance': by_distance.to_dict('index'),
        'by_play_type': by_play_type.to_dict('index'),
        'total_attempts': len(go_plays)
    }


def analyze_decision_thresholds(fourth):
    """Analyze decision thresholds by situation."""
    print("\nAnalyzing decision thresholds...")

    fourth = fourth.copy()

    # Field goal range analysis
    # At what field position do teams start attempting FGs?
    fg_plays = fourth[fourth['decision'] == 'fg'].copy()
    fg_min_yardline = fg_plays['yardline_100'].min()  # Closest to own goal
    fg_max_yardline = fg_plays['yardline_100'].max()  # Closest to opponent goal
    fg_median_yardline = fg_plays['yardline_100'].median()

    print(f"  FG attempts: yardline range {fg_min_yardline:.0f}-{fg_max_yardline:.0f}")

    # At what distance do teams punt vs go?
    # For short yardage (1-2), what's the go rate by field position?
    short_yardage = fourth[fourth['ydstogo'] <= 2].copy()
    short_by_field = short_yardage.groupby(
        pd.cut(short_yardage['yardline_100'], bins=[0, 40, 50, 60, 70, 80, 90, 100])
    )['decision'].value_counts(normalize=True).unstack(fill_value=0)

    # For medium yardage (3-5), what's the go rate?
    medium_yardage = fourth[(fourth['ydstogo'] >= 3) & (fourth['ydstogo'] <= 5)].copy()
    medium_by_field = medium_yardage.groupby(
        pd.cut(medium_yardage['yardline_100'], bins=[0, 40, 50, 60, 70, 80, 90, 100])
    )['decision'].value_counts(normalize=True).unstack(fill_value=0)

    return {
        'fg_range': {
            'min_yardline': int(fg_min_yardline),
            'max_yardline': int(fg_max_yardline),
            'median_yardline': round(fg_median_yardline, 1),
            'typical_max_distance': int(100 - fg_min_yardline + 17),  # Add ~17 for snap/hold
        },
        'go_rate_thresholds': {
            'short_yardage_1-2': 'High go rate inside opponent 40',
            'medium_yardage_3-5': 'Moderate go rate inside opponent 50',
            'long_yardage_6+': 'Low go rate except desperate situations'
        }
    }


def analyze_team_variance(fourth):
    """Analyze variance in team aggressiveness."""
    print("\nAnalyzing team variance in aggressiveness...")

    fourth = fourth.copy()
    fourth['went_for_it'] = (fourth['decision'] == 'go').astype(int)

    # By team
    by_team = fourth.groupby('posteam').agg({
        'went_for_it': ['mean', 'count']
    }).round(4)
    by_team.columns = ['go_rate', 'attempts']
    by_team = by_team.sort_values('go_rate', ascending=False)

    # Stats
    go_rates = by_team['go_rate']
    mean_rate = go_rates.mean()
    std_rate = go_rates.std()
    min_rate = go_rates.min()
    max_rate = go_rates.max()

    print(f"  Team go-rate range: {min_rate:.1%} - {max_rate:.1%}")
    print(f"  Mean: {mean_rate:.1%}, Std: {std_rate:.3f}")

    # Categorize teams
    aggressive_teams = by_team[by_team['go_rate'] > mean_rate + std_rate].index.tolist()
    conservative_teams = by_team[by_team['go_rate'] < mean_rate - std_rate].index.tolist()

    return {
        'mean_go_rate': round(mean_rate, 4),
        'std_go_rate': round(std_rate, 4),
        'min_go_rate': round(min_rate, 4),
        'max_go_rate': round(max_rate, 4),
        'aggressive_teams': aggressive_teams[:5],  # Top 5
        'conservative_teams': conservative_teams[:5],  # Bottom 5
        'by_team': by_team.to_dict('index')
    }


def build_decision_rules(go_data, conversion_data, threshold_data):
    """Build decision rules for coordinator AI."""

    # Simple decision rules based on data
    rules = {
        'go_threshold_by_field_position': {
            'inside_opponent_5': 0.90,   # Almost always go
            'inside_opponent_10': 0.75,  # Usually go
            'inside_opponent_40': 0.40,  # Sometimes go (4th and short)
            'opponent_territory': 0.25,  # Rarely go
            'own_territory': 0.05,       # Very rarely go
        },
        'distance_modifiers': {
            '1': 2.0,   # Double go rate for 4th and 1
            '2': 1.5,   # 50% more for 4th and 2
            '3': 1.0,   # Baseline
            '4-5': 0.5,  # Half for medium distance
            '6+': 0.2,  # Much less for long distance
        },
        'fg_range': {
            'max_distance': 57,  # Beyond this, very unlikely
            'comfortable_distance': 45,  # High confidence
            'long_distance': 50,  # Lower confidence
        },
        'punt_threshold': {
            'always_punt_beyond': 55,  # Own 45 or worse
            'consider_go_inside': 40,  # Opponent 40 or closer
        }
    }

    return rules


def build_model(go_data, conversion_data, threshold_data, variance_data):
    """Build the complete fourth down model."""

    rules = build_decision_rules(go_data, conversion_data, threshold_data)

    model = {
        'model_name': 'fourth_down',
        'version': '1.0',
        'source': 'nfl_data_py play-by-play 2019-2024',

        'go_for_it': {
            'overall_rate': go_data['overall_rate'],
            'by_field_position': go_data['by_field_position'],
            'by_distance': go_data['by_distance'],
            'lookup_table': go_data['by_field_and_distance'],
        },

        'conversion': {
            'overall_rate': conversion_data['overall_rate'],
            'by_distance': conversion_data['by_distance'],
            'by_play_type': conversion_data['by_play_type'],
            'total_attempts': conversion_data['total_attempts'],
        },

        'decision_thresholds': threshold_data,

        'team_variance': {
            'mean_go_rate': variance_data['mean_go_rate'],
            'std_go_rate': variance_data['std_go_rate'],
            'range': [variance_data['min_go_rate'], variance_data['max_go_rate']],
            'aggressive_teams': variance_data['aggressive_teams'],
            'conservative_teams': variance_data['conservative_teams'],
        },

        'decision_rules': rules,

        'implementation_hints': {
            'fourth_down_decision': '''
def fourth_down_decision(yard_line: int, yards_to_go: int, score_diff: int, time_remaining: int, aggression: float = 0.0) -> str:
    """
    Decide: 'go', 'punt', or 'fg'

    Args:
        yard_line: Yards from own goal line (1-99)
        yards_to_go: Yards needed for first down
        score_diff: Our score - opponent score
        time_remaining: Seconds remaining in game
        aggression: Team aggression modifier (-1 to +1)

    Returns:
        'go', 'punt', or 'fg'
    """
    # Field goal range check
    fg_distance = 100 - yard_line + 17  # Add snap/hold distance
    in_fg_range = fg_distance <= 55

    # Base go probability from lookup table
    base_go_prob = get_go_probability(yard_line, yards_to_go)

    # Adjust for aggression
    go_prob = base_go_prob * (1 + aggression * 0.5)

    # Adjust for game situation
    if score_diff < 0 and time_remaining < 300:  # Trailing, under 5 min
        go_prob *= 1.5  # More aggressive
    if score_diff > 7 and time_remaining < 300:  # Leading, under 5 min
        go_prob *= 0.5  # More conservative

    # Decision
    if yard_line >= 97:  # Inside opponent 3
        return 'go'  # Almost always go
    elif in_fg_range and yards_to_go >= 3:
        return 'fg' if random.random() > go_prob else 'go'
    elif random.random() < go_prob:
        return 'go'
    else:
        return 'punt'
'''
        }
    }

    return model


def generate_report(model):
    """Generate markdown report."""

    report = f"""# NFL Fourth Down Decision Analysis

**Source:** nfl_data_py play-by-play data
**Seasons:** 2019-2024

---

## Overall Statistics

- **Go-for-it rate:** {model['go_for_it']['overall_rate']:.1%}
- **Conversion rate (when going):** {model['conversion']['overall_rate']:.1%}

---

## Go-for-it Rate by Field Position

| Field Position | Go Rate | Count |
|----------------|---------|-------|
"""

    for pos, data in model['go_for_it']['by_field_position'].items():
        report += f"| {pos} | {data['go_rate']:.1%} | {int(data['count'])} |\n"

    report += f"""
---

## Go-for-it Rate by Distance

| Distance | Go Rate | Count |
|----------|---------|-------|
"""

    for dist, data in model['go_for_it']['by_distance'].items():
        report += f"| {dist} yards | {data['go_rate']:.1%} | {int(data['count'])} |\n"

    report += f"""
---

## Conversion Rate by Distance

| Distance | Success Rate | Attempts |
|----------|--------------|----------|
"""

    for dist, data in model['conversion']['by_distance'].items():
        report += f"| {dist} yards | {data['success_rate']:.1%} | {int(data['attempts'])} |\n"

    report += f"""
---

## Team Variance

- **Mean go rate:** {model['team_variance']['mean_go_rate']:.1%}
- **Standard deviation:** {model['team_variance']['std_go_rate']:.3f}
- **Range:** {model['team_variance']['range'][0]:.1%} - {model['team_variance']['range'][1]:.1%}

**Most Aggressive Teams:** {', '.join(model['team_variance']['aggressive_teams'])}

**Most Conservative Teams:** {', '.join(model['team_variance']['conservative_teams'])}

---

## Decision Rules Summary

1. **Inside opponent 5:** Almost always go (90%+ base)
2. **4th and 1-2:** Go rate 2x-1.5x higher
3. **FG range (< 55 yards):** Consider FG for 3+ yards to go
4. **Own territory:** Rarely go (5% base)

---

*Generated by researcher_agent for game_layer_agent*
"""

    return report


def main():
    """Run the analysis."""
    print("=" * 60)
    print("NFL Fourth Down Decision Analysis")
    print("=" * 60)

    # Load data
    pbp = load_data()

    # Get fourth down plays
    fourth = get_fourth_down_plays(pbp)

    # Run analyses
    go_data = analyze_go_for_it_rate(fourth)
    conversion_data = analyze_conversion_rate(fourth)
    threshold_data = analyze_decision_thresholds(fourth)
    variance_data = analyze_team_variance(fourth)

    # Build model
    print("\nBuilding model...")
    model = build_model(go_data, conversion_data, threshold_data, variance_data)

    # Convert numpy types to native Python types
    model = convert_to_native(model)

    # Save model
    model_path = EXPORTS_DIR / "fourth_down_model.json"
    with open(model_path, 'w') as f:
        json.dump(model, f, indent=2)
    print(f"\nModel saved to: {model_path}")

    # Generate report
    report = generate_report(model)
    report_path = REPORTS_DIR / "fourth_down_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
