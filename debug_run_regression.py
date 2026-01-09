"""Debug run game regression - compare direct vs drive play paths."""
import asyncio
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

from huddle.api.routers.v2_sim import (
    create_run_play_session, run_play_to_completion,
    drive_manager, StartDriveRequest, RunPlayRequest, run_drive_play
)
from collections import Counter


async def test_direct_path(n_plays: int = 50, verbose: bool = False):
    """Test direct create_run_play_session + run_play_to_completion."""
    print(f"\n=== DIRECT PATH ({n_plays} plays) ===")
    yards_list = []
    quality_yards = {"great": [], "average": [], "poor": []}
    quality_counts = Counter()
    concepts = ["inside_zone_right", "inside_zone_left", "power_right"]

    for i in range(n_plays):
        concept = concepts[i % len(concepts)]
        session = await create_run_play_session(concept, "cover3")

        # Get blocking quality before running
        orch = session.orchestrator
        # Run pre-snap and snap (which sets blocking quality)
        orch._do_pre_snap_reads()
        orch._do_snap()

        quality = getattr(orch, '_play_blocking_quality', 'average')
        quality_counts[quality] += 1

        # Run the play to get raw yards
        from huddle.simulation.v2.orchestrator import PlayPhase
        start_ball_y = orch.ball.pos.y if orch.ball else 0
        max_ticks = 200

        for _ in range(max_ticks):
            dt = orch.clock.tick()
            orch._update_tick(dt)
            if orch.phase == PlayPhase.POST_PLAY:
                break

        # Calculate raw yards
        end_ball_y = 0
        if orch.ball and orch.ball.carrier_id:
            carrier = orch._get_player(orch.ball.carrier_id)
            if carrier:
                end_ball_y = carrier.pos.y

        raw_yards = int(end_ball_y - start_ball_y)

        # Now run the full function to get adjusted yards
        session2 = await create_run_play_session(concept, "cover3")
        result = await run_play_to_completion(session2)
        final_yards = result.get("yards_gained", 0)

        yards_list.append(final_yards)
        quality_yards[quality].append(raw_yards)

        if verbose and i < 20:
            print(f"  Play {i+1}: quality={quality}, raw={raw_yards}, final=? (new session)")

    mean = sum(yards_list) / len(yards_list)
    stuffs = sum(1 for y in yards_list if y < 0)
    print(f"  Mean yards: {mean:.2f}")
    print(f"  Stuff rate: {100*stuffs/len(yards_list):.1f}%")
    print(f"  Min/Max: {min(yards_list)} / {max(yards_list)}")
    print(f"  Quality distribution: great={quality_counts['great']}, avg={quality_counts['average']}, poor={quality_counts['poor']}")

    for q in ["great", "average", "poor"]:
        if quality_yards[q]:
            qmean = sum(quality_yards[q]) / len(quality_yards[q])
            print(f"    {q}: raw mean = {qmean:.2f} yards ({len(quality_yards[q])} plays)")

    return yards_list


async def test_drive_path(n_plays: int = 50):
    """Test via run_drive_play (calibration test path)."""
    print(f"\n=== DRIVE PATH ({n_plays} plays) ===")
    yards_list = []
    concepts = ["inside_zone_right", "inside_zone_left", "power_right"]

    plays_run = 0
    concept_idx = 0

    while plays_run < n_plays:
        # Start a new drive
        request = StartDriveRequest(starting_yard_line=25)
        drive_state = await start_drive(request)
        drive_id = drive_state.drive_id

        # Run plays until drive ends or we have enough
        while plays_run < n_plays:
            concept = concepts[concept_idx % len(concepts)]
            concept_idx += 1

            request = RunPlayRequest(
                drive_id=drive_id,
                play_type="run",
                run_concept=concept,
            )

            try:
                result = await run_drive_play(request)
                play_result = result["play_result"]
                drive_state_dict = result["drive_state"]

                yards = play_result.get("yards_gained", 0)
                yards_list.append(yards)
                plays_run += 1

                # End drive if not active
                if drive_state_dict["status"] != "active":
                    break
            except Exception as e:
                print(f"  Error: {e}")
                break

    mean = sum(yards_list) / len(yards_list)
    stuffs = sum(1 for y in yards_list if y < 0)
    print(f"  Mean yards: {mean:.2f}")
    print(f"  Stuff rate: {100*stuffs/len(yards_list):.1f}%")
    print(f"  Min/Max: {min(yards_list)} / {max(yards_list)}")
    return yards_list


# Import start_drive
from huddle.api.routers.v2_sim import start_drive


async def trace_single_run_play():
    """Trace through a single run play to see what's happening."""
    print("\n=== SINGLE RUN PLAY TRACE ===")
    session = await create_run_play_session("inside_zone_right", "cover3")
    orch = session.orchestrator
    from huddle.simulation.v2.orchestrator import PlayPhase

    # Pre-snap and snap
    orch._do_pre_snap_reads()
    orch._do_snap()

    quality = getattr(orch, '_play_blocking_quality', 'average')
    print(f"Blocking quality: {quality}")

    # Find RB and QB
    rb = qb = None
    for p in orch.offense:
        if p.position.value == "RB":
            rb = p
        if p.position.value == "QB":
            qb = p

    print(f"QB at y={qb.pos.y:.2f}, RB at y={rb.pos.y:.2f}" if rb and qb else "Players not found")

    # Who has the ball initially?
    initial_carrier = orch._get_player(orch.ball.carrier_id) if orch.ball.carrier_id else None
    if initial_carrier:
        print(f"Ball initially with: {initial_carrier.name} ({initial_carrier.position.value})")

    start_ball_y = orch.ball.pos.y if orch.ball else 0

    # Trace every tick for first 30 ticks
    for tick in range(50):
        dt = orch.clock.tick()
        orch._update_tick(dt)

        if tick < 10 or tick % 10 == 0:
            # Count engaged defenders
            engaged = sum(1 for d in orch.defense if d.is_engaged)

            # Get blocking leverage info
            leverages = []
            for key, state in orch.block_resolver._engagements.items():
                leverages.append(f"{state.leverage:.2f}")

            # Ball carrier position
            carrier = orch._get_player(orch.ball.carrier_id) if orch.ball.carrier_id else None
            if carrier:
                yards = carrier.pos.y - start_ball_y
                lev_str = ",".join(leverages[:4]) if leverages else "none"
                print(f"  Tick {tick}: {carrier.name} ({carrier.position.value}) at y={carrier.pos.y:.2f} ({yards:.1f}yds), {engaged} engaged, lev=[{lev_str}]")

        if orch.phase == PlayPhase.POST_PLAY:
            carrier = orch._get_player(orch.ball.carrier_id) if orch.ball.carrier_id else None
            if carrier:
                yards = carrier.pos.y - start_ball_y
                print(f"  PLAY ENDED at tick {tick}: {carrier.name} tackled at {yards:.1f} yards")
            break

    if orch.phase != PlayPhase.POST_PLAY:
        print(f"  Play still running after 50 ticks")


async def test_quality_impact(n_plays: int = 100):
    """Test each quality level directly without additional randomization."""
    print(f"\n=== QUALITY IMPACT TEST ({n_plays} plays each) ===")
    from huddle.simulation.v2.orchestrator import PlayPhase
    import random

    results = {"great": [], "average": [], "poor": []}
    initial_leverages = {"great": [], "average": [], "poor": []}

    for quality_override in ["great", "average", "poor"]:
        for i in range(n_plays):
            session = await create_run_play_session("inside_zone_right", "cover3")
            orch = session.orchestrator

            # Pre-snap
            orch._do_pre_snap_reads()

            # Snap (this rolls quality)
            orch._do_snap()

            # Check if engagements exist after snap
            engagements_after_snap = len(orch.block_resolver._engagements)

            # Override the quality AFTER snap (so it's used for blocking resolution)
            from huddle.simulation.v2.resolution import blocking
            blocking._current_play_quality = quality_override
            orch._play_blocking_quality = quality_override

            if i == 0:
                print(f"  {quality_override}: engagements after snap = {engagements_after_snap}, quality = {blocking.get_play_blocking_quality()}")

            start_ball_y = orch.ball.pos.y if orch.ball else 0

            # Run first tick to create engagements
            dt = orch.clock.tick()
            orch._update_tick(dt)

            # Record initial leverage
            if i == 0:  # Only first play of each quality
                levs = [state.leverage for state in orch.block_resolver._engagements.values()]
                initial_leverages[quality_override] = levs

            # Run rest of play
            max_ticks = 199
            for _ in range(max_ticks):
                dt = orch.clock.tick()
                orch._update_tick(dt)
                if orch.phase == PlayPhase.POST_PLAY:
                    break

            # Get raw yards
            end_ball_y = 0
            if orch.ball and orch.ball.carrier_id:
                carrier = orch._get_player(orch.ball.carrier_id)
                if carrier:
                    end_ball_y = carrier.pos.y

            raw_yards = int(end_ball_y - start_ball_y)
            results[quality_override].append(raw_yards)

    # Print results
    for q in ["great", "average", "poor"]:
        yards = results[q]
        mean = sum(yards) / len(yards)
        stuffs = sum(1 for y in yards if y < 0)
        levs = initial_leverages[q]
        lev_str = ", ".join(f"{l:.2f}" for l in levs[:4]) if levs else "none"
        print(f"  {q}: mean raw = {mean:.2f} yards, stuff rate = {100*stuffs/len(yards):.1f}%, initial_lev=[{lev_str}]")


async def test_pass_game():
    """Quick pass game test."""
    print("\n=== PASS GAME TEST (100 plays) ===")
    from huddle.api.routers.v2_sim import create_pass_play_session

    results = {"complete": 0, "incomplete": 0, "interception": 0, "sack": 0}

    for i in range(100):
        session = await create_pass_play_session("mesh", "cover3")
        result = await run_play_to_completion(session)

        outcome = result.get("outcome", "unknown")
        if outcome == "complete":
            results["complete"] += 1
        elif outcome == "incomplete":
            results["incomplete"] += 1
        elif outcome == "interception":
            results["interception"] += 1
        elif outcome == "sack":
            results["sack"] += 1

    comp_rate = 100 * results["complete"] / 100
    sack_rate = 100 * results["sack"] / 100
    int_rate = 100 * results["interception"] / 100
    print(f"  Completions: {results['complete']} ({comp_rate:.1f}%)")
    print(f"  Incompletions: {results['incomplete']} ({100-comp_rate-sack_rate-int_rate:.1f}%)")
    print(f"  Sacks: {results['sack']} ({sack_rate:.1f}%)")
    print(f"  Interceptions: {results['interception']} ({int_rate:.1f}%)")


async def main():
    print("=" * 60)
    print("GAME CALIBRATION DEBUG")
    print("=" * 60)

    # Test pass game
    await test_pass_game()

    # Test blocking quality impact
    await test_quality_impact(50)

    # Trace a single play first
    await trace_single_run_play()


if __name__ == "__main__":
    asyncio.run(main())
