"""
Service layer for Historical Simulation Explorer.

Handles running simulations and extracting data for the API.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from huddle.core.simulation.historical_sim import (
    HistoricalSimulator,
    SimulationConfig as CoreSimConfig,
    SimulationResult,
    TeamState,
)
from huddle.core.league.league import League, TeamStanding as CoreTeamStanding
from huddle.core.league.nfl_data import NFL_TEAMS
from huddle.core.models.team import Team
from huddle.generators.player import generate_player
from huddle.api.schemas.history import (
    SimulationConfig,
    SimulationSummary,
    TeamSnapshot,
    TeamRoster,
    PlayerSnapshot,
    ContractSnapshot,
    StandingsData,
    TeamStanding,
    DraftData,
    DraftPick,
    TransactionData,
    TransactionLog,
    SeasonSummary,
    FullSimulationData,
    # New AI visibility schemas
    PositionAllocation,
    CapAllocationData,
    FATarget,
    FASigning,
    FAStrategyData,
    TeamProfile,
    GMComparisonEntry,
    GMComparisonData,
    # Roster planning schemas
    PositionOption,
    PositionPlan,
    RosterPlan,
    # Franchise creation schemas
    StartFranchiseResponse,
    PlayerDevelopmentEntry,
    PlayerDevelopmentResponse,
)


# In-memory storage for simulation results
_simulations: dict[str, tuple[SimulationResult, SimulationConfig]] = {}

# Data directory for saved simulations
SIMULATIONS_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "simulations"


def run_simulation(config: SimulationConfig) -> SimulationSummary:
    """Run a historical simulation and store results."""
    sim_id = str(uuid.uuid4())[:8]

    # Create team data - use NFL teams if 32 teams, otherwise generic
    if config.num_teams == 32:
        from huddle.core.league.nfl_data import NFL_TEAMS
        team_data = [
            {"id": abbr, "name": data.name}
            for abbr, data in NFL_TEAMS.items()
        ]
    else:
        team_data = [
            {"id": f"team_{i}", "name": f"Team {i}"}
            for i in range(config.num_teams)
        ]

    # Create core config
    # Core uses target_season (end year), so calculate from start_year + years
    target_season = config.start_year + config.years_to_simulate - 1
    core_config = CoreSimConfig(
        num_teams=config.num_teams,
        years_to_simulate=config.years_to_simulate,
        target_season=target_season,
        draft_rounds=config.draft_rounds,
        verbose=config.verbose,
    )

    # Run simulation
    sim = HistoricalSimulator(core_config, generate_player, team_data)
    result = sim.run()

    # Store result
    _simulations[sim_id] = (result, config)

    # Create summary
    return SimulationSummary(
        sim_id=sim_id,
        num_teams=config.num_teams,
        seasons_simulated=result.seasons_simulated,
        start_year=config.start_year,
        end_year=config.start_year + result.seasons_simulated - 1,
        total_transactions=len(result.transaction_log.transactions),
        created_at=datetime.now(),
    )


def run_simulation_with_progress(
    config: SimulationConfig,
    progress_callback: callable,
) -> SimulationSummary:
    """Run a historical simulation with progress updates."""
    from typing import Callable

    sim_id = str(uuid.uuid4())[:8]

    # Create team data - use NFL teams if 32 teams, otherwise generic
    if config.num_teams == 32:
        from huddle.core.league.nfl_data import NFL_TEAMS
        team_data = [
            {"id": abbr, "name": data.name}
            for abbr, data in NFL_TEAMS.items()
        ]
    else:
        team_data = [
            {"id": f"team_{i}", "name": f"Team {i}"}
            for i in range(config.num_teams)
        ]

    # Create core config with progress callback
    target_season = config.start_year + config.years_to_simulate - 1
    core_config = CoreSimConfig(
        num_teams=config.num_teams,
        years_to_simulate=config.years_to_simulate,
        target_season=target_season,
        draft_rounds=config.draft_rounds,
        verbose=True,  # Enable verbose for progress messages
        progress_callback=progress_callback,
    )

    # Run simulation
    progress_callback(f"Initializing {config.num_teams}-team league...")
    sim = HistoricalSimulator(core_config, generate_player, team_data)
    result = sim.run()

    # Store result
    _simulations[sim_id] = (result, config)
    progress_callback(f"Simulation complete! ID: {sim_id}")

    # Create summary
    return SimulationSummary(
        sim_id=sim_id,
        num_teams=config.num_teams,
        seasons_simulated=result.seasons_simulated,
        start_year=config.start_year,
        end_year=config.start_year + result.seasons_simulated - 1,
        total_transactions=len(result.transaction_log.transactions),
        created_at=datetime.now(),
    )


def get_simulation_result(sim_id: str) -> Optional[tuple[SimulationResult, SimulationConfig]]:
    """Get raw simulation result and config (for internal use like franchise conversion)."""
    if sim_id not in _simulations:
        return None
    return _simulations[sim_id]


def get_simulation(sim_id: str) -> Optional[FullSimulationData]:
    """Get full simulation data."""
    if sim_id not in _simulations:
        return None

    result, config = _simulations[sim_id]

    # Build season summaries
    seasons = []
    for year in range(config.start_year, config.start_year + result.seasons_simulated):
        season_txs = [
            t for t in result.transaction_log.transactions
            if t.season == year
        ]
        draft_picks = len([t for t in season_txs if t.transaction_type.value == 1])

        # Calculate average cap usage
        total_cap = sum(
            sum(c.cap_hit() for c in ts.contracts.values())
            for ts in result.teams.values()
        )
        avg_cap = total_cap / len(result.teams) if result.teams else 0

        seasons.append(SeasonSummary(
            season=year,
            total_transactions=len(season_txs),
            draft_picks=draft_picks,
            avg_cap_usage=avg_cap / 255_000 * 100,
        ))

    # Build team snapshots (final state)
    teams = []
    for team_id, team in result.teams.items():
        cap_used = sum(c.cap_hit() for c in team.contracts.values())
        teams.append(TeamSnapshot(
            team_id=team_id,
            team_name=team.team_name,
            season=config.start_year + result.seasons_simulated - 1,
            wins=team.wins,
            losses=team.losses,
            win_pct=team.win_pct,
            roster_size=len(team.roster),
            cap_used=cap_used,
            cap_pct=cap_used / team.salary_cap * 100,
            status=team.status.current_status.name if team.status else "UNKNOWN",
            gm_archetype=team.gm_archetype.value if team.gm_archetype else None,
        ))

    return FullSimulationData(
        sim_id=sim_id,
        config=config,
        summary=SimulationSummary(
            sim_id=sim_id,
            num_teams=config.num_teams,
            seasons_simulated=result.seasons_simulated,
            start_year=config.start_year,
            end_year=config.start_year + result.seasons_simulated - 1,
            total_transactions=len(result.transaction_log.transactions),
            created_at=datetime.now(),
        ),
        seasons=seasons,
        teams=teams,
    )


def get_teams_in_season(sim_id: str, season: int) -> Optional[list[TeamSnapshot]]:
    """Get all team snapshots for a specific season."""
    if sim_id not in _simulations:
        return None

    result, config = _simulations[sim_id]

    teams = []
    for team_id, team in result.teams.items():
        cap_used = sum(c.cap_hit() for c in team.contracts.values())
        teams.append(TeamSnapshot(
            team_id=team_id,
            team_name=team.team_name,
            season=season,
            wins=team.wins,
            losses=team.losses,
            win_pct=team.win_pct,
            roster_size=len(team.roster),
            cap_used=cap_used,
            cap_pct=cap_used / team.salary_cap * 100,
            status=team.status.current_status.name if team.status else "UNKNOWN",
            gm_archetype=team.gm_archetype.value if team.gm_archetype else None,
        ))

    return teams


def get_standings(sim_id: str, season: int) -> Optional[StandingsData]:
    """Get standings for a specific season."""
    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]

    # Check if we have per-season standings
    if hasattr(result, 'season_standings') and season in result.season_standings:
        # Use captured season standings
        standings = []
        for rank, snapshot in enumerate(result.season_standings[season], 1):
            total_games = snapshot.wins + snapshot.losses
            win_pct = snapshot.wins / total_games if total_games > 0 else 0.5
            # Get gm_archetype from team state
            team = result.teams.get(snapshot.team_id)
            gm_arch = team.gm_archetype.value if team and team.gm_archetype else None
            standings.append(TeamStanding(
                rank=rank,
                team_id=snapshot.team_id,
                team_name=snapshot.team_name,
                wins=snapshot.wins,
                losses=snapshot.losses,
                win_pct=win_pct,
                status=snapshot.status,
                gm_archetype=gm_arch,
            ))
        return StandingsData(season=season, teams=standings)

    # Fallback to final standings (for old simulations)
    sorted_teams = sorted(
        result.teams.values(),
        key=lambda t: (t.win_pct, t.wins),
        reverse=True
    )

    standings = []
    for rank, team in enumerate(sorted_teams, 1):
        standings.append(TeamStanding(
            rank=rank,
            team_id=team.team_id,
            team_name=team.team_name,
            wins=team.wins,
            losses=team.losses,
            win_pct=team.win_pct,
            status=team.status.current_status.name if team.status else "UNKNOWN",
            gm_archetype=team.gm_archetype.value if team.gm_archetype else None,
        ))

    return StandingsData(season=season, teams=standings)


def get_draft(sim_id: str, season: int) -> Optional[DraftData]:
    """Get draft results for a specific season with AI reasoning."""
    from huddle.core.ai.draft_ai import get_research_position_value, is_draft_priority_position
    from huddle.core.ai.gm_archetypes import get_gm_profile

    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]

    if season not in result.draft_histories:
        return DraftData(season=season, picks=[])

    draft_state = result.draft_histories[season]

    picks = []
    overall_pick = 0

    # Iterate through rounds and their picks
    for round_order in draft_state.rounds:
        for pick in round_order.order:
            overall_pick += 1

            if pick.player_selected_id:
                # Find the player in teams
                player_name = "Unknown"
                position = "?"
                player_overall = 0

                for team in result.teams.values():
                    for player in team.roster:
                        if str(player.id) == pick.player_selected_id:
                            player_name = player.full_name
                            position = player.position.value
                            player_overall = player.overall
                            break

                team_name = "Unknown"
                team = result.teams.get(pick.current_team_id)
                if team:
                    team_name = team.team_name

                # Compute draft reasoning
                position_value = get_research_position_value(position)
                is_priority = is_draft_priority_position(position)

                # Get GM adjustment if available
                gm_adjustment = None
                if team and team.gm_archetype:
                    gm_profile = get_gm_profile(team.gm_archetype)
                    gm_adjustment = gm_profile.position_adjustments.get(position, 1.0) - 1.0

                picks.append(DraftPick(
                    round=pick.round,
                    pick=overall_pick - (pick.round - 1) * len(round_order.order),
                    overall=overall_pick,
                    team_id=pick.current_team_id,
                    team_name=team_name,
                    player_id=pick.player_selected_id,
                    player_name=player_name,
                    position=position,
                    overall_rating=player_overall,
                    position_value=round(position_value, 2),
                    need_score=None,  # Would need roster analysis at time of pick
                    gm_adjustment=round(gm_adjustment, 2) if gm_adjustment else None,
                    is_draft_priority=is_priority,
                ))

    return DraftData(season=season, picks=picks)


def get_transactions(
    sim_id: str,
    season: Optional[int] = None,
    team_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Optional[TransactionLog]:
    """Get transactions with optional filters."""
    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]

    transactions = list(result.transaction_log.transactions)

    # Apply filters
    if season is not None:
        transactions = [t for t in transactions if t.season == season]
    if team_id is not None:
        transactions = [t for t in transactions if t.team_id == team_id]
    if transaction_type is not None:
        transactions = [t for t in transactions if t.transaction_type.name == transaction_type]

    total = len(transactions)

    # Apply pagination
    transactions = transactions[offset:offset + limit]

    tx_data = []
    for tx in transactions:
        # Build details from available attributes
        details = {}
        if tx.contract_years:
            details["contract_years"] = tx.contract_years
        if hasattr(tx, "contract_value") and tx.contract_value:
            details["contract_value"] = tx.contract_value
        if hasattr(tx, "contract_guaranteed") and tx.contract_guaranteed:
            details["contract_guaranteed"] = tx.contract_guaranteed

        tx_data.append(TransactionData(
            id=tx.transaction_id,
            transaction_type=tx.transaction_type.name,
            season=tx.season,
            date=tx.transaction_date.isoformat() if tx.transaction_date else "",
            team_id=tx.team_id,
            team_name=tx.team_name,
            player_name=tx.player_name or "Unknown",
            player_position=tx.player_position or "",
            details=details,
        ))

    return TransactionLog(transactions=tx_data, total_count=total)


def get_team_roster(sim_id: str, team_id: str, season: int) -> Optional[TeamRoster]:
    """Get full roster for a team."""
    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]

    if team_id not in result.teams:
        return None

    team = result.teams[team_id]

    players = []
    for player in team.roster:
        contract = team.contracts.get(str(player.id))
        contract_snapshot = None
        if contract:
            contract_snapshot = ContractSnapshot(
                player_id=str(player.id),
                team_id=team_id,
                total_value=contract.total_value,
                years_remaining=contract.years_remaining,
                cap_hit=contract.cap_hit(),
                guaranteed_remaining=contract.total_guaranteed,
                contract_type=contract.contract_type.name,
            )

        players.append(PlayerSnapshot(
            id=str(player.id),
            first_name=player.first_name,
            last_name=player.last_name,
            full_name=player.full_name,
            position=player.position.value,
            overall=player.overall,
            age=player.age,
            experience_years=player.experience_years,
            contract=contract_snapshot,
        ))

    # Sort by position and overall
    position_order = ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                      "DE", "DT", "OLB", "ILB", "MLB", "CB", "FS", "SS"]
    players.sort(key=lambda p: (
        position_order.index(p.position) if p.position in position_order else 99,
        -p.overall
    ))

    cap_used = sum(c.cap_hit() for c in team.contracts.values())

    return TeamRoster(
        team_id=team_id,
        team_name=team.team_name,
        season=season,
        players=players,
        cap_used=cap_used,
        cap_remaining=team.salary_cap - cap_used,
    )


def list_simulations() -> list[SimulationSummary]:
    """List all stored simulations."""
    summaries = []
    for sim_id, (result, config) in _simulations.items():
        summaries.append(SimulationSummary(
            sim_id=sim_id,
            num_teams=config.num_teams,
            seasons_simulated=result.seasons_simulated,
            start_year=config.start_year,
            end_year=config.start_year + result.seasons_simulated - 1,
            total_transactions=len(result.transaction_log.transactions),
            created_at=datetime.now(),
        ))
    return summaries


def delete_simulation(sim_id: str) -> bool:
    """Delete a simulation from memory."""
    if sim_id in _simulations:
        del _simulations[sim_id]
        return True
    return False


# =============================================================================
# New AI Visibility Functions
# =============================================================================

# Position groupings for cap allocation analysis
POSITION_GROUPS = {
    "offense": {
        "QB": ["QB"],
        "RB": ["RB", "FB"],
        "WR": ["WR"],
        "TE": ["TE"],
        "OL": ["LT", "LG", "C", "RG", "RT"],
    },
    "defense": {
        "EDGE": ["DE", "OLB"],
        "DL": ["DT", "NT"],
        "LB": ["ILB", "MLB"],
        "CB": ["CB"],
        "S": ["FS", "SS"],
    },
}


def get_team_cap_allocation(
    sim_id: str,
    team_id: str,
    season: int
) -> Optional[CapAllocationData]:
    """Get cap allocation analysis for a team."""
    from huddle.core.ai.allocation_tables import get_optimal_allocation

    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]
    team = result.teams.get(team_id)
    if not team:
        return None

    # Calculate cap by position group
    total_cap = team.salary_cap
    cap_used = sum(c.cap_hit() for c in team.contracts.values())

    # Build position -> cap mapping
    position_cap: dict[str, int] = {}
    position_count: dict[str, int] = {}

    for player in team.roster:
        pos = player.position.value
        contract = team.contracts.get(str(player.id))
        cap_hit = contract.cap_hit() if contract else 0

        position_cap[pos] = position_cap.get(pos, 0) + cap_hit
        position_count[pos] = position_count.get(pos, 0) + 1

    # Aggregate into position groups
    def build_allocations(side: str) -> list[PositionAllocation]:
        allocations = []
        groups = POSITION_GROUPS.get(side, {})

        for group_name, positions in groups.items():
            group_cap = sum(position_cap.get(p, 0) for p in positions)
            group_count = sum(position_count.get(p, 0) for p in positions)
            actual_pct = (group_cap / total_cap * 100) if total_cap > 0 else 0

            # Get optimal target
            opt = get_optimal_allocation(group_name, side)
            target_pct = opt.get("target", 5.0) if isinstance(opt, dict) else 5.0

            allocations.append(PositionAllocation(
                position=group_name,
                actual_pct=round(actual_pct, 1),
                target_pct=target_pct,
                gap=round(target_pct - actual_pct, 1),
                player_count=group_count,
                total_cap=group_cap,
            ))

        return allocations

    return CapAllocationData(
        team_id=team_id,
        team_name=team.team_name,
        season=season,
        gm_archetype=team.gm_archetype.value if team.gm_archetype else "unknown",
        total_cap=total_cap,
        cap_used=cap_used,
        cap_pct=round(cap_used / total_cap * 100, 1) if total_cap > 0 else 0,
        offense_allocation=build_allocations("offense"),
        defense_allocation=build_allocations("defense"),
    )


def get_team_profile(
    sim_id: str,
    team_id: str,
    season: int
) -> Optional[TeamProfile]:
    """Get full team profile with AI personality."""
    from huddle.core.ai.gm_archetypes import get_gm_profile, GM_DESCRIPTIONS

    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]
    team = result.teams.get(team_id)
    if not team:
        return None

    # Get GM profile
    gm_archetype = team.gm_archetype
    gm_profile = get_gm_profile(gm_archetype) if gm_archetype else None

    # Determine spending style based on GM archetype
    spending_styles = {
        "analytics": "data-driven",
        "old_school": "conservative",
        "cap_wizard": "efficient",
        "win_now": "aggressive",
        "balanced": "balanced",
    }

    draft_philosophies = {
        "analytics": "best_available",
        "old_school": "draft_for_need",
        "cap_wizard": "best_available",
        "win_now": "draft_for_need",
        "balanced": "balanced",
    }

    arch_value = gm_archetype.value if gm_archetype else "balanced"

    return TeamProfile(
        team_id=team_id,
        team_name=team.team_name,
        season=season,
        gm_archetype=arch_value,
        gm_description=GM_DESCRIPTIONS.get(arch_value, "Balanced approach to team building"),
        rookie_premium=gm_profile.rookie_premium if gm_profile else 1.0,
        position_preferences=dict(gm_profile.position_adjustments) if gm_profile else {},
        team_identity=None,  # Would come from team.identity if available
        offensive_philosophy=None,
        defensive_philosophy=None,
        status=team.status.current_status.name if team.status else "UNKNOWN",
        status_since=team.status.status_since_season if team.status else None,
        draft_philosophy=draft_philosophies.get(arch_value, "balanced"),
        spending_style=spending_styles.get(arch_value, "balanced"),
    )


def get_team_fa_strategy(
    sim_id: str,
    team_id: str,
    season: int
) -> Optional[FAStrategyData]:
    """Get FA strategy with before/after comparison."""
    from huddle.core.ai.allocation_tables import (
        should_draft_position,
        get_position_priority,
    )
    from huddle.core.ai.draft_ai import POSITION_TO_GROUP

    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]
    team = result.teams.get(team_id)
    if not team:
        return None

    # Get FA signings for this team and season
    fa_signings = [
        tx for tx in result.transaction_log.transactions
        if tx.team_id == team_id
        and tx.season == season
        and tx.transaction_type.name == "SIGNING"
    ]

    # Build target positions based on research (what SHOULD be signed in FA)
    positions_to_sign_in_fa = []
    positions_to_draft = []

    for pos, (group, side) in POSITION_TO_GROUP.items():
        if should_draft_position(group, side):
            positions_to_draft.append(group)
        else:
            positions_to_sign_in_fa.append(group)

    # Deduplicate
    positions_to_sign_in_fa = list(set(positions_to_sign_in_fa))
    positions_to_draft = list(set(positions_to_draft))

    # Build FA targets (what the team should have targeted)
    targets = []
    for i, pos in enumerate(positions_to_sign_in_fa):
        targets.append(FATarget(
            position=pos,
            priority=i + 1,
            budget_pct=5.0,  # Default budget
            reason=f"Research recommends signing {pos} in FA (low rookie premium)",
        ))

    # Build signings list
    signings = []
    positions_filled = set()

    for tx in fa_signings:
        pos = tx.player_position
        group_info = POSITION_TO_GROUP.get(pos, (pos, "offense"))
        group = group_info[0] if isinstance(group_info, tuple) else pos

        was_target = group in positions_to_sign_in_fa
        positions_filled.add(group)

        # Find player in roster for more details
        player_overall = 0
        player_age = 0
        for player in team.roster:
            if player.full_name == tx.player_name:
                player_overall = player.overall
                player_age = player.age
                break

        contract = team.contracts.get(tx.player_id)
        cap_hit = contract.cap_hit() if contract else 0
        contract_years = contract.years_remaining if contract else 0
        contract_value = contract.total_value if contract else 0

        signings.append(FASigning(
            player_id=tx.player_id or "",
            player_name=tx.player_name or "Unknown",
            position=pos,
            overall=player_overall,
            age=player_age,
            contract_years=contract_years,
            contract_value=contract_value,
            cap_hit=cap_hit,
            was_target=was_target,
            value_vs_market=0.0,  # Would need market data to compute
        ))

    # Calculate success metrics
    target_positions_set = set(positions_to_sign_in_fa)
    positions_missed = list(target_positions_set - positions_filled)
    positions_filled_list = list(positions_filled & target_positions_set)

    plan_success = len(positions_filled_list) / len(targets) * 100 if targets else 0

    total_spent = sum(s.cap_hit for s in signings)

    return FAStrategyData(
        team_id=team_id,
        team_name=team.team_name,
        season=season,
        gm_archetype=team.gm_archetype.value if team.gm_archetype else "unknown",
        cap_space_before=team.salary_cap,  # Approximate
        target_positions=targets,
        positions_to_avoid=positions_to_draft,
        cap_space_after=team.salary_cap - sum(c.cap_hit() for c in team.contracts.values()),
        signings=signings,
        total_spent=total_spent,
        plan_success_pct=round(plan_success, 1),
        positions_filled=positions_filled_list,
        positions_missed=positions_missed,
    )


def get_gm_comparison(sim_id: str, season: int) -> Optional[GMComparisonData]:
    """Compare performance across GM archetypes."""
    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]

    # Group teams by archetype
    archetype_teams: dict[str, list] = {}
    for team in result.teams.values():
        arch = team.gm_archetype.value if team.gm_archetype else "balanced"
        if arch not in archetype_teams:
            archetype_teams[arch] = []
        archetype_teams[arch].append(team)

    entries = []
    for archetype, teams in archetype_teams.items():
        if not teams:
            continue

        total_wins = sum(t.wins for t in teams)
        total_games = sum(t.wins + t.losses for t in teams)
        avg_wins = total_wins / len(teams)
        avg_win_pct = total_wins / total_games if total_games > 0 else 0.5

        # Check season standings for playoff/championship info
        playoffs_made = 0
        championships = 0
        if hasattr(result, 'season_standings') and season in result.season_standings:
            for snapshot in result.season_standings[season]:
                team = result.teams.get(snapshot.team_id)
                if team and team.gm_archetype and team.gm_archetype.value == archetype:
                    if snapshot.made_playoffs:
                        playoffs_made += 1
                    if snapshot.won_championship:
                        championships += 1

        entries.append(GMComparisonEntry(
            archetype=archetype,
            team_count=len(teams),
            avg_wins=round(avg_wins, 1),
            avg_win_pct=round(avg_win_pct, 3),
            playoffs_made=playoffs_made,
            championships=championships,
            avg_cap_efficiency=95.0,  # Placeholder - would need detailed calculation
            draft_hit_rate=0.65,  # Placeholder - would need draft tracking
        ))

    # Sort by avg wins
    entries.sort(key=lambda e: e.avg_wins, reverse=True)

    return GMComparisonData(season=season, archetypes=entries)


def get_roster_plan(
    sim_id: str,
    team_id: str,
    season: int
) -> Optional[RosterPlan]:
    """
    Generate position-by-position roster plan showing options for each position.

    Shows for each position of need:
    - Current player (if any)
    - FA options with probabilities
    - Draft options with probabilities
    - Keep current option
    """
    import random
    from huddle.core.ai.allocation_tables import (
        get_rookie_premium,
        should_draft_position,
    )
    from huddle.core.ai.draft_ai import POSITION_TO_GROUP
    from huddle.core.ai.gm_archetypes import get_gm_profile

    if sim_id not in _simulations:
        return None

    result, _ = _simulations[sim_id]
    team = result.teams.get(team_id)
    if not team:
        return None

    # Get transactions for this team and season
    fa_signings = [
        tx for tx in result.transaction_log.transactions
        if tx.team_id == team_id
        and tx.season == season
        and tx.transaction_type.name == "SIGNING"
    ]

    draft_picks = [
        tx for tx in result.transaction_log.transactions
        if tx.team_id == team_id
        and tx.season == season
        and tx.transaction_type.name == "DRAFT"
    ]

    # Get GM profile for probability adjustments
    gm_profile = get_gm_profile(team.gm_archetype) if team.gm_archetype else None

    # Define position groups
    OFFENSE_POSITIONS = ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
    DEFENSE_POSITIONS = ["DE", "DT", "OLB", "ILB", "CB", "FS", "SS"]

    # Group roster by position
    roster_by_pos: dict[str, list] = {}
    for player in team.roster:
        pos = player.position.value
        if pos not in roster_by_pos:
            roster_by_pos[pos] = []
        roster_by_pos[pos].append(player)

    # Sort each position by overall
    for pos in roster_by_pos:
        roster_by_pos[pos].sort(key=lambda p: p.overall, reverse=True)

    # Generate synthetic FA and draft names for display
    FA_FIRST_NAMES = ["Marcus", "DeShawn", "Tyler", "Brandon", "Chris", "Jordan", "Michael", "James", "David", "Robert"]
    FA_LAST_NAMES = ["Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Anderson", "Thomas", "Jackson", "White"]
    DRAFT_FIRST_NAMES = ["Jaylen", "Malik", "Trevor", "Zach", "Justin", "Caleb", "Jalen", "Drake", "DeVonta", "Ja'Marr"]
    DRAFT_LAST_NAMES = ["Smith", "Jones", "Adams", "Lawrence", "Fields", "Williams", "Chase", "Waddle", "Pitts", "Parsons"]

    def generate_fa_name(pos: str, seed: int) -> str:
        random.seed(f"{pos}_{seed}_fa")
        return f"{random.choice(FA_FIRST_NAMES)} {random.choice(FA_LAST_NAMES)}"

    def generate_draft_name(pos: str, seed: int) -> str:
        random.seed(f"{pos}_{seed}_draft")
        return f"{random.choice(DRAFT_FIRST_NAMES)} {random.choice(DRAFT_LAST_NAMES)}"

    offense_plans = []
    defense_plans = []

    all_positions = OFFENSE_POSITIONS + DEFENSE_POSITIONS

    for pos in all_positions:
        # Get position group for research lookup
        group_info = POSITION_TO_GROUP.get(pos, (pos, "offense"))
        if isinstance(group_info, tuple):
            group, side = group_info
        else:
            group, side = pos, "offense" if pos in OFFENSE_POSITIONS else "defense"

        # Get current starter
        current_players = roster_by_pos.get(pos, [])
        current_starter = current_players[0] if current_players else None

        # Calculate need level
        need_level = 0.0
        need_reason = "Adequate depth"

        if not current_starter:
            need_level = 1.0
            need_reason = "No starter"
        elif current_starter.overall < 70:
            need_level = 0.8
            need_reason = f"Below average starter ({current_starter.overall} OVR)"
        elif current_starter.age >= 32:
            need_level = 0.7
            need_reason = f"Aging starter (age {current_starter.age})"
        elif len(current_players) < 2:
            need_level = 0.4
            need_reason = "Lacks depth"
        else:
            need_level = 0.2
            need_reason = "Solid starter"

        # Get research recommendation
        rookie_premium_data = get_rookie_premium(group, side)
        rookie_premium = rookie_premium_data.get("value_multiplier", 1.0)
        should_draft = should_draft_position(group, side)
        research_rec = "Draft" if should_draft else "Sign in FA"

        # Build options list
        options = []

        # Check if we actually signed someone at this position
        pos_signings = [s for s in fa_signings if s.player_position == pos]
        pos_drafts = [d for d in draft_picks if d.player_position == pos]

        # Calculate base probabilities based on research and what happened
        if should_draft:
            # Research says draft - higher draft probability
            base_draft_prob = 50
            base_fa_prob = 25
            base_keep_prob = 25
        else:
            # Research says sign in FA - higher FA probability
            base_draft_prob = 25
            base_fa_prob = 50
            base_keep_prob = 25

        # Adjust based on need level
        if need_level < 0.3:
            base_keep_prob += 30
            base_draft_prob -= 15
            base_fa_prob -= 15
        elif need_level > 0.7:
            base_keep_prob -= 20
            base_draft_prob += 10
            base_fa_prob += 10

        # Option 1: FA signings (actual or synthetic)
        if pos_signings:
            # Use actual signing
            for i, signing in enumerate(pos_signings[:2]):
                # Find player in roster
                player = next((p for p in team.roster if p.full_name == signing.player_name), None)
                options.append(PositionOption(
                    option_type="FA",
                    player_name=signing.player_name,
                    overall=player.overall if player else 75,
                    age=player.age if player else 27,
                    probability=base_fa_prob if i == 0 else base_fa_prob * 0.5,
                    details="Signed" if i == 0 else "Also available",
                    player_id=signing.player_id,
                    projected_cost=team.contracts.get(signing.player_id, None).cap_hit() if signing.player_id and signing.player_id in team.contracts else 3000,
                    years=team.contracts.get(signing.player_id, None).years_remaining if signing.player_id and signing.player_id in team.contracts else 3,
                ))
        else:
            # Generate synthetic FA option
            fa_name = generate_fa_name(pos, season)
            fa_ovr = random.randint(72, 82) if need_level > 0.5 else random.randint(68, 76)
            fa_age = random.randint(26, 30)
            options.append(PositionOption(
                option_type="FA",
                player_name=fa_name,
                overall=fa_ovr,
                age=fa_age,
                probability=base_fa_prob,
                details=f"Market value ~${random.randint(3, 10)}M/yr",
                projected_cost=random.randint(3000, 10000),
                years=random.randint(2, 4),
            ))

        # Option 2: Draft picks (actual or synthetic)
        if pos_drafts:
            # Use actual draft pick
            for i, pick in enumerate(pos_drafts[:2]):
                player = next((p for p in team.roster if p.full_name == pick.player_name), None)
                round_num = pick.details.get("round", 1) if isinstance(pick.details, dict) else 1
                options.append(PositionOption(
                    option_type="DRAFT",
                    player_name=pick.player_name,
                    overall=player.overall if player else 70,
                    age=player.age if player else 22,
                    probability=base_draft_prob if i == 0 else base_draft_prob * 0.4,
                    details=f"Round {round_num} pick" if i == 0 else "Late round option",
                    player_id=pick.player_id,
                    projected_cost=1500 if round_num <= 3 else 800,
                    years=4,
                ))
        else:
            # Generate synthetic draft options
            if need_level > 0.3:
                # Early round prospect (known)
                draft_name = generate_draft_name(pos, season)
                draft_ovr = random.randint(72, 80)
                options.append(PositionOption(
                    option_type="DRAFT",
                    player_name=draft_name,
                    overall=draft_ovr,
                    age=22,
                    probability=base_draft_prob * 0.6,
                    details="Round 2-3 projection",
                    projected_cost=1200,
                    years=4,
                ))

            # Late round prospect (unknown)
            options.append(PositionOption(
                option_type="DRAFT",
                player_name=f"Unknown Prospect ({pos})",
                overall=random.randint(65, 72),
                age=22,
                probability=base_draft_prob * 0.4,
                details="Round 5-7 projection",
                projected_cost=700,
                years=4,
            ))

        # Option 3: Keep current player
        if current_starter:
            contract = team.contracts.get(str(current_starter.id))
            options.append(PositionOption(
                option_type="KEEP",
                player_name=current_starter.full_name,
                overall=current_starter.overall,
                age=current_starter.age,
                probability=base_keep_prob,
                details=f"Current starter, {contract.years_remaining}yr left" if contract else "Current starter",
                player_id=str(current_starter.id),
                projected_cost=contract.cap_hit() if contract else 1000,
                years=contract.years_remaining if contract else 1,
            ))

        # Normalize probabilities to sum to ~100
        total_prob = sum(o.probability for o in options)
        if total_prob > 0:
            for o in options:
                o.probability = round(o.probability / total_prob * 100, 1)

        # Sort by probability
        options.sort(key=lambda o: o.probability, reverse=True)

        # Create position plan
        plan = PositionPlan(
            position=pos,
            position_group=group,
            need_level=round(need_level, 2),
            need_reason=need_reason,
            current_starter=current_starter.full_name if current_starter else None,
            current_overall=current_starter.overall if current_starter else None,
            current_age=current_starter.age if current_starter else None,
            current_contract_years=team.contracts.get(str(current_starter.id)).years_remaining if current_starter and str(current_starter.id) in team.contracts else None,
            research_recommendation=research_rec,
            rookie_premium=rookie_premium,
            options=options,
        )

        # Add to appropriate list (show ALL positions)
        if pos in OFFENSE_POSITIONS:
            offense_plans.append(plan)
        else:
            defense_plans.append(plan)

    # Sort plans by need level
    offense_plans.sort(key=lambda p: p.need_level, reverse=True)
    defense_plans.sort(key=lambda p: p.need_level, reverse=True)

    # Get draft picks info
    team_draft_picks = [
        f"Rd {p.details.get('round', '?')} #{p.details.get('pick', '?')}"
        for p in draft_picks
        if isinstance(p.details, dict)
    ][:10]  # Limit to first 10

    return RosterPlan(
        team_id=team_id,
        team_name=team.team_name,
        season=season,
        gm_archetype=team.gm_archetype.value if team.gm_archetype else "balanced",
        cap_space=team.salary_cap - sum(c.cap_hit() for c in team.contracts.values()),
        draft_picks=team_draft_picks if team_draft_picks else ["No picks recorded"],
        offense_plans=offense_plans,
        defense_plans=defense_plans,
        total_needs=len([p for p in offense_plans + defense_plans if p.need_level > 0.5]),
        fa_targets=len([p for p in offense_plans + defense_plans if p.research_recommendation == "Sign in FA" and p.need_level > 0.5]),
        draft_targets=len([p for p in offense_plans + defense_plans if p.research_recommendation == "Draft" and p.need_level > 0.5]),
    )


# =============================================================================
# Simulation to Playable League Conversion
# =============================================================================


def convert_simulation_to_league(
    sim_result: SimulationResult,
    target_season: Optional[int] = None,
) -> League:
    """
    Convert a SimulationResult to a playable League.

    Takes the final state of all teams from the simulation and creates
    a League object that can be used with the management system.

    Args:
        sim_result: The completed simulation result
        target_season: Season year for the league (defaults to sim's end year)

    Returns:
        A League object ready for franchise creation
    """
    from huddle.core.models.roster import Roster
    from huddle.generators.league import generate_nfl_schedule
    from huddle.generators.player import generate_draft_class

    # Use final season if not specified
    if target_season is None:
        target_season = sim_result.end_year

    # Create the league
    league = League(
        name=f"Historical League {target_season}",
        current_season=target_season,
        current_week=0,
    )

    # Create teams from simulation state
    for team_id, team_state in sim_result.teams.items():
        # Get NFL team data for this abbreviation
        nfl_data = NFL_TEAMS.get(team_id)
        if not nfl_data:
            continue

        # Create roster from simulation roster
        roster = Roster()
        for player in team_state.roster:
            roster.add_player(player)

        # Create team
        team = Team(
            abbreviation=team_id,
            name=nfl_data.nickname,
            city=nfl_data.city,
            roster=roster,
            primary_color=nfl_data.primary_color,
            secondary_color=nfl_data.secondary_color,
        )

        # Transfer contracts from simulation to team's players
        for player_id, contract in team_state.contracts.items():
            player = roster.get_player(player_id)
            if player and player.contract is None:
                player.contract = contract

        # Recalculate team financials
        team.recalculate_financials()

        # Add team to league
        league.teams[team_id] = team

        # Initialize standings from simulation
        standing = CoreTeamStanding(
            team_id=team.id,
            abbreviation=team_id,
            wins=team_state.wins,
            losses=team_state.losses,
            ties=0,
        )
        league.standings[team_id] = standing

    # Generate schedule for the new season
    league.schedule = generate_nfl_schedule(target_season, list(league.teams.keys()))

    # Generate draft class
    league.draft_class = generate_draft_class(target_season + 1)

    # Generate free agents
    from huddle.generators.league import _generate_free_agent_pool
    league.free_agents = _generate_free_agent_pool(150)

    # Set initial draft order (reverse of standings - worst teams pick first)
    sorted_teams = sorted(
        league.standings.values(),
        key=lambda s: (s.wins, s.point_diff if hasattr(s, 'point_diff') else 0)
    )
    league.draft_order = [s.abbreviation for s in sorted_teams]

    return league


def get_player_development_history(
    sim_id: str,
    player_id: str,
) -> Optional[PlayerDevelopmentResponse]:
    """
    Get the development history for a player across simulated seasons.

    Args:
        sim_id: The simulation ID
        player_id: The player's ID

    Returns:
        Development history if found, None otherwise
    """
    if sim_id not in _simulations:
        return None

    sim_result, _ = _simulations[sim_id]

    # Search for player in development histories
    if hasattr(sim_result, "player_histories") and sim_result.player_histories:
        for history in sim_result.player_histories.values():
            if str(history.player_id) == player_id:
                career_arc = []
                for entry in history.get_career_arc():
                    career_arc.append(
                        PlayerDevelopmentEntry(
                            season=entry["season"],
                            age=entry["age"],
                            overall=entry["overall"],
                            change=entry.get("change", 0),
                        )
                    )
                return PlayerDevelopmentResponse(
                    player_id=player_id,
                    player_name=history.player_name,
                    position=history.position,
                    career_arc=career_arc,
                )

    # If no development history tracking, try to find player in teams
    for team_state in sim_result.teams.values():
        for player in team_state.roster:
            if str(player.id) == player_id:
                # Return single-point "history" based on current state
                return PlayerDevelopmentResponse(
                    player_id=player_id,
                    player_name=player.full_name,
                    position=player.position.value if player.position else "UNK",
                    career_arc=[
                        PlayerDevelopmentEntry(
                            season=sim_result.end_year,
                            age=player.age,
                            overall=player.overall,
                            change=0,
                        )
                    ],
                )

    return None


# =============================================================================
# Save/Load Functions
# =============================================================================


def save_simulation(sim_id: str) -> bool:
    """
    Save a simulation to disk.

    Args:
        sim_id: The simulation ID to save

    Returns:
        True if saved successfully, False if simulation not found
    """
    if sim_id not in _simulations:
        return False

    sim_result, config = _simulations[sim_id]

    # Ensure directory exists
    SIMULATIONS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create simulation directory
    sim_dir = SIMULATIONS_DATA_DIR / sim_id
    sim_dir.mkdir(exist_ok=True)

    # Save simulation result
    result_file = sim_dir / "simulation.json"
    with open(result_file, "w") as f:
        json.dump(sim_result.to_dict(), f, indent=2, default=str)

    # Save config as metadata
    meta_file = sim_dir / "metadata.json"
    meta = {
        "sim_id": sim_id,
        "config": {
            "num_teams": config.num_teams,
            "years_to_simulate": config.years_to_simulate,
            "start_year": config.start_year,
            "draft_rounds": config.draft_rounds,
            "verbose": config.verbose,
        },
        "seasons_simulated": sim_result.seasons_simulated,
        "total_transactions": sim_result.total_transactions,
        "saved_at": datetime.now().isoformat(),
    }
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2)

    return True


def load_simulation(sim_id: str) -> Optional[SimulationSummary]:
    """
    Load a simulation from disk into memory.

    Args:
        sim_id: The simulation ID to load

    Returns:
        SimulationSummary if loaded successfully, None if not found
    """
    sim_dir = SIMULATIONS_DATA_DIR / sim_id

    if not sim_dir.exists():
        return None

    result_file = sim_dir / "simulation.json"
    meta_file = sim_dir / "metadata.json"

    if not result_file.exists() or not meta_file.exists():
        return None

    try:
        # Load metadata
        with open(meta_file) as f:
            meta = json.load(f)

        # Load simulation result
        with open(result_file) as f:
            result_data = json.load(f)

        sim_result = SimulationResult.from_dict(result_data)

        # Reconstruct config
        config_data = meta.get("config", {})
        config = SimulationConfig(
            num_teams=config_data.get("num_teams", 32),
            years_to_simulate=config_data.get("years_to_simulate", 3),
            start_year=config_data.get("start_year", 2021),
            draft_rounds=config_data.get("draft_rounds", 7),
            verbose=config_data.get("verbose", False),
        )

        # Store in memory
        _simulations[sim_id] = (sim_result, config)

        # Calculate end year
        end_year = config.start_year + sim_result.seasons_simulated - 1

        return SimulationSummary(
            sim_id=sim_id,
            num_teams=config.num_teams,
            seasons_simulated=sim_result.seasons_simulated,
            start_year=config.start_year,
            end_year=end_year,
            total_transactions=sim_result.total_transactions,
            created_at=meta.get("saved_at", datetime.now().isoformat()),
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error loading simulation {sim_id}: {e}")
        return None


def list_saved_simulations() -> list[dict]:
    """
    List all saved simulations on disk.

    Returns:
        List of dicts with simulation info (id, start_year, end_year, etc.)
    """
    saved = []

    if not SIMULATIONS_DATA_DIR.exists():
        return saved

    for sim_dir in SIMULATIONS_DATA_DIR.iterdir():
        if not sim_dir.is_dir():
            continue

        meta_file = sim_dir / "metadata.json"
        if not meta_file.exists():
            continue

        try:
            with open(meta_file) as f:
                meta = json.load(f)

            config = meta.get("config", {})
            start_year = config.get("start_year", 2021)
            seasons = meta.get("seasons_simulated", 0)

            saved.append({
                "sim_id": sim_dir.name,
                "start_year": start_year,
                "end_year": start_year + seasons - 1,
                "seasons_simulated": seasons,
                "num_teams": config.get("num_teams", 32),
                "total_transactions": meta.get("total_transactions", 0),
                "saved_at": meta.get("saved_at", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    # Sort by saved time, newest first
    saved.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    return saved


def delete_saved_simulation(sim_id: str) -> bool:
    """
    Delete a saved simulation from disk.

    Args:
        sim_id: The simulation ID to delete

    Returns:
        True if deleted successfully, False if not found
    """
    import shutil

    sim_dir = SIMULATIONS_DATA_DIR / sim_id

    if not sim_dir.exists():
        return False

    try:
        shutil.rmtree(sim_dir)
        return True
    except Exception:
        return False
