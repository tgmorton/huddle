"""
Free Agency Scheduling System.

Determines when free agents become available and how long they persist:
- Elite players appear early (high demand)
- Personality affects persistence (stubborn hold out longer)
- Unsatisfied players re-list with lowered asking price
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
import random

from huddle.core.contracts.market_value import calculate_market_value
from huddle.core.models.player import Player


class FAPersonality(Enum):
    """Free agent personality types affecting negotiation."""
    AGREEABLE = "agreeable"      # Signs quickly at fair value
    STUBBORN = "stubborn"        # Holds out for top dollar
    GREEDY = "greedy"            # Demands maximum, very persistent
    RING_CHASER = "ring_chaser"  # Prioritizes contenders
    LOYAL = "loyal"              # Prefers early interest


class FAStatus(Enum):
    """Status of a free agent in the market."""
    UPCOMING = "upcoming"        # Not yet available
    AVAILABLE = "available"      # On the market
    IN_AUCTION = "in_auction"    # Currently being bid on
    SIGNED = "signed"            # Signed by a team
    HOLDOUT = "holdout"          # Rejected offers, waiting


@dataclass
class FAPlayerListing:
    """A free agent player listing with market info."""

    player_id: UUID
    name: str
    position: str
    overall: int
    age: int

    # Market pricing
    market_value: int      # Fair market value (calculated)
    floor_price: int       # Minimum they'll accept (~80% of asking)
    asking_price: int      # What they want (personality-adjusted)

    # Personality and patience
    personality: FAPersonality = FAPersonality.AGREEABLE
    initial_patience: int = 5   # Days before lowering expectations
    patience_remaining: int = 5

    # Availability
    available_day: int = 1      # Day they enter market
    status: FAStatus = FAStatus.UPCOMING

    # Tracking
    interested_teams: list[UUID] = field(default_factory=list)
    rejection_count: int = 0
    original_asking: int = 0    # Track initial asking for stats

    def __post_init__(self):
        if self.original_asking == 0:
            self.original_asking = self.asking_price

    def is_available_on_day(self, day: int) -> bool:
        """Check if player is available on given day."""
        if day < self.available_day:
            return False
        return self.status in {FAStatus.AVAILABLE, FAStatus.HOLDOUT}

    def enter_market(self) -> None:
        """Player enters the free agent market."""
        self.status = FAStatus.AVAILABLE

    def start_auction(self) -> None:
        """Player enters an auction."""
        self.status = FAStatus.IN_AUCTION

    def sign(self) -> None:
        """Player signs with a team."""
        self.status = FAStatus.SIGNED

    def reject_and_holdout(self) -> None:
        """Player rejects offer and enters holdout."""
        self.status = FAStatus.HOLDOUT
        self.rejection_count += 1

    def return_to_market(self) -> None:
        """Player returns to market after holdout."""
        self.status = FAStatus.AVAILABLE

    def lower_asking(self, pct: float = 0.05) -> None:
        """Lower asking price after patience runs out."""
        self.asking_price = int(self.asking_price * (1 - pct))
        # Floor price also drops slightly
        self.floor_price = int(self.floor_price * (1 - pct * 0.5))
        # Reset patience
        self.patience_remaining = self.initial_patience

    def tick_patience(self) -> bool:
        """
        Reduce patience by 1 day.

        Returns True if patience ran out (should lower asking).
        """
        if self.status == FAStatus.HOLDOUT:
            self.patience_remaining -= 1
            if self.patience_remaining <= 0:
                return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "player_id": str(self.player_id),
            "name": self.name,
            "position": self.position,
            "overall": self.overall,
            "age": self.age,
            "market_value": self.market_value,
            "floor_price": self.floor_price,
            "asking_price": self.asking_price,
            "personality": self.personality.value,
            "available_day": self.available_day,
            "status": self.status.value,
            "interested_team_count": len(self.interested_teams),
            "rejection_count": self.rejection_count,
        }


def calculate_availability_day(overall: int, personality: FAPersonality) -> int:
    """
    Calculate which day a player enters the FA market.

    Elite players appear early (days 1-3), depth later.
    Personality can adjust timing.
    """
    # Base day by tier
    if overall >= 88:  # Elite
        base_day = 1
    elif overall >= 82:  # High starter
        base_day = random.randint(1, 3)
    elif overall >= 78:  # Starter
        base_day = random.randint(2, 5)
    elif overall >= 72:  # Solid depth
        base_day = random.randint(4, 8)
    elif overall >= 68:  # Depth
        base_day = random.randint(6, 10)
    else:  # Minimum / camp bodies
        base_day = random.randint(8, 14)

    # Personality adjustment
    if personality == FAPersonality.AGREEABLE:
        pass  # No change
    elif personality == FAPersonality.STUBBORN:
        base_day = max(1, base_day - 1)  # Appears early but may persist
    elif personality == FAPersonality.GREEDY:
        base_day = max(1, base_day - 1)  # Also appears early
    elif personality == FAPersonality.RING_CHASER:
        base_day += 1  # Waits to see contender interest
    elif personality == FAPersonality.LOYAL:
        pass  # No change

    return max(1, min(14, base_day))


def calculate_patience(personality: FAPersonality) -> int:
    """Calculate how many days a player waits before lowering asking."""
    base_patience = {
        FAPersonality.AGREEABLE: 2,
        FAPersonality.STUBBORN: 7,
        FAPersonality.GREEDY: 10,
        FAPersonality.RING_CHASER: 4,
        FAPersonality.LOYAL: 3,
    }
    return base_patience.get(personality, 3)


def calculate_asking_price(
    market_value: int,
    personality: FAPersonality,
    overall: int,
) -> int:
    """
    Calculate player's asking price based on personality.

    - Agreeable: Asks for fair market value
    - Stubborn/Greedy: Asks for premium
    - Ring-chaser: Slightly below market (wants contender)
    """
    # Personality multipliers
    multipliers = {
        FAPersonality.AGREEABLE: 1.0,
        FAPersonality.STUBBORN: 1.10,
        FAPersonality.GREEDY: 1.20,
        FAPersonality.RING_CHASER: 0.95,
        FAPersonality.LOYAL: 1.0,
    }

    multiplier = multipliers.get(personality, 1.0)

    # Elite players (88+) add extra premium regardless of personality
    if overall >= 88:
        multiplier *= 1.05

    return int(market_value * multiplier)


def calculate_floor_price(asking_price: int, personality: FAPersonality) -> int:
    """
    Calculate minimum a player will accept.

    Floor aligns with acceptance threshold so auction can succeed.
    """
    # These should match acceptance thresholds in should_player_accept()
    floor_pcts = {
        FAPersonality.AGREEABLE: 0.85,   # Accepts at 85%
        FAPersonality.STUBBORN: 0.95,    # Needs 95%
        FAPersonality.GREEDY: 0.98,      # Very demanding
        FAPersonality.RING_CHASER: 0.75, # Will take less for contender
        FAPersonality.LOYAL: 0.80,       # Reasonable
    }

    floor_pct = floor_pcts.get(personality, 0.85)
    return int(asking_price * floor_pct)


def assign_personality(player: Player) -> FAPersonality:
    """
    Assign a FA personality to a player.

    Could be based on player traits, but for now use weighted random.
    Elite players more likely to be stubborn/greedy.
    """
    overall = player.overall

    if overall >= 88:
        # Elite players
        weights = {
            FAPersonality.AGREEABLE: 0.10,
            FAPersonality.STUBBORN: 0.35,
            FAPersonality.GREEDY: 0.30,
            FAPersonality.RING_CHASER: 0.20,
            FAPersonality.LOYAL: 0.05,
        }
    elif overall >= 78:
        # Starters
        weights = {
            FAPersonality.AGREEABLE: 0.25,
            FAPersonality.STUBBORN: 0.25,
            FAPersonality.GREEDY: 0.15,
            FAPersonality.RING_CHASER: 0.20,
            FAPersonality.LOYAL: 0.15,
        }
    else:
        # Depth players
        weights = {
            FAPersonality.AGREEABLE: 0.40,
            FAPersonality.STUBBORN: 0.15,
            FAPersonality.GREEDY: 0.05,
            FAPersonality.RING_CHASER: 0.25,
            FAPersonality.LOYAL: 0.15,
        }

    personalities = list(weights.keys())
    probs = list(weights.values())

    return random.choices(personalities, weights=probs, k=1)[0]


def create_fa_listing(player: Player) -> FAPlayerListing:
    """
    Create a free agent listing from a Player object.

    Calculates market value, assigns personality, determines
    availability day and asking price.
    """
    # Get market value
    market_result = calculate_market_value(player)
    market_value = market_result.total_value

    # Assign personality
    personality = assign_personality(player)

    # Calculate asking and floor
    asking_price = calculate_asking_price(market_value, personality, player.overall)
    floor_price = calculate_floor_price(asking_price, personality)

    # Calculate availability day
    available_day = calculate_availability_day(player.overall, personality)

    # Calculate patience
    patience = calculate_patience(personality)

    # Get position as string
    pos_str = player.position.value if hasattr(player.position, 'value') else str(player.position)

    return FAPlayerListing(
        player_id=player.id,
        name=player.full_name,
        position=pos_str,
        overall=player.overall,
        age=player.age,
        market_value=market_value,
        floor_price=floor_price,
        asking_price=asking_price,
        personality=personality,
        initial_patience=patience,
        patience_remaining=patience,
        available_day=available_day,
        status=FAStatus.UPCOMING,
    )


def should_player_accept(
    listing: FAPlayerListing,
    offer_amount: int,
    winner_is_contender: bool = False,
) -> bool:
    """
    Determine if a player accepts a winning bid.

    Considers personality and offer vs asking price.
    """
    if offer_amount >= listing.asking_price:
        return True  # Always accept if meets asking

    offer_pct = offer_amount / listing.asking_price

    # Personality-based thresholds
    thresholds = {
        FAPersonality.AGREEABLE: 0.85,
        FAPersonality.STUBBORN: 0.95,
        FAPersonality.GREEDY: 0.98,
        FAPersonality.RING_CHASER: 0.75 if winner_is_contender else 0.90,
        FAPersonality.LOYAL: 0.80,
    }

    threshold = thresholds.get(listing.personality, 0.80)
    return offer_pct >= threshold


@dataclass
class FreeAgencySession:
    """
    A free agency session for a franchise.

    Tracks available players, auctions, and signings across
    a two-week FA period.
    """

    session_id: UUID = field(default_factory=uuid4)
    franchise_id: UUID = field(default_factory=uuid4)
    user_team_id: UUID = field(default_factory=uuid4)

    # Time
    current_day: int = 1
    max_days: int = 14  # Two week FA period

    # Player pool
    all_players: dict[UUID, FAPlayerListing] = field(default_factory=dict)

    # Completed
    signings: list[dict] = field(default_factory=list)  # {player_id, team_id, amount}

    # Active auction (one at a time for simplicity)
    active_auction_id: Optional[UUID] = None

    @property
    def is_active(self) -> bool:
        """Check if FA period is still active."""
        return self.current_day <= self.max_days

    def get_available_today(self) -> list[FAPlayerListing]:
        """Get all players available on current day."""
        available = []
        for listing in self.all_players.values():
            if listing.is_available_on_day(self.current_day):
                if listing.status in {FAStatus.AVAILABLE, FAStatus.HOLDOUT}:
                    available.append(listing)
        return sorted(available, key=lambda p: -p.overall)

    def get_upcoming(self) -> list[FAPlayerListing]:
        """Get players not yet available."""
        return [
            p for p in self.all_players.values()
            if p.status == FAStatus.UPCOMING and p.available_day > self.current_day
        ]

    def advance_day(self) -> dict:
        """
        Advance to the next day.

        Returns summary of what happened.
        """
        self.current_day += 1

        newly_available = []
        lowered_asking = []

        for listing in self.all_players.values():
            # Check if player becomes available today
            if listing.status == FAStatus.UPCOMING and listing.available_day == self.current_day:
                listing.enter_market()
                newly_available.append(listing)

            # Tick patience for holdouts
            if listing.status == FAStatus.HOLDOUT:
                if listing.tick_patience():
                    listing.lower_asking()
                    listing.return_to_market()
                    lowered_asking.append(listing)

        return {
            "day": self.current_day,
            "newly_available": [p.to_dict() for p in newly_available],
            "lowered_asking": [p.to_dict() for p in lowered_asking],
            "is_active": self.is_active,
        }

    def record_signing(
        self,
        player_id: UUID,
        team_id: UUID,
        team_name: str,
        amount: int,
    ) -> None:
        """Record a successful signing."""
        listing = self.all_players.get(player_id)
        if listing:
            listing.sign()

        self.signings.append({
            "player_id": str(player_id),
            "player_name": listing.name if listing else "",
            "position": listing.position if listing else "",
            "team_id": str(team_id),
            "team_name": team_name,
            "amount": amount,
            "day": self.current_day,
        })

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "session_id": str(self.session_id),
            "franchise_id": str(self.franchise_id),
            "current_day": self.current_day,
            "max_days": self.max_days,
            "is_active": self.is_active,
            "available_count": len(self.get_available_today()),
            "upcoming_count": len(self.get_upcoming()),
            "signings_count": len(self.signings),
        }
