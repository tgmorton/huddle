"""
Contract Integration Module.

Bridges the legacy player contract fields with the new Contract class system.
Provides utilities for:
- Converting between legacy fields and Contract objects
- Syncing Contract state to legacy fields for backward compatibility
- Creating contracts from market value calculations
"""

from datetime import date
from typing import Optional

from huddle.core.contracts.contract import (
    Contract,
    ContractType,
    ContractYear,
    create_rookie_contract,
    create_veteran_contract,
    create_minimum_contract,
)
from huddle.core.contracts.market_value import calculate_market_value, MarketValue

# Avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from huddle.core.models.player import Player


def sync_contract_to_player(player: "Player") -> None:
    """
    Sync Contract object fields to legacy player contract fields.

    Call this after modifying a player's contract to keep legacy
    fields in sync for backward compatibility.
    """
    if not player.contract:
        return

    c = player.contract
    current = c.current_year_data()

    player.contract_years = c.total_years
    player.contract_year_remaining = c.years_remaining
    player.salary = current.base_salary if current else 0
    player.signing_bonus = c.signing_bonus

    # Calculate remaining bonus proration
    if c.proration_years > 0:
        years_remaining = c.proration_years - c.current_year + 1
        player.signing_bonus_remaining = c.prorated_bonus * max(0, years_remaining)
    else:
        player.signing_bonus_remaining = 0


def create_contract_from_legacy(player: "Player", team_id: str) -> Optional[Contract]:
    """
    Create a Contract object from legacy player fields.

    Used when upgrading existing data to use the new Contract system.
    """
    if player.contract_years is None or player.salary is None:
        return None

    import uuid

    years = []
    for i in range(player.contract_years):
        # Assume escalating salary structure
        year_salary = player.salary * (1 + i * 0.05)

        # First year guaranteed
        guaranteed = int(year_salary) if i == 0 else 0

        years.append(ContractYear(
            year_number=i + 1,
            base_salary=int(year_salary),
            guaranteed_salary=guaranteed,
            guarantee_type="full" if i == 0 else "none",
        ))

    contract = Contract(
        contract_id=str(uuid.uuid4()),
        player_id=str(player.id),
        team_id=team_id,
        contract_type=ContractType.VETERAN,  # Assume veteran for legacy
        total_years=player.contract_years,
        current_year=player.contract_years - (player.contract_year_remaining or 1) + 1,
        years=years,
        signing_bonus=player.signing_bonus or 0,
    )

    return contract


def assign_contract_with_sync(
    player: "Player",
    team_id: str,
    years: int = None,
    salary: int = None,
    signing_bonus: int = None,
    use_market_value: bool = True,
    contract_type: ContractType = ContractType.VETERAN,
    signed_date: date = None,
) -> Contract:
    """
    Assign a contract to a player, creating both the Contract object
    and syncing to legacy fields.

    This is the preferred way to assign contracts that works with
    both old and new code.
    """
    import uuid

    signed_date = signed_date or date.today()

    # Calculate values from market if needed
    if use_market_value and (years is None or salary is None):
        market = calculate_market_value(player)
        years = years or market.years
        salary = salary or market.base_salary
        signing_bonus = signing_bonus if signing_bonus is not None else market.signing_bonus

    # Defaults
    years = years or 1
    salary = salary or 1000
    signing_bonus = signing_bonus or 0

    # Create contract based on type
    if contract_type == ContractType.MINIMUM:
        contract = create_minimum_contract(
            player_id=str(player.id),
            team_id=team_id,
            years=years,
            player_experience=player.experience_years,
            signed_date=signed_date,
        )
    else:
        # Calculate total value and guaranteed
        total_value = salary * years + signing_bonus
        guaranteed = signing_bonus + salary  # First year guaranteed

        contract = create_veteran_contract(
            player_id=str(player.id),
            team_id=team_id,
            total_years=years,
            total_value=total_value,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
            signed_date=signed_date,
        )

    # Assign to player
    player.contract = contract

    # Sync to legacy fields
    sync_contract_to_player(player)

    return contract


def assign_rookie_contract_with_sync(
    player: "Player",
    team_id: str,
    pick_number: int,
    signed_date: date = None,
) -> Contract:
    """
    Assign a rookie contract based on draft position.

    Creates full Contract object and syncs to legacy fields.
    """
    signed_date = signed_date or date.today()

    contract = create_rookie_contract(
        player_id=str(player.id),
        team_id=team_id,
        pick_number=pick_number,
        signed_date=signed_date,
    )

    player.contract = contract
    player.draft_pick = pick_number

    # Sync to legacy fields
    sync_contract_to_player(player)

    return contract


def advance_contract_year(player: "Player") -> bool:
    """
    Advance a player's contract by one year.

    Updates both Contract object and legacy fields.

    Returns:
        True if contract continues, False if expired
    """
    if player.contract:
        continues = player.contract.advance_year()
        sync_contract_to_player(player)
        return continues

    # Legacy fallback
    if player.contract_year_remaining:
        player.contract_year_remaining -= 1

        # Update signing bonus remaining
        if player.signing_bonus_remaining and player.contract_years:
            bonus_per_year = player.signing_bonus // player.contract_years
            player.signing_bonus_remaining = max(0, player.signing_bonus_remaining - bonus_per_year)

        return player.contract_year_remaining > 0

    return False


def clear_contract(player: "Player") -> int:
    """
    Clear a player's contract (for free agency or release).

    Returns the dead money from clearing the contract.
    """
    dead_money = 0

    if player.contract:
        dead_money = player.contract.dead_money_if_cut()
        player.contract = None

    # Clear legacy fields
    if player.signing_bonus_remaining:
        dead_money = max(dead_money, player.signing_bonus_remaining)

    player.contract_years = None
    player.contract_year_remaining = None
    player.salary = None
    player.signing_bonus = None
    player.signing_bonus_remaining = None

    return dead_money


def restructure_contract(player: "Player", amount_to_convert: int) -> int:
    """
    Restructure a contract by converting salary to signing bonus.

    Returns cap savings achieved.
    """
    if not player.contract:
        return 0

    savings = player.contract.restructure(amount_to_convert)
    sync_contract_to_player(player)

    return savings


def get_contract_summary(player: "Player") -> dict:
    """
    Get a summary of a player's contract for display.
    """
    if player.contract:
        c = player.contract
        return {
            "type": c.contract_type.name,
            "years_total": c.total_years,
            "years_remaining": c.years_remaining,
            "total_value": c.total_value,
            "total_guaranteed": c.total_guaranteed,
            "cap_hit": c.cap_hit(),
            "dead_money": c.dead_money_if_cut(),
            "cap_savings_if_cut": c.cap_savings_if_cut(),
            "is_expiring": c.is_expiring(),
        }

    # Legacy fallback
    return {
        "type": "VETERAN",
        "years_total": player.contract_years or 0,
        "years_remaining": player.contract_year_remaining or 0,
        "total_value": (player.salary or 0) * (player.contract_years or 0),
        "total_guaranteed": player.signing_bonus or 0,
        "cap_hit": player.cap_hit,
        "dead_money": player.dead_money,
        "cap_savings_if_cut": player.cap_hit - player.dead_money,
        "is_expiring": player.is_contract_expiring,
    }


def upgrade_roster_contracts(
    roster_players: list["Player"],
    team_id: str,
) -> int:
    """
    Upgrade all players on a roster from legacy fields to Contract objects.

    Returns number of contracts upgraded.
    """
    upgraded = 0

    for player in roster_players:
        if player.contract:
            continue  # Already has Contract

        if player.contract_years is None:
            continue  # No contract to upgrade

        contract = create_contract_from_legacy(player, team_id)
        if contract:
            player.contract = contract
            upgraded += 1

    return upgraded
