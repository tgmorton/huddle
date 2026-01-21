"""
Contract Analysis Model

Analyzes real NFL contract data to build salary generation models.
Uses Over The Cap data from contracts.parquet.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "cached"
EXPORT_DIR = Path(__file__).parent.parent / "exports"

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


def load_contracts():
    """Load contract data."""
    print("Loading contracts...")
    contracts = pd.read_parquet(DATA_DIR / "contracts.parquet")
    print(f"  Total contracts: {len(contracts):,}")
    return contracts


def analyze_position_markets(contracts):
    """Analyze salary distribution by position."""
    print("\n=== POSITION MARKET ANALYSIS ===")

    # Filter to recent, active contracts
    recent = contracts[
        (contracts['year_signed'] >= 2020) &
        (contracts['apy'].notna()) &
        (contracts['apy'] > 0)
    ].copy()

    # Group positions
    position_map = {
        'QB': 'QB',
        'RB': 'RB', 'FB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'LT': 'OT', 'RT': 'OT', 'OT': 'OT',
        'LG': 'G', 'RG': 'G', 'G': 'G',
        'C': 'C',
        'EDGE': 'EDGE', 'OLB': 'EDGE', 'DE': 'EDGE',
        'DT': 'DT', 'NT': 'DT', 'DL': 'DT',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'CB',
        'FS': 'S', 'SS': 'S', 'S': 'S', 'DB': 'S',
        'K': 'K',
        'P': 'P',
        'LS': 'LS',
    }

    recent['pos_group'] = recent['position'].map(position_map)
    recent = recent[recent['pos_group'].notna()]

    position_stats = {}

    for pos in recent['pos_group'].unique():
        pos_data = recent[recent['pos_group'] == pos]['apy']

        if len(pos_data) < 10:
            continue

        stats = {
            'count': len(pos_data),
            'min': pos_data.min(),
            'p10': pos_data.quantile(0.10),
            'p25': pos_data.quantile(0.25),
            'median': pos_data.median(),
            'p75': pos_data.quantile(0.75),
            'p90': pos_data.quantile(0.90),
            'max': pos_data.max(),
            'mean': pos_data.mean(),
            'std': pos_data.std(),
        }

        position_stats[pos] = stats

        print(f"\n{pos}:")
        print(f"  Count: {stats['count']}")
        print(f"  Range: ${stats['min']:.2f}M - ${stats['max']:.2f}M")
        print(f"  Median: ${stats['median']:.2f}M")
        print(f"  75th %ile: ${stats['p75']:.2f}M")

    return position_stats


def analyze_guarantee_rates(contracts):
    """Analyze guaranteed money as percentage of total value."""
    print("\n=== GUARANTEE ANALYSIS ===")

    recent = contracts[
        (contracts['year_signed'] >= 2020) &
        (contracts['value'].notna()) &
        (contracts['value'] > 0) &
        (contracts['guaranteed'].notna())
    ].copy()

    recent['gtd_pct'] = recent['guaranteed'] / recent['value']
    recent['gtd_pct'] = recent['gtd_pct'].clip(0, 1)  # Cap at 100%

    # By APY tier
    recent['apy_tier'] = pd.qcut(recent['apy'], q=4, labels=['Low', 'Mid', 'High', 'Elite'])

    gtd_by_tier = recent.groupby('apy_tier')['gtd_pct'].agg(['mean', 'std', 'median'])
    print("\nGuarantee % by APY Tier:")
    print(gtd_by_tier)

    # By position
    position_map = {
        'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE',
        'LT': 'OL', 'RT': 'OL', 'OT': 'OL', 'LG': 'OL', 'RG': 'OL', 'G': 'OL', 'C': 'OL',
        'EDGE': 'EDGE', 'OLB': 'EDGE', 'DE': 'EDGE',
        'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'DB', 'FS': 'DB', 'SS': 'DB', 'S': 'DB', 'DB': 'DB',
    }
    recent['pos_group'] = recent['position'].map(position_map)

    gtd_by_pos = recent.groupby('pos_group')['gtd_pct'].agg(['mean', 'median', 'count'])
    print("\nGuarantee % by Position:")
    print(gtd_by_pos.sort_values('mean', ascending=False))

    return {
        'by_tier': gtd_by_tier.to_dict(),
        'by_position': gtd_by_pos.to_dict(),
        'overall_mean': recent['gtd_pct'].mean(),
        'overall_median': recent['gtd_pct'].median(),
    }


def analyze_contract_lengths(contracts):
    """Analyze contract length distribution."""
    print("\n=== CONTRACT LENGTH ANALYSIS ===")

    recent = contracts[
        (contracts['year_signed'] >= 2020) &
        (contracts['years'].notna()) &
        (contracts['years'] > 0)
    ].copy()

    # Overall distribution
    length_dist = recent['years'].value_counts().sort_index()
    print("\nContract Length Distribution:")
    for years, count in length_dist.items():
        print(f"  {int(years)} years: {count} ({count/len(recent)*100:.1f}%)")

    # By APY tier
    recent['apy_tier'] = pd.qcut(recent['apy'].fillna(0), q=4, labels=['Low', 'Mid', 'High', 'Elite'], duplicates='drop')

    length_by_tier = recent.groupby('apy_tier')['years'].agg(['mean', 'median'])
    print("\nAvg Length by APY Tier:")
    print(length_by_tier)

    return {
        'distribution': {int(k): int(v) for k, v in length_dist.items()},
        'by_tier': length_by_tier.to_dict(),
        'overall_mean': recent['years'].mean(),
    }


def analyze_rookie_contracts(contracts):
    """Analyze rookie contracts by draft position."""
    print("\n=== ROOKIE CONTRACT ANALYSIS ===")

    rookies = contracts[
        (contracts['draft_year'].notna()) &
        (contracts['draft_round'].notna()) &
        (contracts['year_signed'] >= 2020) &
        (contracts['draft_year'] >= 2020)
    ].copy()

    # First round
    round1 = rookies[rookies['draft_round'] == 1].copy()
    round1 = round1.sort_values('draft_overall')

    print("\nFirst Round Contracts (recent):")
    print(round1[['player', 'draft_overall', 'value', 'guaranteed', 'apy']].head(20).to_string())

    # By round
    round_stats = {}
    for rd in [1, 2, 3, 4, 5, 6, 7]:
        rd_data = rookies[rookies['draft_round'] == rd]
        if len(rd_data) < 3:
            continue

        round_stats[rd] = {
            'count': len(rd_data),
            'avg_value': rd_data['value'].mean(),
            'avg_guaranteed': rd_data['guaranteed'].mean(),
            'avg_years': rd_data['years'].mean(),
            'gtd_pct': (rd_data['guaranteed'] / rd_data['value']).mean(),
        }

        print(f"\nRound {rd}:")
        print(f"  Count: {len(rd_data)}")
        print(f"  Avg Value: ${rd_data['value'].mean():.2f}M")
        print(f"  Avg Guaranteed: ${rd_data['guaranteed'].mean():.2f}M")
        print(f"  Guarantee %: {round_stats[rd]['gtd_pct']*100:.1f}%")

    # Pick-by-pick for round 1
    pick_values = {}
    for _, row in round1.iterrows():
        pick = int(row['draft_overall'])
        if pick <= 32:
            pick_values[pick] = {
                'value': row['value'],
                'guaranteed': row['guaranteed'],
                'apy': row['apy'],
            }

    return {
        'by_round': round_stats,
        'round1_by_pick': pick_values,
    }


def analyze_team_cap_situations(contracts):
    """Analyze team cap situations to identify archetypes."""
    print("\n=== TEAM CAP SITUATION ANALYSIS ===")

    # Get current active contracts
    active = contracts[contracts['is_active'] == True].copy()

    # Position mapping
    position_map = {
        'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE',
        'LT': 'OL', 'RT': 'OL', 'OT': 'OL', 'LG': 'OL', 'RG': 'OL', 'G': 'OL', 'C': 'OL',
        'EDGE': 'EDGE', 'OLB': 'EDGE', 'DE': 'EDGE',
        'DT': 'DL', 'NT': 'DL', 'DL': 'DL',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'DB', 'FS': 'DB', 'SS': 'DB', 'S': 'DB', 'DB': 'DB',
        'K': 'K', 'P': 'P', 'LS': 'LS',
    }
    active['pos_group'] = active['position'].map(position_map)

    team_stats = []

    for team in active['team'].unique():
        team_contracts = active[active['team'] == team]

        if len(team_contracts) < 20:
            continue

        total_apy = team_contracts['apy'].sum()
        top3_apy = team_contracts.nlargest(3, 'apy')['apy'].sum()
        qb_contracts = team_contracts[team_contracts['pos_group'] == 'QB']
        qb_apy = qb_contracts['apy'].max() if len(qb_contracts) > 0 else 0

        # Count rookies (drafted in last 4 years)
        rookies = team_contracts[
            (team_contracts['draft_year'].notna()) &
            (team_contracts['draft_year'] >= 2021)
        ]

        team_stats.append({
            'team': team,
            'total_apy': total_apy,
            'top3_pct': top3_apy / total_apy if total_apy > 0 else 0,
            'qb_apy': qb_apy,
            'qb_pct': qb_apy / total_apy if total_apy > 0 else 0,
            'player_count': len(team_contracts),
            'rookie_count': len(rookies),
            'rookie_pct': len(rookies) / len(team_contracts),
            'avg_contract_length': team_contracts['years'].mean(),
        })

    team_df = pd.DataFrame(team_stats)
    team_df = team_df.sort_values('qb_pct', ascending=False)

    print("\nTeam QB Spending (as % of total):")
    print(team_df[['team', 'qb_apy', 'qb_pct', 'top3_pct', 'rookie_pct']].head(15).to_string())

    # Identify archetypes
    print("\n\nArchetype Examples from Data:")

    # High QB spend, low rookie %
    contenders = team_df[(team_df['qb_pct'] > 0.15) & (team_df['rookie_pct'] < 0.3)]
    print(f"\nContending (high QB, low rookie): {contenders['team'].tolist()[:5]}")

    # Low QB spend, high rookie %
    rebuilding = team_df[(team_df['qb_pct'] < 0.08) & (team_df['rookie_pct'] > 0.4)]
    print(f"Rebuilding (low QB, high rookie): {rebuilding['team'].tolist()[:5]}")

    # High top3 concentration
    top_heavy = team_df[team_df['top3_pct'] > 0.35]
    print(f"Top-heavy (>35% in top 3): {top_heavy['team'].tolist()[:5]}")

    return {
        'team_stats': team_df.to_dict('records'),
        'archetype_thresholds': {
            'contending': {'qb_pct_min': 0.15, 'rookie_pct_max': 0.30},
            'rebuilding': {'qb_pct_max': 0.08, 'rookie_pct_min': 0.40},
            'top_heavy': {'top3_pct_min': 0.35},
        }
    }


def analyze_contract_structures(contracts):
    """Analyze year-by-year contract structures from the cols field."""
    print("\n=== CONTRACT STRUCTURE ANALYSIS ===")

    # Get contracts with detailed structure
    has_structure = contracts[contracts['cols'].notna()].copy()

    structures = []

    for _, row in has_structure.head(500).iterrows():  # Sample for speed
        cols = row['cols']
        if not isinstance(cols, list):
            continue

        # Filter to actual years (not Total)
        years = [c for c in cols if c.get('year') != 'Total' and c.get('year') is not None]
        if len(years) < 2:
            continue

        total_value = row['value']
        if pd.isna(total_value) or total_value <= 0:
            continue

        # Calculate year-by-year percentages
        cap_hits = [y.get('cap_number', 0) or 0 for y in years[:5]]  # First 5 years max
        total_cap = sum(cap_hits)

        if total_cap <= 0:
            continue

        cap_pcts = [h / total_cap for h in cap_hits]

        # Classify structure
        if len(cap_pcts) >= 3:
            if cap_pcts[0] < 0.15 and cap_pcts[-1] > 0.30:
                structure_type = 'backloaded'
            elif cap_pcts[0] > 0.30 and cap_pcts[-1] < 0.20:
                structure_type = 'frontloaded'
            else:
                structure_type = 'flat'

            structures.append({
                'player': row['player'],
                'position': row['position'],
                'apy': row['apy'],
                'years': len(years),
                'structure': structure_type,
                'year1_pct': cap_pcts[0],
                'year2_pct': cap_pcts[1] if len(cap_pcts) > 1 else None,
                'year3_pct': cap_pcts[2] if len(cap_pcts) > 2 else None,
                'last_year_pct': cap_pcts[-1],
            })

    struct_df = pd.DataFrame(structures)

    if len(struct_df) > 0:
        print("\nContract Structure Distribution:")
        print(struct_df['structure'].value_counts())

        print("\nAvg Cap % by Year (all contracts):")
        print(f"  Year 1: {struct_df['year1_pct'].mean()*100:.1f}%")
        print(f"  Year 2: {struct_df['year2_pct'].mean()*100:.1f}%")
        print(f"  Year 3: {struct_df['year3_pct'].mean()*100:.1f}%")

        # By structure type
        for stype in ['backloaded', 'frontloaded', 'flat']:
            subset = struct_df[struct_df['structure'] == stype]
            if len(subset) > 5:
                print(f"\n{stype.title()} Contracts:")
                print(f"  Count: {len(subset)}")
                print(f"  Year 1 avg: {subset['year1_pct'].mean()*100:.1f}%")
                print(f"  Last year avg: {subset['last_year_pct'].mean()*100:.1f}%")

    return {
        'structure_counts': struct_df['structure'].value_counts().to_dict() if len(struct_df) > 0 else {},
        'structure_patterns': struct_df.groupby('structure').agg({
            'year1_pct': 'mean',
            'year2_pct': 'mean',
            'last_year_pct': 'mean',
        }).to_dict() if len(struct_df) > 0 else {},
    }


def analyze_cap_percentages(contracts):
    """Analyze APY as percentage of salary cap."""
    print("\n=== CAP PERCENTAGE ANALYSIS ===")

    recent = contracts[
        (contracts['year_signed'] >= 2020) &
        (contracts['apy_cap_pct'].notna()) &
        (contracts['apy_cap_pct'] > 0)
    ].copy()

    # Position mapping
    position_map = {
        'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE',
        'LT': 'OT', 'RT': 'OT', 'OT': 'OT',
        'LG': 'G', 'RG': 'G', 'G': 'G', 'C': 'C',
        'EDGE': 'EDGE', 'OLB': 'EDGE', 'DE': 'EDGE',
        'DT': 'DT', 'NT': 'DT', 'DL': 'DT',
        'ILB': 'LB', 'MLB': 'LB', 'LB': 'LB',
        'CB': 'CB', 'FS': 'S', 'SS': 'S', 'S': 'S', 'DB': 'S',
    }
    recent['pos_group'] = recent['position'].map(position_map)
    recent = recent[recent['pos_group'].notna()]

    cap_pct_stats = {}

    for pos in recent['pos_group'].unique():
        pos_data = recent[recent['pos_group'] == pos]['apy_cap_pct']

        if len(pos_data) < 10:
            continue

        cap_pct_stats[pos] = {
            'count': len(pos_data),
            'max': pos_data.max(),
            'p90': pos_data.quantile(0.90),
            'p75': pos_data.quantile(0.75),
            'median': pos_data.median(),
            'mean': pos_data.mean(),
        }

    print("\nAPY as % of Salary Cap by Position:")
    for pos, stats in sorted(cap_pct_stats.items(), key=lambda x: -x[1]['max']):
        print(f"  {pos}: max={stats['max']*100:.1f}%, p75={stats['p75']*100:.1f}%, median={stats['median']*100:.1f}%")

    return cap_pct_stats


def main():
    """Run all contract analyses."""
    contracts = load_contracts()

    position_markets = analyze_position_markets(contracts)
    guarantee_stats = analyze_guarantee_rates(contracts)
    length_stats = analyze_contract_lengths(contracts)
    rookie_stats = analyze_rookie_contracts(contracts)
    team_stats = analyze_team_cap_situations(contracts)
    structure_stats = analyze_contract_structures(contracts)
    cap_pct_stats = analyze_cap_percentages(contracts)

    # Compile results
    results = {
        'position_markets': position_markets,
        'guarantee_rates': guarantee_stats,
        'contract_lengths': length_stats,
        'rookie_contracts': rookie_stats,
        'team_situations': team_stats,
        'contract_structures': structure_stats,
        'cap_percentages': cap_pct_stats,
    }

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "contract_analysis.json"

    with open(export_path, 'w') as f:
        json.dump(convert_to_native(results), f, indent=2)

    print(f"\n\nExported to: {export_path}")

    return results


if __name__ == "__main__":
    results = main()
