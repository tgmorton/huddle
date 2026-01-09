"""
Transaction Logging System.

Records all roster moves, trades, signings, and player movements.
Provides audit trail and history for all team/player changes.

Uses day-based calendar system (no minutes/hours).
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from huddle.core.contracts.contract import Contract
    from huddle.core.draft.picks import DraftPick


class TransactionType(Enum):
    """Type of roster/asset transaction."""

    # Draft
    DRAFT_SELECTION = auto()      # Player selected in draft
    DRAFT_TRADE = auto()          # Trade during draft

    # Free Agency
    FA_SIGNING = auto()           # Free agent signed
    EXTENSION = auto()            # Contract extension
    RESTRUCTURE = auto()          # Contract restructure

    # Roster Moves
    CUT = auto()                  # Player released
    CUT_JUNE1 = auto()            # June 1 cut (splits dead money)
    WAIVER_CLAIM = auto()         # Player claimed off waivers
    WAIVER_PASS = auto()          # Player cleared waivers

    # Practice Squad
    PS_SIGN = auto()              # Signed to practice squad
    PS_ELEVATE = auto()           # Elevated from practice squad
    PS_RELEASE = auto()           # Released from practice squad
    PS_PROTECT = auto()           # Protected on practice squad

    # Injured Reserve
    IR_PLACE = auto()             # Placed on IR
    IR_RETURN = auto()            # Activated from IR
    IR_DESIGNATE_RETURN = auto()  # Designated to return from IR

    # PUP/NFI
    PUP_PLACE = auto()            # Placed on PUP list
    PUP_ACTIVATE = auto()         # Activated from PUP
    NFI_PLACE = auto()            # Placed on NFI list
    NFI_ACTIVATE = auto()         # Activated from NFI

    # Trades
    TRADE = auto()                # Player traded

    # Tags
    FRANCHISE_TAG = auto()        # Franchise tag applied
    TRANSITION_TAG = auto()       # Transition tag applied
    TAG_REMOVE = auto()           # Tag removed/signed

    # Other
    RETIREMENT = auto()           # Player retired
    UNRETIREMENT = auto()         # Player came out of retirement
    SUSPENSION = auto()           # Player suspended
    REINSTATEMENT = auto()        # Player reinstated from suspension
    RESERVE_LIST = auto()         # Placed on reserve list

    # Administrative
    ROSTER_EXEMPTION = auto()     # Granted roster exemption
    TENDER = auto()               # RFA/ERFA tender


# Transaction types that affect cap
CAP_AFFECTING_TRANSACTIONS = {
    TransactionType.FA_SIGNING,
    TransactionType.EXTENSION,
    TransactionType.RESTRUCTURE,
    TransactionType.CUT,
    TransactionType.CUT_JUNE1,
    TransactionType.TRADE,
    TransactionType.FRANCHISE_TAG,
    TransactionType.TRANSITION_TAG,
}


@dataclass
class TransactionParty:
    """A party involved in a transaction (team or player)."""
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_position: Optional[str] = None


@dataclass
class TradeAsset:
    """An asset in a trade (player, pick, or cash)."""
    asset_type: str  # "player", "pick", "cash"

    # For players
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_position: Optional[str] = None
    player_overall: Optional[int] = None
    contract_years_remaining: Optional[int] = None
    contract_value: Optional[int] = None

    # For picks
    pick_id: Optional[str] = None
    pick_year: Optional[int] = None
    pick_round: Optional[int] = None
    pick_original_team: Optional[str] = None
    pick_conditions: Optional[str] = None

    # For cash
    cash_amount: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "asset_type": self.asset_type,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_position": self.player_position,
            "player_overall": self.player_overall,
            "contract_years_remaining": self.contract_years_remaining,
            "contract_value": self.contract_value,
            "pick_id": self.pick_id,
            "pick_year": self.pick_year,
            "pick_round": self.pick_round,
            "pick_original_team": self.pick_original_team,
            "pick_conditions": self.pick_conditions,
            "cash_amount": self.cash_amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeAsset":
        return cls(**data)

    def __repr__(self) -> str:
        if self.asset_type == "player":
            return f"{self.player_name} ({self.player_position})"
        elif self.asset_type == "pick":
            cond = f" ({self.pick_conditions})" if self.pick_conditions else ""
            orig = f" via {self.pick_original_team}" if self.pick_original_team else ""
            return f"{self.pick_year} Round {self.pick_round}{orig}{cond}"
        elif self.asset_type == "cash":
            return f"${self.cash_amount:,}K"
        return "Unknown asset"


@dataclass
class Transaction:
    """
    A single transaction in the league.

    Records all details for historical reference and cap calculations.
    """
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transaction_type: TransactionType = TransactionType.FA_SIGNING

    # When
    transaction_date: date = field(default_factory=date.today)
    season: int = 0
    week: int = 0  # 0 = offseason, 1-18 = regular season, 19+ = playoffs

    # Who (primary)
    team_id: str = ""
    team_name: str = ""
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_position: Optional[str] = None

    # Secondary party (for trades)
    other_team_id: Optional[str] = None
    other_team_name: Optional[str] = None

    # Trade details
    assets_sent: list[TradeAsset] = field(default_factory=list)
    assets_received: list[TradeAsset] = field(default_factory=list)

    # Contract details
    contract_years: Optional[int] = None
    contract_total_value: Optional[int] = None
    contract_guaranteed: Optional[int] = None
    contract_id: Optional[str] = None

    # Cap implications
    cap_hit: int = 0
    dead_money: int = 0
    dead_money_next_year: int = 0  # For June 1 cuts
    cap_savings: int = 0

    # Draft details
    draft_pick_number: Optional[int] = None
    draft_round: Optional[int] = None

    # Injury details (for IR moves)
    injury_type: Optional[str] = None
    expected_return_weeks: Optional[int] = None

    # Additional context
    notes: str = ""
    is_conditional: bool = False
    conditions: str = ""

    def get_headline(self) -> str:
        """Generate news headline for this transaction."""
        t = self.transaction_type

        if t == TransactionType.DRAFT_SELECTION:
            return f"{self.team_name} select {self.player_name} ({self.player_position}) with pick #{self.draft_pick_number}"

        elif t == TransactionType.FA_SIGNING:
            value_str = f"${self.contract_total_value:,}K" if self.contract_total_value else "terms undisclosed"
            return f"{self.team_name} sign {self.player_name} to {self.contract_years}-year deal ({value_str})"

        elif t == TransactionType.EXTENSION:
            return f"{self.team_name} extend {self.player_name} for {self.contract_years} years"

        elif t == TransactionType.CUT or t == TransactionType.CUT_JUNE1:
            return f"{self.team_name} release {self.player_name}"

        elif t == TransactionType.TRADE:
            sent = ", ".join(str(a) for a in self.assets_sent)
            recv = ", ".join(str(a) for a in self.assets_received)
            return f"{self.team_name} trade {sent} to {self.other_team_name} for {recv}"

        elif t == TransactionType.IR_PLACE:
            return f"{self.team_name} place {self.player_name} on injured reserve ({self.injury_type})"

        elif t == TransactionType.IR_RETURN:
            return f"{self.team_name} activate {self.player_name} from injured reserve"

        elif t == TransactionType.FRANCHISE_TAG:
            return f"{self.team_name} apply franchise tag to {self.player_name}"

        elif t == TransactionType.RETIREMENT:
            return f"{self.player_name} announces retirement"

        elif t == TransactionType.WAIVER_CLAIM:
            return f"{self.team_name} claim {self.player_name} off waivers"

        elif t == TransactionType.PS_SIGN:
            return f"{self.team_name} sign {self.player_name} to practice squad"

        else:
            return f"{self.team_name}: {self.player_name} - {t.name}"

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type.name,
            "transaction_date": self.transaction_date.isoformat(),
            "season": self.season,
            "week": self.week,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_position": self.player_position,
            "other_team_id": self.other_team_id,
            "other_team_name": self.other_team_name,
            "assets_sent": [a.to_dict() for a in self.assets_sent],
            "assets_received": [a.to_dict() for a in self.assets_received],
            "contract_years": self.contract_years,
            "contract_total_value": self.contract_total_value,
            "contract_guaranteed": self.contract_guaranteed,
            "contract_id": self.contract_id,
            "cap_hit": self.cap_hit,
            "dead_money": self.dead_money,
            "dead_money_next_year": self.dead_money_next_year,
            "cap_savings": self.cap_savings,
            "draft_pick_number": self.draft_pick_number,
            "draft_round": self.draft_round,
            "injury_type": self.injury_type,
            "expected_return_weeks": self.expected_return_weeks,
            "notes": self.notes,
            "is_conditional": self.is_conditional,
            "conditions": self.conditions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            transaction_id=data.get("transaction_id", str(uuid.uuid4())),
            transaction_type=TransactionType[data["transaction_type"]],
            transaction_date=date.fromisoformat(data["transaction_date"]),
            season=data.get("season", 0),
            week=data.get("week", 0),
            team_id=data.get("team_id", ""),
            team_name=data.get("team_name", ""),
            player_id=data.get("player_id"),
            player_name=data.get("player_name"),
            player_position=data.get("player_position"),
            other_team_id=data.get("other_team_id"),
            other_team_name=data.get("other_team_name"),
            assets_sent=[TradeAsset.from_dict(a) for a in data.get("assets_sent", [])],
            assets_received=[TradeAsset.from_dict(a) for a in data.get("assets_received", [])],
            contract_years=data.get("contract_years"),
            contract_total_value=data.get("contract_total_value"),
            contract_guaranteed=data.get("contract_guaranteed"),
            contract_id=data.get("contract_id"),
            cap_hit=data.get("cap_hit", 0),
            dead_money=data.get("dead_money", 0),
            dead_money_next_year=data.get("dead_money_next_year", 0),
            cap_savings=data.get("cap_savings", 0),
            draft_pick_number=data.get("draft_pick_number"),
            draft_round=data.get("draft_round"),
            injury_type=data.get("injury_type"),
            expected_return_weeks=data.get("expected_return_weeks"),
            notes=data.get("notes", ""),
            is_conditional=data.get("is_conditional", False),
            conditions=data.get("conditions", ""),
        )


@dataclass
class TransactionLog:
    """
    Complete transaction history for a league.

    Provides querying and filtering capabilities for all transactions.
    """
    league_id: str
    transactions: list[Transaction] = field(default_factory=list)

    def add(self, transaction: Transaction) -> None:
        """Add a transaction to the log."""
        self.transactions.append(transaction)
        # Keep sorted by date
        self.transactions.sort(key=lambda t: (t.transaction_date, t.transaction_id))

    def get_by_team(self, team_id: str, season: int = None) -> list[Transaction]:
        """Get all transactions for a team."""
        results = [t for t in self.transactions
                   if t.team_id == team_id or t.other_team_id == team_id]
        if season is not None:
            results = [t for t in results if t.season == season]
        return results

    def get_by_player(self, player_id: str) -> list[Transaction]:
        """Get all transactions for a player."""
        return [t for t in self.transactions if t.player_id == player_id]

    def get_by_type(self, transaction_type: TransactionType, season: int = None) -> list[Transaction]:
        """Get all transactions of a specific type."""
        results = [t for t in self.transactions if t.transaction_type == transaction_type]
        if season is not None:
            results = [t for t in results if t.season == season]
        return results

    def get_by_date_range(self, start: date, end: date) -> list[Transaction]:
        """Get transactions within a date range."""
        return [t for t in self.transactions
                if start <= t.transaction_date <= end]

    def get_by_season(self, season: int) -> list[Transaction]:
        """Get all transactions for a season."""
        return [t for t in self.transactions if t.season == season]

    def get_recent(self, count: int = 10) -> list[Transaction]:
        """Get most recent transactions."""
        return self.transactions[-count:]

    def get_trades(self, season: int = None) -> list[Transaction]:
        """Get all trades."""
        return self.get_by_type(TransactionType.TRADE, season)

    def get_signings(self, season: int = None) -> list[Transaction]:
        """Get all free agent signings."""
        return self.get_by_type(TransactionType.FA_SIGNING, season)

    def get_cuts(self, season: int = None) -> list[Transaction]:
        """Get all player releases."""
        cuts = self.get_by_type(TransactionType.CUT, season)
        cuts.extend(self.get_by_type(TransactionType.CUT_JUNE1, season))
        return sorted(cuts, key=lambda t: t.transaction_date)

    def get_draft_selections(self, year: int) -> list[Transaction]:
        """Get all draft selections for a year."""
        return [t for t in self.transactions
                if t.transaction_type == TransactionType.DRAFT_SELECTION and t.season == year]

    def calculate_team_dead_money(self, team_id: str, season: int) -> int:
        """Calculate total dead money for a team from all transactions."""
        total = 0
        for t in self.get_by_team(team_id, season):
            if t.team_id == team_id:
                total += t.dead_money
        return total

    def to_dict(self) -> dict:
        return {
            "league_id": self.league_id,
            "transactions": [t.to_dict() for t in self.transactions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TransactionLog":
        return cls(
            league_id=data["league_id"],
            transactions=[Transaction.from_dict(t) for t in data.get("transactions", [])],
        )


# =============================================================================
# Transaction Factory Functions
# =============================================================================


def create_draft_transaction(
    team_id: str,
    team_name: str,
    player_id: str,
    player_name: str,
    player_position: str,
    pick_number: int,
    pick_round: int,
    season: int,
    transaction_date: date,
    contract_id: str = None,
    contract_value: int = None,
) -> Transaction:
    """Create a draft selection transaction."""
    return Transaction(
        transaction_type=TransactionType.DRAFT_SELECTION,
        transaction_date=transaction_date,
        season=season,
        week=0,  # Offseason
        team_id=team_id,
        team_name=team_name,
        player_id=player_id,
        player_name=player_name,
        player_position=player_position,
        contract_id=contract_id,
        contract_total_value=contract_value,
        draft_pick_number=pick_number,
        draft_round=pick_round,
    )


def create_signing_transaction(
    team_id: str,
    team_name: str,
    player_id: str,
    player_name: str,
    player_position: str,
    contract_years: int,
    contract_value: int,
    contract_guaranteed: int,
    season: int,
    transaction_date: date,
    contract_id: str = None,
    cap_hit: int = 0,
) -> Transaction:
    """Create a free agent signing transaction."""
    return Transaction(
        transaction_type=TransactionType.FA_SIGNING,
        transaction_date=transaction_date,
        season=season,
        week=0,
        team_id=team_id,
        team_name=team_name,
        player_id=player_id,
        player_name=player_name,
        player_position=player_position,
        contract_years=contract_years,
        contract_total_value=contract_value,
        contract_guaranteed=contract_guaranteed,
        contract_id=contract_id,
        cap_hit=cap_hit,
    )


def create_cut_transaction(
    team_id: str,
    team_name: str,
    player_id: str,
    player_name: str,
    player_position: str,
    season: int,
    transaction_date: date,
    dead_money: int = 0,
    cap_savings: int = 0,
    is_june1: bool = False,
    dead_money_next_year: int = 0,
) -> Transaction:
    """Create a player release transaction."""
    return Transaction(
        transaction_type=TransactionType.CUT_JUNE1 if is_june1 else TransactionType.CUT,
        transaction_date=transaction_date,
        season=season,
        week=0,
        team_id=team_id,
        team_name=team_name,
        player_id=player_id,
        player_name=player_name,
        player_position=player_position,
        dead_money=dead_money,
        dead_money_next_year=dead_money_next_year,
        cap_savings=cap_savings,
    )


def create_trade_transaction(
    team_id: str,
    team_name: str,
    other_team_id: str,
    other_team_name: str,
    assets_sent: list[TradeAsset],
    assets_received: list[TradeAsset],
    season: int,
    transaction_date: date,
    dead_money: int = 0,
    notes: str = "",
) -> Transaction:
    """Create a trade transaction."""
    # Get player info if player is being traded
    player_id = None
    player_name = None
    player_position = None

    for asset in assets_sent:
        if asset.asset_type == "player":
            player_id = asset.player_id
            player_name = asset.player_name
            player_position = asset.player_position
            break

    return Transaction(
        transaction_type=TransactionType.TRADE,
        transaction_date=transaction_date,
        season=season,
        week=0,
        team_id=team_id,
        team_name=team_name,
        player_id=player_id,
        player_name=player_name,
        player_position=player_position,
        other_team_id=other_team_id,
        other_team_name=other_team_name,
        assets_sent=assets_sent,
        assets_received=assets_received,
        dead_money=dead_money,
        notes=notes,
    )


def create_ir_transaction(
    team_id: str,
    team_name: str,
    player_id: str,
    player_name: str,
    player_position: str,
    season: int,
    week: int,
    transaction_date: date,
    injury_type: str,
    expected_weeks: int = None,
    is_return: bool = False,
) -> Transaction:
    """Create an IR placement or return transaction."""
    return Transaction(
        transaction_type=TransactionType.IR_RETURN if is_return else TransactionType.IR_PLACE,
        transaction_date=transaction_date,
        season=season,
        week=week,
        team_id=team_id,
        team_name=team_name,
        player_id=player_id,
        player_name=player_name,
        player_position=player_position,
        injury_type=injury_type,
        expected_return_weeks=expected_weeks,
    )
