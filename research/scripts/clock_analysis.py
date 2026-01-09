"""
Clock Management Analysis for Game Layer Agent

Analyzes NFL play-by-play data to understand:
- Time elapsed per play by type
- Hurry-up vs normal pace
- End of half/game timing
- Clock management patterns

Data source: nfl_data_py (nflfastR play-by-play)
"""

import json
import nfl_data_py as nfl
import pandas as pd
import numpy as np
from pathlib import Path


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


def analyze_clock():
    """Analyze clock management patterns from NFL data."""

    print("Loading play-by-play data (2019-2024)...")
    pbp = nfl.import_pbp_data(years=range(2019, 2025))

    # Filter to scrimmage plays
    scrimmage = pbp[pbp['play_type'].isin(['pass', 'run'])].copy()

    print(f"Analyzing {len(scrimmage):,} scrimmage plays...")

    results = {
        "model_name": "clock_management",
        "version": "1.0",
        "source": "nfl_data_py play-by-play 2019-2024"
    }

    # === TIME BETWEEN PLAYS ===
    print("\nAnalyzing time between plays...")

    # Sort by game and play order
    scrimmage = scrimmage.sort_values(['game_id', 'play_id'])

    # Calculate time elapsed between consecutive plays within same drive
    scrimmage['time_elapsed'] = scrimmage.groupby(['game_id', 'drive'])['game_seconds_remaining'].diff(-1)

    # Filter valid time elapsed (positive, less than 2 minutes to remove quarter breaks)
    valid_time = scrimmage[
        (scrimmage['time_elapsed'] > 0) &
        (scrimmage['time_elapsed'] < 120)
    ].copy()

    results["time_between_plays"] = {
        "overall": {
            "mean": round(valid_time['time_elapsed'].mean(), 1),
            "median": round(valid_time['time_elapsed'].median(), 1),
            "std": round(valid_time['time_elapsed'].std(), 1),
            "percentiles": {
                "p10": round(valid_time['time_elapsed'].quantile(0.10), 1),
                "p25": round(valid_time['time_elapsed'].quantile(0.25), 1),
                "p75": round(valid_time['time_elapsed'].quantile(0.75), 1),
                "p90": round(valid_time['time_elapsed'].quantile(0.90), 1)
            }
        }
    }

    # === BY PLAY TYPE ===
    print("Analyzing by play type...")

    results["time_between_plays"]["by_play_type"] = {}

    for play_type in ['pass', 'run']:
        type_plays = valid_time[valid_time['play_type'] == play_type]
        if len(type_plays) > 100:
            results["time_between_plays"]["by_play_type"][play_type] = {
                "mean": round(type_plays['time_elapsed'].mean(), 1),
                "median": round(type_plays['time_elapsed'].median(), 1),
                "std": round(type_plays['time_elapsed'].std(), 1)
            }

    # === BY PLAY RESULT ===
    print("Analyzing by play result...")

    results["time_between_plays"]["by_result"] = {}

    # Complete pass
    complete = valid_time[(valid_time['play_type'] == 'pass') & (valid_time['complete_pass'] == 1)]
    if len(complete) > 100:
        results["time_between_plays"]["by_result"]["complete_pass"] = {
            "mean": round(complete['time_elapsed'].mean(), 1),
            "median": round(complete['time_elapsed'].median(), 1),
            "note": "Clock runs, normal pace"
        }

    # Incomplete pass
    incomplete = valid_time[(valid_time['play_type'] == 'pass') & (valid_time['incomplete_pass'] == 1)]
    if len(incomplete) > 100:
        results["time_between_plays"]["by_result"]["incomplete_pass"] = {
            "mean": round(incomplete['time_elapsed'].mean(), 1),
            "median": round(incomplete['time_elapsed'].median(), 1),
            "note": "Clock stops, faster next snap"
        }

    # First down
    first_down = valid_time[valid_time['first_down'] == 1]
    if len(first_down) > 100:
        results["time_between_plays"]["by_result"]["first_down"] = {
            "mean": round(first_down['time_elapsed'].mean(), 1),
            "median": round(first_down['time_elapsed'].median(), 1),
            "note": "Clock stops briefly for chains"
        }

    # Out of bounds (approximation via sack/scramble)
    # This is harder to detect directly, skip for now

    # === HURRY-UP ANALYSIS ===
    print("Analyzing hurry-up situations...")

    # Two-minute drill: under 2 minutes in 2nd or 4th quarter
    two_min = valid_time[
        ((valid_time['qtr'] == 2) | (valid_time['qtr'] == 4)) &
        (valid_time['half_seconds_remaining'] <= 120)
    ]

    # Normal pace: 1st/3rd quarter or early in 2nd/4th
    normal = valid_time[
        ((valid_time['qtr'] == 1) | (valid_time['qtr'] == 3)) |
        (valid_time['half_seconds_remaining'] > 300)
    ]

    results["pace"] = {
        "hurry_up": {
            "mean": round(two_min['time_elapsed'].mean(), 1),
            "median": round(two_min['time_elapsed'].median(), 1),
            "sample_size": len(two_min),
            "description": "Under 2 min in 2nd/4th quarter"
        },
        "normal": {
            "mean": round(normal['time_elapsed'].mean(), 1),
            "median": round(normal['time_elapsed'].median(), 1),
            "sample_size": len(normal),
            "description": "1st/3rd quarter or early 2nd/4th"
        }
    }

    # === BY SCORE DIFFERENTIAL ===
    print("Analyzing by score differential...")

    valid_time['abs_score_diff'] = abs(valid_time['score_differential'])

    results["by_score_differential"] = {}

    # Close game (within 8)
    close = valid_time[valid_time['abs_score_diff'] <= 8]
    if len(close) > 100:
        results["by_score_differential"]["close_game"] = {
            "range": "within 8 points",
            "mean": round(close['time_elapsed'].mean(), 1),
            "median": round(close['time_elapsed'].median(), 1)
        }

    # Leading big
    leading_big = valid_time[valid_time['score_differential'] >= 14]
    if len(leading_big) > 100:
        results["by_score_differential"]["leading_big"] = {
            "range": "up 14+",
            "mean": round(leading_big['time_elapsed'].mean(), 1),
            "median": round(leading_big['time_elapsed'].median(), 1),
            "note": "Run clock, slower pace"
        }

    # Trailing big
    trailing_big = valid_time[valid_time['score_differential'] <= -14]
    if len(trailing_big) > 100:
        results["by_score_differential"]["trailing_big"] = {
            "range": "down 14+",
            "mean": round(trailing_big['time_elapsed'].mean(), 1),
            "median": round(trailing_big['time_elapsed'].median(), 1),
            "note": "More urgency"
        }

    # === BY QUARTER ===
    print("Analyzing by quarter...")

    results["by_quarter"] = {}

    for qtr in [1, 2, 3, 4]:
        qtr_plays = valid_time[valid_time['qtr'] == qtr]
        if len(qtr_plays) > 1000:
            results["by_quarter"][f"Q{qtr}"] = {
                "mean": round(qtr_plays['time_elapsed'].mean(), 1),
                "median": round(qtr_plays['time_elapsed'].median(), 1),
                "sample_size": len(qtr_plays)
            }

    # === PLAY CLOCK USAGE ===
    print("Analyzing play clock usage...")

    # Play clock data - convert to numeric first
    scrimmage['play_clock_numeric'] = pd.to_numeric(scrimmage['play_clock'], errors='coerce')
    clock_plays = scrimmage[scrimmage['play_clock_numeric'].notna()].copy()

    if len(clock_plays) > 1000:
        results["play_clock"] = {
            "mean_at_snap": round(clock_plays['play_clock_numeric'].mean(), 1),
            "median_at_snap": round(clock_plays['play_clock_numeric'].median(), 1),
            "std": round(clock_plays['play_clock_numeric'].std(), 1),
            "percentiles": {
                "p10": round(clock_plays['play_clock_numeric'].quantile(0.10), 1),
                "p25": round(clock_plays['play_clock_numeric'].quantile(0.25), 1),
                "p75": round(clock_plays['play_clock_numeric'].quantile(0.75), 1),
                "p90": round(clock_plays['play_clock_numeric'].quantile(0.90), 1)
            },
            "note": "Seconds remaining on play clock at snap"
        }

        # Delay of game approximation (very low play clock)
        delay_risk = clock_plays[clock_plays['play_clock_numeric'] <= 2]
        results["play_clock"]["delay_risk_rate"] = round(len(delay_risk) / len(clock_plays), 4)

    # === GAME LENGTH ===
    print("Analyzing game length...")

    # Total plays per game
    game_plays = scrimmage.groupby('game_id').agg({
        'play_id': 'count'
    }).reset_index()
    game_plays.columns = ['game_id', 'total_plays']

    results["game_length"] = {
        "plays_per_game": {
            "mean": round(game_plays['total_plays'].mean(), 1),
            "median": round(game_plays['total_plays'].median(), 1),
            "std": round(game_plays['total_plays'].std(), 1)
        },
        "estimated_game_time": {
            "scrimmage_minutes": round(
                game_plays['total_plays'].mean() * results["time_between_plays"]["overall"]["mean"] / 60, 1
            ),
            "note": "Does not include stoppages, commercials, halftime"
        }
    }

    # === TIMEOUT PATTERNS ===
    print("Analyzing timeout patterns...")

    timeouts = pbp[pbp['timeout'] == 1].copy()

    if len(timeouts) > 100:
        results["timeouts"] = {
            "total_timeouts": len(timeouts),
            "per_game": round(len(timeouts) / len(game_plays), 2),
            "by_quarter": {}
        }

        for qtr in [1, 2, 3, 4]:
            qtr_to = timeouts[timeouts['qtr'] == qtr]
            results["timeouts"]["by_quarter"][f"Q{qtr}"] = len(qtr_to)

    # === IMPLEMENTATION HINTS ===
    results["implementation_hints"] = {
        "time_off_clock": """
def time_off_clock(play_type: str, play_result: dict, pace: str = 'normal') -> int:
    '''
    Calculate seconds elapsed for a play.

    Args:
        play_type: 'pass' or 'run'
        play_result: dict with 'complete', 'first_down', 'out_of_bounds'
        pace: 'normal', 'hurry_up', or 'milk_clock'

    Returns:
        Seconds elapsed
    '''
    # Base time by pace
    if pace == 'hurry_up':
        base = 25  # ~25 seconds hurry-up
    elif pace == 'milk_clock':
        base = 40  # Use full play clock
    else:
        base = 32  # Normal pace ~32 seconds

    # Adjustments for clock-stopping plays
    if play_type == 'pass' and not play_result.get('complete', True):
        # Incomplete pass - clock stops, faster next play
        return max(5, base - 10)

    if play_result.get('out_of_bounds', False):
        # Out of bounds - clock stops
        return max(5, base - 8)

    if play_result.get('first_down', False):
        # First down - brief stop for chains
        return base + 3

    return base
""",
        "pace_selection": """
def select_pace(score_diff: int, quarter: int, time_remaining: int) -> str:
    '''
    Determine offensive pace based on game situation.

    Returns: 'hurry_up', 'normal', or 'milk_clock'
    '''
    # Two-minute drill
    if quarter in [2, 4] and time_remaining <= 120 and score_diff <= 0:
        return 'hurry_up'

    # Trailing late
    if quarter == 4 and time_remaining <= 300 and score_diff < -8:
        return 'hurry_up'

    # Leading late - milk clock
    if quarter == 4 and time_remaining <= 300 and score_diff >= 8:
        return 'milk_clock'

    # Leading big anytime
    if score_diff >= 17:
        return 'milk_clock'

    return 'normal'
"""
    }

    return convert_to_native(results)


def main():
    results = analyze_clock()

    # Save JSON export
    export_path = Path("research/exports/clock_model.json")
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {export_path}")

    # Generate markdown report
    report = f"""# NFL Clock Management Analysis

**Source:** nfl_data_py play-by-play data
**Seasons:** 2019-2024

---

## Time Between Plays (Overall)

| Metric | Seconds |
|--------|---------|
| Mean | {results['time_between_plays']['overall']['mean']} |
| Median | {results['time_between_plays']['overall']['median']} |
| Std Dev | {results['time_between_plays']['overall']['std']} |
| P10 | {results['time_between_plays']['overall']['percentiles']['p10']} |
| P90 | {results['time_between_plays']['overall']['percentiles']['p90']} |

---

## By Play Type

| Type | Mean | Median |
|------|------|--------|
| Pass | {results['time_between_plays']['by_play_type']['pass']['mean']} | {results['time_between_plays']['by_play_type']['pass']['median']} |
| Run | {results['time_between_plays']['by_play_type']['run']['mean']} | {results['time_between_plays']['by_play_type']['run']['median']} |

---

## By Play Result

| Result | Mean | Median | Note |
|--------|------|--------|------|
"""

    for result, data in results['time_between_plays']['by_result'].items():
        note = data.get('note', '')
        report += f"| {result} | {data['mean']} | {data['median']} | {note} |\n"

    report += f"""
---

## Pace Comparison

| Pace | Mean | Median | Sample |
|------|------|--------|--------|
| Hurry-up | {results['pace']['hurry_up']['mean']} | {results['pace']['hurry_up']['median']} | {results['pace']['hurry_up']['sample_size']:,} |
| Normal | {results['pace']['normal']['mean']} | {results['pace']['normal']['median']} | {results['pace']['normal']['sample_size']:,} |

---

## By Quarter

| Quarter | Mean | Median |
|---------|------|--------|
"""

    for qtr, data in results['by_quarter'].items():
        report += f"| {qtr} | {data['mean']} | {data['median']} |\n"

    report += f"""
---

## Play Clock at Snap

| Metric | Seconds |
|--------|---------|
| Mean | {results['play_clock']['mean_at_snap']} |
| Median | {results['play_clock']['median_at_snap']} |
| Delay Risk Rate | {results['play_clock']['delay_risk_rate']*100:.2f}% |

---

## Game Length

- **Plays per game:** {results['game_length']['plays_per_game']['mean']} (median: {results['game_length']['plays_per_game']['median']})
- **Estimated scrimmage time:** {results['game_length']['estimated_game_time']['scrimmage_minutes']} minutes

---

## Timeouts

- **Per game:** {results['timeouts']['per_game']}
- **By quarter:** Q1={results['timeouts']['by_quarter']['Q1']}, Q2={results['timeouts']['by_quarter']['Q2']}, Q3={results['timeouts']['by_quarter']['Q3']}, Q4={results['timeouts']['by_quarter']['Q4']}

---

*Generated by researcher_agent for game_layer_agent*
"""

    report_path = Path("research/reports/clock_analysis.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"Saved: {report_path}")

    # Print summary
    print("\n" + "="*50)
    print("CLOCK MANAGEMENT SUMMARY")
    print("="*50)
    print(f"Time between plays (overall): {results['time_between_plays']['overall']['mean']} sec")
    print(f"Hurry-up pace: {results['pace']['hurry_up']['mean']} sec")
    print(f"Normal pace: {results['pace']['normal']['mean']} sec")
    print(f"Play clock at snap: {results['play_clock']['mean_at_snap']} sec remaining")
    print(f"Plays per game: {results['game_length']['plays_per_game']['mean']}")


if __name__ == "__main__":
    main()
