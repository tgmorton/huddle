"""
Schemas for Historical Simulation Explorer API.

Provides data models for exploring simulated league history:
- Simulation summaries
- Team snapshots by season
- Standings, drafts, transactions
- Player data with contracts
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """Configuration for running a historical simulation."""
    num_teams: int = Field(default=32, ge=4, le=32)
    years_to_simulate: int = Field(default=3, ge=1, le=10)
    start_year: int = Field(default=2021, ge=2000, le=2030)
    draft_rounds: int = Field(default=7, ge=1, le=7)
    verbose: bool = False


class SimulationSummary(BaseModel):
    """Summary of a completed simulation."""
    sim_id: str
    num_teams: int
    seasons_simulated: int
    start_year: int
    end_year: int
    total_transactions: int
    created_at: datetime


class ContractSnapshot(BaseModel):
    """Contract information for a player."""
    player_id: str
    team_id: str
    total_value: int  # In thousands
    years_remaining: int
    cap_hit: int  # Current year cap hit
    guaranteed_remaining: int
    contract_type: str


class PlayerSnapshot(BaseModel):
    """Player data at a point in time."""
    id: str
    first_name: str
    last_name: str
    full_name: str
    position: str
    overall: int
    age: int
    experience_years: int
    contract: Optional[ContractSnapshot] = None


class TeamSnapshot(BaseModel):
    """Team data for a specific season."""
    team_id: str
    team_name: str
    season: int
    wins: int
    losses: int
    win_pct: float
    roster_size: int
    cap_used: int  # In thousands
    cap_pct: float
    status: str  # DYNASTY, CONTENDING, REBUILDING, etc.
    gm_archetype: Optional[str] = None  # analytics, old_school, cap_wizard, win_now, balanced


class TeamRoster(BaseModel):
    """Full roster for a team in a season."""
    team_id: str
    team_name: str
    season: int
    players: list[PlayerSnapshot]
    cap_used: int
    cap_remaining: int


class TeamStanding(BaseModel):
    """Single team's standing."""
    rank: int
    team_id: str
    team_name: str
    wins: int
    losses: int
    win_pct: float
    status: str
    gm_archetype: Optional[str] = None


class StandingsData(BaseModel):
    """Season standings."""
    season: int
    teams: list[TeamStanding]


class DraftPick(BaseModel):
    """Single draft pick with AI reasoning."""
    round: int
    pick: int
    overall: int
    team_id: str
    team_name: str
    player_id: str
    player_name: str
    position: str
    overall_rating: int
    # AI reasoning (why this pick was made)
    position_value: Optional[float] = None  # Research-backed draft value (0-1)
    need_score: Optional[float] = None  # How badly team needed this position (0-1)
    gm_adjustment: Optional[float] = None  # GM archetype modifier
    is_draft_priority: Optional[bool] = None  # Should draft vs sign in FA


class DraftData(BaseModel):
    """Draft results for a season."""
    season: int
    picks: list[DraftPick]


class TransactionData(BaseModel):
    """Single transaction record."""
    id: str
    transaction_type: str  # DRAFT, SIGNING, CUT, TRADE
    season: int
    date: str
    team_id: str
    team_name: str
    player_name: str
    player_position: str
    details: dict


class TransactionLog(BaseModel):
    """Collection of transactions."""
    transactions: list[TransactionData]
    total_count: int


class SeasonSummary(BaseModel):
    """Summary data for a single season."""
    season: int
    champion_team_id: Optional[str] = None
    champion_team_name: Optional[str] = None
    total_transactions: int
    draft_picks: int
    avg_cap_usage: float


class FullSimulationData(BaseModel):
    """Complete simulation data for export/viewing."""
    sim_id: str
    config: SimulationConfig
    summary: SimulationSummary
    seasons: list[SeasonSummary]
    teams: list[TeamSnapshot]


# =============================================================================
# New Schemas for AI System Visibility
# =============================================================================


class PositionAllocation(BaseModel):
    """Cap allocation for a single position group."""
    position: str  # QB, RB, WR, OL, etc.
    actual_pct: float  # Actual cap percentage
    target_pct: float  # Optimal target from research
    gap: float  # target - actual (positive = under-invested)
    player_count: int
    total_cap: int  # Cap dollars at this position


class CapAllocationData(BaseModel):
    """Full cap allocation analysis for a team."""
    team_id: str
    team_name: str
    season: int
    gm_archetype: str
    total_cap: int
    cap_used: int
    cap_pct: float
    offense_allocation: list[PositionAllocation]
    defense_allocation: list[PositionAllocation]


class FATarget(BaseModel):
    """A free agency target position."""
    position: str
    priority: int  # 1 = highest priority
    budget_pct: float  # Percentage of cap willing to spend
    reason: str  # Why targeting this position


class FASigning(BaseModel):
    """A completed free agency signing."""
    player_id: str
    player_name: str
    position: str
    overall: int
    age: int
    contract_years: int
    contract_value: int  # Total value
    cap_hit: int  # Year 1 cap hit
    was_target: bool  # Was this position a target?
    value_vs_market: float  # How much over/under market value


class FAStrategyData(BaseModel):
    """Free agency strategy comparison: plan vs results."""
    team_id: str
    team_name: str
    season: int
    gm_archetype: str
    # Pre-FA plan
    cap_space_before: int
    target_positions: list[FATarget]
    positions_to_avoid: list[str]  # Positions to draft instead
    # Post-FA results
    cap_space_after: int
    signings: list[FASigning]
    total_spent: int
    # Analysis
    plan_success_pct: float  # How many targets were signed
    positions_filled: list[str]
    positions_missed: list[str]


class TeamProfile(BaseModel):
    """Full team profile showing AI personality and strategy."""
    team_id: str
    team_name: str
    season: int
    # GM Profile
    gm_archetype: str
    gm_description: str
    rookie_premium: float  # How much GM values rookie contracts
    position_preferences: dict[str, float]  # Position adjustments
    # Team Identity
    team_identity: Optional[str] = None  # power_run, air_raid, etc.
    offensive_philosophy: Optional[str] = None
    defensive_philosophy: Optional[str] = None
    # Current Status
    status: str
    status_since: Optional[int] = None
    # Strategy
    draft_philosophy: str  # best_available vs draft_for_need
    spending_style: str  # aggressive, conservative, balanced


class GMComparisonEntry(BaseModel):
    """Single GM archetype's performance metrics."""
    archetype: str
    team_count: int
    avg_wins: float
    avg_win_pct: float
    playoffs_made: int
    championships: int
    avg_cap_efficiency: float  # Cap used vs optimal
    draft_hit_rate: float  # Percentage of draft picks still on roster


class GMComparisonData(BaseModel):
    """Compare performance across GM archetypes."""
    season: int
    archetypes: list[GMComparisonEntry]


# =============================================================================
# Position-by-Position Roster Planning
# =============================================================================


class PositionOption(BaseModel):
    """A single option for filling a roster spot."""
    option_type: str  # "FA", "DRAFT", "KEEP", "TRADE"
    player_name: str  # e.g., "Bobby Smith" or "Unknown Prospect (Rd 4)"
    overall: int  # Current or projected rating
    age: int
    probability: float  # 0-100, how likely this option is chosen
    details: str  # e.g., "Cap hit: $5M/yr" or "Round 2 pick"
    # Additional context
    player_id: Optional[str] = None  # If known player
    projected_cost: Optional[int] = None  # Cap hit in thousands
    years: Optional[int] = None  # Contract years


class PositionPlan(BaseModel):
    """Plan for filling a single position."""
    position: str  # QB, RB, WR, etc.
    position_group: str  # Position group for research lookup
    need_level: float  # 0-1, how much this position needs upgrading
    need_reason: str  # "No starter" / "Aging veteran" / "Below average"
    # Current state
    current_starter: Optional[str] = None  # Current starter name
    current_overall: Optional[int] = None
    current_age: Optional[int] = None
    current_contract_years: Optional[int] = None
    # Research recommendation
    research_recommendation: str  # "Draft" or "Sign in FA"
    rookie_premium: float  # Value multiplier from research
    # Options with probabilities
    options: list[PositionOption]


class RosterPlan(BaseModel):
    """Complete roster plan for a team entering the offseason."""
    team_id: str
    team_name: str
    season: int
    gm_archetype: str
    cap_space: int  # Available cap space
    draft_picks: list[str]  # e.g., ["Rd 1 #5", "Rd 2 #36", ...]
    # Position plans (only for positions with needs)
    offense_plans: list[PositionPlan]
    defense_plans: list[PositionPlan]
    # Summary
    total_needs: int
    fa_targets: int
    draft_targets: int
