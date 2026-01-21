"""
Drive Outcome Analysis for Game Layer Agent

Analyzes NFL play-by-play data to understand:
- Drive outcomes by starting field position
- Red zone conversion rates
- Scoring probabilities by field position
- Drive success metrics

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


def get_field_position_bucket(yardline_100):
    """
    Convert yardline_100 (distance from opponent's end zone) to bucket.
    yardline_100: 1 = opponent's 1, 99 = own 1, 50 = midfield
    """
    if yardline_100 is None or pd.isna(yardline_100):
        return None

    if yardline_100 <= 10:
        return "opp_1-10"  # Red zone
    elif yardline_100 <= 20:
        return "opp_11-20"  # Inside 20
    elif yardline_100 <= 35:
        return "opp_21-35"  # Field goal range
    elif yardline_100 <= 50:
        return "opp_36-50"  # Opponent territory
    elif yardline_100 <= 65:
        return "own_36-50"  # Midfield-ish
    elif yardline_100 <= 80:
        return "own_21-35"
    else:
        return "own_1-20"  # Deep own territory


def analyze_drive_outcomes():
    """Analyze drive outcome patterns from NFL data."""

    print("Loading play-by-play data (2019-2024)...")
    pbp = nfl.import_pbp_data(years=range(2019, 2025))

    # Filter to scrimmage plays for drive analysis
    scrimmage = pbp[pbp['play_type'].isin(['pass', 'run'])].copy()

    print(f"Analyzing {len(scrimmage):,} scrimmage plays...")

    results = {
        "model_name": "drive_outcomes",
        "version": "1.0",
        "source": "nfl_data_py play-by-play 2019-2024"
    }

    # === BUILD DRIVE TABLE ===
    print("\nBuilding drive summary table...")

    # Get first and last play of each drive
    drives = scrimmage.groupby(['game_id', 'posteam', 'drive']).agg({
        'yardline_100': 'first',  # Starting field position
        'fixed_drive_result': 'last',  # Drive outcome
        'play_id': 'count',  # Plays in drive
        'yards_gained': 'sum',  # Total yards
        'first_down': 'sum'  # First downs
    }).reset_index()

    drives.columns = ['game_id', 'posteam', 'drive', 'start_yardline', 'result', 'plays', 'yards', 'first_downs']

    # Add field position bucket
    drives['start_bucket'] = drives['start_yardline'].apply(get_field_position_bucket)
    drives = drives[drives['start_bucket'].notna()]  # Remove invalid

    print(f"Analyzing {len(drives):,} drives...")

    # === OVERALL DRIVE OUTCOMES ===
    print("Analyzing overall drive outcomes...")

    outcome_counts = drives['result'].value_counts()
    total_drives = len(drives)

    results["overall_outcomes"] = {}
    for outcome in ['Touchdown', 'Field goal', 'Punt', 'Turnover', 'Turnover on downs', 'End of half', 'Safety']:
        if outcome in outcome_counts:
            results["overall_outcomes"][outcome.lower().replace(' ', '_')] = {
                "count": int(outcome_counts[outcome]),
                "rate": round(outcome_counts[outcome] / total_drives, 4)
            }

    results["total_drives"] = total_drives

    # === OUTCOMES BY STARTING FIELD POSITION ===
    print("Analyzing outcomes by starting field position...")

    results["by_starting_position"] = {}

    # Order buckets from opponent's end zone to own end zone
    bucket_order = ["opp_1-10", "opp_11-20", "opp_21-35", "opp_36-50", "own_36-50", "own_21-35", "own_1-20"]

    for bucket in bucket_order:
        bucket_drives = drives[drives['start_bucket'] == bucket]
        if len(bucket_drives) < 50:
            continue

        bucket_total = len(bucket_drives)
        bucket_outcomes = bucket_drives['result'].value_counts()

        results["by_starting_position"][bucket] = {
            "count": bucket_total,
            "outcomes": {}
        }

        for outcome in ['Touchdown', 'Field goal', 'Punt', 'Turnover', 'Turnover on downs']:
            if outcome in bucket_outcomes:
                results["by_starting_position"][bucket]["outcomes"][outcome.lower().replace(' ', '_')] = {
                    "count": int(bucket_outcomes[outcome]),
                    "rate": round(bucket_outcomes[outcome] / bucket_total, 4)
                }

        # Scoring rate (TD + FG)
        td_count = bucket_outcomes.get('Touchdown', 0)
        fg_count = bucket_outcomes.get('Field goal', 0)
        results["by_starting_position"][bucket]["scoring_rate"] = round((td_count + fg_count) / bucket_total, 4)
        results["by_starting_position"][bucket]["points_expected"] = round(
            (td_count * 6.5 + fg_count * 3) / bucket_total, 2  # 6.5 accounts for XP
        )

    # === RED ZONE ANALYSIS ===
    print("Analyzing red zone efficiency...")

    red_zone_drives = drives[drives['start_yardline'] <= 20]
    rz_total = len(red_zone_drives)
    rz_outcomes = red_zone_drives['result'].value_counts()

    results["red_zone"] = {
        "total_drives": rz_total,
        "td_rate": round(rz_outcomes.get('Touchdown', 0) / rz_total, 4),
        "fg_rate": round(rz_outcomes.get('Field goal', 0) / rz_total, 4),
        "scoring_rate": round((rz_outcomes.get('Touchdown', 0) + rz_outcomes.get('Field goal', 0)) / rz_total, 4),
        "turnover_rate": round((rz_outcomes.get('Turnover', 0) + rz_outcomes.get('Turnover on downs', 0)) / rz_total, 4)
    }

    # Break down by inside 10 vs 11-20
    inside_10 = drives[drives['start_yardline'] <= 10]
    inside_10_outcomes = inside_10['result'].value_counts()

    results["red_zone"]["inside_10"] = {
        "total_drives": len(inside_10),
        "td_rate": round(inside_10_outcomes.get('Touchdown', 0) / len(inside_10), 4),
        "scoring_rate": round(
            (inside_10_outcomes.get('Touchdown', 0) + inside_10_outcomes.get('Field goal', 0)) / len(inside_10), 4
        )
    }

    rz_11_20 = drives[(drives['start_yardline'] > 10) & (drives['start_yardline'] <= 20)]
    rz_11_20_outcomes = rz_11_20['result'].value_counts()

    results["red_zone"]["11_to_20"] = {
        "total_drives": len(rz_11_20),
        "td_rate": round(rz_11_20_outcomes.get('Touchdown', 0) / len(rz_11_20), 4),
        "scoring_rate": round(
            (rz_11_20_outcomes.get('Touchdown', 0) + rz_11_20_outcomes.get('Field goal', 0)) / len(rz_11_20), 4
        )
    }

    # === SCORING PROBABILITY BY YARDLINE ===
    print("Analyzing scoring probability by yardline...")

    # Create finer-grained lookup (every 10 yards)
    results["scoring_by_yardline"] = {}

    for start in range(1, 100, 10):
        end = min(start + 9, 99)
        bucket_drives = drives[(drives['start_yardline'] >= start) & (drives['start_yardline'] <= end)]

        if len(bucket_drives) < 100:
            continue

        bucket_outcomes = bucket_drives['result'].value_counts()
        bucket_total = len(bucket_drives)

        td_count = bucket_outcomes.get('Touchdown', 0)
        fg_count = bucket_outcomes.get('Field goal', 0)

        results["scoring_by_yardline"][f"{start}-{end}"] = {
            "count": bucket_total,
            "td_rate": round(td_count / bucket_total, 4),
            "fg_rate": round(fg_count / bucket_total, 4),
            "scoring_rate": round((td_count + fg_count) / bucket_total, 4),
            "points_expected": round((td_count * 6.5 + fg_count * 3) / bucket_total, 2)
        }

    # === DRIVE EFFICIENCY METRICS ===
    print("Analyzing drive efficiency...")

    results["drive_efficiency"] = {
        "avg_yards_per_drive": round(drives['yards'].mean(), 1),
        "avg_plays_per_drive": round(drives['plays'].mean(), 1),
        "avg_first_downs_per_drive": round(drives['first_downs'].mean(), 2),
        "yards_per_play": round(drives['yards'].sum() / drives['plays'].sum(), 2)
    }

    # By outcome
    results["drive_efficiency"]["by_outcome"] = {}
    for outcome in ['Touchdown', 'Field goal', 'Punt', 'Turnover']:
        outcome_drives = drives[drives['result'] == outcome]
        if len(outcome_drives) > 100:
            results["drive_efficiency"]["by_outcome"][outcome.lower().replace(' ', '_')] = {
                "avg_yards": round(outcome_drives['yards'].mean(), 1),
                "avg_plays": round(outcome_drives['plays'].mean(), 1),
                "avg_first_downs": round(outcome_drives['first_downs'].mean(), 2)
            }

    # === THREE AND OUT RATE ===
    print("Analyzing three-and-out rate...")

    three_and_out = drives[(drives['plays'] <= 3) & (drives['result'] == 'Punt')]
    results["three_and_out"] = {
        "rate": round(len(three_and_out) / len(drives), 4),
        "count": len(three_and_out)
    }

    # === IMPLEMENTATION HINTS ===
    results["implementation_hints"] = {
        "expected_points": """
def expected_points_from_field_position(yardline_100: int) -> float:
    '''
    Expected points based on starting field position.
    yardline_100: distance from opponent's end zone (1 = opponent's 1, 99 = own 1)

    Returns expected points for the drive.
    '''
    # Approximate from research data
    if yardline_100 <= 10:
        return 4.5  # Red zone inside 10
    elif yardline_100 <= 20:
        return 3.8  # Red zone 11-20
    elif yardline_100 <= 35:
        return 2.5  # Field goal range
    elif yardline_100 <= 50:
        return 1.8  # Opponent territory
    elif yardline_100 <= 65:
        return 1.2  # Midfield
    elif yardline_100 <= 80:
        return 0.8  # Own 20-35
    else:
        return 0.4  # Deep own territory
""",
        "drive_outcome_probability": """
def drive_outcome_probabilities(start_yardline: int) -> dict:
    '''
    Returns probability distribution for drive outcomes.

    Example for midfield (start_yardline ~50):
    - TD: 22%
    - FG: 12%
    - Punt: 45%
    - Turnover: 12%
    - TOD: 5%
    - Other: 4%
    '''
    # Lookup from by_starting_position table
    pass
"""
    }

    return convert_to_native(results)


def main():
    results = analyze_drive_outcomes()

    # Save JSON export
    export_path = Path("research/exports/drive_outcome_model.json")
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {export_path}")

    # Generate markdown report
    report = f"""# NFL Drive Outcome Analysis

**Source:** nfl_data_py play-by-play data
**Seasons:** 2019-2024
**Total Drives:** {results['total_drives']:,}

---

## Overall Drive Outcomes

| Outcome | Rate | Count |
|---------|------|-------|
"""

    for outcome, data in results['overall_outcomes'].items():
        report += f"| {outcome.replace('_', ' ').title()} | {data['rate']*100:.1f}% | {data['count']:,} |\n"

    report += """
---

## Outcomes by Starting Field Position

| Start Position | Count | TD% | FG% | Punt% | Scoring% | Exp. Pts |
|----------------|-------|-----|-----|-------|----------|----------|
"""

    for bucket, data in results['by_starting_position'].items():
        td_rate = data['outcomes'].get('touchdown', {}).get('rate', 0) * 100
        fg_rate = data['outcomes'].get('field_goal', {}).get('rate', 0) * 100
        punt_rate = data['outcomes'].get('punt', {}).get('rate', 0) * 100
        report += f"| {bucket} | {data['count']:,} | {td_rate:.1f}% | {fg_rate:.1f}% | {punt_rate:.1f}% | {data['scoring_rate']*100:.1f}% | {data['points_expected']:.2f} |\n"

    report += f"""
---

## Red Zone Efficiency

| Metric | Value |
|--------|-------|
| Total RZ Drives | {results['red_zone']['total_drives']:,} |
| TD Rate | {results['red_zone']['td_rate']*100:.1f}% |
| FG Rate | {results['red_zone']['fg_rate']*100:.1f}% |
| Scoring Rate | {results['red_zone']['scoring_rate']*100:.1f}% |
| Turnover Rate | {results['red_zone']['turnover_rate']*100:.1f}% |

**Inside 10:**
- TD Rate: {results['red_zone']['inside_10']['td_rate']*100:.1f}%
- Scoring Rate: {results['red_zone']['inside_10']['scoring_rate']*100:.1f}%

**11-20 Yard Line:**
- TD Rate: {results['red_zone']['11_to_20']['td_rate']*100:.1f}%
- Scoring Rate: {results['red_zone']['11_to_20']['scoring_rate']*100:.1f}%

---

## Scoring Probability by Yardline

| Yardline | Count | TD% | FG% | Scoring% | Exp. Pts |
|----------|-------|-----|-----|----------|----------|
"""

    for bucket, data in results['scoring_by_yardline'].items():
        report += f"| {bucket} | {data['count']:,} | {data['td_rate']*100:.1f}% | {data['fg_rate']*100:.1f}% | {data['scoring_rate']*100:.1f}% | {data['points_expected']:.2f} |\n"

    report += f"""
---

## Drive Efficiency

| Metric | Value |
|--------|-------|
| Avg Yards/Drive | {results['drive_efficiency']['avg_yards_per_drive']} |
| Avg Plays/Drive | {results['drive_efficiency']['avg_plays_per_drive']} |
| Avg First Downs/Drive | {results['drive_efficiency']['avg_first_downs_per_drive']} |
| Yards/Play | {results['drive_efficiency']['yards_per_play']} |

**Three-and-Out Rate:** {results['three_and_out']['rate']*100:.1f}%

---

*Generated by researcher_agent for game_layer_agent*
"""

    report_path = Path("research/reports/drive_outcome_analysis.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"Saved: {report_path}")

    # Print summary
    print("\n" + "="*50)
    print("DRIVE OUTCOME SUMMARY")
    print("="*50)
    print(f"Total drives analyzed: {results['total_drives']:,}")
    print(f"TD rate: {results['overall_outcomes']['touchdown']['rate']*100:.1f}%")
    print(f"FG rate: {results['overall_outcomes']['field_goal']['rate']*100:.1f}%")
    print(f"Punt rate: {results['overall_outcomes']['punt']['rate']*100:.1f}%")
    print(f"Turnover rate: {results['overall_outcomes']['turnover']['rate']*100:.1f}%")
    print(f"Red zone scoring: {results['red_zone']['scoring_rate']*100:.1f}%")
    print(f"Three-and-out: {results['three_and_out']['rate']*100:.1f}%")


if __name__ == "__main__":
    main()
