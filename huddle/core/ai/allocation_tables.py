"""
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

EFFECTIVE_SALARY_PARAMS = {
    "description": "Convert rookie cap % to veteran-equivalent cap %",
    "formula": "effective = multiplier * (1 + rookie_cap_pct)^exponent",
    "offense": {
        "QB": {
            "multiplier": 3.0364,
            "exponent": 0.5098,
            "lookup": {
                "0.5": 3.73,
                "1.0": 4.32,
                "2.0": 5.32,
                "3.0": 6.16,
                "5.0": 7.57,
                "10.0": 10.31
            }
        },
        "RB": {
            "multiplier": 0.0447,
            "exponent": 3.121,
            "lookup": {
                "0.5": 0.16,
                "1.0": 0.39,
                "2.0": 1.38,
                "3.0": 3.38,
                "5.0": 12.0,
                "10.0": 79.56
            }
        },
        "WR": {
            "multiplier": 0.8441,
            "exponent": 1.4255,
            "lookup": {
                "0.5": 1.5,
                "1.0": 2.27,
                "2.0": 4.04,
                "3.0": 6.09,
                "5.0": 10.86,
                "10.0": 25.76
            }
        },
        "TE": {
            "multiplier": 0.6322,
            "exponent": 1.4482,
            "lookup": {
                "0.5": 1.14,
                "1.0": 1.72,
                "2.0": 3.1,
                "3.0": 4.71,
                "5.0": 8.47,
                "10.0": 20.37
            }
        },
        "OL": {
            "multiplier": 7.7971,
            "exponent": 0.2942,
            "lookup": {
                "0.5": 8.79,
                "1.0": 9.56,
                "2.0": 10.77,
                "3.0": 11.72,
                "5.0": 13.21,
                "10.0": 15.79
            }
        }
    },
    "defense": {
        "CB": {
            "multiplier": 0.1165,
            "exponent": 2.3048,
            "lookup": {
                "0.5": 0.3,
                "1.0": 0.58,
                "2.0": 1.47,
                "3.0": 2.84,
                "5.0": 7.24,
                "10.0": 29.27
            }
        },
        "S": {
            "multiplier": 0.9966,
            "exponent": 1.162,
            "lookup": {
                "0.5": 1.6,
                "1.0": 2.23,
                "2.0": 3.57,
                "3.0": 4.99,
                "5.0": 7.99,
                "10.0": 16.17
            }
        },
        "LB": {
            "multiplier": 0.3552,
            "exponent": 1.7024,
            "lookup": {
                "0.5": 0.71,
                "1.0": 1.16,
                "2.0": 2.31,
                "3.0": 3.76,
                "5.0": 7.5,
                "10.0": 21.06
            }
        },
        "EDGE": {
            "multiplier": 1.7143,
            "exponent": 0.9189,
            "lookup": {
                "0.5": 2.49,
                "1.0": 3.24,
                "2.0": 4.7,
                "3.0": 6.13,
                "5.0": 8.89,
                "10.0": 15.52
            }
        },
        "DL": {
            "multiplier": 2.2872,
            "exponent": 0.7442,
            "lookup": {
                "0.5": 3.09,
                "1.0": 3.83,
                "2.0": 5.18,
                "3.0": 6.42,
                "5.0": 8.68,
                "10.0": 13.62
            }
        }
    }
}


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

MARKET_VALUE = {
    "QB": {
        "elite": 4.08,
        "starter": 0.84,
        "backup": 0.27,
        "minimum": 0.21
    },
    "RB": {
        "elite": 1.34,
        "starter": 0.75,
        "backup": 0.24,
        "minimum": 0.2
    },
    "WR": {
        "elite": 1.26,
        "starter": 0.75,
        "backup": 0.23,
        "minimum": 0.2
    },
    "TE": {
        "elite": 1.34,
        "starter": 0.76,
        "backup": 0.23,
        "minimum": 0.19
    },
    "OL": {
        "elite": 2.58,
        "starter": 0.8,
        "backup": 0.23,
        "minimum": 0.21
    },
    "LB": {
        "elite": 1.65,
        "starter": 0.8,
        "backup": 0.26,
        "minimum": 0.21
    },
    "CB": {
        "elite": 1.37,
        "starter": 0.76,
        "backup": 0.23,
        "minimum": 0.2
    },
    "S": {
        "elite": 1.9,
        "starter": 0.81,
        "backup": 0.25,
        "minimum": 0.21
    },
    "K": {
        "elite": 1.53,
        "starter": 0.66,
        "backup": 0.22,
        "minimum": 0.17
    },
    "P": {
        "elite": 2.1,
        "starter": 0.82,
        "backup": 0.28,
        "minimum": 0.17
    },
    "LS": {
        "elite": 1.35,
        "starter": 0.9,
        "backup": 0.32,
        "minimum": 0.23
    }
}


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

OPTIMAL_ALLOCATION = {
    "description": "Target cap allocation by position",
    "total_offense_pct": 52.0,
    "total_defense_pct": 48.0,
    "offense": {
        "QB": {
            "target": 8.5,
            "range": [
                4.0,
                15.0
            ],
            "priority": 1
        },
        "WR": {
            "target": 12.0,
            "range": [
                8.0,
                16.0
            ],
            "priority": 2
        },
        "OL": {
            "target": 18.0,
            "range": [
                12.0,
                24.0
            ],
            "priority": 3
        },
        "TE": {
            "target": 4.0,
            "range": [
                2.0,
                7.0
            ],
            "priority": 4
        },
        "RB": {
            "target": 3.0,
            "range": [
                1.0,
                6.0
            ],
            "priority": 5
        }
    },
    "defense": {
        "EDGE": {
            "target": 12.0,
            "range": [
                8.0,
                16.0
            ],
            "priority": 1
        },
        "DL": {
            "target": 10.0,
            "range": [
                6.0,
                14.0
            ],
            "priority": 2
        },
        "CB": {
            "target": 10.0,
            "range": [
                6.0,
                14.0
            ],
            "priority": 3
        },
        "LB": {
            "target": 8.0,
            "range": [
                5.0,
                12.0
            ],
            "priority": 4
        },
        "S": {
            "target": 6.0,
            "range": [
                3.0,
                10.0
            ],
            "priority": 5
        }
    }
}


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

POSITION_PRIORITY = {
    "description": "Which positions to prioritize based on current roster",
    "offense": {
        "if_strong": {
            "QB": {
                "decreases": [
                    "WR",
                    "TE"
                ],
                "increases": [
                    "OL"
                ]
            },
            "WR": {
                "decreases": [
                    "QB"
                ],
                "increases": [
                    "OL"
                ]
            },
            "OL": {
                "decreases": [
                    "RB"
                ],
                "increases": [
                    "QB",
                    "WR"
                ]
            },
            "RB": {
                "decreases": [],
                "increases": [
                    "OL"
                ]
            },
            "TE": {
                "decreases": [],
                "increases": [
                    "QB"
                ]
            }
        },
        "if_weak": {
            "QB": {
                "prioritize": [
                    "WR",
                    "TE",
                    "OL"
                ]
            },
            "OL": {
                "prioritize": [
                    "RB"
                ]
            },
            "WR": {
                "prioritize": [
                    "TE",
                    "RB"
                ]
            }
        }
    },
    "defense": {
        "if_strong": {
            "EDGE": {
                "decreases": [
                    "CB"
                ],
                "increases": [
                    "DL"
                ]
            },
            "CB": {
                "decreases": [
                    "S"
                ],
                "increases": [
                    "EDGE"
                ]
            },
            "DL": {
                "decreases": [
                    "LB"
                ],
                "increases": [
                    "EDGE"
                ]
            },
            "LB": {
                "decreases": [],
                "increases": [
                    "DL"
                ]
            },
            "S": {
                "decreases": [],
                "increases": [
                    "CB"
                ]
            }
        },
        "if_weak": {
            "EDGE": {
                "prioritize": [
                    "CB",
                    "S"
                ]
            },
            "CB": {
                "prioritize": [
                    "EDGE",
                    "S"
                ]
            }
        }
    }
}


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

ROOKIE_PREMIUM = {
    "description": "Value multiplier for rookie contracts (effective/actual)",
    "offense": {
        "QB": {
            "value_multiplier": 4.32,
            "draft_priority": "high"
        },
        "RB": {
            "value_multiplier": 0.39,
            "draft_priority": "low"
        },
        "WR": {
            "value_multiplier": 2.27,
            "draft_priority": "high"
        },
        "TE": {
            "value_multiplier": 1.72,
            "draft_priority": "medium"
        },
        "OL": {
            "value_multiplier": 5.0,
            "draft_priority": "high"
        }
    },
    "defense": {
        "CB": {
            "value_multiplier": 0.58,
            "draft_priority": "low"
        },
        "S": {
            "value_multiplier": 2.23,
            "draft_priority": "high"
        },
        "LB": {
            "value_multiplier": 1.16,
            "draft_priority": "medium"
        },
        "EDGE": {
            "value_multiplier": 3.24,
            "draft_priority": "high"
        },
        "DL": {
            "value_multiplier": 3.83,
            "draft_priority": "high"
        }
    }
}


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
