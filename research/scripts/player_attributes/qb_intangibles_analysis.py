"""
QB Intangibles Analysis

Extracts measurable proxies for QB intangible qualities:
1. Clutch - 4th quarter, 2-minute drill, close game performance
2. Poise - Resistance to pressure effects
3. Decision-making - Situational INT patterns
4. Anticipation - Time-to-throw efficiency
5. Pocket presence - Sack avoidance when pressured
6. Aggressiveness - Tight window throwing
7. Consistency - Game-to-game variance
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "cached"
EXPORT_DIR = Path(__file__).parent.parent / "exports"
REPORT_DIR = Path(__file__).parent.parent / "reports" / "calibration"

def convert_to_native(obj):
    """Convert numpy types to native Python for JSON serialization."""
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
    elif pd.isna(obj):
        return None
    return obj

def load_data():
    """Load PBP and NGS data."""
    print("Loading data...")
    pbp = pd.read_parquet(DATA_DIR / "pbp_2019_2024.parquet")

    # Filter to pass plays
    passes = pbp[
        (pbp['play_type'] == 'pass') &
        (pbp['passer_id'].notna()) &
        (pbp['air_yards'].notna())
    ].copy()

    # Load NGS passing data
    ngs = pd.read_parquet(DATA_DIR / "ngs_passing.parquet")

    print(f"  Pass plays: {len(passes):,}")
    print(f"  NGS records: {len(ngs):,}")

    return passes, ngs


def analyze_clutch(passes):
    """
    Analyze clutch performance - how QBs perform when stakes are highest.

    Situations:
    - 4th quarter
    - 2-minute drill (final 2 min of half)
    - Close games (within 8 points)
    - Comeback situations (trailing in 4th)
    """
    print("\n=== CLUTCH PERFORMANCE ===")

    # Define clutch situations
    passes = passes.copy()
    passes['is_4th_quarter'] = passes['qtr'] == 4
    passes['is_2min_drill'] = (
        ((passes['qtr'] == 2) & (passes['game_seconds_remaining'] <= 120 + 1800)) |  # End of 2nd
        ((passes['qtr'] == 4) & (passes['game_seconds_remaining'] <= 120))  # End of 4th
    )
    passes['is_close_game'] = abs(passes['score_differential']) <= 8
    passes['is_trailing_4th'] = (passes['qtr'] == 4) & (passes['score_differential'] < 0)
    passes['is_clutch'] = (
        passes['is_4th_quarter'] &
        passes['is_close_game']
    )

    # Calculate per-QB stats in clutch vs normal
    qb_clutch = []

    for passer_id in passes['passer_id'].unique():
        qb_plays = passes[passes['passer_id'] == passer_id]

        if len(qb_plays) < 200:  # Min sample
            continue

        passer_name = qb_plays['passer'].iloc[0]

        # Normal situations
        normal = qb_plays[~qb_plays['is_clutch']]
        clutch = qb_plays[qb_plays['is_clutch']]
        trailing_4th = qb_plays[qb_plays['is_trailing_4th']]
        two_min = qb_plays[qb_plays['is_2min_drill']]

        if len(clutch) < 30:  # Need enough clutch plays
            continue

        normal_comp = normal['complete_pass'].mean()
        clutch_comp = clutch['complete_pass'].mean()

        normal_epa = normal['epa'].mean()
        clutch_epa = clutch['epa'].mean()

        qb_clutch.append({
            'passer': passer_name,
            'passer_id': passer_id,
            'total_plays': len(qb_plays),
            'clutch_plays': len(clutch),
            'normal_comp_pct': normal_comp,
            'clutch_comp_pct': clutch_comp,
            'clutch_comp_diff': clutch_comp - normal_comp,
            'normal_epa': normal_epa,
            'clutch_epa': clutch_epa,
            'clutch_epa_diff': clutch_epa - normal_epa,
            'trailing_4th_plays': len(trailing_4th),
            'trailing_4th_epa': trailing_4th['epa'].mean() if len(trailing_4th) > 20 else None,
            'two_min_plays': len(two_min),
            'two_min_comp_pct': two_min['complete_pass'].mean() if len(two_min) > 20 else None,
        })

    clutch_df = pd.DataFrame(qb_clutch)
    clutch_df = clutch_df.sort_values('clutch_epa_diff', ascending=False)

    print(f"\nQBs analyzed: {len(clutch_df)}")
    print(f"\nTop 10 Clutch Performers (EPA diff in clutch situations):")
    print(clutch_df[['passer', 'clutch_plays', 'clutch_comp_diff', 'clutch_epa_diff']].head(10).to_string(index=False))

    print(f"\nBottom 10 Clutch Performers:")
    print(clutch_df[['passer', 'clutch_plays', 'clutch_comp_diff', 'clutch_epa_diff']].tail(10).to_string(index=False))

    # League-wide clutch effect
    all_normal = passes[~passes['is_clutch']]
    all_clutch = passes[passes['is_clutch']]

    league_clutch = {
        'normal_comp_pct': all_normal['complete_pass'].mean(),
        'clutch_comp_pct': all_clutch['complete_pass'].mean(),
        'normal_epa': all_normal['epa'].mean(),
        'clutch_epa': all_clutch['epa'].mean(),
        'clutch_plays_pct': len(all_clutch) / len(passes),
    }

    print(f"\nLeague-wide clutch effect:")
    print(f"  Normal completion: {league_clutch['normal_comp_pct']:.1%}")
    print(f"  Clutch completion: {league_clutch['clutch_comp_pct']:.1%}")
    print(f"  Normal EPA: {league_clutch['normal_epa']:.3f}")
    print(f"  Clutch EPA: {league_clutch['clutch_epa']:.3f}")

    return {
        'qb_clutch_stats': clutch_df.to_dict('records'),
        'league_clutch': league_clutch,
        'clutch_spread': {
            'best_epa_diff': clutch_df['clutch_epa_diff'].max(),
            'worst_epa_diff': clutch_df['clutch_epa_diff'].min(),
            'std_epa_diff': clutch_df['clutch_epa_diff'].std(),
        }
    }


def analyze_poise(passes):
    """
    Analyze poise - how much pressure affects each QB vs league average.

    A poised QB maintains performance under pressure.
    Measured as: (QB pressure penalty) vs (League avg pressure penalty)
    """
    print("\n=== POISE (Pressure Resilience) ===")

    # Need pressure data
    if 'was_pressure' not in passes.columns:
        print("  No pressure data available, using sack proxy")
        passes = passes.copy()
        passes['was_pressure'] = passes['sack'] == 1

    # League average pressure effect
    clean = passes[passes['was_pressure'] == False]
    pressured = passes[passes['was_pressure'] == True]

    league_clean_comp = clean['complete_pass'].mean()
    league_pressure_comp = pressured['complete_pass'].mean()
    league_pressure_penalty = league_clean_comp - league_pressure_comp

    print(f"\nLeague pressure effect:")
    print(f"  Clean pocket: {league_clean_comp:.1%}")
    print(f"  Under pressure: {league_pressure_comp:.1%}")
    print(f"  Pressure penalty: {league_pressure_penalty:.1%}")

    # Per-QB pressure resilience
    qb_poise = []

    for passer_id in passes['passer_id'].unique():
        qb_plays = passes[passes['passer_id'] == passer_id]

        if len(qb_plays) < 200:
            continue

        passer_name = qb_plays['passer'].iloc[0]

        qb_clean = qb_plays[qb_plays['was_pressure'] == False]
        qb_pressured = qb_plays[qb_plays['was_pressure'] == True]

        if len(qb_pressured) < 30:
            continue

        clean_comp = qb_clean['complete_pass'].mean()
        pressure_comp = qb_pressured['complete_pass'].mean()
        pressure_penalty = clean_comp - pressure_comp

        # Poise = how much BETTER than league avg under pressure
        # Positive = more resilient than average
        poise_score = league_pressure_penalty - pressure_penalty

        qb_poise.append({
            'passer': passer_name,
            'passer_id': passer_id,
            'total_plays': len(qb_plays),
            'pressure_plays': len(qb_pressured),
            'pressure_rate': len(qb_pressured) / len(qb_plays),
            'clean_comp_pct': clean_comp,
            'pressure_comp_pct': pressure_comp,
            'pressure_penalty': pressure_penalty,
            'poise_score': poise_score,  # Positive = poised, negative = rattled
        })

    poise_df = pd.DataFrame(qb_poise)
    poise_df = poise_df.sort_values('poise_score', ascending=False)

    print(f"\nTop 10 Most Poised QBs (smallest pressure penalty vs league):")
    print(poise_df[['passer', 'pressure_plays', 'pressure_penalty', 'poise_score']].head(10).to_string(index=False))

    print(f"\nBottom 10 (Most Rattled by Pressure):")
    print(poise_df[['passer', 'pressure_plays', 'pressure_penalty', 'poise_score']].tail(10).to_string(index=False))

    return {
        'qb_poise_stats': poise_df.to_dict('records'),
        'league_pressure_penalty': league_pressure_penalty,
        'poise_spread': {
            'best_poise': poise_df['poise_score'].max(),
            'worst_poise': poise_df['poise_score'].min(),
            'std_poise': poise_df['poise_score'].std(),
        }
    }


def analyze_decision_making(passes):
    """
    Analyze decision-making - situational INT patterns.

    Good decision-makers:
    - Lower INT rate on short/safe throws
    - Avoid INTs when trailing (desperation)
    - Lower INT rate in red zone (don't force it)
    """
    print("\n=== DECISION-MAKING (INT Patterns) ===")

    passes = passes.copy()
    passes['is_interception'] = passes['interception'] == 1

    # Situational INT analysis
    situations = {
        'short': passes['air_yards'] < 10,
        'medium': (passes['air_yards'] >= 10) & (passes['air_yards'] < 20),
        'deep': passes['air_yards'] >= 20,
        'trailing': passes['score_differential'] < 0,
        'leading': passes['score_differential'] > 7,
        'red_zone': passes['yardline_100'] <= 20,
        'third_down': passes['down'] == 3,
    }

    print("\nLeague INT rates by situation:")
    for name, mask in situations.items():
        subset = passes[mask]
        int_rate = subset['is_interception'].mean()
        print(f"  {name}: {int_rate:.2%} ({len(subset):,} plays)")

    # Per-QB decision score
    qb_decisions = []

    for passer_id in passes['passer_id'].unique():
        qb_plays = passes[passes['passer_id'] == passer_id]

        if len(qb_plays) < 300:
            continue

        passer_name = qb_plays['passer'].iloc[0]

        # Overall INT rate
        overall_int = qb_plays['is_interception'].mean()

        # "Bad decision" INTs - short throws shouldn't be picked
        short_plays = qb_plays[qb_plays['air_yards'] < 10]
        short_int = short_plays['is_interception'].mean() if len(short_plays) > 50 else None

        # Desperation INTs - trailing late
        trailing_late = qb_plays[(qb_plays['score_differential'] < -7) & (qb_plays['qtr'] >= 4)]
        desperation_int = trailing_late['is_interception'].mean() if len(trailing_late) > 20 else None

        # Red zone discipline
        rz_plays = qb_plays[qb_plays['yardline_100'] <= 20]
        rz_int = rz_plays['is_interception'].mean() if len(rz_plays) > 30 else None

        # Decision score: lower INT rates = better decisions
        # Weight short throws heavily (those are real mistakes)
        decision_score = 0
        components = 0
        if short_int is not None:
            decision_score += (0.015 - short_int) * 100  # League avg ~1.5%
            components += 1
        if rz_int is not None:
            decision_score += (0.02 - rz_int) * 50  # RZ avg ~2%
            components += 1

        if components > 0:
            decision_score /= components

        qb_decisions.append({
            'passer': passer_name,
            'passer_id': passer_id,
            'total_plays': len(qb_plays),
            'overall_int_rate': overall_int,
            'short_int_rate': short_int,
            'desperation_int_rate': desperation_int,
            'red_zone_int_rate': rz_int,
            'decision_score': decision_score,
        })

    decisions_df = pd.DataFrame(qb_decisions)
    decisions_df = decisions_df.sort_values('decision_score', ascending=False)

    print(f"\nTop 10 Decision-Makers (low INT on short/RZ throws):")
    cols = ['passer', 'overall_int_rate', 'short_int_rate', 'red_zone_int_rate', 'decision_score']
    print(decisions_df[cols].head(10).to_string(index=False))

    print(f"\nBottom 10 Decision-Makers:")
    print(decisions_df[cols].tail(10).to_string(index=False))

    return {
        'qb_decision_stats': decisions_df.to_dict('records'),
        'league_int_by_situation': {name: passes[mask]['is_interception'].mean() for name, mask in situations.items()},
        'decision_spread': {
            'best': decisions_df['decision_score'].max(),
            'worst': decisions_df['decision_score'].min(),
            'std': decisions_df['decision_score'].std(),
        }
    }


def analyze_anticipation(passes, ngs):
    """
    Analyze anticipation - throwing before receiver breaks.

    Measured by time-to-throw on completions.
    Great anticipators complete passes with LESS time.
    """
    print("\n=== ANTICIPATION (Time-to-Throw Efficiency) ===")

    # NGS has avg_time_to_throw
    if 'avg_time_to_throw' not in ngs.columns:
        print("  No time_to_throw data in NGS")
        return None

    # Get QB seasons with time to throw
    qb_seasons = ngs.groupby(['player_display_name', 'season']).agg({
        'avg_time_to_throw': 'mean',
        'attempts': 'sum',
        'completions': 'sum',
        'completion_percentage': 'mean',
        'avg_air_yards_to_sticks': 'mean',
    }).reset_index()

    qb_seasons = qb_seasons[qb_seasons['attempts'] >= 200]

    # Anticipation = completing passes with less time
    # Need to control for depth (deeper throws take longer)

    # Simple metric: completion % relative to time
    # Higher completion with lower time = better anticipation

    avg_ttt = qb_seasons['avg_time_to_throw'].mean()
    avg_comp = qb_seasons['completion_percentage'].mean()

    # Anticipation score: completion above avg, time below avg
    qb_seasons['time_vs_avg'] = avg_ttt - qb_seasons['avg_time_to_throw']  # Positive = faster
    qb_seasons['comp_vs_avg'] = qb_seasons['completion_percentage'] - avg_comp  # Positive = better
    qb_seasons['anticipation_score'] = qb_seasons['time_vs_avg'] * 10 + qb_seasons['comp_vs_avg']

    # Career averages
    qb_career = qb_seasons.groupby('player_display_name').agg({
        'avg_time_to_throw': 'mean',
        'completion_percentage': 'mean',
        'attempts': 'sum',
        'anticipation_score': 'mean',
    }).reset_index()

    qb_career = qb_career[qb_career['attempts'] >= 500]
    qb_career = qb_career.sort_values('anticipation_score', ascending=False)

    print(f"\nLeague avg time to throw: {avg_ttt:.2f}s")
    print(f"League avg completion: {avg_comp:.1f}%")

    print(f"\nTop 10 Anticipators (high completion with quick release):")
    cols = ['player_display_name', 'avg_time_to_throw', 'completion_percentage', 'anticipation_score']
    print(qb_career[cols].head(10).to_string(index=False))

    print(f"\nBottom 10 (slow processing):")
    print(qb_career[cols].tail(10).to_string(index=False))

    # Time to throw distribution
    ttt_dist = {
        'mean': qb_seasons['avg_time_to_throw'].mean(),
        'std': qb_seasons['avg_time_to_throw'].std(),
        'min': qb_seasons['avg_time_to_throw'].min(),
        'max': qb_seasons['avg_time_to_throw'].max(),
        'p10': qb_seasons['avg_time_to_throw'].quantile(0.1),
        'p90': qb_seasons['avg_time_to_throw'].quantile(0.9),
    }

    return {
        'qb_anticipation_stats': qb_career.to_dict('records'),
        'time_to_throw_distribution': ttt_dist,
        'anticipation_spread': {
            'best': qb_career['anticipation_score'].max(),
            'worst': qb_career['anticipation_score'].min(),
            'std': qb_career['anticipation_score'].std(),
        }
    }


def analyze_pocket_presence(passes):
    """
    Analyze pocket presence - avoiding sacks when pressured.

    Good pocket presence = low sack rate even with high pressure.
    Measured as: sacks / pressures (or sacks / dropbacks as proxy)
    """
    print("\n=== POCKET PRESENCE (Sack Avoidance) ===")

    # Per-QB sack analysis
    qb_pocket = []

    for passer_id in passes['passer_id'].unique():
        qb_plays = passes[passes['passer_id'] == passer_id]

        if len(qb_plays) < 200:
            continue

        passer_name = qb_plays['passer'].iloc[0]

        dropbacks = len(qb_plays)
        sacks = qb_plays['sack'].sum()
        sack_rate = sacks / dropbacks

        # If we have pressure data
        if 'was_pressure' in qb_plays.columns:
            pressures = qb_plays['was_pressure'].sum()
            pressure_rate = pressures / dropbacks
            sack_per_pressure = sacks / pressures if pressures > 0 else 0
        else:
            pressure_rate = None
            sack_per_pressure = None

        # Scrambles (escaping pressure)
        scrambles = qb_plays['qb_scramble'].sum() if 'qb_scramble' in qb_plays.columns else 0
        scramble_rate = scrambles / dropbacks

        qb_pocket.append({
            'passer': passer_name,
            'passer_id': passer_id,
            'dropbacks': dropbacks,
            'sacks': sacks,
            'sack_rate': sack_rate,
            'pressure_rate': pressure_rate,
            'sack_per_pressure': sack_per_pressure,
            'scramble_rate': scramble_rate,
            # Lower sack rate = better pocket presence
            'pocket_presence_score': (0.05 - sack_rate) * 100,  # League avg ~5%
        })

    pocket_df = pd.DataFrame(qb_pocket)
    pocket_df = pocket_df.sort_values('pocket_presence_score', ascending=False)

    league_sack_rate = passes['sack'].mean()
    print(f"\nLeague avg sack rate: {league_sack_rate:.1%}")

    print(f"\nTop 10 Pocket Presence (lowest sack rate):")
    cols = ['passer', 'dropbacks', 'sack_rate', 'scramble_rate', 'pocket_presence_score']
    print(pocket_df[cols].head(10).to_string(index=False))

    print(f"\nBottom 10 (highest sack rate):")
    print(pocket_df[cols].tail(10).to_string(index=False))

    return {
        'qb_pocket_stats': pocket_df.to_dict('records'),
        'league_sack_rate': league_sack_rate,
        'pocket_presence_spread': {
            'best_sack_rate': pocket_df['sack_rate'].min(),
            'worst_sack_rate': pocket_df['sack_rate'].max(),
            'std_sack_rate': pocket_df['sack_rate'].std(),
        }
    }


def analyze_aggressiveness(ngs):
    """
    Analyze aggressiveness - willingness to throw into tight windows.

    NGS tracks "aggressiveness" directly.
    Also look at avg_air_yards and deep ball attempts.
    """
    print("\n=== AGGRESSIVENESS (Tight Window Throwing) ===")

    if 'aggressiveness' not in ngs.columns:
        print("  No aggressiveness data in NGS")
        return None

    # QB seasons
    qb_seasons = ngs.groupby(['player_display_name', 'season']).agg({
        'aggressiveness': 'mean',
        'avg_intended_air_yards': 'mean',
        'attempts': 'sum',
        'completion_percentage': 'mean',
        'passer_rating': 'mean',
    }).reset_index()

    qb_seasons = qb_seasons[qb_seasons['attempts'] >= 200]

    # Career averages
    qb_career = qb_seasons.groupby('player_display_name').agg({
        'aggressiveness': 'mean',
        'avg_intended_air_yards': 'mean',
        'completion_percentage': 'mean',
        'passer_rating': 'mean',
        'attempts': 'sum',
    }).reset_index()

    qb_career = qb_career[qb_career['attempts'] >= 500]
    qb_career = qb_career.sort_values('aggressiveness', ascending=False)

    print(f"\nLeague avg aggressiveness: {qb_seasons['aggressiveness'].mean():.1f}%")
    print(f"League avg intended air yards: {qb_seasons['avg_intended_air_yards'].mean():.1f}")

    print(f"\nTop 10 Most Aggressive QBs:")
    cols = ['player_display_name', 'aggressiveness', 'avg_intended_air_yards', 'completion_percentage']
    print(qb_career[cols].head(10).to_string(index=False))

    print(f"\nMost Conservative QBs:")
    print(qb_career[cols].tail(10).to_string(index=False))

    # Correlation: does aggressiveness hurt completion %?
    corr = qb_seasons['aggressiveness'].corr(qb_seasons['completion_percentage'])
    print(f"\nCorrelation (aggressiveness vs completion %): {corr:.3f}")

    return {
        'qb_aggressiveness_stats': qb_career.to_dict('records'),
        'league_avg_aggressiveness': qb_seasons['aggressiveness'].mean(),
        'aggressiveness_completion_correlation': corr,
        'aggressiveness_spread': {
            'most_aggressive': qb_career['aggressiveness'].max(),
            'least_aggressive': qb_career['aggressiveness'].min(),
            'std': qb_career['aggressiveness'].std(),
        }
    }


def analyze_consistency(passes):
    """
    Analyze consistency - game-to-game variance.

    Consistent QBs have low variance in their performance.
    """
    print("\n=== CONSISTENCY (Game-to-Game Variance) ===")

    # Game-level stats per QB
    game_stats = passes.groupby(['passer_id', 'passer', 'game_id']).agg({
        'complete_pass': ['sum', 'count', 'mean'],
        'epa': ['sum', 'mean'],
        'air_yards': 'mean',
    }).reset_index()

    game_stats.columns = ['passer_id', 'passer', 'game_id',
                          'completions', 'attempts', 'comp_pct',
                          'total_epa', 'epa_per_play', 'avg_air_yards']

    # Filter to games with enough attempts
    game_stats = game_stats[game_stats['attempts'] >= 15]

    # Per-QB consistency (coefficient of variation)
    qb_consistency = []

    for passer_id in game_stats['passer_id'].unique():
        qb_games = game_stats[game_stats['passer_id'] == passer_id]

        if len(qb_games) < 10:  # Need enough games
            continue

        passer_name = qb_games['passer'].iloc[0]

        # Coefficient of variation (std/mean) - lower = more consistent
        comp_cv = qb_games['comp_pct'].std() / qb_games['comp_pct'].mean() if qb_games['comp_pct'].mean() > 0 else float('inf')
        epa_std = qb_games['epa_per_play'].std()

        qb_consistency.append({
            'passer': passer_name,
            'passer_id': passer_id,
            'games': len(qb_games),
            'avg_comp_pct': qb_games['comp_pct'].mean(),
            'comp_pct_std': qb_games['comp_pct'].std(),
            'comp_cv': comp_cv,
            'avg_epa': qb_games['epa_per_play'].mean(),
            'epa_std': epa_std,
            # Lower CV = more consistent = higher score
            'consistency_score': (0.15 - comp_cv) * 100 if comp_cv < 0.3 else -10,
        })

    consistency_df = pd.DataFrame(qb_consistency)
    consistency_df = consistency_df.sort_values('consistency_score', ascending=False)

    league_cv = game_stats.groupby('passer_id')['comp_pct'].std().mean()
    print(f"\nLeague avg completion % std (game-to-game): {league_cv:.1%}")

    print(f"\nTop 10 Most Consistent QBs (lowest game-to-game variance):")
    cols = ['passer', 'games', 'avg_comp_pct', 'comp_pct_std', 'consistency_score']
    print(consistency_df[cols].head(10).to_string(index=False))

    print(f"\nMost Inconsistent QBs:")
    print(consistency_df[cols].tail(10).to_string(index=False))

    return {
        'qb_consistency_stats': consistency_df.to_dict('records'),
        'league_avg_game_variance': league_cv,
        'consistency_spread': {
            'most_consistent_cv': consistency_df['comp_cv'].min(),
            'least_consistent_cv': consistency_df['comp_cv'].max(),
            'std_cv': consistency_df['comp_cv'].std(),
        }
    }


def create_composite_intangibles(clutch_data, poise_data, decision_data,
                                  anticipation_data, pocket_data,
                                  aggression_data, consistency_data):
    """
    Create composite intangibles scores per QB.
    """
    print("\n=== COMPOSITE INTANGIBLES ===")

    # Collect all QBs
    all_qbs = {}

    # Clutch
    if clutch_data:
        for qb in clutch_data['qb_clutch_stats']:
            name = qb['passer']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['clutch_score'] = qb['clutch_epa_diff']

    # Poise
    if poise_data:
        for qb in poise_data['qb_poise_stats']:
            name = qb['passer']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['poise_score'] = qb['poise_score']

    # Decision-making
    if decision_data:
        for qb in decision_data['qb_decision_stats']:
            name = qb['passer']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['decision_score'] = qb['decision_score']

    # Anticipation
    if anticipation_data:
        for qb in anticipation_data['qb_anticipation_stats']:
            name = qb['player_display_name']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['anticipation_score'] = qb['anticipation_score']

    # Pocket presence
    if pocket_data:
        for qb in pocket_data['qb_pocket_stats']:
            name = qb['passer']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['pocket_score'] = qb['pocket_presence_score']

    # Consistency
    if consistency_data:
        for qb in consistency_data['qb_consistency_stats']:
            name = qb['passer']
            if name not in all_qbs:
                all_qbs[name] = {'passer': name}
            all_qbs[name]['consistency_score'] = qb['consistency_score']

    # Calculate composite
    composite_df = pd.DataFrame(list(all_qbs.values()))

    # Normalize each score to 0-100 scale
    score_cols = ['clutch_score', 'poise_score', 'decision_score',
                  'anticipation_score', 'pocket_score', 'consistency_score']

    for col in score_cols:
        if col in composite_df.columns:
            min_val = composite_df[col].min()
            max_val = composite_df[col].max()
            if max_val > min_val:
                composite_df[f'{col}_norm'] = (composite_df[col] - min_val) / (max_val - min_val) * 100
            else:
                composite_df[f'{col}_norm'] = 50

    # Composite = average of available normalized scores
    norm_cols = [f'{col}_norm' for col in score_cols if f'{col}_norm' in composite_df.columns]
    composite_df['composite_intangibles'] = composite_df[norm_cols].mean(axis=1)

    composite_df = composite_df.sort_values('composite_intangibles', ascending=False)

    print(f"\nTop 15 QBs by Composite Intangibles:")
    display_cols = ['passer', 'composite_intangibles'] + [c for c in score_cols if c in composite_df.columns]
    print(composite_df[display_cols].head(15).to_string(index=False))

    return composite_df.to_dict('records')


def main():
    """Run all intangibles analyses."""

    passes, ngs = load_data()

    # Run all analyses
    clutch_data = analyze_clutch(passes)
    poise_data = analyze_poise(passes)
    decision_data = analyze_decision_making(passes)
    anticipation_data = analyze_anticipation(passes, ngs)
    pocket_data = analyze_pocket_presence(passes)
    aggression_data = analyze_aggressiveness(ngs)
    consistency_data = analyze_consistency(passes)

    # Composite scores
    composite = create_composite_intangibles(
        clutch_data, poise_data, decision_data,
        anticipation_data, pocket_data,
        aggression_data, consistency_data
    )

    # Compile results
    results = {
        'clutch': clutch_data,
        'poise': poise_data,
        'decision_making': decision_data,
        'anticipation': anticipation_data,
        'pocket_presence': pocket_data,
        'aggressiveness': aggression_data,
        'consistency': consistency_data,
        'composite_rankings': composite,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "qb_intangibles_analysis.json"

    with open(export_path, 'w') as f:
        json.dump(convert_to_native(results), f, indent=2)

    print(f"\n\nExported to: {export_path}")

    return results


if __name__ == "__main__":
    results = main()
