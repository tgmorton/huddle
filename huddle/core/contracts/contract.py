"""
Full NFL-Style Contract System.

Contracts track:
- Multi-year terms with per-year salary structures
- Signing bonuses (prorated for cap)
- Guaranteed money
- Team/player options
- Void years for cap manipulation
- Dead money calculations
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import Optional
import random


class ContractType(Enum):
    """Type of contract affecting structure and rules."""
    ROOKIE = auto()          # First contract, slotted value
    ROOKIE_EXTENSION = auto() # Extension before rookie deal expires
    VETERAN = auto()         # Standard veteran contract
    FRANCHISE_TAG = auto()   # One-year franchise tag
    TRANSITION_TAG = auto()  # One-year transition tag
    MINIMUM = auto()         # League minimum deal
    PRACTICE_SQUAD = auto()  # Practice squad contract


class ContractStatus(Enum):
    """Current status of the contract."""
    ACTIVE = auto()          # Currently in effect
    EXPIRED = auto()         # Contract ended naturally
    TERMINATED = auto()      # Player was cut
    VOIDED = auto()          # Contract voided (violation, retirement)
    RESTRUCTURED = auto()    # Has been restructured (history tracking)


# Rookie wage scale by pick (values in thousands)
# Based on 2024 NFL rookie pool
ROOKIE_WAGE_SCALE = {
    # Round 1
    1: {"total": 41_200, "signing": 27_000, "years": 4, "fifth_year_option": True},
    2: {"total": 37_800, "signing": 24_500, "years": 4, "fifth_year_option": True},
    3: {"total": 34_600, "signing": 22_200, "years": 4, "fifth_year_option": True},
    4: {"total": 31_600, "signing": 20_100, "years": 4, "fifth_year_option": True},
    5: {"total": 28_900, "signing": 18_200, "years": 4, "fifth_year_option": True},
    10: {"total": 18_500, "signing": 10_800, "years": 4, "fifth_year_option": True},
    15: {"total": 13_200, "signing": 7_100, "years": 4, "fifth_year_option": True},
    20: {"total": 10_800, "signing": 5_400, "years": 4, "fifth_year_option": True},
    25: {"total": 9_200, "signing": 4_300, "years": 4, "fifth_year_option": True},
    32: {"total": 7_800, "signing": 3_400, "years": 4, "fifth_year_option": True},
    # Round 2
    33: {"total": 7_500, "signing": 3_200, "years": 4, "fifth_year_option": False},
    40: {"total": 6_200, "signing": 2_400, "years": 4, "fifth_year_option": False},
    50: {"total": 5_100, "signing": 1_800, "years": 4, "fifth_year_option": False},
    64: {"total": 4_400, "signing": 1_400, "years": 4, "fifth_year_option": False},
    # Round 3
    65: {"total": 4_300, "signing": 1_350, "years": 4, "fifth_year_option": False},
    80: {"total": 3_800, "signing": 1_100, "years": 4, "fifth_year_option": False},
    100: {"total": 3_500, "signing": 900, "years": 4, "fifth_year_option": False},
    # Round 4-7
    110: {"total": 3_400, "signing": 800, "years": 4, "fifth_year_option": False},
    140: {"total": 3_200, "signing": 600, "years": 4, "fifth_year_option": False},
    170: {"total": 3_100, "signing": 450, "years": 4, "fifth_year_option": False},
    200: {"total": 3_000, "signing": 350, "years": 4, "fifth_year_option": False},
    224: {"total": 2_950, "signing": 250, "years": 4, "fifth_year_option": False},
    # UDFA
    225: {"total": 2_800, "signing": 100, "years": 3, "fifth_year_option": False},
}


def get_rookie_contract_value(pick_number: int) -> dict:
    """Get rookie contract values for a pick, interpolating if needed."""
    if pick_number in ROOKIE_WAGE_SCALE:
        return ROOKIE_WAGE_SCALE[pick_number]

    # Interpolate between known values
    known_picks = sorted(ROOKIE_WAGE_SCALE.keys())

    if pick_number < known_picks[0]:
        return ROOKIE_WAGE_SCALE[known_picks[0]]
    if pick_number > known_picks[-1]:
        return ROOKIE_WAGE_SCALE[known_picks[-1]]

    # Find surrounding picks
    lower = max(p for p in known_picks if p <= pick_number)
    upper = min(p for p in known_picks if p >= pick_number)

    if lower == upper:
        return ROOKIE_WAGE_SCALE[lower]

    # Linear interpolation
    ratio = (pick_number - lower) / (upper - lower)
    lower_val = ROOKIE_WAGE_SCALE[lower]
    upper_val = ROOKIE_WAGE_SCALE[upper]

    return {
        "total": int(lower_val["total"] + (upper_val["total"] - lower_val["total"]) * ratio),
        "signing": int(lower_val["signing"] + (upper_val["signing"] - lower_val["signing"]) * ratio),
        "years": lower_val["years"],
        "fifth_year_option": lower_val["fifth_year_option"],
    }


@dataclass
class ContractYear:
    """Single year of a contract."""
    year_number: int          # 1-indexed year of contract
    base_salary: int          # Base salary for this year (thousands)
    roster_bonus: int = 0     # Roster bonus if on roster at trigger date
    workout_bonus: int = 0    # Workout/reporting bonus
    incentives: int = 0       # Performance incentives (likely to be earned)

    # Guarantees
    guaranteed_salary: int = 0     # Portion of base that's guaranteed
    guarantee_type: str = "none"   # "full", "injury", "skill", "none"

    # Options
    is_option_year: bool = False
    option_type: str = ""          # "team", "player", "void"
    option_exercised: bool = False
    option_deadline: Optional[date] = None

    @property
    def total_cash(self) -> int:
        """Total cash for this year (excluding prorated bonus)."""
        return self.base_salary + self.roster_bonus + self.workout_bonus + self.incentives

    def to_dict(self) -> dict:
        return {
            "year_number": self.year_number,
            "base_salary": self.base_salary,
            "roster_bonus": self.roster_bonus,
            "workout_bonus": self.workout_bonus,
            "incentives": self.incentives,
            "guaranteed_salary": self.guaranteed_salary,
            "guarantee_type": self.guarantee_type,
            "is_option_year": self.is_option_year,
            "option_type": self.option_type,
            "option_exercised": self.option_exercised,
            "option_deadline": self.option_deadline.isoformat() if self.option_deadline else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContractYear":
        return cls(
            year_number=data["year_number"],
            base_salary=data["base_salary"],
            roster_bonus=data.get("roster_bonus", 0),
            workout_bonus=data.get("workout_bonus", 0),
            incentives=data.get("incentives", 0),
            guaranteed_salary=data.get("guaranteed_salary", 0),
            guarantee_type=data.get("guarantee_type", "none"),
            is_option_year=data.get("is_option_year", False),
            option_type=data.get("option_type", ""),
            option_exercised=data.get("option_exercised", False),
            option_deadline=date.fromisoformat(data["option_deadline"]) if data.get("option_deadline") else None,
        )


@dataclass
class Contract:
    """
    Full NFL-style player contract.

    All monetary values in thousands (e.g., 15000 = $15M).
    """
    contract_id: str
    player_id: str
    team_id: str

    # Contract metadata
    contract_type: ContractType
    status: ContractStatus = ContractStatus.ACTIVE
    signed_date: Optional[date] = None

    # Structure
    total_years: int = 4
    current_year: int = 1      # 1-indexed, which year we're in
    years: list[ContractYear] = field(default_factory=list)

    # Signing bonus (prorated across all years for cap)
    signing_bonus: int = 0

    # Void years (count toward proration but player isn't actually signed)
    void_years: int = 0

    # Tracking
    original_team_id: str = ""  # Team that originally signed (for trade tracking)
    is_restructured: bool = False
    restructure_count: int = 0

    # Extensions
    extension_eligible: bool = False

    def __post_init__(self):
        if not self.original_team_id:
            self.original_team_id = self.team_id
        if not self.years and self.total_years > 0:
            # Generate default years if not provided
            self._generate_default_years()

    def _generate_default_years(self):
        """Generate default year structure based on contract type."""
        if self.contract_type == ContractType.MINIMUM:
            for i in range(self.total_years):
                self.years.append(ContractYear(
                    year_number=i + 1,
                    base_salary=1000,  # ~$1M minimum
                    guaranteed_salary=1000 if i == 0 else 0,
                    guarantee_type="full" if i == 0 else "none",
                ))
        else:
            # Escalating salary structure
            base = 2000
            for i in range(self.total_years):
                escalation = 1.0 + (i * 0.1)  # 10% increase per year
                self.years.append(ContractYear(
                    year_number=i + 1,
                    base_salary=int(base * escalation),
                ))

    @property
    def total_value(self) -> int:
        """Total contract value including all bonuses."""
        return sum(y.total_cash for y in self.years) + self.signing_bonus

    @property
    def total_guaranteed(self) -> int:
        """Total guaranteed money."""
        guaranteed = self.signing_bonus  # Signing bonus always guaranteed
        for year in self.years:
            guaranteed += year.guaranteed_salary
        return guaranteed

    @property
    def years_remaining(self) -> int:
        """Years left on contract including current year."""
        return self.total_years - self.current_year + 1

    @property
    def proration_years(self) -> int:
        """Years for bonus proration (includes void years)."""
        return min(5, self.total_years + self.void_years)

    @property
    def prorated_bonus(self) -> int:
        """Annual cap hit from signing bonus."""
        if self.proration_years == 0:
            return 0
        return self.signing_bonus // self.proration_years

    def cap_hit(self, year: int = None) -> int:
        """
        Calculate cap hit for a given contract year.

        Args:
            year: Contract year (1-indexed). Defaults to current year.
        """
        if year is None:
            year = self.current_year

        if year < 1 or year > len(self.years):
            return 0

        year_data = self.years[year - 1]
        return year_data.total_cash + self.prorated_bonus

    def dead_money_if_cut(self, year: int = None) -> int:
        """
        Calculate dead money if player is cut at given year.

        Dead money = remaining prorated bonus + any guaranteed salary.
        """
        if year is None:
            year = self.current_year

        # Remaining prorated bonus
        years_of_proration_remaining = self.proration_years - year + 1
        remaining_bonus = self.prorated_bonus * max(0, years_of_proration_remaining)

        # Add guaranteed salary for remaining years
        guaranteed_remaining = 0
        for y in self.years[year - 1:]:
            guaranteed_remaining += y.guaranteed_salary

        return remaining_bonus + guaranteed_remaining

    def dead_money_june1_cut(self, year: int = None) -> tuple[int, int]:
        """
        Calculate dead money for a June 1 cut (or post-June 1 designation).

        Returns (this_year, next_year) dead money split.
        """
        if year is None:
            year = self.current_year

        # This year: just current year's prorated bonus
        this_year = self.prorated_bonus

        # Next year: remaining prorated bonus
        years_remaining = self.proration_years - year
        next_year = self.prorated_bonus * max(0, years_remaining)

        # Guaranteed salary all accelerates this year
        for y in self.years[year - 1:]:
            this_year += y.guaranteed_salary

        return (this_year, next_year)

    def cap_savings_if_cut(self, year: int = None) -> int:
        """Calculate cap savings from cutting the player."""
        if year is None:
            year = self.current_year

        return self.cap_hit(year) - self.dead_money_if_cut(year)

    def current_year_data(self) -> Optional[ContractYear]:
        """Get current year's contract details."""
        if 1 <= self.current_year <= len(self.years):
            return self.years[self.current_year - 1]
        return None

    def advance_year(self) -> bool:
        """
        Advance to next contract year.

        Returns True if contract continues, False if expired.
        """
        self.current_year += 1

        if self.current_year > self.total_years:
            self.status = ContractStatus.EXPIRED
            return False

        return True

    def is_expiring(self) -> bool:
        """Is this the final year of the contract?"""
        return self.current_year >= self.total_years

    def restructure(self, amount_to_convert: int) -> int:
        """
        Restructure contract by converting salary to signing bonus.

        This creates immediate cap savings but adds future dead money risk.

        Args:
            amount_to_convert: Salary to convert to bonus

        Returns:
            Cap savings achieved
        """
        current = self.current_year_data()
        if not current:
            return 0

        # Can't convert more than base salary
        amount_to_convert = min(amount_to_convert, current.base_salary)

        if self.years_remaining < 2:
            return 0  # Need at least 2 years to restructure

        # Reduce base salary
        current.base_salary -= amount_to_convert

        # Add to signing bonus (prorated over remaining years)
        self.signing_bonus += amount_to_convert

        # Calculate new proration
        old_prorated = self.prorated_bonus
        # Proration is now over remaining years (max 5)
        new_proration_years = min(5, self.years_remaining)
        new_prorated = self.signing_bonus // new_proration_years

        self.is_restructured = True
        self.restructure_count += 1

        # Cap savings = amount converted - new proration hit
        return amount_to_convert - (new_prorated - old_prorated)

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "player_id": self.player_id,
            "team_id": self.team_id,
            "contract_type": self.contract_type.name,
            "status": self.status.name,
            "signed_date": self.signed_date.isoformat() if self.signed_date else None,
            "total_years": self.total_years,
            "current_year": self.current_year,
            "years": [y.to_dict() for y in self.years],
            "signing_bonus": self.signing_bonus,
            "void_years": self.void_years,
            "original_team_id": self.original_team_id,
            "is_restructured": self.is_restructured,
            "restructure_count": self.restructure_count,
            "extension_eligible": self.extension_eligible,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Contract":
        return cls(
            contract_id=data["contract_id"],
            player_id=data["player_id"],
            team_id=data["team_id"],
            contract_type=ContractType[data["contract_type"]],
            status=ContractStatus[data.get("status", "ACTIVE")],
            signed_date=date.fromisoformat(data["signed_date"]) if data.get("signed_date") else None,
            total_years=data["total_years"],
            current_year=data.get("current_year", 1),
            years=[ContractYear.from_dict(y) for y in data.get("years", [])],
            signing_bonus=data.get("signing_bonus", 0),
            void_years=data.get("void_years", 0),
            original_team_id=data.get("original_team_id", data["team_id"]),
            is_restructured=data.get("is_restructured", False),
            restructure_count=data.get("restructure_count", 0),
            extension_eligible=data.get("extension_eligible", False),
        )


def create_rookie_contract(
    player_id: str,
    team_id: str,
    pick_number: int,
    signed_date: date,
) -> Contract:
    """
    Create a rookie contract based on draft position.

    Uses the rookie wage scale to determine value.
    """
    import uuid

    values = get_rookie_contract_value(pick_number)

    total_years = values["years"]
    total_value = values["total"]
    signing_bonus = values["signing"]

    # Calculate per-year salary (escalating 5% per year)
    remaining_value = total_value - signing_bonus
    base_year1 = remaining_value // total_years

    years = []
    for i in range(total_years):
        escalation = 1.0 + (i * 0.05)
        salary = int(base_year1 * escalation)

        # First round picks: fully guaranteed first year, partial second
        if pick_number <= 32:
            if i == 0:
                guaranteed = salary
                guarantee_type = "full"
            elif i == 1:
                guaranteed = salary // 2
                guarantee_type = "injury"
            else:
                guaranteed = 0
                guarantee_type = "none"
        else:
            # Later picks: only signing bonus guaranteed
            guaranteed = 0
            guarantee_type = "none"

        years.append(ContractYear(
            year_number=i + 1,
            base_salary=salary,
            guaranteed_salary=guaranteed,
            guarantee_type=guarantee_type,
        ))

    # 5th year option for first rounders
    if values["fifth_year_option"]:
        # Option year added but not exercised yet
        years.append(ContractYear(
            year_number=5,
            base_salary=0,  # Set when option exercised
            is_option_year=True,
            option_type="team",
            option_exercised=False,
        ))

    contract = Contract(
        contract_id=str(uuid.uuid4()),
        player_id=player_id,
        team_id=team_id,
        contract_type=ContractType.ROOKIE,
        signed_date=signed_date,
        total_years=total_years,
        current_year=1,
        years=years[:total_years],  # Don't include option year in base years
        signing_bonus=signing_bonus,
        extension_eligible=False,  # Eligible after year 3
    )

    return contract


def create_veteran_contract(
    player_id: str,
    team_id: str,
    total_years: int,
    total_value: int,
    guaranteed: int,
    signing_bonus: int,
    signed_date: date,
) -> Contract:
    """
    Create a veteran free agent contract.

    Args:
        player_id: Player being signed
        team_id: Team signing player
        total_years: Contract length
        total_value: Total contract value (thousands)
        guaranteed: Total guaranteed money (thousands)
        signing_bonus: Signing bonus amount (thousands)
        signed_date: Date contract signed
    """
    import uuid

    # Remaining value after signing bonus
    remaining_value = total_value - signing_bonus

    # Typical NFL structure: escalating salaries
    # Year 1 is lower (often can be cut with minimal dead money by year 3+)
    base_year1 = remaining_value // total_years
    escalation_rate = 0.12  # 12% annual increase

    years = []
    remaining_guaranteed = guaranteed - signing_bonus  # Signing bonus already counted

    for i in range(total_years):
        # Escalating base salary
        escalation = 1.0 + (i * escalation_rate)
        salary = int(base_year1 * escalation)

        # Front-load guarantees
        if remaining_guaranteed > 0:
            year_guaranteed = min(salary, remaining_guaranteed)
            remaining_guaranteed -= year_guaranteed
            guarantee_type = "full" if i < 2 else "injury"
        else:
            year_guaranteed = 0
            guarantee_type = "none"

        years.append(ContractYear(
            year_number=i + 1,
            base_salary=salary,
            guaranteed_salary=year_guaranteed,
            guarantee_type=guarantee_type,
        ))

    return Contract(
        contract_id=str(uuid.uuid4()),
        player_id=player_id,
        team_id=team_id,
        contract_type=ContractType.VETERAN,
        signed_date=signed_date,
        total_years=total_years,
        current_year=1,
        years=years,
        signing_bonus=signing_bonus,
        extension_eligible=True,
    )


def create_minimum_contract(
    player_id: str,
    team_id: str,
    years: int,
    player_experience: int,
    signed_date: date,
) -> Contract:
    """
    Create a league minimum contract.

    Salary based on years of experience (NFL veteran minimum scale).
    """
    import uuid

    # Veteran minimum by experience (2024 values, thousands)
    MINIMUM_SALARY = {
        0: 795,   # Rookie
        1: 915,   # 1 year
        2: 990,   # 2 years
        3: 1065,  # 3 years
        4: 1140,  # 4+ years
        5: 1140,
        6: 1140,
        7: 1215,  # 7+ years
    }

    base_salary = MINIMUM_SALARY.get(min(player_experience, 7), 1215)

    contract_years = []
    for i in range(years):
        # Experience increases each year
        exp_in_year = player_experience + i
        salary = MINIMUM_SALARY.get(min(exp_in_year, 7), 1215)

        contract_years.append(ContractYear(
            year_number=i + 1,
            base_salary=salary,
            guaranteed_salary=salary if i == 0 else 0,
            guarantee_type="full" if i == 0 else "none",
        ))

    return Contract(
        contract_id=str(uuid.uuid4()),
        player_id=player_id,
        team_id=team_id,
        contract_type=ContractType.MINIMUM,
        signed_date=signed_date,
        total_years=years,
        current_year=1,
        years=contract_years,
        signing_bonus=0,
        extension_eligible=True,
    )


def create_franchise_tag(
    player_id: str,
    team_id: str,
    position: str,
    tag_value: int,
    signed_date: date,
    is_exclusive: bool = False,
) -> Contract:
    """
    Create a franchise tag contract.

    Args:
        player_id: Tagged player
        team_id: Team applying tag
        position: Player position (affects tag value)
        tag_value: Calculated tag value (thousands)
        signed_date: Date tag applied
        is_exclusive: Exclusive (can't negotiate) vs non-exclusive
    """
    import uuid

    return Contract(
        contract_id=str(uuid.uuid4()),
        player_id=player_id,
        team_id=team_id,
        contract_type=ContractType.FRANCHISE_TAG,
        signed_date=signed_date,
        total_years=1,
        current_year=1,
        years=[ContractYear(
            year_number=1,
            base_salary=tag_value,
            guaranteed_salary=tag_value,
            guarantee_type="full",
        )],
        signing_bonus=0,
        extension_eligible=True,  # Can negotiate long-term deal
    )
