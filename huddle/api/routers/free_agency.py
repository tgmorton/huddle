"""
API Router for Free Agency Bidding System.

Provides endpoints for:
- Managing FA sessions
- Viewing available free agents
- Running ascending auctions
- Submitting bids
- Tracking signings
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from huddle.api.schemas.free_agency import (
    CreateSessionRequest,
    StartAuctionRequest,
    SubmitBidRequest,
    SessionResponse,
    SessionDetailResponse,
    FAPlayerResponse,
    AvailablePlayersResponse,
    AuctionResponse,
    RoundResultResponse,
    AdvanceDayResponse,
    SigningResponse,
)
from huddle.api.services import free_agency_service

router = APIRouter(prefix="/free-agency", tags=["free-agency"])


# === Session Management ===

@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new free agency session.

    Generates a pool of free agents and starts the FA period.
    """
    try:
        session = free_agency_service.create_session(
            franchise_id=request.franchise_id,
            user_team_id=request.user_team_id,
        )
        return session.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """
    Get full session state including available players and active auction.
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    available = free_agency_service.get_available_players(session_id)
    signings = free_agency_service.get_signings(session_id)

    # Get active auction if any
    active_auction = None
    if session.active_auction_id:
        auction = free_agency_service.get_auction(str(session.active_auction_id))
        if auction:
            active_auction = auction.to_dict()

    return {
        "session": session.to_dict(),
        "available_players": [p.to_dict() for p in available],
        "active_auction": active_auction,
        "signings": signings,
    }


@router.post("/sessions/{session_id}/advance-day", response_model=AdvanceDayResponse)
async def advance_day(session_id: str):
    """
    Advance to the next day in the FA period.

    - Resolves any pending auctions
    - New players become available
    - Holdout players may lower their asking price
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = free_agency_service.advance_day(session_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# === Player Browsing ===

@router.get("/sessions/{session_id}/available", response_model=AvailablePlayersResponse)
async def get_available_players(session_id: str):
    """
    Get all free agents available today.

    Returns players who are on the market and not currently in auction.
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    players = free_agency_service.get_available_players(session_id)

    return {
        "day": session.current_day,
        "count": len(players),
        "players": [p.to_dict() for p in players],
    }


@router.get("/sessions/{session_id}/players/{player_id}", response_model=FAPlayerResponse)
async def get_player(session_id: str, player_id: str):
    """
    Get details about a specific free agent.
    """
    player = free_agency_service.get_player(session_id, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return player.to_dict()


# === Auction Management ===

@router.post("/sessions/{session_id}/auctions", response_model=AuctionResponse)
async def start_auction(session_id: str, request: StartAuctionRequest):
    """
    Start an auction for a free agent.

    Creates an ascending auction where teams bid against each other.
    The auction starts at the player's floor price and rises each round.
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    auction = free_agency_service.start_auction(
        session_id=session_id,
        player_id=str(request.player_id),
        user_opening_bid=request.opening_bid,
    )

    if not auction:
        raise HTTPException(status_code=400, detail="Failed to start auction. Player may not be available.")

    return auction.to_dict()


@router.get("/sessions/{session_id}/auctions/{auction_id}", response_model=AuctionResponse)
async def get_auction(session_id: str, auction_id: str):
    """
    Get the current state of an auction.
    """
    auction = free_agency_service.get_auction(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    return auction.to_dict()


@router.post("/sessions/{session_id}/auctions/{auction_id}/bid")
async def submit_bid(session_id: str, auction_id: str, request: SubmitBidRequest):
    """
    Submit a bid action in the current round.

    Actions:
    - "stay": Stay in at the current price
    - "drop": Drop out of the auction
    - "raise": Raise the bid (optional, aggressive move)

    After all teams act, the round advances:
    - If 1 team left: They win at current price
    - If 0 teams left: Auction fails, player stays available
    - Otherwise: Price increases, next round begins
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = free_agency_service.submit_bid(
        auction_id=auction_id,
        team_id=str(session.user_team_id),
        action=request.action.value,
        amount=request.amount,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # If auction resolved successfully, record the signing
    if result.get("auction_resolved") and result.get("outcome") == "success":
        free_agency_service.record_signing(session_id, auction_id)

    return result


# === Signings ===

@router.get("/sessions/{session_id}/signings", response_model=list[SigningResponse])
async def get_signings(session_id: str):
    """
    Get all signings made during this FA period.
    """
    session = free_agency_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return free_agency_service.get_signings(session_id)
