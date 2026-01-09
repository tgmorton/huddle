"""
Contracts management router.

Handles financial and contract-related endpoints:
- Team financials
- Player contracts (list, detail)
- Contract restructure
- Cut player
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.api.schemas.management import (
    TeamFinancialsResponse,
    PlayerContractInfo,
    ContractsResponse,
    ContractYearInfo,
    ContractDetailInfo,
    RestructureContractRequest,
    RestructureContractResponse,
    CutPlayerRequest,
    CutPlayerResponse,
)
from .deps import get_session, get_session_with_team

router = APIRouter(tags=["contracts"])


@router.get("/franchise/{franchise_id}/financials", response_model=TeamFinancialsResponse)
async def get_team_financials(franchise_id: UUID) -> TeamFinancialsResponse:
    """Get salary cap and financial state for the user's team."""
    session = get_session_with_team(franchise_id)
    team = session.team

    fin = team.financials
    return TeamFinancialsResponse(
        team_abbr=team.abbreviation,
        salary_cap=fin.salary_cap,
        total_salary=fin.total_salary,
        dead_money=fin.dead_money,
        dead_money_next_year=fin.dead_money_next_year,
        cap_room=fin.cap_room,
        cap_used_pct=round(fin.cap_used_pct * 100, 1),  # Convert to percentage
    )


@router.get("/franchise/{franchise_id}/contracts", response_model=ContractsResponse)
async def get_contracts(franchise_id: UUID) -> ContractsResponse:
    """Get all player contracts for the user's team."""
    session = get_session_with_team(franchise_id)
    team = session.team

    contracts = []
    for player in team.roster.players.values():
        contracts.append(
            PlayerContractInfo(
                player_id=str(player.id),
                name=f"{player.first_name[0]}. {player.last_name}",
                position=player.position.value if player.position else "UNK",
                overall=player.overall or 0,
                age=player.age or 0,
                salary=player.salary or 0,
                signing_bonus=player.signing_bonus or 0,
                years_total=player.contract_years or 0,
                years_remaining=player.contract_year_remaining or 0,
                dead_money_if_cut=player.signing_bonus_remaining or 0,
            )
        )

    # Sort by salary descending
    contracts.sort(key=lambda c: c.salary, reverse=True)

    return ContractsResponse(
        team_abbr=team.abbreviation,
        total_salary=team.financials.total_salary,
        contracts=contracts,
    )


@router.get("/franchise/{franchise_id}/contracts/{player_id}", response_model=ContractDetailInfo)
async def get_player_contract(franchise_id: UUID, player_id: str) -> ContractDetailInfo:
    """Get detailed contract info for a specific player."""
    session = get_session_with_team(franchise_id)
    team = session.team

    # Convert string to UUID for roster lookup
    from uuid import UUID as PyUUID

    try:
        pid = PyUUID(player_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    player = team.roster.players.get(pid)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found on roster")

    # Build year-by-year breakdown
    years_info = []
    total_value = 0
    total_guaranteed = 0

    if hasattr(player, "contract") and player.contract is not None:
        contract = player.contract
        for i, year in enumerate(contract.years):
            year_num = i + 1
            cap_hit = (
                year.base_salary + contract.prorated_bonus + year.roster_bonus + year.incentives
            )
            years_info.append(
                ContractYearInfo(
                    year=year_num,
                    base_salary=year.base_salary,
                    signing_bonus_proration=contract.prorated_bonus,
                    roster_bonus=year.roster_bonus,
                    incentives=year.incentives,
                    cap_hit=cap_hit,
                    guaranteed_salary=year.guaranteed_salary,
                    is_current=(year_num == contract.current_year),
                )
            )
            total_value += year.total_cash + contract.prorated_bonus
            total_guaranteed += year.guaranteed_salary

        total_guaranteed += contract.signing_bonus  # Signing bonus is always guaranteed

        dead_this, dead_next = contract.dead_money_june1_cut()

        return ContractDetailInfo(
            player_id=player_id,
            name=f"{player.first_name} {player.last_name}",
            position=player.position.value if player.position else "UNK",
            overall=player.overall or 0,
            age=player.age or 0,
            experience=getattr(player, "experience", 0) or 0,
            total_value=total_value,
            total_guaranteed=total_guaranteed,
            signing_bonus=contract.signing_bonus,
            years_total=contract.total_years,
            years_remaining=contract.years_remaining,
            current_year=contract.current_year,
            years=years_info,
            dead_money_if_cut=contract.dead_money_if_cut(),
            dead_money_june1_this_year=dead_this,
            dead_money_june1_next_year=dead_next,
            cap_savings_if_cut=contract.cap_savings_if_cut(),
            is_restructured=contract.is_restructured,
            restructure_count=contract.restructure_count,
            can_restructure=contract.years_remaining >= 2,
        )
    else:
        # Fallback for players without full contract objects
        years_remaining = player.contract_year_remaining or 1
        salary = player.salary or 0
        signing_bonus = player.signing_bonus or 0
        prorated = signing_bonus // years_remaining if years_remaining > 0 else 0

        for i in range(years_remaining):
            years_info.append(
                ContractYearInfo(
                    year=i + 1,
                    base_salary=salary,
                    signing_bonus_proration=prorated,
                    roster_bonus=0,
                    incentives=0,
                    cap_hit=salary + prorated,
                    guaranteed_salary=0,
                    is_current=(i == 0),
                )
            )

        return ContractDetailInfo(
            player_id=player_id,
            name=f"{player.first_name} {player.last_name}",
            position=player.position.value if player.position else "UNK",
            overall=player.overall or 0,
            age=player.age or 0,
            experience=getattr(player, "experience", 0) or 0,
            total_value=salary * years_remaining + signing_bonus,
            total_guaranteed=signing_bonus,
            signing_bonus=signing_bonus,
            years_total=player.contract_years or years_remaining,
            years_remaining=years_remaining,
            current_year=1,
            years=years_info,
            dead_money_if_cut=player.signing_bonus_remaining or 0,
            dead_money_june1_this_year=prorated,
            dead_money_june1_next_year=(player.signing_bonus_remaining or 0) - prorated,
            cap_savings_if_cut=salary,
            is_restructured=False,
            restructure_count=0,
            can_restructure=years_remaining >= 2,
        )


@router.post(
    "/franchise/{franchise_id}/contracts/{player_id}/restructure",
    response_model=RestructureContractResponse,
)
async def restructure_contract(
    franchise_id: UUID, player_id: str, request: RestructureContractRequest
) -> RestructureContractResponse:
    """Restructure a player's contract by converting salary to signing bonus."""
    from huddle.core.contracts.contract import Contract
    from uuid import UUID as PyUUID

    session = get_session_with_team(franchise_id)
    team = session.team

    # Find the player
    try:
        pid = PyUUID(player_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    player = team.roster.players.get(pid)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found on roster")

    # Check if player has a contract object
    if not hasattr(player, "contract") or player.contract is None:
        raise HTTPException(
            status_code=400, detail="Player does not have a restructurable contract"
        )

    contract: Contract = player.contract

    # Check if can restructure
    if contract.years_remaining < 2:
        raise HTTPException(
            status_code=400, detail="Need at least 2 years remaining to restructure"
        )

    # Perform restructure
    current_year_data = contract.current_year_data()
    old_salary = current_year_data.base_salary if current_year_data else 0
    old_bonus = contract.signing_bonus

    cap_savings = contract.restructure(request.amount_to_convert)

    if cap_savings == 0 and request.amount_to_convert > 0:
        raise HTTPException(status_code=400, detail="Unable to restructure contract")

    new_year_data = contract.current_year_data()
    new_salary = new_year_data.base_salary if new_year_data else 0

    # Update player salary fields for display
    player.salary = new_salary
    player.signing_bonus = contract.signing_bonus
    if hasattr(player, "signing_bonus_remaining"):
        player.signing_bonus_remaining = contract.remaining_signing_bonus

    player_name = f"{player.first_name} {player.last_name}"

    return RestructureContractResponse(
        success=True,
        player_id=player_id,
        player_name=player_name,
        amount_converted=old_salary - new_salary,
        cap_savings=cap_savings,
        new_base_salary=new_salary,
        new_signing_bonus=contract.signing_bonus,
        restructure_count=contract.restructure_count,
    )


@router.post(
    "/franchise/{franchise_id}/contracts/{player_id}/cut", response_model=CutPlayerResponse
)
async def cut_player(
    franchise_id: UUID, player_id: str, request: CutPlayerRequest
) -> CutPlayerResponse:
    """Cut a player from the roster."""
    from uuid import UUID as PyUUID

    session = get_session_with_team(franchise_id)
    team = session.team

    # Find the player
    try:
        pid = PyUUID(player_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    player = team.roster.players.get(pid)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found on roster")

    player_name = f"{player.first_name} {player.last_name}"

    # Calculate dead money before cutting
    dead_this_year = 0
    dead_next_year = 0
    cap_savings = 0

    if hasattr(player, "contract") and player.contract is not None:
        contract = player.contract
        if request.june_1_designation:
            dead_this_year, dead_next_year = contract.dead_money_june1_cut()
        else:
            dead_this_year = contract.dead_money_if_cut()
            dead_next_year = 0
        cap_savings = contract.cap_savings_if_cut()
    else:
        # Simple calculation from player fields
        dead_this_year = player.signing_bonus_remaining or 0
        cap_savings = (player.salary or 0) - dead_this_year

    # Remove player from roster
    del team.roster.players[pid]

    # Add player to free agents
    if hasattr(player, "team_id"):
        player.team_id = None
    session.service.league.free_agents.append(player)

    # Update team financials
    if hasattr(team.financials, "recalculate"):
        team.financials.recalculate(list(team.roster.players.values()))

    return CutPlayerResponse(
        success=True,
        player_id=player_id,
        player_name=player_name,
        dead_money_this_year=dead_this_year,
        dead_money_next_year=dead_next_year,
        cap_savings=cap_savings,
        was_june_1=request.june_1_designation,
    )
