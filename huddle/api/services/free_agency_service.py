"""
Service layer for Free Agency Bidding API.

Manages FA sessions, auctions, and player availability.
"""

from typing import Optional
from uuid import UUID, uuid4
import random

from huddle.core.contracts.fa_auction import (
    Auction,
    AuctionStatus,
    BidAction,
    TeamBid,
    calculate_ai_max_offer,
    ai_should_stay,
)
from huddle.core.contracts.fa_scheduling import (
    FreeAgencySession,
    FAPlayerListing,
    FAStatus,
    FAPersonality,
    create_fa_listing,
    should_player_accept,
)
from huddle.core.contracts.market_value import calculate_market_value
from huddle.core.models.player import Position
from huddle.generators.player import generate_player


# In-memory storage for FA sessions
_sessions: dict[str, FreeAgencySession] = {}
_auctions: dict[str, Auction] = {}


def create_session(
    franchise_id: UUID,
    user_team_id: UUID,
    num_free_agents: int = 100,
) -> FreeAgencySession:
    """
    Create a new FA session with generated free agents.

    Args:
        franchise_id: Franchise running the FA period
        user_team_id: User's team ID for participation tracking
        num_free_agents: Number of FAs to generate

    Returns:
        New FreeAgencySession
    """
    session = FreeAgencySession(
        franchise_id=franchise_id,
        user_team_id=user_team_id,
    )

    # Generate free agents
    positions = [
        Position.QB, Position.RB, Position.WR, Position.WR, Position.WR, Position.TE,
        Position.LT, Position.LG, Position.C, Position.RG, Position.RT,
        Position.DE, Position.DE, Position.DT, Position.DT,
        Position.OLB, Position.ILB, Position.ILB, Position.OLB,
        Position.CB, Position.CB, Position.FS, Position.SS,
    ]

    for _ in range(num_free_agents):
        position = random.choice(positions)
        player = generate_player(position=position)

        listing = create_fa_listing(player)
        session.all_players[listing.player_id] = listing

    # Initialize day 1 players as available
    for listing in session.all_players.values():
        if listing.available_day == 1:
            listing.enter_market()

    # Store session
    session_key = str(session.session_id)
    _sessions[session_key] = session

    return session


def get_session(session_id: str) -> Optional[FreeAgencySession]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def get_available_players(session_id: str) -> list[FAPlayerListing]:
    """Get all players available today in a session."""
    session = _sessions.get(session_id)
    if not session:
        return []
    return session.get_available_today()


def get_player(session_id: str, player_id: str) -> Optional[FAPlayerListing]:
    """Get a specific player listing."""
    session = _sessions.get(session_id)
    if not session:
        return None

    player_uuid = UUID(player_id)
    return session.all_players.get(player_uuid)


def advance_day(session_id: str) -> dict:
    """Advance the FA session to the next day."""
    session = _sessions.get(session_id)
    if not session:
        return {"error": "Session not found"}

    return session.advance_day()


def start_auction(
    session_id: str,
    player_id: str,
    user_opening_bid: Optional[int] = None,
    ai_teams: Optional[list[dict]] = None,
) -> Optional[Auction]:
    """
    Start an auction for a free agent.

    Args:
        session_id: FA session ID
        player_id: Player to auction
        user_opening_bid: User's opening bid (optional)
        ai_teams: List of AI team data for bidding
            [{"team_id": UUID, "name": str, "cap_room": int, "position_need": float, "status": str}]

    Returns:
        New Auction, or None if player not available
    """
    session = _sessions.get(session_id)
    if not session:
        return None

    player_uuid = UUID(player_id)
    listing = session.all_players.get(player_uuid)
    if not listing:
        return None

    if listing.status != FAStatus.AVAILABLE:
        return None

    # Create auction
    auction = Auction(
        player_id=player_uuid,
        player_name=listing.name,
        player_position=listing.position,
        player_overall=listing.overall,
        floor_price=listing.floor_price,
        asking_price=listing.asking_price,
        market_value=listing.market_value,
        user_team_id=session.user_team_id,
    )

    # Add user team
    user_bid = TeamBid(
        team_id=session.user_team_id,
        team_name="Your Team",
        cap_room=100000,  # Would come from franchise data
        position_need=0.7,  # Would be calculated
        team_status="CONTENDING",
    )
    user_bid.max_offer = user_opening_bid or listing.market_value
    auction.add_team(user_bid)

    # Add AI teams (generate some if not provided)
    if ai_teams is None:
        ai_teams = _generate_ai_interest(listing)

    for team_data in ai_teams:
        ai_bid = TeamBid(
            team_id=team_data.get("team_id", uuid4()),
            team_name=team_data.get("name", "AI Team"),
            cap_room=team_data.get("cap_room", 50000),
            position_need=team_data.get("position_need", 0.5),
            team_status=team_data.get("status", "AVERAGE"),
        )
        # Calculate AI max offer using GM archetype
        # Different GM philosophies value positions differently (research-backed)
        gm_archetype = team_data.get("gm_archetype", "balanced")
        ai_bid.max_offer = calculate_ai_max_offer(
            player_market_value=listing.market_value,
            position_need=ai_bid.position_need,
            team_status=ai_bid.team_status,
            cap_room=ai_bid.cap_room,
            player_position=listing.position,
            gm_archetype=gm_archetype,
        )
        auction.add_team(ai_bid)

    # Mark player as in auction
    listing.start_auction()
    session.active_auction_id = auction.auction_id

    # Start the auction
    auction.start()

    # Store auction
    _auctions[str(auction.auction_id)] = auction

    return auction


def get_auction(auction_id: str) -> Optional[Auction]:
    """Get an auction by ID."""
    return _auctions.get(auction_id)


def submit_bid(
    auction_id: str,
    team_id: str,
    action: str,
    amount: Optional[int] = None,
) -> dict:
    """
    Submit a bid action in an auction.

    Returns result of the round if all teams have acted.
    """
    auction = _auctions.get(auction_id)
    if not auction:
        return {"error": "Auction not found"}

    team_uuid = UUID(team_id)

    # Convert action string to enum
    try:
        bid_action = BidAction(action.lower())
    except ValueError:
        return {"error": f"Invalid action: {action}"}

    # Process the user's action
    auction.process_team_action(team_uuid, bid_action)

    # Process AI team actions
    _process_ai_bids(auction)

    # Check if round is complete
    if not auction.all_teams_acted():
        return {
            "round_complete": False,
            "waiting_for": [
                str(t.team_id) for t in auction.get_active_teams()
                if str(t.team_id) not in auction.rounds[-1].actions
            ],
        }

    # Advance to next round or resolve
    next_round = auction.advance_round()

    if next_round is None:
        # Auction resolved
        return _handle_auction_resolution(auction)

    # New round started
    return {
        "round_complete": True,
        "auction_resolved": False,
        "round_number": next_round.round_number,
        "price": next_round.price,
        "active_team_count": len(next_round.active_teams),
    }


def _process_ai_bids(auction: Auction) -> None:
    """Process all AI team bid decisions."""
    for team in auction.get_active_teams():
        if team.team_id == auction.user_team_id:
            continue  # Skip user team

        current_round = auction.rounds[-1]
        if str(team.team_id) in current_round.actions:
            continue  # Already acted

        # AI decision: stay if price <= their max
        if ai_should_stay(team, auction.current_price):
            auction.process_team_action(team.team_id, BidAction.STAY)
        else:
            auction.process_team_action(team.team_id, BidAction.DROP)


def _handle_auction_resolution(auction: Auction) -> dict:
    """Handle auction resolution and player acceptance."""
    if auction.status == AuctionStatus.FAILED:
        return {
            "round_complete": True,
            "auction_resolved": True,
            "outcome": "failed",
            "reason": auction.rejection_reason,
        }

    # Check player acceptance
    # Get personality from session (would need to look up)
    # For now, use agreeable
    if not auction.player_accepts("agreeable"):
        auction.reject_winning_bid()
        return {
            "round_complete": True,
            "auction_resolved": True,
            "outcome": "rejected",
            "reason": "player_rejected",
        }

    # Success!
    winner = auction.teams.get(auction.winner_team_id)
    return {
        "round_complete": True,
        "auction_resolved": True,
        "outcome": "success",
        "winner_team_id": str(auction.winner_team_id),
        "winner_team_name": winner.team_name if winner else "",
        "final_price": auction.final_price,
    }


def _generate_ai_interest(listing: FAPlayerListing) -> list[dict]:
    """Generate AI team interest based on player quality."""
    # Number of interested teams based on player tier
    if listing.overall >= 88:
        num_teams = random.randint(5, 10)
    elif listing.overall >= 82:
        num_teams = random.randint(3, 7)
    elif listing.overall >= 78:
        num_teams = random.randint(2, 5)
    elif listing.overall >= 72:
        num_teams = random.randint(1, 4)
    else:
        num_teams = random.randint(0, 2)

    # Team names
    team_names = [
        "Patriots", "Cowboys", "Packers", "49ers", "Chiefs",
        "Eagles", "Bills", "Bengals", "Ravens", "Dolphins",
        "Jets", "Broncos", "Raiders", "Chargers", "Steelers",
        "Browns", "Texans", "Colts", "Jaguars", "Titans",
        "Cardinals", "Rams", "Seahawks", "Saints", "Falcons",
        "Buccaneers", "Panthers", "Giants", "Commanders", "Bears",
        "Lions", "Vikings",
    ]

    # GM archetypes with weights based on team status
    # From research: different GM philosophies create market diversity
    gm_archetypes = ["analytics", "old_school", "cap_wizard", "win_now", "balanced"]

    teams = []
    for i in range(num_teams):
        name = team_names[i % len(team_names)]
        status = random.choice([
            "CONTENDING", "CONTENDING", "AVERAGE",
            "REBUILDING", "EMERGING",
        ])
        position_need = random.uniform(0.3, 1.0)
        cap_room = random.randint(20000, 80000)

        # Assign GM archetype based on team status
        if status in ("CONTENDING", "WINDOW_CLOSING"):
            # Contenders more likely to be win_now or balanced
            archetype_weights = [0.15, 0.20, 0.10, 0.35, 0.20]
        elif status in ("REBUILDING", "EMERGING"):
            # Rebuilding teams more likely to be analytics or cap_wizard
            archetype_weights = [0.30, 0.15, 0.30, 0.05, 0.20]
        else:
            # Average distribution
            archetype_weights = [0.20, 0.25, 0.15, 0.10, 0.30]

        gm_archetype = random.choices(gm_archetypes, weights=archetype_weights, k=1)[0]

        teams.append({
            "team_id": uuid4(),
            "name": name,
            "cap_room": cap_room,
            "position_need": position_need,
            "status": status,
            "gm_archetype": gm_archetype,
        })

    return teams


def record_signing(
    session_id: str,
    auction_id: str,
) -> Optional[dict]:
    """
    Record a successful signing from an auction.

    Returns signing details or None if auction not resolved.
    """
    session = _sessions.get(session_id)
    auction = _auctions.get(auction_id)

    if not session or not auction:
        return None

    if auction.status != AuctionStatus.RESOLVED:
        return None

    winner = auction.teams.get(auction.winner_team_id)
    if not winner:
        return None

    session.record_signing(
        player_id=auction.player_id,
        team_id=auction.winner_team_id,
        team_name=winner.team_name,
        amount=auction.final_price,
    )

    # Clear active auction
    session.active_auction_id = None

    return {
        "player_id": str(auction.player_id),
        "player_name": auction.player_name,
        "team_id": str(auction.winner_team_id),
        "team_name": winner.team_name,
        "amount": auction.final_price,
    }


def get_signings(session_id: str) -> list[dict]:
    """Get all signings for a session."""
    session = _sessions.get(session_id)
    if not session:
        return []
    return session.signings
