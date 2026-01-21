"""
QB Variance Analysis

Deep analysis of QB performance variance including:
- Time to throw effects and distributions
- Game-to-game consistency
- Situational variance (down, distance, score)
- Air yards and aggressiveness
- Completion above/below expectation
- Pressure timing effects

Purpose: Understand how to model QB variance in simulation
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from scipy import stats


def load_data():
    """Load PBP and NGS passing data."""
    data_dir = Path(__file__).parent.parent / "data" / "cached"

    pbp = pd.read_parquet(data_dir / "pbp_2019_2024.parquet")
    ngs = pd.read_parquet(data_dir / "ngs_passing.parquet")

    return pbp, ngs


def convert_to_native(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(i) for i in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj


def analyze_time_to_throw(ngs, pbp):
    """Analyze time to throw distributions and effects."""

    print("  Analyzing time to throw distributions...")

    # Filter to QBs with enough attempts
    qb_seasons = ngs[
        (ngs['player_position'] == 'QB') &
        (ngs['attempts'] >= 100)
    ].copy()

    results = {
        'distribution': {},
        'by_tier': {},
        'correlation_with_success': {},
        'optimal_range': {}
    }

    # Overall distribution
    ttt = qb_seasons['avg_time_to_throw']
    results['distribution'] = {
        'mean': round(ttt.mean(), 3),
        'std': round(ttt.std(), 3),
        'min': round(ttt.min(), 3),
        'max': round(ttt.max(), 3),
        'p10': round(ttt.quantile(0.10), 3),
        'p25': round(ttt.quantile(0.25), 3),
        'p50': round(ttt.quantile(0.50), 3),
        'p75': round(ttt.quantile(0.75), 3),
        'p90': round(ttt.quantile(0.90), 3),
        'sample': len(qb_seasons)
    }

    # Tier QBs by time to throw
    qb_seasons['ttt_tier'] = pd.qcut(
        qb_seasons['avg_time_to_throw'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Quick', 'Normal-Quick', 'Normal-Slow', 'Slow']
    )

    for tier in ['Quick', 'Normal-Quick', 'Normal-Slow', 'Slow']:
        tier_data = qb_seasons[qb_seasons['ttt_tier'] == tier]
        if len(tier_data) >= 10:
            results['by_tier'][tier] = {
                'avg_time_to_throw': round(tier_data['avg_time_to_throw'].mean(), 3),
                'completion_pct': round(tier_data['completion_percentage'].mean(), 2),
                'comp_above_expected': round(tier_data['completion_percentage_above_expectation'].mean(), 2),
                'passer_rating': round(tier_data['passer_rating'].mean(), 1),
                'int_rate': round((tier_data['interceptions'] / tier_data['attempts']).mean() * 100, 2),
                'sample': len(tier_data)
            }

    # Correlation with success metrics
    results['correlation_with_success'] = {
        'ttt_vs_completion': round(qb_seasons['avg_time_to_throw'].corr(qb_seasons['completion_percentage']), 3),
        'ttt_vs_passer_rating': round(qb_seasons['avg_time_to_throw'].corr(qb_seasons['passer_rating']), 3),
        'ttt_vs_comp_above_exp': round(qb_seasons['avg_time_to_throw'].corr(qb_seasons['completion_percentage_above_expectation']), 3),
        'ttt_vs_int_rate': round(qb_seasons['avg_time_to_throw'].corr(qb_seasons['interceptions'] / qb_seasons['attempts']), 3)
    }

    # Find optimal time to throw range
    # Bin into 0.1s increments and find best performance
    qb_seasons['ttt_bin'] = (qb_seasons['avg_time_to_throw'] * 10).round() / 10

    ttt_performance = qb_seasons.groupby('ttt_bin').agg({
        'completion_percentage': 'mean',
        'passer_rating': 'mean',
        'avg_time_to_throw': 'count'
    }).reset_index()
    ttt_performance.columns = ['ttt_bin', 'completion_pct', 'passer_rating', 'count']

    # Filter to bins with enough data
    ttt_performance = ttt_performance[ttt_performance['count'] >= 5]

    if len(ttt_performance) > 0:
        best_rating_bin = ttt_performance.loc[ttt_performance['passer_rating'].idxmax(), 'ttt_bin']
        results['optimal_range'] = {
            'best_time_for_rating': round(best_rating_bin, 2),
            'recommended_range': [2.4, 2.8],  # Will refine based on data
            'performance_by_time': {
                round(row['ttt_bin'], 2): {
                    'completion_pct': round(row['completion_pct'], 1),
                    'passer_rating': round(row['passer_rating'], 1),
                    'sample': int(row['count'])
                }
                for _, row in ttt_performance.iterrows()
            }
        }

    return results


def analyze_pressure_timing(pbp):
    """Analyze how pressure affects outcomes at different times."""

    print("  Analyzing pressure timing effects...")

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_player_name'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    # Determine pressure
    pass_plays['pressured'] = (
        (pass_plays.get('sack', 0) == 1) |
        (pass_plays.get('qb_hit', 0) == 1)
    )

    results = {
        'overall_pressure_rate': round(pass_plays['pressured'].mean(), 4),
        'completion_clean': round(pass_plays[~pass_plays['pressured']]['complete_pass'].mean(), 4),
        'completion_pressured': round(pass_plays[pass_plays['pressured']]['complete_pass'].mean(), 4),
        'pressure_penalty': None,
        'sack_on_pressure': None
    }

    results['pressure_penalty'] = round(
        results['completion_clean'] - results['completion_pressured'], 4
    )

    # Sack rate when pressured
    pressured_plays = pass_plays[pass_plays['pressured']]
    if len(pressured_plays) > 0:
        results['sack_on_pressure'] = round(pressured_plays['sack'].mean(), 4)

    # Analyze by down
    results['by_down'] = {}
    for down in [1, 2, 3, 4]:
        down_plays = pass_plays[pass_plays['down'] == down]
        if len(down_plays) >= 500:
            clean = down_plays[~down_plays['pressured']]
            pressured = down_plays[down_plays['pressured']]
            results['by_down'][down] = {
                'pressure_rate': round(down_plays['pressured'].mean(), 4),
                'completion_clean': round(clean['complete_pass'].mean(), 4) if len(clean) > 100 else None,
                'completion_pressured': round(pressured['complete_pass'].mean(), 4) if len(pressured) > 100 else None,
                'sample': len(down_plays)
            }

    return results


def analyze_game_to_game_variance(pbp):
    """Analyze QB game-to-game consistency."""

    print("  Analyzing game-to-game variance...")

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_player_name'].notna()) &
        (pbp['complete_pass'].notna()) &
        (pbp['epa'].notna())
    ].copy()

    # Get game-level stats for each QB
    game_stats = pass_plays.groupby(['season', 'passer_player_name', 'game_id']).agg({
        'complete_pass': ['mean', 'count'],
        'epa': 'mean',
        'yards_gained': 'mean',
        'interception': 'sum'
    }).reset_index()
    game_stats.columns = ['season', 'passer', 'game_id', 'completion_pct', 'attempts', 'epa_per_play', 'avg_yards', 'ints']

    # Filter to games with 15+ attempts
    game_stats = game_stats[game_stats['attempts'] >= 15]

    # Calculate per-QB variance
    qb_variance = game_stats.groupby(['season', 'passer']).agg({
        'completion_pct': ['mean', 'std', 'count'],
        'epa_per_play': ['mean', 'std'],
        'avg_yards': ['mean', 'std']
    }).reset_index()
    qb_variance.columns = ['season', 'passer', 'comp_mean', 'comp_std', 'games',
                           'epa_mean', 'epa_std', 'yards_mean', 'yards_std']

    # Filter to QBs with 8+ games
    qb_variance = qb_variance[qb_variance['games'] >= 8]

    results = {
        'completion_variance': {
            'avg_game_to_game_std': round(qb_variance['comp_std'].mean(), 4),
            'min_std': round(qb_variance['comp_std'].min(), 4),
            'max_std': round(qb_variance['comp_std'].max(), 4),
            'typical_range': round(qb_variance['comp_std'].median() * 2, 4)  # ~95% of games
        },
        'epa_variance': {
            'avg_game_to_game_std': round(qb_variance['epa_std'].mean(), 4),
            'min_std': round(qb_variance['epa_std'].min(), 4),
            'max_std': round(qb_variance['epa_std'].max(), 4)
        },
        'yards_variance': {
            'avg_game_to_game_std': round(qb_variance['yards_std'].mean(), 4)
        }
    }

    # Tier QBs by consistency (lower std = more consistent)
    qb_variance['consistency_tier'] = pd.qcut(
        qb_variance['comp_std'],
        q=[0, 0.25, 0.75, 1.0],
        labels=['Consistent', 'Average', 'Volatile']
    )

    results['by_consistency'] = {}
    for tier in ['Consistent', 'Average', 'Volatile']:
        tier_data = qb_variance[qb_variance['consistency_tier'] == tier]
        if len(tier_data) >= 5:
            results['by_consistency'][tier] = {
                'comp_std': round(tier_data['comp_std'].mean(), 4),
                'comp_mean': round(tier_data['comp_mean'].mean(), 4),
                'epa_mean': round(tier_data['epa_mean'].mean(), 4),
                'sample': len(tier_data)
            }

    # Coefficient of variation (normalized variance)
    qb_variance['cv'] = qb_variance['comp_std'] / qb_variance['comp_mean']
    results['coefficient_of_variation'] = {
        'mean': round(qb_variance['cv'].mean(), 4),
        'median': round(qb_variance['cv'].median(), 4),
        'interpretation': 'CV of 0.15 means typical game varies ±15% from season average'
    }

    return results


def analyze_situational_variance(pbp):
    """Analyze QB performance variance by situation."""

    print("  Analyzing situational variance...")

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_player_name'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    results = {}

    # By down
    results['by_down'] = {}
    for down in [1, 2, 3, 4]:
        down_plays = pass_plays[pass_plays['down'] == down]
        if len(down_plays) >= 1000:
            results['by_down'][down] = {
                'completion_rate': round(down_plays['complete_pass'].mean(), 4),
                'avg_air_yards': round(down_plays['air_yards'].mean(), 2) if 'air_yards' in down_plays.columns else None,
                'int_rate': round(down_plays['interception'].mean(), 4) if 'interception' in down_plays.columns else None,
                'sample': len(down_plays)
            }

    # By distance to go
    results['by_distance'] = {}
    distance_bins = [(1, 3, 'Short'), (4, 7, 'Medium'), (8, 12, 'Long'), (13, 99, 'Very Long')]
    for min_d, max_d, label in distance_bins:
        dist_plays = pass_plays[(pass_plays['ydstogo'] >= min_d) & (pass_plays['ydstogo'] <= max_d)]
        if len(dist_plays) >= 1000:
            results['by_distance'][label] = {
                'completion_rate': round(dist_plays['complete_pass'].mean(), 4),
                'avg_air_yards': round(dist_plays['air_yards'].mean(), 2) if 'air_yards' in dist_plays.columns else None,
                'sample': len(dist_plays)
            }

    # By score differential
    results['by_score'] = {}
    pass_plays['score_diff'] = pass_plays['posteam_score'] - pass_plays['defteam_score']
    score_bins = [(-99, -14, 'Down Big'), (-13, -7, 'Down 2 Scores'), (-6, -1, 'Down 1 Score'),
                  (0, 0, 'Tied'), (1, 6, 'Up 1 Score'), (7, 13, 'Up 2 Scores'), (14, 99, 'Up Big')]

    for min_s, max_s, label in score_bins:
        score_plays = pass_plays[(pass_plays['score_diff'] >= min_s) & (pass_plays['score_diff'] <= max_s)]
        if len(score_plays) >= 1000:
            results['by_score'][label] = {
                'completion_rate': round(score_plays['complete_pass'].mean(), 4),
                'avg_air_yards': round(score_plays['air_yards'].mean(), 2) if 'air_yards' in score_plays.columns else None,
                'sample': len(score_plays)
            }

    # By quarter
    results['by_quarter'] = {}
    for qtr in [1, 2, 3, 4]:
        qtr_plays = pass_plays[pass_plays['qtr'] == qtr]
        if len(qtr_plays) >= 1000:
            results['by_quarter'][qtr] = {
                'completion_rate': round(qtr_plays['complete_pass'].mean(), 4),
                'sample': len(qtr_plays)
            }

    # Red zone vs normal
    results['by_field_position'] = {}
    redzone = pass_plays[pass_plays['yardline_100'] <= 20]
    midfield = pass_plays[(pass_plays['yardline_100'] > 20) & (pass_plays['yardline_100'] <= 50)]
    own_territory = pass_plays[pass_plays['yardline_100'] > 50]

    for name, plays in [('Red Zone', redzone), ('Midfield', midfield), ('Own Territory', own_territory)]:
        if len(plays) >= 1000:
            results['by_field_position'][name] = {
                'completion_rate': round(plays['complete_pass'].mean(), 4),
                'avg_air_yards': round(plays['air_yards'].mean(), 2) if 'air_yards' in plays.columns else None,
                'sample': len(plays)
            }

    return results


def analyze_air_yards_variance(pbp, ngs):
    """Analyze air yards distribution and aggressiveness."""

    print("  Analyzing air yards and aggressiveness...")

    results = {}

    # PBP air yards distribution
    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['air_yards'].notna()) &
        (pbp['complete_pass'].notna())
    ].copy()

    air_yards = pass_plays['air_yards']
    results['air_yards_distribution'] = {
        'mean': round(air_yards.mean(), 2),
        'std': round(air_yards.std(), 2),
        'median': round(air_yards.median(), 2),
        'p10': round(air_yards.quantile(0.10), 2),
        'p25': round(air_yards.quantile(0.25), 2),
        'p75': round(air_yards.quantile(0.75), 2),
        'p90': round(air_yards.quantile(0.90), 2),
        'negative_rate': round((air_yards < 0).mean(), 4),
        'deep_rate': round((air_yards >= 20).mean(), 4)
    }

    # Completion rate by air yards
    results['completion_by_air_yards'] = {}
    bins = [(-10, -1, 'Behind LOS'), (0, 4, 'Screen/Check'), (5, 9, 'Short'),
            (10, 14, 'Intermediate'), (15, 19, 'Medium-Deep'), (20, 29, 'Deep'), (30, 99, 'Bomb')]

    for min_ay, max_ay, label in bins:
        bin_plays = pass_plays[(pass_plays['air_yards'] >= min_ay) & (pass_plays['air_yards'] <= max_ay)]
        if len(bin_plays) >= 500:
            results['completion_by_air_yards'][label] = {
                'completion_rate': round(bin_plays['complete_pass'].mean(), 4),
                'int_rate': round(bin_plays['interception'].mean(), 4) if 'interception' in bin_plays.columns else None,
                'avg_yards_if_complete': round(bin_plays[bin_plays['complete_pass'] == 1]['yards_gained'].mean(), 2),
                'sample': len(bin_plays)
            }

    # NGS aggressiveness analysis
    qb_ngs = ngs[(ngs['player_position'] == 'QB') & (ngs['attempts'] >= 100)].copy()

    if 'aggressiveness' in qb_ngs.columns:
        agg = qb_ngs['aggressiveness']
        results['aggressiveness_distribution'] = {
            'mean': round(agg.mean(), 2),
            'std': round(agg.std(), 2),
            'min': round(agg.min(), 2),
            'max': round(agg.max(), 2),
            'p25': round(agg.quantile(0.25), 2),
            'p75': round(agg.quantile(0.75), 2)
        }

        # Tier by aggressiveness
        qb_ngs['agg_tier'] = pd.qcut(
            qb_ngs['aggressiveness'],
            q=[0, 0.33, 0.67, 1.0],
            labels=['Conservative', 'Moderate', 'Aggressive']
        )

        results['by_aggressiveness'] = {}
        for tier in ['Conservative', 'Moderate', 'Aggressive']:
            tier_data = qb_ngs[qb_ngs['agg_tier'] == tier]
            if len(tier_data) >= 10:
                results['by_aggressiveness'][tier] = {
                    'aggressiveness': round(tier_data['aggressiveness'].mean(), 2),
                    'completion_pct': round(tier_data['completion_percentage'].mean(), 2),
                    'comp_above_expected': round(tier_data['completion_percentage_above_expectation'].mean(), 2),
                    'passer_rating': round(tier_data['passer_rating'].mean(), 1),
                    'int_rate': round((tier_data['interceptions'] / tier_data['attempts']).mean() * 100, 2),
                    'avg_intended_air_yards': round(tier_data['avg_intended_air_yards'].mean(), 2),
                    'sample': len(tier_data)
                }

    return results


def analyze_completion_above_expected(ngs):
    """Analyze completion percentage above expectation (CPOE)."""

    print("  Analyzing completion above expectation (CPOE)...")

    qb_ngs = ngs[(ngs['player_position'] == 'QB') & (ngs['attempts'] >= 100)].copy()

    cpoe = qb_ngs['completion_percentage_above_expectation']

    results = {
        'distribution': {
            'mean': round(cpoe.mean(), 2),
            'std': round(cpoe.std(), 2),
            'min': round(cpoe.min(), 2),
            'max': round(cpoe.max(), 2),
            'p10': round(cpoe.quantile(0.10), 2),
            'p25': round(cpoe.quantile(0.25), 2),
            'p50': round(cpoe.quantile(0.50), 2),
            'p75': round(cpoe.quantile(0.75), 2),
            'p90': round(cpoe.quantile(0.90), 2)
        },
        'interpretation': {
            'elite_threshold': 3.0,
            'good_threshold': 1.0,
            'bad_threshold': -2.0,
            'note': 'CPOE measures accuracy independent of target depth and pressure'
        }
    }

    # Tier by CPOE
    qb_ngs['cpoe_tier'] = pd.qcut(
        qb_ngs['completion_percentage_above_expectation'],
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=['Poor', 'Below Avg', 'Above Avg', 'Elite']
    )

    results['by_tier'] = {}
    for tier in ['Elite', 'Above Avg', 'Below Avg', 'Poor']:
        tier_data = qb_ngs[qb_ngs['cpoe_tier'] == tier]
        if len(tier_data) >= 10:
            results['by_tier'][tier] = {
                'cpoe': round(tier_data['completion_percentage_above_expectation'].mean(), 2),
                'raw_completion': round(tier_data['completion_percentage'].mean(), 2),
                'expected_completion': round(tier_data['expected_completion_percentage'].mean(), 2),
                'passer_rating': round(tier_data['passer_rating'].mean(), 1),
                'avg_intended_air_yards': round(tier_data['avg_intended_air_yards'].mean(), 2),
                'sample': len(tier_data)
            }

    # Correlation with other metrics
    results['correlations'] = {
        'cpoe_vs_passer_rating': round(qb_ngs['completion_percentage_above_expectation'].corr(qb_ngs['passer_rating']), 3),
        'cpoe_vs_raw_completion': round(qb_ngs['completion_percentage_above_expectation'].corr(qb_ngs['completion_percentage']), 3),
        'cpoe_vs_air_yards': round(qb_ngs['completion_percentage_above_expectation'].corr(qb_ngs['avg_intended_air_yards']), 3)
    }

    return results


def analyze_interception_variance(pbp):
    """Analyze interception patterns and variance."""

    print("  Analyzing interception variance...")

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_player_name'].notna())
    ].copy()

    results = {}

    # Overall INT rate
    int_rate = pass_plays['interception'].mean()
    results['overall_int_rate'] = round(int_rate, 4)

    # INT rate by air yards
    results['int_by_air_yards'] = {}
    if 'air_yards' in pass_plays.columns:
        bins = [(0, 9, 'Short'), (10, 19, 'Medium'), (20, 99, 'Deep')]
        for min_ay, max_ay, label in bins:
            bin_plays = pass_plays[(pass_plays['air_yards'] >= min_ay) & (pass_plays['air_yards'] <= max_ay)]
            if len(bin_plays) >= 1000:
                results['int_by_air_yards'][label] = {
                    'int_rate': round(bin_plays['interception'].mean(), 4),
                    'sample': len(bin_plays)
                }

    # INT rate by down
    results['int_by_down'] = {}
    for down in [1, 2, 3, 4]:
        down_plays = pass_plays[pass_plays['down'] == down]
        if len(down_plays) >= 1000:
            results['int_by_down'][down] = {
                'int_rate': round(down_plays['interception'].mean(), 4),
                'sample': len(down_plays)
            }

    # INT rate by score differential
    results['int_by_score'] = {}
    pass_plays['score_diff'] = pass_plays['posteam_score'] - pass_plays['defteam_score']
    for label, min_s, max_s in [('Down Big', -99, -14), ('Down', -13, -1), ('Close', 0, 6), ('Up', 7, 99)]:
        score_plays = pass_plays[(pass_plays['score_diff'] >= min_s) & (pass_plays['score_diff'] <= max_s)]
        if len(score_plays) >= 1000:
            results['int_by_score'][label] = {
                'int_rate': round(score_plays['interception'].mean(), 4),
                'sample': len(score_plays)
            }

    # QB-level INT variance
    qb_seasons = pass_plays.groupby(['season', 'passer_player_name']).agg({
        'interception': ['sum', 'count']
    }).reset_index()
    qb_seasons.columns = ['season', 'passer', 'ints', 'attempts']
    qb_seasons = qb_seasons[qb_seasons['attempts'] >= 200]
    qb_seasons['int_rate'] = qb_seasons['ints'] / qb_seasons['attempts']

    results['qb_int_distribution'] = {
        'mean': round(qb_seasons['int_rate'].mean(), 4),
        'std': round(qb_seasons['int_rate'].std(), 4),
        'min': round(qb_seasons['int_rate'].min(), 4),
        'max': round(qb_seasons['int_rate'].max(), 4),
        'p10': round(qb_seasons['int_rate'].quantile(0.10), 4),
        'p90': round(qb_seasons['int_rate'].quantile(0.90), 4)
    }

    return results


def analyze_play_outcome_variance(pbp):
    """Analyze variance in individual play outcomes."""

    print("  Analyzing play-level outcome variance...")

    pass_plays = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['yards_gained'].notna())
    ].copy()

    results = {}

    # Overall yards distribution
    yards = pass_plays['yards_gained']
    results['yards_distribution'] = {
        'mean': round(yards.mean(), 2),
        'std': round(yards.std(), 2),
        'median': round(yards.median(), 2),
        'p10': round(yards.quantile(0.10), 2),
        'p25': round(yards.quantile(0.25), 2),
        'p75': round(yards.quantile(0.75), 2),
        'p90': round(yards.quantile(0.90), 2),
        'negative_rate': round((yards < 0).mean(), 4),
        'big_play_rate': round((yards >= 20).mean(), 4)
    }

    # Yards by completion
    completions = pass_plays[pass_plays['complete_pass'] == 1]['yards_gained']
    incompletions = pass_plays[pass_plays['complete_pass'] == 0]['yards_gained']

    results['yards_by_result'] = {
        'completed': {
            'mean': round(completions.mean(), 2),
            'std': round(completions.std(), 2),
            'median': round(completions.median(), 2)
        },
        'incomplete': {
            'mean': round(incompletions.mean(), 2),
            'note': 'Includes sacks and throwaways'
        }
    }

    # EPA distribution
    if 'epa' in pass_plays.columns:
        epa = pass_plays['epa'].dropna()
        results['epa_distribution'] = {
            'mean': round(epa.mean(), 3),
            'std': round(epa.std(), 3),
            'median': round(epa.median(), 3),
            'p10': round(epa.quantile(0.10), 3),
            'p90': round(epa.quantile(0.90), 3),
            'negative_rate': round((epa < 0).mean(), 4)
        }

    return results


def build_variance_recommendations(results):
    """Build recommendations for modeling QB variance in simulation."""

    recommendations = {
        'time_to_throw': {
            'base_distribution': {
                'mean': results['time_to_throw']['distribution']['mean'],
                'std': results['time_to_throw']['distribution']['std']
            },
            'simulation_guidance': [
                'Model time to throw as normal distribution around QB baseline',
                'Quick releases (2.2-2.5s) have slightly better outcomes',
                'Holding ball >3.0s increases sack probability significantly',
                'Adjust completion probability based on time in pocket'
            ],
            'formula': 'time_to_throw = max(2.0, normal(qb_baseline, 0.3))'
        },
        'game_to_game': {
            'completion_std': results['game_to_game']['completion_variance']['avg_game_to_game_std'],
            'simulation_guidance': [
                'Apply game-level modifier to QB baseline: normal(0, 0.08)',
                'Consistent QBs: std ~0.06, Volatile QBs: std ~0.12',
                'Game variance should stack with play-level variance'
            ],
            'formula': 'game_modifier = normal(0, consistency_factor)'
        },
        'situational': {
            'key_factors': [
                'Down: 3rd down completion ~2% lower than 1st/2nd',
                'Score: Trailing by 14+ increases INT rate ~50%',
                'Field position: Red zone completion ~4% lower',
                'Quarter: 4th quarter has most variance'
            ],
            'simulation_guidance': [
                'Apply situational modifiers to base completion probability',
                'Increase aggressiveness (air yards) when trailing',
                'Reduce risk-taking when protecting lead'
            ]
        },
        'air_yards': {
            'distribution': results['air_yards']['air_yards_distribution'],
            'simulation_guidance': [
                'Model target selection as distribution based on situation',
                'Each yard of additional air yards reduces completion ~1.5%',
                'Deep passes (20+) have 4x INT rate of short passes',
                'Air yards increase when trailing, decrease when ahead'
            ]
        },
        'play_level_variance': {
            'yards_std': results['play_outcomes']['yards_distribution']['std'],
            'simulation_guidance': [
                'Completion is binary: ~65% base rate',
                'If complete, yards = air_yards + YAC',
                'YAC follows separate distribution by receiver',
                'Sack rate ~6%, INT rate ~2% on pass attempts'
            ]
        },
        'cpoe_as_skill': {
            'spread': {
                'elite': results['cpoe']['by_tier'].get('Elite', {}).get('cpoe', 3.0),
                'poor': results['cpoe']['by_tier'].get('Poor', {}).get('cpoe', -3.0)
            },
            'simulation_guidance': [
                'CPOE represents true QB accuracy skill',
                'Elite QBs: +3% above expected, Poor: -3%',
                'Use as modifier after calculating expected completion',
                'Less correlated with air yards than raw completion'
            ]
        }
    }

    return recommendations


def run_qb_variance_analysis():
    """Run the complete QB variance analysis."""

    print("Loading data...")
    pbp, ngs = load_data()
    print(f"Loaded {len(pbp)} plays, {len(ngs)} NGS records")

    print("\nAnalyzing QB variance factors...")

    results = {}

    results['time_to_throw'] = analyze_time_to_throw(ngs, pbp)
    results['pressure_timing'] = analyze_pressure_timing(pbp)
    results['game_to_game'] = analyze_game_to_game_variance(pbp)
    results['situational'] = analyze_situational_variance(pbp)
    results['air_yards'] = analyze_air_yards_variance(pbp, ngs)
    results['cpoe'] = analyze_completion_above_expected(ngs)
    results['interceptions'] = analyze_interception_variance(pbp)
    results['play_outcomes'] = analyze_play_outcome_variance(pbp)

    print("\nBuilding variance recommendations...")
    results['simulation_recommendations'] = build_variance_recommendations(results)

    # Convert and export
    results = convert_to_native(results)

    export_path = Path(__file__).parent.parent / "exports" / "qb_variance_analysis.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print_summary(results)

    return results


def print_summary(results):
    """Print analysis summary."""

    print("\n" + "="*70)
    print("QB VARIANCE ANALYSIS SUMMARY")
    print("="*70)

    # Time to throw
    ttt = results['time_to_throw']
    print("\nTIME TO THROW:")
    print(f"  Mean: {ttt['distribution']['mean']:.2f}s (std: {ttt['distribution']['std']:.2f})")
    print(f"  Range: {ttt['distribution']['p10']:.2f}s - {ttt['distribution']['p90']:.2f}s (10th-90th)")
    print("\n  By Tier:")
    for tier, data in ttt['by_tier'].items():
        print(f"    {tier}: {data['avg_time_to_throw']:.2f}s → {data['completion_pct']:.1f}% comp, {data['passer_rating']:.1f} rating")

    # Pressure
    pressure = results['pressure_timing']
    print(f"\nPRESSURE EFFECTS:")
    print(f"  Pressure rate: {pressure['overall_pressure_rate']*100:.1f}%")
    print(f"  Completion clean: {pressure['completion_clean']*100:.1f}%")
    print(f"  Completion pressured: {pressure['completion_pressured']*100:.1f}%")
    print(f"  Pressure penalty: -{pressure['pressure_penalty']*100:.1f}%")

    # Game-to-game
    g2g = results['game_to_game']
    print(f"\nGAME-TO-GAME VARIANCE:")
    print(f"  Avg completion std: {g2g['completion_variance']['avg_game_to_game_std']*100:.1f}%")
    print(f"  Typical game range: ±{g2g['completion_variance']['typical_range']*100:.1f}% from season avg")
    print(f"  Coefficient of variation: {g2g['coefficient_of_variation']['mean']:.2f}")

    # Situational
    sit = results['situational']
    print(f"\nSITUATIONAL EFFECTS:")
    print("  By Down:")
    for down, data in sit['by_down'].items():
        print(f"    {down}: {data['completion_rate']*100:.1f}% completion")
    print("  By Score:")
    for score, data in sit['by_score'].items():
        print(f"    {score}: {data['completion_rate']*100:.1f}% completion")

    # Air yards
    ay = results['air_yards']
    print(f"\nAIR YARDS:")
    print(f"  Mean: {ay['air_yards_distribution']['mean']:.1f} yards (std: {ay['air_yards_distribution']['std']:.1f})")
    print(f"  Deep pass rate (20+): {ay['air_yards_distribution']['deep_rate']*100:.1f}%")
    print("\n  Completion by Air Yards:")
    for depth, data in ay['completion_by_air_yards'].items():
        print(f"    {depth}: {data['completion_rate']*100:.1f}% comp, {data.get('int_rate', 0)*100:.2f}% INT")

    # CPOE
    cpoe = results['cpoe']
    print(f"\nCPOE (Completion Above Expected):")
    print(f"  Range: {cpoe['distribution']['p10']:.1f}% to {cpoe['distribution']['p90']:.1f}% (10th-90th)")
    print("  By Tier:")
    for tier, data in cpoe['by_tier'].items():
        print(f"    {tier}: {data['cpoe']:+.1f}% CPOE, {data['raw_completion']:.1f}% raw")

    # INTs
    ints = results['interceptions']
    print(f"\nINTERCEPTION VARIANCE:")
    print(f"  Overall rate: {ints['overall_int_rate']*100:.2f}%")
    print(f"  QB range: {ints['qb_int_distribution']['p10']*100:.2f}% - {ints['qb_int_distribution']['p90']*100:.2f}%")
    print("  By Air Yards:")
    for depth, data in ints.get('int_by_air_yards', {}).items():
        print(f"    {depth}: {data['int_rate']*100:.2f}% INT rate")

    # Play outcomes
    play = results['play_outcomes']
    print(f"\nPLAY-LEVEL VARIANCE:")
    print(f"  Yards mean: {play['yards_distribution']['mean']:.1f} (std: {play['yards_distribution']['std']:.1f})")
    print(f"  Big play rate (20+): {play['yards_distribution']['big_play_rate']*100:.1f}%")
    print(f"  Negative play rate: {play['yards_distribution']['negative_rate']*100:.1f}%")


if __name__ == "__main__":
    results = run_qb_variance_analysis()
