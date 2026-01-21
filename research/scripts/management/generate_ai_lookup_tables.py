#!/usr/bin/env python3
"""
Generate AI Lookup Tables from Calvetti Analysis

Creates lookup tables that team AI can use for:
1. Effective salary conversion (valuing rookie contracts)
2. Position value tiers (expected performance by cap %)
3. Optimal allocation targets
4. Marginal value curves (where to spend next dollar)

Output format is Python dicts that can be directly imported by the game.
"""

import json
import numpy as np
from pathlib import Path

RESEARCH_DIR = Path(__file__).parent.parent
EXPORTS_DIR = RESEARCH_DIR / "exports"


def generate_lookup_tables():
    """Generate all AI lookup tables from analysis results."""

    # Load analysis results
    with open(EXPORTS_DIR / "calvetti_allocation_analysis.json") as f:
        analysis = json.load(f)

    # Load contract analysis for market data
    with open(EXPORTS_DIR / "contract_analysis.json") as f:
        contract_data = json.load(f)

    tables = {
        'meta': {
            'description': 'AI lookup tables for salary cap allocation decisions',
            'source': 'Calvetti-style analysis of NFL data',
            'positions': {
                'offense': ['QB', 'RB', 'WR', 'TE', 'OL'],
                'defense': ['CB', 'S', 'LB', 'EDGE', 'DL'],
            }
        },

        # =================================================================
        # Table 1: Effective Salary Conversion
        # =================================================================
        # Use: value_rookie_contract(position, cap_pct) → effective_cap_pct
        'effective_salary': {
            'description': 'Convert rookie cap % to veteran-equivalent cap %',
            'formula': 'effective = multiplier * (1 + rookie_cap_pct)^exponent',
            'offense': {},
            'defense': {},
        },

        # =================================================================
        # Table 2: Position Market Value (from contract_analysis)
        # =================================================================
        # Use: get_market_value(position, tier) → expected_cap_pct
        'market_value': {
            'description': 'Expected cap hit by position and tier',
            'tiers': ['elite', 'starter', 'backup', 'minimum'],
        },

        # =================================================================
        # Table 3: Optimal Allocation Targets
        # =================================================================
        # Use: get_target_allocation(position) → target_cap_pct
        'optimal_allocation': {
            'description': 'Target cap allocation by position',
            'total_offense_pct': 52.0,
            'total_defense_pct': 48.0,
        },

        # =================================================================
        # Table 4: Position Priority by Roster State
        # =================================================================
        # Use: get_priority(roster_state) → ranked positions
        'position_priority': {
            'description': 'Which positions to prioritize based on current roster',
        },

        # =================================================================
        # Table 5: Rookie Premium by Position
        # =================================================================
        # Use: rookie_value_multiplier(position) → how much more value rookies provide
        'rookie_premium': {
            'description': 'Value multiplier for rookie contracts (effective/actual)',
        },
    }

    # =========================================================================
    # Populate Effective Salary Tables
    # =========================================================================
    for side in ['offense', 'defense']:
        params = analysis.get(side, {}).get('effective_salary_params', {})
        for pos, p in params.items():
            tables['effective_salary'][side][pos] = {
                'multiplier': round(p['multiplier'], 4),
                'exponent': round(p['exponent'], 4),
                # Pre-computed values for common cap percentages
                'lookup': {
                    cap_pct: round(p['multiplier'] * ((1 + cap_pct) ** p['exponent']), 2)
                    for cap_pct in [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
                }
            }

    # =========================================================================
    # Populate Market Value Tables (from contract_analysis)
    # =========================================================================
    position_markets = contract_data.get('position_markets', {})

    # Map contract analysis positions to our groups
    market_map = {
        'QB': 'QB',
        'RB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'OT': 'OL', 'G': 'OL', 'C': 'OL',
        'CB': 'CB',
        'S': 'S',
        'LB': 'LB',
        'ED': 'EDGE',
        'IDL': 'DL',
    }

    tables['market_value']['by_position'] = {}

    for raw_pos, data in position_markets.items():
        pos_group = market_map.get(raw_pos, raw_pos)
        if pos_group not in tables['market_value']['by_position']:
            tables['market_value']['by_position'][pos_group] = {
                'elite': round(data.get('p90', 5.0), 2),
                'starter': round(data.get('median', 1.0), 2),
                'backup': round(data.get('p25', 0.3), 2),
                'minimum': round(data.get('p10', 0.2), 2),
            }

    # =========================================================================
    # Populate Optimal Allocation (use Calvetti findings + NFL averages)
    # =========================================================================
    # Based on Calvetti's findings and Mulholland-Jensen
    tables['optimal_allocation']['offense'] = {
        'QB': {'target': 8.5, 'range': (4.0, 15.0), 'priority': 1},
        'WR': {'target': 12.0, 'range': (8.0, 16.0), 'priority': 2},
        'OL': {'target': 18.0, 'range': (12.0, 24.0), 'priority': 3},
        'TE': {'target': 4.0, 'range': (2.0, 7.0), 'priority': 4},
        'RB': {'target': 3.0, 'range': (1.0, 6.0), 'priority': 5},  # Lowest priority
    }

    tables['optimal_allocation']['defense'] = {
        'EDGE': {'target': 12.0, 'range': (8.0, 16.0), 'priority': 1},
        'DL': {'target': 10.0, 'range': (6.0, 14.0), 'priority': 2},
        'CB': {'target': 10.0, 'range': (6.0, 14.0), 'priority': 3},
        'LB': {'target': 8.0, 'range': (5.0, 12.0), 'priority': 4},
        'S': {'target': 6.0, 'range': (3.0, 10.0), 'priority': 5},
    }

    # =========================================================================
    # Populate Position Priority Matrix
    # =========================================================================
    # Based on interaction terms - when you have strength at position A,
    # the priority of investing in position B changes

    tables['position_priority']['offense'] = {
        # If QB is strong, WR becomes less critical (diminishing returns)
        'if_strong': {
            'QB': {'decreases': ['WR', 'TE'], 'increases': ['OL']},
            'WR': {'decreases': ['QB'], 'increases': ['OL']},
            'OL': {'decreases': ['RB'], 'increases': ['QB', 'WR']},
            'RB': {'decreases': [], 'increases': ['OL']},
            'TE': {'decreases': [], 'increases': ['QB']},
        },
        # If position is weak, these become more important
        'if_weak': {
            'QB': {'prioritize': ['WR', 'TE', 'OL']},  # Need help
            'OL': {'prioritize': ['RB']},  # Can still run
            'WR': {'prioritize': ['TE', 'RB']},  # Alternate weapons
        },
    }

    tables['position_priority']['defense'] = {
        'if_strong': {
            'EDGE': {'decreases': ['CB'], 'increases': ['DL']},  # Rush helps coverage
            'CB': {'decreases': ['S'], 'increases': ['EDGE']},
            'DL': {'decreases': ['LB'], 'increases': ['EDGE']},
            'LB': {'decreases': [], 'increases': ['DL']},
            'S': {'decreases': [], 'increases': ['CB']},
        },
        'if_weak': {
            'EDGE': {'prioritize': ['CB', 'S']},  # Need coverage time
            'CB': {'prioritize': ['EDGE', 'S']},  # Need rush help
        },
    }

    # =========================================================================
    # Populate Rookie Premium Table
    # =========================================================================
    # How much more value do rookies provide relative to cap hit?
    # Based on effective salary at 1% cap hit

    tables['rookie_premium']['offense'] = {}
    tables['rookie_premium']['defense'] = {}

    for side in ['offense', 'defense']:
        params = analysis.get(side, {}).get('effective_salary_params', {})
        for pos, p in params.items():
            effective_at_1pct = p['multiplier'] * ((1 + 1.0) ** p['exponent'])
            premium = effective_at_1pct / 1.0 if effective_at_1pct > 0 else 1.0
            tables['rookie_premium'][side][pos] = {
                'value_multiplier': round(min(premium, 5.0), 2),  # Cap at 5x
                'draft_priority': 'high' if premium > 2.0 else 'medium' if premium > 1.0 else 'low',
            }

    # =========================================================================
    # Save Tables
    # =========================================================================
    output_path = EXPORTS_DIR / "ai_allocation_tables.json"
    with open(output_path, 'w') as f:
        json.dump(tables, f, indent=2)

    print(f"Saved AI lookup tables to: {output_path}")

    # Also generate Python module for direct import
    generate_python_module(tables)

    return tables


def generate_python_module(tables: dict):
    """Generate Python module that can be imported by the game."""

    output = '''"""
AI Salary Allocation Lookup Tables

Auto-generated from Calvetti-style analysis.
Import this module for team AI decision-making.

Usage:
    from huddle.core.ai.allocation_tables import (
        get_effective_salary,
        get_market_value,
        get_optimal_allocation,
        get_position_priority,
    )
"""

from typing import Dict, List, Tuple

# =============================================================================
# Effective Salary Conversion
# =============================================================================
# Converts rookie contract cap % to veteran-equivalent cap %

EFFECTIVE_SALARY_PARAMS = '''

    output += json.dumps(tables['effective_salary'], indent=4)

    output += '''


def get_effective_salary(position: str, rookie_cap_pct: float, side: str = 'offense') -> float:
    """
    Convert rookie cap hit to effective (veteran-equivalent) cap hit.

    Args:
        position: Position group (QB, WR, CB, etc.)
        rookie_cap_pct: Actual cap percentage of rookie contract
        side: 'offense' or 'defense'

    Returns:
        Effective cap percentage (what you'd pay a veteran for same production)
    """
    params = EFFECTIVE_SALARY_PARAMS.get(side, {}).get(position)
    if not params:
        return rookie_cap_pct  # No conversion available

    return params['multiplier'] * ((1 + rookie_cap_pct) ** params['exponent'])


# =============================================================================
# Market Value by Position and Tier
# =============================================================================

MARKET_VALUE = '''

    output += json.dumps(tables['market_value']['by_position'], indent=4)

    output += '''


def get_market_value(position: str, tier: str = 'starter') -> float:
    """
    Get expected cap percentage for a position at a given tier.

    Args:
        position: Position group
        tier: 'elite', 'starter', 'backup', or 'minimum'

    Returns:
        Expected cap percentage
    """
    pos_data = MARKET_VALUE.get(position, {})
    return pos_data.get(tier, 1.0)


# =============================================================================
# Optimal Allocation Targets
# =============================================================================

OPTIMAL_ALLOCATION = '''

    output += json.dumps(tables['optimal_allocation'], indent=4)

    output += '''


def get_optimal_allocation(position: str, side: str = 'offense') -> Dict:
    """
    Get target allocation for a position.

    Returns:
        Dict with 'target', 'range', and 'priority'
    """
    side_data = OPTIMAL_ALLOCATION.get(side, {})
    return side_data.get(position, {'target': 5.0, 'range': (2.0, 10.0), 'priority': 5})


def get_allocation_gap(current_allocation: Dict[str, float], side: str = 'offense') -> Dict[str, float]:
    """
    Compare current allocation to optimal and return gaps.

    Args:
        current_allocation: {position: cap_pct} dict
        side: 'offense' or 'defense'

    Returns:
        {position: gap} where positive means under-invested
    """
    side_data = OPTIMAL_ALLOCATION.get(side, {})
    gaps = {}
    for pos, target_data in side_data.items():
        if isinstance(target_data, dict):
            target = target_data.get('target', 5.0)
            current = current_allocation.get(pos, 0)
            gaps[pos] = target - current
    return gaps


# =============================================================================
# Position Priority Rules
# =============================================================================

POSITION_PRIORITY = '''

    output += json.dumps(tables['position_priority'], indent=4)

    output += '''


def get_position_priority(
    strong_positions: List[str],
    weak_positions: List[str],
    side: str = 'offense'
) -> List[str]:
    """
    Get prioritized list of positions to invest in.

    Args:
        strong_positions: Positions where we have good players
        weak_positions: Positions where we need help
        side: 'offense' or 'defense'

    Returns:
        Ranked list of positions to prioritize
    """
    rules = POSITION_PRIORITY.get(side, {})

    # Start with base priority from optimal allocation
    base_priority = list(OPTIMAL_ALLOCATION.get(side, {}).keys())

    # Adjust based on strength/weakness
    priority_boost = {}

    for pos in strong_positions:
        if_strong = rules.get('if_strong', {}).get(pos, {})
        for p in if_strong.get('increases', []):
            priority_boost[p] = priority_boost.get(p, 0) + 1
        for p in if_strong.get('decreases', []):
            priority_boost[p] = priority_boost.get(p, 0) - 1

    for pos in weak_positions:
        if_weak = rules.get('if_weak', {}).get(pos, {})
        for p in if_weak.get('prioritize', []):
            priority_boost[p] = priority_boost.get(p, 0) + 2

    # Sort by adjusted priority
    def sort_key(pos):
        opt = OPTIMAL_ALLOCATION.get(side, {}).get(pos, {})
        base = opt.get('priority', 5) if isinstance(opt, dict) else 5
        boost = priority_boost.get(pos, 0)
        return base - boost  # Lower is higher priority

    return sorted(base_priority, key=sort_key)


# =============================================================================
# Rookie Premium (Draft Value)
# =============================================================================

ROOKIE_PREMIUM = '''

    output += json.dumps(tables['rookie_premium'], indent=4)

    output += '''


def get_rookie_premium(position: str, side: str = 'offense') -> Dict:
    """
    Get rookie contract value multiplier for a position.

    Returns:
        Dict with 'value_multiplier' and 'draft_priority'
    """
    return ROOKIE_PREMIUM.get(side, {}).get(
        position,
        {'value_multiplier': 1.0, 'draft_priority': 'medium'}
    )


def should_draft_position(position: str, side: str = 'offense') -> bool:
    """
    Determine if a position is high-value to draft (vs sign in FA).

    High draft value = rookies provide much more value than cap hit suggests.
    """
    premium = get_rookie_premium(position, side)
    return premium.get('draft_priority') == 'high'
'''

    # Save Python module
    module_path = Path(__file__).parent.parent.parent / "huddle" / "core" / "ai" / "allocation_tables.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)

    with open(module_path, 'w') as f:
        f.write(output)

    print(f"Saved Python module to: {module_path}")


if __name__ == "__main__":
    tables = generate_lookup_tables()

    # Print summary
    print("\n" + "=" * 60)
    print("AI LOOKUP TABLES GENERATED")
    print("=" * 60)

    print("\n📊 Effective Salary (Rookie → Veteran equivalent):")
    for side in ['offense', 'defense']:
        print(f"\n  {side.upper()}:")
        for pos, data in tables['effective_salary'].get(side, {}).items():
            lookup = data.get('lookup', {})
            print(f"    {pos}: 1% rookie → {lookup.get(1.0, 'N/A')}% effective")

    print("\n🎯 Optimal Allocation Targets:")
    for side in ['offense', 'defense']:
        print(f"\n  {side.upper()}:")
        for pos, data in tables['optimal_allocation'].get(side, {}).items():
            if isinstance(data, dict):
                print(f"    {pos}: {data['target']}% (priority {data['priority']})")

    print("\n📈 Rookie Premium (Draft Value):")
    for side in ['offense', 'defense']:
        print(f"\n  {side.upper()}:")
        for pos, data in tables['rookie_premium'].get(side, {}).items():
            print(f"    {pos}: {data['value_multiplier']}x value ({data['draft_priority']} draft priority)")
