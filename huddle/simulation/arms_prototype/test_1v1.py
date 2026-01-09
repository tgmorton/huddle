"""
Test script for 1v1 OL vs DL scenario.

Run with: python -m huddle.simulation.arms_prototype.test_1v1
"""

import math
from .vec2 import Vec2
from .player import Player, PlayerRole
from .arm import HandState
from .simulation import Simulation, SimulationConfig, blocker_intent, rusher_intent


def describe_situation(ol: Player, dl: Player, state) -> str:
    """
    Debug-focused situation report.
    State info for understanding what's happening, not prose.
    """
    lines = []

    dist = ol.position.distance_to(dl.position)
    dl_shed = dl.id in state.shed_players

    # Who has inside hands?
    ol_inside = ol.has_inside_hands
    dl_inside = dl.has_inside_hands

    # Determine who's winning the leverage battle
    ol_winning = ol.body.balance > dl.body.balance + 0.2
    dl_winning = dl.body.balance > ol.body.balance + 0.2

    if dl_shed:
        lines.append(f"SHED - DL free, rushing to QB")
        lines.append(f"  DL pos: ({dl.position.x:.1f}, {dl.position.y:.1f}) vel: ({dl.velocity.x:.1f}, {dl.velocity.y:.1f})")
        lines.append(f"  OL pos: ({ol.position.x:.1f}, {ol.position.y:.1f}) dist_to_dl: {dist:.1f}")
        lines.append(f"  redirect active: {dist < 2.0}")
        return "\n".join(lines)

    if dist > 1.5:
        lines.append(f"CLOSING - {dist:.1f} yds apart")
        return "\n".join(lines)

    # Engaged - show key state
    hands = "OL inside" if ol_inside else ("DL inside" if dl_inside else "contested")
    leverage = "OL winning" if ol_winning else ("DL winning" if dl_winning else "even")

    lines.append(f"ENGAGED - hands:{hands} leverage:{leverage}")

    # Position delta from start (OL started at 0,0 - DL at 0,2)
    ol_moved = f"OL moved ({ol.position.x:.1f}, {ol.position.y:.1f})"
    dl_moved = f"DL moved ({dl.position.x:.1f}, {dl.position.y - 2.0:.1f}) from start"
    lines.append(f"  {ol_moved}")
    lines.append(f"  {dl_moved}")

    # Key metrics
    lines.append(f"  OL: bal={ol.body.balance:.2f} debt={ol.feet.force_debt.length():.2f} pad={ol.body.pad_level:.2f}")
    lines.append(f"  DL: bal={dl.body.balance:.2f} debt={dl.feet.force_debt.length():.2f} pad={dl.body.pad_level:.2f}")

    # Foot state
    ol_feet = f"L:{ol.feet.left.phase.value[:4]} R:{ol.feet.right.phase.value[:4]}"
    dl_feet = f"L:{dl.feet.left.phase.value[:4]} R:{dl.feet.right.phase.value[:4]}"
    lines.append(f"  feet: OL[{ol_feet}] DL[{dl_feet}]")

    return "\n".join(lines)


def run_1v1_test(verbose: bool = True, log_moves: bool = True) -> dict:
    """
    Run a 1v1 OL vs DL test.

    Setup:
    - OL at (0, 0) facing upfield (+y)
    - DL at (0, 2) facing downfield (-y)
    - Target (QB) at (0, -5)
    - DL tries to reach QB, OL tries to block

    Returns summary of what happened.
    """
    config = SimulationConfig(
        dt=0.05,
        max_ticks=200,  # 10 seconds
        target_position=Vec2(0, -5),
    )

    sim = Simulation(config)

    # Enable verbose move logging
    if log_moves:
        sim.state._verbose = True

    # Create players
    ol = Player.create_lineman(
        id="OL",
        role=PlayerRole.BLOCKER,
        position=Vec2(0, 0),
        facing=math.pi / 2,  # Facing upfield (+y)
        weight=315,
    )

    dl = Player.create_lineman(
        id="DL",
        role=PlayerRole.RUSHER,
        position=Vec2(0, 2),
        facing=-math.pi / 2,  # Facing downfield (-y)
        weight=280,
    )

    sim.add_player(ol)
    sim.add_player(dl)

    sim.set_intent("OL", blocker_intent)
    sim.set_intent("DL", rusher_intent)

    # Run simulation with optional frame-by-frame output
    frames = []

    if verbose:
        print("=" * 60)
        print("1v1 PASS RUSH REP")
        print(f"OL: 315 lbs, protecting the quarterback")
        print(f"DL: 280 lbs, coming off the edge")
        print("=" * 60)

    while True:
        # Capture frame
        frame = sim.get_frame_data()
        frames.append(frame)

        # Print periodic updates
        if verbose and (sim.state.tick % 20 == 0):
            print(f"\n[{sim.state.time:.1f}s]")
            print(describe_situation(
                sim.state.players["OL"],
                sim.state.players["DL"],
                sim.state
            ))

        # Run tick
        if not sim.tick():
            break

    # Final result
    result = {
        "ticks": sim.state.tick,
        "time": sim.state.time,
        "rusher_won": sim.state.rusher_reached_target,
        "blocker_held": sim.state.blocker_held,
        "frames": frames,
    }

    if verbose:
        print("\n" + "=" * 60)
        if sim.state.rusher_reached_target:
            print(f"SACK! DL gets to the QB in {sim.state.time:.1f} seconds.")
        else:
            print(f"PROTECTION HOLDS. OL wins the rep after {sim.state.time:.1f} seconds.")
        print("=" * 60)

    return result


def run_multiple_tests(n: int = 10) -> None:
    """Run multiple tests to see win rates."""
    rusher_wins = 0
    blocker_wins = 0
    total_time = 0.0

    print(f"\nRunning {n} reps...")

    for i in range(n):
        result = run_1v1_test(verbose=False, log_moves=False)
        total_time += result["time"]

        if result["rusher_won"]:
            rusher_wins += 1
        else:
            blocker_wins += 1

    print(f"\nResults ({n} reps):")
    print(f"  Sacks: {rusher_wins} ({100*rusher_wins/n:.0f}%)")
    print(f"  Protection held: {blocker_wins} ({100*blocker_wins/n:.0f}%)")
    print(f"  Avg pocket time: {total_time/n:.1f}s")


if __name__ == "__main__":
    # Run single verbose test
    run_1v1_test(verbose=True)

    # Run batch tests
    print("\n")
    run_multiple_tests(20)
