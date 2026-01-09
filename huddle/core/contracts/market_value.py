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
#
# These reflect MARKET RATES (what teams actually pay), NOT optimal allocation.
# The market has known inefficiencies that create opportunities for smart GMs:
#
# RESEARCH FINDINGS (Calvetti 2023, Mulholland-Jensen 2019):
#   Overvalued by market: LT (blind side myth), RB (replaceable but paid)
#   Undervalued by market: Guards, RT, Interior D-line, ILB
#   High variance (R²): QB=0.06, RB=0.04 (salary poorly predicts performance)
#   Low variance (R²): LT=0.44, RT=0.39 (salary correlates with performance)
#
# For "smart GM" AI, see OPTIMAL_ALLOCATION below.
#
POSITION_VALUE_MULTIPLIERS = {
    "QB": 5.0,    # Franchise QBs - market pays premium despite low R² (0.06)
    "DE": 2.5,    # Elite pass rushers
    "DT": 1.8,    # Interior pressure (undervalued - optimal is higher)
    "CB": 2.0,    # Shutdown corners
    "WR": 2.2,    # Elite receivers
    "LT": 2.0,    # Blind side premium - OVERVALUED by market (optimal: 1.2-5%)
    "RT": 1.5,    # Right tackle - UNDERVALUED by market (optimal: 7.8%)
    "TE": 1.3,    # Receiving tight ends
    "SS": 1.2,    # Strong safety
    "FS": 1.2,    # Free safety
    "OLB": 1.6,   # Edge rushers from OLB (undervalued - optimal: 15.2%!)
    "MLB": 1.0,   # Middle linebacker
    "ILB": 0.9,   # Inside linebacker - market undervalues (optimal: 10%)
    "RB": 0.8,    # Running backs - market still overpays (optimal: 0.8%)
    "LG": 1.1,    # Guards - SEVERELY UNDERVALUED (optimal: 12.4% vs 5.8% actual)
    "RG": 1.1,    # Same inefficiency
    "C": 1.1,     # Centers undervalued
    "FB": 0.5,    # Fullbacks (niche role)
    "NT": 0.9,    # Nose tackle
    "K": 0.4,     # Kickers
    "P": 0.4,     # Punters
    "LS": 0.3,    # Long snappers
}

# Optimal allocation for winning (research-backed) - use for smart AI GMs
# These are per-player percentages of cap (divide by # starters for positions with 2+)
OPTIMAL_ALLOCATION = {
    "QB": 8.6,    # But high variance - risky investment
    "OLB": 7.6,   # Per OLB (15.2% / 2)
    "DE": 6.9,    # Per DE (13.7% / 2)
    "LG": 6.2,    # Per Guard (12.4% / 2)
    "RG": 6.2,
    "DT": 5.1,    # Per DT (10.2% / 2)
    "ILB": 5.0,   # Per ILB (10% / 2)
    "LT": 1.2,    # Single position - much lower than market pays!
    "RT": 2.5,    # Single position
    "CB": 3.6,    # Per CB (7.1% / 2)
    "FS": 4.4,    # Single position
    "SS": 3.2,    # Single position
    "WR": 1.9,    # Per WR (5.6% / 3)
    "C": 1.9,     # Single position
    "RB": 0.8,    # Single position - highly replaceable
    "TE": 0.35,   # Per TE (0.7% / 2)
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

    Key insight: Position determines the CEILING, overall determines
    where you fall within your position's pay scale.
    - Elite QB: $50-55M
    - Good QB: $30-40M
    - Elite ILB: $12-16M
    - Good ILB: $6-10M

    Args:
        player: The player to evaluate
        position_scarcity: League-wide position scarcity (0.5-1.5)
        team_need: How much team needs this position (0.0-1.0)

    Returns:
        MarketValue with recommended contract terms
    """
    overall = player.overall
    pos_mult = POSITION_VALUE_MULTIPLIERS.get(player.position.value, 1.0)

    # Position-specific salary ceilings (in thousands, so 55000 = $55M)
    # These reflect MARKET rates - what elite players at each position actually earn.
    # The market has inefficiencies (LT overpaid, Guards underpaid) - that's realistic.
    POSITION_CEILINGS = {
        "QB": 55000,   # Elite QBs get $55M
        "DE": 32000,   # Elite EDGE
        "WR": 30000,   # Elite WR
        "DT": 25000,   # Elite DT
        "CB": 23000,   # Elite CB
        "LT": 23000,   # Elite LT - market pays premium (overvalued per research)
        "OLB": 20000,  # Elite OLB
        "RT": 18000,   # RT gets less than LT (market inefficiency)
        "TE": 18000,   # Elite TE
        "SS": 15000,
        "FS": 15000,
        "MLB": 14000,
        "ILB": 14000,  # Elite ILB - market undervalues
        "C": 14000,
        "LG": 14000,   # Guards underpaid by market (12.4% optimal vs 5.8% actual)
        "RG": 14000,
        "RB": 12000,   # RBs - market still pays but replaceable
        "NT": 12000,
        "FB": 4000,
        "K": 6000,
        "P": 4000,
        "LS": 1500,
    }

    ceiling = POSITION_CEILINGS.get(player.position.value, 15000)
    is_qb = player.position.value == "QB"

    # Calculate what percentage of ceiling this player earns based on OVR
    # QBs have an EXPONENTIAL curve - elite QBs are worth exponentially more
    # because of extreme scarcity (only 5-8 elite QBs in the whole league)
    #
    # Non-QB positions use a more linear scale

    if is_qb:
        # QB exponential market: the difference between 85 and 90 OVR QB
        # is worth WAY more than the difference between 75 and 80
        # Real NFL: Dak ($40M) vs Mahomes ($55M) - small gap in skill, huge gap in pay
        if overall >= 92:
            # Elite tier - bidding wars, franchise-altering talent
            pct = 0.85 + (overall - 92) * 0.03  # 85-100%+ (can exceed ceiling)
        elif overall >= 88:
            # Pro Bowl tier - teams will pay premium
            pct = 0.60 + (overall - 88) * 0.0625  # 60-85%
        elif overall >= 84:
            # Solid starter - bridge/stop-gap money
            pct = 0.35 + (overall - 84) * 0.0625  # 35-60%
        elif overall >= 80:
            # Replacement level - backup money or prove-it deal
            pct = 0.15 + (overall - 80) * 0.05  # 15-35%
        elif overall >= 75:
            # Backup tier
            pct = 0.06 + (overall - 75) * 0.018  # 6-15%
        else:
            # Third string / practice squad
            pct = 0.03  # ~$1.5M minimum
    else:
        # Non-QB positions: more linear scale
        # Elite (95+): 90-100% of ceiling
        # Star (90-94): 65-90% of ceiling
        # Starter (85-89): 40-65% of ceiling
        # Solid (80-84): 20-40% of ceiling
        # Rotational (75-79): 10-20% of ceiling
        # Depth (70-74): 5-10% of ceiling
        # Backup (65-69): 3-5% of ceiling
        # Filler (<65): minimum salary

        if overall >= 95:
            pct = 0.90 + (overall - 95) * 0.02  # 90-100%
        elif overall >= 90:
            pct = 0.65 + (overall - 90) * 0.05  # 65-90%
        elif overall >= 85:
            pct = 0.40 + (overall - 85) * 0.05  # 40-65%
        elif overall >= 80:
            pct = 0.20 + (overall - 80) * 0.04  # 20-40%
        elif overall >= 75:
            pct = 0.10 + (overall - 75) * 0.02  # 10-20%
        elif overall >= 70:
            pct = 0.05 + (overall - 70) * 0.01  # 5-10%
        elif overall >= 65:
            pct = 0.03 + (overall - 65) * 0.004  # 3-5%
        else:
            pct = 0.02  # Minimum ~2% of ceiling

    base = int(ceiling * pct)

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

    Key insight: Position value should dominate OVR value because a mediocre
    QB is worth more than an elite ILB due to positional scarcity and impact.

    QBs specifically have an exponential curve - elite QBs are worth
    exponentially more due to extreme scarcity in the NFL.
    """
    overall = player.overall
    is_qb = player.position.value == "QB"

    if is_qb:
        # QB exponential curve - elite QBs are MASSIVELY more valuable
        # This mirrors the intense bidding war market for franchise QBs
        if overall >= 92:
            base = 200 + (overall - 92) * 30  # 200-320+
        elif overall >= 88:
            base = 120 + (overall - 88) * 20  # 120-200
        elif overall >= 84:
            base = 70 + (overall - 84) * 12.5  # 70-120
        elif overall >= 80:
            base = 40 + (overall - 80) * 7.5  # 40-70
        elif overall >= 75:
            base = 20 + (overall - 75) * 4  # 20-40
        else:
            base = 8 + max(0, (overall - 65)) * 1.2  # 8-20
    else:
        # Non-QB positions: flatter OVR curve, position multiplier dominates
        if overall >= 95:
            base = 80 + (overall - 95) * 5  # 80-100
        elif overall >= 90:
            base = 60 + (overall - 90) * 4  # 60-80
        elif overall >= 85:
            base = 45 + (overall - 85) * 3  # 45-60
        elif overall >= 80:
            base = 30 + (overall - 80) * 3  # 30-45
        elif overall >= 75:
            base = 20 + (overall - 75) * 2  # 20-30
        elif overall >= 70:
            base = 12 + (overall - 70) * 1.6  # 12-20
        else:
            base = 5 + max(0, (overall - 60)) * 0.7  # 5-12

        # Apply position multiplier for non-QBs
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
    variance: float = 0.10,
) -> None:
    """
    Assign contracts to all players on a roster using calibrated NFL market data.

    Uses real NFL position tier data from research/exports/contract_model.json
    for realistic contract values. When total market values exceed cap budget,
    scales all contracts proportionally while maintaining relative differences.

    Args:
        roster: The roster to assign contracts to
        salary_cap: Team salary cap (in thousands)
        target_cap_room: Target remaining cap space (in thousands)
        min_salary: Minimum player salary (in thousands)
        variance: Random variance factor (0.0-0.3) for salary variety
    """
    from huddle.generators.calibration import calculate_contract_value

    players = list(roster.players.values())
    if not players:
        return

    # Budget = cap - target room (e.g., $255M - $30M = $225M)
    budget = salary_cap - target_cap_room

    # Get calibrated market values for all players
    market_data = []
    for player in players:
        cv = calculate_contract_value(
            position=player.position.value,
            overall=player.overall,
            age=player.age,
        )
        # Convert from millions to thousands
        market_salary = int(cv["apy_millions"] * 1000)
        market_data.append({
            "salary": max(min_salary, market_salary),
            "years": cv["years"],
            "guaranteed_pct": cv["guaranteed_pct"],
            "tier": cv["tier"],
        })

    # Calculate total market value
    total_market = sum(md["salary"] for md in market_data)

    # Calculate scaling factor if over budget
    # We preserve minimum salary floor, so only scale the "excess" portion
    min_reserved = min_salary * len(players)
    scalable_budget = budget - min_reserved
    scalable_market = total_market - min_reserved

    if scalable_market > 0 and total_market > budget:
        scale_factor = scalable_budget / scalable_market
    else:
        scale_factor = 1.0

    # Assign contracts to each player
    for i, player in enumerate(players):
        # Skip if player already has contract
        if player.contract_years is not None:
            continue

        md = market_data[i]
        market_salary = md["salary"]

        # Scale salary: min_salary + scaled portion above minimum
        if scale_factor < 1.0:
            scaled_salary = min_salary + int((market_salary - min_salary) * scale_factor)
        else:
            scaled_salary = market_salary

        # Add variance for variety across teams
        if variance > 0:
            var_factor = 1.0 + random.uniform(-variance, variance)
            scaled_salary = int(scaled_salary * var_factor)

        # Ensure minimum
        scaled_salary = max(min_salary, scaled_salary)

        # Contract length from calibration data
        years = md["years"]

        # Randomize years remaining (simulate mid-contract)
        years_remaining = random.randint(1, years)

        # Signing bonus based on tier's guaranteed percentage
        total_value_contract = scaled_salary * years
        bonus_pct = md["guaranteed_pct"] * 0.5  # Half of guaranteed is signing bonus
        signing_bonus = int(total_value_contract * bonus_pct)

        # Remaining bonus (prorated)
        bonus_per_year = signing_bonus // years if years > 0 else 0
        remaining_bonus = bonus_per_year * years_remaining

        # Assign to player
        player.contract_years = years
        player.contract_year_remaining = years_remaining
        player.salary = scaled_salary
        player.signing_bonus = signing_bonus
        player.signing_bonus_remaining = remaining_bonus
