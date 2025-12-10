"""
Team Identity and Philosophy System.

This module defines the characteristics that make each team unique:
- Offensive/Defensive schemes
- Personnel preferences
- Team building philosophy
- AI decision-making tendencies

These identities influence:
- Player generation (run-heavy teams get better OL/RBs)
- AI roster decisions (draft, free agency, trades)
- Game simulation (play calling tendencies)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import random


# =============================================================================
# Offensive Schemes
# =============================================================================


class OffensiveScheme(Enum):
    """The team's offensive identity/philosophy."""

    # Run-first schemes
    POWER_RUN = auto()  # Traditional smashmouth, strong OL, power backs
    ZONE_RUN = auto()  # Outside zone, athletic OL, one-cut backs
    OPTION = auto()  # Read option, mobile QB, versatile backs

    # Balanced schemes
    WEST_COAST = auto()  # Short passing game, YAC, timing routes
    PRO_STYLE = auto()  # Traditional NFL offense, balanced
    PISTOL = auto()  # Hybrid run/pass, pre-snap motion

    # Pass-first schemes
    AIR_RAID = auto()  # 4-5 WR sets, vertical passing, tempo
    SPREAD = auto()  # Spread formation, RPOs, mobile QB
    VERTICAL = auto()  # Deep shots, big-play receivers


class DefensiveScheme(Enum):
    """The team's defensive identity/philosophy."""

    # Base defenses
    DEFENSE_4_3 = auto()  # 4 DL, 3 LB - traditional, balanced
    DEFENSE_3_4 = auto()  # 3 DL, 4 LB - versatile, pass rush from LBs
    HYBRID = auto()  # Multiple fronts, sub packages

    # Coverage emphasis
    MAN_PRESS = auto()  # Aggressive man coverage, press at line
    COVER_2 = auto()  # Tampa 2 style, two deep safeties
    COVER_3 = auto()  # Single high safety, pattern matching
    QUARTERS = auto()  # Cover 4, prevent big plays

    # Aggressive styles
    BLITZ_HEAVY = auto()  # Frequent blitzes, disguised pressures
    BEND_DONT_BREAK = auto()  # Conservative, prevent big plays


# =============================================================================
# Personnel Preferences (affects drafting/signing)
# =============================================================================


class PersonnelPreference(Enum):
    """What the team values in players."""

    SPEED_OVER_STRENGTH = auto()  # Prefer athletic, fast players
    STRENGTH_OVER_SPEED = auto()  # Prefer powerful, physical players
    BALANCED_ATHLETICISM = auto()  # No strong preference

    POTENTIAL_OVER_PRODUCTION = auto()  # Prefer high-ceiling raw players
    PRODUCTION_OVER_POTENTIAL = auto()  # Prefer proven, polished players
    BALANCED_PROJECTION = auto()  # No strong preference

    YOUTH_MOVEMENT = auto()  # Prefer young players, build for future
    WIN_NOW = auto()  # Prefer veterans, compete immediately
    BALANCED_AGE = auto()  # Mix of youth and experience


class DraftPhilosophy(Enum):
    """How the team approaches the draft."""

    BEST_AVAILABLE = auto()  # Always take highest-rated player
    DRAFT_FOR_NEED = auto()  # Fill roster holes
    VALUE_BASED = auto()  # Balance of need and value

    TRADE_UP_AGGRESSIVE = auto()  # Will overpay to move up for "their guy"
    TRADE_DOWN_AGGRESSIVE = auto()  # Accumulate picks, quantity over quality
    STAY_PUT = auto()  # Rarely trades draft picks


class TradePhilosophy(Enum):
    """How the team approaches trades (from NFL HC09)."""

    HEAVY_TRADER = auto()  # Actively shops players/picks
    LIGHT_TRADER = auto()  # Rarely initiates trades
    MODERATE_TRADER = auto()  # Average trade activity

    # Negotiation style
    LOW_BALL = auto()  # Starts 20% below market value
    OVER_OFFER = auto()  # Starts 10% above to secure quickly
    HAGGLE = auto()  # Multiple counter-offers


class FreeAgencyPhilosophy(Enum):
    """How the team approaches free agency."""

    BIG_SPENDER = auto()  # Aggressive, will overpay for stars
    BARGAIN_HUNTER = auto()  # Looks for value, avoids big contracts
    MODERATE_SPENDER = auto()  # Average spending

    FAVOR_OWN_PLAYERS = auto()  # Prioritizes re-signing own players
    FAVOR_OUTSIDE_PLAYERS = auto()  # Looks externally for upgrades
    BALANCED_RETENTION = auto()  # No strong preference


# =============================================================================
# Team Identity (combines all philosophies)
# =============================================================================


@dataclass
class TeamIdentity:
    """
    Complete identity profile for a team.

    This defines WHO the team is - their schemes, preferences, and
    decision-making tendencies. Used for:
    - Player generation tuning
    - AI decision making
    - Play calling in simulation
    """

    # Schemes
    offensive_scheme: OffensiveScheme = OffensiveScheme.PRO_STYLE
    defensive_scheme: DefensiveScheme = DefensiveScheme.DEFENSE_4_3

    # Personnel preferences
    athleticism_preference: PersonnelPreference = (
        PersonnelPreference.BALANCED_ATHLETICISM
    )
    projection_preference: PersonnelPreference = PersonnelPreference.BALANCED_PROJECTION
    age_preference: PersonnelPreference = PersonnelPreference.BALANCED_AGE

    # Team building
    draft_philosophy: DraftPhilosophy = DraftPhilosophy.VALUE_BASED
    trade_philosophy: TradePhilosophy = TradePhilosophy.MODERATE_TRADER
    trade_negotiation: TradePhilosophy = TradePhilosophy.HAGGLE
    free_agency_philosophy: FreeAgencyPhilosophy = (
        FreeAgencyPhilosophy.MODERATE_SPENDER
    )
    retention_philosophy: FreeAgencyPhilosophy = FreeAgencyPhilosophy.BALANCED_RETENTION

    # Tendencies (0.0 to 1.0) - used in game simulation
    run_tendency: float = 0.5  # Higher = more runs
    aggression: float = 0.5  # Higher = more aggressive (4th down, 2pt)
    blitz_tendency: float = 0.3  # Higher = more blitzes
    tempo: float = 0.5  # Higher = faster pace

    def get_position_boost(self, position: str) -> float:
        """
        Get the overall rating boost/penalty for a position based on scheme.

        Returns a modifier (-10 to +10) applied to generated players.
        Scheme-specific positions get better players.
        """
        boosts: dict[str, float] = {}

        # Offensive scheme boosts
        if self.offensive_scheme == OffensiveScheme.POWER_RUN:
            boosts = {
                "RB": 5,
                "FB": 8,
                "LT": 5,
                "LG": 7,
                "C": 5,
                "RG": 7,
                "RT": 5,
                "TE": 3,
                "WR": -3,
            }
        elif self.offensive_scheme == OffensiveScheme.ZONE_RUN:
            boosts = {
                "RB": 5,
                "LT": 6,
                "LG": 6,
                "C": 6,
                "RG": 6,
                "RT": 6,
                "TE": 3,
            }
        elif self.offensive_scheme == OffensiveScheme.AIR_RAID:
            boosts = {
                "QB": 7,
                "WR": 8,
                "TE": -3,
                "RB": -5,
                "FB": -10,
                "LT": 3,
            }
        elif self.offensive_scheme == OffensiveScheme.SPREAD:
            boosts = {"QB": 5, "WR": 5, "RB": 3, "TE": -2}
        elif self.offensive_scheme == OffensiveScheme.WEST_COAST:
            boosts = {"QB": 5, "WR": 5, "TE": 5, "RB": 3}
        elif self.offensive_scheme == OffensiveScheme.VERTICAL:
            boosts = {"QB": 7, "WR": 7, "TE": 3}
        elif self.offensive_scheme == OffensiveScheme.OPTION:
            boosts = {"QB": 3, "RB": 5}

        # Defensive scheme boosts
        if self.defensive_scheme == DefensiveScheme.DEFENSE_4_3:
            boosts.update({"DE": 5, "DT": 3, "MLB": 5})
        elif self.defensive_scheme == DefensiveScheme.DEFENSE_3_4:
            boosts.update({"DT": -3, "NT": 8, "OLB": 7, "ILB": 5, "DE": -2})
        elif self.defensive_scheme == DefensiveScheme.MAN_PRESS:
            boosts.update({"CB": 7, "SS": 3})
        elif self.defensive_scheme == DefensiveScheme.COVER_2:
            boosts.update({"FS": 5, "SS": 5, "CB": 3, "MLB": 5})
        elif self.defensive_scheme == DefensiveScheme.BLITZ_HEAVY:
            boosts.update({"OLB": 5, "SS": 5, "CB": 3})

        return boosts.get(position, 0)

    def get_attribute_emphasis(self, position: str) -> dict[str, float]:
        """
        Get attribute emphasis modifiers based on scheme.

        Returns dict of attribute_name -> modifier (0.8 to 1.2).
        Used to skew attribute generation for scheme-specific builds.
        """
        emphasis: dict[str, float] = {}

        # Speed vs Strength preference
        if self.athleticism_preference == PersonnelPreference.SPEED_OVER_STRENGTH:
            emphasis["speed"] = 1.1
            emphasis["acceleration"] = 1.1
            emphasis["agility"] = 1.1
            emphasis["strength"] = 0.9
        elif self.athleticism_preference == PersonnelPreference.STRENGTH_OVER_SPEED:
            emphasis["strength"] = 1.1
            emphasis["trucking"] = 1.1
            emphasis["speed"] = 0.95

        # Scheme-specific emphasis
        if self.offensive_scheme == OffensiveScheme.POWER_RUN:
            emphasis["run_block"] = 1.15
            emphasis["strength"] = 1.1
            emphasis["trucking"] = 1.1
            emphasis["break_tackle"] = 1.1
        elif self.offensive_scheme == OffensiveScheme.ZONE_RUN:
            emphasis["agility"] = 1.1
            emphasis["ball_carrier_vision"] = 1.15
            emphasis["speed"] = 1.05
        elif self.offensive_scheme == OffensiveScheme.AIR_RAID:
            emphasis["throw_accuracy_deep"] = 1.1
            emphasis["throw_power"] = 1.1
            emphasis["speed"] = 1.1
            emphasis["route_running"] = 1.1
        elif self.offensive_scheme == OffensiveScheme.WEST_COAST:
            emphasis["throw_accuracy_short"] = 1.15
            emphasis["catching"] = 1.1
            emphasis["route_running"] = 1.1

        if self.defensive_scheme == DefensiveScheme.MAN_PRESS:
            emphasis["man_coverage"] = 1.15
            emphasis["press"] = 1.15
            emphasis["speed"] = 1.1
        elif self.defensive_scheme == DefensiveScheme.BLITZ_HEAVY:
            emphasis["finesse_moves"] = 1.1
            emphasis["power_moves"] = 1.1
            emphasis["pursuit"] = 1.1

        return emphasis


# =============================================================================
# Predefined Team Identities (based on real NFL tendencies)
# =============================================================================


def create_identity_power_run() -> TeamIdentity:
    """Create a power run team identity (e.g., Ravens, Titans style)."""
    return TeamIdentity(
        offensive_scheme=OffensiveScheme.POWER_RUN,
        defensive_scheme=DefensiveScheme.DEFENSE_3_4,
        athleticism_preference=PersonnelPreference.STRENGTH_OVER_SPEED,
        projection_preference=PersonnelPreference.PRODUCTION_OVER_POTENTIAL,
        run_tendency=0.65,
        aggression=0.6,
        blitz_tendency=0.35,
        tempo=0.4,
    )


def create_identity_air_raid() -> TeamIdentity:
    """Create an air raid passing team identity (e.g., Chiefs, Dolphins style)."""
    return TeamIdentity(
        offensive_scheme=OffensiveScheme.AIR_RAID,
        defensive_scheme=DefensiveScheme.MAN_PRESS,
        athleticism_preference=PersonnelPreference.SPEED_OVER_STRENGTH,
        projection_preference=PersonnelPreference.POTENTIAL_OVER_PRODUCTION,
        run_tendency=0.35,
        aggression=0.7,
        blitz_tendency=0.4,
        tempo=0.7,
    )


def create_identity_west_coast() -> TeamIdentity:
    """Create a west coast team identity (e.g., 49ers style)."""
    return TeamIdentity(
        offensive_scheme=OffensiveScheme.WEST_COAST,
        defensive_scheme=DefensiveScheme.COVER_3,
        athleticism_preference=PersonnelPreference.BALANCED_ATHLETICISM,
        run_tendency=0.48,
        aggression=0.5,
        blitz_tendency=0.25,
        tempo=0.55,
    )


def create_identity_defensive() -> TeamIdentity:
    """Create a defense-first team identity (e.g., Bears, Steelers style)."""
    return TeamIdentity(
        offensive_scheme=OffensiveScheme.PRO_STYLE,
        defensive_scheme=DefensiveScheme.BLITZ_HEAVY,
        athleticism_preference=PersonnelPreference.STRENGTH_OVER_SPEED,
        projection_preference=PersonnelPreference.PRODUCTION_OVER_POTENTIAL,
        run_tendency=0.52,
        aggression=0.55,
        blitz_tendency=0.5,
        tempo=0.45,
    )


def create_identity_balanced() -> TeamIdentity:
    """Create a balanced pro-style identity."""
    return TeamIdentity(
        offensive_scheme=OffensiveScheme.PRO_STYLE,
        defensive_scheme=DefensiveScheme.DEFENSE_4_3,
        athleticism_preference=PersonnelPreference.BALANCED_ATHLETICISM,
        projection_preference=PersonnelPreference.BALANCED_PROJECTION,
        age_preference=PersonnelPreference.BALANCED_AGE,
        run_tendency=0.5,
        aggression=0.5,
        blitz_tendency=0.3,
        tempo=0.5,
    )


def create_random_identity() -> TeamIdentity:
    """Create a randomized team identity."""
    return TeamIdentity(
        offensive_scheme=random.choice(list(OffensiveScheme)),
        defensive_scheme=random.choice(list(DefensiveScheme)),
        athleticism_preference=random.choice(
            [
                PersonnelPreference.SPEED_OVER_STRENGTH,
                PersonnelPreference.STRENGTH_OVER_SPEED,
                PersonnelPreference.BALANCED_ATHLETICISM,
            ]
        ),
        projection_preference=random.choice(
            [
                PersonnelPreference.POTENTIAL_OVER_PRODUCTION,
                PersonnelPreference.PRODUCTION_OVER_POTENTIAL,
                PersonnelPreference.BALANCED_PROJECTION,
            ]
        ),
        age_preference=random.choice(
            [
                PersonnelPreference.YOUTH_MOVEMENT,
                PersonnelPreference.WIN_NOW,
                PersonnelPreference.BALANCED_AGE,
            ]
        ),
        draft_philosophy=random.choice(list(DraftPhilosophy)),
        trade_philosophy=random.choice(
            [
                TradePhilosophy.HEAVY_TRADER,
                TradePhilosophy.LIGHT_TRADER,
                TradePhilosophy.MODERATE_TRADER,
            ]
        ),
        trade_negotiation=random.choice(
            [TradePhilosophy.LOW_BALL, TradePhilosophy.OVER_OFFER, TradePhilosophy.HAGGLE]
        ),
        free_agency_philosophy=random.choice(
            [
                FreeAgencyPhilosophy.BIG_SPENDER,
                FreeAgencyPhilosophy.BARGAIN_HUNTER,
                FreeAgencyPhilosophy.MODERATE_SPENDER,
            ]
        ),
        run_tendency=random.uniform(0.35, 0.65),
        aggression=random.uniform(0.3, 0.7),
        blitz_tendency=random.uniform(0.2, 0.5),
        tempo=random.uniform(0.4, 0.7),
    )


# =============================================================================
# Positional Philosophy (affects how OVR is calculated for specific positions)
# =============================================================================


class PositionalPhilosophy(Enum):
    """Position-specific player preferences that alter OVR calculation."""

    # Wide Receiver Philosophy
    WR_SPEED = auto()  # Prioritize speed, deep threat
    WR_POSSESSION = auto()  # Prioritize catching, route running
    WR_BALANCED = auto()

    # Running Back Philosophy
    RB_POWER = auto()  # Prioritize trucking, break tackle
    RB_SPEED = auto()  # Prioritize speed, elusiveness
    RB_RECEIVING = auto()  # Prioritize catching, pass blocking
    RB_BALANCED = auto()

    # Tight End Philosophy
    TE_RECEIVING = auto()  # Prioritize receiving skills
    TE_BLOCKING = auto()  # Prioritize blocking skills
    TE_BALANCED = auto()

    # Offensive Line Philosophy
    OL_PASS_PROTECT = auto()  # Prioritize pass blocking
    OL_RUN_BLOCK = auto()  # Prioritize run blocking
    OL_BALANCED = auto()

    # Cornerback Philosophy
    CB_MAN_PRESS = auto()  # Prioritize man coverage, press
    CB_ZONE = auto()  # Prioritize zone coverage
    CB_BALANCED = auto()

    # Linebacker Philosophy
    LB_RUN_STUFF = auto()  # Prioritize tackling, block shed
    LB_COVERAGE = auto()  # Prioritize coverage skills
    LB_PASS_RUSH = auto()  # Prioritize pass rush moves
    LB_BALANCED = auto()


# =============================================================================
# Cap Management Style
# =============================================================================


class CapManagementStyle(Enum):
    """How the team manages their salary cap."""

    SPEND_TO_CAP = auto()  # Always near cap limit, maximize talent now
    MODERATE = auto()  # Balance spending with flexibility
    THRIFTY = auto()  # Conservative, maintain cap flexibility
    REBUILDING = auto()  # Dump salary, accumulate assets


# =============================================================================
# Team Financials (Salary Cap State)
# =============================================================================


@dataclass
class TeamFinancials:
    """
    Financial state of a team for salary cap management.

    Based on NFL HC09's cap system where cutting/trading players
    with bonuses accelerates "dead money" penalties.

    Supports:
    - Multi-year dead money tracking (for June 1 cuts)
    - Contract restructuring (convert salary to bonus)
    - Detailed cap projections
    """

    # Cap numbers (in thousands, e.g., 250000 = $250M)
    salary_cap: int = 255_000  # NFL salary cap (~$255M in 2024)
    total_salary: int = 0  # Sum of all player salaries
    dead_money: int = 0  # Cap hit from cut/traded players (this year)
    dead_money_next_year: int = 0  # Dead money that carries to next year (June 1 cuts)
    cap_penalties: int = 0  # Fines for cap violations

    @property
    def cap_room(self) -> int:
        """Available cap space."""
        return self.salary_cap - self.total_salary - self.dead_money - self.cap_penalties

    @property
    def cap_used_pct(self) -> float:
        """Percentage of cap used."""
        return (self.total_salary + self.dead_money + self.cap_penalties) / self.salary_cap

    @property
    def total_cap_charge(self) -> int:
        """Total cap obligation."""
        return self.total_salary + self.dead_money + self.cap_penalties

    def can_sign(self, salary: int) -> bool:
        """Check if team can afford a new contract."""
        return self.cap_room >= salary

    def add_contract(self, salary: int) -> None:
        """Add a new contract to the cap."""
        self.total_salary += salary

    def cut_player(
        self,
        salary: int,
        remaining_bonus: int,
        june_1_cut: bool = False,
    ) -> tuple[int, int]:
        """
        Cut a player and handle cap implications.

        When a player is cut, their base salary is removed but
        any remaining signing bonus accelerates as dead money.

        June 1 cuts spread dead money over 2 years - useful for
        cutting players with large remaining bonuses.

        Args:
            salary: Player's annual salary
            remaining_bonus: Remaining signing bonus to accelerate
            june_1_cut: If True, split dead money over 2 years

        Returns:
            (this_year_dead, next_year_dead) - dead money incurred
        """
        self.total_salary -= salary

        if june_1_cut and remaining_bonus > 0:
            # Split dead money: half this year, half next year
            this_year = remaining_bonus // 2
            next_year = remaining_bonus - this_year
            self.dead_money += this_year
            self.dead_money_next_year += next_year
            return (this_year, next_year)
        else:
            # All dead money accelerates this year
            self.dead_money += remaining_bonus
            return (remaining_bonus, 0)

    def trade_player(self, salary: int, remaining_bonus: int) -> int:
        """
        Trade a player - same cap implications as cutting.

        The receiving team takes on the salary, but the original
        team keeps the dead money from the prorated bonus.

        Returns:
            Dead money incurred
        """
        self.total_salary -= salary
        self.dead_money += remaining_bonus
        return remaining_bonus

    def restructure_contract(
        self,
        current_salary: int,
        amount_to_convert: int,
        years_remaining: int,
    ) -> int:
        """
        Restructure a contract by converting salary to signing bonus.

        This creates immediate cap space but commits future cap dollars.
        The converted amount is prorated over remaining years.

        Args:
            current_salary: Player's current salary
            amount_to_convert: How much salary to convert to bonus
            years_remaining: Years left on contract (including this year)

        Returns:
            Cap savings this year
        """
        if amount_to_convert > current_salary:
            amount_to_convert = current_salary

        if years_remaining < 2:
            # Can't spread over less than 2 years
            return 0

        # Reduce salary
        self.total_salary -= amount_to_convert

        # Add prorated bonus back (smaller annual hit)
        prorated_hit = amount_to_convert // years_remaining
        self.total_salary += prorated_hit

        # The savings is the difference
        cap_savings = amount_to_convert - prorated_hit
        return cap_savings

    def new_season(self) -> None:
        """Reset for new season - process dead money, increase cap."""
        # Carry over next year's dead money
        self.dead_money = self.dead_money_next_year
        self.dead_money_next_year = 0
        self.cap_penalties = 0
        # Cap typically increases ~5-8% per year
        self.salary_cap = int(self.salary_cap * 1.06)

    def project_cap_room(self, years: int = 1) -> int:
        """
        Project cap room for a future year.

        Assumes current salary obligations but accounts for
        pending dead money.
        """
        if years == 0:
            return self.cap_room
        elif years == 1:
            # Next year: current cap * 1.06, current salary minus some expiring
            # This is approximate - actual depends on contract structures
            projected_cap = int(self.salary_cap * 1.06)
            projected_dead = self.dead_money_next_year
            # Assume some salary drops off (contracts expire)
            projected_salary = int(self.total_salary * 0.85)
            return projected_cap - projected_salary - projected_dead
        else:
            # Further out is speculative
            projected_cap = int(self.salary_cap * (1.06 ** years))
            projected_salary = int(self.total_salary * (0.85 ** years))
            return projected_cap - projected_salary


# =============================================================================
# Extended Team Identity (includes financials and positional preferences)
# =============================================================================


@dataclass
class ExtendedTeamIdentity(TeamIdentity):
    """
    Full team identity including financials and positional philosophies.

    Extends base TeamIdentity with:
    - Salary cap state and management style
    - Position-specific player preferences
    - Future pick valuation
    """

    # Financials
    financials: TeamFinancials = None  # type: ignore
    cap_management: CapManagementStyle = CapManagementStyle.MODERATE

    # Positional philosophies (affects OVR calculation and drafting)
    wr_philosophy: PositionalPhilosophy = PositionalPhilosophy.WR_BALANCED
    rb_philosophy: PositionalPhilosophy = PositionalPhilosophy.RB_BALANCED
    te_philosophy: PositionalPhilosophy = PositionalPhilosophy.TE_BALANCED
    ol_philosophy: PositionalPhilosophy = PositionalPhilosophy.OL_BALANCED
    cb_philosophy: PositionalPhilosophy = PositionalPhilosophy.CB_BALANCED
    lb_philosophy: PositionalPhilosophy = PositionalPhilosophy.LB_BALANCED

    # Future pick valuation (from NFL HC09)
    future_pick_value: str = "NEUTRAL"  # HOARD, NEUTRAL, TRADE_AWAY

    def __post_init__(self):
        if self.financials is None:
            self.financials = TeamFinancials()

    def get_positional_attribute_weights(self, position: str) -> dict[str, float]:
        """
        Get attribute weight modifiers based on positional philosophy.

        Returns multipliers for attribute importance in OVR calculation.
        """
        weights: dict[str, float] = {}

        if position == "WR":
            if self.wr_philosophy == PositionalPhilosophy.WR_SPEED:
                weights = {"speed": 1.3, "acceleration": 1.2, "catching": 0.9}
            elif self.wr_philosophy == PositionalPhilosophy.WR_POSSESSION:
                weights = {"catching": 1.3, "route_running": 1.2, "catch_in_traffic": 1.2, "speed": 0.9}

        elif position == "RB":
            if self.rb_philosophy == PositionalPhilosophy.RB_POWER:
                weights = {"trucking": 1.3, "break_tackle": 1.2, "strength": 1.2, "speed": 0.9}
            elif self.rb_philosophy == PositionalPhilosophy.RB_SPEED:
                weights = {"speed": 1.3, "acceleration": 1.2, "elusiveness": 1.2}
            elif self.rb_philosophy == PositionalPhilosophy.RB_RECEIVING:
                weights = {"catching": 1.3, "route_running": 1.2, "pass_block": 1.2}

        elif position == "TE":
            if self.te_philosophy == PositionalPhilosophy.TE_RECEIVING:
                weights = {"catching": 1.3, "route_running": 1.2, "speed": 1.1, "run_block": 0.8}
            elif self.te_philosophy == PositionalPhilosophy.TE_BLOCKING:
                weights = {"run_block": 1.3, "pass_block": 1.2, "strength": 1.1, "catching": 0.8}

        elif position in ["LT", "LG", "C", "RG", "RT"]:
            if self.ol_philosophy == PositionalPhilosophy.OL_PASS_PROTECT:
                weights = {"pass_block": 1.3, "awareness": 1.1, "run_block": 0.9}
            elif self.ol_philosophy == PositionalPhilosophy.OL_RUN_BLOCK:
                weights = {"run_block": 1.3, "strength": 1.1, "impact_blocking": 1.2, "pass_block": 0.9}

        elif position == "CB":
            if self.cb_philosophy == PositionalPhilosophy.CB_MAN_PRESS:
                weights = {"man_coverage": 1.3, "press": 1.3, "speed": 1.1, "zone_coverage": 0.8}
            elif self.cb_philosophy == PositionalPhilosophy.CB_ZONE:
                weights = {"zone_coverage": 1.3, "play_recognition": 1.2, "man_coverage": 0.9}

        elif position in ["MLB", "ILB", "OLB"]:
            if self.lb_philosophy == PositionalPhilosophy.LB_RUN_STUFF:
                weights = {"tackle": 1.3, "block_shedding": 1.2, "hit_power": 1.2}
            elif self.lb_philosophy == PositionalPhilosophy.LB_COVERAGE:
                weights = {"zone_coverage": 1.3, "man_coverage": 1.2, "speed": 1.1}
            elif self.lb_philosophy == PositionalPhilosophy.LB_PASS_RUSH:
                weights = {"finesse_moves": 1.3, "power_moves": 1.2, "speed": 1.1}

        return weights


# =============================================================================
# Scouting Grades (Hidden attributes revealed through scouting)
# =============================================================================


@dataclass
class ScoutingGrades:
    """
    Hidden grades revealed through the scouting funnel.

    These are NOT raw attributes - they're letter grades (A-F)
    that abstract the true values until fully scouted.
    """

    # Revealed at different scouting stages
    production_grade: Optional[str] = None  # A-F, college stats (Stage 1)
    athleticism_grade: Optional[str] = None  # A-F, combine results (Stage 2)
    intangibles_grade: Optional[str] = None  # A-F, interviews (Stage 2)
    durability_grade: Optional[str] = None  # A-F, medical (Stage 3)
    potential_grade: Optional[str] = None  # A-F, workouts only (Stage 4)

    # Track what's been revealed
    combine_attended: bool = False
    pro_day_attended: bool = False
    individual_workout: bool = False

    def letter_to_range(self, grade: str) -> tuple[int, int]:
        """Convert letter grade to approximate rating range."""
        ranges = {
            "A+": (95, 99),
            "A": (90, 94),
            "A-": (85, 89),
            "B+": (80, 84),
            "B": (75, 79),
            "B-": (70, 74),
            "C+": (65, 69),
            "C": (60, 64),
            "C-": (55, 59),
            "D+": (50, 54),
            "D": (45, 49),
            "D-": (40, 44),
            "F": (0, 39),
        }
        return ranges.get(grade, (50, 70))

    @staticmethod
    def rating_to_letter(rating: int) -> str:
        """Convert a 0-99 rating to a letter grade."""
        if rating >= 95:
            return "A+"
        elif rating >= 90:
            return "A"
        elif rating >= 85:
            return "A-"
        elif rating >= 80:
            return "B+"
        elif rating >= 75:
            return "B"
        elif rating >= 70:
            return "B-"
        elif rating >= 65:
            return "C+"
        elif rating >= 60:
            return "C"
        elif rating >= 55:
            return "C-"
        elif rating >= 50:
            return "D+"
        elif rating >= 45:
            return "D"
        elif rating >= 40:
            return "D-"
        else:
            return "F"
