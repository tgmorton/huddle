#!/usr/bin/env python3
"""Run test scenarios and produce logs for analysis.

This script exercises the existing v2 systems and produces detailed
logs that can be analyzed for behavioral correctness.

Usage:
    python -m huddle.simulation.v2.testing.run_scenarios [scenario_name]

    # Run all route tests
    python -m huddle.simulation.v2.testing.run_scenarios routes

    # Run a specific route
    python -m huddle.simulation.v2.testing.run_scenarios slant

    # Run coverage tests
    python -m huddle.simulation.v2.testing.run_scenarios coverage

    # Run with verbose output
    python -m huddle.simulation.v2.testing.run_scenarios slant --verbose
"""

from __future__ import annotations

import sys
from typing import List, Optional

from ..core.vec2 import Vec2
from ..core.entities import Player, Ball, BallState, Team, Position
from ..core.clock import Clock
from ..core.events import EventBus, EventType
from ..physics.movement import MovementProfile, MovementSolver
from ..systems.route_runner import RouteRunner, RouteAssignment
from ..systems.coverage import CoverageSystem, CoverageType, ZoneType
from ..systems.passing import PassingSystem
from ..plays.routes import RouteType, get_route, ROUTE_LIBRARY

from .scenario import Scenario, ScenarioResult, ScenarioType
from .logger import PlayLogger
from .stats import PlayStats, aggregate_stats, analyze_route_execution, analyze_coverage_performance


def run_route_vs_air(
    route_type: RouteType,
    verbose: bool = False,
) -> ScenarioResult:
    """Run a route with no defender to test route execution."""
    print(f"\n{'='*60}")
    print(f"ROUTE VS AIR: {route_type.value}")
    print(f"{'='*60}")

    # Setup
    scenario = Scenario.route_vs_air(route_type)
    clock = scenario.clock
    event_bus = scenario.event_bus
    logger = scenario.logger

    # Get route and receiver
    route = get_route(route_type)
    receiver = scenario.offense[0]
    alignment = receiver.pos

    # Create movement profile
    profile = MovementProfile.from_attributes(
        speed=receiver.attributes.speed,
        acceleration=receiver.attributes.acceleration,
        agility=receiver.attributes.agility,
    )

    # Setup route runner
    route_runner = RouteRunner(event_bus)
    route_runner.assign_route(receiver, route, alignment, is_left_side=False)

    # Snap
    route_runner.start_all_routes(clock)
    logger.set_phase("route_running")

    print(f"\nRoute: {route.name}")
    print(f"Break depth: {route.break_depth} yards")
    print(f"Total depth: {route.total_depth} yards")
    print(f"Settles: {route.settles}")
    print(f"\nReceiver: speed={receiver.attributes.speed}, agility={receiver.attributes.agility}")
    print(f"Alignment: {alignment}")
    print()

    # Run simulation
    while not scenario.should_stop():
        dt = clock.tick()

        # Update route
        result, reasoning = route_runner.update(receiver, profile, dt, clock)

        # Apply movement
        receiver.pos = result.new_pos
        receiver.velocity = result.new_vel
        receiver.facing = result.new_vel.normalized() if result.new_vel.length() > 0.1 else receiver.facing

        # Log
        logger.log_tick(clock, scenario.offense, scenario.defense, scenario.ball, list(event_bus.history[-5:]))

        # Print progress
        if verbose or clock.tick_count % 10 == 0:
            assignment = route_runner.get_assignment(receiver.id)
            phase = assignment.phase.value if assignment else "?"
            print(f"[{clock.current_time:.2f}s] pos={receiver.pos} speed={result.speed_after:.1f} phase={phase}")
            if reasoning and verbose:
                print(f"          {reasoning}")

        # Check if route complete
        assignment = route_runner.get_assignment(receiver.id)
        if assignment and assignment.is_complete:
            logger.add_note("Route completed")
            # Run a few more ticks to see settling/continuing behavior
            if clock.tick_count > len(logger.ticks) + 10:
                break

    # Results
    result = scenario.get_result(success=True)

    # Analysis
    analysis = analyze_route_execution(logger, receiver.id)
    result.add_metric("total_distance", analysis["total_distance"])
    result.add_metric("top_speed", analysis["top_speed"])
    result.add_metric("time_to_break", analysis["time_to_break"])
    result.add_metric("depth_at_break", analysis["depth_at_break"])

    # Summary
    print(f"\n{'-'*40}")
    print("RESULTS:")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print(f"  Distance traveled: {analysis['total_distance']:.1f} yards")
    print(f"  Top speed: {analysis['top_speed']:.1f} yards/sec")
    if analysis["time_to_break"]:
        print(f"  Time to break: {analysis['time_to_break']:.2f}s")
    if analysis["depth_at_break"]:
        print(f"  Depth at break: {analysis['depth_at_break']:.1f} yards")

    # Final position
    print(f"  Final position: {receiver.pos}")

    return result


def run_route_vs_man(
    route_type: RouteType,
    db_speed: int = 90,
    db_coverage: int = 80,
    cushion: float = 7.0,
    verbose: bool = False,
) -> ScenarioResult:
    """Run a route vs man coverage to test coverage behavior."""
    print(f"\n{'='*60}")
    print(f"ROUTE VS MAN: {route_type.value}")
    print(f"DB: speed={db_speed}, coverage={db_coverage}, cushion={cushion}")
    print(f"{'='*60}")

    # Setup
    scenario = Scenario.route_vs_man(route_type, db_speed=db_speed, db_man_coverage=db_coverage, cushion=cushion)
    clock = scenario.clock
    event_bus = scenario.event_bus
    logger = scenario.logger

    # Get route and players
    route = get_route(route_type)
    receiver = scenario.offense[0]
    defender = scenario.defense[0]
    alignment = receiver.pos

    # Create movement profiles
    wr_profile = MovementProfile.from_attributes(
        speed=receiver.attributes.speed,
        acceleration=receiver.attributes.acceleration,
        agility=receiver.attributes.agility,
    )
    db_profile = MovementProfile.from_attributes(
        speed=defender.attributes.speed,
        acceleration=defender.attributes.acceleration,
        agility=defender.attributes.agility,
    )

    # Setup systems
    route_runner = RouteRunner(event_bus)
    route_runner.assign_route(receiver, route, alignment, is_left_side=False)

    coverage_system = CoverageSystem(event_bus)
    coverage_system.assign_man_coverage(defender, receiver.id, defender.pos)

    # Snap
    route_runner.start_all_routes(clock)
    coverage_system.start_coverage(clock)
    logger.set_phase("route_vs_coverage")

    print(f"\nRoute: {route.name} (break at {route.break_depth}yd)")
    print(f"Receiver: speed={receiver.attributes.speed}")
    print(f"Alignment: {alignment}")
    print(f"DB starting position: {defender.pos}")
    print()

    # Run simulation
    while not scenario.should_stop():
        dt = clock.tick()

        # Update receiver
        wr_result, wr_reasoning = route_runner.update(receiver, wr_profile, dt, clock)
        receiver.pos = wr_result.new_pos
        receiver.velocity = wr_result.new_vel
        receiver.facing = wr_result.new_vel.normalized() if wr_result.new_vel.length() > 0.1 else receiver.facing
        receiver.set_decision("route", wr_reasoning)

        # Update defender
        db_result, db_reasoning = coverage_system.update(
            defender, db_profile, scenario.offense, dt, clock
        )
        defender.pos = db_result.new_pos
        defender.velocity = db_result.new_vel
        defender.facing = db_result.new_vel.normalized() if db_result.new_vel.length() > 0.1 else defender.facing
        defender.set_decision("coverage", db_reasoning)

        # Calculate separation
        separation = receiver.pos.distance_to(defender.pos)

        # Log
        logger.log_tick(clock, scenario.offense, scenario.defense, scenario.ball, list(event_bus.history[-5:]))

        # Print progress
        if verbose or clock.tick_count % 10 == 0:
            wr_assignment = route_runner.get_assignment(receiver.id)
            db_assignment = coverage_system.get_assignment(defender.id)
            wr_phase = wr_assignment.phase.value if wr_assignment else "?"
            db_phase = db_assignment.phase.value if db_assignment else "?"
            print(f"[{clock.current_time:.2f}s] WR={receiver.pos.rounded()} DB={defender.pos.rounded()} sep={separation:.1f}yd")
            print(f"          WR phase={wr_phase}, DB phase={db_phase}")
            if verbose:
                print(f"          WR: {wr_reasoning[:60]}...")
                print(f"          DB: {db_reasoning[:60]}...")

        # Check if route complete (give a few extra ticks)
        assignment = route_runner.get_assignment(receiver.id)
        if assignment and assignment.is_complete:
            if clock.tick_count > len(logger.ticks) + 15:
                break

    # Results
    result = scenario.get_result(success=True)

    # Analysis
    cov_analysis = analyze_coverage_performance(logger, receiver.id, defender.id)
    result.add_metric("initial_cushion", cov_analysis["initial_cushion"])
    result.add_metric("max_separation", cov_analysis["max_separation"])
    result.add_metric("min_separation", cov_analysis["min_separation"])
    result.add_metric("separation_at_break", cov_analysis["separation_at_break"])

    # Summary
    print(f"\n{'-'*40}")
    print("RESULTS:")
    print(f"  Duration: {result.duration:.2f}s ({result.tick_count} ticks)")
    print(f"  Initial cushion: {cov_analysis['initial_cushion']:.1f} yards")
    print(f"  Max separation: {cov_analysis['max_separation']:.1f} yards")
    print(f"  Min separation: {cov_analysis['min_separation']:.1f} yards")
    if cov_analysis["separation_at_break"]:
        print(f"  Separation at break: {cov_analysis['separation_at_break']:.1f} yards")

    return result


def run_all_routes(verbose: bool = False) -> List[ScenarioResult]:
    """Run all route types vs air."""
    results = []
    for route_type in [
        RouteType.HITCH, RouteType.SLANT, RouteType.CURL,
        RouteType.OUT, RouteType.IN, RouteType.POST,
        RouteType.GO, RouteType.CORNER, RouteType.DRAG,
    ]:
        result = run_route_vs_air(route_type, verbose=verbose)
        results.append(result)
    return results


def run_coverage_tests(verbose: bool = False) -> List[ScenarioResult]:
    """Run coverage tests with various parameters."""
    results = []

    # Test different routes vs man
    for route_type in [RouteType.SLANT, RouteType.CURL, RouteType.GO]:
        result = run_route_vs_man(route_type, verbose=verbose)
        results.append(result)

    # Test different DB speeds
    print("\n" + "=" * 60)
    print("TESTING DB SPEED IMPACT")
    print("=" * 60)
    for db_speed in [85, 92, 98]:
        result = run_route_vs_man(RouteType.GO, db_speed=db_speed, verbose=verbose)
        results.append(result)
        result.add_note(f"DB speed test: {db_speed}")

    return results


def main():
    """Main entry point."""
    args = sys.argv[1:]

    verbose = "--verbose" in args or "-v" in args
    args = [a for a in args if a not in ("--verbose", "-v")]

    if not args or args[0] == "help":
        print(__doc__)
        return

    scenario_name = args[0].lower()

    if scenario_name == "routes":
        results = run_all_routes(verbose=verbose)
        print("\n" + "=" * 60)
        print("ALL ROUTES COMPLETE")
        print(f"Ran {len(results)} scenarios")

    elif scenario_name == "coverage":
        results = run_coverage_tests(verbose=verbose)
        print("\n" + "=" * 60)
        print("COVERAGE TESTS COMPLETE")
        print(f"Ran {len(results)} scenarios")

    elif scenario_name in [rt.value for rt in RouteType]:
        route_type = RouteType(scenario_name)
        run_route_vs_air(route_type, verbose=verbose)
        run_route_vs_man(route_type, verbose=verbose)

    else:
        print(f"Unknown scenario: {scenario_name}")
        print("Available: routes, coverage, or a route name (slant, curl, go, etc.)")


if __name__ == "__main__":
    main()
