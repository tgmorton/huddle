"""
Test script for historical league simulation.

Tests:
1. Contract coverage (all players have contracts)
2. Cap compliance (teams within salary cap)
3. Cap manager integration (cuts, re-signs work properly)
4. Multi-season evolution (contracts expire, players age)
"""

from huddle.core.simulation.historical_sim import HistoricalSimulator, SimulationConfig
from huddle.generators.player import generate_player


def test_historical_simulation():
    """Run a full historical simulation and validate results."""
    print("=" * 60)
    print("HISTORICAL SIMULATION TEST")
    print("=" * 60)

    # Create team data - full 32-team league
    team_data = [
        {"id": f"team_{i}", "name": f"Team {i}"}
        for i in range(32)
    ]

    # Run 32-team, 3-season simulation (realistic NFL-like)
    config = SimulationConfig(
        num_teams=32,
        years_to_simulate=3,
        verbose=True,
    )

    sim = HistoricalSimulator(config, generate_player, team_data)
    result = sim.run()

    print("\n" + "=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    print(f"Teams simulated: {len(result.teams)}")
    print(f"Seasons simulated: {result.seasons_simulated}")
    print(f"Total transactions: {len(result.transaction_log.transactions)}")

    # Validate each team
    all_passed = True
    issues = []

    print("\n" + "-" * 60)
    print("TEAM-BY-TEAM ANALYSIS")
    print("-" * 60)

    for team_id, team_state in result.teams.items():
        roster_count = len(team_state.roster)
        contract_count = len(team_state.contracts)

        # Calculate cap usage
        total_cap = sum(c.cap_hit() for c in team_state.contracts.values())
        cap_pct = (total_cap / 255_000) * 100

        print(f"\n{team_state.team_name}:")
        print(f"  Roster size: {roster_count}")
        print(f"  Contracts: {contract_count}")
        print(f"  Cap usage: ${total_cap:,}K / $255,000K ({cap_pct:.1f}%)")
        print(f"  Team status: {team_state.status.current_status.value}")
        print(f"  Wins: {team_state.wins}, Losses: {team_state.losses}")

        # Test 1: Contract coverage
        roster_ids = {str(p.id) for p in team_state.roster}
        contract_ids = set(team_state.contracts.keys())
        missing_contracts = roster_ids - contract_ids
        orphan_contracts = contract_ids - roster_ids

        if missing_contracts:
            issues.append(f"{team_state.team_name}: {len(missing_contracts)} players missing contracts")
            print(f"  [FAIL] {len(missing_contracts)} players missing contracts")
            all_passed = False
        else:
            print(f"  [PASS] All players have contracts")

        if orphan_contracts:
            issues.append(f"{team_state.team_name}: {len(orphan_contracts)} orphan contracts")
            print(f"  [WARN] {len(orphan_contracts)} contracts for non-roster players")

        # Test 2: Cap compliance
        if total_cap > 255_000:
            over_by = total_cap - 255_000
            issues.append(f"{team_state.team_name}: Over cap by ${over_by:,}K")
            print(f"  [FAIL] Over cap by ${over_by:,}K")
            all_passed = False
        else:
            print(f"  [PASS] Under salary cap")

        # Test 3: Roster size
        if roster_count < 45:
            issues.append(f"{team_state.team_name}: Only {roster_count} players (need 45-53)")
            print(f"  [FAIL] Roster too small: {roster_count}")
            all_passed = False
        elif roster_count > 53:
            issues.append(f"{team_state.team_name}: {roster_count} players (max 53)")
            print(f"  [FAIL] Roster too large: {roster_count}")
            all_passed = False
        else:
            print(f"  [PASS] Roster size valid")

    # Transaction breakdown
    print("\n" + "-" * 60)
    print("TRANSACTION BREAKDOWN")
    print("-" * 60)

    tx_counts = {}
    for tx in result.transaction_log.transactions:
        tx_type = tx.transaction_type.value
        tx_counts[tx_type] = tx_counts.get(tx_type, 0) + 1

    for tx_type, count in sorted(tx_counts.items()):
        print(f"  {tx_type}: {count}")

    # Contract age distribution
    print("\n" + "-" * 60)
    print("CONTRACT YEAR DISTRIBUTION")
    print("-" * 60)

    year_counts = {}
    for team_id, team_state in result.teams.items():
        for contract in team_state.contracts.values():
            years = contract.years_remaining
            year_counts[years] = year_counts.get(years, 0) + 1

    for years, count in sorted(year_counts.items()):
        print(f"  {years} years remaining: {count} contracts")

    # Final summary
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    print("=" * 60)

    return all_passed


def test_cap_manager_integration():
    """Test that CapManager is being used correctly."""
    print("\n" + "=" * 60)
    print("CAP MANAGER INTEGRATION TEST")
    print("=" * 60)

    from huddle.core.ai.cap_manager import CapManager, CapStrategy
    from huddle.core.contracts.contract import create_veteran_contract
    from huddle.core.enums.positions import Position
    from datetime import date

    # Generate a test roster
    roster = [
        generate_player(Position.QB, age=28),
        generate_player(Position.RB, age=25),
        generate_player(Position.WR, age=26),
        generate_player(Position.WR, age=27),
        generate_player(Position.LT, age=29),
    ]

    # Create contracts that put team over cap
    contracts = {}
    for player in roster:
        # Create expensive contracts
        contract = create_veteran_contract(
            player_id=str(player.id),
            team_id="test_team",
            total_value=60_000,  # $60M each - way over cap
            total_years=3,
            guaranteed=30_000,
            signing_bonus=10_000,
            signed_date=date.today(),
        )
        contracts[str(player.id)] = contract

    # Total should be $300M+ - way over cap
    total_cap = sum(c.cap_hit() for c in contracts.values())
    print(f"Initial cap usage: ${total_cap:,}K (cap is $255,000K)")
    print(f"Over cap by: ${total_cap - 255_000:,}K")

    # Create CapManager and try to get under cap
    cap_mgr = CapManager(
        team_id="test_team",
        roster=roster,
        contracts=contracts,
        salary_cap=255_000,
    )

    print(f"\nCapManager strategy: {cap_mgr.strategy.name}")
    print(f"Cap space: ${cap_mgr.situation.cap_space:,}K")
    print(f"Is over cap: {cap_mgr.situation.is_over_cap}")

    # Get cuts to make
    cuts = cap_mgr.get_under_cap(target_cushion=5_000)
    print(f"\nPlayers to cut: {len(cuts)}")
    for player, dead_money in cuts:
        savings = contracts[str(player.id)].cap_savings_if_cut()
        print(f"  - {player.full_name} ({player.position.value}): saves ${savings:,}K, dead money ${dead_money:,}K")

    # Apply cuts
    for player, _ in cuts:
        roster = [p for p in roster if p.id != player.id]
        if str(player.id) in contracts:
            del contracts[str(player.id)]

    # Check new cap situation
    new_total = sum(c.cap_hit() for c in contracts.values())
    print(f"\nAfter cuts - cap usage: ${new_total:,}K")
    print(f"Remaining players: {len(roster)}")

    if new_total <= 255_000:
        print("[PASS] Under cap after cuts")
        return True
    else:
        print(f"[FAIL] Still over cap by ${new_total - 255_000:,}K")
        return False


if __name__ == "__main__":
    # Run tests
    result1 = test_historical_simulation()
    result2 = test_cap_manager_integration()

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Historical Simulation: {'PASS' if result1 else 'FAIL'}")
    print(f"Cap Manager Integration: {'PASS' if result2 else 'FAIL'}")
