"""Pydantic schemas for Free Agency Bidding API."""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# === Enums ===

class FAPersonalitySchema(str, Enum):
    """Free agent personality types."""
    AGREEABLE = "agreeable"
    STUBBORN = "stubborn"
    GREEDY = "greedy"
    RING_CHASER = "ring_chaser"
    LOYAL = "loyal"


class FAStatusSchema(str, Enum):
    """Free agent status in the market."""
    UPCOMING = "upcoming"
    AVAILABLE = "available"
    IN_AUCTION = "in_auction"
    SIGNED = "signed"
    HOLDOUT = "holdout"


class AuctionStatusSchema(str, Enum):
    """Auction status."""
    PENDING = "pending"
    BIDDING = "bidding"
    RESOLVED = "resolved"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BidActionSchema(str, Enum):
    """Actions a team can take in bidding."""
    STAY = "stay"
    DROP = "drop"
    RAISE = "raise"


# === Request Schemas ===

class CreateSessionRequest(BaseModel):
    """Request to create a new FA session."""
    franchise_id: UUID = Field(..., description="Franchise running FA period")
    user_team_id: UUID = Field(..., description="User's team ID")


class StartAuctionRequest(BaseModel):
    """Request to start an auction for a player."""
    player_id: UUID = Field(..., description="Player to start auction for")
    opening_bid: Optional[int] = Field(
        None,
        description="Optional opening bid amount (defaults to floor price)"
    )


class SubmitBidRequest(BaseModel):
    """Request to submit a bid in an auction."""
    action: BidActionSchema = Field(..., description="Bid action: stay, drop, or raise")
    amount: Optional[int] = Field(
        None,
        description="Bid amount (only for 'raise' action)"
    )


# === Response Schemas ===

class FAPlayerResponse(BaseModel):
    """Free agent player listing response."""
    player_id: str
    name: str
    position: str
    overall: int
    age: int
    market_value: int
    floor_price: int
    asking_price: int
    personality: FAPersonalitySchema
    available_day: int
    status: FAStatusSchema
    interested_team_count: int
    rejection_count: int

    class Config:
        from_attributes = True


class TeamBidResponse(BaseModel):
    """Team participating in an auction."""
    team_id: str
    team_name: str
    is_active: bool


class AuctionResponse(BaseModel):
    """Auction state response."""
    auction_id: str
    player_id: str
    player_name: str
    player_position: str
    player_overall: int
    floor_price: int
    asking_price: int
    market_value: int
    status: AuctionStatusSchema
    current_round: int
    current_price: int
    price_increment: int
    active_team_count: int
    user_is_participating: bool
    winner_team_id: Optional[str] = None
    final_price: Optional[int] = None
    rejection_reason: Optional[str] = None
    teams: list[TeamBidResponse]

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """FA session state response."""
    session_id: str
    franchise_id: str
    current_day: int
    max_days: int
    is_active: bool
    available_count: int
    upcoming_count: int
    signings_count: int

    class Config:
        from_attributes = True


class SigningResponse(BaseModel):
    """A completed signing."""
    player_id: str
    player_name: str
    position: str
    team_id: str
    team_name: str
    amount: int
    day: int


class AvailablePlayersResponse(BaseModel):
    """List of available FA players."""
    day: int
    count: int
    players: list[FAPlayerResponse]


class AdvanceDayResponse(BaseModel):
    """Response after advancing a day."""
    day: int
    newly_available: list[FAPlayerResponse]
    lowered_asking: list[FAPlayerResponse]
    is_active: bool


class RoundResultResponse(BaseModel):
    """Result of processing a bidding round."""
    round_number: int
    price: int
    active_team_count: int
    dropped_teams: list[str]
    auction_resolved: bool
    winner_team_id: Optional[str] = None
    winner_team_name: Optional[str] = None
    final_price: Optional[int] = None


class SessionDetailResponse(BaseModel):
    """Detailed session state with active auction and available players."""
    session: SessionResponse
    available_players: list[FAPlayerResponse]
    active_auction: Optional[AuctionResponse] = None
    signings: list[SigningResponse]


# === WebSocket Message Schemas ===

class WSAuctionStarted(BaseModel):
    """WebSocket: Auction started."""
    type: str = "auction_started"
    auction_id: str
    player_name: str
    player_position: str
    player_overall: int
    starting_price: int
    team_count: int


class WSRoundStarted(BaseModel):
    """WebSocket: New bidding round started."""
    type: str = "round_started"
    auction_id: str
    round_number: int
    current_price: int
    remaining_teams: int


class WSTeamDropped(BaseModel):
    """WebSocket: Team dropped from auction."""
    type: str = "team_dropped"
    auction_id: str
    team_name: str
    remaining_count: int


class WSAuctionWon(BaseModel):
    """WebSocket: Auction won by a team."""
    type: str = "auction_won"
    auction_id: str
    winner_team_id: str
    winner_team_name: str
    final_price: int
    player_name: str


class WSAuctionFailed(BaseModel):
    """WebSocket: Auction failed (no winner)."""
    type: str = "auction_failed"
    auction_id: str
    reason: str  # "all_dropped" or "player_rejected"
    player_name: str


class WSPlayerAvailable(BaseModel):
    """WebSocket: New player became available."""
    type: str = "player_available"
    player_id: str
    name: str
    position: str
    overall: int
    market_value: int


class WSDayAdvanced(BaseModel):
    """WebSocket: Day advanced in FA period."""
    type: str = "day_advanced"
    day: int
    new_available_count: int
    lowered_asking_count: int
