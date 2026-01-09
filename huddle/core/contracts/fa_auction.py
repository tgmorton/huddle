"""
Free Agency Auction System.

Implements HC09-style ascending auctions where:
- Price starts at floor and rises each round
- Teams drop out when price exceeds their valuation
- Last team standing wins (or player rejects if below asking)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class AuctionStatus(Enum):
    """Status of an auction."""
    PENDING = "pending"      # Not yet started
    BIDDING = "bidding"      # Active bidding rounds
    RESOLVED = "resolved"    # Winner determined and accepted
    FAILED = "failed"        # No winner (all dropped or player rejected)
    CANCELLED = "cancelled"  # Auction cancelled


class BidAction(Enum):
    """Actions a team can take in a bidding round."""
    STAY = "stay"    # Stay in at current price
    DROP = "drop"    # Drop out of auction
    RAISE = "raise"  # Raise the bid (optional aggressive move)


@dataclass
class TeamBid:
    """A team's participation in an auction."""
    team_id: UUID
    team_name: str

    # Bidding state
    is_active: bool = True  # Still in the auction
    last_action: Optional[BidAction] = None
    max_offer: int = 0  # Maximum they're willing to pay

    # Team context for AI decisions
    cap_room: int = 0
    position_need: float = 0.0  # 0-1 scale
    team_status: str = "AVERAGE"  # CONTENDING, REBUILDING, etc.

    def drop_out(self) -> None:
        """Team drops out of auction."""
        self.is_active = False
        self.last_action = BidAction.DROP

    def stay_in(self) -> None:
        """Team stays in at current price."""
        self.last_action = BidAction.STAY


@dataclass
class AuctionRound:
    """Record of a single auction round."""
    round_number: int
    price: int

    # Who was in and what they did
    active_teams: list[UUID] = field(default_factory=list)
    actions: dict[str, BidAction] = field(default_factory=dict)  # team_id -> action

    # Who dropped this round
    dropped_teams: list[UUID] = field(default_factory=list)


@dataclass
class Auction:
    """
    An ascending auction for a free agent.

    Flow:
    1. Auction created with interested teams
    2. Round 1: Price = floor_price, all teams decide STAY/DROP
    3. Round N: Price += increment, remaining teams decide
    4. Resolution: 1 team left = winner, 0 = failed
    5. Player acceptance check for stubborn players
    """

    auction_id: UUID = field(default_factory=uuid4)
    player_id: UUID = field(default_factory=uuid4)

    # Player info (for display)
    player_name: str = ""
    player_position: str = ""
    player_overall: int = 0

    # Pricing
    floor_price: int = 0       # Minimum player will accept
    asking_price: int = 0      # What player wants
    market_value: int = 0      # Fair market value

    # Auction state
    status: AuctionStatus = AuctionStatus.PENDING
    current_round: int = 0
    current_price: int = 0
    price_increment: int = 0   # How much price rises each round

    # Participants
    teams: dict[UUID, TeamBid] = field(default_factory=dict)
    user_team_id: Optional[UUID] = None  # User's team if participating

    # Round history
    rounds: list[AuctionRound] = field(default_factory=list)

    # Resolution
    winner_team_id: Optional[UUID] = None
    final_price: Optional[int] = None
    rejection_reason: Optional[str] = None

    def __post_init__(self):
        # Default price increment is 5% of market value, minimum $500K
        if self.price_increment == 0 and self.market_value > 0:
            self.price_increment = max(500, int(self.market_value * 0.05))

    # === Team Management ===

    def add_team(self, team: TeamBid) -> None:
        """Add a team to the auction."""
        self.teams[team.team_id] = team

    def get_active_teams(self) -> list[TeamBid]:
        """Get teams still in the auction."""
        return [t for t in self.teams.values() if t.is_active]

    def get_active_team_count(self) -> int:
        """Count of teams still in."""
        return len(self.get_active_teams())

    @property
    def user_is_participating(self) -> bool:
        """Check if user's team is in the auction."""
        if self.user_team_id is None:
            return False
        team = self.teams.get(self.user_team_id)
        return team is not None and team.is_active

    # === Auction Flow ===

    def start(self) -> AuctionRound:
        """Start the auction with round 1."""
        if self.status != AuctionStatus.PENDING:
            raise ValueError(f"Cannot start auction in {self.status} status")

        if len(self.teams) == 0:
            raise ValueError("Cannot start auction with no teams")

        self.status = AuctionStatus.BIDDING
        self.current_round = 1
        self.current_price = self.floor_price

        # Create round 1
        round_record = AuctionRound(
            round_number=1,
            price=self.current_price,
            active_teams=[t.team_id for t in self.get_active_teams()],
        )
        self.rounds.append(round_record)

        return round_record

    def process_team_action(self, team_id: UUID, action: BidAction) -> None:
        """Process a team's action for the current round."""
        if self.status != AuctionStatus.BIDDING:
            raise ValueError(f"Cannot bid in {self.status} status")

        team = self.teams.get(team_id)
        if team is None:
            raise ValueError(f"Team {team_id} not in auction")

        if not team.is_active:
            raise ValueError(f"Team {team_id} already dropped out")

        current_round = self.rounds[-1]

        if action == BidAction.DROP:
            team.drop_out()
            current_round.dropped_teams.append(team_id)
        else:
            team.stay_in()

        current_round.actions[str(team_id)] = action

    def all_teams_acted(self) -> bool:
        """Check if all active teams have acted this round."""
        current_round = self.rounds[-1]
        active_teams = self.get_active_teams()

        for team in active_teams:
            if str(team.team_id) not in current_round.actions:
                return False
        return True

    def advance_round(self) -> Optional[AuctionRound]:
        """
        Advance to next round after all teams have acted.

        Returns the new round, or None if auction resolved.
        """
        if not self.all_teams_acted():
            raise ValueError("Not all teams have acted yet")

        active_count = self.get_active_team_count()

        # Check for resolution
        if active_count <= 1:
            self._resolve()
            return None

        # Advance to next round
        self.current_round += 1
        self.current_price += self.price_increment

        round_record = AuctionRound(
            round_number=self.current_round,
            price=self.current_price,
            active_teams=[t.team_id for t in self.get_active_teams()],
        )
        self.rounds.append(round_record)

        return round_record

    def _resolve(self) -> None:
        """Resolve the auction after bidding ends."""
        active_teams = self.get_active_teams()

        if len(active_teams) == 0:
            # All teams dropped - auction failed
            self.status = AuctionStatus.FAILED
            self.rejection_reason = "all_teams_dropped"
            return

        if len(active_teams) == 1:
            # One team left - they win at current price
            winner = active_teams[0]
            self.winner_team_id = winner.team_id
            self.final_price = self.current_price
            self.status = AuctionStatus.RESOLVED
            return

        # Multiple teams still in - shouldn't happen if advance_round called correctly
        raise ValueError(f"Unexpected state: {len(active_teams)} teams still active")

    # === Player Acceptance ===

    def player_accepts(self, personality: str = "agreeable") -> bool:
        """
        Check if player accepts the winning bid.

        Stubborn players may reject offers below their asking price.
        """
        if self.status != AuctionStatus.RESOLVED:
            return False

        if self.final_price is None or self.asking_price == 0:
            return True

        offer_pct = self.final_price / self.asking_price

        # Personality-based acceptance thresholds
        thresholds = {
            "agreeable": 0.85,    # Accepts 85%+ of asking
            "stubborn": 0.95,     # Needs 95%+ of asking
            "greedy": 0.98,       # Very demanding
            "ring_chaser": 0.75,  # Will take less for contender
            "loyal": 0.80,        # Reasonable
        }

        threshold = thresholds.get(personality, 0.80)
        return offer_pct >= threshold

    def reject_winning_bid(self) -> None:
        """Player rejects the winning bid."""
        self.status = AuctionStatus.FAILED
        self.rejection_reason = "player_rejected"

    # === Serialization ===

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "auction_id": str(self.auction_id),
            "player_id": str(self.player_id),
            "player_name": self.player_name,
            "player_position": self.player_position,
            "player_overall": self.player_overall,
            "floor_price": self.floor_price,
            "asking_price": self.asking_price,
            "market_value": self.market_value,
            "status": self.status.value,
            "current_round": self.current_round,
            "current_price": self.current_price,
            "price_increment": self.price_increment,
            "active_team_count": self.get_active_team_count(),
            "user_is_participating": self.user_is_participating,
            "winner_team_id": str(self.winner_team_id) if self.winner_team_id else None,
            "final_price": self.final_price,
            "rejection_reason": self.rejection_reason,
            "teams": [
                {
                    "team_id": str(t.team_id),
                    "team_name": t.team_name,
                    "is_active": t.is_active,
                }
                for t in self.teams.values()
            ],
        }


def calculate_ai_max_offer(
    player_market_value: int,
    position_need: float,
    team_status: str,
    cap_room: int,
    player_position: str = "",
    gm_archetype: str = "balanced",
) -> int:
    """
    Calculate the maximum an AI team would pay for a player.

    Args:
        player_market_value: Fair market value (based on market rates)
        position_need: 0-1 scale of how much team needs this position
        team_status: CONTENDING, REBUILDING, etc.
        cap_room: Available cap space
        player_position: Position code (for GM valuation adjustments)
        gm_archetype: GM philosophy - affects valuation strategy

    Returns:
        Maximum offer in thousands

    GM Archetypes (from Calvetti/M-J research):
        - "analytics": Follows optimal allocation, avoids overpaying
        - "old_school": Traditional premiums, prefers veterans
        - "cap_wizard": Maximizes effective salary, loves rookies
        - "win_now": Overpays for immediate impact
        - "balanced": Market rates (default)
    """
    # Status multipliers - how desperate is the team?
    status_multipliers = {
        "DYNASTY": 1.10,
        "CONTENDING": 1.15,
        "WINDOW_CLOSING": 1.25,  # Desperate
        "EMERGING": 1.00,
        "REBUILDING": 0.85,
        "MISMANAGED": 0.75,
        "AVERAGE": 1.00,
    }

    multiplier = status_multipliers.get(team_status, 1.00)

    # Need-based adjustment (0.5 to 1.0 range based on need)
    need_factor = 0.5 + (position_need * 0.5)

    # GM archetype position adjustments
    # Research-backed: different GMs value positions differently
    archetype_adjustments = {
        "analytics": {
            # Corrects market inefficiencies
            "LT": 0.75,    # Overvalued by market
            "RB": 0.70,    # Highly replaceable
            "LG": 1.25,    # Undervalued (12.4% optimal vs 5.8% actual)
            "RG": 1.25,
            "RT": 1.20,    # Undervalued
            "ILB": 1.20,   # Undervalued (10% optimal)
            "OLB": 1.15,   # Undervalued
            "DT": 1.15,    # Interior D undervalued
            "QB": 0.90,    # High variance (R²=0.06)
        },
        "old_school": {
            # Falls for market inefficiencies
            "LT": 1.20,    # Blind side premium myth
            "QB": 1.15,    # Any QB is valuable
            "RB": 1.15,    # Bell cow philosophy
            "CB": 1.10,    # Shutdown corner premium
            "LG": 0.85,    # Undervalues guards
            "RG": 0.85,
            "ILB": 0.80,   # "Just a linebacker"
        },
        "cap_wizard": {
            # Focuses on value positions
            "LG": 1.30,    # High value per dollar
            "RG": 1.30,
            "ILB": 1.25,
            "RT": 1.20,
            "DT": 1.15,
            "QB": 0.80,    # Too expensive
            "LT": 0.75,    # Overpaid
            "RB": 0.60,    # Never pay a RB
        },
        "win_now": {
            # Pays premium for impact
            "QB": 1.25,    # Need QB to win
            "DE": 1.20,    # Pass rush wins
            "CB": 1.15,
            "WR": 1.15,
            "LT": 1.15,    # Protect QB
        },
        "balanced": {},  # Uses market rates
    }

    position_adj = archetype_adjustments.get(gm_archetype, {})
    pos_mult = position_adj.get(player_position, 1.0)
    multiplier *= pos_mult

    # Calculate max
    max_offer = int(player_market_value * multiplier * need_factor)

    # Can't exceed cap room
    max_offer = min(max_offer, cap_room)

    return max_offer


def ai_should_stay(team: TeamBid, current_price: int) -> bool:
    """
    Determine if an AI team should stay in at current price.

    Simple check: stay if current price <= their max offer.
    """
    return current_price <= team.max_offer
