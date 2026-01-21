"""
Trade Market System - Competitive Market-Based Trading.

Replaces sequential, capped trading with a simultaneous market-based auction
system where:
1. All 32 teams participate equally
2. Multiple teams can bid on the same asset
3. Sellers pick the best offer, not the first acceptable one
4. Trade volume determined by market demand, not arbitrary caps

Based on real market dynamics where competition drives prices and
all participants have equal opportunity.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple
from uuid import UUID
import random

from huddle.core.draft.picks import DraftPick, DraftPickInventory
from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    TradePhilosophy,
)
from huddle.core.ai.gm_archetypes import GMArchetype
from huddle.core.ai.position_planner import (
    PositionPlan,
    AcquisitionPath,
    DraftProspect,
    PositionNeed,
)

if TYPE_CHECKING:
    from huddle.core.models.player import Player
    from huddle.core.models.team_identity import TeamIdentity
    from huddle.core.contracts.contract import Contract
    from huddle.core.ai.trade_ai import TradeAI, TradeAsset, TradeProposal


# =============================================================================
# Configuration System (Tunable Sliders)
# =============================================================================


@dataclass
class TradeMarketConfig:
    """
    All tunable parameters for trade market behavior.

    Exposed as central config for easy tuning without code changes.

    Calibration notes (from research/exports/reference/ai_decisions/trade_value_empirical.json):
    - NFL averages ~70 trades/year (1627 trades over 2002-2025)
    - 160 player trades, 54 pick-only trades in sample
    - Most trades are lower-value (6th-7th round picks)
    """

    # === MARKET STRUCTURE ===
    max_rounds: int = 5                    # More rounds = more opportunity
    min_trade_value: int = 50              # Lower threshold - late round picks count

    # === TEAM PARTICIPATION ===
    base_participation_rate: float = 0.75  # Higher - most teams engage each round
    cooldown_rounds: int = 0               # No cooldown - teams can trade multiple times

    # === BIDDING BEHAVIOR ===
    competition_premium_max: float = 0.15  # Max % increase for contested assets
    lowball_threshold: float = 0.70        # More lenient - accept decent offers
    overbid_chance: float = 0.15           # Higher chance to overbid

    # === GM ARCHETYPE MODIFIERS ===
    gm_participation_rates: Dict[str, float] = field(default_factory=lambda: {
        "WIN_NOW": 0.80,
        "CAP_WIZARD": 0.70,
        "ANALYTICS": 0.50,
        "BALANCED": 0.40,
        "OLD_SCHOOL": 0.25,
    })
    gm_aggression_modifiers: Dict[str, float] = field(default_factory=lambda: {
        "WIN_NOW": 1.15,      # Bids 15% higher
        "CAP_WIZARD": 1.05,   # Slightly aggressive
        "ANALYTICS": 1.00,    # Market value
        "BALANCED": 0.95,     # Slightly conservative
        "OLD_SCHOOL": 0.85,   # Conservative
    })

    # === TEAM STATUS EFFECTS ===
    status_pick_value_mults: Dict[str, float] = field(default_factory=lambda: {
        "DYNASTY": 0.80,
        "CONTENDING": 0.85,
        "WINDOW_CLOSING": 0.70,  # Desperate, undervalue picks
        "REBUILDING": 1.40,      # Hoard picks
        "EMERGING": 1.20,
        "STUCK_IN_MIDDLE": 1.00,
        "UNKNOWN": 1.00,
    })
    status_player_value_mults: Dict[str, float] = field(default_factory=lambda: {
        "DYNASTY": 1.10,
        "CONTENDING": 1.05,
        "WINDOW_CLOSING": 1.15,  # Desperate for players
        "REBUILDING": 0.80,      # Sell players
        "EMERGING": 0.90,
        "STUCK_IN_MIDDLE": 1.00,
        "UNKNOWN": 1.00,
    })

    # === COMMITMENT PREMIUMS (HC09-style) ===
    commitment_premium_draft_early: float = 1.50   # Very committed to pick
    commitment_premium_draft_mid: float = 1.20
    commitment_premium_draft_late: float = 1.10
    commitment_premium_fa_path: float = 0.90       # Willing to trade pick
    commitment_premium_keep_player: float = 1.30   # Want to keep
    commitment_premium_trade_path: float = 0.85    # Actively shopping

    # === BLOCKBUSTER TRADES ===
    blockbuster_chance_per_round: float = 0.10     # 10% per round
    blockbuster_elite_threshold: int = 85          # OVR to be "elite"
    blockbuster_min_pick_haul: int = 2500          # Value required for blockbuster

    # === SCHEME FIT ===
    scheme_fit_bid_bonus_max: int = 250            # Max bonus for perfect fit
    scheme_fit_mismatch_penalty: int = 150         # Penalty for poor fit

    # === DRAFT DAY TRADES ===
    # Based on research: ~2-3 pick trades per draft (54 over 23 years ≈ 2.3/year)
    draft_mock_noise: float = 0.15                 # How much teams disagree on rankings (0.0-0.3)
    draft_trade_up_range: int = 12                 # Max picks ahead to consider trading
    draft_fall_probability: float = 0.30           # Chance a player falls past projection (higher = fewer trades)
    draft_trade_value_threshold: float = 0.90      # Min value ratio to accept trade (higher = pickier)
    draft_trade_check_frequency: int = 4           # Check for trades every N picks (performance)
    draft_max_trades_per_draft: int = 5            # Cap on trades per draft (realism)


# =============================================================================
# Market Data Structures
# =============================================================================


@dataclass
class TradeListing:
    """
    An asset available for trade.

    Created during market discovery phase when teams identify what they're
    willing to trade.
    """
    asset_type: str  # "player" or "pick"
    listing_team_id: str
    asking_price: int
    commitment_multiplier: float  # From position plan (1.0-1.6x)

    # Player info (if asset_type == "player")
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_overall: Optional[int] = None
    player_age: Optional[int] = None
    player_position: Optional[str] = None
    contract_years: Optional[int] = None

    # Pick info (if asset_type == "pick")
    pick: Optional[DraftPick] = None

    @property
    def asset_key(self) -> str:
        """Unique key for this asset."""
        if self.asset_type == "player":
            return f"player_{self.player_id}"
        elif self.pick:
            # Use year attribute (DraftPick uses 'year' not 'season')
            pick_year = getattr(self.pick, 'year', getattr(self.pick, 'season', 0))
            return f"pick_{self.pick.round}_{pick_year}_{self.listing_team_id}"
        return f"unknown_{id(self)}"

    @property
    def effective_asking_price(self) -> int:
        """Asking price adjusted by commitment multiplier."""
        return int(self.asking_price * self.commitment_multiplier)

    def __repr__(self) -> str:
        if self.asset_type == "player":
            return f"Listing: {self.player_name} ({self.player_position}, {self.player_overall} OVR) - asking {self.asking_price}"
        elif self.pick:
            return f"Listing: {self.pick} - asking {self.asking_price}"
        return "Unknown listing"


@dataclass
class TradeTarget:
    """
    Something a team wants to acquire.

    Created during market discovery when teams identify their needs.
    """
    target_type: str  # "player_position", "specific_player", "pick_round"
    team_id: str
    priority: float  # 0-1, how badly they want it
    max_value_willing: int  # Maximum they'd pay

    # Position targeting
    position: Optional[str] = None
    min_overall: Optional[int] = None

    # Specific player targeting
    player_id: Optional[str] = None

    # Pick targeting
    target_round: Optional[int] = None
    target_season: Optional[int] = None

    def matches_listing(self, listing: TradeListing) -> bool:
        """Check if this target matches a listing."""
        if self.target_type == "player_position":
            return (
                listing.asset_type == "player" and
                listing.player_position == self.position and
                (listing.player_overall or 0) >= (self.min_overall or 0)
            )
        elif self.target_type == "specific_player":
            return (
                listing.asset_type == "player" and
                listing.player_id == self.player_id
            )
        elif self.target_type == "pick_round":
            return (
                listing.asset_type == "pick" and
                listing.pick is not None and
                listing.pick.round <= (self.target_round or 7)
            )
        return False


@dataclass
class Bid:
    """
    A bid on a listing.

    Contains the bidding team's offer package and valuation.
    """
    bidding_team_id: str
    target_asset_key: str
    offered_assets: List["TradeAsset"]
    offered_value: int
    scheme_fit_bonus: int = 0

    # Metadata for auction resolution
    fills_need: bool = False
    priority: float = 0.0  # How badly this team wants it

    @property
    def total_value(self) -> int:
        """Total bid value including scheme fit."""
        return self.offered_value + self.scheme_fit_bonus

    def __repr__(self) -> str:
        assets_str = ", ".join(str(a) for a in self.offered_assets[:3])
        return f"Bid from {self.bidding_team_id}: {assets_str} (value: {self.offered_value})"


@dataclass
class BidPool:
    """
    All bids for one asset.

    Collects all competing offers for a single listing so the seller
    can evaluate them together.
    """
    listing: TradeListing
    bids: List[Bid] = field(default_factory=list)
    winning_bid: Optional[Bid] = None

    def add_bid(self, bid: Bid):
        """Add a bid to the pool."""
        self.bids.append(bid)

    @property
    def is_contested(self) -> bool:
        """True if multiple teams are bidding."""
        return len(self.bids) > 1

    @property
    def highest_bid(self) -> Optional[Bid]:
        """Get the highest value bid."""
        if not self.bids:
            return None
        return max(self.bids, key=lambda b: b.total_value)

    def __repr__(self) -> str:
        return f"BidPool for {self.listing}: {len(self.bids)} bids"


@dataclass
class ExecutedTrade:
    """Record of a completed trade."""
    seller_team_id: str
    buyer_team_id: str
    assets_to_buyer: List["TradeAsset"]
    assets_to_seller: List["TradeAsset"]
    round_executed: int
    seller_value: int
    buyer_value: int

    def __repr__(self) -> str:
        to_buyer = ", ".join(str(a) for a in self.assets_to_buyer[:2])
        to_seller = ", ".join(str(a) for a in self.assets_to_seller[:2])
        return f"Trade: {self.seller_team_id} sends {to_buyer} to {self.buyer_team_id} for {to_seller}"


@dataclass
class TradeMarket:
    """
    Central market coordinating supply and demand.

    Manages all trade activity for a single round, tracking supply (what's
    available), demand (what teams want), bids, and executed trades.
    """
    season: int
    round_number: int = 1
    config: TradeMarketConfig = field(default_factory=TradeMarketConfig)

    # Supply: team_id -> list of available assets
    supply: Dict[str, List[TradeListing]] = field(default_factory=dict)

    # Demand: team_id -> list of wanted assets
    demand: Dict[str, List[TradeTarget]] = field(default_factory=dict)

    # Bidding: asset_key -> all bids for that asset
    bid_pools: Dict[str, BidPool] = field(default_factory=dict)

    # Results
    executed_trades: List[ExecutedTrade] = field(default_factory=list)

    # Cooldowns: team_id -> last round they traded
    team_cooldowns: Dict[str, int] = field(default_factory=dict)

    def get_all_listings(self) -> List[TradeListing]:
        """Get all listings from all teams."""
        all_listings = []
        for team_listings in self.supply.values():
            all_listings.extend(team_listings)
        return all_listings

    def is_team_on_cooldown(self, team_id: str) -> bool:
        """Check if a team is on trade cooldown."""
        last_trade = self.team_cooldowns.get(team_id, -999)
        return (self.round_number - last_trade) <= self.config.cooldown_rounds

    def apply_cooldown(self, team_id: str):
        """Apply cooldown to a team after trading."""
        self.team_cooldowns[team_id] = self.round_number

    def __repr__(self) -> str:
        total_listings = sum(len(l) for l in self.supply.values())
        total_targets = sum(len(t) for t in self.demand.values())
        return f"TradeMarket(round={self.round_number}, listings={total_listings}, targets={total_targets}, trades={len(self.executed_trades)})"


# =============================================================================
# Team State Interface (to avoid circular imports)
# =============================================================================


@dataclass
class TeamTradeState:
    """
    Lightweight wrapper for team state needed during trade market operations.

    This avoids circular imports with full Team objects while providing
    all necessary data for trade decisions.
    """
    team_id: str
    roster: List["Player"]
    contracts: Dict[str, "Contract"]
    pick_inventory: DraftPickInventory
    position_plan: Optional[PositionPlan]
    identity: Optional["TeamIdentity"]
    status: TeamStatusState
    needs: Dict[str, float]  # position -> need score (0-1)

    # GM archetype for behavior modifiers
    gm_archetype: Optional[GMArchetype] = None

    # Cap situation (for salary dump motivation)
    salary_cap: int = 255_000_000  # ~$255M NFL cap
    cap_used: int = 0

    @property
    def cap_space(self) -> int:
        """Remaining cap space."""
        return self.salary_cap - self.cap_used

    @property
    def cap_pressure(self) -> float:
        """
        How much cap pressure the team is under (0-1).

        0.0 = plenty of space (< 80% used)
        0.5 = moderate pressure (90% used)
        1.0 = severe pressure (at or over cap)
        """
        if self.salary_cap <= 0:
            return 0.0
        usage = self.cap_used / self.salary_cap
        if usage >= 1.0:
            return 1.0
        elif usage >= 0.95:
            return 0.8
        elif usage >= 0.90:
            return 0.5
        elif usage >= 0.85:
            return 0.3
        else:
            return 0.0

    def get_player_by_id(self, player_id: str) -> Optional["Player"]:
        """Find a player by ID."""
        for player in self.roster:
            if str(player.id) == player_id:
                return player
        return None


# =============================================================================
# Market Discovery Functions
# =============================================================================


def identify_available_assets(
    team: TeamTradeState,
    config: TradeMarketConfig,
    draft_prospects: Optional[List[DraftProspect]] = None,
) -> List[TradeListing]:
    """
    Identify what assets a team is willing to trade (supply).

    Called during Phase 1 for all 32 teams simultaneously.
    """
    from huddle.core.ai.trade_ai import player_trade_value

    listings = []

    # === PLAYER LISTINGS ===
    for player in team.roster:
        player_id = str(player.id)
        contract = team.contracts.get(player_id)
        contract_years = contract.years_remaining if contract else 1

        # Calculate base trade value
        base_value = player_trade_value(
            player.overall,
            player.age,
            contract_years,
            player.position.value,
        )

        # Skip low-value players
        if base_value < config.min_trade_value:
            continue

        # Determine commitment multiplier from position plan
        commitment = 1.0
        if team.position_plan:
            pos_need = team.position_plan.needs.get(player.position.value)
            if pos_need:
                if pos_need.acquisition_path == AcquisitionPath.KEEP_CURRENT:
                    # Team wants to keep - high commitment = high asking price
                    if player.overall >= 85:
                        commitment = config.commitment_premium_keep_player
                    else:
                        commitment = 1.1
                elif pos_need.acquisition_path == AcquisitionPath.TRADE:
                    # Actively shopping - lower asking price
                    commitment = config.commitment_premium_trade_path
                elif pos_need.acquisition_path in (
                    AcquisitionPath.DRAFT_EARLY,
                    AcquisitionPath.DRAFT_MID,
                ):
                    # Planning to draft replacement - more willing to trade
                    commitment = 0.95

        # Status-based adjustment
        status_name = team.status.current_status.name
        status_mult = config.status_player_value_mults.get(status_name, 1.0)

        # Skip elite players unless rebuilding
        if player.overall >= 90 and team.status.current_status != TeamStatus.REBUILDING:
            continue

        # Skip positions we desperately need
        need = team.needs.get(player.position.value, 0.3)
        if need > 0.7:
            continue

        # Trade likelihood filter - be more permissive
        # Empirical data shows NFL trades lots of low-value players
        trade_likelihood = 0.4  # Higher base
        if player.age >= 30:
            trade_likelihood += 0.2
        if player.age >= 28:
            trade_likelihood += 0.1
        if need < 0.3:  # More lenient
            trade_likelihood += 0.2
        if contract_years == 1:
            trade_likelihood += 0.2
        if team.status.current_status == TeamStatus.REBUILDING:
            trade_likelihood += 0.2

        # CAP PRESSURE: Teams under cap pressure are MORE willing to trade
        # This creates salary dump scenarios
        if team.cap_pressure > 0:
            # Get contract cap hit
            cap_hit = 0
            if contract:
                cap_hit = contract.cap_hit() if hasattr(contract, 'cap_hit') else 0

            # High cap hit + high pressure = very tradeable
            if cap_hit > 10_000_000:  # $10M+ contracts
                trade_likelihood += team.cap_pressure * 0.4  # Up to +0.4
            elif cap_hit > 5_000_000:  # $5M+ contracts
                trade_likelihood += team.cap_pressure * 0.2

        if trade_likelihood <= 0.3:  # Lower threshold
            continue

        # Cap pressure also lowers asking price (desperate to move)
        if team.cap_pressure > 0.5:
            commitment *= (1.0 - team.cap_pressure * 0.2)  # Up to 20% discount

        listings.append(TradeListing(
            asset_type="player",
            listing_team_id=team.team_id,
            asking_price=base_value,
            commitment_multiplier=commitment * status_mult,
            player_id=player_id,
            player_name=player.full_name,
            player_overall=player.overall,
            player_age=player.age,
            player_position=player.position.value,
            contract_years=contract_years,
        ))

    # === PICK LISTINGS ===
    if team.pick_inventory:
        for pick in team.pick_inventory.picks:
            # Only list picks we own
            if pick.current_team_id != team.team_id:
                continue

            # Don't list compensatory picks
            if pick.is_compensatory:
                continue

            base_value = pick.estimated_value

            # Skip low-value picks
            if base_value < config.min_trade_value:
                continue

            # Determine commitment multiplier
            commitment = 1.0
            if team.position_plan and draft_prospects:
                # Check if we have a specific plan for this pick
                from huddle.core.ai.trade_ai import TradeAI

                # Project what position this pick would address
                # Higher commitment if we've DECIDED to use this pick
                for pos, need in team.position_plan.needs.items():
                    if need.acquisition_path == AcquisitionPath.DRAFT_EARLY:
                        if pick.round == 1:
                            commitment = config.commitment_premium_draft_early
                            break
                    elif need.acquisition_path == AcquisitionPath.DRAFT_MID:
                        if pick.round in (3, 4):
                            commitment = config.commitment_premium_draft_mid
                            break
                    elif need.acquisition_path == AcquisitionPath.FREE_AGENCY:
                        # Planning FA instead - pick is expendable
                        commitment = config.commitment_premium_fa_path

            # Status-based adjustment
            status_name = team.status.current_status.name
            status_mult = config.status_pick_value_mults.get(status_name, 1.0)

            listings.append(TradeListing(
                asset_type="pick",
                listing_team_id=team.team_id,
                asking_price=base_value,
                commitment_multiplier=commitment * status_mult,
                pick=pick,
            ))

    return listings


def identify_trade_targets(
    team: TeamTradeState,
    config: TradeMarketConfig,
) -> List[TradeTarget]:
    """
    Identify what a team wants to acquire (demand).

    Called during Phase 1 for all 32 teams simultaneously.
    """
    targets = []

    # === PLAYER TARGETS (based on needs) ===
    # Be MUCH more permissive - teams should opportunistically look at trade market
    # even if they have draft plans (the right player at right price changes plans)
    for position, need_score in team.needs.items():
        if need_score < 0.2:  # Very low threshold - almost all positions considered
            continue

        # Position plan affects PRIORITY but doesn't exclude
        priority_modifier = 1.0
        if team.position_plan:
            pos_need = team.position_plan.needs.get(position)
            if pos_need:
                # If planning to draft, still look at trades but lower priority
                if pos_need.acquisition_path in (
                    AcquisitionPath.DRAFT_EARLY,
                    AcquisitionPath.DRAFT_MID,
                ):
                    priority_modifier = 0.5  # Half priority, but still look
                elif pos_need.acquisition_path == AcquisitionPath.DRAFT_LATE:
                    priority_modifier = 0.7  # Late round can be replaced by trade
                elif pos_need.acquisition_path == AcquisitionPath.KEEP_CURRENT:
                    priority_modifier = 0.3  # Low priority but opportunistic
                elif pos_need.acquisition_path == AcquisitionPath.TRADE:
                    priority_modifier = 1.5  # Actively looking!

        # Determine minimum overall based on need urgency
        if need_score >= 0.8:
            min_ovr = 75  # Desperate - take anyone decent
        elif need_score >= 0.6:
            min_ovr = 78
        else:
            min_ovr = 80  # Only want upgrades

        # Calculate max value willing to pay
        base_max = 1500 if need_score >= 0.7 else 800

        # Status adjustment
        status_name = team.status.current_status.name
        status_mult = config.status_player_value_mults.get(status_name, 1.0)
        max_value = int(base_max * status_mult)

        # Apply priority modifier from position plan
        adjusted_priority = need_score * priority_modifier

        targets.append(TradeTarget(
            target_type="player_position",
            team_id=team.team_id,
            priority=adjusted_priority,
            max_value_willing=max_value,
            position=position,
            min_overall=min_ovr,
        ))

    # === PICK TARGETS (rebuilding teams) ===
    if team.status.current_status == TeamStatus.REBUILDING:
        # Want early picks
        targets.append(TradeTarget(
            target_type="pick_round",
            team_id=team.team_id,
            priority=0.7,
            max_value_willing=2500,
            target_round=2,  # Looking for rounds 1-2
        ))

    return targets


# =============================================================================
# Bid Generation Functions
# =============================================================================


def generate_competitive_bid(
    bidding_team: TeamTradeState,
    listing: TradeListing,
    competition_level: float,
    config: TradeMarketConfig,
    draft_prospects: Optional[List[DraftProspect]] = None,
) -> Optional[Bid]:
    """
    Generate a competitive bid for a listing.

    Takes into account:
    - Competition level (more competition = higher bids)
    - Team's valuation based on needs
    - GM archetype (aggressive vs conservative bidding)
    - Scheme fit bonus
    """
    from huddle.core.ai.trade_ai import TradeAsset, player_trade_value
    from huddle.core.philosophy.evaluation import get_scheme_fit_bonus

    # Calculate how much this asset is worth TO US
    base_value = listing.asking_price

    # Scheme fit bonus
    scheme_bonus = 0
    if listing.asset_type == "player" and bidding_team.identity:
        player = bidding_team.get_player_by_id(listing.player_id)
        if player:
            scheme_bonus = get_scheme_fit_bonus(
                player,
                offensive_scheme=getattr(bidding_team.identity, 'offensive_scheme', None),
                defensive_scheme=getattr(bidding_team.identity, 'defensive_scheme', None),
            ) * 50  # Convert to trade points

    # Need bonus
    need_bonus = 0
    if listing.asset_type == "player" and listing.player_position:
        need = bidding_team.needs.get(listing.player_position, 0.3)
        if need > 0.5:
            need_bonus = int(base_value * 0.1 * need)  # Up to 10% bonus for high need

    our_valuation = base_value + scheme_bonus + need_bonus

    # GM archetype modifier
    aggression = 1.0
    if bidding_team.gm_archetype:
        arch_name = bidding_team.gm_archetype.name
        aggression = config.gm_aggression_modifiers.get(arch_name, 1.0)

    # Competition premium
    if competition_level > 0:
        premium = min(
            config.competition_premium_max,
            competition_level * config.competition_premium_max
        )
        our_valuation = int(our_valuation * (1 + premium))

    # Apply aggression modifier
    our_valuation = int(our_valuation * aggression)

    # Check if we'd even consider this (lowball threshold)
    effective_ask = listing.effective_asking_price
    if our_valuation < effective_ask * config.lowball_threshold:
        return None  # We're too far apart

    # Small chance to overbid
    if random.random() < config.overbid_chance:
        our_valuation = int(our_valuation * 1.1)

    # Build offer package from our picks
    offer_assets = []
    offer_value = 0
    target_value = our_valuation

    available_picks = []
    if bidding_team.pick_inventory:
        for pick in bidding_team.pick_inventory.picks:
            if pick.current_team_id == bidding_team.team_id and not pick.is_compensatory:
                # Check commitment - don't use heavily committed picks
                commitment = 1.0
                if bidding_team.position_plan:
                    for pos, need in bidding_team.position_plan.needs.items():
                        if need.acquisition_path == AcquisitionPath.DRAFT_EARLY and pick.round == 1:
                            commitment = config.commitment_premium_draft_early
                            break
                        elif need.acquisition_path == AcquisitionPath.DRAFT_MID and pick.round in (3, 4):
                            commitment = config.commitment_premium_draft_mid
                            break

                if commitment < 1.3:  # Only use non-committed picks
                    available_picks.append(pick)

    # Sort by value (use highest value picks first)
    available_picks.sort(key=lambda p: p.estimated_value, reverse=True)

    for pick in available_picks:
        if offer_value >= target_value:
            break

        # Status adjustment for how we value this pick
        status_name = bidding_team.status.current_status.name
        our_pick_mult = config.status_pick_value_mults.get(status_name, 1.0)
        pick_value_to_us = int(pick.estimated_value * our_pick_mult)

        offer_assets.append(TradeAsset(
            asset_type="pick",
            pick=pick,
            value=pick.estimated_value,
        ))
        offer_value += pick_value_to_us

    # Check if we have enough
    if offer_value < effective_ask * config.lowball_threshold:
        return None  # Can't afford

    # Determine priority
    priority = 0.5
    if listing.asset_type == "player" and listing.player_position:
        priority = bidding_team.needs.get(listing.player_position, 0.5)

    return Bid(
        bidding_team_id=bidding_team.team_id,
        target_asset_key=listing.asset_key,
        offered_assets=offer_assets,
        offered_value=offer_value,
        scheme_fit_bonus=scheme_bonus,
        fills_need=priority > 0.5,
        priority=priority,
    )


def generate_all_bids(
    market: TradeMarket,
    teams: Dict[str, TeamTradeState],
    draft_prospects: Optional[List[DraftProspect]] = None,
) -> None:
    """
    Phase 2: Generate all bids from interested teams.

    For each listing, find interested teams and generate their bids.
    Updates market.bid_pools in place.
    """
    all_listings = market.get_all_listings()

    for listing in all_listings:
        # Skip if seller is on cooldown
        if market.is_team_on_cooldown(listing.listing_team_id):
            continue

        pool = BidPool(listing=listing)

        # Find interested teams
        interested_teams = []
        for team_id, team in teams.items():
            # Can't bid on own assets
            if team_id == listing.listing_team_id:
                continue

            # Skip teams on cooldown
            if market.is_team_on_cooldown(team_id):
                continue

            # Check if any of their targets match this listing
            for target in market.demand.get(team_id, []):
                if target.matches_listing(listing):
                    interested_teams.append((team, target.priority))
                    break

        if not interested_teams:
            continue

        # Calculate competition level
        competition_level = min(1.0, len(interested_teams) / 3.0)

        # Generate bids
        for team, priority in interested_teams:
            # Participation check based on GM archetype
            participation_rate = market.config.base_participation_rate
            if team.gm_archetype:
                arch_name = team.gm_archetype.name
                participation_rate = market.config.gm_participation_rates.get(
                    arch_name, participation_rate
                )

            if random.random() > participation_rate:
                continue

            bid = generate_competitive_bid(
                team,
                listing,
                competition_level,
                market.config,
                draft_prospects,
            )

            if bid:
                pool.add_bid(bid)

        if pool.bids:
            market.bid_pools[listing.asset_key] = pool


# =============================================================================
# Auction Resolution Functions
# =============================================================================


def evaluate_bid_for_seller(
    seller: TeamTradeState,
    bid: Bid,
    listing: TradeListing,
    config: TradeMarketConfig,
) -> Tuple[float, str]:
    """
    Seller evaluates a bid and returns (score, reason).

    Score is used to compare bids - highest score wins.
    """
    # Base score is the offered value
    base_score = bid.total_value

    # Compare to asking price
    effective_ask = listing.effective_asking_price
    value_ratio = base_score / max(1, effective_ask)

    # Bonus for exceeding asking price
    if value_ratio >= 1.0:
        score = base_score * 1.1  # 10% bonus for meeting/exceeding
    else:
        score = base_score

    # Check if received assets fill our needs
    need_bonus = 0
    for asset in bid.offered_assets:
        if asset.asset_type == "pick":
            # Rebuilding teams love picks
            if seller.status.current_status == TeamStatus.REBUILDING:
                need_bonus += 100
        elif asset.asset_type == "player" and asset.player_position:
            need = seller.needs.get(asset.player_position, 0.3)
            if need > 0.5:
                need_bonus += 150

    score += need_bonus

    reason = f"Value: {base_score}, ratio: {value_ratio:.2f}, need_bonus: {need_bonus}"
    return score, reason


def resolve_auctions(
    market: TradeMarket,
    teams: Dict[str, TeamTradeState],
) -> List[ExecutedTrade]:
    """
    Phase 3: Resolve all auctions - best bid wins.

    Process pools in order of value (most valuable assets first),
    seller picks the best offer.
    """
    from huddle.core.ai.trade_ai import TradeAsset

    executed = []

    # Sort pools by listing value (most valuable first)
    sorted_pools = sorted(
        market.bid_pools.values(),
        key=lambda p: p.listing.effective_asking_price,
        reverse=True,
    )

    for pool in sorted_pools:
        if not pool.bids:
            continue

        listing = pool.listing
        seller = teams.get(listing.listing_team_id)
        if not seller:
            continue

        # Skip if seller already traded this round
        if market.is_team_on_cooldown(seller.team_id):
            continue

        # Evaluate all bids
        evaluated = []
        for bid in pool.bids:
            # Skip if bidder already traded
            if market.is_team_on_cooldown(bid.bidding_team_id):
                continue

            score, reason = evaluate_bid_for_seller(
                seller, bid, listing, market.config
            )
            evaluated.append((bid, score, reason))

        if not evaluated:
            continue

        # Pick the best
        winner, best_score, best_reason = max(evaluated, key=lambda x: x[1])

        # Check minimum threshold (must be at least 85% of asking)
        effective_ask = listing.effective_asking_price
        if best_score < effective_ask * market.config.lowball_threshold:
            continue  # Best offer not good enough

        # Execute trade!
        pool.winning_bid = winner

        # Create trade record
        assets_to_buyer = []
        if listing.asset_type == "player":
            assets_to_buyer.append(TradeAsset(
                asset_type="player",
                player_id=listing.player_id,
                player_name=listing.player_name,
                player_overall=listing.player_overall,
                player_age=listing.player_age,
                player_position=listing.player_position,
                contract_years=listing.contract_years,
                value=listing.asking_price,
            ))
        elif listing.asset_type == "pick":
            assets_to_buyer.append(TradeAsset(
                asset_type="pick",
                pick=listing.pick,
                value=listing.asking_price,
            ))

        trade = ExecutedTrade(
            seller_team_id=seller.team_id,
            buyer_team_id=winner.bidding_team_id,
            assets_to_buyer=assets_to_buyer,
            assets_to_seller=winner.offered_assets,
            round_executed=market.round_number,
            seller_value=winner.offered_value,
            buyer_value=listing.asking_price,
        )

        executed.append(trade)
        market.executed_trades.append(trade)

        # Apply cooldowns
        market.apply_cooldown(seller.team_id)
        market.apply_cooldown(winner.bidding_team_id)

    return executed


# =============================================================================
# Market Orchestration
# =============================================================================


def build_trade_market(
    teams: Dict[str, TeamTradeState],
    season: int,
    round_number: int,
    config: TradeMarketConfig,
    draft_prospects: Optional[List[DraftProspect]] = None,
    previous_cooldowns: Optional[Dict[str, int]] = None,
) -> TradeMarket:
    """
    Phase 1: Market Discovery - all teams identify supply and demand.

    All 32 teams simultaneously decide:
    - What assets they're willing to trade (supply)
    - What assets they want to acquire (demand)
    """
    market = TradeMarket(
        season=season,
        round_number=round_number,
        config=config,
    )

    # Carry over cooldowns from previous round
    if previous_cooldowns:
        market.team_cooldowns = previous_cooldowns.copy()

    # Build supply and demand for all teams
    for team_id, team in teams.items():
        # Supply: What are we willing to trade?
        listings = identify_available_assets(team, config, draft_prospects)
        if listings:
            market.supply[team_id] = listings

        # Demand: What do we want?
        targets = identify_trade_targets(team, config)
        if targets:
            market.demand[team_id] = targets

    return market


def simulate_trade_market(
    teams: Dict[str, TeamTradeState],
    season: int,
    config: Optional[TradeMarketConfig] = None,
    draft_prospects: Optional[List[DraftProspect]] = None,
    on_trade: Optional[callable] = None,
) -> List[ExecutedTrade]:
    """
    Main entry point: Run the full trade market simulation.

    Runs multiple rounds of:
    1. Market discovery (supply/demand)
    2. Bid generation (competitive)
    3. Auction resolution (best bid wins)

    Returns all executed trades.
    """
    if config is None:
        config = TradeMarketConfig()

    all_trades = []
    cooldowns: Dict[str, int] = {}

    for round_num in range(1, config.max_rounds + 1):
        # Phase 1: Build market
        market = build_trade_market(
            teams=teams,
            season=season,
            round_number=round_num,
            config=config,
            draft_prospects=draft_prospects,
            previous_cooldowns=cooldowns,
        )

        # Phase 2: Generate bids
        generate_all_bids(market, teams, draft_prospects)

        # Phase 3: Resolve auctions
        round_trades = resolve_auctions(market, teams)

        if not round_trades:
            break  # Market exhausted

        all_trades.extend(round_trades)

        # Update cooldowns for next round
        cooldowns = market.team_cooldowns.copy()

        # Callback for each trade (used for logging, UI updates, etc.)
        if on_trade:
            for trade in round_trades:
                on_trade(trade, round_num)

    return all_trades


# =============================================================================
# Blockbuster Trade Support
# =============================================================================


def attempt_blockbuster_trade(
    teams: Dict[str, TeamTradeState],
    season: int,
    config: TradeMarketConfig,
    draft_prospects: Optional[List[DraftProspect]] = None,
) -> Optional[ExecutedTrade]:
    """
    Attempt to generate a blockbuster trade (franchise-altering).

    Blockbuster conditions:
    1. REBUILDING team has elite (85+ OVR) player
    2. CONTENDING/WINDOW_CLOSING team has pick capital to pay
    """
    from huddle.core.ai.trade_ai import TradeAsset

    # Roll for blockbuster
    if random.random() > config.blockbuster_chance_per_round:
        return None

    # Find rebuilding teams with elite players
    for seller_id, seller in teams.items():
        if seller.status.current_status != TeamStatus.REBUILDING:
            continue

        elite_players = [
            p for p in seller.roster
            if p.overall >= config.blockbuster_elite_threshold
            and p.position.value not in ("K", "P")
        ]

        if not elite_players:
            continue

        best_elite = max(elite_players, key=lambda p: p.overall)

        # Find a buying team
        for buyer_id, buyer in teams.items():
            if buyer_id == seller_id:
                continue

            if buyer.status.current_status not in {
                TeamStatus.CONTENDING,
                TeamStatus.WINDOW_CLOSING,
            }:
                continue

            # Check if they need this position
            need = buyer.needs.get(best_elite.position.value, 0.3)
            if need < 0.3:
                continue

            # Check pick capital
            available_picks = []
            if buyer.pick_inventory:
                for pick in buyer.pick_inventory.picks:
                    if pick.current_team_id == buyer_id and not pick.is_compensatory:
                        available_picks.append(pick)

            available_picks.sort(key=lambda p: p.estimated_value, reverse=True)

            # Build blockbuster package
            offer_value = 0
            offer_picks = []
            for pick in available_picks[:4]:
                offer_picks.append(pick)
                offer_value += pick.estimated_value
                if offer_value >= config.blockbuster_min_pick_haul:
                    break

            if offer_value < config.blockbuster_min_pick_haul:
                continue

            # Create blockbuster trade
            from huddle.core.ai.trade_ai import player_trade_value

            contract = seller.contracts.get(str(best_elite.id))
            player_value = player_trade_value(
                best_elite.overall,
                best_elite.age,
                contract.years_remaining if contract else 1,
                best_elite.position.value,
            )

            assets_to_buyer = [TradeAsset(
                asset_type="player",
                player_id=str(best_elite.id),
                player_name=best_elite.full_name,
                player_overall=best_elite.overall,
                player_age=best_elite.age,
                player_position=best_elite.position.value,
                contract_years=contract.years_remaining if contract else 1,
                value=player_value,
            )]

            assets_to_seller = [
                TradeAsset(asset_type="pick", pick=p, value=p.estimated_value)
                for p in offer_picks
            ]

            return ExecutedTrade(
                seller_team_id=seller_id,
                buyer_team_id=buyer_id,
                assets_to_buyer=assets_to_buyer,
                assets_to_seller=assets_to_seller,
                round_executed=0,  # Pre-market blockbuster
                seller_value=offer_value,
                buyer_value=player_value,
            )

    return None
