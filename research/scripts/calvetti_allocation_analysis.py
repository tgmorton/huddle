#!/usr/bin/env python3
"""
Calvetti-Style Salary Cap Allocation Analysis

Implements the framework from Calvetti (2023) MIT thesis:
- Separate salary-to-performance regressions for rookies/veterans
- Effective salary conversion
- Performance regression with position interaction terms
- Greedy and global optimization for cap allocation

Extended to include defensive positions.

References:
- Calvetti, P.G. (2023). "Optimizing the Allocation of Capital Among Offensive Positions in the NFL"
"""

import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import json
import warnings
warnings.filterwarnings('ignore')

# Optional imports for optimization and regression
try:
    from scipy.optimize import minimize
    from scipy.stats import pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Paths
RESEARCH_DIR = Path(__file__).parent.parent
DATA_DIR = RESEARCH_DIR / "data"
CACHED_DIR = DATA_DIR / "cached"
EXPORTS_DIR = RESEARCH_DIR / "exports"
REPORTS_DIR = RESEARCH_DIR / "reports"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Team Name Standardization
# =============================================================================
# Map all team name variants to standard 2-3 letter abbreviations

TEAM_NAME_MAP = {
    # Full nicknames → abbreviations
    '49ers': 'SF', 'Bears': 'CHI', 'Bengals': 'CIN', 'Bills': 'BUF',
    'Broncos': 'DEN', 'Browns': 'CLE', 'Buccaneers': 'TB', 'Cardinals': 'ARI',
    'Chargers': 'LAC', 'Chiefs': 'KC', 'Colts': 'IND', 'Commanders': 'WAS',
    'Cowboys': 'DAL', 'Dolphins': 'MIA', 'Eagles': 'PHI', 'Falcons': 'ATL',
    'Giants': 'NYG', 'Jaguars': 'JAX', 'Jets': 'NYJ', 'Lions': 'DET',
    'Packers': 'GB', 'Panthers': 'CAR', 'Patriots': 'NE', 'Raiders': 'LV',
    'Rams': 'LA', 'Ravens': 'BAL', 'Saints': 'NO', 'Seahawks': 'SEA',
    'Steelers': 'PIT', 'Texans': 'HOU', 'Titans': 'TEN', 'Vikings': 'MIN',
    'Redskins': 'WAS', 'Washington': 'WAS',
    # LA → LAR for consistency (Rams)
    'LA': 'LA', 'LAR': 'LA',
    # Already abbreviations
    'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CAR': 'CAR',
    'CHI': 'CHI', 'CIN': 'CIN', 'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN',
    'DET': 'DET', 'GB': 'GB', 'HOU': 'HOU', 'IND': 'IND', 'JAX': 'JAX',
    'KC': 'KC', 'LAC': 'LAC', 'LV': 'LV', 'MIA': 'MIA', 'MIN': 'MIN',
    'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ', 'PHI': 'PHI',
    'PIT': 'PIT', 'SEA': 'SEA', 'SF': 'SF', 'TB': 'TB', 'TEN': 'TEN',
    'WAS': 'WAS',
}


def standardize_team_name(team: str) -> str:
    """Convert any team name variant to standard abbreviation."""
    if not team or pd.isna(team):
        return None
    # Handle compound names like "ARI/BAL" - take first team
    if '/' in team:
        team = team.split('/')[0]
    return TEAM_NAME_MAP.get(team, team)


# =============================================================================
# Position Groups
# =============================================================================

OFFENSIVE_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'OL']
DEFENSIVE_POSITIONS = ['CB', 'S', 'LB', 'EDGE', 'DL']

# Detailed position mapping
POSITION_MAP = {
    # Offense
    'QB': 'QB',
    'RB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'LT': 'OL', 'RT': 'OL', 'LG': 'OL', 'RG': 'OL', 'C': 'OL', 'OT': 'OL', 'G': 'OL',
    # Defense
    'CB': 'CB',
    'S': 'S', 'FS': 'S', 'SS': 'S', 'DB': 'S',
    'LB': 'LB', 'ILB': 'LB', 'MLB': 'LB', 'OLB': 'LB',
    'ED': 'EDGE', 'EDGE': 'EDGE', 'DE': 'EDGE',
    'IDL': 'DL', 'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
}

# Interaction term sets (from Calvetti methodology)
# G0 = no interactions, G1 = basic, G2 = extended
OFFENSIVE_INTERACTIONS = {
    'G0': [],
    'G1': [('QB', 'WR'), ('RB', 'OL')],
    'G2': [('QB', 'WR'), ('RB', 'OL'), ('QB', 'TE')],
}

DEFENSIVE_INTERACTIONS = {
    'G0': [],
    'G1': [('CB', 'S'), ('EDGE', 'DL')],
    'G2': [('CB', 'S'), ('EDGE', 'DL'), ('CB', 'EDGE'), ('LB', 'DL')],
}


# =============================================================================
# Data Loading
# =============================================================================

def load_contracts() -> pd.DataFrame:
    """Load and flatten contract data with year-by-year cap hits."""
    print("Loading contracts...")

    contracts = pd.read_parquet(CACHED_DIR / "contracts.parquet")

    # Flatten the 'cols' column which contains year-by-year data
    rows = []
    for _, row in contracts.iterrows():
        cols_data = row.get('cols')
        if cols_data is None or (isinstance(cols_data, list) and len(cols_data) == 0):
            continue
        if isinstance(cols_data, float) and pd.isna(cols_data):
            continue

        player_info = {
            'player': row['player'],
            'position': row['position'],
            'team': row['team'],
            'draft_year': row.get('draft_year'),
            'draft_round': row.get('draft_round'),
            'gsis_id': row.get('gsis_id'),
        }

        for year_data in cols_data:
            if year_data.get('year') == 'Total':
                continue
            try:
                year = int(year_data['year'])
                cap_number = float(year_data.get('cap_number', 0) or 0)
                cap_percent = year_data.get('cap_percent')

                if cap_percent is not None:
                    cap_percent = float(cap_percent) * 100  # Convert to percentage

                # Standardize team name
                raw_team = year_data.get('team', row['team'])
                team_std = standardize_team_name(raw_team)

                rows.append({
                    **player_info,
                    'year': year,
                    'cap_hit': cap_number,
                    'cap_pct': cap_percent,
                    'team_that_year': team_std,
                })
            except (ValueError, TypeError):
                continue

    df = pd.DataFrame(rows)

    # Add position group
    df['position_group'] = df['position'].map(POSITION_MAP)
    df = df.dropna(subset=['position_group'])

    # Determine rookie vs veteran status
    # Rookie = within 4 years of draft
    df['years_since_draft'] = df['year'] - df['draft_year']
    df['is_rookie_contract'] = (df['years_since_draft'] >= 0) & (df['years_since_draft'] <= 4)

    print(f"  Loaded {len(df):,} player-year records")
    print(f"  Years: {df['year'].min()} - {df['year'].max()}")
    print(f"  Rookie contracts: {df['is_rookie_contract'].sum():,} ({df['is_rookie_contract'].mean()*100:.1f}%)")

    return df


def load_team_scoring() -> pd.DataFrame:
    """Compute team PPG and PAPG from play-by-play data."""
    print("Loading team scoring...")

    pbp = pd.read_parquet(CACHED_DIR / "pbp_2019_2024.parquet")

    # Get final scores per game
    game_scores = pbp.groupby(['game_id', 'season', 'home_team', 'away_team']).agg({
        'home_score': 'max',
        'away_score': 'max'
    }).reset_index()

    # Create team-level scoring records
    team_records = []

    for _, game in game_scores.iterrows():
        # Home team
        team_records.append({
            'team': game['home_team'],
            'year': game['season'],
            'points_for': game['home_score'],
            'points_against': game['away_score'],
        })
        # Away team
        team_records.append({
            'team': game['away_team'],
            'year': game['season'],
            'points_for': game['away_score'],
            'points_against': game['home_score'],
        })

    team_df = pd.DataFrame(team_records)

    # Aggregate to season level
    team_season = team_df.groupby(['team', 'year']).agg({
        'points_for': ['sum', 'count'],
        'points_against': 'sum'
    }).reset_index()

    team_season.columns = ['team', 'year', 'total_pf', 'games', 'total_pa']
    team_season['ppg'] = team_season['total_pf'] / team_season['games']
    team_season['papg'] = team_season['total_pa'] / team_season['games']

    print(f"  Loaded {len(team_season)} team-seasons")
    print(f"  Avg PPG: {team_season['ppg'].mean():.1f}")
    print(f"  Avg PAPG: {team_season['papg'].mean():.1f}")

    return team_season


def load_player_stats() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load player seasonal stats for performance metric."""
    print("Loading player stats...")

    # Offensive stats (fantasy points)
    offense_stats = pd.read_parquet(CACHED_DIR / "seasonal_stats.parquet")
    offense_stats = offense_stats.rename(columns={'season': 'year', 'player_id': 'gsis_id'})
    offense_stats['performance'] = offense_stats['fantasy_points'].fillna(0)
    print(f"  Loaded {len(offense_stats):,} offensive player-seasons")

    # Defensive stats (computed DV)
    dv_path = CACHED_DIR / "defensive_value.parquet"
    if dv_path.exists():
        defense_stats = pd.read_parquet(dv_path)
        defense_stats = defense_stats.rename(columns={'season': 'year', 'player_id': 'gsis_id'})
        defense_stats['performance'] = defense_stats['defensive_value'].fillna(0)
        print(f"  Loaded {len(defense_stats):,} defensive player-seasons")
    else:
        print("  Warning: No defensive_value.parquet found. Run compute_defensive_value.py first.")
        defense_stats = pd.DataFrame(columns=['gsis_id', 'year', 'performance'])

    return (
        offense_stats[['gsis_id', 'year', 'performance']],
        defense_stats[['gsis_id', 'year', 'performance']]
    )


# =============================================================================
# Data Aggregation
# =============================================================================

def aggregate_team_data(contracts: pd.DataFrame,
                        team_scoring: pd.DataFrame,
                        offense_stats: pd.DataFrame,
                        defense_stats: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregate all data to team-season-position level.

    Returns tuple of (offense_data, defense_data) DataFrames with columns:
    - team, year
    - position_group
    - cap_pct_rookie, cap_pct_veteran, cap_pct_total
    - performance_rookie, performance_veteran, performance_total
    - ppg, papg (team scoring)
    """
    print("Aggregating team data...")

    def aggregate_side(contracts_df, player_stats, positions, side_name):
        """Aggregate data for one side of the ball."""
        # Filter contracts to relevant positions
        side_contracts = contracts_df[contracts_df['position_group'].isin(positions)].copy()

        # Merge contracts with player performance
        merged = side_contracts.merge(
            player_stats,
            on=['gsis_id', 'year'],
            how='left'
        )

        # Fill missing performance with 0
        merged['performance'] = merged['performance'].fillna(0)

        # Aggregate by team-year-position-contract_type
        agg_data = []

        for (team, year, pos, is_rookie), group in merged.groupby(
            ['team_that_year', 'year', 'position_group', 'is_rookie_contract']
        ):
            agg_data.append({
                'team': team,
                'year': year,
                'position_group': pos,
                'is_rookie': is_rookie,
                'cap_pct': group['cap_pct'].sum(),
                'performance': group['performance'].sum(),
                'player_count': len(group),
            })

        if not agg_data:
            return pd.DataFrame()

        agg_df = pd.DataFrame(agg_data)

        # Pivot to get rookie/veteran columns
        pivot_cap = agg_df.pivot_table(
            index=['team', 'year', 'position_group'],
            columns='is_rookie',
            values='cap_pct',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        if True in pivot_cap.columns and False in pivot_cap.columns:
            pivot_cap.columns = ['team', 'year', 'position_group', 'cap_pct_veteran', 'cap_pct_rookie']
        else:
            pivot_cap['cap_pct_veteran'] = 0
            pivot_cap['cap_pct_rookie'] = 0

        pivot_perf = agg_df.pivot_table(
            index=['team', 'year', 'position_group'],
            columns='is_rookie',
            values='performance',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        if True in pivot_perf.columns and False in pivot_perf.columns:
            pivot_perf.columns = ['team', 'year', 'position_group', 'perf_veteran', 'perf_rookie']
        else:
            pivot_perf['perf_veteran'] = 0
            pivot_perf['perf_rookie'] = 0

        # Merge pivots
        result = pivot_cap.merge(pivot_perf, on=['team', 'year', 'position_group'])

        # Add totals
        result['cap_pct_total'] = result['cap_pct_rookie'] + result['cap_pct_veteran']
        result['perf_total'] = result['perf_rookie'] + result['perf_veteran']

        # Merge with team scoring
        result = result.merge(team_scoring[['team', 'year', 'ppg', 'papg']], on=['team', 'year'], how='left')

        print(f"  Created {len(result):,} {side_name} team-year-position records")
        return result

    # Aggregate offense and defense separately
    offense_data = aggregate_side(contracts, offense_stats, OFFENSIVE_POSITIONS, 'offense')
    defense_data = aggregate_side(contracts, defense_stats, DEFENSIVE_POSITIONS, 'defense')

    return offense_data, defense_data


# =============================================================================
# Calvetti Regressions
# =============================================================================

@dataclass
class RegressionResult:
    """Store regression results."""
    alpha0: float  # intercept
    alpha1: float  # log coefficient
    r_squared: float
    n_obs: int
    position: str
    contract_type: str  # 'rookie', 'veteran', or 'effective'


def fit_salary_to_performance(data: pd.DataFrame,
                               position: str,
                               contract_type: str) -> Optional[RegressionResult]:
    """
    Fit: Performance = α₀ + α₁ × log(1 + Salary)

    Following Calvetti equation 3.1/3.2
    """
    if contract_type == 'rookie':
        cap_col = 'cap_pct_rookie'
        perf_col = 'perf_rookie'
    else:
        cap_col = 'cap_pct_veteran'
        perf_col = 'perf_veteran'

    pos_data = data[data['position_group'] == position].copy()
    pos_data = pos_data[pos_data[cap_col] > 0]  # Need non-zero salary

    if len(pos_data) < 10:
        return None

    X = np.log1p(pos_data[cap_col])  # log(1 + salary)
    y = pos_data[perf_col]

    if HAS_STATSMODELS:
        X_const = sm.add_constant(X)
        model = sm.OLS(y, X_const).fit()
        return RegressionResult(
            alpha0=model.params.iloc[0],
            alpha1=model.params.iloc[1],
            r_squared=model.rsquared,
            n_obs=len(pos_data),
            position=position,
            contract_type=contract_type
        )
    else:
        # Simple fallback using numpy
        X_mat = np.column_stack([np.ones(len(X)), X])
        coeffs, residuals, rank, s = np.linalg.lstsq(X_mat, y, rcond=None)
        y_pred = X_mat @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return RegressionResult(
            alpha0=coeffs[0],
            alpha1=coeffs[1],
            r_squared=r_squared,
            n_obs=len(pos_data),
            position=position,
            contract_type=contract_type
        )


def compute_effective_salary_params(rookie_reg: RegressionResult,
                                     veteran_reg: RegressionResult) -> Dict:
    """
    Compute effective salary conversion parameters.

    From Calvetti equation 3.4:
    f(S_rookie) = exp((α₀ʳ - α₀ᵛ) / α₁ᵛ) × (1 + S_rookie)^(α₁ʳ/α₁ᵛ)
    """
    if veteran_reg.alpha1 == 0:
        return None

    multiplier = np.exp((rookie_reg.alpha0 - veteran_reg.alpha0) / veteran_reg.alpha1)
    exponent = rookie_reg.alpha1 / veteran_reg.alpha1

    return {
        'position': rookie_reg.position,
        'multiplier': multiplier,
        'exponent': exponent,
        'rookie_alpha0': rookie_reg.alpha0,
        'rookie_alpha1': rookie_reg.alpha1,
        'veteran_alpha0': veteran_reg.alpha0,
        'veteran_alpha1': veteran_reg.alpha1,
    }


def rookie_to_effective_salary(salary_rookie: float, params: Dict) -> float:
    """Convert rookie salary to effective (veteran-equivalent) salary."""
    if salary_rookie <= 0:
        return 0
    return params['multiplier'] * ((1 + salary_rookie) ** params['exponent'])


# =============================================================================
# Performance Model (PPG/PAPG from Position AV)
# =============================================================================

def fit_performance_model(data: pd.DataFrame,
                          positions: List[str],
                          interactions: List[Tuple[str, str]],
                          target: str = 'ppg') -> Dict:
    """
    Fit: PPG = β₀ + Σᵢ βᵢ×Perfᵢ + Σᵢⱼ βᵢⱼ×√(Perfᵢ×Perfⱼ)

    Following Calvetti equation 3.8
    """
    # Pivot data to have positions as columns
    pivot = data.pivot_table(
        index=['team', 'year'],
        columns='position_group',
        values='perf_total',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Filter to positions we care about
    available_positions = [p for p in positions if p in pivot.columns]

    # Get target variable
    target_df = data[['team', 'year', target]].drop_duplicates()
    pivot = pivot.merge(target_df, on=['team', 'year'])
    pivot = pivot.dropna(subset=[target])

    if len(pivot) < 20:
        print(f"  Warning: Only {len(pivot)} samples for {target} model")
        return None

    # Build feature matrix
    feature_cols = []

    # Main effects
    for pos in available_positions:
        feature_cols.append(pos)

    # Interaction terms
    for pos1, pos2 in interactions:
        if pos1 in available_positions and pos2 in available_positions:
            col_name = f'{pos1}_{pos2}_interaction'
            # Clip negative values to 0 before sqrt to avoid NaN
            product = pivot[pos1].clip(lower=0) * pivot[pos2].clip(lower=0)
            pivot[col_name] = np.sqrt(product)
            feature_cols.append(col_name)

    X = pivot[feature_cols]
    y = pivot[target]

    # Drop rows with NaN/inf values
    valid_mask = X.notna().all(axis=1) & y.notna() & np.isfinite(X).all(axis=1)
    X = X[valid_mask]
    y = y[valid_mask]

    if len(X) < 20:
        print(f"  Warning: Only {len(X)} valid samples for {target} model after NaN removal")
        return None

    if HAS_STATSMODELS:
        X_const = sm.add_constant(X)
        model = sm.OLS(y, X_const).fit()

        coefficients = {'intercept': model.params.iloc[0]}
        for i, col in enumerate(feature_cols):
            coefficients[col] = model.params.iloc[i + 1]

        return {
            'coefficients': coefficients,
            'r_squared': model.rsquared,
            'r_squared_adj': model.rsquared_adj,
            'n_obs': len(pivot),
            'positions': available_positions,
            'interactions': interactions,
            'target': target,
        }
    else:
        # Numpy fallback
        X_mat = np.column_stack([np.ones(len(X)), X.values])
        coeffs, _, _, _ = np.linalg.lstsq(X_mat, y.values, rcond=None)

        y_pred = X_mat @ coeffs
        ss_res = np.sum((y.values - y_pred) ** 2)
        ss_tot = np.sum((y.values - y.values.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        coefficients = {'intercept': coeffs[0]}
        for i, col in enumerate(feature_cols):
            coefficients[col] = coeffs[i + 1]

        return {
            'coefficients': coefficients,
            'r_squared': r_squared,
            'n_obs': len(pivot),
            'positions': available_positions,
            'interactions': interactions,
            'target': target,
        }


# =============================================================================
# Optimization
# =============================================================================

def greedy_marginal_value(current_allocation: Dict[str, float],
                          effective_salary_params: Dict[str, Dict],
                          performance_model: Dict,
                          position: str) -> float:
    """
    Compute ∂PPG/∂S_x for a given position.

    From Calvetti equation 3.12
    """
    coeffs = performance_model['coefficients']
    interactions = performance_model['interactions']

    S_e = current_allocation.get(position, 0.5)  # Effective salary at position

    # Get α₁ for this position (from effective salary params)
    params = effective_salary_params.get(position)
    if params is None:
        alpha1_e = 1.0  # Default
    else:
        alpha1_e = params['veteran_alpha1']

    # Base coefficient
    beta_x = coeffs.get(position, 0)

    # Interaction terms
    interaction_sum = 0
    for pos1, pos2 in interactions:
        if pos1 == position or pos2 == position:
            other_pos = pos2 if pos1 == position else pos1
            beta_xy = coeffs.get(f'{pos1}_{pos2}_interaction', 0)

            # √(Perf_y / Perf_x) term
            perf_x = current_allocation.get(position, 0.5)
            perf_y = current_allocation.get(other_pos, 0.5)

            if perf_x > 0:
                interaction_sum += 0.5 * beta_xy * np.sqrt(perf_y / perf_x)

    # Full marginal value
    marginal = (alpha1_e / (1 + S_e)) * (beta_x + interaction_sum)

    return marginal


def find_optimal_allocation(total_cap_pct: float,
                            positions: List[str],
                            effective_salary_params: Dict[str, Dict],
                            performance_model: Dict,
                            min_position_cap: float = 0.5) -> Dict[str, float]:
    """
    Solve non-linear optimization for optimal cap allocation.

    Following Calvetti equation 3.13
    """
    if not HAS_SCIPY:
        print("  Warning: scipy not available, using equal allocation")
        return {pos: total_cap_pct / len(positions) for pos in positions}

    n_positions = len(positions)
    coeffs = performance_model['coefficients']
    interactions = performance_model['interactions']

    def objective(x):
        """Negative PPG (we minimize, so negate to maximize)."""
        allocation = {pos: x[i] for i, pos in enumerate(positions)}

        # Compute performance at each position from salary
        perf = {}
        for pos in positions:
            params = effective_salary_params.get(pos, {})
            alpha0 = params.get('veteran_alpha0', 0)
            alpha1 = params.get('veteran_alpha1', 1)
            perf[pos] = alpha0 + alpha1 * np.log1p(allocation[pos])

        # Compute PPG
        ppg = coeffs.get('intercept', 0)

        for pos in positions:
            ppg += coeffs.get(pos, 0) * perf[pos]

        for pos1, pos2 in interactions:
            if pos1 in positions and pos2 in positions:
                key = f'{pos1}_{pos2}_interaction'
                ppg += coeffs.get(key, 0) * np.sqrt(perf[pos1] * perf[pos2])

        return -ppg  # Negative because we minimize

    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda x: np.sum(x) - total_cap_pct}  # Sum to total
    ]

    # Bounds
    bounds = [(min_position_cap, total_cap_pct) for _ in positions]

    # Initial guess: equal allocation
    x0 = np.array([total_cap_pct / n_positions] * n_positions)

    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )

    if result.success:
        return {pos: result.x[i] for i, pos in enumerate(positions)}
    else:
        print(f"  Warning: Optimization did not converge: {result.message}")
        return {pos: total_cap_pct / n_positions for pos in positions}


# =============================================================================
# Main Analysis
# =============================================================================

def run_calvetti_analysis():
    """Run full Calvetti-style analysis for offense and defense."""
    print("=" * 60)
    print("CALVETTI SALARY ALLOCATION ANALYSIS")
    print("=" * 60)

    # Load data
    contracts = load_contracts()
    team_scoring = load_team_scoring()
    offense_stats, defense_stats = load_player_stats()

    # Aggregate (returns tuple of offense_data, defense_data)
    offense_data, defense_data = aggregate_team_data(
        contracts, team_scoring, offense_stats, defense_stats
    )

    results = {
        'offense': {},
        'defense': {},
    }

    # ==========================================================================
    # OFFENSE ANALYSIS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("OFFENSIVE ANALYSIS")
    print("=" * 60)

    # Step 1: Fit salary-to-performance regressions
    print("\n1. Fitting salary → performance regressions...")

    offense_regressions = {}
    offense_effective_params = {}

    for pos in OFFENSIVE_POSITIONS:
        rookie_reg = fit_salary_to_performance(offense_data, pos, 'rookie')
        veteran_reg = fit_salary_to_performance(offense_data, pos, 'veteran')

        if rookie_reg and veteran_reg:
            offense_regressions[f'{pos}_rookie'] = rookie_reg
            offense_regressions[f'{pos}_veteran'] = veteran_reg

            eff_params = compute_effective_salary_params(rookie_reg, veteran_reg)
            if eff_params:
                offense_effective_params[pos] = eff_params

            print(f"  {pos}: Rookie α₁={rookie_reg.alpha1:.2f} (R²={rookie_reg.r_squared:.2f}), "
                  f"Veteran α₁={veteran_reg.alpha1:.2f} (R²={veteran_reg.r_squared:.2f})")

    # Step 2: Fit PPG model with interactions
    print("\n2. Fitting PPG → position performance model...")

    offense_models = {}
    for g_name, interactions in OFFENSIVE_INTERACTIONS.items():
        model = fit_performance_model(offense_data, OFFENSIVE_POSITIONS, interactions, 'ppg')
        if model:
            offense_models[g_name] = model
            print(f"  {g_name}: R²={model['r_squared']:.3f} (n={model['n_obs']})")

    # Step 3: Compute optimal allocation
    print("\n3. Computing optimal offensive allocation...")

    best_model = offense_models.get('G2') or offense_models.get('G1') or offense_models.get('G0')
    if best_model:
        optimal_offense = find_optimal_allocation(
            total_cap_pct=52.0,  # ~52% of cap goes to offense
            positions=OFFENSIVE_POSITIONS,
            effective_salary_params=offense_effective_params,
            performance_model=best_model,
        )

        # Get league average for comparison
        league_avg = offense_data.groupby('position_group')['cap_pct_total'].mean()

        print("\n  Position | Optimal | League Avg | Difference")
        print("  " + "-" * 50)
        for pos in OFFENSIVE_POSITIONS:
            opt = optimal_offense.get(pos, 0)
            avg = league_avg.get(pos, 0)
            diff = opt - avg
            print(f"  {pos:8s} | {opt:6.1f}% | {avg:6.1f}%    | {diff:+.1f}%")

    results['offense'] = {
        'regressions': {k: vars(v) for k, v in offense_regressions.items()},
        'effective_salary_params': offense_effective_params,
        'models': offense_models,
        'optimal_allocation': optimal_offense if best_model else None,
    }

    # ==========================================================================
    # DEFENSE ANALYSIS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("DEFENSIVE ANALYSIS")
    print("=" * 60)

    # Step 1: Fit salary-to-performance regressions
    print("\n1. Fitting salary → performance regressions...")

    defense_regressions = {}
    defense_effective_params = {}

    for pos in DEFENSIVE_POSITIONS:
        rookie_reg = fit_salary_to_performance(defense_data, pos, 'rookie')
        veteran_reg = fit_salary_to_performance(defense_data, pos, 'veteran')

        if rookie_reg and veteran_reg:
            defense_regressions[f'{pos}_rookie'] = rookie_reg
            defense_regressions[f'{pos}_veteran'] = veteran_reg

            eff_params = compute_effective_salary_params(rookie_reg, veteran_reg)
            if eff_params:
                defense_effective_params[pos] = eff_params

            print(f"  {pos}: Rookie α₁={rookie_reg.alpha1:.2f} (R²={rookie_reg.r_squared:.2f}), "
                  f"Veteran α₁={veteran_reg.alpha1:.2f} (R²={veteran_reg.r_squared:.2f})")

    # Step 2: Fit PAPG model (note: for defense, lower is better)
    print("\n2. Fitting PAPG → position performance model...")

    defense_models = {}
    for g_name, interactions in DEFENSIVE_INTERACTIONS.items():
        model = fit_performance_model(defense_data, DEFENSIVE_POSITIONS, interactions, 'papg')
        if model:
            defense_models[g_name] = model
            print(f"  {g_name}: R²={model['r_squared']:.3f} (n={model['n_obs']})")

    # Step 3: Compute optimal allocation
    print("\n3. Computing optimal defensive allocation...")

    best_model = defense_models.get('G2') or defense_models.get('G1') or defense_models.get('G0')
    if best_model:
        optimal_defense = find_optimal_allocation(
            total_cap_pct=48.0,  # ~48% of cap goes to defense
            positions=DEFENSIVE_POSITIONS,
            effective_salary_params=defense_effective_params,
            performance_model=best_model,
        )

        # Get league average for comparison
        league_avg = defense_data.groupby('position_group')['cap_pct_total'].mean()

        print("\n  Position | Optimal | League Avg | Difference")
        print("  " + "-" * 50)
        for pos in DEFENSIVE_POSITIONS:
            opt = optimal_defense.get(pos, 0)
            avg = league_avg.get(pos, 0)
            diff = opt - avg
            print(f"  {pos:8s} | {opt:6.1f}% | {avg:6.1f}%    | {diff:+.1f}%")

    results['defense'] = {
        'regressions': {k: vars(v) for k, v in defense_regressions.items()},
        'effective_salary_params': defense_effective_params,
        'models': defense_models,
        'optimal_allocation': optimal_defense if best_model else None,
    }

    # ==========================================================================
    # EXPORT RESULTS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("EXPORTING RESULTS")
    print("=" * 60)

    # Convert numpy types for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        return obj

    results_clean = convert_numpy(results)

    output_path = EXPORTS_DIR / "calvetti_allocation_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(results_clean, f, indent=2)

    print(f"  Saved results to: {output_path}")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 60)
    print("KEY INSIGHTS")
    print("=" * 60)

    print("\n📊 Rookie Contract Premium (Effective Salary Multiplier):")
    for side, params in [('Offense', offense_effective_params), ('Defense', defense_effective_params)]:
        print(f"\n  {side}:")
        for pos, p in params.items():
            if p['exponent'] > 0:
                # At 1% cap, what's the effective salary?
                eff_at_1pct = rookie_to_effective_salary(1.0, p)
                print(f"    {pos}: 1% rookie cap → {eff_at_1pct:.1f}% effective (mult={p['multiplier']:.2f})")

    print("\n🎯 Optimal Allocation vs League Average:")
    print("  (Positive = model says invest MORE, Negative = invest LESS)")

    return results


if __name__ == "__main__":
    run_calvetti_analysis()
