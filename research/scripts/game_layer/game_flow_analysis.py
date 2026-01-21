"""
Game Flow Analysis for Game Layer Agent

Analyzes NFL play-by-play data to understand:
- Plays per game
- Drives per team per game
- Plays per drive (by outcome)
- Time per play (by type)
- Possession patterns

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


def analyze_game_flow():
    """Analyze game flow patterns from NFL data."""

    print("Loading play-by-play data (2019-2024)...")
    pbp = nfl.import_pbp_data(years=range(2019, 2025))

    # Filter to regular plays (exclude penalties, timeouts, etc.)
    plays = pbp[pbp['play_type'].isin(['pass', 'run', 'punt', 'field_goal', 'kickoff', 'extra_point', 'two_point_attempt'])].copy()

    # Scrimmage plays only for most stats
    scrimmage = pbp[pbp['play_type'].isin(['pass', 'run'])].copy()

    print(f"Analyzing {len(plays):,} total plays, {len(scrimmage):,} scrimmage plays...")

    results = {
        "model_name": "game_flow",
        "version": "1.0",
        "source": "nfl_data_py play-by-play 2019-2024"
    }

    # === PLAYS PER GAME ===
    print("\nAnalyzing plays per game...")

    game_plays = scrimmage.groupby('game_id').size()

    results["plays_per_game"] = {
        "mean": round(game_plays.mean(), 1),
        "median": round(game_plays.median(), 1),
        "std": round(game_plays.std(), 1),
        "min": int(game_plays.min()),
        "max": int(game_plays.max()),
        "percentiles": {
            "p10": round(game_plays.quantile(0.10), 1),
            "p25": round(game_plays.quantile(0.25), 1),
            "p75": round(game_plays.quantile(0.75), 1),
            "p90": round(game_plays.quantile(0.90), 1)
        },
        "total_games": len(game_plays)
    }

    # === PLAYS PER TEAM PER GAME ===
    print("Analyzing plays per team per game...")

    # Get plays per possession team per game
    team_plays = scrimmage.groupby(['game_id', 'posteam']).size().reset_index(name='plays')

    results["plays_per_team_per_game"] = {
        "mean": round(team_plays['plays'].mean(), 1),
        "median": round(team_plays['plays'].median(), 1),
        "std": round(team_plays['plays'].std(), 1),
        "percentiles": {
            "p10": round(team_plays['plays'].quantile(0.10), 1),
            "p25": round(team_plays['plays'].quantile(0.25), 1),
            "p75": round(team_plays['plays'].quantile(0.75), 1),
            "p90": round(team_plays['plays'].quantile(0.90), 1)
        }
    }

    # === DRIVES PER GAME ===
    print("Analyzing drives per game...")

    # Each unique drive_id per game
    drives = scrimmage.groupby('game_id')['drive'].nunique()

    results["drives_per_game"] = {
        "mean": round(drives.mean(), 1),
        "median": round(drives.median(), 1),
        "std": round(drives.std(), 1),
        "percentiles": {
            "p10": round(drives.quantile(0.10), 1),
            "p25": round(drives.quantile(0.25), 1),
            "p75": round(drives.quantile(0.75), 1),
            "p90": round(drives.quantile(0.90), 1)
        }
    }

    # Drives per team per game
    team_drives = scrimmage.groupby(['game_id', 'posteam'])['drive'].nunique().reset_index(name='drives')

    results["drives_per_team_per_game"] = {
        "mean": round(team_drives['drives'].mean(), 1),
        "median": round(team_drives['drives'].median(), 1),
        "std": round(team_drives['drives'].std(), 1),
        "percentiles": {
            "p10": round(team_drives['drives'].quantile(0.10), 1),
            "p25": round(team_drives['drives'].quantile(0.25), 1),
            "p75": round(team_drives['drives'].quantile(0.75), 1),
            "p90": round(team_drives['drives'].quantile(0.90), 1)
        }
    }

    # === PLAYS PER DRIVE ===
    print("Analyzing plays per drive...")

    # Group by game and drive to get plays per drive
    drive_plays = scrimmage.groupby(['game_id', 'posteam', 'drive']).agg({
        'play_id': 'count',
        'fixed_drive_result': 'first'  # Drive outcome
    }).reset_index()
    drive_plays.columns = ['game_id', 'posteam', 'drive', 'plays', 'result']

    results["plays_per_drive"] = {
        "overall": {
            "mean": round(drive_plays['plays'].mean(), 2),
            "median": round(drive_plays['plays'].median(), 1),
            "std": round(drive_plays['plays'].std(), 2),
            "percentiles": {
                "p10": round(drive_plays['plays'].quantile(0.10), 1),
                "p25": round(drive_plays['plays'].quantile(0.25), 1),
                "p75": round(drive_plays['plays'].quantile(0.75), 1),
                "p90": round(drive_plays['plays'].quantile(0.90), 1)
            }
        },
        "by_outcome": {}
    }

    # Plays per drive by outcome
    for outcome in ['Touchdown', 'Field goal', 'Punt', 'Turnover', 'Turnover on downs', 'End of half']:
        outcome_drives = drive_plays[drive_plays['result'] == outcome]
        if len(outcome_drives) > 50:
            results["plays_per_drive"]["by_outcome"][outcome.lower().replace(' ', '_')] = {
                "mean": round(outcome_drives['plays'].mean(), 2),
                "median": round(outcome_drives['plays'].median(), 1),
                "count": len(outcome_drives)
            }

    # === TIME PER PLAY ===
    print("Analyzing time per play...")

    # Filter plays with valid time data
    timed_plays = scrimmage[
        (scrimmage['play_clock'].notna()) &
        (scrimmage['game_seconds_remaining'].notna())
    ].copy()

    # Calculate time elapsed between plays (approximation)
    # Using game_seconds_remaining difference within same drive
    timed_plays = timed_plays.sort_values(['game_id', 'play_id'])
    timed_plays['time_elapsed'] = timed_plays.groupby(['game_id', 'drive'])['game_seconds_remaining'].diff(-1)
    timed_plays = timed_plays[timed_plays['time_elapsed'] > 0]  # Remove negative/zero
    timed_plays = timed_plays[timed_plays['time_elapsed'] < 120]  # Cap at 2 minutes (removes quarter breaks)

    results["time_per_play"] = {
        "overall": {
            "mean": round(timed_plays['time_elapsed'].mean(), 1),
            "median": round(timed_plays['time_elapsed'].median(), 1),
            "std": round(timed_plays['time_elapsed'].std(), 1)
        },
        "by_play_type": {}
    }

    # Time by play type
    for play_type in ['pass', 'run']:
        type_plays = timed_plays[timed_plays['play_type'] == play_type]
        if len(type_plays) > 100:
            results["time_per_play"]["by_play_type"][play_type] = {
                "mean": round(type_plays['time_elapsed'].mean(), 1),
                "median": round(type_plays['time_elapsed'].median(), 1)
            }

    # Time by completion result
    complete_plays = timed_plays[(timed_plays['play_type'] == 'pass') & (timed_plays['complete_pass'] == 1)]
    incomplete_plays = timed_plays[(timed_plays['play_type'] == 'pass') & (timed_plays['incomplete_pass'] == 1)]

    if len(complete_plays) > 100:
        results["time_per_play"]["by_play_type"]["complete_pass"] = {
            "mean": round(complete_plays['time_elapsed'].mean(), 1),
            "median": round(complete_plays['time_elapsed'].median(), 1)
        }

    if len(incomplete_plays) > 100:
        results["time_per_play"]["by_play_type"]["incomplete_pass"] = {
            "mean": round(incomplete_plays['time_elapsed'].mean(), 1),
            "median": round(incomplete_plays['time_elapsed'].median(), 1),
            "note": "Clock stops on incomplete"
        }

    # === PASS/RUN RATIO ===
    print("Analyzing pass/run ratio...")

    pass_plays = len(scrimmage[scrimmage['play_type'] == 'pass'])
    run_plays = len(scrimmage[scrimmage['play_type'] == 'run'])
    total_scrimmage = pass_plays + run_plays

    results["pass_run_ratio"] = {
        "pass_rate": round(pass_plays / total_scrimmage, 4),
        "run_rate": round(run_plays / total_scrimmage, 4),
        "pass_plays": pass_plays,
        "run_plays": run_plays
    }

    # === SCORING ===
    print("Analyzing scoring patterns...")

    # Points per game
    game_scores = pbp.groupby('game_id').agg({
        'home_score': 'max',
        'away_score': 'max'
    })
    game_scores['total_points'] = game_scores['home_score'] + game_scores['away_score']
    game_scores['winning_margin'] = abs(game_scores['home_score'] - game_scores['away_score'])

    results["scoring"] = {
        "points_per_game": {
            "mean": round(game_scores['total_points'].mean(), 1),
            "median": round(game_scores['total_points'].median(), 1)
        },
        "points_per_team": {
            "mean": round(game_scores['total_points'].mean() / 2, 1),
            "median": round(game_scores['total_points'].median() / 2, 1)
        },
        "winning_margin": {
            "mean": round(game_scores['winning_margin'].mean(), 1),
            "median": round(game_scores['winning_margin'].median(), 1)
        }
    }

    # === FIRST DOWNS ===
    print("Analyzing first downs...")

    first_downs = scrimmage[scrimmage['first_down'] == 1]
    fd_per_game = first_downs.groupby('game_id').size()
    fd_per_team = first_downs.groupby(['game_id', 'posteam']).size()

    results["first_downs"] = {
        "per_game": {
            "mean": round(fd_per_game.mean(), 1),
            "median": round(fd_per_game.median(), 1)
        },
        "per_team_per_game": {
            "mean": round(fd_per_team.mean(), 1),
            "median": round(fd_per_team.median(), 1)
        },
        "by_type": {
            "passing": len(scrimmage[(scrimmage['first_down_pass'] == 1)]),
            "rushing": len(scrimmage[(scrimmage['first_down_rush'] == 1)]),
            "penalty": len(scrimmage[(scrimmage['first_down_penalty'] == 1)])
        }
    }

    # Calculate percentages
    total_fd = sum(results["first_downs"]["by_type"].values())
    results["first_downs"]["by_type_pct"] = {
        "passing": round(results["first_downs"]["by_type"]["passing"] / total_fd, 4),
        "rushing": round(results["first_downs"]["by_type"]["rushing"] / total_fd, 4),
        "penalty": round(results["first_downs"]["by_type"]["penalty"] / total_fd, 4)
    }

    # === TURNOVERS ===
    print("Analyzing turnovers...")

    interceptions = scrimmage[scrimmage['interception'] == 1]
    fumbles_lost = scrimmage[scrimmage['fumble_lost'] == 1]

    int_per_game = interceptions.groupby('game_id').size()
    fum_per_game = fumbles_lost.groupby('game_id').size()

    results["turnovers"] = {
        "interceptions_per_game": {
            "mean": round(int_per_game.mean(), 2),
            "median": round(int_per_game.median(), 1)
        },
        "fumbles_lost_per_game": {
            "mean": round(fum_per_game.mean(), 2),
            "median": round(fum_per_game.median(), 1)
        },
        "total_turnovers_per_game": {
            "mean": round(int_per_game.mean() + fum_per_game.mean(), 2)
        }
    }

    # === IMPLEMENTATION HINTS ===
    results["implementation_hints"] = {
        "game_simulation": """
def simulate_game_flow():
    '''
    Typical NFL game structure:
    - ~130 scrimmage plays total (~65 per team)
    - ~24 drives total (~12 per team)
    - ~5.4 plays per drive
    - ~40 seconds between plays
    - ~46 points total (~23 per team)
    '''
    plays_per_team = random.gauss(65, 8)
    drives_per_team = random.gauss(12, 1.5)
    plays_per_drive = plays_per_team / drives_per_team
    return plays_per_team, drives_per_team, plays_per_drive
""",
        "clock_management": """
def time_off_clock(play_type: str, is_complete: bool) -> int:
    '''
    Time elapsed per play (seconds):
    - Run play: ~42 seconds
    - Complete pass: ~42 seconds
    - Incomplete pass: ~28 seconds (clock stops)
    '''
    if play_type == 'run':
        return random.gauss(42, 8)
    elif is_complete:
        return random.gauss(42, 8)
    else:
        return random.gauss(28, 6)  # Clock stops, faster snap
"""
    }

    return convert_to_native(results)


def main():
    results = analyze_game_flow()

    # Save JSON export
    export_path = Path("research/exports/game_flow_model.json")
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {export_path}")

    # Generate markdown report
    report = f"""# NFL Game Flow Analysis

**Source:** nfl_data_py play-by-play data
**Seasons:** 2019-2024

---

## Plays Per Game

| Metric | Value |
|--------|-------|
| Mean | {results['plays_per_game']['mean']} |
| Median | {results['plays_per_game']['median']} |
| Std Dev | {results['plays_per_game']['std']} |
| Range | {results['plays_per_game']['min']} - {results['plays_per_game']['max']} |

**Per Team:** {results['plays_per_team_per_game']['mean']} plays/team/game (median: {results['plays_per_team_per_game']['median']})

---

## Drives Per Game

| Metric | Total | Per Team |
|--------|-------|----------|
| Mean | {results['drives_per_game']['mean']} | {results['drives_per_team_per_game']['mean']} |
| Median | {results['drives_per_game']['median']} | {results['drives_per_team_per_game']['median']} |

---

## Plays Per Drive

| Overall | Value |
|---------|-------|
| Mean | {results['plays_per_drive']['overall']['mean']} |
| Median | {results['plays_per_drive']['overall']['median']} |

**By Outcome:**
"""

    for outcome, stats in results['plays_per_drive']['by_outcome'].items():
        report += f"- {outcome.replace('_', ' ').title()}: {stats['mean']} plays (n={stats['count']})\n"

    report += f"""
---

## Time Per Play

| Play Type | Mean (sec) | Median (sec) |
|-----------|------------|--------------|
| Overall | {results['time_per_play']['overall']['mean']} | {results['time_per_play']['overall']['median']} |
| Run | {results['time_per_play']['by_play_type']['run']['mean']} | {results['time_per_play']['by_play_type']['run']['median']} |
| Pass | {results['time_per_play']['by_play_type']['pass']['mean']} | {results['time_per_play']['by_play_type']['pass']['median']} |
| Complete Pass | {results['time_per_play']['by_play_type']['complete_pass']['mean']} | {results['time_per_play']['by_play_type']['complete_pass']['median']} |
| Incomplete Pass | {results['time_per_play']['by_play_type']['incomplete_pass']['mean']} | {results['time_per_play']['by_play_type']['incomplete_pass']['median']} |

---

## Pass/Run Ratio

- **Pass Rate:** {results['pass_run_ratio']['pass_rate']*100:.1f}%
- **Run Rate:** {results['pass_run_ratio']['run_rate']*100:.1f}%

---

## Scoring

| Metric | Mean | Median |
|--------|------|--------|
| Points Per Game | {results['scoring']['points_per_game']['mean']} | {results['scoring']['points_per_game']['median']} |
| Points Per Team | {results['scoring']['points_per_team']['mean']} | {results['scoring']['points_per_team']['median']} |
| Winning Margin | {results['scoring']['winning_margin']['mean']} | {results['scoring']['winning_margin']['median']} |

---

## First Downs

- **Per Game:** {results['first_downs']['per_game']['mean']} (median: {results['first_downs']['per_game']['median']})
- **Per Team:** {results['first_downs']['per_team_per_game']['mean']} (median: {results['first_downs']['per_team_per_game']['median']})

**By Type:**
- Passing: {results['first_downs']['by_type_pct']['passing']*100:.1f}%
- Rushing: {results['first_downs']['by_type_pct']['rushing']*100:.1f}%
- Penalty: {results['first_downs']['by_type_pct']['penalty']*100:.1f}%

---

## Turnovers

- **Interceptions/Game:** {results['turnovers']['interceptions_per_game']['mean']}
- **Fumbles Lost/Game:** {results['turnovers']['fumbles_lost_per_game']['mean']}
- **Total Turnovers/Game:** {results['turnovers']['total_turnovers_per_game']['mean']}

---

*Generated by researcher_agent for game_layer_agent*
"""

    report_path = Path("research/reports/game_flow_analysis.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"Saved: {report_path}")

    # Print summary
    print("\n" + "="*50)
    print("GAME FLOW SUMMARY")
    print("="*50)
    print(f"Plays per game: {results['plays_per_game']['mean']} (median: {results['plays_per_game']['median']})")
    print(f"Plays per team: {results['plays_per_team_per_game']['mean']}")
    print(f"Drives per game: {results['drives_per_game']['mean']}")
    print(f"Drives per team: {results['drives_per_team_per_game']['mean']}")
    print(f"Plays per drive: {results['plays_per_drive']['overall']['mean']}")
    print(f"Time per play: {results['time_per_play']['overall']['mean']} seconds")
    print(f"Pass rate: {results['pass_run_ratio']['pass_rate']*100:.1f}%")
    print(f"Points per game: {results['scoring']['points_per_game']['mean']}")


if __name__ == "__main__":
    main()
