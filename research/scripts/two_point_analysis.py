"""
Two-Point Conversion Analysis for Game Layer Agent

Analyzes NFL play-by-play data to understand:
- When teams go for 2-point conversions
- Success rates by play type
- Score differential patterns
- Optimal decision making

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


def analyze_two_point():
    """Analyze two-point conversion patterns from NFL data."""

    print("Loading play-by-play data (2019-2024)...")
    pbp = nfl.import_pbp_data(years=range(2019, 2025))

    # Filter to PAT and 2-point attempts
    # PAT plays have play_type == 'extra_point'
    pat_plays = pbp[pbp['play_type'] == 'extra_point'].copy()
    # 2PT plays are detected via two_point_conv_result being non-null
    two_pt_plays = pbp[pbp['two_point_conv_result'].notna()].copy()

    print(f"Analyzing {len(pat_plays):,} PAT attempts, {len(two_pt_plays):,} two-point attempts...")

    results = {
        "model_name": "two_point",
        "version": "1.0",
        "source": "nfl_data_py play-by-play 2019-2024"
    }

    # === OVERALL RATES ===
    print("\nAnalyzing overall conversion rates...")

    total_td_conversions = len(pat_plays) + len(two_pt_plays)

    # PAT success
    pat_success = pat_plays[pat_plays['extra_point_result'] == 'good']
    pat_rate = len(pat_success) / len(pat_plays) if len(pat_plays) > 0 else 0

    # 2PT success
    two_pt_success = two_pt_plays[two_pt_plays['two_point_conv_result'] == 'success']
    two_pt_rate = len(two_pt_success) / len(two_pt_plays) if len(two_pt_plays) > 0 else 0

    # Go-for-2 rate
    go_for_2_rate = len(two_pt_plays) / total_td_conversions if total_td_conversions > 0 else 0

    results["overall"] = {
        "pat_attempts": len(pat_plays),
        "pat_success_rate": round(pat_rate, 4),
        "two_point_attempts": len(two_pt_plays),
        "two_point_success_rate": round(two_pt_rate, 4),
        "go_for_2_rate": round(go_for_2_rate, 4),
        "expected_points_pat": round(pat_rate * 1, 4),
        "expected_points_2pt": round(two_pt_rate * 2, 4)
    }

    # === BY PLAY TYPE ===
    print("Analyzing success by play type...")

    # Determine play type from pass_attempt/rush_attempt
    two_pt_plays['is_pass'] = two_pt_plays['pass_attempt'] == 1
    two_pt_plays['is_run'] = two_pt_plays['rush_attempt'] == 1

    pass_2pt = two_pt_plays[two_pt_plays['is_pass'] == True]
    run_2pt = two_pt_plays[two_pt_plays['is_run'] == True]

    pass_success = pass_2pt[pass_2pt['two_point_conv_result'] == 'success']
    run_success = run_2pt[run_2pt['two_point_conv_result'] == 'success']

    results["by_play_type"] = {
        "pass": {
            "attempts": len(pass_2pt),
            "success_rate": round(len(pass_success) / len(pass_2pt), 4) if len(pass_2pt) > 0 else 0
        },
        "run": {
            "attempts": len(run_2pt),
            "success_rate": round(len(run_success) / len(run_2pt), 4) if len(run_2pt) > 0 else 0
        }
    }

    # === BY SCORE DIFFERENTIAL ===
    print("Analyzing by score differential...")

    # Calculate score diff BEFORE the TD (subtract 6 from posteam score)
    two_pt_plays['score_diff_before_td'] = (
        two_pt_plays['posteam_score'] - 6 - two_pt_plays['defteam_score']
    )

    results["by_score_differential"] = {}

    # Common score differentials where 2PT decisions matter
    score_diffs = {
        "down_2": -2,   # Down 2, need 2PT to tie
        "down_5": -5,   # Down 5, 2PT gets within FG
        "down_8": -8,   # Down 8, 2PT makes it one score
        "down_9": -9,   # Down 9, need 2PT to make it one score
        "down_11": -11, # Down 11, 2PT gets within one score (with FG)
        "down_12": -12, # Down 12
        "down_14": -14, # Down 14, two TDs needed
        "down_15": -15, # Down 15
        "tied": 0,      # Tied, go ahead
        "up_1": 1,      # Up 1
        "up_7": 7,      # Up 7
        "up_8": 8,      # Up 8
    }

    for name, diff in score_diffs.items():
        # Find 2PT attempts at this score differential
        diff_2pt = two_pt_plays[two_pt_plays['score_diff_before_td'] == diff]
        diff_pat = pat_plays[
            (pat_plays['posteam_score'] - 6 - pat_plays['defteam_score']) == diff
        ]

        total_at_diff = len(diff_2pt) + len(diff_pat)
        if total_at_diff < 10:
            continue

        go_rate = len(diff_2pt) / total_at_diff if total_at_diff > 0 else 0

        diff_success = diff_2pt[diff_2pt['two_point_conv_result'] == 'success']
        success_rate = len(diff_success) / len(diff_2pt) if len(diff_2pt) > 0 else 0

        results["by_score_differential"][name] = {
            "score_diff": diff,
            "total_tds": total_at_diff,
            "two_point_attempts": len(diff_2pt),
            "go_for_2_rate": round(go_rate, 4),
            "success_rate": round(success_rate, 4) if len(diff_2pt) > 0 else None
        }

    # === BY QUARTER ===
    print("Analyzing by quarter...")

    results["by_quarter"] = {}

    for qtr in [1, 2, 3, 4]:
        qtr_2pt = two_pt_plays[two_pt_plays['qtr'] == qtr]
        qtr_pat = pat_plays[pat_plays['qtr'] == qtr]

        total_qtr = len(qtr_2pt) + len(qtr_pat)
        if total_qtr < 50:
            continue

        go_rate = len(qtr_2pt) / total_qtr
        qtr_success = qtr_2pt[qtr_2pt['two_point_conv_result'] == 'success']
        success_rate = len(qtr_success) / len(qtr_2pt) if len(qtr_2pt) > 0 else 0

        results["by_quarter"][f"Q{qtr}"] = {
            "total_tds": total_qtr,
            "two_point_attempts": len(qtr_2pt),
            "go_for_2_rate": round(go_rate, 4),
            "success_rate": round(success_rate, 4) if len(qtr_2pt) > 0 else None
        }

    # === BY TIME REMAINING ===
    print("Analyzing by time remaining...")

    results["by_time_remaining"] = {}

    # Only look at 4th quarter
    q4_2pt = two_pt_plays[two_pt_plays['qtr'] == 4].copy()
    q4_pat = pat_plays[pat_plays['qtr'] == 4].copy()

    time_buckets = [
        ("under_2_min", 0, 120),
        ("2_to_5_min", 120, 300),
        ("5_to_10_min", 300, 600),
        ("over_10_min", 600, 900)
    ]

    for name, min_sec, max_sec in time_buckets:
        bucket_2pt = q4_2pt[
            (q4_2pt['game_seconds_remaining'] >= min_sec) &
            (q4_2pt['game_seconds_remaining'] < max_sec)
        ]
        bucket_pat = q4_pat[
            (q4_pat['game_seconds_remaining'] >= min_sec) &
            (q4_pat['game_seconds_remaining'] < max_sec)
        ]

        total_bucket = len(bucket_2pt) + len(bucket_pat)
        if total_bucket < 20:
            continue

        go_rate = len(bucket_2pt) / total_bucket
        bucket_success = bucket_2pt[bucket_2pt['two_point_conv_result'] == 'success']
        success_rate = len(bucket_success) / len(bucket_2pt) if len(bucket_2pt) > 0 else 0

        results["by_time_remaining"][name] = {
            "total_tds": total_bucket,
            "two_point_attempts": len(bucket_2pt),
            "go_for_2_rate": round(go_rate, 4),
            "success_rate": round(success_rate, 4) if len(bucket_2pt) > 0 else None
        }

    # === DECISION CHART ===
    print("Building decision chart...")

    # Classic 2-point decision chart based on score differential after TD
    # (before PAT/2PT decision)
    results["decision_chart"] = {
        "description": "Score differential AFTER scoring TD, BEFORE PAT/2PT",
        "recommendations": {
            "-8": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT ties game, PAT still down 7"
            },
            "-5": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT gets within FG, PAT still need TD"
            },
            "-2": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT ties, PAT down 1"
            },
            "-9": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT makes it one score (down 7)"
            },
            "-15": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT makes it two scores (down 13)"
            },
            "-14": {
                "recommendation": "KICK_PAT",
                "reason": "PAT down 13, 2PT down 12 - both two scores"
            },
            "-11": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT down 9 (TD+2PT ties), PAT down 10 (need TD+FG)"
            },
            "-4": {
                "recommendation": "KICK_PAT",
                "reason": "PAT down 3 (FG ties), 2PT down 2 (similar)"
            },
            "-1": {
                "recommendation": "KICK_PAT",
                "reason": "PAT ties game"
            },
            "0": {
                "recommendation": "KICK_PAT",
                "reason": "PAT goes up 1, safe lead"
            },
            "+1": {
                "recommendation": "GO_FOR_2",
                "reason": "2PT up 3 (need FG to tie), PAT up 2"
            },
            "+7": {
                "recommendation": "KICK_PAT",
                "reason": "PAT up 8 (need TD+2PT to tie)"
            },
            "+8": {
                "recommendation": "KICK_PAT",
                "reason": "PAT up 9 (two scores)"
            }
        }
    }

    # === IMPLEMENTATION HINTS ===
    results["implementation_hints"] = {
        "two_point_decision": """
def should_go_for_two(score_diff_after_td: int, quarter: int, time_remaining: int) -> bool:
    '''
    Decide whether to attempt 2-point conversion.

    Args:
        score_diff_after_td: Our score - opponent score AFTER TD (before PAT/2PT)
        quarter: Current quarter (1-4)
        time_remaining: Seconds remaining in game

    Returns:
        True if should go for 2, False for PAT
    '''
    # Classic chart situations (always go for 2)
    go_for_2_diffs = [-8, -5, -2, -9, -15, -11, 1]

    if score_diff_after_td in go_for_2_diffs:
        return True

    # Late game trailing - more aggressive
    if quarter == 4 and time_remaining < 300 and score_diff_after_td < 0:
        # Down multiple scores late, go for 2
        if score_diff_after_td <= -8:
            return True

    # Default: kick PAT
    return False
""",
        "expected_value_comparison": """
# Expected points comparison
PAT_SUCCESS_RATE = 0.944
TWO_PT_SUCCESS_RATE = 0.477

expected_pat = PAT_SUCCESS_RATE * 1  # = 0.944 points
expected_2pt = TWO_PT_SUCCESS_RATE * 2  # = 0.954 points

# Pure EV says go for 2, but game theory matters more
# The decision chart accounts for discrete score states
"""
    }

    return convert_to_native(results)


def main():
    results = analyze_two_point()

    # Save JSON export
    export_path = Path("research/exports/two_point_model.json")
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {export_path}")

    # Generate markdown report
    report = f"""# NFL Two-Point Conversion Analysis

**Source:** nfl_data_py play-by-play data
**Seasons:** 2019-2024

---

## Overall Statistics

| Metric | Value |
|--------|-------|
| PAT Attempts | {results['overall']['pat_attempts']:,} |
| PAT Success Rate | {results['overall']['pat_success_rate']*100:.1f}% |
| 2PT Attempts | {results['overall']['two_point_attempts']:,} |
| 2PT Success Rate | {results['overall']['two_point_success_rate']*100:.1f}% |
| Go-for-2 Rate | {results['overall']['go_for_2_rate']*100:.1f}% |

**Expected Points:**
- PAT: {results['overall']['expected_points_pat']:.3f} points
- 2PT: {results['overall']['expected_points_2pt']:.3f} points

---

## Success Rate by Play Type

| Play Type | Attempts | Success Rate |
|-----------|----------|--------------|
| Pass | {results['by_play_type']['pass']['attempts']} | {results['by_play_type']['pass']['success_rate']*100:.1f}% |
| Run | {results['by_play_type']['run']['attempts']} | {results['by_play_type']['run']['success_rate']*100:.1f}% |

---

## Go-for-2 Rate by Score Differential

| Situation | Score Diff | TDs | 2PT Attempts | Go Rate | Success |
|-----------|------------|-----|--------------|---------|---------|
"""

    for name, data in results['by_score_differential'].items():
        success = f"{data['success_rate']*100:.1f}%" if data['success_rate'] else "N/A"
        report += f"| {name} | {data['score_diff']:+d} | {data['total_tds']} | {data['two_point_attempts']} | {data['go_for_2_rate']*100:.1f}% | {success} |\n"

    report += """
---

## By Quarter

| Quarter | TDs | 2PT Attempts | Go Rate | Success |
|---------|-----|--------------|---------|---------|
"""

    for qtr, data in results['by_quarter'].items():
        success = f"{data['success_rate']*100:.1f}%" if data['success_rate'] else "N/A"
        report += f"| {qtr} | {data['total_tds']} | {data['two_point_attempts']} | {data['go_for_2_rate']*100:.1f}% | {success} |\n"

    report += """
---

## Q4 by Time Remaining

| Time | TDs | 2PT Attempts | Go Rate | Success |
|------|-----|--------------|---------|---------|
"""

    for name, data in results['by_time_remaining'].items():
        success = f"{data['success_rate']*100:.1f}%" if data['success_rate'] else "N/A"
        report += f"| {name} | {data['total_tds']} | {data['two_point_attempts']} | {data['go_for_2_rate']*100:.1f}% | {success} |\n"

    report += """
---

## Decision Chart

Score differential shown is AFTER TD, BEFORE PAT/2PT decision.

| Score Diff | Recommendation | Reason |
|------------|----------------|--------|
"""

    for diff, data in results['decision_chart']['recommendations'].items():
        report += f"| {diff} | {data['recommendation']} | {data['reason']} |\n"

    report += """
---

*Generated by researcher_agent for game_layer_agent*
"""

    report_path = Path("research/reports/two_point_analysis.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"Saved: {report_path}")

    # Print summary
    print("\n" + "="*50)
    print("TWO-POINT CONVERSION SUMMARY")
    print("="*50)
    print(f"PAT success rate: {results['overall']['pat_success_rate']*100:.1f}%")
    print(f"2PT success rate: {results['overall']['two_point_success_rate']*100:.1f}%")
    print(f"Go-for-2 rate: {results['overall']['go_for_2_rate']*100:.1f}%")
    print(f"Pass 2PT success: {results['by_play_type']['pass']['success_rate']*100:.1f}%")
    print(f"Run 2PT success: {results['by_play_type']['run']['success_rate']*100:.1f}%")
    print(f"Expected points PAT: {results['overall']['expected_points_pat']:.3f}")
    print(f"Expected points 2PT: {results['overall']['expected_points_2pt']:.3f}")


if __name__ == "__main__":
    main()
