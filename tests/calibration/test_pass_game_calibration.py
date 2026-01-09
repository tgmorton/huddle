"""Pass Game Calibration Tests.

Tests pass game simulation output against NFL targets from research data.

NFL Targets (121,640 plays analyzed):
- Overall completion rate: 60.5%
- Clean pocket completion: 67.2%
- Under pressure completion: 41.1%
- Average yards per completion: 11.0
- Time to throw: 2.79 seconds

Completion by Depth:
- Behind LOS: 76.9%
- 0-5 yards: 74.0%
- 6-10 yards: 63.2%
- 11-15 yards: 56.8%
- 16-20 yards: 51.8%
- 21-30 yards: 38.2%
- 30+ yards: 29.8%
"""

import asyncio
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from huddle.api.routers.v2_sim import (
    session_manager, SimulationConfig, PlayerConfig,
    create_pass_play_session
)
from huddle.simulation.v2.orchestrator import PlayPhase


# =============================================================================
# NFL Calibration Targets
# =============================================================================

NFL_TARGETS = {
    # Overall rates
    "completion_rate": 60.5,
    "clean_pocket_completion": 67.2,
    "pressure_completion": 41.1,

    # Interception rates (of all pass attempts)
    "interception_rate": 2.3,  # Overall
    "clean_int_rate": 2.1,
    "pressure_int_rate": 4.1,

    # Sack rate
    "sack_rate": 6.5,  # ~6.5% of dropbacks

    # By depth (completion %)
    "depth_behind_los": 76.9,
    "depth_0_5": 74.0,
    "depth_6_10": 63.2,
    "depth_11_15": 56.8,
    "depth_16_20": 51.8,
    "depth_21_30": 38.2,
    "depth_30_plus": 29.8,

    # YAC by depth
    "yac_short": 4.2,      # 0-5 yards
    "yac_medium": 3.4,     # 6-15 yards
    "yac_deep": 5.0,       # 16+ yards (includes bombs)

    # Yards per completion
    "yards_per_completion": 11.0,

    # Tolerances
    "tolerance": {
        "completion_rate": 8.0,         # +/- 8%
        "clean_pocket_completion": 8.0,
        "pressure_completion": 10.0,
        "interception_rate": 2.0,
        "clean_int_rate": 2.0,
        "pressure_int_rate": 3.0,
        "sack_rate": 3.0,
        "depth_behind_los": 10.0,
        "depth_0_5": 10.0,
        "depth_6_10": 10.0,
        "depth_11_15": 10.0,
        "depth_16_20": 12.0,
        "depth_21_30": 15.0,
        "depth_30_plus": 15.0,
        "yac_short": 2.0,
        "yac_medium": 2.0,
        "yac_deep": 3.0,
        "yards_per_completion": 3.0,
    }
}


@dataclass
class PassResult:
    """Single pass play result."""
    outcome: str  # complete, incomplete, interception, sack
    yards: int
    air_yards: float  # Depth of target
    yac: float  # Yards after catch (if complete)
    time_to_throw: float
    was_pressure: bool = False

    @property
    def is_complete(self) -> bool:
        return self.outcome == "complete"

    @property
    def is_interception(self) -> bool:
        return self.outcome == "interception"

    @property
    def is_sack(self) -> bool:
        return self.outcome == "sack"


@dataclass
class PassCalibrationReport:
    """Calibration test results for pass game."""
    total_plays: int
    results: List[PassResult]

    # Computed metrics
    completion_rate: float = 0.0
    interception_rate: float = 0.0
    sack_rate: float = 0.0
    yards_per_completion: float = 0.0
    avg_yac: float = 0.0
    avg_time_to_throw: float = 0.0

    # By depth
    completion_by_depth: Dict[str, float] = field(default_factory=dict)
    yac_by_depth: Dict[str, float] = field(default_factory=dict)

    def compute_metrics(self):
        """Compute all metrics from results."""
        if not self.results:
            return

        n = len(self.results)
        completions = [r for r in self.results if r.is_complete]
        interceptions = [r for r in self.results if r.is_interception]
        sacks = [r for r in self.results if r.is_sack]

        # Overall rates
        self.completion_rate = 100 * len(completions) / n
        self.interception_rate = 100 * len(interceptions) / n
        self.sack_rate = 100 * len(sacks) / n

        if completions:
            self.yards_per_completion = np.mean([r.yards for r in completions])
            self.avg_yac = np.mean([r.yac for r in completions if r.yac >= 0])

        self.avg_time_to_throw = np.mean([r.time_to_throw for r in self.results if r.time_to_throw > 0])

        # Completion by depth buckets
        depth_buckets = {
            "behind_los": (float('-inf'), 0),
            "0_5": (0, 5),
            "6_10": (6, 10),
            "11_15": (11, 15),
            "16_20": (16, 20),
            "21_30": (21, 30),
            "30_plus": (30, float('inf')),
        }

        for bucket, (low, high) in depth_buckets.items():
            bucket_plays = [r for r in self.results if low <= r.air_yards < high]
            if bucket_plays:
                bucket_completions = [r for r in bucket_plays if r.is_complete]
                self.completion_by_depth[bucket] = 100 * len(bucket_completions) / len(bucket_plays)
            else:
                self.completion_by_depth[bucket] = 0.0

        # YAC by depth (short, medium, deep)
        short_completions = [r for r in completions if 0 <= r.air_yards <= 5]
        medium_completions = [r for r in completions if 6 <= r.air_yards <= 15]
        deep_completions = [r for r in completions if r.air_yards > 15]

        self.yac_by_depth["short"] = np.mean([r.yac for r in short_completions]) if short_completions else 0
        self.yac_by_depth["medium"] = np.mean([r.yac for r in medium_completions]) if medium_completions else 0
        self.yac_by_depth["deep"] = np.mean([r.yac for r in deep_completions]) if deep_completions else 0

    def compare_to_nfl(self) -> Dict[str, Dict[str, Any]]:
        """Compare metrics to NFL targets."""
        comparisons = {}

        # Main metrics
        main_metrics = [
            ("completion_rate", self.completion_rate),
            ("interception_rate", self.interception_rate),
            ("sack_rate", self.sack_rate),
            ("yards_per_completion", self.yards_per_completion),
        ]

        for metric, actual in main_metrics:
            if metric in NFL_TARGETS:
                target = NFL_TARGETS[metric]
                tolerance = NFL_TARGETS["tolerance"].get(metric, 5.0)
                diff = actual - target
                comparisons[metric] = {
                    "actual": actual,
                    "target": target,
                    "diff": diff,
                    "tolerance": tolerance,
                    "pass": abs(diff) <= tolerance,
                }

        # Depth metrics
        depth_metrics = [
            ("depth_0_5", self.completion_by_depth.get("0_5", 0)),
            ("depth_6_10", self.completion_by_depth.get("6_10", 0)),
            ("depth_11_15", self.completion_by_depth.get("11_15", 0)),
            ("depth_16_20", self.completion_by_depth.get("16_20", 0)),
        ]

        for metric, actual in depth_metrics:
            if metric in NFL_TARGETS:
                target = NFL_TARGETS[metric]
                tolerance = NFL_TARGETS["tolerance"].get(metric, 10.0)
                diff = actual - target
                comparisons[metric] = {
                    "actual": actual,
                    "target": target,
                    "diff": diff,
                    "tolerance": tolerance,
                    "pass": abs(diff) <= tolerance,
                }

        return comparisons

    def print_report(self):
        """Print formatted calibration report."""
        print("=" * 70)
        print("PASS GAME CALIBRATION REPORT")
        print("=" * 70)
        print(f"Total plays: {self.total_plays}")
        print()

        # Overall stats
        completions = sum(1 for r in self.results if r.is_complete)
        interceptions = sum(1 for r in self.results if r.is_interception)
        sacks = sum(1 for r in self.results if r.is_sack)
        incompletes = self.total_plays - completions - interceptions - sacks

        print("OUTCOMES:")
        print(f"  Completions: {completions} ({self.completion_rate:.1f}%)")
        print(f"  Incompletions: {incompletes} ({100*incompletes/self.total_plays:.1f}%)")
        print(f"  Interceptions: {interceptions} ({self.interception_rate:.1f}%)")
        print(f"  Sacks: {sacks} ({self.sack_rate:.1f}%)")
        print()

        if completions > 0:
            print("COMPLETION STATS:")
            print(f"  Yards per completion: {self.yards_per_completion:.1f} (NFL: {NFL_TARGETS['yards_per_completion']})")
            print(f"  Average YAC: {self.avg_yac:.1f}")
            print()

        # Completion by depth
        print("COMPLETION BY DEPTH:")
        print("-" * 50)
        print(f"{'Depth':<15} {'Actual':>10} {'Target':>10} {'Status':>10}")
        print("-" * 50)

        depth_map = {
            "0_5": "0-5 yds",
            "6_10": "6-10 yds",
            "11_15": "11-15 yds",
            "16_20": "16-20 yds",
            "21_30": "21-30 yds",
        }

        for key, label in depth_map.items():
            actual = self.completion_by_depth.get(key, 0)
            target_key = f"depth_{key}"
            target = NFL_TARGETS.get(target_key, 0)
            tolerance = NFL_TARGETS["tolerance"].get(target_key, 10.0)
            status = "PASS" if abs(actual - target) <= tolerance else "FAIL"
            print(f"{label:<15} {actual:>9.1f}% {target:>9.1f}% {f'[{status}]':>10}")

        print()

        # Comparison table
        print("COMPARISON TO NFL TARGETS:")
        print("-" * 70)
        print(f"{'Metric':<25} {'Actual':>10} {'Target':>10} {'Diff':>10} {'Status':>10}")
        print("-" * 70)

        comparisons = self.compare_to_nfl()
        for metric, data in comparisons.items():
            status = "PASS" if data["pass"] else "FAIL"
            status_str = f"[{status}]"

            if "rate" in metric or "depth" in metric:
                print(f"{metric:<25} {data['actual']:>9.1f}% {data['target']:>9.1f}% {data['diff']:>+9.1f}% {status_str:>10}")
            else:
                print(f"{metric:<25} {data['actual']:>10.1f} {data['target']:>10.1f} {data['diff']:>+10.1f} {status_str:>10}")

        print("-" * 70)

        # Pass/fail summary
        passed = sum(1 for d in comparisons.values() if d["pass"])
        total = len(comparisons)
        print(f"RESULT: {passed}/{total} metrics within tolerance")
        print()


async def run_single_pass_play(concept: str = "mesh", coverage: str = "cover3") -> Optional[PassResult]:
    """Run a single pass play and return the result."""
    try:
        session = await create_pass_play_session(concept, coverage)
        orch = session.orchestrator

        # Run pre-snap and snap
        orch._do_pre_snap_reads()
        orch._do_snap()

        start_time = orch.clock.current_time
        start_ball_y = orch.ball.pos.y if orch.ball else 0

        # Track throw time
        throw_time = 0.0
        threw = False

        # Run until play ends
        max_ticks = 200
        for _ in range(max_ticks):
            dt = orch.clock.tick()
            orch._update_tick(dt)

            # Detect throw using is_in_flight property
            if not threw and orch.ball and orch.ball.is_in_flight:
                throw_time = orch.clock.current_time - start_time
                threw = True

            if orch.phase == PlayPhase.POST_PLAY:
                break

        # Determine outcome
        outcome = orch._result_outcome or "unknown"

        # Calculate yards
        end_ball_y = 0
        if orch.ball and orch.ball.carrier_id:
            carrier = orch._get_player(orch.ball.carrier_id)
            if carrier:
                end_ball_y = carrier.pos.y

        yards_gained = int(end_ball_y - start_ball_y)

        # Get air yards from actual throw distance
        # Calculate from ball flight if available
        air_yards = 10.0  # Default
        passing_system = getattr(orch, 'passing_system', None)
        if passing_system and passing_system.throw_result:
            # Distance = velocity * flight_time
            air_yards = passing_system.throw_result.velocity * passing_system.throw_result.flight_time

        # Calculate YAC (if complete)
        yac = 0.0
        if outcome == "complete":
            # YAC = total yards - air yards
            yac = max(0, yards_gained - air_yards)

        # Was there pressure?
        was_pressure = outcome == "sack" or getattr(orch, '_qb_was_pressured', False)

        return PassResult(
            outcome=outcome,
            yards=yards_gained if outcome != "incomplete" else 0,
            air_yards=air_yards,
            yac=yac,
            time_to_throw=throw_time if threw else 0.0,
            was_pressure=was_pressure,
        )

    except Exception as e:
        print(f"Error running pass play: {e}")
        return None


async def run_pass_calibration_test(
    num_plays: int = 200,
    concepts: List[str] = None,
    coverages: List[str] = None,
) -> PassCalibrationReport:
    """Run calibration test with specified number of plays.

    Args:
        num_plays: Number of pass plays to simulate
        concepts: List of pass concepts to use
        coverages: List of coverages to face

    Returns:
        PassCalibrationReport with all results and metrics
    """
    if concepts is None:
        concepts = [
            "mesh",
            "shallow_cross",
            "smash",
            "four_verts",
            "levels",
            "curl_flat",
        ]

    if coverages is None:
        coverages = [
            "cover3",
            "cover2",
            "cover1",
            "cover4",
        ]

    results = []
    concept_idx = 0
    coverage_idx = 0

    print(f"Running {num_plays} pass plays...")

    for i in range(num_plays):
        concept = concepts[concept_idx % len(concepts)]
        coverage = coverages[coverage_idx % len(coverages)]
        concept_idx += 1
        coverage_idx += 1

        result = await run_single_pass_play(concept, coverage)
        if result:
            results.append(result)

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{num_plays} plays completed...")

    print(f"Completed {len(results)} plays")

    report = PassCalibrationReport(
        total_plays=len(results),
        results=results,
    )
    report.compute_metrics()

    return report


async def run_depth_breakdown(num_plays_per_depth: int = 50) -> Dict[str, PassCalibrationReport]:
    """Run calibration broken down by route depth.

    Uses concepts that target different depths:
    - Short (0-5): screens, hitches
    - Medium (6-15): curls, digs, mesh
    - Deep (16+): posts, corners, go routes
    """
    depth_concepts = {
        "short": ["curl_flat", "mesh"],  # Short routes
        "medium": ["levels", "shallow_cross", "smash"],  # Medium
        "deep": ["four_verts"],  # Deep
    }

    reports = {}

    for depth, concepts in depth_concepts.items():
        print(f"\nTesting {depth} routes...")
        report = await run_pass_calibration_test(
            num_plays=num_plays_per_depth,
            concepts=concepts,
        )
        reports[depth] = report
        print(f"  Completion: {report.completion_rate:.1f}%, YPC: {report.yards_per_completion:.1f}")

    return reports


async def main():
    """Run full calibration suite."""
    print("=" * 70)
    print("PASS GAME CALIBRATION SUITE")
    print("=" * 70)
    print()

    # Overall calibration
    print("PHASE 1: Overall Pass Game Calibration")
    print("-" * 70)
    report = await run_pass_calibration_test(num_plays=300)
    report.print_report()

    # Depth breakdown
    print("\n" + "=" * 70)
    print("PHASE 2: By Depth Breakdown")
    print("=" * 70)

    depth_reports = await run_depth_breakdown(num_plays_per_depth=50)

    print("\nDEPTH SUMMARY:")
    print("-" * 50)
    print(f"{'Depth':<15} {'Comp%':>10} {'YPC':>10} {'INT%':>10}")
    print("-" * 50)

    for depth, rpt in depth_reports.items():
        print(f"{depth:<15} {rpt.completion_rate:>9.1f}% {rpt.yards_per_completion:>10.1f} {rpt.interception_rate:>9.1f}%")

    print()
    print("=" * 70)
    print("CALIBRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
