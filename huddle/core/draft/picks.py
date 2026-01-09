"""
Draft Pick Tracking System.

Tracks:
- Pick ownership (original team, current team)
- Conditional picks with protections
- Pick value for trade evaluation
- Draft pick inventory per team
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import Optional
import uuid


class PickProtection(Enum):
    """Type of protection on a conditional pick."""
    NONE = auto()              # Unprotected
    TOP_1 = auto()             # Top 1 protected
    TOP_3 = auto()             # Top 3 protected
    TOP_5 = auto()             # Top 5 protected
    TOP_10 = auto()            # Top 10 protected
    TOP_15 = auto()            # Top 15 protected
    TOP_20 = auto()            # Top 20 protected
    LOTTERY = auto()           # Top 14 protected (lottery picks)


# Protection thresholds (pick number at or below = protected)
PROTECTION_THRESHOLDS = {
    PickProtection.NONE: 0,
    PickProtection.TOP_1: 1,
    PickProtection.TOP_3: 3,
    PickProtection.TOP_5: 5,
    PickProtection.TOP_10: 10,
    PickProtection.TOP_15: 15,
    PickProtection.TOP_20: 20,
    PickProtection.LOTTERY: 14,
}


# Jimmy Johnson trade value chart (classic)
# Pick number -> trade value points
JIMMY_JOHNSON_VALUES = {
    1: 3000, 2: 2600, 3: 2200, 4: 1800, 5: 1700,
    6: 1600, 7: 1500, 8: 1400, 9: 1350, 10: 1300,
    11: 1250, 12: 1200, 13: 1150, 14: 1100, 15: 1050,
    16: 1000, 17: 950, 18: 900, 19: 875, 20: 850,
    21: 800, 22: 780, 23: 760, 24: 740, 25: 720,
    26: 700, 27: 680, 28: 660, 29: 640, 30: 620,
    31: 600, 32: 590,
    # Round 2
    33: 580, 34: 560, 35: 550, 36: 540, 37: 530,
    38: 520, 39: 510, 40: 500, 41: 490, 42: 480,
    43: 470, 44: 460, 45: 450, 46: 440, 47: 430,
    48: 420, 49: 410, 50: 400, 51: 390, 52: 380,
    53: 370, 54: 360, 55: 350, 56: 340, 57: 330,
    58: 320, 59: 310, 60: 300, 61: 292, 62: 284,
    63: 276, 64: 270,
    # Round 3
    65: 265, 66: 260, 67: 255, 68: 250, 69: 245,
    70: 240, 71: 235, 72: 230, 73: 225, 74: 220,
    75: 215, 76: 210, 77: 205, 78: 200, 79: 195,
    80: 190, 81: 185, 82: 180, 83: 175, 84: 170,
    85: 165, 86: 160, 87: 155, 88: 150, 89: 145,
    90: 140, 91: 136, 92: 132, 93: 128, 94: 124,
    95: 120, 96: 116,
    # Round 4
    97: 112, 98: 108, 99: 104, 100: 100,
    # Rounds 5-7 continue decreasing
}


def get_pick_value(pick_number: int) -> int:
    """
    Get trade value for a pick using Jimmy Johnson chart.

    Extrapolates for picks beyond the chart.
    """
    if pick_number in JIMMY_JOHNSON_VALUES:
        return JIMMY_JOHNSON_VALUES[pick_number]

    if pick_number < 1:
        return 0

    if pick_number <= 100:
        # Interpolate
        known = sorted(JIMMY_JOHNSON_VALUES.keys())
        lower = max(k for k in known if k <= pick_number)
        upper = min(k for k in known if k >= pick_number)
        if lower == upper:
            return JIMMY_JOHNSON_VALUES[lower]
        ratio = (pick_number - lower) / (upper - lower)
        return int(JIMMY_JOHNSON_VALUES[lower] +
                   (JIMMY_JOHNSON_VALUES[upper] - JIMMY_JOHNSON_VALUES[lower]) * ratio)

    # Beyond round 4, diminishing returns
    if pick_number <= 140:  # Round 5
        return max(20, 100 - (pick_number - 100) * 2)
    elif pick_number <= 180:  # Round 6
        return max(10, 40 - (pick_number - 140))
    else:  # Round 7
        return max(1, 10 - (pick_number - 180) // 5)


def get_round_from_pick(pick_number: int, teams: int = 32) -> int:
    """Get round number from overall pick number."""
    return ((pick_number - 1) // teams) + 1


@dataclass
class DraftPick:
    """
    A draft pick that can be owned and traded.

    Tracks original ownership, current ownership, conditions,
    and eventual selection.
    """
    pick_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Identification
    year: int = 0                  # Draft year
    round: int = 1                 # Round (1-7)

    # Ownership
    original_team_id: str = ""     # Team that originally held pick
    current_team_id: str = ""      # Current owner

    # Conditions (for traded picks)
    protection: PickProtection = PickProtection.NONE
    protection_converts_to: Optional[str] = None  # "2026 2nd" if protected
    condition_description: str = ""  # Human readable

    # After draft
    pick_number: Optional[int] = None     # Actual overall pick (1-224)
    player_selected_id: Optional[str] = None
    selection_date: Optional[date] = None

    # Trade tracking
    times_traded: int = 0
    trade_history: list[str] = field(default_factory=list)  # List of transaction IDs

    # Compensation picks
    is_compensatory: bool = False

    @property
    def is_owned_by_original(self) -> bool:
        """Does original team still own this pick?"""
        return self.original_team_id == self.current_team_id

    @property
    def is_conditional(self) -> bool:
        """Does this pick have conditions?"""
        return self.protection != PickProtection.NONE

    @property
    def estimated_value(self) -> int:
        """
        Estimate pick value for trades.

        Uses middle of round if pick number not yet known.
        """
        if self.pick_number:
            return get_pick_value(self.pick_number)

        # Estimate based on round
        estimated_pick = {
            1: 16,   # Middle of round 1
            2: 48,   # Middle of round 2
            3: 80,   # Middle of round 3
            4: 112,  # etc.
            5: 144,
            6: 176,
            7: 208,
        }.get(self.round, 200)

        return get_pick_value(estimated_pick)

    def check_protection(self, actual_pick: int) -> bool:
        """
        Check if protection is triggered.

        Returns True if pick conveys (protection NOT triggered).
        Returns False if pick is protected (doesn't convey).
        """
        threshold = PROTECTION_THRESHOLDS.get(self.protection, 0)
        return actual_pick > threshold  # Conveys if pick is WORSE than protection

    def to_dict(self) -> dict:
        return {
            "pick_id": self.pick_id,
            "year": self.year,
            "round": self.round,
            "original_team_id": self.original_team_id,
            "current_team_id": self.current_team_id,
            "protection": self.protection.name,
            "protection_converts_to": self.protection_converts_to,
            "condition_description": self.condition_description,
            "pick_number": self.pick_number,
            "player_selected_id": self.player_selected_id,
            "selection_date": self.selection_date.isoformat() if self.selection_date else None,
            "times_traded": self.times_traded,
            "trade_history": self.trade_history,
            "is_compensatory": self.is_compensatory,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftPick":
        return cls(
            pick_id=data.get("pick_id", str(uuid.uuid4())),
            year=data["year"],
            round=data["round"],
            original_team_id=data["original_team_id"],
            current_team_id=data["current_team_id"],
            protection=PickProtection[data.get("protection", "NONE")],
            protection_converts_to=data.get("protection_converts_to"),
            condition_description=data.get("condition_description", ""),
            pick_number=data.get("pick_number"),
            player_selected_id=data.get("player_selected_id"),
            selection_date=date.fromisoformat(data["selection_date"]) if data.get("selection_date") else None,
            times_traded=data.get("times_traded", 0),
            trade_history=data.get("trade_history", []),
            is_compensatory=data.get("is_compensatory", False),
        )

    def __repr__(self) -> str:
        owner = "OWN" if self.is_owned_by_original else self.original_team_id[:3].upper()
        cond = f" ({self.protection.name})" if self.is_conditional else ""
        return f"{self.year} R{self.round} ({owner}){cond}"


@dataclass
class DraftPickInventory:
    """
    Track all draft pick assets for a team.

    Provides methods to query picks by year, check tradeable assets,
    and manage pick ownership.
    """
    team_id: str
    picks: list[DraftPick] = field(default_factory=list)

    def get_picks_for_year(self, year: int) -> list[DraftPick]:
        """Get all picks team owns for a given year."""
        return [p for p in self.picks if p.year == year and p.current_team_id == self.team_id]

    def get_picks_by_round(self, year: int, round_num: int) -> list[DraftPick]:
        """Get picks for a specific round."""
        return [p for p in self.picks
                if p.year == year and p.round == round_num and p.current_team_id == self.team_id]

    def get_own_picks(self, year: int) -> list[DraftPick]:
        """Get picks that were originally this team's."""
        return [p for p in self.picks
                if p.year == year and p.original_team_id == self.team_id and p.current_team_id == self.team_id]

    def get_acquired_picks(self, year: int) -> list[DraftPick]:
        """Get picks acquired from other teams."""
        return [p for p in self.picks
                if p.year == year and p.original_team_id != self.team_id and p.current_team_id == self.team_id]

    def get_traded_away_picks(self, year: int) -> list[DraftPick]:
        """Get this team's original picks that were traded away."""
        return [p for p in self.picks
                if p.year == year and p.original_team_id == self.team_id and p.current_team_id != self.team_id]

    def total_value_for_year(self, year: int) -> int:
        """Sum of estimated pick values for a year."""
        return sum(p.estimated_value for p in self.get_picks_for_year(year))

    def has_first_round_pick(self, year: int) -> bool:
        """Does team have any first round pick for this year?"""
        return any(p.round == 1 for p in self.get_picks_for_year(year))

    def count_picks(self, year: int) -> int:
        """Total picks owned for a year."""
        return len(self.get_picks_for_year(year))

    def can_trade_pick(self, pick: DraftPick) -> bool:
        """
        Check if a pick can be traded.

        NFL rule: Can't trade picks more than 3 years out.
        Also can't trade if you don't own it.
        """
        if pick.current_team_id != self.team_id:
            return False
        # Compensatory picks can't be traded (in most cases)
        if pick.is_compensatory:
            return False
        return True

    def add_pick(self, pick: DraftPick) -> None:
        """Add a pick to inventory."""
        # Check for duplicates
        if any(p.pick_id == pick.pick_id for p in self.picks):
            return
        self.picks.append(pick)

    def remove_pick(self, pick_id: str) -> Optional[DraftPick]:
        """Remove and return a pick from inventory."""
        for i, p in enumerate(self.picks):
            if p.pick_id == pick_id:
                return self.picks.pop(i)
        return None

    def transfer_pick(self, pick_id: str, to_team_id: str, transaction_id: str) -> bool:
        """Transfer ownership of a pick to another team."""
        for pick in self.picks:
            if pick.pick_id == pick_id:
                pick.current_team_id = to_team_id
                pick.times_traded += 1
                pick.trade_history.append(transaction_id)
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "picks": [p.to_dict() for p in self.picks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftPickInventory":
        return cls(
            team_id=data["team_id"],
            picks=[DraftPick.from_dict(p) for p in data.get("picks", [])],
        )


def create_initial_picks_for_team(
    team_id: str,
    start_year: int,
    years_ahead: int = 3,
    rounds: int = 7,
) -> DraftPickInventory:
    """
    Create initial draft pick inventory for a team.

    Generates picks for current year plus future years.
    """
    inventory = DraftPickInventory(team_id=team_id)

    for year in range(start_year, start_year + years_ahead + 1):
        for round_num in range(1, rounds + 1):
            pick = DraftPick(
                year=year,
                round=round_num,
                original_team_id=team_id,
                current_team_id=team_id,
            )
            inventory.add_pick(pick)

    return inventory


def create_league_draft_picks(
    team_ids: list[str],
    start_year: int,
    years_ahead: int = 3,
) -> dict[str, DraftPickInventory]:
    """
    Create draft pick inventories for all teams in a league.

    Returns dict mapping team_id -> DraftPickInventory.
    """
    inventories = {}
    for team_id in team_ids:
        inventories[team_id] = create_initial_picks_for_team(
            team_id, start_year, years_ahead
        )
    return inventories


@dataclass
class DraftOrder:
    """
    Draft order for a single round.

    Tracks the order of picks for draft execution.
    """
    year: int
    round: int
    order: list[DraftPick] = field(default_factory=list)

    def set_pick_numbers(self, start_pick: int = None) -> None:
        """Assign actual pick numbers based on order."""
        if start_pick is None:
            start_pick = (self.round - 1) * len(self.order) + 1

        for i, pick in enumerate(self.order):
            pick.pick_number = start_pick + i


@dataclass
class DraftState:
    """
    State of an ongoing or completed draft.

    Tracks all rounds, current position, and selections.
    """
    year: int
    rounds: list[DraftOrder] = field(default_factory=list)
    current_round: int = 1
    current_pick_in_round: int = 0
    is_complete: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @property
    def current_pick(self) -> Optional[DraftPick]:
        """Get the current pick on the clock."""
        if self.is_complete:
            return None
        if self.current_round > len(self.rounds):
            return None
        round_order = self.rounds[self.current_round - 1]
        if self.current_pick_in_round >= len(round_order.order):
            return None
        return round_order.order[self.current_pick_in_round]

    def advance(self) -> bool:
        """
        Advance to next pick.

        Returns True if draft continues, False if complete.
        """
        self.current_pick_in_round += 1

        # Check if round complete
        if self.current_pick_in_round >= len(self.rounds[self.current_round - 1].order):
            self.current_round += 1
            self.current_pick_in_round = 0

            # Check if draft complete
            if self.current_round > len(self.rounds):
                self.is_complete = True
                return False

        return True

    def make_selection(self, player_id: str, selection_date: date) -> Optional[DraftPick]:
        """
        Make a selection with the current pick.

        Returns the pick that was used, or None if draft is complete.
        """
        pick = self.current_pick
        if not pick:
            return None

        pick.player_selected_id = player_id
        pick.selection_date = selection_date

        self.advance()
        return pick

    def get_all_selections(self) -> list[DraftPick]:
        """Get all picks that have been used to select players."""
        selections = []
        for round_order in self.rounds:
            for pick in round_order.order:
                if pick.player_selected_id:
                    selections.append(pick)
        return selections

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "rounds": [
                {
                    "year": r.year,
                    "round": r.round,
                    "order": [p.to_dict() for p in r.order],
                }
                for r in self.rounds
            ],
            "current_round": self.current_round,
            "current_pick_in_round": self.current_pick_in_round,
            "is_complete": self.is_complete,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftState":
        rounds = []
        for r_data in data.get("rounds", []):
            rounds.append(DraftOrder(
                year=r_data["year"],
                round=r_data["round"],
                order=[DraftPick.from_dict(p) for p in r_data["order"]],
            ))

        return cls(
            year=data["year"],
            rounds=rounds,
            current_round=data.get("current_round", 1),
            current_pick_in_round=data.get("current_pick_in_round", 0),
            is_complete=data.get("is_complete", False),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
        )


def create_draft_order(
    year: int,
    team_standings: list[str],  # Team IDs in order of finish (worst to best)
    pick_inventories: dict[str, DraftPickInventory],
    num_rounds: int = 7,
) -> DraftState:
    """
    Create draft order from team standings and pick ownership.

    Args:
        year: Draft year
        team_standings: Teams in draft order (worst record first)
        pick_inventories: Pick ownership by team
        num_rounds: Number of rounds

    Returns:
        DraftState ready for draft execution
    """
    rounds = []

    for round_num in range(1, num_rounds + 1):
        round_picks = []

        for team_id in team_standings:
            # Find who owns this team's pick for this round
            for inv in pick_inventories.values():
                for pick in inv.picks:
                    if (pick.original_team_id == team_id and
                        pick.year == year and
                        pick.round == round_num):
                        round_picks.append(pick)
                        break

        order = DraftOrder(year=year, round=round_num, order=round_picks)
        order.set_pick_numbers()
        rounds.append(order)

    return DraftState(year=year, rounds=rounds)
