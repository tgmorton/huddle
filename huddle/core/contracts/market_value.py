"""
Market Value Calculator.

Calculates fair market value for players based on:
- Overall rating (exponential scaling - elite players worth much more)
- Position value (QB most valuable, then EDGE, CB, etc.)
- Age (peak 26-29, decline after 30)
- Experience (veterans command higher salaries)
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
import random

if TYPE_CHECKING:
    from huddle.core.models.player import Player


# Position value multipliers for salary calculation
# Based on NFL market rates - QBs and pass rushers command premiums
# Scaled down to keep team totals under cap
POSITION_VALUE_MULTIPLIERS = {
    "QB": 2.0,    # Franchise quarterbacks are highest paid
    "DE": 1.5,    # Elite pass rushers
    "DT": 1.2,    # Interior pressure
    "CB": 1.3,    # Shutdown corners
    "WR": 1.2,    # Elite receivers
    "LT": 1.2,    # Protect the blind side
    "RT": 1.1,    # Right tackle
    "TE": 1.0,    # Receiving tight ends
    "SS": 1.0,    # Strong safety
    "FS": 1.0,    # Free safety
    "OLB": 1.1,   # Edge rushers from OLB
    "MLB": 1.0,   # Middle linebacker
    "ILB": 0.9,   # Inside linebacker
    "RB": 0.9,    # Running backs (replaceable in modern NFL)
    "LG": 0.9,    # Interior line
    "RG": 0.9,
    "C": 0.9,
    "FB": 0.6,    # Fullbacks (niche role)
    "NT": 0.9,    # Nose tackle
    "K": 0.4,     # Kickers
    "P": 0.4,     # Punters
    "LS": 0.3,    # Long snappers
}

# Age curve - prime years are 26-29
AGE_VALUE_CURVE = {
    21: 0.80,
    22: 0.85,
    23: 0.90,
    24: 0.95,
    25: 0.98,
    26: 1.00,  # Peak value
    27: 1.00,
    28: 1.00,
    29: 0.98,
    30: 0.90,
    31: 0.80,
    32: 0.70,
    33: 0.60,
    34: 0.50,
    35: 0.40,
    36: 0.30,
    37: 0.25,
    38: 0.20,
}


@dataclass
class MarketValue:
    """
    Market value assessment for a player.

    All monetary values in thousands (e.g., 15000 = $15M).
    """
    base_salary: int       # Annual salary
    total_value: int       # Total contract value (salary * years + bonus)
    signing_bonus: int     # Recommended signing bonus
    years: int             # Recommended contract length
    cap_hit_year1: int     # First year cap impact (salary + bonus/years)

    @property
    def guaranteed(self) -> int:
        """Total guaranteed money (signing bonus + partial salary)."""
        # Typically 50-70% of total is guaranteed for top players
        return self.signing_bonus + (self.base_salary // 2)


def calculate_market_value(
    player: "Player",
    position_scarcity: float = 1.0,
    team_need: float = 0.5,
) -> MarketValue:
    """
    Calculate fair market value for a player.

    Designed so a full 53-man roster averages ~$200-220M total salary,
    leaving cap room for moves. Elite players are expensive but most
    roster spots are filled with cheap depth.

    Args:
        player: The player to evaluate
        position_scarcity: League-wide position scarcity (0.5-1.5)
        team_need: How much team needs this position (0.0-1.0)

    Returns:
        MarketValue with recommended contract terms
    """
    # Base salary from overall rating
    # Scaled so average 53-man roster fits under $255M cap with ~$30-50M room
    # With avg roster OVR ~82, target ~$3.5-4M avg = ~$190-210M total
    overall = player.overall

    if overall >= 95:
        base = 20000 + (overall - 95) * 2500  # $20M-30M for elite (very rare)
    elif overall >= 90:
        base = 10000 + (overall - 90) * 2000  # $10M-20M for stars
    elif overall >= 85:
        base = 4000 + (overall - 85) * 1200   # $4M-10M for quality starters
    elif overall >= 80:
        base = 2000 + (overall - 80) * 400    # $2M-4M for solid starters
    elif overall >= 75:
        base = 1200 + (overall - 75) * 160    # $1.2M-2M for rotational
    elif overall >= 70:
        base = 900 + (overall - 70) * 60      # $900K-1.2M for depth
    else:
        base = 800 + max(0, (overall - 60)) * 10  # $800K-900K for roster fillers

    # Apply position multiplier
    pos_mult = POSITION_VALUE_MULTIPLIERS.get(player.position.value, 1.0)
    base = int(base * pos_mult)

    # Apply age curve
    age_mult = AGE_VALUE_CURVE.get(player.age, 0.20)
    if player.age < 21:
        age_mult = 0.75
    base = int(base * age_mult)

    # Apply scarcity and need modifiers
    base = int(base * position_scarcity * (1.0 + team_need * 0.2))

    # Minimum salary (league minimum ~$1M)
    base = max(1000, base)

    # Contract length based on age and value
    if player.age >= 32:
        years = random.choice([1, 2])
    elif player.age >= 29:
        years = random.choice([2, 3])
    elif overall >= 90:
        years = random.choice([4, 5])  # Elite players get long-term deals
    elif overall >= 80:
        years = random.choice([3, 4])
    else:
        years = random.choice([2, 3])

    # Signing bonus: 20-40% of total value for starters, less for depth
    if overall >= 85:
        bonus_pct = random.uniform(0.25, 0.40)
    elif overall >= 75:
        bonus_pct = random.uniform(0.15, 0.25)
    else:
        bonus_pct = random.uniform(0.05, 0.15)

    salary_total = base * years
    signing_bonus = int(salary_total * bonus_pct)
    total_value = salary_total + signing_bonus  # Total contract value includes bonus

    # Cap hit year 1 = salary + prorated bonus
    cap_hit_year1 = base + (signing_bonus // years)

    return MarketValue(
        base_salary=base,
        total_value=total_value,
        signing_bonus=signing_bonus,
        years=years,
        cap_hit_year1=cap_hit_year1,
    )


def assign_contract(
    player: "Player",
    years: int = None,
    salary: int = None,
    signing_bonus: int = None,
    use_market_value: bool = True,
) -> None:
    """
    Assign a contract to a player.

    If use_market_value is True and no values provided, calculates
    market value and assigns appropriate contract.

    Args:
        player: Player to assign contract to
        years: Contract length (optional)
        salary: Annual salary in thousands (optional)
        signing_bonus: Signing bonus in thousands (optional)
        use_market_value: If True, calculate missing values from market
    """
    if use_market_value and (years is None or salary is None):
        market = calculate_market_value(player)
        years = years or market.years
        salary = salary or market.base_salary
        signing_bonus = signing_bonus if signing_bonus is not None else market.signing_bonus

    # Ensure we have values
    years = years or 1
    salary = salary or 1000
    signing_bonus = signing_bonus or 0

    player.contract_years = years
    player.contract_year_remaining = years
    player.salary = salary
    player.signing_bonus = signing_bonus
    player.signing_bonus_remaining = signing_bonus


def calculate_relative_value(player: "Player") -> float:
    """
    Calculate relative value weight for a player (not dollar amount).

    Used for proportional salary distribution within a cap budget.
    Higher value = larger share of team salary.
    """
    overall = player.overall

    # Base value from OVR (exponential-ish scaling)
    if overall >= 95:
        base = 100 + (overall - 95) * 15
    elif overall >= 90:
        base = 50 + (overall - 90) * 10
    elif overall >= 85:
        base = 25 + (overall - 85) * 5
    elif overall >= 80:
        base = 12 + (overall - 80) * 2.6
    elif overall >= 75:
        base = 6 + (overall - 75) * 1.2
    elif overall >= 70:
        base = 3 + (overall - 70) * 0.6
    else:
        base = 1 + max(0, (overall - 60)) * 0.2

    # Position multiplier
    pos_mult = POSITION_VALUE_MULTIPLIERS.get(player.position.value, 1.0)
    base *= pos_mult

    # Age adjustment
    age_mult = AGE_VALUE_CURVE.get(player.age, 0.20)
    if player.age < 21:
        age_mult = 0.75
    base *= age_mult

    return max(1.0, base)  # Minimum weight of 1


def generate_roster_contracts(
    roster: "Roster",
    salary_cap: int = 255_000,
    target_cap_room: int = 30_000,
    min_salary: int = 900,
    variance: float = 0.15,
) -> None:
    """
    Assign contracts to all players on a roster using constrained optimization.

    Instead of assigning market-rate salaries that may exceed cap,
    this distributes a fixed budget proportionally based on player value.

    Args:
        roster: The roster to assign contracts to
        salary_cap: Team salary cap (in thousands)
        target_cap_room: Target remaining cap space (in thousands)
        min_salary: Minimum player salary (in thousands)
        variance: Random variance factor (0.0-0.3) for salary variety
    """
    players = list(roster.players.values())
    if not players:
        return

    # Calculate relative values for all players
    relative_values = [calculate_relative_value(p) for p in players]
    total_value = sum(relative_values)

    # Budget = cap - target room
    budget = salary_cap - target_cap_room

    # Reserve minimum salary for each player first
    reserved = min_salary * len(players)
    distributable = budget - reserved

    if distributable < 0:
        # Not enough budget even for minimums - just assign minimums
        distributable = 0

    # Distribute remaining budget proportionally
    for i, player in enumerate(players):
        # Skip if player already has contract
        if player.contract_years is not None:
            continue

        # Base salary from proportional share + minimum
        share = relative_values[i] / total_value
        base_salary = min_salary + int(distributable * share)

        # Add some variance so teams aren't identical
        if variance > 0:
            var_factor = 1.0 + random.uniform(-variance, variance)
            base_salary = int(base_salary * var_factor)

        # Ensure minimum
        base_salary = max(min_salary, base_salary)

        # Contract length based on age and value tier
        value_percentile = relative_values[i] / max(relative_values)
        if player.age >= 32:
            years = random.choice([1, 2])
        elif player.age >= 29:
            years = random.choice([2, 3])
        elif value_percentile >= 0.7:
            years = random.choice([4, 5])
        elif value_percentile >= 0.3:
            years = random.choice([3, 4])
        else:
            years = random.choice([2, 3])

        # Randomize years remaining (simulate mid-contract)
        years_remaining = random.randint(1, years)

        # Signing bonus: 15-30% of total value for good players
        if value_percentile >= 0.5:
            bonus_pct = random.uniform(0.15, 0.30)
        else:
            bonus_pct = random.uniform(0.05, 0.15)

        total_value_contract = base_salary * years
        signing_bonus = int(total_value_contract * bonus_pct)

        # Remaining bonus (prorated)
        bonus_per_year = signing_bonus // years if years > 0 else 0
        remaining_bonus = bonus_per_year * years_remaining

        # Assign to player
        player.contract_years = years
        player.contract_year_remaining = years_remaining
        player.salary = base_salary
        player.signing_bonus = signing_bonus
        player.signing_bonus_remaining = remaining_bonus
